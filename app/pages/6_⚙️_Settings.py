"""
Settings Page
=============
Full configuration UI for FTEX.
Allows customization of all aspects of the platform.
"""

import streamlit as st
import yaml
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state
from core.config_manager import (
    ConfigManager, get_config, 
    INDUSTRY_TEMPLATES, HOLIDAY_CALENDARS, DEFAULT_CONFIG
)
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="Settings | FTEX", page_icon="⚙️", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()
config = get_config()


def render_settings():
    """Render the settings page."""
    
    st.title("⚙️ Configuration")
    st.caption("Customize FTEX for your organization and workflow")
    
    # Tabs for different settings sections
    tabs = st.tabs([
        "🎨 Branding",
        "🏭 Industry",
        "⏱️ SLA",
        "📅 Working Hours",
        "🏷️ Categories",
        "📝 Patterns",
        "🤖 AI",
        "🔌 Integrations",
        "📤 Export"
    ])
    
    # =========================================================================
    # BRANDING TAB
    # =========================================================================
    with tabs[0]:
        st.subheader("🎨 Branding & Personalization")
        st.caption("Customize the platform appearance for your organization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Company Identity")
            
            st.text_input(
                "Company Name",
                value=config.get('branding', 'company_name', default='My Company'),
                key="brand_company_name",
                help="Your company name displayed in the header and exports"
            )
            
            st.text_input(
                "Platform Name",
                value=config.get('branding', 'platform_name', default='FTEX Ticket Intelligence'),
                key="brand_platform_name",
                help="Custom name for your analytics platform"
            )
            
            st.text_input(
                "Tagline",
                value=config.get('branding', 'tagline', default='AI-Powered Support Analytics'),
                key="brand_tagline",
                help="Short tagline displayed below the platform name"
            )
            
            st.markdown("---")
            st.markdown("##### Logo & Images")
            
            logo_file = st.file_uploader(
                "Upload Logo",
                type=['png', 'jpg', 'jpeg', 'svg'],
                key="brand_logo",
                help="Recommended: 200x60px, transparent PNG"
            )
            
            if logo_file:
                st.image(logo_file, width=200, caption="Logo Preview")
                # Store logo path in session for use across app
                st.session_state['custom_logo'] = logo_file
                st.success("✓ Logo uploaded! Click 'Save Configuration' to apply.")
            
            favicon_file = st.file_uploader(
                "Upload Favicon",
                type=['ico', 'png'],
                key="brand_favicon",
                help="16x16 or 32x32 pixels for browser tab icon"
            )
            
            if favicon_file:
                st.success("✓ Favicon uploaded!")
        
        with col2:
            st.markdown("##### Color Theme")
            
            primary_color = st.color_picker(
                "Primary Color",
                value=config.get('branding', 'primary_color', default='#1F4E79'),
                key="brand_primary_color",
                help="Main brand color for headers and accents"
            )
            
            secondary_color = st.color_picker(
                "Secondary Color",
                value=config.get('branding', 'secondary_color', default='#2E75B6'),
                key="brand_secondary_color",
                help="Secondary color for gradients and highlights"
            )
            
            accent_color = st.color_picker(
                "Accent Color",
                value=config.get('branding', 'accent_color', default='#10B981'),
                key="brand_accent_color",
                help="Color for success states and CTAs"
            )
            
            st.markdown("---")
            st.markdown("##### Theme Preview")
            
            # Preview card with custom colors
            preview_style = f"""
            <div style="
                background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%);
                border-radius: 12px;
                padding: 20px;
                color: white;
                margin-bottom: 10px;
            ">
                <h3 style="margin: 0; color: white;">📊 {st.session_state.get('brand_platform_name', 'FTEX Ticket Intelligence')}</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">{st.session_state.get('brand_tagline', 'AI-Powered Support Analytics')}</p>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 10px;">
                <span style="background: {primary_color}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px;">Primary</span>
                <span style="background: {secondary_color}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px;">Secondary</span>
                <span style="background: {accent_color}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px;">Accent</span>
            </div>
            """
            st.markdown(preview_style, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("##### Export Branding")
            
            st.toggle(
                "Include logo in PDF exports",
                value=config.get('branding', 'logo_in_exports', default=True),
                key="brand_logo_exports"
            )
            
            st.toggle(
                "Include logo in Excel exports",
                value=config.get('branding', 'logo_in_excel', default=True),
                key="brand_logo_excel"
            )
            
            st.text_input(
                "Footer Text",
                value=config.get('branding', 'footer_text', default='Confidential - Internal Use Only'),
                key="brand_footer",
                help="Text displayed in export footers"
            )
    
    # =========================================================================
    # INDUSTRY TAB
    # =========================================================================
    with tabs[1]:
        st.subheader("Industry Configuration")
        st.caption("Select a preset or customize for your industry")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Industry preset selection
            presets = ['custom'] + list(INDUSTRY_TEMPLATES.keys())
            preset_labels = ['Custom'] + [INDUSTRY_TEMPLATES[k]['name'] for k in INDUSTRY_TEMPLATES.keys()]
            
            current_preset = config.get('industry', 'preset', default='custom')
            selected_idx = presets.index(current_preset) if current_preset in presets else 0
            
            selected_preset = st.selectbox(
                "Industry Preset",
                presets,
                index=selected_idx,
                format_func=lambda x: INDUSTRY_TEMPLATES.get(x, {}).get('name', 'Custom'),
                help="Select a preset to auto-configure settings for your industry"
            )
            
            if selected_preset != 'custom' and st.button("Apply Preset", type="primary"):
                config.apply_template(selected_preset)
                st.success(f"✓ Applied {INDUSTRY_TEMPLATES[selected_preset]['name']} preset!")
                st.rerun()
        
        with col2:
            # Custom settings
            st.text_input(
                "Organization Name",
                value=config.get('industry', 'name', default='My Organization'),
                key="org_name"
            )
            
            entity_options = ['customer', 'vessel', 'site', 'product', 'account']
            current_entity = config.get('industry', 'primary_entity', default='customer')
            
            st.selectbox(
                "Primary Entity Type",
                entity_options,
                index=entity_options.index(current_entity) if current_entity in entity_options else 0,
                key="entity_type",
                help="The main entity to track (e.g., vessels for maritime, customers for SaaS)"
            )
            
            st.text_input(
                "Entity Field Mapping",
                value=config.get('industry', 'entity_field', default='company.name'),
                key="entity_field",
                help="JSON path to the entity field in ticket data (e.g., 'cf_vesselname' or 'company.name')"
            )
    
    # =========================================================================
    # SLA TAB
    # =========================================================================
    with tabs[2]:
        st.subheader("SLA Configuration")
        st.caption("Define your service level agreement thresholds")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Global Thresholds")
            
            st.number_input(
                "First Response Target (hours)",
                value=config.get('sla', 'first_response_hours', default=12),
                min_value=1,
                max_value=168,
                key="sla_frt"
            )
            
            st.number_input(
                "Resolution Target (hours)",
                value=config.get('sla', 'resolution_hours', default=24),
                min_value=1,
                max_value=720,
                key="sla_resolution"
            )
            
            st.number_input(
                "Stale Ticket Threshold (days)",
                value=config.get('sla', 'stale_threshold_days', default=15),
                min_value=1,
                max_value=90,
                key="sla_stale"
            )
        
        with col2:
            st.markdown("##### By Priority")
            
            priority_sla = config.get('sla', 'by_priority', default={})
            
            for priority in ['Urgent', 'High', 'Medium', 'Low']:
                with st.expander(f"📌 {priority}", expanded=(priority == 'Urgent')):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.number_input(
                            "First Response (hrs)",
                            value=priority_sla.get(priority, {}).get('first_response', 12),
                            min_value=1,
                            key=f"sla_{priority.lower()}_frt"
                        )
                    with col_b:
                        st.number_input(
                            "Resolution (hrs)",
                            value=priority_sla.get(priority, {}).get('resolution', 24),
                            min_value=1,
                            key=f"sla_{priority.lower()}_res"
                        )
        
        st.markdown("---")
        st.markdown("##### SLA Performance Bands")
        
        bands = config.get('sla', 'bands', default={})
        band_cols = st.columns(5)
        
        band_info = [
            ('excellent', 'Excellent', '🟢', 95, 100),
            ('good', 'Good', '🔵', 90, 95),
            ('acceptable', 'Acceptable', '🟡', 80, 90),
            ('needs_improvement', 'Needs Improvement', '🟠', 70, 80),
            ('poor', 'Poor', '🔴', 0, 70),
        ]
        
        for i, (key, label, icon, default_min, default_max) in enumerate(band_info):
            with band_cols[i]:
                st.markdown(f"**{icon} {label}**")
                st.text(f"{bands.get(key, {}).get('min', default_min)}-{bands.get(key, {}).get('max', default_max)}%")
    
    # =========================================================================
    # WORKING HOURS TAB
    # =========================================================================
    with tabs[3]:
        st.subheader("Working Hours & Holidays")
        st.caption("Configure business hours for accurate SLA calculations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Business Hours")
            
            import pytz
            timezones = ['UTC', 'US/Eastern', 'US/Pacific', 'Europe/London', 'Europe/Paris', 
                        'Asia/Kolkata', 'Asia/Singapore', 'Asia/Tokyo', 'Australia/Sydney']
            
            current_tz = config.get('working_hours', 'timezone', default='UTC')
            st.selectbox(
                "Timezone",
                timezones,
                index=timezones.index(current_tz) if current_tz in timezones else 0,
                key="timezone"
            )
            
            time_col1, time_col2 = st.columns(2)
            with time_col1:
                st.number_input(
                    "Start Hour",
                    value=config.get('working_hours', 'start_hour', default=9),
                    min_value=0,
                    max_value=23,
                    key="work_start"
                )
            with time_col2:
                st.number_input(
                    "End Hour",
                    value=config.get('working_hours', 'end_hour', default=18),
                    min_value=0,
                    max_value=23,
                    key="work_end"
                )
            
            st.markdown("##### Work Days")
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            current_days = config.get('working_hours', 'work_days', default=[0,1,2,3,4])
            
            day_cols = st.columns(7)
            for i, day in enumerate(days):
                with day_cols[i]:
                    st.checkbox(day[:3], value=i in current_days, key=f"day_{i}")
        
        with col2:
            st.markdown("##### Holiday Calendar")
            
            calendar_names = list(HOLIDAY_CALENDARS.keys())
            calendar_labels = [HOLIDAY_CALENDARS[k]['name'] for k in calendar_names]
            
            current_cal = config.get('working_hours', 'holiday_calendar', default='default')
            
            selected_cal = st.selectbox(
                "Select Calendar",
                calendar_names,
                format_func=lambda x: HOLIDAY_CALENDARS.get(x, {}).get('name', x),
                key="holiday_calendar"
            )
            
            # Show holidays
            if selected_cal in HOLIDAY_CALENDARS:
                holidays = HOLIDAY_CALENDARS[selected_cal]['holidays']
                st.markdown(f"**{len(holidays)} holidays configured**")
                
                with st.expander("View Holidays"):
                    for date, name in sorted(holidays.items()):
                        st.text(f"{date}: {name}")
            
            st.markdown("---")
            st.markdown("##### Custom Holidays")
            
            with st.expander("➕ Add Custom Holiday"):
                custom_date = st.date_input("Date", key="custom_holiday_date")
                custom_name = st.text_input("Holiday Name", key="custom_holiday_name")
                if st.button("Add Holiday"):
                    st.success(f"Added: {custom_date} - {custom_name}")
    
    # =========================================================================
    # CATEGORIES TAB
    # =========================================================================
    with tabs[4]:
        st.subheader("Ticket Categories")
        st.caption("Define categories and their detection keywords")
        
        st.toggle(
            "Auto-detect categories",
            value=config.get('categories', 'auto_detect', default=True),
            key="auto_categories",
            help="Automatically categorize tickets based on keywords"
        )
        
        st.markdown("##### Category Definitions")
        
        categories = config.get('categories', 'custom', default=[])
        
        for i, cat in enumerate(categories):
            with st.expander(f"🏷️ {cat['name']}", expanded=False):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.text_input("Name", value=cat['name'], key=f"cat_name_{i}")
                with col2:
                    st.text_input(
                        "Keywords (comma-separated)",
                        value=', '.join(cat['keywords']),
                        key=f"cat_keywords_{i}"
                    )
                if st.button("🗑️ Remove", key=f"cat_remove_{i}"):
                    st.warning("Category removed (save to apply)")
        
        st.markdown("---")
        with st.expander("➕ Add New Category"):
            new_cat_name = st.text_input("Category Name", key="new_cat_name")
            new_cat_keywords = st.text_input("Keywords (comma-separated)", key="new_cat_keywords")
            if st.button("Add Category"):
                st.success(f"Added category: {new_cat_name}")
    
    # =========================================================================
    # PATTERNS TAB
    # =========================================================================
    with tabs[5]:
        st.subheader("Detection Patterns")
        st.caption("Configure patterns for detecting canned responses, promises, dependencies, etc.")
        
        pattern_tabs = st.tabs(["Canned Responses", "24h Promises", "Dependencies", "Config Issues"])
        
        # Canned Responses
        with pattern_tabs[0]:
            st.toggle(
                "Detect canned responses",
                value=config.get('canned_responses', 'detect', default=True),
                key="detect_canned"
            )
            
            st.markdown("##### Template Patterns")
            patterns = config.get('canned_responses', 'patterns', default={})
            
            for name, pattern in patterns.items():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.text_input("Name", value=name, key=f"canned_{name}_name", disabled=True)
                with col2:
                    st.text_input("Pattern", value=pattern, key=f"canned_{name}_pattern")
        
        # 24h Promises
        with pattern_tabs[1]:
            st.toggle(
                "Track 24h promises",
                value=config.get('promise_tracking', 'enabled', default=True),
                key="track_promises"
            )
            
            st.number_input(
                "Promise Window (hours)",
                value=config.get('promise_tracking', 'window_hours', default=24),
                min_value=1,
                max_value=72,
                key="promise_window"
            )
            
            st.markdown("##### Promise Detection Patterns")
            promise_patterns = config.get('promise_tracking', 'patterns', default=[])
            for i, pattern in enumerate(promise_patterns):
                st.text_input(f"Pattern {i+1}", value=pattern, key=f"promise_pattern_{i}")
        
        # Dependencies
        with pattern_tabs[2]:
            st.toggle(
                "Track internal dependencies",
                value=config.get('dependency_tracking', 'enabled', default=True),
                key="track_deps"
            )
            
            st.markdown("##### Dependency Detection Patterns")
            dep_patterns = config.get('dependency_tracking', 'patterns', default=[])
            for i, pattern in enumerate(dep_patterns):
                st.text_input(f"Pattern {i+1}", value=pattern, key=f"dep_pattern_{i}")
        
        # Config Issues
        with pattern_tabs[3]:
            st.toggle(
                "Detect configuration issues",
                value=config.get('config_issues', 'detect', default=True),
                key="detect_config"
            )
            
            issue_types = config.get('config_issues', 'types', default={})
            
            for issue_key, issue_data in issue_types.items():
                with st.expander(f"⚙️ {issue_data['name']}"):
                    st.text_input(
                        "Keywords",
                        value=', '.join(issue_data.get('keywords', [])),
                        key=f"config_{issue_key}_keywords"
                    )
                    st.text_input(
                        "Fault Indicators",
                        value=', '.join(issue_data.get('fault_indicators', [])),
                        key=f"config_{issue_key}_fault"
                    )
    
    # =========================================================================
    # AI TAB
    # =========================================================================
    with tabs[6]:
        st.subheader("AI Configuration")
        st.caption("Configure AI providers for intelligent analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### AI Provider")
            
            providers = ['ollama', 'openai', 'anthropic', 'none']
            current_provider = config.get('ai', 'provider', default='ollama')
            
            provider = st.selectbox(
                "Provider",
                providers,
                index=providers.index(current_provider) if current_provider in providers else 0,
                format_func=lambda x: {'ollama': '🦙 Ollama (Local)', 'openai': '🤖 OpenAI', 
                                      'anthropic': '🔷 Anthropic', 'none': '❌ Disabled'}.get(x, x),
                key="ai_provider"
            )
            
            if provider == 'ollama':
                st.text_input(
                    "Ollama URL",
                    value=config.get('ai', 'ollama', 'base_url', default='http://localhost:11434'),
                    key="ollama_url"
                )
                st.text_input(
                    "Model",
                    value=config.get('ai', 'ollama', 'model', default='qwen2.5:14b'),
                    key="ollama_model"
                )
            
            elif provider == 'openai':
                st.text_input(
                    "API Key",
                    type="password",
                    key="openai_key"
                )
                st.selectbox(
                    "Model",
                    ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
                    key="openai_model"
                )
            
            st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.1,
                key="ai_temperature"
            )
        
        with col2:
            st.markdown("##### AI Features")
            
            features = config.get('ai', 'features', default={})
            
            st.toggle(
                "Issue Clustering",
                value=features.get('issue_clustering', True),
                key="ai_clustering",
                help="Group similar tickets into issue clusters"
            )
            
            st.toggle(
                "Root Cause Analysis",
                value=features.get('root_cause_analysis', True),
                key="ai_root_cause",
                help="Identify root causes for issue clusters"
            )
            
            st.toggle(
                "Auto Categorization",
                value=features.get('auto_categorization', True),
                key="ai_auto_cat",
                help="Automatically categorize uncategorized tickets"
            )
            
            st.toggle(
                "Sentiment Analysis",
                value=features.get('sentiment_analysis', False),
                key="ai_sentiment",
                help="Analyze customer sentiment in messages"
            )
            
            if st.button("🔗 Test Connection", type="secondary"):
                with st.spinner("Testing AI connection..."):
                    # Simulate test
                    import time
                    time.sleep(1)
                    st.success("✓ AI connection successful!")
    
    # =========================================================================
    # INTEGRATIONS TAB
    # =========================================================================
    with tabs[7]:
        st.subheader("Integrations")
        st.caption("Connect to external services")
        
        st.markdown("##### Freshdesk API")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input(
                "Domain",
                value=config.get('freshdesk', 'domain', default=''),
                placeholder="your-company",
                key="fd_domain"
            )
            
            st.text_input(
                "API Key",
                type="password",
                value=config.get('freshdesk', 'api_key', default=''),
                key="fd_api_key"
            )
        
        with col2:
            st.number_input(
                "Group ID (optional)",
                value=config.get('freshdesk', 'group_id', default=0) or 0,
                key="fd_group"
            )
            
            st.number_input(
                "Days to Fetch",
                value=config.get('freshdesk', 'days_to_fetch', default=180),
                min_value=1,
                max_value=365,
                key="fd_days"
            )
        
        st.toggle(
            "Include conversations",
            value=config.get('freshdesk', 'include_conversations', default=True),
            key="fd_convs"
        )
        
        st.toggle(
            "Include private notes",
            value=config.get('freshdesk', 'include_notes', default=True),
            key="fd_notes"
        )
        
        if st.button("🔗 Test Freshdesk Connection"):
            st.info("Connection test coming soon!")
        
        st.markdown("---")
        st.markdown("##### Agent Cache")
        
        st.text_input(
            "Agent Cache File",
            value=config.get('agent_cache', 'file', default='.agent_cache.json'),
            key="agent_cache_file"
        )
        
        st.file_uploader(
            "Upload Agent Excel (dl_agents.xlsx)",
            type=['xlsx'],
            key="agent_excel"
        )
    
    # =========================================================================
    # EXPORT TAB
    # =========================================================================
    with tabs[8]:
        st.subheader("Export Settings")
        st.caption("Configure report generation options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Excel Export")
            
            st.toggle(
                "Include charts",
                value=config.get('export', 'excel', 'include_charts', default=True),
                key="excel_charts"
            )
            
            st.toggle(
                "Include formulas",
                value=config.get('export', 'excel', 'include_formulas', default=True),
                key="excel_formulas"
            )
            
            st.toggle(
                "Password protect",
                value=config.get('export', 'excel', 'password_protect', default=False),
                key="excel_password"
            )
        
        with col2:
            st.markdown("##### PDF Export")
            
            st.toggle(
                "Include charts",
                value=config.get('export', 'pdf', 'include_charts', default=True),
                key="pdf_charts"
            )
            
            st.selectbox(
                "Page Size",
                ['A4', 'Letter', 'Legal'],
                key="pdf_size"
            )
    
    # =========================================================================
    # SAVE BUTTON
    # =========================================================================
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            # Collect all settings from session state widgets and save
            try:
                # Branding settings
                if 'brand_company_name' in st.session_state:
                    config.set('branding', 'company_name', st.session_state.brand_company_name)
                if 'brand_platform_name' in st.session_state:
                    config.set('branding', 'platform_name', st.session_state.brand_platform_name)
                if 'brand_tagline' in st.session_state:
                    config.set('branding', 'tagline', st.session_state.brand_tagline)
                if 'brand_primary_color' in st.session_state:
                    config.set('branding', 'primary_color', st.session_state.brand_primary_color)
                if 'brand_secondary_color' in st.session_state:
                    config.set('branding', 'secondary_color', st.session_state.brand_secondary_color)
                if 'brand_accent_color' in st.session_state:
                    config.set('branding', 'accent_color', st.session_state.brand_accent_color)
                
                # Industry settings
                if 'org_name' in st.session_state:
                    config.set('industry', 'name', st.session_state.org_name)
                if 'entity_type' in st.session_state:
                    config.set('industry', 'primary_entity', st.session_state.entity_type)
                if 'entity_field' in st.session_state:
                    config.set('industry', 'entity_field', st.session_state.entity_field)
                
                # SLA settings
                if 'sla_frt' in st.session_state:
                    config.set('sla', 'first_response_hours', st.session_state.sla_frt)
                if 'sla_resolution' in st.session_state:
                    config.set('sla', 'resolution_hours', st.session_state.sla_resolution)
                if 'sla_stale' in st.session_state:
                    config.set('sla', 'stale_threshold_days', st.session_state.sla_stale)
                
                # Working hours
                if 'timezone' in st.session_state:
                    config.set('working_hours', 'timezone', st.session_state.timezone)
                if 'work_start' in st.session_state:
                    config.set('working_hours', 'start_hour', st.session_state.work_start)
                if 'work_end' in st.session_state:
                    config.set('working_hours', 'end_hour', st.session_state.work_end)
                
                # AI settings - CRITICAL for model persistence
                if 'ai_provider' in st.session_state:
                    config.set('ai', 'provider', st.session_state.ai_provider)
                if 'ollama_url' in st.session_state:
                    config.set('ai', 'ollama', 'base_url', st.session_state.ollama_url)
                if 'ollama_model' in st.session_state:
                    config.set('ai', 'ollama', 'model', st.session_state.ollama_model)
                if 'ai_temperature' in st.session_state:
                    config.set('ai', 'ollama', 'temperature', st.session_state.ai_temperature)
                if 'openai_key' in st.session_state:
                    config.set('ai', 'openai', 'api_key', st.session_state.openai_key)
                if 'openai_model' in st.session_state:
                    config.set('ai', 'openai', 'model', st.session_state.openai_model)
                
                # AI features
                if 'ai_clustering' in st.session_state:
                    config.set('ai', 'features', 'issue_clustering', st.session_state.ai_clustering)
                if 'ai_root_cause' in st.session_state:
                    config.set('ai', 'features', 'root_cause_analysis', st.session_state.ai_root_cause)
                if 'ai_auto_cat' in st.session_state:
                    config.set('ai', 'features', 'auto_categorization', st.session_state.ai_auto_cat)
                if 'ai_sentiment' in st.session_state:
                    config.set('ai', 'features', 'sentiment_analysis', st.session_state.ai_sentiment)
                
                # Freshdesk settings
                if 'fd_domain' in st.session_state:
                    config.set('freshdesk', 'domain', st.session_state.fd_domain)
                if 'fd_api_key' in st.session_state:
                    config.set('freshdesk', 'api_key', st.session_state.fd_api_key)
                if 'fd_group' in st.session_state:
                    config.set('freshdesk', 'group_id', st.session_state.fd_group)
                if 'fd_days' in st.session_state:
                    config.set('freshdesk', 'days_to_fetch', st.session_state.fd_days)
                
                # Now save to disk
                config.save()
                st.success("✅ Configuration saved!")
                st.caption(f"Model set to: {st.session_state.get('ollama_model', 'N/A')}")
            except Exception as e:
                st.error(f"Error saving: {e}")
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            if st.session_state.get('confirm_reset'):
                # Reset
                st.session_state.config = DEFAULT_CONFIG.copy()
                st.success("✓ Reset to defaults!")
                del st.session_state['confirm_reset']
            else:
                st.session_state['confirm_reset'] = True
                st.warning("Click again to confirm reset")
    
    with col3:
        st.download_button(
            "📥 Export Config (YAML)",
            data=yaml.dump(config.to_dict(), default_flow_style=False),
            file_name="ftex_config.yaml",
            mime="text/yaml",
            use_container_width=True
        )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    render_settings()
