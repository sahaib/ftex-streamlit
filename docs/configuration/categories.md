# Category Configuration

Define ticket categories with keyword detection.

## Basic Setup

```yaml
categories:
  auto_detect: true
  
  custom:
    - name: Bug Report
      keywords:
        - bug
        - error
        - crash
        - broken
    
    - name: Feature Request
      keywords:
        - feature
        - enhancement
        - suggestion
```

## Detection Logic

1. Keywords match subject and description
2. Case-insensitive
3. First match wins
4. Unmatched → "Uncategorized"

## Tips

- Use specific keywords
- Order by specificity
- Include misspellings
