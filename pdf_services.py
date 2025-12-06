# pdf_service.py
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.units import mm
from reportlab.lib import colors

# ---- Brand colors (Option C) ----
PRIMARY = colors.HexColor("#000000")
SECONDARY = colors.HexColor("#FFFFFF")
ACCENT = colors.HexColor("#F5F5F5")
TEXT = colors.HexColor("#111111")


def generate_invoice_pdf(
    order,
    customer,
    cart,
    subtotal,
    delivery,
    total,
    logo_path="C:\\Users\\djeev\\Downloads\\migfulllogo.png",
    output_dir="bills",
):
    """
    Creates a branded PDF invoice and returns the file path.

    order: row from orders table (tuple)
    customer: row from customers table (tuple)
    cart: list of cart dicts from BillingEngine.cart
    """
    # Safety checks
    if order is None or customer is None:
        raise ValueError("Order or customer data missing for PDF generation")

    os.makedirs(output_dir, exist_ok=True)

    order_id = order[0]
    file_name = f"Medingen_Invoice_{order_id}.pdf"
    file_path = os.path.join(output_dir, file_name)

    # ---- PDF document ----
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        alignment=TA_CENTER,
        textColor=PRIMARY,
        spaceAfter=6,
    )

    small_label = ParagraphStyle(
        "SmallLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=TEXT,
    )

    normal_text = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontSize=10,
        textColor=TEXT,
    )

    right_text = ParagraphStyle(
        "RightText",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_RIGHT,
        textColor=TEXT,
    )

    elements = []

    # ---- Header: logo + company block ----
    header_table_data = []

    # Logo cell
    logo_cell = ""
    if os.path.exists(logo_path):
        img = Image(logo_path, width=40 * mm, height=18 * mm)
        logo_cell = img

    company_block = [
        "<b>Medingen Pharmacy</b>",
        "Saves your Health and Wealth",
        "12, Gandhi Street, Chennai, Tamil Nadu, 600056",
        "Phone: +91-8438644780",
        "Email: support@medingen.in",
        "GST: 33ABCDE1234FZ1",
    ]
    company_para = Paragraph("<br/>".join(company_block), normal_text)

    header_table_data.append([logo_cell, company_para])

    header_table = Table(
        header_table_data,
        colWidths=[50 * mm, 110 * mm],
        hAlign="LEFT",
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    elements.append(header_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("TAX INVOICE", title_style))
    elements.append(Spacer(1, 6))

    # ---- Invoice meta + customer block ----
    invoice_no = f"MED-{order_id:05d}"
    order_date_str = order[9]  # order_date as stored
    try:
        dt = datetime.strptime(order_date_str, "%Y-%m-%d %H:%M:%S")
        formatted_date = dt.strftime("%d-%m-%Y %H:%M")
    except Exception:
        formatted_date = order_date_str

    meta_lines = [
        f"<b>Invoice No:</b> {invoice_no}",
        f"<b>Order Date:</b> {formatted_date}",
        f"<b>Payment Mode:</b> {order[7] or 'N/A'}",
        f"<b>Payment Status:</b> {order[8] or 'N/A'}",
        f"<b>Order Status:</b> {order[5]}",
    ]
    meta_para = Paragraph("<br/>".join(meta_lines), small_label)

    customer_lines = [
        "<b>Bill To:</b>",
        f"{customer[1]}",
        f"Phone: {customer[2]}",
        f"Email: {customer[3]}",
        f"Address: {order[6]}",
    ]
    customer_para = Paragraph("<br/>".join(customer_lines), small_label)

    meta_table = Table(
        [[customer_para, meta_para]],
        colWidths=[90 * mm, 70 * mm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
                ("BOX", (0, 0), (-1, -1), 0.5, PRIMARY),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PRIMARY),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # ---- Items table ----
    table_data = [
        [
            "S. No",
            "Medicine",
            "Qty (strips)",
            "Price / strip (₹)",
            "Line Total (₹)",
            "Expiry",
        ]
    ]

    for idx, item in enumerate(cart, start=1):
        table_data.append(
            [
                str(idx),
                item["name"],
                str(item["quantity"]),
                f"{item['price']:.2f}",
                f"{item['line_total']:.2f}",
                item["expiry_date"],
            ]
        )

    items_table = Table(
        table_data,
        colWidths=[15 * mm, 55 * mm, 25 * mm, 30 * mm, 35 * mm, 30 * mm],
        hAlign="LEFT",
    )

    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), SECONDARY),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),

                ("GRID", (0, 0), (-1, -1), 0.25, PRIMARY),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (5, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), SECONDARY),
            ]
        )
    )

    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # ---- Totals table ----
    totals_data = [
        ["Subtotal:", f"₹ {subtotal:.2f}"],
        ["Delivery charge:", f"₹ {delivery:.2f}"],
        ["Total Amount:", f"₹ {total:.2f}"],
    ]

    totals_table = Table(
        totals_data,
        colWidths=[60 * mm, 40 * mm],
        hAlign="RIGHT",
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
                ("BACKGROUND", (0, 0), (-1, -2), SECONDARY),
                ("BACKGROUND", (0, -1), (-1, -1), ACCENT),
                ("BOX", (0, 0), (-1, -1), 0.5, PRIMARY),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    elements.append(totals_table)
    elements.append(Spacer(1, 15))

    # ---- Footer ----
    footer_text = "Thank you for choosing Medingen."
    footer_para = Paragraph(footer_text, ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=TEXT,
    ))
    elements.append(footer_para)

    # Build PDF
    doc.build(elements)

    return file_path
