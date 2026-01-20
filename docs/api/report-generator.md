# Report Generator API

Generate Excel reports.

## Usage

```python
from pages.export import ReportGenerator

generator = ReportGenerator(tickets, config.to_dict())
excel_data = generator.generate_excel()

with open('report.xlsx', 'wb') as f:
    f.write(excel_data)
```

## Methods

### `generate_excel()`
Generate 27-sheet Excel report.

Returns: `bytes` (Excel content)

## Customization

```python
class CustomGenerator(ReportGenerator):
    def _create_executive_summary(self):
        ws = self.wb.create_sheet("Executive Summary")
        # Custom implementation
```

## Styling

```python
from pages.export import ExcelStyles

ExcelStyles.HEADER_BG   # Header background
ExcelStyles.SUCCESS     # Green
ExcelStyles.DANGER      # Red
```
