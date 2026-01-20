"""
Shared UI Components
====================
Common UI elements used across all pages.
"""

import streamlit as st


def inject_beta_badge():
    """Inject the Beta badge CSS and HTML into the page."""
    st.markdown("""
    <style>
    .beta-badge {
        position: fixed;
        top: 70px;
        right: 20px;
        background: linear-gradient(135deg, #F59E0B 0%, #EF4444 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
        z-index: 1000;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    </style>
    <div class="beta-badge">🧪 Beta</div>
    """, unsafe_allow_html=True)
