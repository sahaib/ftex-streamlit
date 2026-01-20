# AI Providers

Configure AI for intelligent analysis.

## Ollama (Local, Free)

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull qwen2.5:14b
```

```yaml
ai:
  provider: ollama
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
```

## OpenAI

```yaml
ai:
  provider: openai
  openai:
    model: "gpt-4o-mini"
```

```bash
export OPENAI_API_KEY=sk-...
```

## Anthropic

```yaml
ai:
  provider: anthropic
  anthropic:
    model: "claude-3-haiku-20240307"
```

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Disable AI

```yaml
ai:
  provider: none
```
