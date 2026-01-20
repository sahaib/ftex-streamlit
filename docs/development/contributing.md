# Contributing Guide

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ftex-streamlit.git
   ```
3. Create a branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```

## Development Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
streamlit run app/main.py
```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions focused

## Pull Request Process

1. Update documentation
2. Add tests
3. Ensure tests pass
4. Update CHANGELOG.md
5. Submit PR
