"""
Run from the project root:
    python scripts/generate_statements.py

Generates one combined 3-month PDF statement per user into data/.
"""

import os
import sys

# Make sure relative imports resolve from the project root regardless of cwd
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

styles     = getSampleStyleSheet()
HEADER     = ["Date", "Description", "Amount", "Type", "Balance"]
TABLE_STYLE = TableStyle([
    ("BACKGROUND",   (0, 0), (-1, 0),  colors.lightgrey),
    ("GRID",         (0, 0), (-1, -1), 1, colors.black),
    ("ALIGN",        (2, 1), (-1, -1), "RIGHT"),
    ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
    ("FONTSIZE",     (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightyellow]),
])

# -------------------------------------------------------
# Transaction data — 11 rows per month per user
# -------------------------------------------------------

JOHN_MONTHS = [
    {
        "period": "January 2025",
        "rows": [
            ["2025-01-02", "Opening Balance",      "5000.00", "Credit", "5000.00"],
            ["2025-01-05", "Electricity Bill",      "180.75",  "Debit",  "4819.25"],
            ["2025-01-08", "Netflix Subscription",   "15.99",  "Debit",  "4803.26"],
            ["2025-01-10", "Amazon Purchase",        "299.99",  "Debit",  "4503.27"],
            ["2025-01-12", "Gym Membership",          "45.00",  "Debit",  "4458.27"],
            ["2025-01-14", "Freelance Income",       "800.00",  "Credit", "5258.27"],
            ["2025-01-17", "Grocery Store",          "130.50",  "Debit",  "5127.77"],
            ["2025-01-20", "Gas Station",             "60.00",  "Debit",  "5067.77"],
            ["2025-01-22", "Restaurant",              "75.40",  "Debit",  "4992.37"],
            ["2025-01-25", "Salary Credit",         "3000.00",  "Credit", "7992.37"],
            ["2025-01-28", "Phone Bill",              "55.00",  "Debit",  "7937.37"],
        ],
    },
    {
        "period": "February 2025",
        "rows": [
            ["2025-02-01", "Grocery Store",          "120.50",  "Debit",  "7816.87"],
            ["2025-02-02", "Salary Credit",         "3000.00",  "Credit","10816.87"],
            ["2025-02-05", "Amazon Purchase",         "250.75",  "Debit", "10566.12"],
            ["2025-02-07", "Coffee Shop",              "12.80",  "Debit", "10553.32"],
            ["2025-02-10", "Insurance Premium",       "320.00",  "Debit", "10233.32"],
            ["2025-02-12", "Online Transfer",         "500.00",  "Debit",  "9733.32"],
            ["2025-02-14", "Valentine Dinner",        "145.00",  "Debit",  "9588.32"],
            ["2025-02-18", "Restaurant",               "89.40",  "Debit",  "9498.92"],
            ["2025-02-20", "Freelance Income",        "600.00",  "Credit","10098.92"],
            ["2025-02-22", "Netflix Subscription",    "15.99",  "Debit", "10082.93"],
            ["2025-02-25", "Gas Station",              "58.50",  "Debit", "10024.43"],
        ],
    },
    {
        "period": "March 2025",
        "rows": [
            ["2025-03-01", "Rent Payment",          "1200.00",  "Debit",  "8824.43"],
            ["2025-03-03", "Internet Bill",            "75.00",  "Debit",  "8749.43"],
            ["2025-03-05", "Grocery Store",           "145.30",  "Debit",  "8604.13"],
            ["2025-03-08", "Uber Ride",                "32.20",  "Debit",  "8571.93"],
            ["2025-03-10", "Coffee Shop",              "18.50",  "Debit",  "8553.43"],
            ["2025-03-12", "Freelance Income",        "750.00",  "Credit", "9303.43"],
            ["2025-03-15", "Salary Credit",          "3000.00",  "Credit","12303.43"],
            ["2025-03-18", "Amazon Purchase",         "189.99",  "Debit", "12113.44"],
            ["2025-03-20", "Gym Membership",           "45.00",  "Debit", "12068.44"],
            ["2025-03-22", "Flight Booking",          "560.00",  "Debit", "11508.44"],
            ["2025-03-28", "Restaurant",               "67.80",  "Debit", "11440.64"],
        ],
    },
]

JANE_MONTHS = [
    {
        "period": "January 2025",
        "rows": [
            ["2025-01-02", "Opening Balance",      "8000.00",  "Credit", "8000.00"],
            ["2025-01-04", "Rent Payment",         "1500.00",  "Debit",  "6500.00"],
            ["2025-01-06", "Grocery Store",           "95.30",  "Debit",  "6404.70"],
            ["2025-01-09", "Yoga Classes",            "60.00",  "Debit",  "6344.70"],
            ["2025-01-12", "Salary Credit",        "4500.00",  "Credit","10844.70"],
            ["2025-01-14", "Pharmacy",                "38.75",  "Debit", "10805.95"],
            ["2025-01-16", "Online Shopping",        "215.00",  "Debit", "10590.95"],
            ["2025-01-20", "Car Insurance",          "180.00",  "Debit", "10410.95"],
            ["2025-01-23", "Coffee Shop",             "14.50",  "Debit", "10396.45"],
            ["2025-01-27", "Dividend Income",        "250.00",  "Credit","10646.45"],
            ["2025-01-30", "Streaming Services",      "28.99",  "Debit", "10617.46"],
        ],
    },
    {
        "period": "February 2025",
        "rows": [
            ["2025-02-01", "Rent Payment",         "1500.00",  "Debit",  "9117.46"],
            ["2025-02-03", "Grocery Store",          "112.40",  "Debit",  "9005.06"],
            ["2025-02-05", "Salary Credit",        "4500.00",  "Credit","13505.06"],
            ["2025-02-07", "Pharmacy",                "52.20",  "Debit", "13452.86"],
            ["2025-02-10", "Gym Membership",          "50.00",  "Debit", "13402.86"],
            ["2025-02-13", "Online Shopping",        "340.00",  "Debit", "13062.86"],
            ["2025-02-15", "Utilities Bill",         "195.00",  "Debit", "12867.86"],
            ["2025-02-18", "Coffee Shop",             "16.80",  "Debit", "12851.06"],
            ["2025-02-20", "Restaurant",              "98.50",  "Debit", "12752.56"],
            ["2025-02-22", "Dividend Income",        "250.00",  "Credit","13002.56"],
            ["2025-02-28", "Streaming Services",      "28.99",  "Debit", "12973.57"],
        ],
    },
    {
        "period": "March 2025",
        "rows": [
            ["2025-03-01", "Rent Payment",         "1500.00",  "Debit", "11473.57"],
            ["2025-03-04", "Grocery Store",          "108.60",  "Debit", "11364.97"],
            ["2025-03-06", "Salary Credit",        "4500.00",  "Credit","15864.97"],
            ["2025-03-08", "Pharmacy",                "44.30",  "Debit", "15820.67"],
            ["2025-03-11", "Yoga Classes",            "60.00",  "Debit", "15760.67"],
            ["2025-03-14", "Online Shopping",        "275.50",  "Debit", "15485.17"],
            ["2025-03-17", "Car Insurance",          "180.00",  "Debit", "15305.17"],
            ["2025-03-19", "Restaurant",              "88.90",  "Debit", "15216.27"],
            ["2025-03-22", "Dividend Income",        "250.00",  "Credit","15466.27"],
            ["2025-03-25", "Coffee Shop",             "21.40",  "Debit", "15444.87"],
            ["2025-03-28", "Streaming Services",      "28.99",  "Debit", "15415.88"],
        ],
    },
]

COMBINED_USERS = [
    {"filename": "john_doe_statement_2025.pdf",  "name": "John Doe",   "account": "XXXX-1234", "months": JOHN_MONTHS},
    {"filename": "jane_smith_statement_2025.pdf", "name": "Jane Smith", "account": "XXXX-5678", "months": JANE_MONTHS},
]


def build_month_table(rows):
    table = Table([HEADER] + rows, colWidths=[90, 180, 70, 60, 80])
    table.setStyle(TABLE_STYLE)
    return table


def main():
    for user in COMBINED_USERS:
        doc = SimpleDocTemplate(os.path.join(DATA_DIR, user["filename"]), pagesize=LETTER)
        elements = []

        elements.append(Paragraph("Annual Transaction Statement — 2025", styles["Title"]))
        elements.append(Paragraph(f"Account Holder: {user['name']}", styles["Normal"]))
        elements.append(Paragraph(f"Account Number: {user['account']}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        for i, month in enumerate(user["months"]):
            if i > 0:
                elements.append(PageBreak())
            elements.append(Paragraph(f"Statement Period: {month['period']}", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            elements.append(build_month_table(month["rows"]))

        doc.build(elements)
        print(f"  Generated: {user['filename']}")

    print("\n✅ Combined PDFs generated successfully for both users.")


if __name__ == "__main__":
    main()
