"""
Pending Party Detection
========================
Determine who a ticket is waiting on - internal (us) or external (customer).

This is critical for understanding ticket queue status:
- INTERNAL: We need to respond (customer sent last message or internal note)
- EXTERNAL: Customer needs to respond (we sent last public reply)
"""

from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


class PendingParty(Enum):
    """Who the ticket is currently pending on."""
    INTERNAL = "internal"   # We (Navtor) need to act
    EXTERNAL = "external"   # Customer needs to respond
    UNKNOWN = "unknown"     # No conversations or can't determine


@dataclass
class PendingStatus:
    """Full pending status for a ticket."""
    party: PendingParty
    waiting_since: Optional[datetime]
    waiting_duration: Optional[timedelta]
    last_message_type: str  # 'customer', 'agent_response', 'internal_note'
    last_message_by: Optional[str]
    message_count: int
    customer_messages: int
    agent_responses: int
    internal_notes: int


class PendingPartyAnalyzer:
    """Determine who ticket is pending on based on conversation flow."""
    
    def __init__(self):
        pass
    
    def analyze(self, ticket) -> PendingParty:
        """
        Analyze conversation flow to determine pending party.
        
        Logic:
        - Last message from customer (incoming=True) → INTERNAL (we need to respond)
        - Last message is internal note (private=True) → INTERNAL (still with us)
        - Last message is public reply from us → EXTERNAL (customer needs to respond)
        """
        conversations = getattr(ticket, 'conversations', None) or []
        
        if not conversations:
            # No conversations - check ticket status
            status = getattr(ticket, 'status', None)
            if status in [2]:  # Open
                return PendingParty.INTERNAL
            elif status in [3]:  # Pending (waiting on customer)
                return PendingParty.EXTERNAL
            return PendingParty.UNKNOWN
        
        # Sort by created_at to get the last conversation
        try:
            sorted_convs = sorted(
                conversations, 
                key=lambda c: c.get('created_at', '') if isinstance(c, dict) else getattr(c, 'created_at', ''),
                reverse=False
            )
        except (TypeError, AttributeError):
            sorted_convs = conversations
        
        if not sorted_convs:
            return PendingParty.UNKNOWN
        
        last = sorted_convs[-1]
        
        # Handle both dict and object access
        if isinstance(last, dict):
            is_incoming = last.get('incoming', False)
            is_private = last.get('private', False)
        else:
            is_incoming = getattr(last, 'incoming', False)
            is_private = getattr(last, 'private', False)
        
        # Last message was from customer → We need to respond
        if is_incoming:
            return PendingParty.INTERNAL
        
        # Last message was an internal note → Still with us
        if is_private:
            return PendingParty.INTERNAL
        
        # Last message was our public reply → Ball is with customer
        return PendingParty.EXTERNAL
    
    def get_full_status(self, ticket) -> PendingStatus:
        """Get comprehensive pending status for a ticket."""
        conversations = getattr(ticket, 'conversations', None) or []
        
        # Count message types
        customer_messages = 0
        agent_responses = 0
        internal_notes = 0
        
        for conv in conversations:
            if isinstance(conv, dict):
                is_incoming = conv.get('incoming', False)
                is_private = conv.get('private', False)
            else:
                is_incoming = getattr(conv, 'incoming', False)
                is_private = getattr(conv, 'private', False)
            
            if is_incoming:
                customer_messages += 1
            elif is_private:
                internal_notes += 1
            else:
                agent_responses += 1
        
        # Get last message details
        waiting_since = None
        last_message_type = "unknown"
        last_message_by = None
        
        if conversations:
            try:
                sorted_convs = sorted(
                    conversations,
                    key=lambda c: c.get('created_at', '') if isinstance(c, dict) else getattr(c, 'created_at', ''),
                    reverse=False
                )
                last = sorted_convs[-1]
                
                if isinstance(last, dict):
                    created_at_str = last.get('created_at')
                    is_incoming = last.get('incoming', False)
                    is_private = last.get('private', False)
                    user_id = last.get('user_id')
                else:
                    created_at_str = getattr(last, 'created_at', None)
                    is_incoming = getattr(last, 'incoming', False)
                    is_private = getattr(last, 'private', False)
                    user_id = getattr(last, 'user_id', None)
                
                # Parse date
                if created_at_str:
                    waiting_since = self._parse_date(created_at_str)
                
                # Determine message type
                if is_incoming:
                    last_message_type = "customer"
                elif is_private:
                    last_message_type = "internal_note"
                else:
                    last_message_type = "agent_response"
                
                last_message_by = str(user_id) if user_id else None
                
            except (TypeError, AttributeError, IndexError):
                pass
        
        # Calculate waiting duration
        waiting_duration = None
        if waiting_since:
            now = datetime.now(timezone.utc)
            if waiting_since.tzinfo is None:
                waiting_since = waiting_since.replace(tzinfo=timezone.utc)
            waiting_duration = now - waiting_since
        
        return PendingStatus(
            party=self.analyze(ticket),
            waiting_since=waiting_since,
            waiting_duration=waiting_duration,
            last_message_type=last_message_type,
            last_message_by=last_message_by,
            message_count=len(conversations),
            customer_messages=customer_messages,
            agent_responses=agent_responses,
            internal_notes=internal_notes,
        )
    
    def get_waiting_time(self, ticket) -> Optional[timedelta]:
        """How long has ticket been waiting for current party?"""
        status = self.get_full_status(ticket)
        return status.waiting_duration
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from Freshdesk format."""
        if not date_str:
            return None
        
        try:
            # Handle ISO format with Z
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass
        
        # Try other formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def format_waiting_time(self, duration: Optional[timedelta]) -> str:
        """Format waiting duration as human-readable string."""
        if not duration:
            return "Unknown"
        
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            if hours:
                return f"{days}d {hours}h"
            return f"{days}d"


# Singleton instance for easy access
_analyzer = None

def get_pending_analyzer() -> PendingPartyAnalyzer:
    """Get singleton pending party analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = PendingPartyAnalyzer()
    return _analyzer


def get_pending_party(ticket) -> PendingParty:
    """Quick helper to get pending party for a ticket."""
    return get_pending_analyzer().analyze(ticket)


def get_pending_status(ticket) -> PendingStatus:
    """Quick helper to get full pending status for a ticket."""
    return get_pending_analyzer().get_full_status(ticket)
