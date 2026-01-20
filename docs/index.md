# FTEX Ticket Intelligence Platform

<p align="center">
  <strong>🎫 AI-Powered Support Analytics for Everyone</strong>
</p>

<p align="center">
  Open-source, self-hosted ticket analytics platform with AI-powered insights, interactive dashboards, and comprehensive reporting.
</p>

---

## What is FTEX?

**FTEX** (Freshdesk Ticket EXtraction & Analysis) transforms your support data into actionable insights:

- 📊 **27+ Analytics Views** - Executive dashboards to granular metrics
- 🤖 **AI-Powered Analysis** - Issue clustering, root cause detection
- ⏱️ **SLA Tracking** - Real-time compliance monitoring
- 🏢 **Entity Intelligence** - Track customers, vessels, sites, or products
- 📈 **Professional Reports** - Enterprise-grade Excel exports

## Quick Start

=== "Docker (Recommended)"

    ```bash
    git clone https://github.com/sahaib/ftex-streamlit.git
    cd ftex-streamlit
    docker-compose up -d
    # Open http://localhost:8501
    ```

=== "Local Installation"

    ```bash
    git clone https://github.com/sahaib/ftex-streamlit.git
    cd ftex-streamlit
    pip install -r requirements.txt
    streamlit run app/main.py
    ```

## Key Features

### 📊 Comprehensive Analytics

| Category | Features |
|----------|----------|
| **Overview** | KPIs, trends, alerts |
| **SLA** | First response, resolution tracking |
| **Agents** | Performance, workload, efficiency |
| **Entities** | Customer health, risk scoring |
| **AI** | Clustering, root cause, recommendations |

### 🤖 AI Integration

Works with multiple providers:

- **Ollama** - Free, local, private
- **OpenAI** - GPT-4, GPT-3.5
- **Anthropic** - Claude models

### 📈 Professional Reports

27-sheet Excel reports including:

- Executive Summary
- All Tickets & Stale Tickets
- SLA Performance & Breaches
- Customer Health & At-Risk Accounts
- Agent Performance
- Category Analysis
- And 20+ more sheets...

## Industry Presets

FTEX comes pre-configured for:

| Preset | Entity | Use Case |
|--------|--------|----------|
| `general` | Customer | General helpdesk |
| `maritime` | Vessel | Shipping/maritime |
| `it_support` | Customer | IT helpdesk |
| `saas` | Customer | SaaS support |
| `ecommerce` | Customer | E-commerce |

## Getting Help

- 📖 [Documentation](getting-started/installation.md) - Full guides
- 💬 [GitHub Discussions](https://github.com/sahaib/ftex-streamlit/discussions) - Ask questions
- 🐛 [Issues](https://github.com/sahaib/ftex-streamlit/issues) - Report bugs
- ⭐ [Star on GitHub](https://github.com/sahaib/ftex-streamlit) - Show support!

---

<p align="center">
  <strong>Ready to get started?</strong><br>
  <a href="getting-started/installation/">Installation Guide →</a>
</p>
