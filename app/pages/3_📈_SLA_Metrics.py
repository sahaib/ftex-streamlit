"""
SLA Metrics Page
================
Comprehensive SLA performance tracking and analysis.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state, apply_filters
from core.config_manager import get_config
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="SLA Metrics | FTEX", page_icon="📈", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()
config = get_config()


def render_sla_page():
    """Render the SLA metrics page."""
    
    st.title("📈 SLA Performance")
    st.caption("Track service level agreement compliance")
    
    # Check for data
    if not st.session_state.get('data_loaded'):
        st.warning("⚠️ No data loaded. Please upload a file from the home page.")
        st.page_link("main.py", label="← Go to Home", icon="🏠")
        return
    
    tickets = apply_filters(st.session_state.tickets)
    
    if not tickets:
        st.info("No tickets match the current filters.")
        return
    
    # Get SLA config
    sla_config = config.get('sla', default={})
    frt_target = sla_config.get('first_response_hours', 12)
    resolution_target = sla_config.get('resolution_hours', 24)
    
    # Calculate metrics
    with_response = [t for t in tickets if t.first_response_time is not None]
    resolved = [t for t in tickets if t.resolution_time is not None]
    
    frt_met = sum(1 for t in with_response if t.first_response_time <= frt_target)
    frt_rate = (frt_met / len(with_response) * 100) if with_response else 0
    
    res_met = sum(1 for t in resolved if t.resolution_time <= resolution_target)
    res_rate = (res_met / len(resolved) * 100) if resolved else 0
    
    avg_frt = sum(t.first_response_time for t in with_response) / len(with_response) if with_response else 0
    avg_resolution = sum(t.resolution_time for t in resolved) / len(resolved) if resolved else 0
    
    # =========================================================================
    # KPI ROW
    # =========================================================================
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "First Response SLA",
            f"{frt_rate:.1f}%",
            delta=f"Target: {frt_target}h",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            "Resolution SLA",
            f"{res_rate:.1f}%",
            delta=f"Target: {resolution_target}h",
            delta_color="off"
        )
    
    with col3:
        st.metric(
            "Avg First Response",
            f"{avg_frt:.1f}h"
        )
    
    with col4:
        st.metric(
            "Avg Resolution",
            f"{avg_resolution:.1f}h"
        )
    
    st.markdown("---")
    
    # =========================================================================
    # SLA GAUGE CHARTS
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏱️ First Response Time SLA")
        
        # Gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=frt_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Target: <{frt_target}h"},
            delta={'reference': 90, 'increasing': {'color': "green"}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#1F4E79"},
                'steps': [
                    {'range': [0, 70], 'color': "#FEE2E2"},
                    {'range': [70, 80], 'color': "#FEF3C7"},
                    {'range': [80, 90], 'color': "#FEF9C3"},
                    {'range': [90, 100], 'color': "#D1FAE5"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        # Stats
        st.markdown(f"""
        - **Met SLA**: {frt_met:,} tickets ({frt_rate:.1f}%)
        - **Breached SLA**: {len(with_response) - frt_met:,} tickets
        - **Average**: {avg_frt:.1f} hours
        """)
    
    with col2:
        st.subheader("✅ Resolution Time SLA")
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=res_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Target: <{resolution_target}h"},
            delta={'reference': 90, 'increasing': {'color': "green"}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#1F4E79"},
                'steps': [
                    {'range': [0, 70], 'color': "#FEE2E2"},
                    {'range': [70, 80], 'color': "#FEF3C7"},
                    {'range': [80, 90], 'color': "#FEF9C3"},
                    {'range': [90, 100], 'color': "#D1FAE5"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown(f"""
        - **Met SLA**: {res_met:,} tickets ({res_rate:.1f}%)
        - **Breached SLA**: {len(resolved) - res_met:,} tickets
        - **Average**: {avg_resolution:.1f} hours
        """)
    
    # =========================================================================
    # SLA TRENDS
    # =========================================================================
    st.markdown("---")
    st.subheader("📊 SLA Performance Over Time")
    
    # Group by week
    weekly_data = defaultdict(lambda: {'total': 0, 'met': 0})
    
    for t in with_response:
        if t.created_at:
            week = t.created_at.strftime('%Y-W%W')
            weekly_data[week]['total'] += 1
            if t.first_response_time <= frt_target:
                weekly_data[week]['met'] += 1
    
    weeks = sorted(weekly_data.keys())[-12:]  # Last 12 weeks
    rates = [
        (weekly_data[w]['met'] / weekly_data[w]['total'] * 100) if weekly_data[w]['total'] > 0 else 0
        for w in weeks
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks, y=rates,
        mode='lines+markers',
        name='SLA Rate',
        line=dict(color='#1F4E79', width=3),
        marker=dict(size=8),
    ))
    fig.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Target (90%)")
    fig.update_layout(
        height=350,
        xaxis_title="Week",
        yaxis_title="SLA Compliance %",
        yaxis_range=[0, 100],
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # SLA BY PRIORITY
    # =========================================================================
    st.markdown("---")
    st.subheader("⚡ SLA by Priority")
    
    priority_sla = sla_config.get('by_priority', {})
    
    priority_data = []
    for priority_name in ['Urgent', 'High', 'Medium', 'Low']:
        priority_tickets = [t for t in with_response if t.priority_name == priority_name]
        if priority_tickets:
            target = priority_sla.get(priority_name, {}).get('first_response', frt_target)
            met = sum(1 for t in priority_tickets if t.first_response_time <= target)
            rate = met / len(priority_tickets) * 100
            avg = sum(t.first_response_time for t in priority_tickets) / len(priority_tickets)
            priority_data.append({
                'Priority': priority_name,
                'Tickets': len(priority_tickets),
                'Target (hrs)': target,
                'Met SLA': met,
                'SLA %': f"{rate:.1f}%",
                'Avg Response (hrs)': f"{avg:.1f}",
            })
    
    if priority_data:
        import pandas as pd
        df = pd.DataFrame(priority_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # =========================================================================
    # SLA BREACHES TABLE
    # =========================================================================
    st.markdown("---")
    st.subheader("⚠️ Recent SLA Breaches")
    
    breaches = [t for t in with_response if t.first_response_time > frt_target]
    breaches = sorted(breaches, key=lambda t: t.first_response_time, reverse=True)[:20]
    
    if breaches:
        breach_data = []
        for t in breaches:
            breach_data.append({
                'Ticket ID': t.id,
                'Subject': t.subject[:40],
                'Company': t.company_name[:25] if t.company_name else '-',
                'Priority': t.priority_name,
                'Response Time (hrs)': f"{t.first_response_time:.1f}",
                'Target (hrs)': frt_target,
                'Breach (hrs)': f"{t.first_response_time - frt_target:.1f}",
            })
        
        import pandas as pd
        df = pd.DataFrame(breach_data)
        
        # Color the breach column
        def highlight_breach(val):
            try:
                hours = float(val)
                if hours > 24:
                    return 'background-color: #FEE2E2'
                elif hours > 12:
                    return 'background-color: #FEF3C7'
                return ''
            except:
                return ''
        
        styled_df = df.style.applymap(highlight_breach, subset=['Breach (hrs)'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No SLA breaches found!")
    
    # =========================================================================
    # SLA BAND ANALYSIS
    # =========================================================================
    st.markdown("---")
    st.subheader("📊 SLA Performance Bands")
    
    bands = sla_config.get('bands', {})
    
    # Categorize tickets by band
    band_counts = Counter()
    for t in with_response:
        rate = 100 if t.first_response_time <= frt_target else 0
        for band_name, band_config in bands.items():
            if band_config['min'] <= rate <= band_config['max']:
                band_counts[band_name] += 1
                break
    
    # Display band summary
    col1, col2, col3, col4, col5 = st.columns(5)
    band_cols = [col1, col2, col3, col4, col5]
    band_order = ['excellent', 'good', 'acceptable', 'needs_improvement', 'poor']
    
    for i, band_name in enumerate(band_order):
        if band_name in bands:
            with band_cols[i]:
                band = bands[band_name]
                icon = {'excellent': '🟢', 'good': '🔵', 'acceptable': '🟡', 
                       'needs_improvement': '🟠', 'poor': '🔴'}.get(band_name, '⚪')
                st.markdown(f"**{icon} {band_name.replace('_', ' ').title()}**")
                st.markdown(f"{band['min']}-{band['max']}%")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    render_sla_page()
