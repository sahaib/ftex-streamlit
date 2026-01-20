# Installation

## Requirements

- **Python**: 3.9+ (3.11 recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 1GB + space for data

## Docker (Recommended)

```bash
git clone https://github.com/sahaib/ftex-streamlit.git
cd ftex-streamlit
cp .env.example .env
docker-compose up -d
```

Access at [http://localhost:8501](http://localhost:8501)

## Local Installation

=== "Linux/macOS"

    ```bash
    git clone https://github.com/sahaib/ftex-streamlit.git
    cd ftex-streamlit
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    streamlit run app/main.py
    ```

=== "Windows"

    ```powershell
    git clone https://github.com/sahaib/ftex-streamlit.git
    cd ftex-streamlit
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app/main.py
    ```

## Environment Variables

Create `.env` file:

```bash
# Freshdesk (optional)
FRESHDESK_DOMAIN=your-company
FRESHDESK_API_KEY=your-api-key

# AI (optional)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
```

## Next Steps

- [Quick Start](quickstart.md) - Get running in 5 minutes
- [Configuration](../configuration/index.md) - Customize settings
