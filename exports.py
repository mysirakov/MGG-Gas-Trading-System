"""Export helpers for download buttons."""
import io
from datetime import date, datetime
from decimal import Decimal
from openpyxl import Workbook

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _coerce(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, str, int, float, bool)):
        return value
    return str(value)


def rows_to_xlsx(rows, sheet_name: str = "Sheet1") -> bytes:
    """Build an xlsx file from a list of dict rows. Header is the keys of the first row."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31] or "Sheet1"

    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([_coerce(row.get(h)) for h in headers])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
