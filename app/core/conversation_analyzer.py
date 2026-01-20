"""
Conversation Analyzer
======================
Full conversation intelligence for ticket threads.

Analyzes ALL conversations in a ticket to extract:
- Issues (multiple per ticket)
- Decisions made
- Commitments/promises
- Entities mentioned
- Products mentioned
- Action items
- Pending status

This is NOT just sentiment analysis - this is deep thread mining.
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    """Type of conversation message."""
    CUSTOMER = "customer"
    AGENT_RESPONSE = "agent_response"
    INTERNAL_NOTE = "internal_note"
    UNKNOWN = "unknown"


@dataclass
class ExtractedIssue:
    """An issue extracted from conversations."""
    title: str
    description: Optional[str] = None
    status: str = "open"  # open, resolved, declined
    source_message_idx: int = 0
    confidence: float = 1.0


@dataclass
class ExtractedDecision:
    """A decision extracted from conversations."""
    topic: str
    choice: str
    date: Optional[str] = None
    made_by: str = "unknown"  # customer, agent


@dataclass
class ExtractedCommitment:
    """A commitment or promise extracted from conversations."""
    what: str
    when: Optional[str] = None
    by_whom: str = "unknown"
    context: Optional[str] = None
    met: Optional[bool] = None


@dataclass
class ThreadAnalysis:
    """Complete analysis of a ticket's conversation thread."""
    ticket_id: int
    
    # Message counts
    total_messages: int = 0
    customer_messages: int = 0
    agent_responses: int = 0
    internal_notes: int = 0
    
    # Issues
    issues: List[ExtractedIssue] = field(default_factory=list)
    issue_count: int = 0
    is_multi_issue: bool = False
    primary_issue: Optional[str] = None
    
    # Decisions
    decisions: List[ExtractedDecision] = field(default_factory=list)
    pending_decisions: List[str] = field(default_factory=list)
    options_presented: List[str] = field(default_factory=list)
    
    # Commitments
    commitments: List[ExtractedCommitment] = field(default_factory=list)
    missed_commitments: List[ExtractedCommitment] = field(default_factory=list)
    
    # Entities and products
    entities_mentioned: List[str] = field(default_factory=list)
    products_mentioned: List[str] = field(default_factory=list)
    
    # Action items
    action_items: List[str] = field(default_factory=list)
    open_actions: List[str] = field(default_factory=list)
    
    # Communication patterns
    back_and_forth_count: int = 0
    avg_response_gap_hours: float = 0.0
    longest_gap_hours: float = 0.0
    
    # Last activity
    last_activity: Optional[str] = None
    pending_party: str = "unknown"
    
    # Analysis meta
    analyzed_at: Optional[str] = None


class ConversationAnalyzer:
    """
    Analyze ALL conversations in a ticket thread.
    
    This processes 100, 200, even 300+ messages to extract
    comprehensive intelligence.
    """
    
    def __init__(self, config=None):
        self.config = config
        
        # Issue detection patterns
        self.ISSUE_PATTERNS = [
            r'^\s*(\d+)[.)]\s*(.+?)(?=\n|$)',  # Numbered lists: "1. Issue here"
            r'(?:issue|problem|error|bug|request)[\s:]+(.+?)(?:\.|$)',  # Keywords
            r'(?:need|require|want)(?:s|ing)?\s+(.+?)(?:\.|$)',  # Needs
        ]
        
        # Decision patterns
        self.DECISION_PATTERNS = [
            r'(?:option|choice)\s*(\d+)',
            r'(?:selected|chose|decided|approved|rejected)\s+(.+?)(?:\.|$)',
            r'(?:we will|we\'ll|going with)\s+(.+?)(?:\.|$)',
        ]
        
        # Commitment patterns
        self.COMMITMENT_PATTERNS = [
            r'(by\s+(?:the\s+)?end\s+of\s+(?:the\s+)?(?:month|week|day))',
            r'(within\s+\d+\s+(?:hours?|days?|weeks?))',
            r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',  # Date
            r'(?:we will|we\'ll|shall|expect to)\s+(.+?)(?:\.|$)',
        ]
        
        # Action item patterns
        self.ACTION_PATTERNS = [
            r'(?:please|kindly)\s+(.+?)(?:\.|$)',
            r'(?:request(?:ing)?|awaiting)\s+(.+?)(?:\.|$)',
            r'(?:need(?:s|ed)?)\s+to\s+(.+?)(?:\.|$)',
        ]
        
        # Custom entity patterns (can be extended via config)
        self.ENTITY_PATTERNS = []
        if config:
            custom_patterns = config.get('patterns', 'entity_patterns', default=[])
            self.ENTITY_PATTERNS.extend(custom_patterns)
    
    def analyze(self, ticket) -> ThreadAnalysis:
        """
        Analyze all conversations in a ticket.
        
        Args:
            ticket: Ticket object with .conversations attribute
            
        Returns:
            ThreadAnalysis with all extracted intelligence
        """
        conversations = getattr(ticket, 'conversations', None) or []
        ticket_id = getattr(ticket, 'id', 0)
        
        analysis = ThreadAnalysis(ticket_id=ticket_id)
        analysis.total_messages = len(conversations)
        
        if not conversations:
            return analysis
        
        # Sort by date
        sorted_convs = self._sort_conversations(conversations)
        
        # Classify and count messages
        classified = self._classify_messages(sorted_convs)
        analysis.customer_messages = sum(1 for c in classified if c['type'] == MessageType.CUSTOMER)
        analysis.agent_responses = sum(1 for c in classified if c['type'] == MessageType.AGENT_RESPONSE)
        analysis.internal_notes = sum(1 for c in classified if c['type'] == MessageType.INTERNAL_NOTE)
        
        # Extract all text for analysis
        all_text = self._extract_all_text(sorted_convs)
        customer_text = self._extract_customer_text(sorted_convs)
        agent_text = self._extract_agent_text(sorted_convs)
        
        # Extract issues
        analysis.issues = self._extract_issues(all_text, sorted_convs)
        analysis.issue_count = len(analysis.issues)
        analysis.is_multi_issue = analysis.issue_count > 1
        if analysis.issues:
            analysis.primary_issue = analysis.issues[0].title
        
        # Extract decisions
        analysis.decisions = self._extract_decisions(agent_text, sorted_convs)
        analysis.options_presented = self._find_options(all_text)
        analysis.pending_decisions = self._find_pending_decisions(all_text)
        
        # Extract commitments
        analysis.commitments = self._extract_commitments(agent_text, sorted_convs)
        
        # Extract entities and products
        analysis.entities_mentioned = self._extract_entities(all_text, ticket)
        analysis.products_mentioned = self._extract_products(all_text, ticket)
        
        # Extract action items
        analysis.action_items = self._extract_actions(all_text)
        analysis.open_actions = self._find_open_actions(analysis.action_items, all_text)
        
        # Communication patterns
        analysis.back_and_forth_count = self._count_exchanges(classified)
        gaps = self._calculate_gaps(sorted_convs)
        if gaps:
            analysis.avg_response_gap_hours = sum(gaps) / len(gaps)
            analysis.longest_gap_hours = max(gaps)
        
        # Pending party
        analysis.pending_party = self._determine_pending_party(sorted_convs)
        
        # Last activity
        if sorted_convs:
            last = sorted_convs[-1]
            analysis.last_activity = self._get_date(last)
        
        analysis.analyzed_at = datetime.now(timezone.utc).isoformat()
        
        return analysis
    
    def _sort_conversations(self, convs: List) -> List:
        """Sort conversations by created_at."""
        try:
            return sorted(
                convs,
                key=lambda c: c.get('created_at', '') if isinstance(c, dict) else getattr(c, 'created_at', ''),
            )
        except (TypeError, AttributeError):
            return list(convs)
    
    def _classify_messages(self, convs: List) -> List[Dict]:
        """Classify each message by type."""
        result = []
        for conv in convs:
            if isinstance(conv, dict):
                incoming = conv.get('incoming', False)
                private = conv.get('private', False)
            else:
                incoming = getattr(conv, 'incoming', False)
                private = getattr(conv, 'private', False)
            
            if incoming:
                msg_type = MessageType.CUSTOMER
            elif private:
                msg_type = MessageType.INTERNAL_NOTE
            else:
                msg_type = MessageType.AGENT_RESPONSE
            
            result.append({'conv': conv, 'type': msg_type})
        
        return result
    
    def _extract_all_text(self, convs: List) -> str:
        """Extract all text from conversations."""
        texts = []
        for conv in convs:
            text = self._get_text(conv)
            if text:
                texts.append(text)
        return '\n\n'.join(texts)
    
    def _extract_customer_text(self, convs: List) -> str:
        """Extract only customer messages."""
        texts = []
        for conv in convs:
            if isinstance(conv, dict):
                incoming = conv.get('incoming', False)
            else:
                incoming = getattr(conv, 'incoming', False)
            
            if incoming:
                text = self._get_text(conv)
                if text:
                    texts.append(text)
        return '\n\n'.join(texts)
    
    def _extract_agent_text(self, convs: List) -> str:
        """Extract only agent messages."""
        texts = []
        for conv in convs:
            if isinstance(conv, dict):
                incoming = conv.get('incoming', False)
            else:
                incoming = getattr(conv, 'incoming', False)
            
            if not incoming:
                text = self._get_text(conv)
                if text:
                    texts.append(text)
        return '\n\n'.join(texts)
    
    def _get_text(self, conv) -> str:
        """Get text content from a conversation."""
        if isinstance(conv, dict):
            return conv.get('body_text', '') or ''
        return getattr(conv, 'body_text', '') or ''
    
    def _get_date(self, conv) -> Optional[str]:
        """Get created_at from a conversation."""
        if isinstance(conv, dict):
            return conv.get('created_at')
        return getattr(conv, 'created_at', None)
    
    def _extract_issues(self, text: str, convs: List) -> List[ExtractedIssue]:
        """Extract issues from text."""
        issues = []
        seen = set()
        
        # Pattern 1: Numbered items
        numbered = re.findall(r'^\s*\d+[.)]\s*(.+?)(?:\n|$)', text, re.MULTILINE)
        for item in numbered:
            title = item.strip()[:100]
            if title and title.lower() not in seen:
                seen.add(title.lower())
                issues.append(ExtractedIssue(title=title, confidence=0.9))
        
        # Pattern 2: Question marks often indicate issues
        questions = re.findall(r'([^.!?]+\?)', text)
        for q in questions[:5]:  # Limit to first 5
            title = q.strip()[:100]
            if len(title) > 20 and title.lower() not in seen:
                seen.add(title.lower())
                issues.append(ExtractedIssue(title=title, confidence=0.7))
        
        # Pattern 3: Keyword-based
        for pattern in self.ISSUE_PATTERNS[1:]:  # Skip numbered (already done)
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:3]:
                if isinstance(match, tuple):
                    match = match[-1]
                title = match.strip()[:100]
                if len(title) > 10 and title.lower() not in seen:
                    seen.add(title.lower())
                    issues.append(ExtractedIssue(title=title, confidence=0.6))
        
        return issues[:10]  # Limit to top 10
    
    def _extract_decisions(self, text: str, convs: List) -> List[ExtractedDecision]:
        """Extract decisions from text."""
        decisions = []
        
        for pattern in self.DECISION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(m for m in match if m)
                decisions.append(ExtractedDecision(
                    topic="Decision",
                    choice=match.strip()[:100],
                    made_by="agent",
                ))
        
        return decisions[:5]
    
    def _find_options(self, text: str) -> List[str]:
        """Find presented options (Option 1/2/3, etc.)."""
        options = []
        
        # Option N patterns
        matches = re.findall(r'option\s*(\d+)[:\s-]+(.+?)(?:\n|$)', text, re.IGNORECASE)
        for num, desc in matches:
            options.append(f"Option {num}: {desc.strip()[:50]}")
        
        return options[:5]
    
    def _find_pending_decisions(self, text: str) -> List[str]:
        """Find decisions still pending."""
        pending = []
        
        patterns = [
            r'(?:please|kindly)\s+(?:confirm|decide|choose|select)',
            r'(?:awaiting|waiting for)\s+(?:your|their)\s+(?:decision|approval|confirmation)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            pending.extend(matches)
        
        return pending[:3]
    
    def _extract_commitments(self, text: str, convs: List) -> List[ExtractedCommitment]:
        """Extract commitments and promises."""
        commitments = []
        
        for pattern in self.COMMITMENT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                context_start = max(0, m.start() - 50)
                context_end = min(len(text), m.end() + 50)
                commitments.append(ExtractedCommitment(
                    what=m.group(1) if m.lastindex else m.group(0),
                    context=text[context_start:context_end].strip(),
                    by_whom="agent",
                ))
        
        return commitments[:10]
    
    def _extract_entities(self, text: str, ticket) -> List[str]:
        """Extract entity names mentioned."""
        entities = set()
        
        # From ticket's entity name
        entity_name = getattr(ticket, 'entity_name', None)
        if entity_name:
            entities.add(entity_name)
        
        # From custom fields
        cf = getattr(ticket, 'custom_fields', {}) or {}
        if cf.get('cf_vesselname'):
            entities.add(cf['cf_vesselname'])
        
        # Pattern: All caps words (often ship/company names)
        caps = re.findall(r'\b([A-Z][A-Z\s]{3,}[A-Z])\b', text)
        for c in caps[:10]:
            if len(c) > 4:
                entities.add(c.strip())
        
        return list(entities)[:20]
    
    def _extract_products(self, text: str, ticket) -> List[str]:
        """Extract product names mentioned."""
        products = set()
        
        # From custom fields
        cf = getattr(ticket, 'custom_fields', {}) or {}
        if cf.get('cf_products'):
            products.add(cf['cf_products'])
        
        # From subject (often "PRODUCT | ENTITY | TYPE")
        subject = getattr(ticket, 'subject', '') or ''
        parts = subject.split('|')
        if len(parts) > 1:
            products.add(parts[0].strip())
        
        # From tags
        tags = getattr(ticket, 'tags', []) or []
        for tag in tags:
            if tag.startswith('product:'):
                products.add(tag.replace('product:', ''))
        
        return list(products)[:10]
    
    def _extract_actions(self, text: str) -> List[str]:
        """Extract action items."""
        actions = []
        
        for pattern in self.ACTION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:5]:
                action = match.strip()[:100]
                if len(action) > 10:
                    actions.append(action)
        
        return actions[:10]
    
    def _find_open_actions(self, actions: List[str], text: str) -> List[str]:
        """Find actions that appear unresolved."""
        # Simple heuristic: if no "done", "completed", "resolved" nearby
        open_actions = []
        resolution_words = ['done', 'completed', 'resolved', 'finished', 'closed']
        
        text_lower = text.lower()
        for action in actions:
            action_lower = action.lower()
            # Check if resolution words appear near this action
            is_resolved = any(word in text_lower for word in resolution_words if action_lower in text_lower)
            if not is_resolved:
                open_actions.append(action)
        
        return open_actions
    
    def _count_exchanges(self, classified: List[Dict]) -> int:
        """Count back-and-forth exchanges."""
        exchanges = 0
        last_type = None
        
        for c in classified:
            if c['type'] != last_type and c['type'] in [MessageType.CUSTOMER, MessageType.AGENT_RESPONSE]:
                if last_type is not None:
                    exchanges += 1
                last_type = c['type']
        
        return exchanges
    
    def _calculate_gaps(self, convs: List) -> List[float]:
        """Calculate time gaps between messages in hours."""
        gaps = []
        
        if len(convs) < 2:
            return gaps
        
        for i in range(1, len(convs)):
            prev_date = self._get_date(convs[i-1])
            curr_date = self._get_date(convs[i])
            
            if prev_date and curr_date:
                try:
                    prev = datetime.fromisoformat(prev_date.replace('Z', '+00:00'))
                    curr = datetime.fromisoformat(curr_date.replace('Z', '+00:00'))
                    gap_hours = (curr - prev).total_seconds() / 3600
                    if gap_hours > 0:
                        gaps.append(gap_hours)
                except:
                    pass
        
        return gaps
    
    def _determine_pending_party(self, convs: List) -> str:
        """Determine who ticket is pending on."""
        if not convs:
            return "unknown"
        
        last = convs[-1]
        if isinstance(last, dict):
            incoming = last.get('incoming', False)
            private = last.get('private', False)
        else:
            incoming = getattr(last, 'incoming', False)
            private = getattr(last, 'private', False)
        
        if incoming:
            return "internal"
        elif private:
            return "internal"
        else:
            return "external"


# =========================================================================
# SINGLETON ACCESS
# =========================================================================

_analyzer_instance: Optional[ConversationAnalyzer] = None

def get_conversation_analyzer(config=None) -> ConversationAnalyzer:
    """Get singleton conversation analyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ConversationAnalyzer(config)
    return _analyzer_instance


def analyze_ticket_conversations(ticket) -> ThreadAnalysis:
    """Quick helper to analyze a ticket's conversations."""
    return get_conversation_analyzer().analyze(ticket)
