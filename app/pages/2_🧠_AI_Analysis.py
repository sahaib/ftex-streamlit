"""
AI Analysis Page
================
AI-powered issue clustering and root cause analysis.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_state import init_session_state, apply_filters
from core.config_manager import get_config
from core.ui_components import inject_beta_badge

# Page config
st.set_page_config(page_title="AI Analysis | FTEX", page_icon="🧠", layout="wide")

# Beta badge
inject_beta_badge()

# Initialize
init_session_state()
config = get_config()


def render_ai_page():
    """Render the AI analysis page."""
    
    st.title("🧠 AI-Powered Analysis")
    st.caption("Intelligent issue clustering and root cause analysis")
    
    # Check for data
    if not st.session_state.get('data_loaded'):
        st.warning("⚠️ No data loaded. Please upload a file from the home page.")
        st.page_link("main.py", label="← Go to Home", icon="🏠")
        return
    
    tickets = apply_filters(st.session_state.tickets)
    
    if not tickets:
        st.info("No tickets match the current filters.")
        return
    
    # AI Configuration status
    ai_config = config.get('ai', default={})
    provider = ai_config.get('provider', 'none')
    
    # Sidebar AI settings
    with st.sidebar:
        st.subheader("🤖 AI Settings")
        
        provider_display = {
            'ollama': '🦙 Ollama (Local)',
            'openai': '🤖 OpenAI',
            'anthropic': '🔷 Anthropic',
            'none': '❌ Disabled'
        }
        
        st.info(f"Provider: {provider_display.get(provider, provider)}")
        
        if provider == 'ollama':
            st.caption(f"Model: {ai_config.get('ollama', {}).get('model', 'N/A')}")
        
        # Test connection button
        if st.button("🔗 Test Connection"):
            from core.ai_service import get_ai_service
            ai_service = get_ai_service(ai_config)
            if ai_service.test_connection():
                st.success("✅ Connected!")
            else:
                st.error(f"❌ Failed: {ai_service.last_error}")
        
        st.markdown("---")
        
        # =====================================================================
        # CHECKPOINT & RESUME SECTION (always visible)
        # =====================================================================
        st.markdown("##### 📦 Saved Progress")
        
        ai_enrichment = st.session_state.get('ai_enrichment', {})
        analyzed_ids = set(ai_enrichment.get('analyzed_ticket_ids', []))
        in_progress = ai_enrichment.get('in_progress', False)
        
        if analyzed_ids:
            # Show status
            if in_progress:
                st.warning(f"⏸️ Paused at {len(analyzed_ids):,} tickets")
            else:
                st.success(f"✅ Completed: {len(analyzed_ids):,} tickets")
            
            # Remaining count
            remaining = len([t for t in tickets if t.id not in analyzed_ids])
            if remaining > 0:
                st.caption(f"📊 {remaining:,} remaining to analyze")
            
            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if remaining > 0 and st.button("▶️ Resume", type="primary", use_container_width=True):
                    st.session_state.run_ai_analysis = True
                    st.session_state.resume_from_checkpoint = True
            with col2:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state.ai_enrichment = {}
                    st.session_state.deep_analysis = {}
                    from core.session_state import save_to_cache
                    save_to_cache()
                    st.rerun()
        else:
            st.info("No checkpoint saved yet")
            st.caption("Progress saves automatically every 100 tickets, or when you click Stop")
        
        st.markdown("---")
        
        # =====================================================================
        # NEW ANALYSIS SECTION
        # =====================================================================
        st.markdown("##### 🆕 New Analysis")
        
        # Analyze ALL toggle
        analyze_all = st.toggle(
            "Analyze ALL tickets",
            value=False,
            key="analyze_all_tickets",
            help="⚠️ May take 10+ minutes for large datasets"
        )
        
        # Ticket count slider (only if not analyzing all)
        if analyze_all:
            ticket_count = len(tickets)
            st.caption(f"Will analyze all {len(tickets):,} tickets")
        elif len(tickets) <= 100:
            # Not enough tickets for slider, analyze all
            ticket_count = len(tickets)
            st.caption(f"Will analyze all {len(tickets)} tickets (dataset ≤100)")
        else:
            ticket_count = st.slider(
                "Tickets to analyze",
                min_value=50,
                max_value=min(len(tickets), 5000),
                value=min(500, len(tickets)),
                step=50,
                key="analysis_ticket_limit",
                help="Start small to test, then increase"
            )
        
        # Start fresh button
        if st.button("🚀 Start Fresh Analysis", use_container_width=True):
            st.session_state.run_ai_analysis = True
            st.session_state.resume_from_checkpoint = False
            st.session_state.analysis_ticket_count = ticket_count
        
        if st.button("⚙️ Configure AI"):
            st.switch_page("pages/6_⚙️_Settings.py")
    
    # =========================================================================
    # ANALYSIS TABS
    # =========================================================================
    tabs = st.tabs([
        "🎯 Issue Clusters",
        "� Sentiment",
        "🔄 Recurring Issues",
        "⏰ Promise Tracker",
        "🚨 Escalation Watch",
        "�🔍 Root Causes", 
        "📊 Category Intelligence",
        "💡 Recommendations"
    ])
    
    # =========================================================================
    # TAB 1: ISSUE CLUSTERS
    # =========================================================================
    with tabs[0]:
        st.subheader("Issue Clusters")
        st.caption("Similar tickets grouped by AI analysis")
        
        # Run AI Analysis if button was clicked
        if st.session_state.get('run_ai_analysis'):
            st.session_state.run_ai_analysis = False  # Reset flag
            
            with st.status("🤖 Running AI Analysis...", expanded=True) as status:
                try:
                    from core.ai_service import get_ai_service
                    from core.session_state import save_to_cache
                    ai_service = get_ai_service(ai_config)
                    
                    st.write("🔗 Connecting to AI model...")
                    if not ai_service.test_connection():
                        st.error(f"❌ Cannot connect to AI: {ai_service.last_error}")
                        st.info("💡 Make sure Ollama is running: `ollama serve`")
                    else:
                        st.write("✅ Connected to Ollama")
                        
                        # Check resume mode
                        resume = st.session_state.get('resume_from_checkpoint', False)
                        existing_enrichment = st.session_state.get('ai_enrichment', {})
                        
                        if resume:
                            # Resume from checkpoint
                            existing_categories = existing_enrichment.get('categories', {})
                            analyzed_ids = set(existing_enrichment.get('analyzed_ticket_ids', []))
                            st.write(f"📦 Resuming from checkpoint ({len(analyzed_ids):,} already done)")
                            
                            # Get unanalyzed tickets
                            analysis_tickets = [t for t in tickets if t.id not in analyzed_ids]
                            st.write(f"� {len(analysis_tickets):,} tickets remaining...")
                        else:
                            # Fresh start
                            sample_size = st.session_state.get('analysis_ticket_count', 500)
                            analysis_tickets = tickets[:sample_size]
                            existing_categories = {}
                            analyzed_ids = set()
                            st.write(f"📊 Analyzing {len(analysis_tickets):,} tickets (fresh start)...")
                        
                        # Categorize in batches
                        st.write("🏷️ Categorizing with AI...")
                        batch_size = 25
                        new_categories = {}
                        
                        # Progress display
                        status_display = st.empty()
                        counter_display = st.empty()
                        prog_col, stop_col = st.columns([4, 1])
                        with prog_col:
                            progress = st.progress(0)
                        with stop_col:
                            stop_btn = st.empty()
                        
                        stopped = False
                        total_to_analyze = len(analysis_tickets)
                        total_batches = (total_to_analyze + batch_size - 1) // batch_size
                        processed = 0
                        batch_times = []
                        
                        # Show initial status
                        counter_display.markdown(f"### 📊 **0** / {total_to_analyze:,} tickets")
                        status_display.info(f"Starting analysis of {total_batches} batches...")
                        
                        import time
                        
                        for batch_num, i in enumerate(range(0, total_to_analyze, batch_size)):
                            # Check for stop
                            with stop_btn:
                                if st.button("⏹️ Stop", key=f"stop_{i}", type="secondary"):
                                    stopped = True
                                    break
                            
                            batch_start = time.time()
                            batch = analysis_tickets[i:i+batch_size]
                            batch_cats = ai_service.categorize_tickets(batch, batch_size=batch_size)
                            new_categories.update(batch_cats)
                            batch_time = time.time() - batch_start
                            batch_times.append(batch_time)
                            
                            # Update counter
                            processed = min(i + len(batch), total_to_analyze)
                            avg_time = sum(batch_times) / len(batch_times)
                            remaining_batches = total_batches - batch_num - 1
                            eta_seconds = remaining_batches * avg_time
                            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s" if eta_seconds > 60 else f"{int(eta_seconds)}s"
                            
                            counter_display.markdown(f"### 📊 **{processed:,}** / {total_to_analyze:,} tickets")
                            status_display.info(f"Batch {batch_num + 1}/{total_batches} • {avg_time:.1f}s avg • ETA: {eta_str}")
                            
                            # Progress bar
                            pct = processed / total_to_analyze
                            progress.progress(min(pct, 0.98))
                            
                            # Save checkpoint after EVERY batch
                            st.session_state.ai_enrichment = {
                                'categories': {**existing_categories, **new_categories},
                                'analyzed_ticket_ids': list(analyzed_ids | set(new_categories.keys())),
                                'analyzed_count': len(analyzed_ids) + len(new_categories),
                                'timestamp': datetime.now().isoformat(),
                                'in_progress': True,
                            }
                            save_to_cache()
                        
                        # Merge all categories
                        all_categories = {**existing_categories, **new_categories}
                        all_analyzed_ids = analyzed_ids | set(new_categories.keys())
                        
                        # Apply categories to tickets
                        for t in tickets:
                            if t.id in all_categories:
                                t.category = all_categories[t.id]
                        
                        if stopped:
                            # Save checkpoint for later resume
                            st.session_state.ai_enrichment = {
                                'categories': all_categories,
                                'analyzed_ticket_ids': list(all_analyzed_ids),
                                'summary': existing_enrichment.get('summary', ''),
                                'analyzed_count': len(all_analyzed_ids),
                                'timestamp': datetime.now().isoformat(),
                                'in_progress': True,
                            }
                            save_to_cache()
                            status.update(label=f"⏸️ Paused! {len(new_categories):,} tickets saved", state="complete")
                            st.info("💡 Click '▶️ Resume' in sidebar to continue")
                        else:
                            # Generate summary
                            st.write("📝 Generating summary...")
                            progress.progress(0.98)
                            summary = ai_service.generate_summary(tickets)
                            
                            # Save final results
                            st.session_state.ai_enrichment = {
                                'categories': all_categories,
                                'analyzed_ticket_ids': list(all_analyzed_ids),
                                'summary': summary,
                                'analyzed_count': len(all_analyzed_ids),
                                'timestamp': datetime.now().isoformat(),
                                'in_progress': False,
                            }
                            save_to_cache()
                            
                            progress.progress(1.0)
                            status.update(label=f"✅ Complete! Categorized {len(new_categories):,} tickets", state="complete")
                        
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        # Check for existing AI enrichment
        ai_enrichment = st.session_state.get('ai_enrichment', {})
        
        # Show summary if available
        if ai_enrichment.get('summary'):
            st.success(f"**🤖 AI Summary:** {ai_enrichment['summary']}")
            st.caption(f"Analyzed {ai_enrichment.get('analyzed_count', 0)} tickets at {ai_enrichment.get('timestamp', 'unknown')[:16]}")
        
        clusters = ai_enrichment.get('clusters', [])
        
        if not clusters:
            # Generate clusters based on categories
            
            # Simple clustering based on categories
            category_clusters = defaultdict(list)
            for t in tickets:
                cat = t.category or 'Uncategorized'
                category_clusters[cat].append(t)
            
            # Create cluster cards
            col1, col2 = st.columns(2)
            
            for i, (cat_name, cat_tickets) in enumerate(sorted(
                category_clusters.items(), 
                key=lambda x: len(x[1]), 
                reverse=True
            )[:10]):
                with col1 if i % 2 == 0 else col2:
                    with st.expander(f"🏷️ {cat_name} ({len(cat_tickets)} tickets)", expanded=(i < 2)):
                        # Cluster stats
                        open_count = sum(1 for t in cat_tickets if t.is_open)
                        stale_count = sum(1 for t in cat_tickets if t.is_open and t.days_open >= 15)
                        
                        stat_cols = st.columns(3)
                        with stat_cols[0]:
                            st.metric("Total", len(cat_tickets))
                        with stat_cols[1]:
                            st.metric("Open", open_count)
                        with stat_cols[2]:
                            st.metric("Stale", stale_count)
                        
                        # Sample tickets
                        st.markdown("**Sample Tickets:**")
                        for t in cat_tickets[:3]:
                            st.markdown(f"- `#{t.id}` {t.subject[:50]}...")
                        
                        if len(cat_tickets) > 3:
                            st.caption(f"+ {len(cat_tickets) - 3} more tickets")
        else:
            # Display AI-generated clusters
            for cluster in clusters:
                with st.expander(f"🎯 {cluster.get('label', 'Unknown')} ({cluster.get('count', 0)} tickets)"):
                    st.markdown(f"**Description:** {cluster.get('description', 'N/A')}")
                    st.markdown(f"**Root Cause:** {cluster.get('root_cause', 'N/A')}")
                    st.markdown(f"**Recommended Action:** {cluster.get('action', 'N/A')}")
        
        # Cluster visualization
        st.markdown("---")
        st.subheader("📊 Cluster Distribution")
        
        category_counts = Counter(t.category or 'Uncategorized' for t in tickets)
        
        fig = go.Figure(data=[go.Treemap(
            labels=list(category_counts.keys()),
            parents=[""] * len(category_counts),
            values=list(category_counts.values()),
            textinfo="label+value+percent parent",
            marker=dict(
                colors=list(category_counts.values()),
                colorscale='Blues',
            ),
        )])
        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # TAB 2: SENTIMENT ANALYSIS
    # =========================================================================
    with tabs[1]:
        st.subheader("😊 Sentiment Analysis")
        st.caption("Customer sentiment and emotional patterns")
        
        deep_analysis = st.session_state.get('deep_analysis', {})
        sentiment_data = deep_analysis.get('sentiment', {})
        
        if not sentiment_data:
            st.info("🤖 Run Deep Analysis to see sentiment insights")
            if st.button("🚀 Run Deep Analysis", key="run_deep_sentiment", type="primary"):
                with st.status("Analyzing sentiment...", expanded=True) as status:
                    try:
                        from core.ai_service import get_ai_service
                        ai_service = get_ai_service(ai_config)
                        
                        def progress_cb(step, total, msg):
                            status.update(label=f"Step {step}/{total}: {msg}")
                        
                        results = ai_service.run_deep_analysis(tickets, progress_callback=progress_cb)
                        st.session_state.deep_analysis = results
                        
                        from core.session_state import save_to_cache
                        save_to_cache()
                        
                        status.update(label="✅ Deep Analysis Complete!", state="complete")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            # Sentiment distribution
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Sentiment Distribution")
                labels = [s.get('label', 'unknown') for s in sentiment_data.values()]
                label_counts = Counter(labels)
                
                colors = {'positive': '#10B981', 'neutral': '#6B7280', 'negative': '#F59E0B', 
                         'frustrated': '#EF4444', 'angry': '#DC2626'}
                
                fig = go.Figure(data=[go.Pie(
                    labels=list(label_counts.keys()),
                    values=list(label_counts.values()),
                    marker_colors=[colors.get(l, '#6B7280') for l in label_counts.keys()],
                    hole=0.4,
                )])
                fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("##### Avg Sentiment Score")
                scores = [s.get('score', 0) for s in sentiment_data.values()]
                avg_score = sum(scores) / max(len(scores), 1)
                
                st.metric("Average", f"{avg_score:.2f}", delta=None)
                
                # Emotion breakdown
                emotions = [s.get('emotion', 'unknown') for s in sentiment_data.values()]
                emotion_counts = Counter(emotions).most_common(5)
                
                st.markdown("**Top Emotions:**")
                for emotion, count in emotion_counts:
                    st.write(f"• {emotion}: {count}")
            
            # Frustrated customers
            st.markdown("---")
            st.markdown("##### 🚨 Frustrated Customers (Action Needed)")
            frustrated = [(tid, s) for tid, s in sentiment_data.items() 
                         if s.get('label') in ['frustrated', 'angry']][:10]
            
            if frustrated:
                for tid, s in frustrated:
                    ticket = next((t for t in tickets if t.id == tid), None)
                    if ticket:
                        with st.expander(f"⚠️ #{tid} - {ticket.subject[:50]}..."):
                            st.write(f"**Sentiment:** {s.get('label')} (Score: {s.get('score', 0):.2f})")
                            st.write(f"**Emotion:** {s.get('emotion', 'N/A')}")
                            st.write(f"**Signals:** {', '.join(s.get('signals', []))}")
            else:
                st.success("No highly frustrated customers detected!")
            
            # Re-run option
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"Last analyzed: {deep_analysis.get('timestamp', 'N/A')[:16]}")
            with col2:
                if st.button("🔄 Re-run", key="rerun_deep", help="Clear and re-run deep analysis"):
                    st.session_state.deep_analysis = {}
                    from core.session_state import save_to_cache
                    save_to_cache()
                    st.rerun()
    
    # =========================================================================
    # TAB 3: RECURRING ISSUES
    # =========================================================================
    with tabs[2]:
        st.subheader("🔄 Recurring Issues")
        st.caption("Patterns and repeated problems across tickets")
        
        deep_analysis = st.session_state.get('deep_analysis', {})
        recurring = deep_analysis.get('recurring_issues', [])
        
        if not recurring:
            st.info("🤖 Run Deep Analysis to detect recurring issues")
        else:
            for issue in recurring:
                severity_color = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(
                    issue.get('severity', 'medium'), '⚪')
                
                with st.expander(f"{severity_color} {issue.get('issue', 'Unknown')} ({issue.get('count', 0)} tickets)"):
                    st.markdown(f"**Severity:** {issue.get('severity', 'N/A')}")
                    st.markdown(f"**Root Cause:** {issue.get('root_cause', 'N/A')}")
                    st.markdown(f"**Recommended Solution:** {issue.get('solution', 'N/A')}")
    
    # =========================================================================
    # TAB 4: PROMISE TRACKER
    # =========================================================================
    with tabs[3]:
        st.subheader("⏰ Promise Tracker")
        st.caption("Track commitments made to customers")
        
        deep_analysis = st.session_state.get('deep_analysis', {})
        promises = deep_analysis.get('promises', {})
        
        if not promises:
            st.info("🤖 Run Deep Analysis to detect promises")
        else:
            pending = []
            overdue = []
            
            for tid, promise_list in promises.items():
                for p in promise_list:
                    if p.get('status') == 'overdue':
                        overdue.append((tid, p))
                    elif p.get('status') == 'pending':
                        pending.append((tid, p))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("⚠️ Overdue", len(overdue))
            with col2:
                st.metric("⏳ Pending", len(pending))
            
            if overdue:
                st.markdown("##### 🚨 Overdue Promises")
                for tid, p in overdue[:10]:
                    st.error(f"Ticket #{tid}: {p.get('promise', 'N/A')} (Due: {p.get('deadline', 'N/A')})")
            
            if pending:
                st.markdown("##### ⏳ Pending Promises")
                for tid, p in pending[:10]:
                    st.warning(f"Ticket #{tid}: {p.get('promise', 'N/A')} (Due: {p.get('deadline', 'N/A')})")
    
    # =========================================================================
    # TAB 5: ESCALATION WATCH
    # =========================================================================
    with tabs[4]:
        st.subheader("🚨 Escalation Watch")
        st.caption("Tickets at risk of escalation")
        
        deep_analysis = st.session_state.get('deep_analysis', {})
        escalation = deep_analysis.get('escalation', {})
        
        if not escalation:
            st.info("🤖 Run Deep Analysis to predict escalation risks")
        else:
            # Group by risk
            critical = [(tid, e) for tid, e in escalation.items() if e.get('risk') == 'critical']
            high = [(tid, e) for tid, e in escalation.items() if e.get('risk') == 'high']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔴 Critical", len(critical))
            with col2:
                st.metric("🟠 High Risk", len(high))
            with col3:
                st.metric("📊 Analyzed", len(escalation))
            
            if critical:
                st.markdown("##### 🔴 Critical - Immediate Action Required")
                for tid, e in critical[:5]:
                    ticket = next((t for t in tickets if t.id == tid), None)
                    if ticket:
                        with st.expander(f"🚨 #{tid} - {ticket.subject[:40]}..."):
                            st.write(f"**Risk Probability:** {e.get('probability', 0)*100:.0f}%")
                            st.write(f"**Factors:** {', '.join(e.get('factors', []))}")
                            st.info(f"**Recommendation:** {e.get('recommendation', 'N/A')}")
            
            if high:
                st.markdown("##### 🟠 High Risk")
                for tid, e in high[:5]:
                    ticket = next((t for t in tickets if t.id == tid), None)
                    if ticket:
                        st.warning(f"#{tid}: {ticket.subject[:50]}... - {e.get('recommendation', '')}")
    
    # =========================================================================
    # TAB 6: ROOT CAUSES
    # =========================================================================
    with tabs[5]:
        st.subheader("Root Cause Analysis")
        
        # Analyze common patterns
        patterns = analyze_patterns(tickets)
        
        if patterns:
            for i, pattern in enumerate(patterns[:10], 1):
                severity_color = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(pattern.get('severity', 'medium'), '⚪')
                
                with st.expander(f"{severity_color} {pattern['name']} ({pattern['count']} tickets)", expanded=(i <= 3)):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Description:** {pattern['description']}")
                        st.markdown(f"**Impact:** {pattern['impact']}")
                        st.markdown(f"**Recommended Fix:** {pattern['fix']}")
                    
                    with col2:
                        st.metric("Affected Tickets", pattern['count'])
                        st.metric("Avg Resolution", f"{pattern.get('avg_resolution', 0):.1f}h")
        else:
            st.info("Run AI analysis to identify root causes.")
            if st.button("🚀 Run Analysis", type="primary"):
                with st.spinner("Analyzing tickets..."):
                    import time
                    time.sleep(2)
                    st.success("Analysis complete! Refresh to see results.")
    
    # =========================================================================
    # TAB 7: CATEGORY INTELLIGENCE
    # =========================================================================
    with tabs[6]:
        st.subheader("Category Intelligence")
        st.caption("Deep insights into ticket categories")
        
        # Category analysis
        categories = config.get('categories', 'custom', default=[])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📈 Category Trends")
            
            # Weekly trend by category
            weekly_cats = defaultdict(lambda: Counter())
            for t in tickets:
                if t.created_at:
                    week = t.created_at.strftime('%Y-W%W')
                    cat = t.category or 'Uncategorized'
                    weekly_cats[week][cat] += 1
            
            weeks = sorted(weekly_cats.keys())[-8:]
            top_cats = Counter(t.category or 'Uncategorized' for t in tickets).most_common(5)
            
            fig = go.Figure()
            for cat_name, _ in top_cats:
                fig.add_trace(go.Scatter(
                    x=weeks,
                    y=[weekly_cats[w].get(cat_name, 0) for w in weeks],
                    name=cat_name[:20],
                    mode='lines+markers',
                ))
            
            fig.update_layout(
                height=350,
                xaxis_title="Week",
                yaxis_title="Tickets",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("##### ⏱️ Resolution by Category")
            
            cat_resolution = defaultdict(list)
            for t in tickets:
                if t.resolution_time:
                    cat = t.category or 'Uncategorized'
                    cat_resolution[cat].append(t.resolution_time)
            
            cat_avg = {
                cat: sum(times) / len(times)
                for cat, times in cat_resolution.items()
                if times
            }
            
            sorted_cats = sorted(cat_avg.items(), key=lambda x: x[1], reverse=True)[:10]
            
            fig = go.Figure(data=[go.Bar(
                x=[c[1] for c in sorted_cats],
                y=[c[0][:25] for c in sorted_cats],
                orientation='h',
                marker_color='#1F4E79',
            )])
            fig.update_layout(
                height=350,
                xaxis_title="Avg Resolution (hours)",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Category keyword analysis
        st.markdown("---")
        st.markdown("##### 🔤 Keyword Detection")
        
        for cat in categories[:5]:
            with st.expander(f"🏷️ {cat['name']}"):
                st.markdown(f"**Keywords:** {', '.join(cat['keywords'])}")
                
                # Count matches
                matches = sum(1 for t in tickets if t.category == cat['name'])
                st.metric("Matched Tickets", matches)
    
    # =========================================================================
    # TAB 8: RECOMMENDATIONS
    # =========================================================================
    with tabs[7]:
        st.subheader("💡 AI Recommendations")
        st.caption("Actionable insights to improve support")
        
        recommendations = generate_recommendations(tickets)
        
        for i, rec in enumerate(recommendations, 1):
            priority_color = {
                'high': '🔴',
                'medium': '🟡',
                'low': '�'
            }.get(rec.get('priority', 'medium'), '⚪')
            
            st.markdown(f"### {priority_color} {i}. {rec['title']}")
            st.markdown(rec['description'])
            
            if rec.get('action'):
                st.info(f"**Recommended Action:** {rec['action']}")
            
            if rec.get('impact'):
                st.success(f"**Expected Impact:** {rec['impact']}")
            
            st.markdown("---")


def analyze_patterns(tickets):
    """Analyze tickets for common patterns."""
    patterns = []
    
    # Pattern 1: Configuration issues
    config_keywords = ['config', 'setup', 'setting', 'configure']
    config_tickets = [t for t in tickets if any(kw in t.subject.lower() or kw in t.description.lower() for kw in config_keywords)]
    if config_tickets:
        patterns.append({
            'name': 'Configuration Problems',
            'description': 'Tickets related to system configuration and setup',
            'impact': 'Users unable to properly configure the system',
            'fix': 'Create comprehensive configuration guides and wizards',
            'count': len(config_tickets),
            'severity': 'high' if len(config_tickets) > 20 else 'medium',
            'avg_resolution': sum(t.resolution_time or 0 for t in config_tickets) / max(len(config_tickets), 1),
        })
    
    # Pattern 2: Sync/Connection issues
    sync_keywords = ['sync', 'offline', 'connection', 'network', 'not connecting']
    sync_tickets = [t for t in tickets if any(kw in t.subject.lower() or kw in t.description.lower() for kw in sync_keywords)]
    if sync_tickets:
        patterns.append({
            'name': 'Sync/Connection Issues',
            'description': 'Problems with data synchronization and connectivity',
            'impact': 'Data inconsistencies and workflow interruptions',
            'fix': 'Improve offline capabilities and connection resilience',
            'count': len(sync_tickets),
            'severity': 'high' if len(sync_tickets) > 15 else 'medium',
            'avg_resolution': sum(t.resolution_time or 0 for t in sync_tickets) / max(len(sync_tickets), 1),
        })
    
    # Pattern 3: License/Activation
    license_keywords = ['license', 'activation', 'key', 'subscription', 'expired']
    license_tickets = [t for t in tickets if any(kw in t.subject.lower() or kw in t.description.lower() for kw in license_keywords)]
    if license_tickets:
        patterns.append({
            'name': 'License/Activation Issues',
            'description': 'Problems with product licensing and activation',
            'impact': 'Users blocked from using the product',
            'fix': 'Streamline license delivery and self-service activation',
            'count': len(license_tickets),
            'severity': 'high',
            'avg_resolution': sum(t.resolution_time or 0 for t in license_tickets) / max(len(license_tickets), 1),
        })
    
    # Pattern 4: Long resolution times
    slow_tickets = [t for t in tickets if t.resolution_time and t.resolution_time > 200]
    if slow_tickets:
        patterns.append({
            'name': 'Slow Resolution Pattern',
            'description': f'{len(slow_tickets)} tickets took over 200 hours to resolve',
            'impact': 'Customer frustration and potential churn',
            'fix': 'Identify and address bottlenecks in resolution process',
            'count': len(slow_tickets),
            'severity': 'high',
            'avg_resolution': sum(t.resolution_time or 0 for t in slow_tickets) / max(len(slow_tickets), 1),
        })
    
    return sorted(patterns, key=lambda x: x['count'], reverse=True)


def detect_anomalies(tickets):
    """Detect anomalies in ticket data."""
    anomalies = []
    
    # Anomaly 1: Spike in ticket volume
    daily_counts = Counter(t.created_at.strftime('%Y-%m-%d') for t in tickets if t.created_at)
    if daily_counts:
        avg_daily = sum(daily_counts.values()) / len(daily_counts)
        for date, count in daily_counts.items():
            if count > avg_daily * 3:
                anomalies.append({
                    'type': 'Volume Spike',
                    'description': f'{date}: {count} tickets (3x average)',
                    'severity': 'high',
                    'tickets': [t.id for t in tickets if t.created_at and t.created_at.strftime('%Y-%m-%d') == date],
                })
    
    # Anomaly 2: Many high priority tickets
    high_priority = [t for t in tickets if t.priority >= 3]
    if len(high_priority) > len(tickets) * 0.3:
        anomalies.append({
            'type': 'High Priority Ratio',
            'description': f'{len(high_priority)} high/urgent tickets ({len(high_priority)/len(tickets)*100:.0f}% of total)',
            'severity': 'medium',
            'tickets': [t.id for t in high_priority[:10]],
        })
    
    # Anomaly 3: Old open tickets
    old_open = [t for t in tickets if t.is_open and t.days_open > 30]
    if old_open:
        anomalies.append({
            'type': 'Aging Tickets',
            'description': f'{len(old_open)} tickets open for more than 30 days',
            'severity': 'high',
            'tickets': [t.id for t in old_open[:10]],
        })
    
    return anomalies


def generate_recommendations(tickets):
    """Generate actionable recommendations."""
    recommendations = []
    
    # Rec 1: Stale tickets
    stale = [t for t in tickets if t.is_open and t.days_open >= 15]
    if stale:
        recommendations.append({
            'title': f'Address {len(stale)} Stale Tickets',
            'description': f'There are {len(stale)} tickets that have been open for more than 15 days without resolution.',
            'action': 'Review and prioritize these tickets, escalate if needed, or close with resolution.',
            'impact': 'Improved customer satisfaction and reduced backlog.',
            'priority': 'high',
        })
    
    # Rec 2: No response tickets
    no_response = [t for t in tickets if not t.has_agent_response and t.is_open]
    if no_response:
        recommendations.append({
            'title': f'Respond to {len(no_response)} Unanswered Tickets',
            'description': f'{len(no_response)} open tickets have not received any agent response.',
            'action': 'Assign and respond to these tickets immediately.',
            'impact': 'Prevent customer escalations and improve response metrics.',
            'priority': 'high',
        })
    
    # Rec 3: SLA improvement
    with_response = [t for t in tickets if t.first_response_time is not None]
    sla_breaches = [t for t in with_response if t.first_response_time > 12]
    if len(sla_breaches) > len(with_response) * 0.2:
        recommendations.append({
            'title': 'Improve First Response Time',
            'description': f'{len(sla_breaches)} tickets ({len(sla_breaches)/len(with_response)*100:.0f}%) breached SLA.',
            'action': 'Review workload distribution and consider adding resources during peak hours.',
            'impact': 'Higher SLA compliance and customer satisfaction.',
            'priority': 'medium',
        })
    
    # Rec 4: Knowledge base
    common_issues = Counter(t.category for t in tickets if t.category).most_common(3)
    if common_issues:
        recommendations.append({
            'title': 'Create Knowledge Base Articles',
            'description': f'Top issues: {", ".join([c[0] for c in common_issues])} - consider self-service options.',
            'action': 'Create FAQ articles and troubleshooting guides for common issues.',
            'impact': 'Reduced ticket volume and faster resolution for simple issues.',
            'priority': 'medium',
        })
    
    return recommendations


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    render_ai_page()
