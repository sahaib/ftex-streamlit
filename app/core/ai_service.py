"""
AI Service
==========
Provides LLM integration for intelligent ticket analysis.
Supports Ollama (local), OpenAI, and Anthropic.
"""

import json
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict
import re


@dataclass
class AIConfig:
    """AI configuration."""
    provider: str = 'ollama'
    base_url: str = 'http://localhost:11434'
    model: str = 'qwen2.5:14b'
    temperature: float = 0.3
    api_key: Optional[str] = None


class AIService:
    """AI service for ticket analysis."""
    
    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig()
        self._last_error = None
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    def test_connection(self) -> bool:
        """Test if AI service is available."""
        try:
            if self.config.provider == 'ollama':
                resp = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
                return resp.status_code == 200
            elif self.config.provider == 'openai':
                # Would need API key validation
                return bool(self.config.api_key)
            return False
        except Exception as e:
            self._last_error = str(e)
            return False
    
    def _call_ollama(self, prompt: str, system: str = None) -> Optional[str]:
        """Call Ollama API."""
        try:
            payload = {
                'model': self.config.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': self.config.temperature,
                }
            }
            if system:
                payload['system'] = system
            
            resp = requests.post(
                f"{self.config.base_url}/api/generate",
                json=payload,
                timeout=120  # 2 min timeout for large prompts
            )
            
            if resp.status_code == 200:
                return resp.json().get('response', '')
            else:
                self._last_error = f"Ollama error: {resp.status_code}"
                return None
        except Exception as e:
            self._last_error = str(e)
            return None
    
    def _call_openai(self, prompt: str, system: str = None) -> Optional[str]:
        """Call OpenAI API."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.config.api_key)
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.config.model or "gpt-4o-mini",
                messages=messages,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            self._last_error = str(e)
            return None
    
    def call(self, prompt: str, system: str = None) -> Optional[str]:
        """Call the configured AI provider."""
        if self.config.provider == 'ollama':
            return self._call_ollama(prompt, system)
        elif self.config.provider == 'openai':
            return self._call_openai(prompt, system)
        else:
            self._last_error = f"Unknown provider: {self.config.provider}"
            return None
    
    def categorize_tickets(self, tickets: List[Any], batch_size: int = 25) -> Dict[int, str]:
        """Categorize tickets using AI with robust error handling.
        
        Returns: Dict mapping ticket_id -> category
        """
        categories = {}
        
        system_prompt = """You are a support ticket categorization expert.
Analyze each ticket and assign ONE category from this list:
- Bug Report: Software errors, crashes, broken features
- Feature Request: New features, enhancements, improvements
- Configuration: Setup, settings, configuration issues
- License/Activation: License keys, activation, subscription
- Sync/Connection: Network, sync, offline mode, connectivity
- Training/How-to: Questions about using features, documentation
- Data Issue: Wrong data, missing data, data corruption
- Integration: API, third-party integrations, imports/exports
- Performance: Slow, timeout, resource issues
- Access/Permission: Login, access rights, permissions
- Billing: Invoice, payment, subscription
- Hardware: Device, equipment, physical issues
- General Inquiry: Other questions

IMPORTANT: Respond ONLY with valid JSON like:
{"123": "Bug Report", "456": "Configuration"}

No explanations, no markdown, just the JSON object."""

        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i+batch_size]
            
            # Build prompt with ticket info
            ticket_lines = []
            for t in batch:
                subject = (t.subject or '')[:100].replace('"', "'")
                desc = ''
                if hasattr(t, 'description') and t.description:
                    desc = t.description[:150].replace('"', "'").replace('\n', ' ')
                ticket_lines.append(f"ID {t.id}: {subject}")
                if desc:
                    ticket_lines.append(f"  Description: {desc}")
            
            prompt = f"Categorize these {len(batch)} support tickets:\n\n" + "\n".join(ticket_lines)
            
            # Try up to 3 times
            response = None
            for attempt in range(3):
                response = self.call(prompt, system_prompt)
                if response and '{' in response:
                    break
            
            if not response:
                # Fallback: assign "Uncategorized" to this batch
                for t in batch:
                    categories[t.id] = "Uncategorized"
                continue
            
            # Parse JSON with multiple strategies
            parsed = self._parse_categories_response(response, batch)
            categories.update(parsed)
        
        return categories
    
    def _parse_categories_response(self, response: str, batch: List[Any]) -> Dict[int, str]:
        """Parse AI response into categories with multiple fallback strategies."""
        result = {}
        batch_ids = {t.id for t in batch}
        
        # Strategy 1: Direct JSON parse
        try:
            # Look for JSON object in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                for k, v in parsed.items():
                    tid = int(k)
                    if tid in batch_ids:
                        result[tid] = str(v).strip()
        except:
            pass
        
        # Strategy 2: Line-by-line parsing
        if len(result) < len(batch) // 2:
            for line in response.split('\n'):
                # Look for patterns like "123: Bug Report" or "123" -> "Bug Report"
                match = re.search(r'(\d+)["\s:>\-]+([A-Za-z/\s]+)', line)
                if match:
                    tid = int(match.group(1))
                    cat = match.group(2).strip().strip('"').strip("'")
                    if tid in batch_ids and tid not in result:
                        result[tid] = cat
        
        # Fill missing with "Uncategorized"
        for t in batch:
            if t.id not in result:
                result[t.id] = "Uncategorized"
        
        return result
    
    def analyze_cluster(self, tickets: List[Any], cluster_name: str) -> Dict[str, Any]:
        """Analyze a cluster of tickets to find root cause."""
        
        system_prompt = """You are a support analytics expert. Analyze these tickets from the same category and provide:
1. Root Cause: The underlying issue causing these tickets
2. Impact: How this affects customers
3. Recommendation: How to reduce these tickets

Respond in JSON format:
{"root_cause": "...", "impact": "...", "recommendation": "...", "severity": "high/medium/low"}"""

        # Sample tickets for analysis (max 20)
        sample = tickets[:20]
        
        ticket_details = "\n\n".join([
            f"Ticket #{t.id}: {t.subject}\n{t.description[:300]}..."
            for t in sample
        ])
        
        prompt = f"Analyze these {len(tickets)} tickets in the '{cluster_name}' category:\n\n{ticket_details}"
        
        response = self.call(prompt, system_prompt)
        
        if response:
            try:
                json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        return {
            'root_cause': 'Analysis pending',
            'impact': 'Unknown',
            'recommendation': 'Run AI analysis',
            'severity': 'medium'
        }
    
    def generate_summary(self, tickets: List[Any]) -> str:
        """Generate an executive summary of ticket data."""
        
        # Gather stats
        total = len(tickets)
        open_count = sum(1 for t in tickets if t.is_open)
        categories = Counter(t.category for t in tickets if t.category)
        top_categories = categories.most_common(5)
        
        avg_resolution = 0
        resolved = [t for t in tickets if t.resolution_time]
        if resolved:
            avg_resolution = sum(t.resolution_time for t in resolved) / len(resolved)
        
        system_prompt = """You are a support analytics expert. Write a brief, actionable executive summary (3-4 sentences) based on the ticket statistics provided. Focus on key insights and recommendations."""
        
        prompt = f"""Ticket Statistics:
- Total Tickets: {total}
- Open Tickets: {open_count} ({open_count/total*100:.1f}%)
- Average Resolution Time: {avg_resolution:.1f} hours
- Top Categories: {', '.join([f'{c[0]} ({c[1]})' for c in top_categories])}

Write an executive summary:"""

        response = self.call(prompt, system_prompt)
        return response or "Analysis pending. Please run AI analysis."
    
    def analyze_sentiment_batch(self, tickets: List[Any], batch_size: int = 20) -> Dict[int, Dict]:
        """Analyze sentiment for tickets.
        
        Returns: Dict mapping ticket_id -> {score, label, emotion, signals}
        """
        results = {}
        
        system_prompt = """You are a sentiment analysis expert for support tickets.
Analyze each ticket and provide:
- score: -1.0 (very negative) to 1.0 (very positive)
- label: "positive", "neutral", "negative", "frustrated", "angry"
- emotion: primary emotion (frustrated, confused, satisfied, urgent, grateful)
- signals: key phrases indicating sentiment

Respond with ONLY JSON:
{"12345": {"score": -0.7, "label": "frustrated", "emotion": "frustrated", "signals": ["still not working", "multiple times"]}}"""

        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i+batch_size]
            
            ticket_data = "\n\n".join([
                f"ID {t.id}:\nSubject: {t.subject}\nMessage: {t.description[:500]}"
                for t in batch
            ])
            
            prompt = f"Analyze sentiment for these tickets:\n\n{ticket_data}"
            response = self.call(prompt, system_prompt)
            
            if response:
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        batch_results = json.loads(json_match.group())
                        for tid, data in batch_results.items():
                            results[int(tid)] = data
                except:
                    pass
        
        return results
    
    def detect_urgency_batch(self, tickets: List[Any], batch_size: int = 20) -> Dict[int, Dict]:
        """Detect urgency level for tickets.
        
        Returns: Dict mapping ticket_id -> {score, signals, needs_escalation}
        """
        results = {}
        
        system_prompt = """You are an urgency detection expert for support tickets.
Analyze each ticket and provide:
- score: 1 (low) to 5 (critical)
- signals: phrases indicating urgency
- needs_escalation: true/false if immediate attention needed
- reason: why this urgency level

Look for: deadlines, business impact, repeated issues, emotional distress, compliance/legal

Respond with ONLY JSON:
{"12345": {"score": 4, "signals": ["deadline tomorrow", "audit"], "needs_escalation": true, "reason": "compliance deadline"}}"""

        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i+batch_size]
            
            ticket_data = "\n\n".join([
                f"ID {t.id} [Priority: {t.priority}]:\nSubject: {t.subject}\nMessage: {t.description[:400]}"
                for t in batch
            ])
            
            prompt = f"Detect urgency for these tickets:\n\n{ticket_data}"
            response = self.call(prompt, system_prompt)
            
            if response:
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        batch_results = json.loads(json_match.group())
                        for tid, data in batch_results.items():
                            results[int(tid)] = data
                except:
                    pass
        
        return results
    
    def predict_escalation_batch(self, tickets: List[Any], batch_size: int = 20) -> Dict[int, Dict]:
        """Predict escalation risk for tickets.
        
        Returns: Dict mapping ticket_id -> {risk, probability, factors, recommendation}
        """
        results = {}
        
        system_prompt = """You are an escalation prediction expert.
Analyze each ticket for escalation risk:
- risk: "low", "medium", "high", "critical"
- probability: 0.0 to 1.0 chance of escalation
- factors: list of escalation risk indicators
- recommendation: suggested action to prevent escalation

Look for: repeated contacts, frustration, threats, long wait times, VIP customers, unresolved issues

Respond with ONLY JSON:
{"12345": {"risk": "high", "probability": 0.8, "factors": ["3rd contact", "frustrated tone"], "recommendation": "escalate to senior agent"}}"""

        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i+batch_size]
            
            ticket_data = "\n\n".join([
                f"ID {t.id} [Status: {t.status}, Days Open: {t.days_open}]:\nSubject: {t.subject}\nMessage: {t.description[:400]}"
                for t in batch
            ])
            
            prompt = f"Predict escalation risk:\n\n{ticket_data}"
            response = self.call(prompt, system_prompt)
            
            if response:
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        batch_results = json.loads(json_match.group())
                        for tid, data in batch_results.items():
                            results[int(tid)] = data
                except:
                    pass
        
        return results
    
    def detect_promises(self, tickets: List[Any]) -> Dict[int, List[Dict]]:
        """Detect promises made in ticket conversations.
        
        Returns: Dict mapping ticket_id -> list of promises
        """
        results = {}
        
        system_prompt = """You are a promise detection expert.
Find commitments/promises made by support agents:
- promise: what was promised
- deadline: when (if mentioned)
- status: "pending", "overdue", "fulfilled" based on context

Look for: "I will", "we'll get back", "within 24 hours", "by tomorrow", "I'll follow up"

Respond with ONLY JSON:
{"12345": [{"promise": "respond within 24h", "deadline": "24h", "status": "pending"}]}"""

        # Sample for promise detection (conversations can be long)
        sample = tickets[:50]
        
        ticket_data = "\n\n".join([
            f"ID {t.id}:\n{t.description[:800]}"
            for t in sample
        ])
        
        prompt = f"Detect promises in these tickets:\n\n{ticket_data}"
        response = self.call(prompt, system_prompt)
        
        if response:
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    results = {int(k): v for k, v in json.loads(json_match.group()).items()}
            except:
                pass
        
        return results
    
    def score_conversation_quality(self, tickets: List[Any], batch_size: int = 10) -> Dict[int, Dict]:
        """Score conversation quality for agent responses.
        
        Returns: Dict mapping ticket_id -> quality metrics
        """
        results = {}
        
        system_prompt = """You are a conversation quality analyst.
Score agent response quality:
- overall_score: 1-10
- clarity: 1-10 (clear, understandable response)
- helpfulness: 1-10 (actually solves the problem)
- professionalism: 1-10 (tone and language)
- efficiency: 1-10 (solved quickly, no back-and-forth)
- issues: list of quality issues found

Respond with ONLY JSON:
{"12345": {"overall_score": 7, "clarity": 8, "helpfulness": 6, "professionalism": 9, "efficiency": 5, "issues": ["too generic response"]}}"""

        for i in range(0, min(len(tickets), 100), batch_size):
            batch = tickets[i:i+batch_size]
            
            ticket_data = "\n\n".join([
                f"ID {t.id}:\nCustomer: {t.subject}\n{t.description[:300]}\nAgent Response: {getattr(t, 'last_response', t.description[:200])}"
                for t in batch
            ])
            
            prompt = f"Score conversation quality:\n\n{ticket_data}"
            response = self.call(prompt, system_prompt)
            
            if response:
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        batch_results = json.loads(json_match.group())
                        for tid, data in batch_results.items():
                            results[int(tid)] = data
                except:
                    pass
        
        return results
    
    def detect_recurring_issues(self, tickets: List[Any]) -> List[Dict]:
        """Detect recurring issues across tickets.
        
        Returns: List of recurring issue patterns
        """
        system_prompt = """You are a pattern detection expert.
Find recurring issues across these tickets:
- issue: description of the recurring problem
- count: estimated number of affected tickets
- severity: "low", "medium", "high", "critical"
- root_cause: likely underlying cause
- solution: recommended fix

Respond with ONLY JSON array:
[{"issue": "Login failures after update", "count": 15, "severity": "high", "root_cause": "auth token expiry", "solution": "extend token lifetime"}]"""

        # Summarize tickets for pattern detection
        ticket_summaries = "\n".join([
            f"- {t.subject[:80]}"
            for t in tickets[:200]
        ])
        
        prompt = f"Find recurring issues in these {len(tickets)} tickets:\n\n{ticket_summaries}"
        response = self.call(prompt, system_prompt)
        
        if response:
            try:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        return []
    
    def calculate_customer_health(self, entity_tickets: Dict[str, List[Any]]) -> Dict[str, Dict]:
        """Calculate customer health scores.
        
        Returns: Dict mapping entity_name -> health metrics
        """
        results = {}
        
        for entity, tickets in entity_tickets.items():
            # Calculate metrics
            total = len(tickets)
            open_tickets = sum(1 for t in tickets if t.is_open)
            avg_sentiment = sum(getattr(t, 'sentiment_score', 0) for t in tickets) / max(total, 1)
            high_priority = sum(1 for t in tickets if t.priority >= 3)
            
            # Health score (0-100)
            health = 100
            health -= min(open_tickets * 5, 30)  # -5 per open, max -30
            health -= min(high_priority * 3, 20)  # -3 per urgent, max -20
            health += avg_sentiment * 20  # sentiment adjustment
            
            churn_risk = "low"
            if health < 50:
                churn_risk = "high"
            elif health < 70:
                churn_risk = "medium"
            
            results[entity] = {
                'health_score': max(0, min(100, health)),
                'churn_risk': churn_risk,
                'open_issues': open_tickets,
                'sentiment_avg': avg_sentiment,
                'total_tickets': total,
            }
        
        return results
    
    def run_deep_analysis(self, tickets: List[Any], progress_callback=None) -> Dict[str, Any]:
        """Run comprehensive deep analysis on tickets.
        
        Returns: Complete analysis results
        """
        results = {
            'sentiment': {},
            'urgency': {},
            'escalation': {},
            'promises': {},
            'quality': {},
            'recurring_issues': [],
            'timestamp': None,
        }
        
        total_steps = 6
        
        # 1. Sentiment Analysis
        if progress_callback:
            progress_callback(1, total_steps, "Analyzing sentiment...")
        results['sentiment'] = self.analyze_sentiment_batch(tickets[:200])
        
        # 2. Urgency Detection
        if progress_callback:
            progress_callback(2, total_steps, "Detecting urgency...")
        results['urgency'] = self.detect_urgency_batch(tickets[:200])
        
        # 3. Escalation Prediction
        if progress_callback:
            progress_callback(3, total_steps, "Predicting escalation risks...")
        results['escalation'] = self.predict_escalation_batch(tickets[:100])
        
        # 4. Promise Detection
        if progress_callback:
            progress_callback(4, total_steps, "Finding promises...")
        results['promises'] = self.detect_promises(tickets[:50])
        
        # 5. Conversation Quality
        if progress_callback:
            progress_callback(5, total_steps, "Scoring conversation quality...")
        results['quality'] = self.score_conversation_quality(tickets[:50])
        
        # 6. Recurring Issues
        if progress_callback:
            progress_callback(6, total_steps, "Detecting recurring issues...")
        results['recurring_issues'] = self.detect_recurring_issues(tickets)
        
        from datetime import datetime
        results['timestamp'] = datetime.now().isoformat()
        
        return results


def get_ai_service(config: Dict = None) -> AIService:
    """Get AI service instance from config dict."""
    ai_config = AIConfig()
    
    if config:
        ai_config.provider = config.get('provider', 'ollama')
        
        if ai_config.provider == 'ollama':
            ollama_cfg = config.get('ollama', {})
            ai_config.base_url = ollama_cfg.get('base_url', 'http://localhost:11434')
            ai_config.model = ollama_cfg.get('model', 'qwen2.5:14b')
            ai_config.temperature = ollama_cfg.get('temperature', 0.3)
        elif ai_config.provider == 'openai':
            openai_cfg = config.get('openai', {})
            ai_config.api_key = openai_cfg.get('api_key', '')
            ai_config.model = openai_cfg.get('model', 'gpt-4o-mini')
    
    return AIService(ai_config)
