"""
Dashboard Page
==============
Main analytics dashboard with KPIs and interactive charts.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from collections import Counter
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state, apply_filters
from core.data_loader import DataLoader, analyze_by_company, analyze_by_category
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="Dashboard | FTEX", page_icon="📊", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()


def render_kpi_card(title: str, value: str, delta: str = None, delta_color: str = "normal"):
    """Render a KPI metric card."""
    st.metric(label=title, value=value, delta=delta, delta_color=delta_color)


def render_filters():
    """Render global filters in sidebar."""
    with st.sidebar:
        st.subheader("🔍 Filters")
        
        # Date range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From", value=datetime.now() - timedelta(days=180))
        with col2:
            end_date = st.date_input("To", value=datetime.now())
        
        # Company filter
        companies = ['All'] + sorted(set(t.company_name for t in st.session_state.tickets if t.company_name))
        st.selectbox("Company", companies, key="selected_company")
        
        # Status filter
        st.selectbox("Status", ['All', 'Open', 'Pending', 'Resolved', 'Closed'], key="selected_status")
        
        # Priority filter
        st.selectbox("Priority", ['All', 'Low', 'Medium', 'High', 'Urgent'], key="selected_priority")
        
        st.session_state.date_range = (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))


def render_dashboard():
    """Render the main dashboard."""
    
    st.title("📊 Analytics Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Check for data
    if not st.session_state.get('data_loaded'):
        st.warning("⚠️ No data loaded. Please upload a file or connect to API from the home page.")
        st.page_link("main.py", label="← Go to Home", icon="🏠")
        return
    
    # Render filters
    render_filters()
    
    # Get filtered tickets
    tickets = apply_filters(st.session_state.tickets)
    
    if not tickets:
        st.info("No tickets match the current filters.")
        return
    
    # =========================================================================
    # KPI ROW
    # =========================================================================
    st.markdown("---")
    
    kpi_cols = st.columns(6)
    
    # Calculate metrics
    total = len(tickets)
    open_count = sum(1 for t in tickets if t.is_open)
    pending = sum(1 for t in tickets if t.status == 3)
    resolved = sum(1 for t in tickets if t.is_resolved)
    stale = sum(1 for t in tickets if t.is_open and t.days_open >= 15)
    
    # SLA
    with_response = [t for t in tickets if t.first_response_time is not None]
    sla_met = sum(1 for t in with_response if t.first_response_time <= 12)
    sla_rate = (sla_met / len(with_response) * 100) if with_response else 0
    
    # Avg response
    avg_response = sum(t.first_response_time for t in with_response) / len(with_response) if with_response else 0
    
    with kpi_cols[0]:
        render_kpi_card("Total Tickets", f"{total:,}")
    
    with kpi_cols[1]:
        render_kpi_card("Open", str(open_count), delta=f"{pending} pending")
    
    with kpi_cols[2]:
        delta_color = "normal" if sla_rate >= 90 else "inverse" if sla_rate < 70 else "off"
        render_kpi_card("SLA Compliance", f"{sla_rate:.1f}%", delta_color=delta_color)
    
    with kpi_cols[3]:
        render_kpi_card("Avg Response", f"{avg_response:.1f}h")
    
    with kpi_cols[4]:
        render_kpi_card("Stale (>15d)", str(stale), delta_color="inverse" if stale > 0 else "normal")
    
    with kpi_cols[5]:
        no_response = sum(1 for t in tickets if not t.has_agent_response)
        render_kpi_card("No Response", str(no_response), delta_color="inverse" if no_response > 0 else "normal")
    
    st.markdown("---")
    
    # =========================================================================
    # AI INSIGHTS ROW (if deep analysis available)
    # =========================================================================
    deep_analysis = st.session_state.get('deep_analysis', {})
    if deep_analysis:
        st.subheader("🤖 AI Insights")
        
        ai_col1, ai_col2, ai_col3 = st.columns(3)
        
        with ai_col1:
            # Sentiment Gauge
            sentiment_data = deep_analysis.get('sentiment', {})
            if sentiment_data:
                scores = [s.get('score', 0) for s in sentiment_data.values()]
                avg_score = sum(scores) / max(len(scores), 1)
                
                # Color based on sentiment
                if avg_score > 0.3:
                    gauge_color = "#10B981"  # Green
                    mood = "Positive 😊"
                elif avg_score > -0.3:
                    gauge_color = "#F59E0B"  # Yellow
                    mood = "Neutral 😐"
                else:
                    gauge_color = "#EF4444"  # Red
                    mood = "Negative 😟"
                
                st.markdown("##### 😊 Customer Mood")
                st.metric("Sentiment", mood, delta=f"{avg_score:.2f}")
                
                # Frustrated count
                frustrated = sum(1 for s in sentiment_data.values() 
                               if s.get('label') in ['frustrated', 'angry'])
                if frustrated > 0:
                    st.warning(f"⚠️ {frustrated} frustrated customers")
            else:
                st.info("Run Deep Analysis for sentiment insights")
        
        with ai_col2:
            # Escalation Alerts
            escalation = deep_analysis.get('escalation', {})
            if escalation:
                critical = sum(1 for e in escalation.values() if e.get('risk') == 'critical')
                high = sum(1 for e in escalation.values() if e.get('risk') == 'high')
                
                st.markdown("##### 🚨 Escalation Risk")
                if critical > 0:
                    st.error(f"🔴 {critical} Critical - Action Needed!")
                if high > 0:
                    st.warning(f"🟠 {high} High Risk")
                if critical == 0 and high == 0:
                    st.success("✅ No escalation risks")
            else:
                st.info("Run Deep Analysis for escalation insights")
        
        with ai_col3:
            # Quick summary stats from AI
            st.markdown("##### 📊 Analysis Summary")
            st.caption(f"Last run: {deep_analysis.get('timestamp', 'N/A')[:16]}")
            
            promises = deep_analysis.get('promises', {})
            overdue = sum(1 for pl in promises.values() for p in pl if p.get('status') == 'overdue')
            if overdue > 0:
                st.warning(f"⏰ {overdue} overdue promises")
            
            recurring = len(deep_analysis.get('recurring_issues', []))
            if recurring > 0:
                st.info(f"🔄 {recurring} recurring issues detected")
        
        st.markdown("---")
    
    # =========================================================================
    # CHARTS ROW 1
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Ticket Volume Trend")
        
        # Group by date
        date_counts = Counter(t.created_at.strftime('%Y-%m-%d') for t in tickets if t.created_at)
        dates = sorted(date_counts.keys())
        counts = [date_counts[d] for d in dates]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=counts,
            mode='lines+markers',
            fill='tozeroy',
            fillcolor='rgba(31, 78, 121, 0.2)',
            line=dict(color='#1F4E79', width=2),
            marker=dict(size=4),
        ))
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Date",
            yaxis_title="Tickets",
            hovermode='x unified',
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Status Distribution")
        
        status_counts = Counter(t.status_name for t in tickets)
        
        colors = {
            'Open': '#3B82F6',
            'Pending': '#F59E0B',
            'Resolved': '#10B981',
            'Closed': '#6B7280',
        }
        
        fig = go.Figure(data=[go.Pie(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            hole=0.4,
            marker=dict(colors=[colors.get(s, '#6B7280') for s in status_counts.keys()]),
            textinfo='label+percent',
        )])
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # CHARTS ROW 2
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Category Distribution")
        
        category_counts = Counter(t.category or 'Uncategorized' for t in tickets)
        sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        fig = go.Figure(data=[go.Bar(
            x=[c[1] for c in sorted_cats],
            y=[c[0] for c in sorted_cats],
            orientation='h',
            marker_color='#1F4E79',
        )])
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Count",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚡ Priority Breakdown")
        
        priority_counts = Counter(t.priority_name for t in tickets)
        
        priority_order = ['Urgent', 'High', 'Medium', 'Low']
        colors = {'Urgent': '#EF4444', 'High': '#F97316', 'Medium': '#F59E0B', 'Low': '#10B981'}
        
        fig = go.Figure(data=[go.Bar(
            x=[priority_counts.get(p, 0) for p in priority_order],
            y=priority_order,
            orientation='h',
            marker_color=[colors[p] for p in priority_order],
        )])
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Count",
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # CHARTS ROW 3
    # =========================================================================
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 Top Companies")
        
        company_counts = Counter(t.company_name or '(Unknown)' for t in tickets)
        top_companies = company_counts.most_common(10)
        
        fig = go.Figure(data=[go.Bar(
            x=[c[0][:30] for c in top_companies],
            y=[c[1] for c in top_companies],
            marker_color='#2E75B6',
        )])
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_title="Tickets",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ Response Time Distribution")
        
        response_times = [t.first_response_time for t in tickets if t.first_response_time and t.first_response_time < 200]
        
        if response_times:
            fig = go.Figure(data=[go.Histogram(
                x=response_times,
                nbinsx=20,
                marker_color='#1F4E79',
            )])
            fig.add_vline(x=12, line_dash="dash", line_color="red", annotation_text="SLA (12h)")
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Hours to First Response",
                yaxis_title="Count",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No response time data available")
    
    # =========================================================================
    # RECENT TICKETS TABLE
    # =========================================================================
    st.markdown("---")
    st.subheader("📋 Recent Tickets")
    
    # Sort by created date
    recent = sorted(tickets, key=lambda t: t.created_at or datetime.min, reverse=True)[:20]
    
    # Create display data
    table_data = []
    for t in recent:
        table_data.append({
            'ID': t.id,
            'Subject': t.subject[:50],
            'Company': t.company_name[:30] if t.company_name else '-',
            'Status': t.status_name,
            'Priority': t.priority_name,
            'Created': t.created_at.strftime('%Y-%m-%d') if t.created_at else '-',
            'Days Open': t.days_open,
        })
    
    # Display with color coding
    import pandas as pd
    df = pd.DataFrame(table_data)
    
    # Style function
    def style_status(val):
        colors = {
            'Open': 'background-color: #DBEAFE',
            'Pending': 'background-color: #FEF3C7',
            'Resolved': 'background-color: #D1FAE5',
            'Closed': 'background-color: #F3F4F6',
        }
        return colors.get(val, '')
    
    styled_df = df.style.applymap(style_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # =========================================================================
    # ALERTS SECTION
    # =========================================================================
    st.markdown("---")
    st.subheader("🚨 Attention Required")
    
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        # Stale tickets
        stale_tickets = [t for t in tickets if t.is_open and t.days_open >= 15]
        if stale_tickets:
            with st.expander(f"⚠️ {len(stale_tickets)} Stale Tickets (>15 days)", expanded=True):
                for t in stale_tickets[:5]:
                    st.markdown(f"- **#{t.id}**: {t.subject[:40]}... ({t.days_open} days)")
                if len(stale_tickets) > 5:
                    st.caption(f"+ {len(stale_tickets) - 5} more...")
        else:
            st.success("✅ No stale tickets")
    
    with alert_col2:
        # No response
        no_response_tickets = [t for t in tickets if not t.has_agent_response and t.is_open]
        if no_response_tickets:
            with st.expander(f"🔴 {len(no_response_tickets)} Tickets Without Response", expanded=True):
                for t in no_response_tickets[:5]:
                    st.markdown(f"- **#{t.id}**: {t.subject[:40]}...")
                if len(no_response_tickets) > 5:
                    st.caption(f"+ {len(no_response_tickets) - 5} more...")
        else:
            st.success("✅ All tickets have responses")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Check if we need to load sample data for demo
    if not st.session_state.get('data_loaded'):
        st.warning("No data loaded. Showing demo with sample data.")
        
        # Create sample tickets for demo
        from core.data_loader import Ticket
        import random
        
        sample_tickets = []
        statuses = [2, 3, 4, 5]
        priorities = [1, 2, 3, 4]
        companies = ['Acme Corp', 'TechStart Inc', 'Global Solutions', 'Maritime Ltd', 'DataFlow Systems']
        categories = ['Bug Report', 'Feature Request', 'Configuration', 'Support Query', 'Installation']
        
        for i in range(100):
            created = datetime.now() - timedelta(days=random.randint(1, 180))
            resolved = created + timedelta(hours=random.randint(1, 200)) if random.random() > 0.3 else None
            
            t = Ticket(
                id=1000 + i,
                subject=f"Sample ticket {i+1} - {random.choice(categories)}",
                description="Sample description",
                status=random.choice(statuses),
                priority=random.choice(priorities),
                created_at=created,
                updated_at=created + timedelta(hours=random.randint(1, 48)),
                resolved_at=resolved,
                company_name=random.choice(companies),
                requester_name="John Doe",
                requester_email="john@example.com",
                responder_id=random.randint(1000, 1010) if random.random() > 0.2 else None,
                responder_name="",
                conversations=[],
                tags=[],
                custom_fields={},
                category=random.choice(categories),
                first_response_time=random.uniform(0.5, 50) if random.random() > 0.2 else None,
                resolution_time=random.uniform(1, 200) if resolved else None,
                has_agent_response=random.random() > 0.15,
            )
            sample_tickets.append(t)
        
        st.session_state.tickets = sample_tickets
        st.session_state.data_loaded = True
    
    render_dashboard()
