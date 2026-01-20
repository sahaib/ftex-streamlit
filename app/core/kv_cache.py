"""
KV Cache for AI Results
========================
Persistent key-value cache for storing AI analysis results.

This cache stores:
- Ticket categorizations
- Sentiment analysis results
- Issue extractions
- Entity profiles
- Computed intelligence

Persistence: JSON file on disk, loaded into memory at startup.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
import hashlib
import threading


@dataclass
class TicketIntelligence:
    """Cached intelligence for a single ticket."""
    ticket_id: int
    
    # Categorization
    category: Optional[str] = None
    category_confidence: float = 0.0
    category_source: str = "unknown"  # 'ai', 'rule', 'user'
    
    # Issues extracted
    issues: List[str] = field(default_factory=list)
    issue_count: int = 0
    primary_issue: Optional[str] = None
    
    # Pending party
    pending_party: str = "unknown"  # 'internal', 'external', 'unknown'
    pending_since: Optional[str] = None
    
    # Sentiment/health signals
    escalation_risk: float = 0.0
    customer_frustration: float = 0.0
    resolution_confidence: float = 0.0
    
    # Decisions & commitments
    decisions: List[Dict] = field(default_factory=list)
    commitments: List[Dict] = field(default_factory=list)
    
    # Products/entities mentioned
    products: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)
    
    # Meta
    analyzed_at: Optional[str] = None
    conversation_count: int = 0
    data_hash: Optional[str] = None  # Hash of input data for invalidation


@dataclass
class EntityProfile:
    """Aggregated intelligence for an entity (vessel, customer, etc.)."""
    entity_name: str
    entity_type: str = "customer"
    
    # Aggregated metrics
    total_tickets: int = 0
    open_tickets: int = 0
    avg_resolution_hours: float = 0.0
    escalation_rate: float = 0.0
    
    # Health score (0-100)
    health_score: float = 100.0
    health_trend: str = "stable"  # 'improving', 'declining', 'stable'
    
    # Common issues
    top_issues: List[Dict] = field(default_factory=list)
    
    # Last updated
    updated_at: Optional[str] = None


class KVCache:
    """
    Persistent key-value cache for AI analysis results.
    
    Usage:
        cache = KVCache()
        cache.set_ticket_intelligence(ticket_id, intelligence)
        intel = cache.get_ticket_intelligence(ticket_id)
    """
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Default to .ftex_cache in app directory
            cache_dir = Path(__file__).parent.parent / ".ftex_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.ticket_cache_path = self.cache_dir / "ticket_intelligence.json"
        self.entity_cache_path = self.cache_dir / "entity_profiles.json"
        self.meta_cache_path = self.cache_dir / "cache_meta.json"
        
        # In-memory caches
        self._ticket_cache: Dict[int, TicketIntelligence] = {}
        self._entity_cache: Dict[str, EntityProfile] = {}
        self._meta: Dict[str, Any] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load from disk
        self._load_all()
    
    # =========================================================================
    # TICKET INTELLIGENCE
    # =========================================================================
    
    def get_ticket_intelligence(self, ticket_id: int) -> Optional[TicketIntelligence]:
        """Get cached intelligence for a ticket."""
        with self._lock:
            return self._ticket_cache.get(ticket_id)
    
    def set_ticket_intelligence(self, ticket_id: int, intel: TicketIntelligence):
        """Store intelligence for a ticket."""
        with self._lock:
            intel.analyzed_at = datetime.now(timezone.utc).isoformat()
            self._ticket_cache[ticket_id] = intel
            self._save_ticket_cache()
    
    def get_category(self, ticket_id: int) -> Optional[str]:
        """Quick access to ticket category."""
        intel = self.get_ticket_intelligence(ticket_id)
        return intel.category if intel else None
    
    def set_category(self, ticket_id: int, category: str, confidence: float = 1.0, source: str = "ai"):
        """Set just the category for a ticket."""
        with self._lock:
            intel = self._ticket_cache.get(ticket_id)
            if intel is None:
                intel = TicketIntelligence(ticket_id=ticket_id)
            intel.category = category
            intel.category_confidence = confidence
            intel.category_source = source
            intel.analyzed_at = datetime.now(timezone.utc).isoformat()
            self._ticket_cache[ticket_id] = intel
            self._save_ticket_cache()
    
    def get_pending_party(self, ticket_id: int) -> Optional[str]:
        """Quick access to pending party."""
        intel = self.get_ticket_intelligence(ticket_id)
        return intel.pending_party if intel else None
    
    def set_pending_party(self, ticket_id: int, party: str, pending_since: str = None):
        """Set pending party for a ticket."""
        with self._lock:
            intel = self._ticket_cache.get(ticket_id)
            if intel is None:
                intel = TicketIntelligence(ticket_id=ticket_id)
            intel.pending_party = party
            intel.pending_since = pending_since
            self._ticket_cache[ticket_id] = intel
            self._save_ticket_cache()
    
    def get_all_tickets(self) -> Dict[int, TicketIntelligence]:
        """Get all cached ticket intelligence."""
        with self._lock:
            return dict(self._ticket_cache)
    
    def has_ticket(self, ticket_id: int) -> bool:
        """Check if ticket is in cache."""
        return ticket_id in self._ticket_cache
    
    def invalidate_ticket(self, ticket_id: int):
        """Remove ticket from cache (force re-analysis)."""
        with self._lock:
            if ticket_id in self._ticket_cache:
                del self._ticket_cache[ticket_id]
                self._save_ticket_cache()
    
    # =========================================================================
    # ENTITY PROFILES
    # =========================================================================
    
    def get_entity_profile(self, entity_name: str) -> Optional[EntityProfile]:
        """Get cached profile for an entity."""
        with self._lock:
            return self._entity_cache.get(entity_name)
    
    def set_entity_profile(self, entity_name: str, profile: EntityProfile):
        """Store profile for an entity."""
        with self._lock:
            profile.updated_at = datetime.now(timezone.utc).isoformat()
            self._entity_cache[entity_name] = profile
            self._save_entity_cache()
    
    def get_all_entities(self) -> Dict[str, EntityProfile]:
        """Get all cached entity profiles."""
        with self._lock:
            return dict(self._entity_cache)
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def bulk_set_categories(self, categories: Dict[int, str], source: str = "ai"):
        """Set categories for multiple tickets at once."""
        with self._lock:
            for ticket_id, category in categories.items():
                intel = self._ticket_cache.get(ticket_id)
                if intel is None:
                    intel = TicketIntelligence(ticket_id=ticket_id)
                intel.category = category
                intel.category_source = source
                intel.analyzed_at = datetime.now(timezone.utc).isoformat()
                self._ticket_cache[ticket_id] = intel
            self._save_ticket_cache()
    
    def get_uncached_ticket_ids(self, ticket_ids: List[int]) -> List[int]:
        """Get list of ticket IDs not in cache."""
        with self._lock:
            return [tid for tid in ticket_ids if tid not in self._ticket_cache]
    
    def get_stale_ticket_ids(self, ticket_ids: List[int], max_age_hours: int = 24) -> List[int]:
        """Get list of ticket IDs with stale cache entries."""
        stale = []
        cutoff = datetime.now(timezone.utc)
        
        with self._lock:
            for tid in ticket_ids:
                intel = self._ticket_cache.get(tid)
                if intel is None:
                    stale.append(tid)
                elif intel.analyzed_at:
                    try:
                        analyzed = datetime.fromisoformat(intel.analyzed_at.replace('Z', '+00:00'))
                        if (cutoff - analyzed).total_seconds() > max_age_hours * 3600:
                            stale.append(tid)
                    except:
                        stale.append(tid)
                else:
                    stale.append(tid)
        
        return stale
    
    # =========================================================================
    # DATA HASH FOR INVALIDATION
    # =========================================================================
    
    def compute_ticket_hash(self, ticket) -> str:
        """Compute hash of ticket data for change detection."""
        # Include key fields that would trigger re-analysis
        data = {
            'id': getattr(ticket, 'id', 0),
            'status': getattr(ticket, 'status', 0),
            'updated_at': str(getattr(ticket, 'updated_at', '')),
            'conv_count': len(getattr(ticket, 'conversations', []) or []),
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
    
    def needs_reanalysis(self, ticket) -> bool:
        """Check if ticket needs re-analysis based on data hash."""
        ticket_id = getattr(ticket, 'id', None)
        if ticket_id is None:
            return True
        
        intel = self.get_ticket_intelligence(ticket_id)
        if intel is None:
            return True
        
        current_hash = self.compute_ticket_hash(ticket)
        return intel.data_hash != current_hash
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def _load_all(self):
        """Load all caches from disk."""
        self._load_ticket_cache()
        self._load_entity_cache()
        self._load_meta()
    
    def _load_ticket_cache(self):
        """Load ticket cache from disk."""
        if self.ticket_cache_path.exists():
            try:
                with open(self.ticket_cache_path, 'r') as f:
                    data = json.load(f)
                
                for tid_str, intel_data in data.items():
                    tid = int(tid_str)
                    self._ticket_cache[tid] = TicketIntelligence(**intel_data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Warning: Could not load ticket cache: {e}")
    
    def _save_ticket_cache(self):
        """Save ticket cache to disk."""
        try:
            data = {
                str(tid): asdict(intel)
                for tid, intel in self._ticket_cache.items()
            }
            with open(self.ticket_cache_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save ticket cache: {e}")
    
    def _load_entity_cache(self):
        """Load entity cache from disk."""
        if self.entity_cache_path.exists():
            try:
                with open(self.entity_cache_path, 'r') as f:
                    data = json.load(f)
                
                for name, profile_data in data.items():
                    self._entity_cache[name] = EntityProfile(**profile_data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Warning: Could not load entity cache: {e}")
    
    def _save_entity_cache(self):
        """Save entity cache to disk."""
        try:
            data = {
                name: asdict(profile)
                for name, profile in self._entity_cache.items()
            }
            with open(self.entity_cache_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save entity cache: {e}")
    
    def _load_meta(self):
        """Load cache metadata."""
        if self.meta_cache_path.exists():
            try:
                with open(self.meta_cache_path, 'r') as f:
                    self._meta = json.load(f)
            except:
                pass
    
    def _save_meta(self):
        """Save cache metadata."""
        try:
            self._meta['last_updated'] = datetime.now(timezone.utc).isoformat()
            with open(self.meta_cache_path, 'w') as f:
                json.dump(self._meta, f, indent=2)
        except:
            pass
    
    def clear_all(self):
        """Clear all caches (use with caution)."""
        with self._lock:
            self._ticket_cache.clear()
            self._entity_cache.clear()
            self._meta.clear()
            
            for path in [self.ticket_cache_path, self.entity_cache_path, self.meta_cache_path]:
                if path.exists():
                    path.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'tickets_cached': len(self._ticket_cache),
                'entities_cached': len(self._entity_cache),
                'cache_dir': str(self.cache_dir),
                'last_updated': self._meta.get('last_updated'),
            }


# =========================================================================
# SINGLETON ACCESS
# =========================================================================

_cache_instance: Optional[KVCache] = None

def get_cache() -> KVCache:
    """Get singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = KVCache()
    return _cache_instance


def get_ticket_intelligence(ticket_id: int) -> Optional[TicketIntelligence]:
    """Quick helper to get ticket intelligence."""
    return get_cache().get_ticket_intelligence(ticket_id)


def set_ticket_intelligence(ticket_id: int, intel: TicketIntelligence):
    """Quick helper to set ticket intelligence."""
    get_cache().set_ticket_intelligence(ticket_id, intel)
