# Configuration Overview

FTEX uses YAML configuration for flexibility.

## Configuration Files

| File | Purpose |
|------|---------|
| `config/default.yaml` | Defaults (don't edit) |
| `config/user/config.yaml` | Your settings |
| `.env` | Environment variables |

## Basic Example

```yaml
# config/user/config.yaml

industry:
  name: "My Company"
  preset: general
  primary_entity: customer

sla:
  first_response_hours: 12
  resolution_hours: 24
  stale_threshold_days: 15

ai:
  provider: ollama
  ollama:
    model: "qwen2.5:14b"
```

## Environment Override

All settings can be overridden via environment:

```bash
export FRESHDESK_DOMAIN=your-company
export OLLAMA_MODEL=llama3.1:8b
```

## Next Steps

- [Industry Presets](presets.md)
- [SLA Settings](sla.md)
- [AI Providers](ai-providers.md)
