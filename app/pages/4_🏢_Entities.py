"""
Entities Page
=============
Analysis by primary entity (customer, vessel, site, product).
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import Counter, defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state, apply_filters
from core.config_manager import get_config
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="Entities | FTEX", page_icon="🏢", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()
config = get_config()


def render_entities_page():
    """Render the entities page."""
    
    # Get entity type from config
    entity_type = config.get('industry', 'primary_entity', default='customer')
    entity_label = entity_type.title()
    entity_plural = f"{entity_label}s"
    
    st.title(f"🏢 {entity_plural}")
    st.caption(f"Analysis by {entity_label.lower()}")
    
    # Check for data
    if not st.session_state.get('data_loaded'):
        st.warning("⚠️ No data loaded. Please upload a file from the home page.")
        st.page_link("main.py", label="← Go to Home", icon="🏠")
        return
    
    tickets = apply_filters(st.session_state.tickets)
    
    if not tickets:
        st.info("No tickets match the current filters.")
        return
    
    # Analyze by entity
    entity_data = analyze_entities(tickets, entity_type)
    
    if not entity_data:
        st.info(f"No {entity_label.lower()} data available.")
        return
    
    # =========================================================================
    # SUMMARY KPIs
    # =========================================================================
    st.markdown("---")
    
    # Check for AI deep analysis
    deep_analysis = st.session_state.get('deep_analysis', {})
    sentiment_data = deep_analysis.get('sentiment', {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(f"Total {entity_plural}", len(entity_data))
    
    with col2:
        active = sum(1 for d in entity_data.values() if d['open'] > 0)
        st.metric("With Open Tickets", active)
    
    with col3:
        at_risk = sum(1 for d in entity_data.values() if d['stale'] > 0)
        st.metric("At Risk", at_risk)
    
    with col4:
        total_tickets = sum(d['tickets'] for d in entity_data.values())
        avg = total_tickets / len(entity_data) if entity_data else 0
        st.metric("Avg Tickets", f"{avg:.1f}")
    
    with col5:
        # AI Churn Risk (if deep analysis available)
        if sentiment_data:
            # Calculate churn risk based on sentiment
            churn_high = 0
            for name, data in entity_data.items():
                entity_tickets = [t for t in tickets if (t.entity_name or t.company_name) == name]
                negative = sum(1 for t in entity_tickets 
                             if t.id in sentiment_data and 
                             sentiment_data[t.id].get('label') in ['frustrated', 'angry', 'negative'])
                if negative >= 2 or (data['stale'] >= 2 and data['open'] >= 3):
                    churn_high += 1
            st.metric("🔥 Churn Risk", churn_high, delta="AI detected", delta_color="inverse" if churn_high > 0 else "normal")
        else:
            st.metric("Churn Risk", "N/A", delta="Run AI Analysis")
    
    st.markdown("---")
    
    # =========================================================================
    # TABS
    # =========================================================================
    tabs = st.tabs(["📊 Overview", "🏆 Top Entities", "⚠️ At Risk", "📈 Trends"])
    
    # =========================================================================
    # TAB 1: OVERVIEW
    # =========================================================================
    with tabs[0]:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"📊 {entity_plural} by Ticket Volume")
            
            top_entities = sorted(entity_data.items(), key=lambda x: x[1]['tickets'], reverse=True)[:15]
            
            fig = go.Figure(data=[go.Bar(
                x=[e[1]['tickets'] for e in top_entities],
                y=[e[0][:25] for e in top_entities],
                orientation='h',
                marker_color='#1F4E79',
            )])
            fig.update_layout(
                height=400,
                xaxis_title="Tickets",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader(f"🎯 {entity_label} Health Distribution")
            
            health_counts = Counter(d['health'] for d in entity_data.values())
            
            colors = {
                '🟢 Good': '#10B981',
                '🟡 Fair': '#F59E0B',
                '🟠 Needs Attention': '#F97316',
                '🔴 Critical': '#EF4444',
            }
            
            fig = go.Figure(data=[go.Pie(
                labels=list(health_counts.keys()),
                values=list(health_counts.values()),
                hole=0.4,
                marker=dict(colors=[colors.get(h, '#6B7280') for h in health_counts.keys()]),
            )])
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Entity table
        st.subheader(f"📋 All {entity_plural}")
        
        import pandas as pd
        
        table_data = []
        for name, data in sorted(entity_data.items(), key=lambda x: x[1]['tickets'], reverse=True):
            table_data.append({
                entity_label: name[:35],
                'Tickets': data['tickets'],
                'Open': data['open'],
                'Stale': data['stale'],
                'High Priority': data['high_priority'],
                'Avg Resolution (hrs)': data['avg_resolution'],
                'Health': data['health'],
            })
        
        df = pd.DataFrame(table_data)
        
        # Style
        def style_health(val):
            if '🟢' in val:
                return 'background-color: #D1FAE5'
            elif '🟡' in val:
                return 'background-color: #FEF3C7'
            elif '🟠' in val:
                return 'background-color: #FFEDD5'
            elif '🔴' in val:
                return 'background-color: #FEE2E2'
            return ''
        
        styled_df = df.style.applymap(style_health, subset=['Health'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # =========================================================================
    # TAB 2: TOP ENTITIES
    # =========================================================================
    with tabs[1]:
        st.subheader(f"🏆 Top {entity_plural} by Volume")
        
        top_10 = sorted(entity_data.items(), key=lambda x: x[1]['tickets'], reverse=True)[:10]
        
        for i, (name, data) in enumerate(top_10, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
            
            with st.expander(f"{medal} {name} ({data['tickets']} tickets)", expanded=(i <= 3)):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Tickets", data['tickets'])
                with col2:
                    st.metric("Open", data['open'])
                with col3:
                    st.metric("Stale", data['stale'])
                with col4:
                    st.metric("Health", data['health'])
                
                # Categories breakdown
                if data.get('categories'):
                    st.markdown("**Top Categories:**")
                    for cat, count in data['categories'].most_common(3):
                        st.markdown(f"- {cat}: {count}")
    
    # =========================================================================
    # TAB 3: AT RISK
    # =========================================================================
    with tabs[2]:
        st.subheader(f"⚠️ At-Risk {entity_plural}")
        st.caption(f"{entity_plural} with stale tickets or low health scores")
        
        at_risk_entities = [
            (name, data) for name, data in entity_data.items()
            if data['stale'] > 0 or '🔴' in data['health'] or '🟠' in data['health']
        ]
        at_risk_entities.sort(key=lambda x: x[1]['stale'], reverse=True)
        
        if at_risk_entities:
            for name, data in at_risk_entities[:20]:
                severity = '🔴' if data['stale'] >= 3 or '🔴' in data['health'] else '🟠'
                
                with st.expander(f"{severity} {name} - {data['stale']} stale, {data['open']} open"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Health:** {data['health']}")
                        st.markdown(f"**Total Tickets:** {data['tickets']}")
                        st.markdown(f"**Stale Tickets:** {data['stale']}")
                    
                    with col2:
                        st.markdown(f"**Open Tickets:** {data['open']}")
                        st.markdown(f"**High Priority:** {data['high_priority']}")
                        st.markdown(f"**Avg Resolution:** {data['avg_resolution']:.1f} hrs")
                    
                    st.warning("⚠️ Requires immediate attention")
        else:
            st.success(f"✅ No at-risk {entity_plural.lower()} detected!")
    
    # =========================================================================
    # TAB 4: TRENDS
    # =========================================================================
    with tabs[3]:
        st.subheader(f"📈 {entity_label} Ticket Trends")
        
        # Weekly trend for top entities
        top_5 = sorted(entity_data.items(), key=lambda x: x[1]['tickets'], reverse=True)[:5]
        
        # Build weekly data
        weekly_data = defaultdict(lambda: defaultdict(int))
        for t in tickets:
            if t.created_at:
                entity = t.entity_name or t.company_name or '(Unknown)'
                week = t.created_at.strftime('%Y-W%W')
                weekly_data[entity][week] += 1
        
        # Get all weeks
        all_weeks = sorted(set(
            t.created_at.strftime('%Y-W%W') 
            for t in tickets if t.created_at
        ))[-12:]  # Last 12 weeks
        
        fig = go.Figure()
        
        for name, _ in top_5:
            fig.add_trace(go.Scatter(
                x=all_weeks,
                y=[weekly_data[name].get(w, 0) for w in all_weeks],
                name=name[:20],
                mode='lines+markers',
            ))
        
        fig.update_layout(
            height=400,
            xaxis_title="Week",
            yaxis_title="Tickets",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)


def analyze_entities(tickets, entity_type):
    """Analyze tickets by entity."""
    entity_data = defaultdict(lambda: {
        'tickets': 0,
        'open': 0,
        'stale': 0,
        'high_priority': 0,
        'resolution_times': [],
        'categories': Counter(),
    })
    
    for t in tickets:
        # Determine entity name based on type
        if entity_type == 'vessel':
            entity = t.entity_name or '(Unknown)'
        elif entity_type == 'customer':
            entity = t.company_name or '(Unknown)'
        else:
            entity = t.entity_name or t.company_name or '(Unknown)'
        
        entity_data[entity]['tickets'] += 1
        
        if t.is_open:
            entity_data[entity]['open'] += 1
        
        if t.is_open and t.days_open >= 15:
            entity_data[entity]['stale'] += 1
        
        if t.priority >= 3:
            entity_data[entity]['high_priority'] += 1
        
        if t.resolution_time:
            entity_data[entity]['resolution_times'].append(t.resolution_time)
        
        if t.category:
            entity_data[entity]['categories'][t.category] += 1
    
    # Calculate health scores and averages
    for entity, data in entity_data.items():
        # Average resolution
        if data['resolution_times']:
            data['avg_resolution'] = round(
                sum(data['resolution_times']) / len(data['resolution_times']), 1
            )
        else:
            data['avg_resolution'] = 0
        
        # Health score
        score = 100
        score -= data['stale'] * 15
        score -= data['high_priority'] * 3
        if data['open'] > data['tickets'] * 0.3:
            score -= 10
        
        if score >= 80:
            data['health'] = '🟢 Good'
        elif score >= 60:
            data['health'] = '🟡 Fair'
        elif score >= 40:
            data['health'] = '🟠 Needs Attention'
        else:
            data['health'] = '🔴 Critical'
    
    return dict(entity_data)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    render_entities_page()
