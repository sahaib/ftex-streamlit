"""
Metrics Cache
=============
Pre-computed metrics for all pages.

Instead of each page computing metrics on-demand, we compute once
and cache until data changes. This makes page loads instant.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
import threading
from collections import defaultdict


@dataclass
class DashboardMetrics:
    """Pre-computed metrics for the Dashboard page."""
    total_tickets: int = 0
    open_tickets: int = 0
    pending_tickets: int = 0
    resolved_tickets: int = 0
    closed_tickets: int = 0
    
    # SLA
    sla_compliance_rate: float = 0.0
    avg_first_response_hours: float = 0.0
    avg_resolution_hours: float = 0.0
    
    # Pending party breakdown
    pending_internal: int = 0  # Waiting on us
    pending_external: int = 0  # Waiting on customer
    
    # Trends (last 7 days)
    tickets_created_7d: int = 0
    tickets_resolved_7d: int = 0
    
    # Priority distribution
    priority_urgent: int = 0
    priority_high: int = 0
    priority_medium: int = 0
    priority_low: int = 0
    
    # Category distribution
    categories: Dict[str, int] = field(default_factory=dict)
    
    # Date computed
    computed_at: Optional[str] = None


@dataclass
class AgentMetrics:
    """Pre-computed metrics for a single agent."""
    agent_id: int = 0
    agent_name: str = ""
    
    total_tickets: int = 0
    open_tickets: int = 0
    resolved_tickets: int = 0
    
    avg_resolution_hours: float = 0.0
    avg_first_response_hours: float = 0.0
    sla_compliance_rate: float = 0.0
    
    # Current workload
    current_pending: int = 0
    pending_internal: int = 0
    pending_external: int = 0
    
    # Categories handled
    top_categories: List[Dict] = field(default_factory=list)


@dataclass
class EntityMetrics:
    """Pre-computed metrics for a single entity (vessel, customer, etc.)."""
    entity_name: str = ""
    
    total_tickets: int = 0
    open_tickets: int = 0
    resolved_tickets: int = 0
    
    avg_resolution_hours: float = 0.0
    health_score: float = 100.0
    
    # Issues
    top_issues: List[str] = field(default_factory=list)
    
    # Pending
    pending_internal: int = 0
    pending_external: int = 0


@dataclass
class AIMetrics:
    """Pre-computed metrics for AI Analysis page."""
    total_analyzed: int = 0
    total_unanalyzed: int = 0
    
    # Category distribution
    category_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Sentiment distribution
    sentiment_positive: int = 0
    sentiment_neutral: int = 0
    sentiment_negative: int = 0
    
    # Escalation risk
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    
    # Issues
    total_issues_found: int = 0
    tickets_with_multi_issues: int = 0


class MetricsCache:
    """
    Pre-computed metrics cache for instant page loading.
    
    Usage:
        cache = MetricsCache()
        cache.recompute(tickets)
        dashboard = cache.get_dashboard_metrics()
        agents = cache.get_agent_metrics()
    """
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / ".ftex_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_path = self.cache_dir / "metrics_cache.json"
        
        # In-memory cache
        self._dashboard: Optional[DashboardMetrics] = None
        self._agents: Dict[int, AgentMetrics] = {}
        self._entities: Dict[str, EntityMetrics] = {}
        self._ai: Optional[AIMetrics] = None
        self._data_hash: Optional[str] = None
        
        self._lock = threading.RLock()
        
        # Load from disk
        self._load()
    
    def recompute(self, tickets: List, config=None, kv_cache=None):
        """
        Recompute all metrics from ticket data.
        
        Args:
            tickets: List of Ticket objects
            config: Optional ConfigManager for SLA thresholds
            kv_cache: Optional KVCache for AI results
        """
        with self._lock:
            self._compute_dashboard(tickets, config)
            self._compute_agents(tickets, config)
            self._compute_entities(tickets, config)
            self._compute_ai(tickets, kv_cache)
            self._save()
    
    # =========================================================================
    # GETTERS
    # =========================================================================
    
    def get_dashboard_metrics(self) -> Optional[DashboardMetrics]:
        """Get pre-computed dashboard metrics."""
        return self._dashboard
    
    def get_agent_metrics(self, agent_id: int = None) -> Dict[int, AgentMetrics]:
        """Get agent metrics. If agent_id specified, returns just that agent."""
        if agent_id is not None:
            return {agent_id: self._agents.get(agent_id)}
        return dict(self._agents)
    
    def get_entity_metrics(self, entity_name: str = None) -> Dict[str, EntityMetrics]:
        """Get entity metrics. If entity_name specified, returns just that entity."""
        if entity_name is not None:
            return {entity_name: self._entities.get(entity_name)}
        return dict(self._entities)
    
    def get_ai_metrics(self) -> Optional[AIMetrics]:
        """Get AI analysis metrics."""
        return self._ai
    
    def is_valid(self) -> bool:
        """Check if cache has been computed."""
        return self._dashboard is not None
    
    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    def _compute_dashboard(self, tickets: List, config=None):
        """Compute dashboard metrics."""
        from .pending_party import PendingPartyAnalyzer, PendingParty
        
        analyzer = PendingPartyAnalyzer()
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        
        # Get SLA thresholds from config
        frt_threshold = 12  # hours
        resolution_threshold = 24  # hours
        if config:
            frt_threshold = config.get('sla', 'first_response_hours', default=12)
            resolution_threshold = config.get('sla', 'resolution_hours', default=24)
        
        metrics = DashboardMetrics()
        metrics.total_tickets = len(tickets)
        
        first_response_times = []
        resolution_times = []
        sla_met = 0
        categories = defaultdict(int)
        
        for ticket in tickets:
            status = getattr(ticket, 'status', 0)
            priority = getattr(ticket, 'priority', 0)
            
            # Status counts
            if status == 2:
                metrics.open_tickets += 1
            elif status == 3:
                metrics.pending_tickets += 1
            elif status == 4:
                metrics.resolved_tickets += 1
            elif status == 5:
                metrics.closed_tickets += 1
            
            # Pending party
            pending = analyzer.analyze(ticket)
            if pending == PendingParty.INTERNAL:
                metrics.pending_internal += 1
            elif pending == PendingParty.EXTERNAL:
                metrics.pending_external += 1
            
            # Priority
            if priority == 4:
                metrics.priority_urgent += 1
            elif priority == 3:
                metrics.priority_high += 1
            elif priority == 2:
                metrics.priority_medium += 1
            elif priority == 1:
                metrics.priority_low += 1
            
            # FRT and resolution time
            frt = getattr(ticket, 'first_response_time', None)
            if frt and frt > 0:
                first_response_times.append(frt)
                if frt <= frt_threshold:
                    sla_met += 1
            
            resolution = getattr(ticket, 'resolution_time', None)
            if resolution and resolution > 0:
                resolution_times.append(resolution)
            
            # Recent tickets
            created_at = getattr(ticket, 'created_at', None)
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if created_at >= seven_days_ago:
                        metrics.tickets_created_7d += 1
                except:
                    pass
            
            # Category
            category = getattr(ticket, 'type', None) or getattr(ticket, 'category', None) or 'Uncategorized'
            categories[category] += 1
        
        # Averages
        if first_response_times:
            metrics.avg_first_response_hours = sum(first_response_times) / len(first_response_times)
        if resolution_times:
            metrics.avg_resolution_hours = sum(resolution_times) / len(resolution_times)
        if metrics.total_tickets > 0:
            metrics.sla_compliance_rate = sla_met / metrics.total_tickets
        
        metrics.categories = dict(categories)
        metrics.computed_at = now.isoformat()
        
        self._dashboard = metrics
    
    def _compute_agents(self, tickets: List, config=None):
        """Compute per-agent metrics."""
        from .pending_party import PendingPartyAnalyzer, PendingParty
        
        analyzer = PendingPartyAnalyzer()
        agent_tickets = defaultdict(list)
        
        for ticket in tickets:
            responder_id = getattr(ticket, 'responder_id', None)
            if responder_id:
                agent_tickets[responder_id].append(ticket)
        
        for agent_id, tix in agent_tickets.items():
            metrics = AgentMetrics(agent_id=agent_id)
            metrics.total_tickets = len(tix)
            
            resolution_times = []
            categories = defaultdict(int)
            
            for ticket in tix:
                status = getattr(ticket, 'status', 0)
                
                if status in [2, 3]:
                    metrics.open_tickets += 1
                    
                    pending = analyzer.analyze(ticket)
                    if pending == PendingParty.INTERNAL:
                        metrics.pending_internal += 1
                    elif pending == PendingParty.EXTERNAL:
                        metrics.pending_external += 1
                        
                elif status in [4, 5]:
                    metrics.resolved_tickets += 1
                
                resolution = getattr(ticket, 'resolution_time', None)
                if resolution and resolution > 0:
                    resolution_times.append(resolution)
                
                category = getattr(ticket, 'type', None) or 'Other'
                categories[category] += 1
            
            if resolution_times:
                metrics.avg_resolution_hours = sum(resolution_times) / len(resolution_times)
            
            metrics.current_pending = metrics.open_tickets
            metrics.top_categories = [
                {'name': k, 'count': v}
                for k, v in sorted(categories.items(), key=lambda x: -x[1])[:5]
            ]
            
            self._agents[agent_id] = metrics
    
    def _compute_entities(self, tickets: List, config=None):
        """Compute per-entity metrics."""
        from .pending_party import PendingPartyAnalyzer, PendingParty
        
        analyzer = PendingPartyAnalyzer()
        entity_field = 'entity_name'
        if config:
            entity_field = config.get('industry', 'entity_field', default='entity_name')
        
        entity_tickets = defaultdict(list)
        
        for ticket in tickets:
            entity = getattr(ticket, 'entity_name', None)
            if not entity:
                # Try custom fields
                cf = getattr(ticket, 'custom_fields', {}) or {}
                entity = cf.get('cf_vesselname') or cf.get('cf_company') or 'Unknown'
            if entity:
                entity_tickets[entity].append(ticket)
        
        for entity_name, tix in entity_tickets.items():
            metrics = EntityMetrics(entity_name=entity_name)
            metrics.total_tickets = len(tix)
            
            resolution_times = []
            
            for ticket in tix:
                status = getattr(ticket, 'status', 0)
                
                if status in [2, 3]:
                    metrics.open_tickets += 1
                    pending = analyzer.analyze(ticket)
                    if pending == PendingParty.INTERNAL:
                        metrics.pending_internal += 1
                    elif pending == PendingParty.EXTERNAL:
                        metrics.pending_external += 1
                elif status in [4, 5]:
                    metrics.resolved_tickets += 1
                
                resolution = getattr(ticket, 'resolution_time', None)
                if resolution and resolution > 0:
                    resolution_times.append(resolution)
            
            if resolution_times:
                metrics.avg_resolution_hours = sum(resolution_times) / len(resolution_times)
            
            # Health score based on open/pending
            if metrics.total_tickets > 0:
                open_ratio = metrics.open_tickets / metrics.total_tickets
                metrics.health_score = max(0, 100 - (open_ratio * 50) - (metrics.pending_internal * 5))
            
            self._entities[entity_name] = metrics
    
    def _compute_ai(self, tickets: List, kv_cache=None):
        """Compute AI analysis metrics."""
        metrics = AIMetrics()
        
        if kv_cache is None:
            try:
                from .kv_cache import get_cache
                kv_cache = get_cache()
            except:
                pass
        
        categories = defaultdict(int)
        
        for ticket in tickets:
            ticket_id = getattr(ticket, 'id', None)
            if ticket_id and kv_cache and kv_cache.has_ticket(ticket_id):
                metrics.total_analyzed += 1
                
                intel = kv_cache.get_ticket_intelligence(ticket_id)
                if intel:
                    if intel.category:
                        categories[intel.category] += 1
                    
                    if intel.escalation_risk > 0.7:
                        metrics.high_risk_count += 1
                    elif intel.escalation_risk > 0.3:
                        metrics.medium_risk_count += 1
                    else:
                        metrics.low_risk_count += 1
                    
                    if intel.issue_count > 0:
                        metrics.total_issues_found += intel.issue_count
                    if intel.issue_count > 1:
                        metrics.tickets_with_multi_issues += 1
            else:
                metrics.total_unanalyzed += 1
        
        metrics.category_distribution = dict(categories)
        self._ai = metrics
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def _load(self):
        """Load cache from disk."""
        if not self.cache_path.exists():
            return
        
        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
            
            if 'dashboard' in data:
                self._dashboard = DashboardMetrics(**data['dashboard'])
            
            if 'agents' in data:
                for aid_str, am in data['agents'].items():
                    self._agents[int(aid_str)] = AgentMetrics(**am)
            
            if 'entities' in data:
                for name, em in data['entities'].items():
                    self._entities[name] = EntityMetrics(**em)
            
            if 'ai' in data:
                self._ai = AIMetrics(**data['ai'])
                
        except Exception as e:
            print(f"Warning: Could not load metrics cache: {e}")
    
    def _save(self):
        """Save cache to disk."""
        try:
            data = {
                'dashboard': asdict(self._dashboard) if self._dashboard else None,
                'agents': {str(k): asdict(v) for k, v in self._agents.items()},
                'entities': {k: asdict(v) for k, v in self._entities.items()},
                'ai': asdict(self._ai) if self._ai else None,
            }
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save metrics cache: {e}")
    
    def invalidate(self):
        """Clear the cache."""
        with self._lock:
            self._dashboard = None
            self._agents.clear()
            self._entities.clear()
            self._ai = None
            if self.cache_path.exists():
                self.cache_path.unlink()


# =========================================================================
# SINGLETON ACCESS
# =========================================================================

_metrics_instance: Optional[MetricsCache] = None

def get_metrics_cache() -> MetricsCache:
    """Get singleton metrics cache instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCache()
    return _metrics_instance


def recompute_metrics(tickets: List, config=None, kv_cache=None):
    """Helper to recompute all metrics."""
    get_metrics_cache().recompute(tickets, config, kv_cache)
