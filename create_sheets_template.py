"""
Google Sheets Habit Tracker Template Generator
Creates an exact replica of the bullet-journal style tracker
"""

import datetime
import calendar
import os
import sys

def create_template():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        print("Using gspread with service account...")
        use_gspread = True
    except ImportError:
        use_gspread = False

    # Try openpyxl for local Excel export (can be opened / imported into Sheets)
    try:
        import openpyxl
        from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                                      GradientFill)
        from openpyxl.utils import get_column_letter
        from openpyxl.chart import LineChart, Reference
        from openpyxl.chart.series import DataPoint
    except ImportError:
        print("Installing openpyxl...")
        os.system(f"{sys.executable} -m pip install openpyxl --quiet")
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.chart import LineChart, Reference

    now   = datetime.date.today()
    year  = now.year
    month = now.month
    days  = calendar.monthrange(year, month)[1]
    month_name = now.strftime("%B %Y")

    HABITS = [
        "Wake up before 7am",
        "Exercise / Meditate",
        "Check DMs / Email",
        "Study (2hrs+)",
        "Drink H₂O (2.3L)",
        "Do Work",
        "No Sugar / Junk food",
        "Everything Groomed",
        "Read book / Editorial",
        "Feel Gratitude",
        "Plan Next Day",
        "Learn New Things",
        "Sleep before 12am",
    ]

    MOOD_LEVELS = ["Awesome 🤩", "Good 😊", "Normal 😐", "Stressed 😤", "Tired 😴", "F**ked 😵"]

    # ── Colors ────────────────────────────────────────────────────────────────
    C_PURPLE_DARK = "4C1D95"
    C_PURPLE      = "7C3AED"
    C_PURPLE_LIGHT = "A78BFA"
    C_BG_DARK     = "0F0F1A"
    C_BG_CARD     = "1A1A2E"
    C_BG_HEADER   = "16213E"
    C_WHITE       = "F1F5F9"
    C_MUTED       = "94A3B8"
    C_GRID        = "2D2D44"
    C_DONE        = "22C55E"
    C_FAIL        = "EF4444"
    C_YELLOW      = "F59E0B"
    C_ALT         = "1E1E32"
    C_MOOD = {
        "Awesome 🤩": "4CAF50",
        "Good 😊":    "8BC34A",
        "Normal 😐":  "FFC107",
        "Stressed 😤":"FF9800",
        "Tired 😴":   "F44336",
        "F**ked 😵":  "9C27B0",
    }
    C_MOOD_SCORE = {
        "Awesome 🤩": 5,
        "Good 😊":    4,
        "Normal 😐":  3,
        "Stressed 😤": 2,
        "Tired 😴":   1,
        "F**ked 😵":  0,
    }

    def fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    def font(bold=False, color=C_WHITE, size=10, italic=False):
        return Font(bold=bold, color=color, size=size, name="Segoe UI", italic=italic)

    def center():
        return Alignment(horizontal="center", vertical="center", wrap_text=True)

    def left():
        return Alignment(horizontal="left", vertical="center")

    def border_thin(color=C_GRID):
        s = Side(style="thin", color=color)
        return Border(left=s, right=s, top=s, bottom=s)

    def border_right(color=C_GRID):
        s = Side(style="thin", color=color)
        return Border(right=s)

    # ── Workbook ──────────────────────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = month_name
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = C_PURPLE

    # Column widths
    ws.column_dimensions["A"].width = 3    # row num
    ws.column_dimensions["B"].width = 30   # habit name
    for d in range(1, days + 1):
        ws.column_dimensions[get_column_letter(d + 2)].width = 4
    total_col = get_column_letter(days + 3)
    ws.column_dimensions[total_col].width = 8

    # ── Title row ─────────────────────────────────────────────────────────────
    ws.row_dimensions[1].height = 36
    ws.merge_cells(f"A1:{total_col}1")
    c = ws["A1"]
    c.value = f"✨  Being a Better Version of Me  —  {month_name}"
    c.font = Font(bold=True, color=C_WHITE, size=16, name="Segoe UI")
    c.fill = fill(C_PURPLE)
    c.alignment = center()

    # ── Sub-header: goal ──────────────────────────────────────────────────────
    ws.row_dimensions[2].height = 20
    ws.merge_cells(f"A2:{total_col}2")
    c = ws["A2"]
    c.value = f'Goal / Focus:   "Being Productive"   ← edit me'
    c.font = font(italic=True, color=C_MUTED, size=9)
    c.fill = fill(C_BG_HEADER)
    c.alignment = left()

    # ── HABIT ROUTINE header ──────────────────────────────────────────────────
    ws.row_dimensions[3].height = 22
    ws.merge_cells(f"A3:B3")
    c = ws["A3"]
    c.value = "HABIT / ROUTINE"
    c.font = font(bold=True, color=C_PURPLE_LIGHT, size=10)
    c.fill = fill(C_BG_HEADER)
    c.alignment = left()

    # Day numbers row
    for d in range(1, days + 1):
        col = get_column_letter(d + 2)
        c = ws[f"{col}3"]
        dt = datetime.date(year, month, d)
        is_weekend = dt.weekday() >= 5
        c.value = d
        c.font = font(bold=is_weekend, color=C_PURPLE_LIGHT if is_weekend else C_MUTED, size=8)
        c.fill = fill(C_BG_HEADER)
        c.alignment = center()

    # Day names row
    ws.row_dimensions[4].height = 14
    ws["A4"].value = ""; ws["A4"].fill = fill(C_BG_HEADER)
    ws["B4"].value = ""; ws["B4"].fill = fill(C_BG_HEADER)
    for d in range(1, days + 1):
        col = get_column_letter(d + 2)
        c = ws[f"{col}4"]
        c.value = datetime.date(year, month, d).strftime("%a")[0]
        c.font = font(color=C_MUTED, size=7)
        c.fill = fill(C_BG_HEADER)
        c.alignment = center()

    # TOTAL header
    c = ws[f"{total_col}3"]
    c.value = "TOTAL"
    c.font = font(bold=True, color=C_PURPLE_LIGHT, size=9)
    c.fill = fill(C_BG_HEADER)
    c.alignment = center()
    c = ws[f"{total_col}4"]
    c.fill = fill(C_BG_HEADER)

    # ── Habits rows ───────────────────────────────────────────────────────────
    HABIT_START_ROW = 5
    for i, habit in enumerate(HABITS):
        row = HABIT_START_ROW + i
        ws.row_dimensions[row].height = 22
        bg = C_BG_CARD if i % 2 == 0 else C_ALT

        # Row number
        c = ws[f"A{row}"]
        c.value = i + 1
        c.font = font(color=C_MUTED, size=8)
        c.fill = fill(bg)
        c.alignment = center()

        # Habit name
        c = ws[f"B{row}"]
        c.value = habit
        c.font = font(color=C_WHITE, size=10)
        c.fill = fill(bg)
        c.alignment = left()

        # Day checkboxes (empty = ○, done = ✓, missed = ✗)
        day_cols = []
        for d in range(1, days + 1):
            col = get_column_letter(d + 2)
            cell_ref = f"{col}{row}"
            c = ws[cell_ref]
            c.value = "○"   # default unchecked
            c.font = font(color=C_GRID, size=10)
            c.fill = fill(bg)
            c.alignment = center()
            day_cols.append(cell_ref)

        # TOTAL formula: count ✓ cells
        total_cell = f"{total_col}{row}"
        # Count cells that equal "✓"
        day_range_start = get_column_letter(3)
        day_range_end   = get_column_letter(days + 2)
        ws[total_cell].value = f'=COUNTIF({day_range_start}{row}:{day_range_end}{row},"✓")'
        ws[total_cell].font  = font(bold=True, color=C_WHITE, size=10)
        ws[total_cell].fill  = fill(C_PURPLE)
        ws[total_cell].alignment = center()

    # ── Data validation instructions (tip row) ─────────────────────────────
    tip_row = HABIT_START_ROW + len(HABITS)
    ws.row_dimensions[tip_row].height = 16
    ws.merge_cells(f"A{tip_row}:{total_col}{tip_row}")
    c = ws[f"A{tip_row}"]
    c.value = "TIP: Type  ✓  for done  ·  ✗  for missed  ·  ○  for skipped   (copy-paste the symbols)"
    c.font = font(italic=True, color=C_MUTED, size=8)
    c.fill = fill(C_BG_HEADER)
    c.alignment = center()

    # ── Mood Tracker section ──────────────────────────────────────────────────
    mood_header_row = tip_row + 2
    ws.row_dimensions[mood_header_row].height = 22
    ws.merge_cells(f"A{mood_header_row}:B{mood_header_row}")
    c = ws[f"A{mood_header_row}"]
    c.value = "MOOD TRACKER"
    c.font = font(bold=True, color=C_PURPLE_LIGHT, size=10)
    c.fill = fill(C_BG_HEADER)
    c.alignment = left()

    for d in range(1, days + 1):
        col = get_column_letter(d + 2)
        c = ws[f"{col}{mood_header_row}"]
        c.value = d
        c.font = font(color=C_MUTED, size=8)
        c.fill = fill(C_BG_HEADER)
        c.alignment = center()

    c = ws[f"{total_col}{mood_header_row}"]
    c.fill = fill(C_BG_HEADER)

    mood_start_row = mood_header_row + 1
    mood_score_row = {}  # day -> formula cell row

    for mi, mood in enumerate(MOOD_LEVELS):
        row = mood_start_row + mi
        ws.row_dimensions[row].height = 20
        bg = C_BG_CARD if mi % 2 == 0 else C_ALT
        mood_color = C_MOOD[mood]

        c = ws[f"A{row}"]
        c.value = mi + 1
        c.font = font(color=C_MUTED, size=8)
        c.fill = fill(bg)
        c.alignment = center()

        c = ws[f"B{row}"]
        c.value = mood
        c.font = Font(bold=True, color=mood_color, size=10, name="Segoe UI")
        c.fill = fill(bg)
        c.alignment = left()

        for d in range(1, days + 1):
            col = get_column_letter(d + 2)
            c = ws[f"{col}{row}"]
            c.value = "○"
            c.font = font(color=C_GRID, size=10)
            c.fill = fill(bg)
            c.alignment = center()

        c = ws[f"{total_col}{row}"]
        c.fill = fill(bg)

    # ── Mood Score (hidden helper) row ────────────────────────────────────────
    score_row = mood_start_row + len(MOOD_LEVELS) + 1
    ws.row_dimensions[score_row].height = 14
    ws[f"B{score_row}"].value = "Mood Score (auto)"
    ws[f"B{score_row}"].font = font(italic=True, color=C_MUTED, size=8)
    ws[f"B{score_row}"].fill = fill(C_BG_HEADER)

    for d in range(1, days + 1):
        col = get_column_letter(d + 2)
        # Score = weighted by which mood row is marked ✓
        parts = []
        for mi, mood in enumerate(MOOD_LEVELS):
            row = mood_start_row + mi
            score = C_MOOD_SCORE[mood]
            parts.append(f'IF({col}{row}="✓",{score},0)')
        formula = "=" + "+".join(parts)
        c = ws[f"{col}{score_row}"]
        c.value = formula
        c.font = font(color=C_MUTED, size=8)
        c.fill = fill(C_BG_HEADER)
        c.alignment = center()

    # ── Chart ─────────────────────────────────────────────────────────────────
    chart_row = score_row + 2
    chart = LineChart()
    chart.title   = "Mood Graph"
    chart.style   = 10
    chart.height  = 8
    chart.width   = 24
    chart.grouping = "standard"

    score_range = Reference(ws,
                             min_col=3, max_col=days + 2,
                             min_row=score_row, max_row=score_row)
    day_labels  = Reference(ws,
                             min_col=3, max_col=days + 2,
                             min_row=3, max_row=3)
    chart.add_data(score_range, titles_from_data=False)
    chart.set_categories(day_labels)
    from openpyxl.chart.series import SeriesLabel
    chart.series[0].graphicalProperties.line.solidFill = "7C3AED"
    chart.series[0].graphicalProperties.line.width     = 25000
    chart.series[0].marker.symbol = "circle"
    chart.series[0].marker.size   = 6

    chart.y_axis.title    = "Mood"
    chart.x_axis.title    = "Day"
    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 5

    ws.add_chart(chart, f"B{chart_row}")

    # ── Summary sheet ─────────────────────────────────────────────────────────
    ws2 = wb.create_sheet("📊 Summary")
    ws2.sheet_properties.tabColor = C_PURPLE_DARK
    ws2.column_dimensions["A"].width = 32
    ws2.column_dimensions["B"].width = 12
    ws2.column_dimensions["C"].width = 12

    ws2["A1"].value = "HABIT"
    ws2["B1"].value = "TOTAL ✓"
    ws2["C1"].value = "% Done"
    for cell in ["A1", "B1", "C1"]:
        ws2[cell].font = font(bold=True, color=C_WHITE)
        ws2[cell].fill = fill(C_PURPLE)
        ws2[cell].alignment = center()

    for i, habit in enumerate(HABITS):
        row = i + 2
        ws2.row_dimensions[row].height = 20
        bg = C_BG_CARD if i % 2 == 0 else C_ALT
        ws2[f"A{row}"].value = habit
        ws2[f"A{row}"].font  = font(color=C_WHITE)
        ws2[f"A{row}"].fill  = fill(bg)
        ws2[f"A{row}"].alignment = left()

        # Reference total from main sheet
        col_ref = total_col
        ws2[f"B{row}"].value = f"='{month_name}'!{col_ref}{HABIT_START_ROW + i}"
        ws2[f"B{row}"].font  = font(color=C_WHITE, bold=True)
        ws2[f"B{row}"].fill  = fill(bg)
        ws2[f"B{row}"].alignment = center()

        ws2[f"C{row}"].value = f"=IFERROR(B{row}/{days}*100,0)"
        ws2[f"C{row}"].number_format = "0.0\"%\""
        ws2[f"C{row}"].font  = font(color=C_WHITE)
        ws2[f"C{row}"].fill  = fill(bg)
        ws2[f"C{row}"].alignment = center()

    # ── Instructions sheet ────────────────────────────────────────────────────
    ws3 = wb.create_sheet("ℹ️ How to Use")
    ws3.sheet_properties.tabColor = C_PURPLE_DARK
    ws3.column_dimensions["A"].width = 60
    ws3.row_dimensions[1].height = 30

    instructions = [
        ("✨ HOW TO USE THIS HABIT TRACKER", True, C_PURPLE_LIGHT),
        ("", False, C_WHITE),
        ("1. MARKING HABITS", True, C_PURPLE_LIGHT),
        ("   Type  ✓  when you complete a habit for that day", False, C_WHITE),
        ("   Type  ✗  when you deliberately skipped/failed", False, C_WHITE),
        ("   Leave  ○  if the day hasn't come yet", False, C_WHITE),
        ("", False, C_WHITE),
        ("2. MOOD TRACKER", True, C_PURPLE_LIGHT),
        ("   Each row is a mood level. For each day, type ✓ in ONE mood row only.", False, C_WHITE),
        ("   Awesome=5  Good=4  Normal=3  Stressed=2  Tired=1  F**ked=0", False, C_WHITE),
        ("   The Mood Graph at the bottom auto-updates.", False, C_WHITE),
        ("", False, C_WHITE),
        ("3. SYMBOLS TO COPY-PASTE", True, C_PURPLE_LIGHT),
        ("   Done:    ✓", False, C_DONE),
        ("   Failed:  ✗", False, C_FAIL),
        ("   Empty:   ○", False, C_MUTED),
        ("", False, C_WHITE),
        ("4. TIPS", True, C_PURPLE_LIGHT),
        ("   • Edit the goal/focus text in row 2", False, C_WHITE),
        ("   • Add/remove rows in the habit section freely", False, C_WHITE),
        ("   • Duplicate this sheet each month and rename it", False, C_WHITE),
        ("   • The Summary sheet auto-calculates totals", False, C_WHITE),
    ]

    for r, (text, bold, color) in enumerate(instructions, 1):
        ws3.row_dimensions[r].height = 20
        c = ws3[f"A{r}"]
        c.value = text
        c.font  = Font(bold=bold, color=color, size=11, name="Segoe UI")
        c.fill  = fill(C_BG_CARD)
        c.alignment = left()

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             f"Habit_Tracker_{month_name.replace(' ', '_')}.xlsx")
    wb.save(out_path)
    print(f"\n✅  Template saved:\n    {out_path}")
    print("\nTo use with Google Sheets:")
    print("  1. Go to sheets.google.com")
    print("  2. Click ☰ → Import → Upload → select the .xlsx file")
    print("  3. Choose 'Replace spreadsheet' → Import data")
    print("\nAll formulas and the chart will work natively in Google Sheets!")
    return out_path

if __name__ == "__main__":
    create_template()
