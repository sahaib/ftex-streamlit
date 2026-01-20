# Industry Presets

Pre-configured settings for common industries.

## Available Presets

| Preset | Entity | Use Case |
|--------|--------|----------|
| `general` | customer | General helpdesk |
| `maritime` | vessel | Shipping/maritime |
| `it_support` | customer | IT helpdesk |
| `saas` | customer | SaaS support |
| `ecommerce` | customer | E-commerce |

## Applying Presets

### Via Settings UI

1. Go to **Settings** → **Industry**
2. Select preset from dropdown
3. Click **Apply**

### Via Configuration

```yaml
industry:
  preset: maritime
```

## Customizing

Override any preset setting:

```yaml
industry:
  preset: maritime
  name: "My Shipping Co"
  
categories:
  custom:
    - name: Custom Category
      keywords: [custom, special]
```
