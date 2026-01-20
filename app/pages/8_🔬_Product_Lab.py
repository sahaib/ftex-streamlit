"""
Product Lab Page
================
Issue-centric view for product intelligence.

Groups tickets by product, shows:
- Issue clusters per product
- Trends and patterns
- AI-generated insights
- Product health metrics
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state, get_filtered_tickets
from core.config_manager import get_config
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="Product Lab | FTEX", page_icon="🔬", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()
config = get_config()


def extract_products(tickets) -> dict:
    """Extract unique products from tickets and group tickets by product."""
    product_tickets = defaultdict(list)
    
    for ticket in tickets:
        products = set()
        
        # From custom fields
        cf = getattr(ticket, 'custom_fields', {}) or {}
        if cf.get('cf_products'):
            products.add(cf['cf_products'])
        
        # From subject parsing (e.g., "DIGITAL LOGBOOKS | ENTITY | STATUS")
        subject = getattr(ticket, 'subject', '') or ''
        parts = subject.split('|')
        if len(parts) > 1:
            product_name = parts[0].strip()
            if len(product_name) > 2:
                products.add(product_name)
        
        # From tags
        tags = getattr(ticket, 'tags', []) or []
        for tag in tags:
            if tag.startswith('product:'):
                products.add(tag.replace('product:', ''))
        
        # From type field
        ticket_type = getattr(ticket, 'type', None)
        if ticket_type and ' - ' in str(ticket_type):
            product_part = str(ticket_type).split(' - ')[0].strip()
            if len(product_part) > 2:
                products.add(product_part)
        
        # Assign to products
        if not products:
            products.add('Uncategorized')
        
        for product in products:
            product_tickets[product].append(ticket)
    
    return dict(product_tickets)


def get_issue_clusters(tickets) -> list:
    """Group tickets by common issues using conversation analysis."""
    try:
        from core.conversation_analyzer import ConversationAnalyzer
        analyzer = ConversationAnalyzer()
    except ImportError:
        return []
    
    issue_groups = defaultdict(list)
    
    for ticket in tickets:
        try:
            analysis = analyzer.analyze(ticket)
            for issue in analysis.issues[:3]:  # Top 3 issues per ticket
                # Normalize issue title
                title = issue.title.strip().lower()[:50]
                issue_groups[title].append({
                    'ticket': ticket,
                    'issue': issue,
                })
        except Exception:
            pass
    
    # Sort by frequency
    clusters = [
        {
            'title': title.title(),
            'count': len(items),
            'tickets': [i['ticket'] for i in items],
        }
        for title, items in sorted(issue_groups.items(), key=lambda x: -len(x[1]))
    ]
    
    return clusters[:20]  # Top 20 clusters


def calculate_product_health(tickets) -> dict:
    """Calculate health metrics for a product's tickets."""
    if not tickets:
        return {'score': 100, 'trend': 'stable', 'open': 0, 'resolved': 0}
    
    total = len(tickets)
    open_count = sum(1 for t in tickets if getattr(t, 'status', 0) in [2, 3])
    resolved = sum(1 for t in tickets if getattr(t, 'status', 0) in [4, 5])
    
    # Resolution times
    resolution_times = []
    for t in tickets:
        rt = getattr(t, 'resolution_time', None)
        if rt and rt > 0:
            resolution_times.append(rt)
    
    avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    # Health score
    open_ratio = open_count / total if total > 0 else 0
    score = max(0, 100 - (open_ratio * 40) - (min(avg_resolution, 48) * 0.5))
    
    return {
        'score': round(score, 1),
        'trend': 'stable',
        'open': open_count,
        'resolved': resolved,
        'avg_resolution': round(avg_resolution, 1),
    }


def render_product_lab():
    """Render the Product Lab page."""
    
    st.title("🔬 Product Lab")
    st.caption("Issue-centric intelligence across all products")
    
    # Check for data
    if not st.session_state.get('data_loaded') or not st.session_state.get('tickets'):
        st.warning("📁 Please load ticket data first from the main page.")
        return
    
    tickets = get_filtered_tickets()
    
    if not tickets:
        st.info("No tickets match current filters.")
        return
    
    # Extract products
    product_data = extract_products(tickets)
    products = sorted(product_data.keys())
    
    # Add "All Products" option
    all_options = ["All Products"] + products
    
    # Product selector
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        selected_product = st.selectbox(
            "Select Product",
            options=all_options,
            format_func=lambda x: f"{x} ({len(tickets)} tickets)" if x == "All Products" else f"{x} ({len(product_data.get(x, []))} tickets)"
        )
    
    with col2:
        view_mode = st.selectbox("View", ["Overview", "Issues", "Trends", "Tickets"])
    
    with col3:
        if st.button("🔄 Refresh Analysis"):
            st.rerun()
    
    st.divider()
    
    # Get product tickets - ALL if "All Products" selected
    if selected_product == "All Products":
        product_tickets = tickets
        display_name = "All Products"
    else:
        product_tickets = product_data.get(selected_product, [])
        display_name = selected_product
    
    if not product_tickets:
        st.info(f"No tickets for {selected_product}")
        return
    
    # Product overview metrics
    health = calculate_product_health(product_tickets)
    
    metric_cols = st.columns(5)
    
    with metric_cols[0]:
        st.metric(
            "Health Score",
            f"{health['score']}",
            help="Based on open ticket ratio and resolution times"
        )
    
    with metric_cols[1]:
        st.metric("Total Tickets", len(product_tickets))
    
    with metric_cols[2]:
        st.metric("Open Issues", health['open'])
    
    with metric_cols[3]:
        st.metric("Resolved", health['resolved'])
    
    with metric_cols[4]:
        st.metric("Avg Resolution", f"{health['avg_resolution']}h")
    
    st.divider()
    
    # View modes
    if view_mode == "Overview":
        render_overview(product_tickets, display_name)
    elif view_mode == "Issues":
        render_issues(product_tickets, display_name)
    elif view_mode == "Trends":
        render_trends(product_tickets, display_name)
    else:
        render_tickets_list(product_tickets, display_name)


def render_overview(tickets, product_name):
    """Render product overview."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Issue Clusters")
        
        clusters = get_issue_clusters(tickets)
        
        if clusters:
            for cluster in clusters[:10]:
                with st.expander(f"🔹 {cluster['title']} ({cluster['count']} tickets)"):
                    for t in cluster['tickets'][:5]:
                        st.write(f"• #{t.id}: {t.subject[:50]}...")
                    if len(cluster['tickets']) > 5:
                        st.caption(f"...and {len(cluster['tickets']) - 5} more")
        else:
            st.info("Run conversation analysis to see issue clusters")
    
    with col2:
        st.subheader("🏢 Entities Affected")
        
        entity_counts = defaultdict(int)
        for t in tickets:
            entity = getattr(t, 'entity_name', None)
            if not entity:
                cf = getattr(t, 'custom_fields', {}) or {}
                entity = cf.get('cf_vesselname') or 'Unknown'
            entity_counts[entity] += 1
        
        sorted_entities = sorted(entity_counts.items(), key=lambda x: -x[1])[:10]
        
        for entity, count in sorted_entities:
            st.write(f"• **{entity}**: {count} tickets")
        
        st.divider()
        
        st.subheader("👥 Top Requesters")
        
        requester_counts = defaultdict(int)
        for t in tickets:
            requester = getattr(t, 'requester_name', None) or 'Unknown'
            requester_counts[requester] += 1
        
        sorted_requesters = sorted(requester_counts.items(), key=lambda x: -x[1])[:5]
        
        for requester, count in sorted_requesters:
            st.write(f"• {requester}: {count}")
    
    # AI Product Insights
    st.divider()
    st.subheader("🧠 AI Product Intelligence")
    
    if st.button("✨ Generate AI Insights", type="primary"):
        generate_product_insights(tickets, product_name)


def generate_product_insights(tickets, product_name):
    """Generate AI-powered insights for a product with progress tracking."""
    
    # Check cache first
    cache_key = f"product_insights_{product_name}_{len(tickets)}"
    
    try:
        from core.kv_cache import get_cache
        kv_cache = get_cache()
        
        # Check if we have cached insights
        cached = kv_cache._meta.get(cache_key)
        if cached:
            st.info("💾 Showing cached insights. Click again to regenerate.")
            st.markdown("### 📋 AI Analysis")
            st.markdown(cached)
            return
    except:
        kv_cache = None
    
    # Progress container
    progress_container = st.container()
    
    with progress_container:
        progress = st.progress(0)
        status = st.empty()
        
        # Step 1: Prepare data
        status.text("📊 Step 1/4: Analyzing issue clusters...")
        progress.progress(0.1)
        
        clusters = get_issue_clusters(tickets)
        open_count = sum(1 for t in tickets if getattr(t, 'status', 0) in [2, 3])
        resolved_count = len(tickets) - open_count
        
        progress.progress(0.25)
        status.text("📝 Step 2/4: Building context...")
        
        # Build summary for AI
        issue_summary = "\n".join([
            f"- {c['title']}: {c['count']} tickets"
            for c in clusters[:10]
        ]) if clusters else "No issues extracted yet"
        
        # Get sample subjects
        sample_subjects = [getattr(t, 'subject', '') for t in tickets[:10]]
        
        progress.progress(0.4)
        status.text("🤖 Step 3/4: Calling AI model...")
        
        prompt = f"""Analyze this product's support patterns and provide actionable insights.

Product: {product_name}
Total Tickets: {len(tickets)}
Open: {open_count}
Resolved: {resolved_count}

Top Issue Clusters:
{issue_summary}

Sample Ticket Subjects:
{chr(10).join(f'- {s}' for s in sample_subjects)}

Provide:
1. **Key Patterns**: What are the main themes in these tickets?
2. **Root Causes**: What might be causing these issues?
3. **Recommendations**: How can we reduce ticket volume?
4. **Priority Actions**: What should be addressed immediately?

Be concise and actionable. Focus on patterns, not individual tickets."""

        try:
            from core.ai_service import get_ai_service
            from core.config_manager import get_config
            
            cfg = get_config()
            
            # Build the AI config structure expected by get_ai_service
            ai_config = {
                'provider': cfg.get('ai', 'provider', default='ollama'),
                'ollama': {
                    'base_url': cfg.get('ai', 'ollama', 'base_url', default='http://localhost:11434'),
                    'model': cfg.get('ai', 'ollama', 'model', default='qwen3:14b'),
                    'temperature': cfg.get('ai', 'ollama', 'temperature', default=0.3),
                },
                'openai': {
                    'api_key': cfg.get('ai', 'openai', 'api_key', default=''),
                    'model': cfg.get('ai', 'openai', 'model', default='gpt-4o-mini'),
                },
            }
            
            ai = get_ai_service(ai_config)
            
            response = ai.call(prompt)
            
            progress.progress(0.9)
            status.text("✨ Step 4/4: Formatting results...")
            
            if response and response.strip():
                # Cache the result
                if kv_cache:
                    kv_cache._meta[cache_key] = response
                    kv_cache._save_meta()
                
                progress.progress(1.0)
                status.empty()
                progress.empty()
                
                st.markdown("### 📋 AI Analysis")
                st.markdown(response)
                st.caption(f"💾 Results cached • {len(tickets)} tickets analyzed")
            else:
                progress.empty()
                status.empty()
                # Show detailed error
                error_msg = ai.last_error if hasattr(ai, 'last_error') else "No response received"
                st.warning(f"AI returned empty. Error: {error_msg}")
                st.info(f"Debug: Provider={ai.config.provider}, Model={ai.config.model}, URL={ai.config.base_url}")
                
        except ImportError as e:
            progress.empty()
            status.empty()
            st.info(f"💡 AI service import error: {e}")
        except Exception as e:
            progress.empty()
            status.empty()
            st.error(f"Analysis error: {str(e)}")


def render_issues(tickets, product_name):
    """Render detailed issue analysis."""
    st.subheader(f"🔍 Issue Deep Dive - {product_name}")
    
    clusters = get_issue_clusters(tickets)
    
    if not clusters:
        st.info("💡 Run conversation analysis to extract issues from ticket threads.")
        return
    
    # Issue selector
    issue_names = [c['title'] for c in clusters]
    selected_issue = st.selectbox("Select Issue", issue_names)
    
    # Find selected cluster
    cluster = next((c for c in clusters if c['title'] == selected_issue), None)
    
    if cluster:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### {cluster['title']}")
            st.metric("Affected Tickets", cluster['count'])
            
            st.markdown("#### Sample Tickets")
            for t in cluster['tickets'][:10]:
                status_icon = "🟢" if t.status in [4, 5] else "🟡"
                st.write(f"{status_icon} **#{t.id}**: {t.subject[:60]}")
        
        with col2:
            st.markdown("#### Quick Stats")
            open_in_cluster = sum(1 for t in cluster['tickets'] if t.status in [2, 3])
            st.write(f"• Open: {open_in_cluster}")
            st.write(f"• Resolved: {cluster['count'] - open_in_cluster}")
            
            # Get entities affected
            entities = set()
            for t in cluster['tickets']:
                entity = getattr(t, 'entity_name', None)
                if entity:
                    entities.add(entity)
            
            if entities:
                st.markdown("#### Entities Affected")
                for e in list(entities)[:5]:
                    st.write(f"• {e}")


def render_trends(tickets, product_name):
    """Render trend analysis."""
    st.subheader(f"📈 Trends - {product_name}")
    
    # Group by week
    weekly = defaultdict(int)
    for t in tickets:
        created = getattr(t, 'created_at', None)
        if created:
            try:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                week = created.strftime('%Y-W%W')
                weekly[week] += 1
            except:
                pass
    
    if weekly:
        import pandas as pd
        
        df = pd.DataFrame([
            {'Week': k, 'Tickets': v}
            for k, v in sorted(weekly.items())[-12:]  # Last 12 weeks
        ])
        
        st.bar_chart(df.set_index('Week'))
    else:
        st.info("Not enough data for trends")
    
    # Priority breakdown
    st.markdown("#### Priority Distribution")
    priority_counts = defaultdict(int)
    for t in tickets:
        priority = getattr(t, 'priority_name', 'Unknown')
        priority_counts[priority] += 1
    
    for priority, count in sorted(priority_counts.items(), key=lambda x: -x[1]):
        pct = count / len(tickets) * 100
        st.write(f"• **{priority}**: {count} ({pct:.1f}%)")


def render_tickets_list(tickets, product_name):
    """Render ticket list."""
    st.subheader(f"📋 All Tickets - {product_name}")
    
    # Sort options
    sort_by = st.selectbox("Sort by", ["Created (newest)", "Created (oldest)", "Priority", "Status"])
    
    sorted_tickets = list(tickets)
    if sort_by == "Created (newest)":
        sorted_tickets.sort(key=lambda t: str(getattr(t, 'created_at', '')), reverse=True)
    elif sort_by == "Created (oldest)":
        sorted_tickets.sort(key=lambda t: str(getattr(t, 'created_at', '')))
    elif sort_by == "Priority":
        sorted_tickets.sort(key=lambda t: getattr(t, 'priority', 0), reverse=True)
    elif sort_by == "Status":
        sorted_tickets.sort(key=lambda t: getattr(t, 'status', 0))
    
    # Display
    for t in sorted_tickets[:50]:
        status_icons = {2: "🟡", 3: "🟠", 4: "🟢", 5: "⚫"}
        status_icon = status_icons.get(getattr(t, 'status', 0), "⚪")
        
        priority_icons = {1: "", 2: "🔵", 3: "🟠", 4: "🔴"}
        priority_icon = priority_icons.get(getattr(t, 'priority', 0), "")
        
        st.write(f"{status_icon} {priority_icon} **#{t.id}**: {t.subject[:60]}")
    
    if len(sorted_tickets) > 50:
        st.caption(f"Showing 50 of {len(sorted_tickets)} tickets")


# Run the page
if __name__ == "__main__":
    render_product_lab()
else:
    render_product_lab()
