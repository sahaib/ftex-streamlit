# Entity Analysis

Analyze by primary entity (customers, vessels, sites).

## Configuration

```yaml
industry:
  primary_entity: customer  # or: vessel, site
  entity_field: company.name
```

## Entity Health

Score based on:

- Open ticket count
- Stale tickets
- SLA breaches
- High priority tickets

### Health Levels

- 🟢 **Good** (≥80) - Healthy
- 🟡 **Fair** (60-80) - Minor issues
- 🟠 **Needs Attention** (40-60) - Review required
- 🔴 **Critical** (<40) - Immediate action
