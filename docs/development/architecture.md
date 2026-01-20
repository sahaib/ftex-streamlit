# Architecture

## Directory Structure

```
ftex-streamlit/
├── app/
│   ├── main.py              # Entry point
│   ├── pages/               # Streamlit pages
│   └── core/                # Core modules
├── config/
│   ├── default.yaml
│   └── user/
└── docs/
```

## Data Flow

```
User Upload → DataLoader → Tickets → Analysis → UI/Export
                ↓
            Session State
                ↓
            Config Manager
```

## Key Components

- **DataLoader** - Data ingestion
- **ConfigManager** - Configuration
- **Session State** - State management
- **Pages** - Independent views

## Extension Points

- New pages: `app/pages/`
- New data sources: Extend `DataLoader`
- New AI providers: Extend `ConfigManager`
