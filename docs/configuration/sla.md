# SLA Settings

Configure service level agreements.

## Global Thresholds

```yaml
sla:
  first_response_hours: 12
  resolution_hours: 24
  stale_threshold_days: 15
```

## Priority-Based Targets

```yaml
sla:
  by_priority:
    Urgent:
      first_response: 1
      resolution: 4
    High:
      first_response: 4
      resolution: 24
    Medium:
      first_response: 8
      resolution: 72
    Low:
      first_response: 24
      resolution: 168
```

## Performance Bands

```yaml
sla:
  bands:
    excellent:
      min: 95
      max: 100
      color: "#10B981"
    good:
      min: 90
      max: 95
      color: "#3B82F6"
    poor:
      min: 0
      max: 70
      color: "#EF4444"
```
