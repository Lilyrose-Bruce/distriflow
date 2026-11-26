"""
file_reader.py - reads an uploaded CSV or Excel (.xlsx) order file.

It only READS the file into plain rows of text. Checking the values
(negative quantity, unknown customer...) happens later in staging.py.

Row numbers are the same as in the spreadsheet: the header is row 1,
so the first order is row 2. That way "Row 7" in an error message is row 7 in the file.
"""
import csv
import io
from dataclasses import dataclass
from typing import List

from app import config
from app.services.errors import FileReadError

# Different ways people write the column names -> our standard name
HEADER_ALIASES = {
    "customer": "customer_name",
    "customer_name": "customer_name",
    "product": "product",
    "quantity": "quantity",
    "qty": "quantity",
    "unit_weight": "unit_weight",
    "total_weight": "total_weight",
}

REQUIRED_COLUMNS = ["customer_name", "product", "quantity", "unit_weight"]

# Names shown to the user in messages
PRETTY_NAMES = {
    "customer_name": "Customer",
    "product": "Product",
    "quantity": "Quantity",
    "unit_weight": "Unit weight",
    "total_weight": "Total weight",
}


@dataclass
class RawRow:
    """One row of the file, every value still plain text."""
    row_number: int
    customer_name: str
    product: str
    quantity: str
    unit_weight: str
    total_weight: str   # "" if the file has no total column or the cell is empty


def normalise_header(text: str) -> str:
    """'Unit weight (kg)' -> 'unit_weight',  'Customer Name' -> 'customer_name'."""
    name = text.strip().lower()
    if "(" in name:                        # remove units such as "(kg)"
        name = name.split("(")[0]
    name = name.replace("-", " ").replace("_", " ")
    return "_".join(name.split())


def cell_to_text(value) -> str:
    """Turn any cell value into clean text. Excel gives 10.0 for 10, so we fix that."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_order_file(filename: str, content: bytes) -> List[RawRow]:
    """Read a .csv or .xlsx file and return its rows. Raises FileReadError if it cannot be used."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        table = _read_csv(content)
    elif name.endswith(".xlsx"):
        table = _read_excel(content)
    elif name.endswith(".xls"):
        raise FileReadError("Old .xls files are not supported. Save the file as .xlsx or .csv and upload it again.")
    else:
        raise FileReadError("Please upload a .csv or .xlsx file.")
    return _table_to_rows(table)


def _read_csv(content: bytes) -> List[list]:
    """Read CSV text. Handles Excel's UTF-8 marker and ; or tab separators."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252", errors="replace")   # older Windows files

    first_line = text.splitlines()[0] if text.strip() else ""
    delimiter = max([",", ";", "\t"], key=first_line.count)  # the separator used most in the header
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def _read_excel(content: bytes) -> List[list]:
    """Read the first sheet of an .xlsx file."""
    from openpyxl import load_workbook   # imported here so CSV-only use does not need it

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    except Exception:
        # A damaged or fake .xlsx must never crash the server
        raise FileReadError("The Excel file could not be read. Check that it is a real .xlsx file.")


def _table_to_rows(table: List[list]) -> List[RawRow]:
    """Find the columns from the header row, then build one RawRow per data row."""
    if not table or all(cell_to_text(c) == "" for c in table[0]):
        raise FileReadError("The file is empty. The first row must contain the column names.")

    # Match each header cell to one of our standard names
    column_of = {}
    for position, header in enumerate(table[0]):
        standard = HEADER_ALIASES.get(normalise_header(cell_to_text(header)))
        if standard and standard not in column_of:
            column_of[standard] = position

    missing = [PRETTY_NAMES[c] for c in REQUIRED_COLUMNS if c not in column_of]
    if missing:
        raise FileReadError(
            "The file is missing these columns: " + ", ".join(missing) + ". "
            "Required columns: Customer, Product, Quantity, Unit weight. (Total weight is optional.)"
        )

    def value(row, column_name):
        position = column_of.get(column_name)
        if position is None or position >= len(row):
            return ""
        return cell_to_text(row[position])

    rows = []
    for row_number, row in enumerate(table, start=1):
        if row_number == 1:
            continue                                   # the header
        if all(cell_to_text(c) == "" for c in row):
            continue                                   # skip blank rows
        rows.append(RawRow(
            row_number=row_number,
            customer_name=value(row, "customer_name"),
            product=value(row, "product"),
            quantity=value(row, "quantity"),
            unit_weight=value(row, "unit_weight"),
            total_weight=value(row, "total_weight"),
        ))

    if not rows:
        raise FileReadError("The file has no order rows below the header.")
    if len(rows) > config.MAX_UPLOAD_ROWS:
        raise FileReadError(f"The file has {len(rows)} rows. The maximum is {config.MAX_UPLOAD_ROWS}.")
    return rows
