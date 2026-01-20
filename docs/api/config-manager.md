# Config Manager API

Manage YAML configuration.

## Usage

```python
from core.config_manager import get_config

config = get_config()

# Read
sla_hours = config.get('sla', 'first_response_hours', default=12)

# Write
config.set('sla', 'first_response_hours', 8)

# Apply template
config.apply_template('maritime')

# Save
config.save()
```

## Methods

### `get(*path, default=None)`
Get nested config value.

### `set(*path_and_value)`
Set config value.

### `apply_template(name)`
Apply industry template.

### `save(path=None)`
Save to file.

## Templates

- `general`
- `maritime`
- `it_support`
- `saas`
- `ecommerce`
