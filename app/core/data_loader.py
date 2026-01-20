"""
Data Loader
===========
Handles loading, parsing, and preprocessing of ticket data.
Supports JSON, CSV, and API sources.
"""

import json
import csv
import re
import html
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import io

# Try optional imports
try:
    import ijson
    IJSON_AVAILABLE = True
except ImportError:
    IJSON_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# =============================================================================
# UTILITIES
# =============================================================================

def clean_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', str(text))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00').replace('+00:00', ''))
    except:
        try:
            return datetime.strptime(dt_str[:19], '%Y-%m-%dT%H:%M:%S')
        except:
            return None


def hours_between(dt1: datetime, dt2: datetime) -> float:
    """Calculate hours between two datetimes."""
    if not dt1 or not dt2:
        return 0
    return abs((dt2 - dt1).total_seconds()) / 3600


# =============================================================================
# TICKET DATA CLASS
# =============================================================================

@dataclass
class Ticket:
    """Normalized ticket representation."""
    id: int
    subject: str
    description: str
    status: int
    priority: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    company_name: str
    requester_name: str
    requester_email: str
    responder_id: Optional[int]
    responder_name: str
    conversations: List[Dict]
    tags: List[str]
    custom_fields: Dict[str, Any]
    
    # Computed fields
    category: str = ''
    entity_name: str = ''  # Vessel, site, product, etc.
    first_response_time: Optional[float] = None
    resolution_time: Optional[float] = None
    has_agent_response: bool = False
    message_count: int = 0
    agent_message_count: int = 0
    customer_message_count: int = 0
    
    @property
    def status_name(self) -> str:
        return {2: 'Open', 3: 'Pending', 4: 'Resolved', 5: 'Closed'}.get(self.status, 'Unknown')
    
    @property
    def priority_name(self) -> str:
        return {1: 'Low', 2: 'Medium', 3: 'High', 4: 'Urgent'}.get(self.priority, 'Unknown')
    
    @property
    def is_open(self) -> bool:
        return self.status in [2, 3]
    
    @property
    def is_resolved(self) -> bool:
        return self.status in [4, 5]
    
    @property
    def days_open(self) -> int:
        if not self.created_at:
            return 0
        end = self.resolved_at or datetime.now()
        return (end - self.created_at).days
    
    @classmethod
    def from_dict(cls, data: Dict, config: Dict = None) -> 'Ticket':
        """Create Ticket from raw dictionary data."""
        config = config or {}
        
        # Parse dates
        created = parse_datetime(data.get('created_at', ''))
        updated = parse_datetime(data.get('updated_at', ''))
        
        # Resolved time from stats
        stats = data.get('stats', {}) or {}
        resolved = parse_datetime(stats.get('resolved_at', ''))
        
        # Company name
        company = data.get('company', {})
        company_name = company.get('name', '') if isinstance(company, dict) else str(company or '')
        
        # Conversations
        conversations = data.get('conversations', []) or []
        
        # Count messages
        agent_msgs = sum(1 for c in conversations if not c.get('incoming', True) and not c.get('private', False))
        cust_msgs = sum(1 for c in conversations if c.get('incoming', True))
        
        # First response time
        first_response = None
        for conv in conversations:
            if not conv.get('incoming', True) and not conv.get('private', False):
                response_time = parse_datetime(conv.get('created_at', ''))
                if created and response_time:
                    first_response = hours_between(created, response_time)
                break
        
        # Resolution time
        resolution = None
        if created and resolved:
            resolution = hours_between(created, resolved)
        
        # Custom fields
        custom = data.get('custom_fields', {}) or {}
        
        # Entity name (configurable field)
        entity_field = config.get('entity_field', 'cf_vesselname')
        entity_name = ''
        if '.' in entity_field:
            parts = entity_field.split('.')
            val = data
            for p in parts:
                val = val.get(p, {}) if isinstance(val, dict) else ''
            entity_name = str(val) if val else ''
        else:
            entity_name = str(custom.get(entity_field, '') or '')
        
        return cls(
            id=data.get('id', 0),
            subject=data.get('subject', ''),
            description=clean_html(data.get('description', '')),
            status=data.get('status', 0),
            priority=data.get('priority', 0),
            created_at=created,
            updated_at=updated,
            resolved_at=resolved,
            company_name=company_name,
            requester_name=data.get('requester', {}).get('name', '') if data.get('requester') else '',
            requester_email=data.get('requester', {}).get('email', '') if data.get('requester') else '',
            responder_id=data.get('responder_id'),
            responder_name='',  # Resolved later via agent cache
            conversations=conversations,
            tags=data.get('tags', []) or [],
            custom_fields=custom,
            entity_name=entity_name,
            first_response_time=first_response,
            resolution_time=resolution,
            has_agent_response=agent_msgs > 0,
            message_count=len(conversations),
            agent_message_count=agent_msgs,
            customer_message_count=cust_msgs,
        )


# =============================================================================
# DATA LOADER
# =============================================================================

class DataLoader:
    """Load and preprocess ticket data from various sources."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.tickets: List[Ticket] = []
        self.raw_data: List[Dict] = []
        self.metadata: Dict = {}
    
    def load_json(self, source, progress_callback=None) -> List[Ticket]:
        """Load tickets from JSON file or file-like object.
        
        Args:
            source: File path or file-like object
            progress_callback: Optional callback(current, total) for progress updates
        """
        file_size = 0
        
        # Check if we should use streaming for large files (>100MB)
        use_streaming = False
        if isinstance(source, (str, Path)):
            file_size = Path(source).stat().st_size
            use_streaming = file_size > 100_000_000 and IJSON_AVAILABLE
        elif hasattr(source, 'size'):
            file_size = source.size
            use_streaming = file_size > 100_000_000 and IJSON_AVAILABLE
        
        if use_streaming:
            return self._load_json_streaming(source, file_size, progress_callback)
        else:
            return self._load_json_standard(source, progress_callback)
    
    def _load_json_standard(self, source, progress_callback=None) -> List[Ticket]:
        """Standard JSON loading for smaller files."""
        if isinstance(source, (str, Path)):
            with open(source, 'r') as f:
                data = json.load(f)
        else:
            # File-like object (e.g., uploaded file)
            content = source.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
        
        # Handle different JSON structures
        if isinstance(data, list):
            self.raw_data = data
        elif isinstance(data, dict):
            self.raw_data = data.get('tickets', data.get('data', []))
        else:
            self.raw_data = []
        
        # Convert to Ticket objects with progress
        entity_config = {'entity_field': self.config.get('industry', {}).get('entity_field', 'company.name')}
        total = len(self.raw_data)
        self.tickets = []
        
        for i, t in enumerate(self.raw_data):
            self.tickets.append(Ticket.from_dict(t, entity_config))
            if progress_callback and i % 1000 == 0:
                progress_callback(i, total)
        
        if progress_callback:
            progress_callback(total, total)
        
        self._compute_metadata()
        return self.tickets
    
    def _load_json_streaming(self, source, file_size: int, progress_callback=None) -> List[Ticket]:
        """Streaming JSON loading for large files (>100MB) using ijson."""
        entity_config = {'entity_field': self.config.get('industry', {}).get('entity_field', 'company.name')}
        self.tickets = []
        self.raw_data = []
        
        # Open file for streaming
        if isinstance(source, (str, Path)):
            f = open(source, 'rb')
        else:
            # Reset file pointer for uploaded files
            source.seek(0)
            f = source
        
        try:
            # Try to detect JSON structure (array or object with tickets key)
            # Use ijson to stream parse
            ticket_count = 0
            bytes_read = 0
            
            # Try parsing as array first
            try:
                parser = ijson.items(f, 'item')
                for ticket_dict in parser:
                    self.raw_data.append(ticket_dict)
                    self.tickets.append(Ticket.from_dict(ticket_dict, entity_config))
                    ticket_count += 1
                    
                    # Update progress every 500 tickets
                    if progress_callback and ticket_count % 500 == 0:
                        # Estimate progress based on file position if available
                        if hasattr(f, 'tell'):
                            bytes_read = f.tell()
                            progress_callback(bytes_read, file_size)
            except ijson.JSONError:
                # Try as object with 'tickets' or 'data' key
                f.seek(0) if hasattr(f, 'seek') else None
                for prefix in ['tickets.item', 'data.item']:
                    try:
                        f.seek(0) if hasattr(f, 'seek') else None
                        parser = ijson.items(f, prefix)
                        for ticket_dict in parser:
                            self.raw_data.append(ticket_dict)
                            self.tickets.append(Ticket.from_dict(ticket_dict, entity_config))
                            ticket_count += 1
                            
                            if progress_callback and ticket_count % 500 == 0:
                                if hasattr(f, 'tell'):
                                    bytes_read = f.tell()
                                    progress_callback(bytes_read, file_size)
                        break  # Success, exit prefix loop
                    except (ijson.JSONError, StopIteration):
                        continue
            
            if progress_callback:
                progress_callback(file_size, file_size)
                
        finally:
            if isinstance(source, (str, Path)):
                f.close()
        
        self._compute_metadata()
        return self.tickets
    
    def load_csv(self, source) -> List[Ticket]:
        """Load tickets from CSV file."""
        if isinstance(source, (str, Path)):
            with open(source, 'r') as f:
                reader = csv.DictReader(f)
                self.raw_data = list(reader)
        else:
            content = source.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            self.raw_data = list(reader)
        
        # Map CSV fields to expected structure
        mapped_data = []
        for row in self.raw_data:
            mapped = {
                'id': int(row.get('id', row.get('ticket_id', 0))),
                'subject': row.get('subject', row.get('title', '')),
                'description': row.get('description', row.get('body', '')),
                'status': self._parse_status(row.get('status', '')),
                'priority': self._parse_priority(row.get('priority', '')),
                'created_at': row.get('created_at', row.get('created', '')),
                'updated_at': row.get('updated_at', row.get('updated', '')),
                'company': {'name': row.get('company', row.get('company_name', ''))},
                'responder_id': row.get('responder_id', row.get('agent_id')),
                'conversations': [],
                'tags': row.get('tags', '').split(',') if row.get('tags') else [],
                'custom_fields': {},
            }
            mapped_data.append(mapped)
        
        entity_config = {'entity_field': self.config.get('industry', {}).get('entity_field', 'company.name')}
        self.tickets = [Ticket.from_dict(t, entity_config) for t in mapped_data]
        
        self._compute_metadata()
        return self.tickets
    
    def _parse_status(self, status_str: str) -> int:
        """Parse status string to numeric value."""
        status_map = {
            'open': 2, 'pending': 3, 'resolved': 4, 'closed': 5,
            '2': 2, '3': 3, '4': 4, '5': 5,
        }
        return status_map.get(str(status_str).lower(), 2)
    
    def _parse_priority(self, priority_str: str) -> int:
        """Parse priority string to numeric value."""
        priority_map = {
            'low': 1, 'medium': 2, 'high': 3, 'urgent': 4,
            '1': 1, '2': 2, '3': 3, '4': 4,
        }
        return priority_map.get(str(priority_str).lower(), 2)
    
    def _compute_metadata(self):
        """Compute metadata about loaded tickets."""
        if not self.tickets:
            return
        
        dates = [t.created_at for t in self.tickets if t.created_at]
        
        self.metadata = {
            'total_tickets': len(self.tickets),
            'date_range': {
                'earliest': min(dates).isoformat() if dates else None,
                'latest': max(dates).isoformat() if dates else None,
            },
            'status_distribution': Counter(t.status_name for t in self.tickets),
            'priority_distribution': Counter(t.priority_name for t in self.tickets),
            'companies': len(set(t.company_name for t in self.tickets if t.company_name)),
            'entities': len(set(t.entity_name for t in self.tickets if t.entity_name)),
        }
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        if not self.tickets:
            return {}
        
        open_tickets = [t for t in self.tickets if t.is_open]
        resolved_tickets = [t for t in self.tickets if t.is_resolved]
        
        # SLA calculations
        sla_threshold = self.config.get('sla', {}).get('first_response_hours', 12)
        with_response = [t for t in self.tickets if t.first_response_time is not None]
        sla_met = sum(1 for t in with_response if t.first_response_time <= sla_threshold)
        sla_compliance = (sla_met / len(with_response) * 100) if with_response else 0
        
        # Stale tickets
        stale_threshold = self.config.get('sla', {}).get('stale_threshold_days', 15)
        stale = [t for t in open_tickets if t.days_open >= stale_threshold]
        
        # No response
        no_response = [t for t in self.tickets if not t.has_agent_response]
        
        return {
            'total_tickets': len(self.tickets),
            'open_tickets': len(open_tickets),
            'resolved_tickets': len(resolved_tickets),
            'pending_tickets': sum(1 for t in self.tickets if t.status == 3),
            'stale_tickets': len(stale),
            'no_response_tickets': len(no_response),
            'sla_compliance': round(sla_compliance, 1),
            'avg_first_response': round(
                sum(t.first_response_time for t in with_response) / len(with_response), 1
            ) if with_response else 0,
            'avg_resolution': round(
                sum(t.resolution_time for t in resolved_tickets if t.resolution_time) / 
                len([t for t in resolved_tickets if t.resolution_time]), 1
            ) if any(t.resolution_time for t in resolved_tickets) else 0,
            'companies': self.metadata.get('companies', 0),
            'entities': self.metadata.get('entities', 0),
        }
    
    def get_tickets_df(self) -> 'pd.DataFrame':
        """Convert tickets to pandas DataFrame."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for DataFrame operations")
        
        data = []
        for t in self.tickets:
            data.append({
                'id': t.id,
                'subject': t.subject[:80],
                'company': t.company_name,
                'entity': t.entity_name,
                'status': t.status_name,
                'priority': t.priority_name,
                'category': t.category,
                'created': t.created_at.strftime('%Y-%m-%d') if t.created_at else '',
                'responder_id': t.responder_id,
                'first_response_hrs': t.first_response_time,
                'resolution_hrs': t.resolution_time,
                'days_open': t.days_open,
                'messages': t.message_count,
            })
        
        return pd.DataFrame(data)


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_by_company(tickets: List[Ticket]) -> Dict:
    """Analyze tickets grouped by company."""
    company_data = defaultdict(lambda: {
        'tickets': 0,
        'open': 0,
        'stale': 0,
        'sla_breaches': 0,
        'high_priority': 0,
        'entities': set(),
        'resolution_times': [],
    })
    
    for t in tickets:
        company = t.company_name or '(Unknown)'
        company_data[company]['tickets'] += 1
        if t.is_open:
            company_data[company]['open'] += 1
        if t.is_open and t.days_open >= 15:
            company_data[company]['stale'] += 1
        if t.first_response_time and t.first_response_time > 12:
            company_data[company]['sla_breaches'] += 1
        if t.priority >= 3:
            company_data[company]['high_priority'] += 1
        if t.entity_name:
            company_data[company]['entities'].add(t.entity_name)
        if t.resolution_time:
            company_data[company]['resolution_times'].append(t.resolution_time)
    
    # Convert to serializable format
    result = {}
    for company, data in company_data.items():
        result[company] = {
            'tickets': data['tickets'],
            'open': data['open'],
            'stale': data['stale'],
            'sla_breaches': data['sla_breaches'],
            'high_priority': data['high_priority'],
            'entities': len(data['entities']),
            'avg_resolution': round(
                sum(data['resolution_times']) / len(data['resolution_times']), 1
            ) if data['resolution_times'] else 0,
            'health': _calculate_health(data),
        }
    
    return result


def _calculate_health(data: Dict) -> str:
    """Calculate customer health score."""
    score = 100
    
    # Penalties
    if data['stale'] > 0:
        score -= data['stale'] * 10
    if data['sla_breaches'] > 0:
        score -= data['sla_breaches'] * 5
    if data['high_priority'] > data['tickets'] * 0.3:
        score -= 15
    
    if score >= 80:
        return '🟢 Good'
    elif score >= 60:
        return '🟡 Fair'
    elif score >= 40:
        return '🟠 Needs Attention'
    else:
        return '🔴 Critical'


def build_agent_cache(tickets: List[Ticket]) -> Dict[int, str]:
    """Build a cache mapping agent IDs to agent names from ticket data."""
    agent_names = {}
    
    for t in tickets:
        if t.responder_id and t.responder_id not in agent_names:
            # Try to get name from responder_name field
            if t.responder_name:
                agent_names[t.responder_id] = t.responder_name
            else:
                # Try to extract from conversations
                for conv in t.conversations:
                    if not conv.get('incoming', True) and not conv.get('private', False):
                        user = conv.get('user', {})
                        if isinstance(user, dict) and user.get('name'):
                            agent_names[t.responder_id] = user['name']
                            break
    
    return agent_names


def analyze_by_agent(tickets: List[Ticket]) -> Dict:
    """Analyze tickets grouped by agent with premium metrics."""
    
    # Build agent name cache
    agent_cache = build_agent_cache(tickets)
    
    agent_data = defaultdict(lambda: {
        'name': '',
        'tickets': 0,
        'resolved': 0,
        'open': 0,
        'response_times': [],
        'resolution_times': [],
        'categories': Counter(),
        'message_counts': [],  # For efficiency metrics
        'first_contact_resolutions': 0,  # FCR
        'reopened': 0,  # Escalation proxy
        'created_dates': [],  # For activity patterns
        'priorities': Counter(),  # For workload complexity
        'companies': set(),  # Customer diversity
    })
    
    for t in tickets:
        if t.responder_id:
            agent = t.responder_id
            data = agent_data[agent]
            
            # Set name from cache
            if not data['name']:
                data['name'] = agent_cache.get(agent, f'Agent #{agent}')
            
            data['tickets'] += 1
            
            if t.is_resolved:
                data['resolved'] += 1
                # First Contact Resolution: resolved with <= 2 agent messages
                if t.agent_message_count <= 2 and t.resolution_time and t.resolution_time <= 24:
                    data['first_contact_resolutions'] += 1
            
            if t.is_open:
                data['open'] += 1
            
            if t.first_response_time:
                data['response_times'].append(t.first_response_time)
            
            if t.resolution_time:
                data['resolution_times'].append(t.resolution_time)
            
            if t.category:
                data['categories'][t.category] += 1
            
            # Track message counts for efficiency
            data['message_counts'].append(t.agent_message_count)
            
            # Track dates for activity patterns
            if t.created_at:
                data['created_dates'].append(t.created_at)
            
            # Track priority for complexity metrics
            data['priorities'][t.priority] += 1
            
            # Track customer diversity
            if t.company_name:
                data['companies'].add(t.company_name)
    
    # Convert to serializable format with premium metrics
    result = {}
    total_tickets = len([t for t in tickets if t.responder_id])
    
    for agent_id, data in agent_data.items():
        sla_met = sum(1 for r in data['response_times'] if r <= 12)
        sla_total = len(data['response_times'])
        
        # Premium Metric: First Contact Resolution Rate
        fcr_rate = round(data['first_contact_resolutions'] / data['resolved'] * 100, 1) if data['resolved'] else 0
        
        # Premium Metric: Ticket Touches (avg messages per resolved ticket)
        avg_touches = round(sum(data['message_counts']) / len(data['message_counts']), 1) if data['message_counts'] else 0
        
        # Premium Metric: Agent Utilization (share of total workload)
        utilization = round(data['tickets'] / total_tickets * 100, 1) if total_tickets else 0
        
        # Premium Metric: Complexity Score (% of high/urgent tickets)
        high_priority = data['priorities'].get(3, 0) + data['priorities'].get(4, 0)
        complexity = round(high_priority / data['tickets'] * 100, 1) if data['tickets'] else 0
        
        # Premium Metric: Response Consistency (std dev of response times)
        response_std = 0
        if len(data['response_times']) > 1:
            mean = sum(data['response_times']) / len(data['response_times'])
            variance = sum((x - mean) ** 2 for x in data['response_times']) / len(data['response_times'])
            response_std = round(variance ** 0.5, 1)
        
        # Premium Metric: Resolution Efficiency (resolved / total assigned)
        resolution_rate = round(data['resolved'] / data['tickets'] * 100, 1) if data['tickets'] else 0
        
        # Premium Metric: Customer Coverage (unique companies served)
        customer_coverage = len(data['companies'])
        
        # Activity Distribution by Hour
        hourly_activity = Counter()
        daily_activity = Counter()
        for dt in data['created_dates']:
            hourly_activity[dt.hour] += 1
            daily_activity[dt.strftime('%a')] += 1
        
        result[agent_id] = {
            'agent_name': data['name'],
            'tickets': data['tickets'],
            'resolved': data['resolved'],
            'open': data['open'],
            'avg_response': round(
                sum(data['response_times']) / len(data['response_times']), 1
            ) if data['response_times'] else 0,
            'avg_resolution': round(
                sum(data['resolution_times']) / len(data['resolution_times']), 1
            ) if data['resolution_times'] else 0,
            'sla_met': sla_met,
            'sla_breached': sla_total - sla_met,
            'sla_rate': round(sla_met / sla_total * 100, 1) if sla_total else 0,
            'top_category': data['categories'].most_common(1)[0][0] if data['categories'] else '',
            # Premium Metrics
            'fcr_rate': fcr_rate,
            'avg_touches': avg_touches,
            'utilization': utilization,
            'complexity': complexity,
            'response_consistency': response_std,
            'resolution_rate': resolution_rate,
            'customer_coverage': customer_coverage,
            'hourly_activity': dict(hourly_activity),
            'daily_activity': dict(daily_activity),
            'category_distribution': dict(data['categories']),
        }
    
    return result


def analyze_by_category(tickets: List[Ticket]) -> Dict:
    """Analyze tickets grouped by category."""
    category_data = defaultdict(lambda: {
        'tickets': 0,
        'open': 0,
        'stale': 0,
        'response_times': [],
        'resolution_times': [],
    })
    
    for t in tickets:
        cat = t.category or 'Uncategorized'
        category_data[cat]['tickets'] += 1
        if t.is_open:
            category_data[cat]['open'] += 1
        if t.is_open and t.days_open >= 15:
            category_data[cat]['stale'] += 1
        if t.first_response_time:
            category_data[cat]['response_times'].append(t.first_response_time)
        if t.resolution_time:
            category_data[cat]['resolution_times'].append(t.resolution_time)
    
    # Convert
    result = {}
    for cat, data in category_data.items():
        result[cat] = {
            'count': data['tickets'],
            'percent': round(data['tickets'] / len(tickets) * 100, 1) if tickets else 0,
            'open': data['open'],
            'stale': data['stale'],
            'avg_response': round(
                sum(data['response_times']) / len(data['response_times']), 1
            ) if data['response_times'] else 0,
            'avg_resolution': round(
                sum(data['resolution_times']) / len(data['resolution_times']), 1
            ) if data['resolution_times'] else 0,
        }
    
    return result
