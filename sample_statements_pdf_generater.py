from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

statements = {
    "statement_jan_2025.pdf": [
        ["Date", "Description", "Amount", "Type", "Balance"],
        ["2025-01-05", "Opening Balance", "5000.00", "Credit", "5000.00"],
        ["2025-01-10", "Electricity Bill", "180.75", "Debit", "4819.25"],
        ["2025-01-15", "Amazon Purchase", "299.99", "Debit", "4519.26"],
        ["2025-01-25", "Salary Credit", "3000.00", "Credit", "7519.26"],
    ],
    "statement_feb_2025.pdf": [
        ["Date", "Description", "Amount", "Type", "Balance"],
        ["2025-02-01", "Grocery Store", "120.50", "Debit", "4879.50"],
        ["2025-02-02", "Salary Credit", "3000.00", "Credit", "7879.50"],
        ["2025-02-05", "Amazon Purchase", "250.75", "Debit", "7628.75"],
        ["2025-02-18", "Restaurant", "89.40", "Debit", "7539.35"],
    ],
    "statement_mar_2025.pdf": [
        ["Date", "Description", "Amount", "Type", "Balance"],
        ["2025-03-03", "Internet Bill", "75.00", "Debit", "7464.35"],
        ["2025-03-08", "Uber Ride", "32.20", "Debit", "7432.15"],
        ["2025-03-15", "Salary Credit", "3000.00", "Credit", "10432.15"],
        ["2025-03-22", "Flight Booking", "560.00", "Debit", "9872.15"],
    ],
}

styles = getSampleStyleSheet()

for filename, table_data in statements.items():
    doc = SimpleDocTemplate(
        os.path.join(DATA_DIR, filename),
        pagesize=LETTER
    )

    elements = []
    elements.append(Paragraph("Transaction Statement", styles["Title"]))
    elements.append(Paragraph("Account Holder: John Doe", styles["Normal"]))
    elements.append(Paragraph("Account Number: XXXX-1234", styles["Normal"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    table = Table(table_data)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    )

    elements.append(table)
    doc.build(elements)

print("✅ REAL table PDFs generated successfully")
