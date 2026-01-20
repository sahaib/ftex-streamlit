"""
Configuration Manager
=====================
YAML-based configuration system for FTEX.
Supports industry templates, custom settings, and runtime overrides.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import date
import json


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    'app': {
        'name': 'FTEX Ticket Intelligence',
        'version': '3.0.0',
        'theme': 'light',
    },
    
    'industry': {
        'name': 'General Support',
        'preset': 'general',
        'primary_entity': 'customer',  # customer, vessel, site, product
        'entity_field': 'company.name',
    },
    
    'sla': {
        'first_response_hours': 12,
        'resolution_hours': 24,
        'stale_threshold_days': 15,
        'bands': {
            'excellent': {'min': 95, 'max': 100, 'color': '#10B981'},
            'good': {'min': 90, 'max': 95, 'color': '#3B82F6'},
            'acceptable': {'min': 80, 'max': 90, 'color': '#F59E0B'},
            'needs_improvement': {'min': 70, 'max': 80, 'color': '#F97316'},
            'poor': {'min': 0, 'max': 70, 'color': '#EF4444'},
        },
        'by_priority': {
            'Urgent': {'first_response': 1, 'resolution': 4},
            'High': {'first_response': 4, 'resolution': 24},
            'Medium': {'first_response': 8, 'resolution': 72},
            'Low': {'first_response': 24, 'resolution': 168},
        },
    },
    
    'working_hours': {
        'timezone': 'UTC',
        'start_hour': 9,
        'end_hour': 18,
        'work_days': [0, 1, 2, 3, 4],  # Mon-Fri
        'holiday_calendar': 'default',
    },
    
    'categories': {
        'auto_detect': True,
        'custom': [
            {'name': 'Bug Report', 'keywords': ['bug', 'error', 'crash', 'broken', 'fails']},
            {'name': 'Feature Request', 'keywords': ['feature', 'enhancement', 'suggestion', 'please add']},
            {'name': 'Configuration', 'keywords': ['configure', 'setup', 'settings', 'config']},
            {'name': 'Activation/License', 'keywords': ['license', 'activation', 'subscription', 'product key']},
            {'name': 'Integration/Sync', 'keywords': ['sync', 'integration', 'api', 'connection']},
            {'name': 'Installation', 'keywords': ['install', 'deploy', 'upgrade', 'update']},
            {'name': 'Training', 'keywords': ['training', 'how to', 'documentation', 'guide']},
            {'name': 'Follow-up', 'keywords': ['follow up', 'following up', 'any update', 'reminder']},
            {'name': 'Acknowledgment', 'keywords': ['thank you', 'thanks', 'acknowledged']},
        ],
    },
    
    'canned_responses': {
        'detect': True,
        'patterns': {
            'acknowledgement': 'we acknowledge safe receipt',
            'follow_up': 'this is a follow up',
            'product_key': 'please apply the below product key',
            'teamviewer': 'we request you to provide us following credentials',
            'clear_cache': 'browser cache is not cleared',
            'generic_template': 'we noticed you have a query',
        },
        'threshold_phrases': 3,  # Min phrases to consider canned
    },
    
    'config_issues': {
        'detect': True,
        'types': {
            'access_issues': {
                'name': 'Accessibility Issues',
                'keywords': ['inaccessible', 'cannot access', 'not loading', 'forbidden'],
                'fault_indicators': ['issue has been resolved', 'access restored'],
            },
            'activity_issues': {
                'name': 'Activity Configuration',
                'keywords': ['unable to transfer', 'activity not available', 'not authorized'],
                'fault_indicators': ['activity has been enabled', 'activity was added'],
            },
            'data_issues': {
                'name': 'Data/Template Issues',
                'keywords': ['incorrect data', 'wrong template', 'missing field'],
                'fault_indicators': ['data has been corrected', 'template updated'],
            },
        },
    },
    
    'promise_tracking': {
        'enabled': True,
        'patterns': [
            r"(?:will|we'll) (?:get back|revert|respond) (?:within|in) 24",
            r"within (?:the next )?24\s*(?:hours?|hrs?)",
            r"get back to you (?:soon|shortly|asap)",
        ],
        'window_hours': 24,
    },
    
    'dependency_tracking': {
        'enabled': True,
        'patterns': [
            r"kindly request you to assist",
            r"need your assistance",
            r"please (?:help|assist|advise|clarify)",
            r"forwarding (?:this|the) (?:query|issue)",
        ],
    },
    
    'ai': {
        'provider': 'ollama',  # ollama, openai, anthropic
        'ollama': {
            'base_url': 'http://localhost:11434',
            'model': 'qwen2.5:14b',
            'temperature': 0.3,
        },
        'openai': {
            'model': 'gpt-4o-mini',
            'temperature': 0.3,
        },
        'features': {
            'issue_clustering': True,
            'root_cause_analysis': True,
            'sentiment_analysis': False,
            'auto_categorization': True,
        },
    },
    
    'export': {
        'excel': {
            'include_charts': True,
            'include_formulas': True,
            'password_protect': False,
        },
        'pdf': {
            'include_charts': True,
            'page_size': 'A4',
        },
    },
    
    'freshdesk': {
        'domain': '',
        'api_key': '',
        'group_id': None,
        'include_conversations': True,
        'include_notes': True,
        'days_to_fetch': 180,
    },
    
    'agent_cache': {
        'enabled': True,
        'file': '.agent_cache.json',
        'excel_file': 'agents.xlsx',
    },
}


# =============================================================================
# INDUSTRY TEMPLATES
# =============================================================================

INDUSTRY_TEMPLATES = {
    'maritime': {
        'name': 'Maritime / Shipping',
        'primary_entity': 'vessel',
        'entity_field': 'cf_vesselname',
        'categories': [
            {'name': 'Vessel Query', 'keywords': ['vessel', 'ship', 'imo', 'onboard', 'captain']},
            {'name': 'Compliance', 'keywords': ['compliance', 'audit', 'marpol', 'inspection', 'port state']},
            {'name': 'Sync/NavBox', 'keywords': ['navbox', 'sync', 'offline', 'satellite']},
            {'name': 'Logbook', 'keywords': ['logbook', 'deck log', 'engine log', 'orb']},
            {'name': 'GreenLogs', 'keywords': ['greenlogs', 'garbage log', 'ballast']},
        ],
        'config_issues': {
            'tank_issues': {
                'name': 'Tank Configuration',
                'keywords': ['tank not found', 'missing tank', 'tank not configured'],
                'fault_indicators': ['we have corrected the tank', 'tank was added'],
            },
            'ship_details': {
                'name': 'Ship Details',
                'keywords': ['incorrect ship', 'wrong imo', 'ship particulars'],
                'fault_indicators': ['ship details have been corrected'],
            },
        },
    },
    
    'it_support': {
        'name': 'IT Support / Helpdesk',
        'primary_entity': 'customer',
        'entity_field': 'company.name',
        'categories': [
            {'name': 'Hardware', 'keywords': ['hardware', 'laptop', 'monitor', 'printer', 'keyboard']},
            {'name': 'Software', 'keywords': ['software', 'application', 'install', 'update']},
            {'name': 'Network', 'keywords': ['network', 'wifi', 'vpn', 'internet', 'connection']},
            {'name': 'Account', 'keywords': ['password', 'login', 'account', 'access', 'permission']},
            {'name': 'Email', 'keywords': ['email', 'outlook', 'calendar', 'teams']},
        ],
    },
    
    'saas': {
        'name': 'SaaS Product Support',
        'primary_entity': 'customer',
        'entity_field': 'company.name',
        'categories': [
            {'name': 'Billing', 'keywords': ['billing', 'invoice', 'payment', 'subscription']},
            {'name': 'Onboarding', 'keywords': ['onboarding', 'getting started', 'setup', 'first time']},
            {'name': 'API/Integration', 'keywords': ['api', 'webhook', 'integration', 'connect']},
            {'name': 'Data Export', 'keywords': ['export', 'download', 'backup', 'migrate']},
            {'name': 'Performance', 'keywords': ['slow', 'performance', 'loading', 'timeout']},
        ],
    },
    
    'ecommerce': {
        'name': 'E-Commerce Support',
        'primary_entity': 'customer',
        'entity_field': 'company.name',
        'categories': [
            {'name': 'Order Issues', 'keywords': ['order', 'tracking', 'delivery', 'shipping']},
            {'name': 'Returns', 'keywords': ['return', 'refund', 'exchange', 'damaged']},
            {'name': 'Payment', 'keywords': ['payment', 'checkout', 'card', 'transaction']},
            {'name': 'Product', 'keywords': ['product', 'availability', 'stock', 'size']},
            {'name': 'Account', 'keywords': ['account', 'login', 'password', 'profile']},
        ],
    },
}


# =============================================================================
# HOLIDAY CALENDARS
# =============================================================================

HOLIDAY_CALENDARS = {
    'india': {
        'name': 'India',
        'holidays': {
            '2025-01-01': 'New Year',
            '2025-01-26': 'Republic Day',
            '2025-03-14': 'Holi',
            '2025-04-18': 'Good Friday',
            '2025-05-01': 'Maharashtra Day',
            '2025-08-15': 'Independence Day',
            '2025-10-02': 'Gandhi Jayanti',
            '2025-10-20': 'Diwali',
            '2025-12-25': 'Christmas',
            '2026-01-01': 'New Year',
            '2026-01-26': 'Republic Day',
        },
    },
    'us': {
        'name': 'United States',
        'holidays': {
            '2025-01-01': 'New Year',
            '2025-01-20': 'MLK Day',
            '2025-02-17': 'Presidents Day',
            '2025-05-26': 'Memorial Day',
            '2025-07-04': 'Independence Day',
            '2025-09-01': 'Labor Day',
            '2025-11-27': 'Thanksgiving',
            '2025-12-25': 'Christmas',
        },
    },
    'uk': {
        'name': 'United Kingdom',
        'holidays': {
            '2025-01-01': 'New Year',
            '2025-04-18': 'Good Friday',
            '2025-04-21': 'Easter Monday',
            '2025-05-05': 'May Day',
            '2025-05-26': 'Spring Bank Holiday',
            '2025-08-25': 'Summer Bank Holiday',
            '2025-12-25': 'Christmas',
            '2025-12-26': 'Boxing Day',
        },
    },
    'singapore': {
        'name': 'Singapore',
        'holidays': {
            '2025-01-01': 'New Year',
            '2025-01-29': 'Chinese New Year',
            '2025-01-30': 'Chinese New Year',
            '2025-04-18': 'Good Friday',
            '2025-05-01': 'Labour Day',
            '2025-05-12': 'Vesak Day',
            '2025-08-09': 'National Day',
            '2025-12-25': 'Christmas',
        },
    },
    'norway': {
        'name': 'Norway',
        'holidays': {
            '2025-01-01': 'New Year',
            '2025-04-17': 'Maundy Thursday',
            '2025-04-18': 'Good Friday',
            '2025-04-21': 'Easter Monday',
            '2025-05-01': 'Labour Day',
            '2025-05-17': 'Constitution Day',
            '2025-05-29': 'Ascension Day',
            '2025-06-09': 'Whit Monday',
            '2025-12-25': 'Christmas',
            '2025-12-26': 'Boxing Day',
        },
    },
}


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

class ConfigManager:
    """Manages application configuration with YAML support."""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / 'config'
        self.config = DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from files."""
        # Load user config if exists
        user_config_path = self.config_dir / 'user' / 'config.yaml'
        if user_config_path.exists():
            with open(user_config_path) as f:
                user_config = yaml.safe_load(f)
                self._merge_config(user_config)
        
        # Load from environment
        self._load_env_overrides()
    
    def _merge_config(self, override: dict, base: dict = None):
        """Deep merge configuration dictionaries."""
        if base is None:
            base = self.config
        
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(value, base[key])
            else:
                base[key] = value
    
    def _load_env_overrides(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'FRESHDESK_DOMAIN': ('freshdesk', 'domain'),
            'FRESHDESK_API_KEY': ('freshdesk', 'api_key'),
            'FRESHDESK_GROUP_ID': ('freshdesk', 'group_id'),
            'OLLAMA_URL': ('ai', 'ollama', 'base_url'),
            'OLLAMA_MODEL': ('ai', 'ollama', 'model'),
            'OPENAI_API_KEY': ('ai', 'openai', 'api_key'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(config_path, value)
    
    def _set_nested(self, path: tuple, value: Any):
        """Set a nested configuration value."""
        d = self.config
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value
    
    def get(self, *path, default=None) -> Any:
        """Get a configuration value by path."""
        d = self.config
        try:
            for key in path:
                d = d[key]
            return d
        except (KeyError, TypeError):
            return default
    
    def set(self, *path_and_value):
        """Set a configuration value."""
        *path, value = path_and_value
        self._set_nested(tuple(path), value)
    
    def apply_template(self, template_name: str):
        """Apply an industry template."""
        if template_name in INDUSTRY_TEMPLATES:
            template = INDUSTRY_TEMPLATES[template_name]
            self.config['industry']['name'] = template['name']
            self.config['industry']['preset'] = template_name
            self.config['industry']['primary_entity'] = template['primary_entity']
            self.config['industry']['entity_field'] = template['entity_field']
            
            if 'categories' in template:
                self.config['categories']['custom'] = template['categories']
            
            if 'config_issues' in template:
                self.config['config_issues']['types'].update(template['config_issues'])
    
    def get_holidays(self, calendar_name: str = None) -> Dict[str, str]:
        """Get holidays for a calendar."""
        calendar_name = calendar_name or self.config['working_hours']['holiday_calendar']
        if calendar_name in HOLIDAY_CALENDARS:
            return HOLIDAY_CALENDARS[calendar_name]['holidays']
        return {}
    
    def is_holiday(self, d: date) -> tuple:
        """Check if date is a holiday."""
        holidays = self.get_holidays()
        date_str = d.strftime('%Y-%m-%d')
        if date_str in holidays:
            return True, holidays[date_str]
        return False, ''
    
    def is_working_day(self, d: date) -> bool:
        """Check if date is a working day."""
        # Check weekend
        if d.weekday() not in self.config['working_hours']['work_days']:
            return False
        # Check holiday
        is_hol, _ = self.is_holiday(d)
        return not is_hol
    
    def save(self, path: str = None):
        """Save current configuration to file."""
        save_path = Path(path) if path else self.config_dir / 'user' / 'config.yaml'
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
    
    def to_dict(self) -> dict:
        """Return configuration as dictionary."""
        return self.config.copy()
    
    @classmethod
    def get_template_names(cls) -> List[str]:
        """Get list of available industry templates."""
        return list(INDUSTRY_TEMPLATES.keys())
    
    @classmethod
    def get_calendar_names(cls) -> List[str]:
        """Get list of available holiday calendars."""
        return list(HOLIDAY_CALENDARS.keys())


# Singleton instance
_config_manager = None

def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
