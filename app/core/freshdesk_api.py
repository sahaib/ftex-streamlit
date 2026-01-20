"""
Freshdesk API Client
====================
Built-in Freshdesk integration for live ticket extraction.

Based on freshdesk_extractor_v2.py but designed as a library for in-app use.
"""

import os
import time
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
from requests.auth import HTTPBasicAuth
from dataclasses import dataclass


@dataclass
class FreshdeskConfig:
    """Configuration for Freshdesk connection."""
    domain: str
    api_key: str
    group_id: Optional[int] = None
    include_conversations: bool = True
    include_notes: bool = True
    requests_per_minute: int = 40
    days_to_fetch: int = 180


@dataclass
class SyncProgress:
    """Progress state for sync operations."""
    phase: str = "initializing"
    current: int = 0
    total: int = 0
    current_ticket_id: Optional[int] = None
    current_ticket_subject: Optional[str] = None
    errors: int = 0
    rate_limit_remaining: int = 4000


class FreshdeskClient:
    """
    Freshdesk API client for live ticket extraction.
    
    Usage:
        client = FreshdeskClient(config)
        if client.test_connection():
            tickets = client.fetch_tickets(days=180, on_progress=callback)
    """
    
    BASE_URL = "https://{domain}.freshdesk.com/api/v2"
    
    STATUS_MAP = {2: 'Open', 3: 'Pending', 4: 'Resolved', 5: 'Closed'}
    PRIORITY_MAP = {1: 'Low', 2: 'Medium', 3: 'High', 4: 'Urgent'}
    SOURCE_MAP = {1: 'Email', 2: 'Portal', 3: 'Phone', 7: 'Chat', 9: 'Feedback Widget', 10: 'Outbound Email'}
    
    def __init__(self, config: FreshdeskConfig = None, domain: str = None, api_key: str = None):
        """
        Initialize client with config or individual parameters.
        
        Args:
            config: FreshdeskConfig object
            domain: Freshdesk subdomain (alternative to config)
            api_key: API key (alternative to config)
        """
        if config:
            self.config = config
        else:
            self.config = FreshdeskConfig(
                domain=domain or os.getenv('FRESHDESK_DOMAIN', ''),
                api_key=api_key or os.getenv('FRESHDESK_API_KEY', ''),
                group_id=int(os.getenv('FRESHDESK_GROUP_ID', '0')) or None,
            )
        
        self.base_url = self.BASE_URL.format(domain=self.config.domain)
        
        # Session setup
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.config.api_key, 'X')
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Rate limiting
        self.min_request_interval = 60.0 / self.config.requests_per_minute
        self.last_request_time = 0.0
        
        # Progress tracking
        self.progress = SyncProgress()
    
    def test_connection(self) -> bool:
        """Test API connectivity."""
        try:
            response = self._request('tickets', params={'per_page': 1})
            return response is not None
        except Exception as e:
            print(f"[FreshdeskClient] Connection test failed: {e}")
            return False
    
    def get_rate_limit_info(self) -> Dict[str, int]:
        """Get current rate limit status."""
        return {
            'remaining': self.progress.rate_limit_remaining,
            'total': 4000,
        }
    
    def fetch_tickets(
        self,
        days: int = None,
        group_id: int = None,
        on_progress: Callable[[SyncProgress], None] = None,
    ) -> List[Dict]:
        """
        Fetch tickets from Freshdesk.
        
        Args:
            days: Number of days to look back (default: from config)
            group_id: Filter by group ID (default: from config)
            on_progress: Callback for progress updates
            
        Returns:
            List of ticket dictionaries with conversations
        """
        days = days or self.config.days_to_fetch
        group_id = group_id or self.config.group_id
        
        # Phase 1: Discover ticket IDs
        self.progress.phase = "discovering"
        if on_progress:
            on_progress(self.progress)
        
        ticket_ids = self._discover_tickets(days, group_id)
        
        if not ticket_ids:
            return []
        
        # Phase 2: Fetch full details
        self.progress.phase = "fetching"
        self.progress.total = len(ticket_ids)
        self.progress.current = 0
        
        if on_progress:
            on_progress(self.progress)
        
        tickets = []
        for i, ticket_id in enumerate(ticket_ids):
            self.progress.current = i + 1
            self.progress.current_ticket_id = ticket_id
            
            try:
                ticket = self._fetch_ticket_full(ticket_id)
                if ticket:
                    self.progress.current_ticket_subject = ticket.get('subject', '')[:50]
                    tickets.append(ticket)
            except Exception as e:
                self.progress.errors += 1
                print(f"[FreshdeskClient] Error fetching #{ticket_id}: {e}")
            
            if on_progress:
                on_progress(self.progress)
        
        self.progress.phase = "complete"
        if on_progress:
            on_progress(self.progress)
        
        return tickets
    
    def fetch_single_ticket(self, ticket_id: int) -> Optional[Dict]:
        """Fetch a single ticket with conversations."""
        return self._fetch_ticket_full(ticket_id)
    
    def refresh_tickets(
        self,
        existing_tickets: List[Dict],
        on_progress: Callable[[SyncProgress], None] = None,
    ) -> List[Dict]:
        """
        Refresh existing tickets with latest data.
        
        Args:
            existing_tickets: List of already loaded tickets
            on_progress: Progress callback
            
        Returns:
            Updated list of tickets
        """
        self.progress.phase = "refreshing"
        self.progress.total = len(existing_tickets)
        self.progress.current = 0
        
        if on_progress:
            on_progress(self.progress)
        
        refreshed = []
        for i, old_ticket in enumerate(existing_tickets):
            ticket_id = old_ticket.get('id')
            if not ticket_id:
                refreshed.append(old_ticket)
                continue
            
            self.progress.current = i + 1
            self.progress.current_ticket_id = ticket_id
            
            try:
                new_ticket = self._fetch_ticket_full(ticket_id)
                if new_ticket:
                    refreshed.append(new_ticket)
                else:
                    refreshed.append(old_ticket)  # Keep old if fetch failed
            except Exception as e:
                self.progress.errors += 1
                refreshed.append(old_ticket)
            
            if on_progress:
                on_progress(self.progress)
        
        self.progress.phase = "complete"
        return refreshed
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        if self.progress.rate_limit_remaining < 100:
            print("[FreshdeskClient] Rate limit low, waiting 60s...")
            time.sleep(60)
    
    def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 3,
    ) -> Optional[Any]:
        """Make rate-limited API request with retry logic."""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retry_count):
            self._wait_for_rate_limit()
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                self.last_request_time = time.time()
                
                # Update rate limits
                self.progress.rate_limit_remaining = int(
                    response.headers.get('x-ratelimit-remaining', self.progress.rate_limit_remaining)
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"[FreshdeskClient] Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                elif response.status_code == 404:
                    return None
                else:
                    if attempt < retry_count - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise
        
        return None
    
    def _discover_tickets(self, days: int, group_id: Optional[int]) -> List[int]:
        """Discover all ticket IDs in date range using search API."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Create weekly chunks to handle large date ranges
        chunks = []
        chunk_end = end_date
        while chunk_end > start_date:
            chunk_start = max(chunk_end - timedelta(days=7), start_date)
            chunks.append((chunk_start, chunk_end))
            chunk_end = chunk_start
        
        all_ticket_ids = []
        seen_ids = set()
        
        for chunk_start, chunk_end in chunks:
            chunk_ids = self._search_chunk(group_id, chunk_start, chunk_end)
            
            for tid in chunk_ids:
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    all_ticket_ids.append(tid)
        
        return all_ticket_ids
    
    def _search_chunk(
        self,
        group_id: Optional[int],
        start_date: datetime,
        end_date: datetime,
    ) -> List[int]:
        """Search tickets in a date range."""
        ticket_ids = []
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Build query
        if group_id:
            query = f'"group_id:{group_id} AND updated_at:\'{start_str}\' AND updated_at:<\'{end_str}\'"'
        else:
            query = f'"updated_at:>\'{start_str}\' AND updated_at:<\'{end_str}\'"'
        
        page = 1
        while page <= 10:
            result = self._request('search/tickets', params={'query': query, 'page': page})
            
            if not result:
                break
            
            tickets = result.get('results', [])
            if not tickets:
                break
            
            for t in tickets:
                ticket_ids.append(t['id'])
            
            if len(tickets) < 30:
                break
            
            page += 1
        
        return ticket_ids
    
    def _fetch_ticket_full(self, ticket_id: int) -> Optional[Dict]:
        """Fetch full ticket details with conversations."""
        ticket = self._request(
            f'tickets/{ticket_id}',
            params={'include': 'requester,company,stats'}
        )
        
        if not ticket:
            return None
        
        # Get ALL conversations (pagination)
        if self.config.include_conversations:
            conversations = []
            page = 1
            
            while True:
                convs = self._request(
                    f'tickets/{ticket_id}/conversations',
                    params={'per_page': 100, 'page': page}
                )
                
                if not convs:
                    break
                
                conversations.extend(convs)
                
                if len(convs) < 100:
                    break
                
                page += 1
            
            ticket['conversations'] = conversations
        
        # Add derived fields
        ticket['status_name'] = self.STATUS_MAP.get(ticket.get('status'), 'Unknown')
        ticket['priority_name'] = self.PRIORITY_MAP.get(ticket.get('priority'), 'Unknown')
        ticket['source_name'] = self.SOURCE_MAP.get(ticket.get('source'), 'Unknown')
        ticket['response_count'] = len(ticket.get('conversations', []))
        
        # Calculate resolution time
        if ticket.get('stats') and ticket['stats'].get('resolved_at'):
            try:
                created = datetime.fromisoformat(ticket['created_at'].replace('Z', '+00:00'))
                resolved = datetime.fromisoformat(ticket['stats']['resolved_at'].replace('Z', '+00:00'))
                ticket['resolution_time_hours'] = (resolved - created).total_seconds() / 3600
            except:
                pass
        
        return ticket


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_client_from_config(config_manager) -> FreshdeskClient:
    """Create client from ConfigManager settings."""
    fd_config = FreshdeskConfig(
        domain=config_manager.get('freshdesk', 'domain', default=''),
        api_key=config_manager.get('freshdesk', 'api_key', default=''),
        group_id=config_manager.get('freshdesk', 'group_id', default=None),
        include_conversations=config_manager.get('freshdesk', 'include_conversations', default=True),
        include_notes=config_manager.get('freshdesk', 'include_notes', default=True),
        days_to_fetch=config_manager.get('freshdesk', 'days_to_fetch', default=180),
    )
    return FreshdeskClient(config=fd_config)


def create_client_from_env() -> FreshdeskClient:
    """Create client from environment variables."""
    return FreshdeskClient(config=FreshdeskConfig(
        domain=os.getenv('FRESHDESK_DOMAIN', ''),
        api_key=os.getenv('FRESHDESK_API_KEY', ''),
        group_id=int(os.getenv('FRESHDESK_GROUP_ID', '0')) or None,
    ))
