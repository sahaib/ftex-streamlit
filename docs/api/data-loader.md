# Data Loader API

Load and process ticket data.

## Usage

```python
from core.data_loader import DataLoader

loader = DataLoader(config={'industry': {'entity_field': 'company.name'}})
tickets = loader.load_json('tickets.json')
summary = loader.get_summary()
```

## Methods

### `load_json(source)`
Load from JSON file or file object.

### `load_csv(source)`
Load from CSV file.

### `get_summary()`
Returns dict with ticket statistics.

### `get_tickets_df()`
Convert to pandas DataFrame.

## Ticket Class

```python
@dataclass
class Ticket:
    id: int
    subject: str
    description: str
    status: int
    priority: int
    created_at: datetime
    company_name: str
    # ... more fields
    
    @property
    def is_open(self) -> bool: ...
    
    @property
    def days_open(self) -> int: ...
```
