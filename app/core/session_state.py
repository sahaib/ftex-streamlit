"""
Session State Manager
=====================
Centralized state management for FTEX application.
Provides automatic persistence to disk for data that must survive page refreshes.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional, List
import pickle
import json
from pathlib import Path


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

CACHE_DIR = Path(__file__).parent.parent.parent / 'data' / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cache files (matching existing file names)
TICKETS_CACHE = CACHE_DIR / 'tickets_cache.pkl'
STATE_CACHE = CACHE_DIR / 'state_cache.json'
AI_CACHE = CACHE_DIR / 'ai_analysis_cache.json'


# =============================================================================
# STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state and restore from disk cache.
    
    This function MUST be called at the start of every page.
    It ensures state is always properly initialized and restored.
    """
    
    # Default values for all state keys
    defaults = {
        # Core data
        'data_loaded': False,
        'tickets': [],
        'ticket_count': 0,
        'file_path': '',
        
        # Analysis state
        'analysis_results': {},
        'ai_enrichment': {},
        'deep_analysis': {},
        'quick_stats': {},
        
        # Filters
        'date_range': None,
        'selected_company': 'All',
        'selected_agent': 'All',
        'selected_status': 'All',
        'selected_priority': 'All',
        'selected_category': 'All',
        
        # Config
        'config': {},
        'config_loaded': False,
        
        # AI settings
        'ai_connected': False,
        'ai_provider': 'ollama',
        'ai_model': 'qwen2.5:14b',
        
        # Timestamps
        'last_analysis': None,
        'last_refresh': None,
        
        # UI state
        'current_page': 'home',
        'dark_mode': False,
    }
    
    # Set defaults for any missing keys
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
    
    # CRITICAL: Always try to restore from cache on first load
    if not st.session_state.get('_state_initialized'):
        st.session_state._state_initialized = True
        _restore_all_from_cache()


# =============================================================================
# SAVE FUNCTIONS
# =============================================================================

def save_to_cache():
    """Save all state to disk cache. Call this after any state changes."""
    _save_tickets()
    _save_state()
    _save_ai_analysis()


def _save_tickets():
    """Save tickets to pickle file."""
    try:
        tickets = st.session_state.get('tickets', [])
        if tickets:
            with open(TICKETS_CACHE, 'wb') as f:
                pickle.dump(tickets, f)
    except Exception as e:
        print(f"[StateManager] Error saving tickets: {e}")


def _save_state():
    """Save general state to JSON file."""
    try:
        state = {
            'data_loaded': st.session_state.get('data_loaded', False),
            'ticket_count': st.session_state.get('ticket_count', 0),
            'file_path': st.session_state.get('file_path', ''),
            'quick_stats': st.session_state.get('quick_stats', {}),
            'analysis_results': st.session_state.get('analysis_results', {}),
            'timestamp': datetime.now().isoformat(),
        }
        with open(STATE_CACHE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[StateManager] Error saving state: {e}")


def _save_ai_analysis():
    """Save AI analysis results to JSON file."""
    try:
        ai_enrichment = st.session_state.get('ai_enrichment', {})
        deep_analysis = st.session_state.get('deep_analysis', {})
        
        # Convert any sets to lists for JSON serialization
        def make_serializable(obj):
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(i) for i in obj]
            return obj
        
        ai_data = {
            'ai_enrichment': make_serializable(ai_enrichment),
            'deep_analysis': make_serializable(deep_analysis),
            'timestamp': datetime.now().isoformat(),
        }
        
        # Always save, even if data is empty (so we can see the file exists)
        with open(AI_CACHE, 'w') as f:
            json.dump(ai_data, f, indent=2, default=str)
        
        # Log what was saved
        enrichment_count = len(ai_enrichment.get('categories', {}))
        print(f"[StateManager] Saved AI cache: {enrichment_count} categories")
        
    except Exception as e:
        print(f"[StateManager] ERROR saving AI analysis: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# RESTORE FUNCTIONS
# =============================================================================

def _restore_all_from_cache():
    """Restore all state from disk cache."""
    _restore_tickets()
    _restore_state()
    _restore_ai_analysis()
    _apply_ai_to_tickets()  # Apply AI enrichment to tickets


def _apply_ai_to_tickets():
    """Apply AI enrichment (categories, etc.) to in-memory tickets."""
    try:
        tickets = st.session_state.get('tickets', [])
        ai_enrichment = st.session_state.get('ai_enrichment', {})
        categories = ai_enrichment.get('categories', {})
        
        if tickets and categories:
            applied = 0
            for t in tickets:
                if t.id in categories:
                    t.category = categories[t.id]
                    applied += 1
            print(f"[StateManager] Applied {applied} AI categories to tickets")
    except Exception as e:
        print(f"[StateManager] Error applying AI to tickets: {e}")


def _restore_tickets():
    """Restore tickets from pickle file."""
    try:
        if TICKETS_CACHE.exists():
            with open(TICKETS_CACHE, 'rb') as f:
                tickets = pickle.load(f)
            st.session_state.tickets = tickets
            st.session_state.ticket_count = len(tickets)
            st.session_state.data_loaded = True
            print(f"[StateManager] Restored {len(tickets)} tickets from cache")
    except Exception as e:
        print(f"[StateManager] Error restoring tickets: {e}")


def _restore_state():
    """Restore general state from JSON file."""
    try:
        if STATE_CACHE.exists():
            with open(STATE_CACHE, 'r') as f:
                state = json.load(f)
            
            st.session_state.data_loaded = state.get('data_loaded', False)
            st.session_state.file_path = state.get('file_path', '')
            st.session_state.quick_stats = state.get('quick_stats', {})
            st.session_state.analysis_results = state.get('analysis_results', {})
            print(f"[StateManager] Restored state from cache")
    except Exception as e:
        print(f"[StateManager] Error restoring state: {e}")


def _restore_ai_analysis():
    """Restore AI analysis from JSON file."""
    try:
        if AI_CACHE.exists():
            with open(AI_CACHE, 'r') as f:
                ai_data = json.load(f)
            
            st.session_state.ai_enrichment = ai_data.get('ai_enrichment', {})
            st.session_state.deep_analysis = ai_data.get('deep_analysis', {})
            
            timestamp = ai_data.get('timestamp', 'unknown')
            has_enrichment = bool(st.session_state.ai_enrichment)
            has_deep = bool(st.session_state.deep_analysis)
            print(f"[StateManager] Restored AI analysis (enrichment: {has_enrichment}, deep: {has_deep}, ts: {timestamp[:16]})")
    except Exception as e:
        print(f"[StateManager] Error restoring AI analysis: {e}")


# =============================================================================
# CLEAR FUNCTIONS
# =============================================================================

def clear_cache():
    """Clear all cache files from disk."""
    try:
        for cache_file in [TICKETS_CACHE, STATE_CACHE, AI_CACHE]:
            if cache_file.exists():
                cache_file.unlink()
        return True
    except Exception as e:
        print(f"[StateManager] Error clearing cache: {e}")
        return False


def clear_data():
    """Clear all data from session state and disk cache."""
    # Clear session state
    keys_to_clear = [
        'data_loaded', 'tickets', 'ticket_count', 'file_path',
        'ai_enrichment', 'deep_analysis', 'analysis_results',
        'quick_stats', '_state_initialized'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear disk cache
    clear_cache()


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================

def apply_filters(tickets: list) -> list:
    """Apply current filter settings to ticket list."""
    if not tickets:
        return []
    
    filtered = tickets
    
    # Company filter
    if st.session_state.get('selected_company', 'All') != 'All':
        company = st.session_state.selected_company
        filtered = [t for t in filtered if t.company_name == company]
    
    # Agent filter
    if st.session_state.get('selected_agent', 'All') != 'All':
        agent = st.session_state.selected_agent
        filtered = [t for t in filtered if t.responder_id == agent]
    
    # Status filter
    if st.session_state.get('selected_status', 'All') != 'All':
        status = st.session_state.selected_status
        filtered = [t for t in filtered if t.status_name == status]
    
    # Priority filter
    if st.session_state.get('selected_priority', 'All') != 'All':
        priority = st.session_state.selected_priority
        filtered = [t for t in filtered if t.priority_name == priority]
    
    # Category filter
    if st.session_state.get('selected_category', 'All') != 'All':
        category = st.session_state.selected_category
        filtered = [t for t in filtered if t.category == category]
    
    # Date range filter
    date_range = st.session_state.get('date_range')
    if date_range and len(date_range) == 2:
        start_str, end_str = date_range
        from datetime import datetime as dt
        try:
            start = dt.strptime(start_str, '%Y-%m-%d') if isinstance(start_str, str) else start_str
            end = dt.strptime(end_str, '%Y-%m-%d') if isinstance(end_str, str) else end_str
            filtered = [t for t in filtered 
                       if t.created_at and start <= t.created_at.replace(tzinfo=None) <= end]
        except:
            pass
    
    return filtered


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def set_data_loaded(tickets: list, analysis_results: dict = None):
    """Mark data as loaded and store results."""
    st.session_state.data_loaded = True
    st.session_state.tickets = tickets
    st.session_state.ticket_count = len(tickets)
    
    if analysis_results:
        st.session_state.analysis_results = analysis_results
    
    st.session_state.last_refresh = datetime.now()
    
    # Auto-save to disk
    save_to_cache()


def get_cache_info() -> dict:
    """Get information about current cache state."""
    info = {
        'tickets_cached': TICKETS_CACHE.exists(),
        'state_cached': STATE_CACHE.exists(),
        'ai_cached': AI_CACHE.exists(),
        'cache_dir': str(CACHE_DIR),
    }
    
    if AI_CACHE.exists():
        try:
            with open(AI_CACHE, 'r') as f:
                ai_data = json.load(f)
            info['ai_timestamp'] = ai_data.get('timestamp', 'unknown')
            info['has_enrichment'] = bool(ai_data.get('ai_enrichment'))
            info['has_deep_analysis'] = bool(ai_data.get('deep_analysis'))
        except:
            pass
    
    return info
