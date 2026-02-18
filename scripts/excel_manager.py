#!/usr/bin/env python3
"""
BoBe Content Pipeline - Excel Styling Library

Provides shared styling helpers and color constants for Excel workbook generation.
Used by weekly_pipeline.py.
"""

from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter  # noqa: F401 — re-exported for consumers

__all__ = [
    "style_header_cell", "style_data_cell",
    "COLOR_DARK_BG", "COLOR_BLUE", "COLOR_GREEN", "COLOR_WHITE", "COLOR_LIGHT_ROW",
]

# Colors matching BoBe brand
COLOR_DARK_BG   = "111B32"
COLOR_BLUE      = "1589DC"
COLOR_GREEN     = "5BD69F"
COLOR_YELLOW    = "E0C145"
COLOR_WHITE     = "FFFFFF"
COLOR_LIGHT_ROW = "1A2540"


def style_header_cell(cell, bg_color: str = COLOR_BLUE, text_color: str = COLOR_WHITE):
    """Apply header styling to a cell."""
    cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
    cell.font = Font(bold=True, color=text_color, size=11)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def style_data_cell(cell, row_index: int):
    """Apply alternating row styling."""
    bg = COLOR_DARK_BG if row_index % 2 == 0 else COLOR_LIGHT_ROW
    cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
    cell.font = Font(color=COLOR_WHITE, size=10)
    cell.alignment = Alignment(vertical="top", wrap_text=True)
