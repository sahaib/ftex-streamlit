# AI Analysis

AI-powered insights for intelligent ticket management.

## Features

### Issue Clustering
Groups similar tickets by content, category, and resolution approach.

### Root Cause Analysis
Identifies underlying causes:

- Configuration problems
- Documentation gaps
- Product issues

### Anomaly Detection
Flags unusual patterns:

- Volume spikes
- Response time outliers
- Priority anomalies

### Recommendations
Actionable suggestions based on data analysis.

## Configuration

```yaml
ai:
  provider: ollama  # or: openai, anthropic
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
```

See [AI Providers](../configuration/ai-providers.md) for setup.
