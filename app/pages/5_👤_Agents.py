"""
Agents Page
===========
Agent performance tracking and analysis with premium analytics.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state, apply_filters
from core.data_loader import analyze_by_agent
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="Agents | FTEX", page_icon="👤", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()


def render_premium_kpi_card(title: str, value: str, subtitle: str = None, delta: str = None, help_text: str = None):
    """Render a premium KPI card with optional subtitle and help tooltip."""
    with st.container():
        if help_text:
            st.metric(label=title, value=value, delta=delta, help=help_text)
        else:
            st.metric(label=title, value=value, delta=delta)
        if subtitle:
            st.caption(subtitle)


def render_activity_heatmap(tickets):
    """Render hour-of-day vs day-of-week activity heatmap."""
    st.subheader("🗓️ Activity Heatmap")
    st.caption("When tickets are handled - darker = higher activity")
    
    # Build activity matrix
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_order = {d: i for i, d in enumerate(days)}
    
    activity = defaultdict(int)
    for t in tickets:
        if t.created_at and t.responder_id:
            day = t.created_at.strftime('%a')
            hour = t.created_at.hour
            activity[(day, hour)] += 1
    
    # Create matrix [hours x days]
    z = [[activity.get((d, h), 0) for d in days] for h in range(24)]
    
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=days,
        y=[f"{h:02d}:00" for h in range(24)],
        colorscale='Blues',
        hoverongaps=False,
        hovertemplate='%{x} at %{y}<br>Tickets: %{z}<extra></extra>',
    ))
    
    fig.update_layout(
        height=450,
        margin=dict(l=60, r=20, t=20, b=40),
        xaxis_title="Day of Week",
        yaxis_title="Hour of Day",
        yaxis=dict(autorange="reversed"),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_agent_metric_heatmap(agent_data, sorted_agents):
    """Render agent-by-metric performance heatmap."""
    st.subheader("🎯 Agent Performance Matrix")
    st.caption("Compare agents across key metrics - greener = better")
    
    # Select top agents for readability
    top_agents = sorted_agents[:12]
    
    if len(top_agents) < 2:
        st.info("Need at least 2 agents to render comparison heatmap")
        return
    
    # Define metrics to compare (normalized 0-100 where higher is better)
    metrics = ['SLA %', 'FCR %', 'Resolution %', 'Consistency', 'Volume']
    
    # Build matrix
    agent_names = [data['agent_name'][:15] for _, data in top_agents]
    z = []
    
    # Normalize values for heatmap (all scaled 0-100)
    max_tickets = max(d['tickets'] for _, d in top_agents) if top_agents else 1
    
    for _, data in top_agents:
        row = [
            data['sla_rate'],
            data['fcr_rate'],
            data['resolution_rate'],
            max(0, 100 - data['response_consistency'] * 5),  # Lower std = better (invert)
            (data['tickets'] / max_tickets * 100) if max_tickets else 0,
        ]
        z.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=metrics,
        y=agent_names,
        colorscale='RdYlGn',
        zmin=0,
        zmax=100,
        hoverongaps=False,
        hovertemplate='%{y}<br>%{x}: %{z:.1f}<extra></extra>',
        text=[[f"{v:.0f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont={"size": 11},
    ))
    
    fig.update_layout(
        height=max(300, len(top_agents) * 35),
        margin=dict(l=120, r=20, t=20, b=60),
        xaxis_tickangle=-45,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_agents_page():
    """Render the agents page with premium analytics."""
    
    st.title("👤 Agent Performance")
    st.caption("Premium analytics • First Contact Resolution • Utilization • Consistency Scoring")
    
    # Check for data
    if not st.session_state.get('data_loaded'):
        st.warning("⚠️ No data loaded. Please upload a file from the home page.")
        st.page_link("main.py", label="← Go to Home", icon="🏠")
        return
    
    tickets = apply_filters(st.session_state.tickets)
    
    if not tickets:
        st.info("No tickets match the current filters.")
        return
    
    # Analyze by agent
    agent_data = analyze_by_agent(tickets)
    
    if not agent_data:
        st.info("No agent data available.")
        return
    
    # Sort by ticket count
    sorted_agents = sorted(agent_data.items(), key=lambda x: x[1]['tickets'], reverse=True)
    
    # =========================================================================
    # PREMIUM KPIs ROW
    # =========================================================================
    st.markdown("---")
    st.subheader("📊 Team Overview")
    
    # Check for AI deep analysis
    deep_analysis = st.session_state.get('deep_analysis', {})
    quality_data = deep_analysis.get('quality', {})
    
    kpi_cols = st.columns(7)
    
    total_agents = len(agent_data)
    total_tickets = sum(d['tickets'] for d in agent_data.values())
    avg_tickets = total_tickets / total_agents if total_agents else 0
    avg_sla = sum(d['sla_rate'] for d in agent_data.values()) / total_agents if total_agents else 0
    avg_fcr = sum(d['fcr_rate'] for d in agent_data.values()) / total_agents if total_agents else 0
    avg_resolution = sum(d['resolution_rate'] for d in agent_data.values()) / total_agents if total_agents else 0
    
    with kpi_cols[0]:
        st.metric("Total Agents", total_agents)
    
    with kpi_cols[1]:
        st.metric("Total Handled", f"{total_tickets:,}")
    
    with kpi_cols[2]:
        st.metric("Avg SLA Rate", f"{avg_sla:.1f}%", help="Average first response within SLA")
    
    with kpi_cols[3]:
        st.metric("Avg FCR Rate", f"{avg_fcr:.1f}%", help="First Contact Resolution - tickets resolved with ≤2 messages in ≤24h")
    
    with kpi_cols[4]:
        st.metric("Resolution Rate", f"{avg_resolution:.1f}%", help="Average percentage of tickets resolved per agent")
    
    with kpi_cols[5]:
        avg_consistency = sum(d['response_consistency'] for d in agent_data.values()) / total_agents if total_agents else 0
        st.metric("Avg Consistency", f"±{avg_consistency:.1f}h", help="Response time standard deviation (lower = more consistent)")
    
    with kpi_cols[6]:
        # AI Conversation Quality Score
        if quality_data:
            scores = [q.get('overall_score', 0) for q in quality_data.values()]
            avg_quality = sum(scores) / max(len(scores), 1)
            quality_label = "🟢 Good" if avg_quality >= 7 else "🟡 OK" if avg_quality >= 5 else "🟠 Needs Work"
            st.metric("🤖 AI Quality", f"{avg_quality:.1f}/10", delta=quality_label, help="Average conversation quality score from AI analysis")
        else:
            st.metric("🤖 AI Quality", "N/A", delta="Run AI Analysis", help="Run Deep Analysis to see quality scores")
    
    st.markdown("---")
    
    # =========================================================================
    # HEATMAPS ROW
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        render_activity_heatmap(tickets)
    
    with col2:
        render_agent_metric_heatmap(agent_data, sorted_agents)
    
    # =========================================================================
    # PERFORMANCE TABLE WITH PREMIUM METRICS
    # =========================================================================
    st.markdown("---")
    st.subheader("📋 Agent Performance Details")
    
    # Create table data with agent names
    table_data = []
    for agent_id, data in sorted_agents:
        table_data.append({
            'Agent': data['agent_name'],
            'Tickets': data['tickets'],
            'Resolved': data['resolved'],
            'Open': data['open'],
            'Res. Rate': f"{data['resolution_rate']:.0f}%",
            'Avg Resp.': f"{data['avg_response']:.1f}h",
            'SLA %': f"{data['sla_rate']:.0f}%",
            'FCR %': f"{data['fcr_rate']:.0f}%",
            'Touches': data['avg_touches'],
            'Consistency': f"±{data['response_consistency']:.1f}h",
            'Complexity': f"{data['complexity']:.0f}%",
            'Customers': data['customer_coverage'],
        })
    
    import pandas as pd
    df = pd.DataFrame(table_data)
    
    # Style the SLA column
    def style_sla(val):
        try:
            rate = float(val.replace('%', ''))
            if rate >= 90:
                return 'background-color: #D1FAE5; color: #065F46'
            elif rate >= 70:
                return 'background-color: #FEF3C7; color: #92400E'
            else:
                return 'background-color: #FEE2E2; color: #991B1B'
        except:
            return ''
    
    styled_df = df.style.applymap(style_sla, subset=['SLA %', 'FCR %', 'Res. Rate'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # =========================================================================
    # PREMIUM CHARTS ROW
    # =========================================================================
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🎯 FCR by Agent")
        st.caption("First Contact Resolution Rate")
        
        fcr_sorted = sorted(sorted_agents, key=lambda x: x[1]['fcr_rate'], reverse=True)[:10]
        
        fig = go.Figure(data=[go.Bar(
            x=[d['agent_name'][:12] for _, d in fcr_sorted],
            y=[d['fcr_rate'] for _, d in fcr_sorted],
            marker_color=[
                '#10B981' if d['fcr_rate'] >= 50 else
                '#F59E0B' if d['fcr_rate'] >= 30 else
                '#EF4444'
                for _, d in fcr_sorted
            ],
        )])
        fig.add_hline(y=50, line_dash="dash", line_color="green", annotation_text="Target 50%")
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=60),
            yaxis_range=[0, 100],
            yaxis_title="FCR %",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Utilization")
        st.caption("Workload Distribution")
        
        # Pie chart
        top_10 = sorted_agents[:10]
        others = sum(a[1]['tickets'] for a in sorted_agents[10:])
        
        labels = [d['agent_name'][:12] for _, d in top_10]
        values = [d['tickets'] for _, d in top_10]
        
        if others > 0:
            labels.append('Others')
            values.append(others)
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            textinfo='label+percent',
        )])
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        st.subheader("⚡ Ticket Touches")
        st.caption("Avg messages per ticket (lower = efficient)")
        
        touches_sorted = sorted(sorted_agents, key=lambda x: x[1]['avg_touches'])[:10]
        
        fig = go.Figure(data=[go.Bar(
            x=[d['avg_touches'] for _, d in touches_sorted],
            y=[d['agent_name'][:15] for _, d in touches_sorted],
            orientation='h',
            marker_color=[
                '#10B981' if d['avg_touches'] <= 2 else
                '#F59E0B' if d['avg_touches'] <= 4 else
                '#EF4444'
                for _, d in touches_sorted
            ],
        )])
        fig.add_vline(x=2, line_dash="dash", line_color="green", annotation_text="Efficient")
        fig.update_layout(
            height=300,
            margin=dict(l=100, r=20, t=20, b=40),
            xaxis_title="Avg Touches",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # CONSISTENCY & COMPLEXITY ANALYSIS
    # =========================================================================
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Response Consistency")
        st.caption("Lower standard deviation = more predictable response times")
        
        consistency_sorted = sorted(sorted_agents, key=lambda x: x[1]['response_consistency'])[:12]
        
        fig = go.Figure(data=[go.Bar(
            x=[d['agent_name'][:12] for _, d in consistency_sorted],
            y=[d['response_consistency'] for _, d in consistency_sorted],
            marker_color=[
                '#10B981' if d['response_consistency'] <= 5 else
                '#F59E0B' if d['response_consistency'] <= 15 else
                '#EF4444'
                for _, d in consistency_sorted
            ],
        )])
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=60),
            yaxis_title="Std Dev (hours)",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔥 Complexity Load")
        st.caption("% of High/Urgent priority tickets handled")
        
        complexity_sorted = sorted(sorted_agents, key=lambda x: x[1]['complexity'], reverse=True)[:12]
        
        fig = go.Figure(data=[go.Bar(
            x=[d['agent_name'][:12] for _, d in complexity_sorted],
            y=[d['complexity'] for _, d in complexity_sorted],
            marker_color='#6366F1',
        )])
        fig.add_hline(y=30, line_dash="dash", line_color="orange", annotation_text="High complexity")
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=60),
            yaxis_title="% High/Urgent",
            yaxis_range=[0, 100],
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # TOP PERFORMERS & NEEDS ATTENTION
    # =========================================================================
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top Performers")
        
        # Score based on multiple metrics
        scored = []
        for agent_id, data in sorted_agents:
            score = (
                data['sla_rate'] * 0.3 +
                data['fcr_rate'] * 0.25 +
                data['resolution_rate'] * 0.25 +
                max(0, 100 - data['response_consistency'] * 2) * 0.2
            )
            scored.append((agent_id, data, score))
        
        top_performers = sorted(scored, key=lambda x: x[2], reverse=True)[:5]
        
        for i, (agent_id, data, score) in enumerate(top_performers, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, '⭐')
            st.markdown(f"{medal} **{data['agent_name']}**: Score {score:.0f} | SLA {data['sla_rate']:.0f}% | FCR {data['fcr_rate']:.0f}%")
    
    with col2:
        st.subheader("⚠️ Needs Coaching")
        
        bottom_performers = sorted(scored, key=lambda x: x[2])[:5]
        
        for agent_id, data, score in bottom_performers:
            issues = []
            if data['sla_rate'] < 70:
                issues.append(f"SLA {data['sla_rate']:.0f}%")
            if data['fcr_rate'] < 20:
                issues.append(f"FCR {data['fcr_rate']:.0f}%")
            if data['response_consistency'] > 15:
                issues.append(f"Inconsistent")
            
            issue_str = " • ".join(issues) if issues else "General improvement needed"
            st.markdown(f"🔴 **{data['agent_name']}**: {issue_str}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    render_agents_page()
