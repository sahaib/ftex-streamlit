#!/usr/bin/env python3
"""
FTEX Ticket Intelligence Platform
=================================
Open-source, self-hosted ticket analytics with AI-powered insights.

Features:
- 🎯 Comprehensive ticket analysis (27+ metric categories)
- 🤖 AI-powered issue detection (Ollama/OpenAI)
- 📊 Interactive dashboards with Plotly
- ⚙️ Fully configurable for any industry
- 📥 Professional Excel/PDF exports

Run:
    streamlit run app/main.py
"""

import streamlit as st
import os
import sys
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import core modules
from core.config_manager import ConfigManager
from core.data_loader import DataLoader
from core.session_state import init_session_state

# Page config must be first Streamlit command
st.set_page_config(
    page_title="FTEX Ticket Intelligence",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/sahaib/FTEX',
        'Report a bug': 'https://github.com/sahaib/FTEX/issues',
        'About': '# FTEX Ticket Intelligence Platform\nOpen-source ticket analytics'
    }
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Modern color scheme */
    :root {
        --primary: #1F4E79;
        --primary-light: #2E75B6;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --info: #3B82F6;
        --bg-dark: #1E1E2E;
        --bg-light: #F8FAFC;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom header */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1F4E79, #2E75B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 700;
        line-height: 1;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    .kpi-delta {
        font-size: 0.8rem;
        margin-top: 0.3rem;
    }
    
    .kpi-delta.positive { color: #10B981; }
    .kpi-delta.negative { color: #EF4444; }
    
    /* Beta Badge */
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
    
    /* Hero Section */
    .hero-section {
        background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 50%, #4A90C2 100%);
        border-radius: 16px;
        padding: 2.5rem;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(31, 78, 121, 0.3);
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-bottom: 1.5rem;
    }
    
    /* Feature Cards */
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #E2E8F0;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 0.75rem;
    }
    
    .feature-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1F4E79;
        margin-bottom: 0.5rem;
    }
    
    .feature-desc {
        font-size: 0.9rem;
        color: #64748B;
        line-height: 1.5;
    }
    
    /* Status badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-success { background: #D1FAE5; color: #065F46; }
    .badge-warning { background: #FEF3C7; color: #92400E; }
    .badge-danger { background: #FEE2E2; color: #991B1B; }
    .badge-info { background: #DBEAFE; color: #1E40AF; }
    
    /* Data tables */
    .dataframe {
        font-size: 0.85rem !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1E1E2E 0%, #2D2D44 100%);
    }
    
    /* Cards */
    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9;
        border-radius: 8px;
        padding: 8px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1F4E79;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Initialize session state
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/sahaib/FTEX/main/docs/logo.png", width=200)
        st.markdown("---")
        
        # Data source selection
        st.subheader("📁 Data Source")
        
        data_source = st.radio(
            "Select source",
            ["Upload File", "Connect API", "Sample Data"],
            key="data_source",
            label_visibility="collapsed"
        )
        
        if data_source == "Upload File":
            st.caption("💡 For files >1GB, use 'Load from Path' below")
            uploaded_file = st.file_uploader(
                "Upload tickets.json",
                type=['json', 'csv'],
                help="Upload your ticket export file (max 2GB)"
            )
            if uploaded_file:
                st.session_state.uploaded_file = uploaded_file
                st.session_state.file_path = None  # Clear path if upload used
            
            # Alternative: load from file path for very large files
            with st.expander("📂 Load from Path (for 1GB+ files)"):
                file_path = st.text_input(
                    "File Path",
                    value=st.session_state.get('file_path', ''),
                    placeholder="/path/to/tickets.json",
                    help="Enter full path to a local JSON file",
                    key="file_path_input"
                )
                if file_path:
                    from pathlib import Path
                    if Path(file_path).exists():
                        st.session_state.file_path = file_path
                        file_size = Path(file_path).stat().st_size / (1024**3)
                        st.success(f"✓ File found ({file_size:.2f} GB)")
                    else:
                        st.error("File not found")
            
            # Show Process button if file available
            if st.session_state.get('uploaded_file') or st.session_state.get('file_path'):
                if st.button("🚀 Process Data", type="primary", use_container_width=True):
                    with st.spinner("Loading and processing tickets..."):
                        try:
                            loader = DataLoader()
                            
                            # Create progress bar
                            progress_bar = st.progress(0, text="Loading...")
                            
                            def update_progress(current, total):
                                if total > 0:
                                    pct = min(current / total, 1.0)
                                    progress_bar.progress(pct, text=f"Processing... {pct*100:.0f}%")
                            
                            # Load from path or uploaded file
                            if st.session_state.get('file_path'):
                                tickets = loader.load_json(st.session_state.file_path, progress_callback=update_progress)
                            else:
                                tickets = loader.load_json(st.session_state.uploaded_file, progress_callback=update_progress)
                            
                            # Store in session
                            st.session_state.tickets = tickets
                            st.session_state.data_loaded = True
                            st.session_state.ticket_count = len(tickets)
                            st.session_state.analysis_results = loader.get_summary()
                            st.session_state.quick_stats = {
                                'total': len(tickets),
                                'open': sum(1 for t in tickets if t.is_open),
                                'sla_rate': loader.get_summary().get('sla_compliance', 0),
                            }
                            
                            # Save to disk cache for persistence across refreshes
                            from core.session_state import save_to_cache
                            save_to_cache()
                            
                            progress_bar.progress(1.0, text="Complete!")
                            st.success(f"✅ Loaded {len(tickets):,} tickets!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error loading data: {e}")
        
        elif data_source == "Connect API":
            with st.expander("API Configuration", expanded=True):
                api_domain = st.text_input("Domain", placeholder="your-company", key="api_domain",
                                          help="Your Freshdesk subdomain (e.g., 'your-company' for your-company.freshdesk.com)")
                api_key = st.text_input("API Key", type="password", key="api_key",
                                       help="Your Freshdesk API key (found in Profile Settings)")
                group_id = st.number_input("Group ID (optional)", value=0, key="group_id",
                                          help="Filter tickets by group ID (0 = all groups)")
                days_back = st.slider("Days to fetch", 30, 365, 180, key="days_back",
                                     help="Fetch tickets from the last N days")
                
                if st.button("🔗 Connect & Fetch", type="primary", use_container_width=True):
                    if not api_domain or not api_key:
                        st.error("Please enter both domain and API key")
                    else:
                        with st.spinner("Connecting to Freshdesk API..."):
                            try:
                                import requests
                                from datetime import datetime, timedelta
                                
                                base_url = f"https://{api_domain}.freshdesk.com/api/v2"
                                auth = (api_key, 'X')
                                
                                # Test connection
                                test_resp = requests.get(f"{base_url}/tickets?per_page=1", auth=auth, timeout=10)
                                
                                if test_resp.status_code == 401:
                                    st.error("❌ Invalid API key")
                                elif test_resp.status_code != 200:
                                    st.error(f"❌ API error: {test_resp.status_code}")
                                else:
                                    st.success("✅ Connected to Freshdesk!")
                                    
                                    # Fetch tickets
                                    progress_bar = st.progress(0, text="Fetching tickets...")
                                    all_tickets = []
                                    page = 1
                                    
                                    # Build query params
                                    since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%dT00:00:00Z')
                                    params = {
                                        'per_page': 100,
                                        'updated_since': since_date,
                                        'include': 'stats,company'
                                    }
                                    if group_id > 0:
                                        params['group_id'] = group_id
                                    
                                    while True:
                                        params['page'] = page
                                        resp = requests.get(f"{base_url}/tickets", auth=auth, params=params, timeout=30)
                                        
                                        if resp.status_code != 200:
                                            break
                                        
                                        tickets_batch = resp.json()
                                        if not tickets_batch:
                                            break
                                        
                                        all_tickets.extend(tickets_batch)
                                        progress_bar.progress(min(page/20, 0.9), text=f"Fetched {len(all_tickets)} tickets...")
                                        page += 1
                                        
                                        # Respect rate limits
                                        if page > 50:  # Safety limit
                                            break
                                    
                                    if all_tickets:
                                        # Convert to Ticket objects
                                        loader = DataLoader()
                                        loader.raw_data = all_tickets
                                        entity_config = {'entity_field': 'company.name'}
                                        from core.data_loader import Ticket
                                        tickets = [Ticket.from_dict(t, entity_config) for t in all_tickets]
                                        
                                        # Store in session
                                        st.session_state.tickets = tickets
                                        st.session_state.data_loaded = True
                                        st.session_state.ticket_count = len(tickets)
                                        st.session_state.quick_stats = {
                                            'total': len(tickets),
                                            'open': sum(1 for t in tickets if t.is_open),
                                            'sla_rate': 0,  # Calculate later
                                        }
                                        
                                        # Save to disk cache for persistence
                                        from core.session_state import save_to_cache
                                        save_to_cache()
                                        
                                        progress_bar.progress(1.0, text="Complete!")
                                        st.success(f"✅ Loaded {len(tickets):,} tickets from Freshdesk!")
                                        st.rerun()
                                    else:
                                        st.warning("No tickets found in the specified date range")
                                        
                            except requests.exceptions.Timeout:
                                st.error("❌ Connection timeout - please try again")
                            except requests.exceptions.ConnectionError:
                                st.error("❌ Cannot connect to Freshdesk - check your domain")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
        
        else:  # Sample Data
            if st.button("📥 Load Sample Data", use_container_width=True):
                st.session_state.use_sample_data = True
                st.success("Sample data loaded!")
        
        st.markdown("---")
        
        # Quick stats if data loaded
        if st.session_state.get('data_loaded'):
            st.subheader("📊 Quick Stats")
            stats = st.session_state.get('quick_stats', {})
            st.metric("Total Tickets", f"{stats.get('total', 0):,}")
            st.metric("Open Tickets", stats.get('open', 0))
            st.metric("SLA Compliance", f"{stats.get('sla_rate', 0):.1f}%")
            
            # Show cache status
            if st.session_state.get('last_refresh'):
                st.caption(f"📦 Cached: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M')}")
            
            # Clear data button
            if st.button("🗑️ Clear Data", use_container_width=True):
                from core.session_state import clear_data
                clear_data()
                st.rerun()
        
        st.markdown("---")
        
        # Settings link
        st.page_link("pages/6_⚙️_Settings.py", label="⚙️ Settings", icon="⚙️")
        
        # Footer
        st.markdown("---")
        st.caption("FTEX v3.1 | Open Source")
        st.caption("[GitHub](https://github.com/sahaib/ftex-streamlit) | [Docs](https://ftex.readthedocs.io)")
    
    # Main content
    # Beta Badge (always visible)
    st.markdown('<div class="beta-badge">🧪 Beta</div>', unsafe_allow_html=True)
    
    # Check if data is loaded
    if not st.session_state.get('data_loaded'):
        # Hero Section
        st.markdown("""
        <div class="hero-section">
            <div class="hero-title">🎫 FTEX Ticket Intelligence</div>
            <div class="hero-subtitle">Transform your support tickets into actionable insights with AI-powered analytics</div>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    ✨ 27+ Analytics Views
                </span>
                <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    🤖 AI-Powered Insights
                </span>
                <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    🔒 Self-Hosted & Private
                </span>
                <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    📊 Export to Excel/PDF
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature Cards
        st.markdown("### ✨ What You'll Get")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <div class="feature-title">Smart Dashboard</div>
                <div class="feature-desc">Real-time KPIs, trend analysis, and SLA tracking in one view</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">AI Analysis</div>
                <div class="feature-desc">Automatic categorization, sentiment detection, and issue clustering</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">👥</div>
                <div class="feature-title">Agent Insights</div>
                <div class="feature-desc">Performance metrics, response quality, and workload balance</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🏢</div>
                <div class="feature-title">Entity Health</div>
                <div class="feature-desc">Customer satisfaction, churn risk, and account health scores</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Get Started
        st.markdown("### 🚀 Get Started in 3 Steps")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            #### Step 1: Load Data
            Upload your `tickets.json` export or connect directly to your Freshdesk API via the sidebar.
            
            📁 Supports files up to **2GB**
            """)
        
        with col2:
            st.markdown("""
            #### Step 2: Configure AI
            Set up Ollama (local) or connect OpenAI/Anthropic for AI-powered insights.
            
            🔒 Your data stays **private**
            """)
        
        with col3:
            st.markdown("""
            #### Step 3: Explore
            Navigate to Dashboard, AI Analysis, Agents, or Entities to uncover insights.
            
            📊 Export reports anytime
            """)
        
        st.markdown("---")
        
        # Demo mode
        st.info("👆 Use the sidebar to upload data or load sample data to get started!")
        
    else:
        # Data is loaded - show dashboard preview
        st.markdown("---")
        
        # Load analysis results
        results = st.session_state.get('analysis_results', {})
        
        # KPI Row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Tickets",
                f"{results.get('total_tickets', 0):,}",
                delta=None
            )
        
        with col2:
            sla_rate = results.get('sla_compliance', 0)
            st.metric(
                "SLA Compliance",
                f"{sla_rate:.1f}%",
                delta=f"{sla_rate - 90:.1f}%" if sla_rate else None,
                delta_color="normal"
            )
        
        with col3:
            st.metric(
                "Open Tickets",
                results.get('open_tickets', 0),
                delta=None
            )
        
        with col4:
            st.metric(
                "Stale (>15d)",
                results.get('stale_tickets', 0),
                delta=None,
                delta_color="inverse"
            )
        
        with col5:
            st.metric(
                "AI Issues",
                results.get('ai_issues', 0),
                delta=None
            )
        
        st.markdown("---")
        
        # Navigation cards
        st.subheader("📍 Quick Navigation")
        
        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
        
        with nav_col1:
            if st.button("📊 Dashboard", use_container_width=True, type="primary"):
                st.switch_page("pages/1_📊_Dashboard.py")
        
        with nav_col2:
            if st.button("🧠 AI Analysis", use_container_width=True):
                st.switch_page("pages/2_🧠_AI_Analysis.py")
        
        with nav_col3:
            if st.button("📈 SLA Metrics", use_container_width=True):
                st.switch_page("pages/3_📈_SLA_Metrics.py")
        
        with nav_col4:
            if st.button("👤 Agents", use_container_width=True):
                st.switch_page("pages/5_👤_Agents.py")
        
        st.markdown("---")
        
        # Recent activity or alerts
        st.subheader("🚨 Attention Required")
        
        alerts = results.get('alerts', [])
        if alerts:
            for alert in alerts[:5]:
                severity = alert.get('severity', 'info')
                icon = {'critical': '🔴', 'warning': '🟠', 'info': '🔵'}.get(severity, '⚪')
                st.warning(f"{icon} {alert.get('message', 'Unknown alert')}")
        else:
            st.success("✅ No critical issues detected!")


if __name__ == "__main__":
    main()
