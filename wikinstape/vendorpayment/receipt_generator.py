import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime

class VendorReceiptGenerator:
    def __init__(self, receipt_data):
        self.receipt_data = receipt_data
    
    def generate_pdf(self):
        """Generate PDF receipt"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            alignment=TA_LEFT,
            spaceAfter=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_LEFT
        )
        
        story = []
        
        story.append(Paragraph("Vendor Payment Receipt", title_style))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph(f"<b>Receipt No:</b> {self.receipt_data['receipt_number']}", normal_style))
        story.append(Paragraph(f"<b>Date:</b> {self.receipt_data['date']}", normal_style))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Sender Details", heading_style))
        story.append(Paragraph(f"<b>Name:</b> {self.receipt_data['user']['name']}", normal_style))
        story.append(Paragraph(f"<b>Phone:</b> {self.receipt_data['user']['phone']}", normal_style))
        story.append(Paragraph(f"<b>Email:</b> {self.receipt_data['user']['email']}", normal_style))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Recipient Details", heading_style))
        story.append(Paragraph(f"<b>Name:</b> {self.receipt_data['recipient']['name']}", normal_style))
        story.append(Paragraph(f"<b>Account:</b> {self.receipt_data['recipient']['account']}", normal_style))
        story.append(Paragraph(f"<b>IFSC:</b> {self.receipt_data['recipient']['ifsc']}", normal_style))
        story.append(Paragraph(f"<b>Bank Reference:</b> {self.receipt_data['recipient']['bank_ref']}", normal_style))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Payment Details", heading_style))
        
        amount_data = [
            ['Description', 'Amount (₹)'],
            ['Transfer Amount', f"{self.receipt_data['amount_details']['transfer_amount']:.2f}"],
            ['Processing Fee', f"{self.receipt_data['amount_details']['processing_fee']:.2f}"],
            ['GST (18%)', f"{self.receipt_data['amount_details']['gst']:.2f}"],
            ['', ''],
            ['<b>Total Deducted</b>', f"<b>{self.receipt_data['amount_details']['total_deducted']:.2f}</b>"]
        ]
        
        table = Table(amount_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.5*inch))
        
        story.append(Paragraph("Transaction Information", heading_style))
        story.append(Paragraph(f"<b>Transaction ID:</b> {self.receipt_data['transaction']['id']}", normal_style))
        story.append(Paragraph(f"<b>EKO TID:</b> {self.receipt_data['transaction']['eko_tid']}", normal_style))
        story.append(Paragraph(f"<b>Payment Mode:</b> {self.receipt_data['transaction']['mode']}", normal_style))
        story.append(Paragraph(f"<b>Purpose:</b> {self.receipt_data['transaction']['purpose']}", normal_style))
        story.append(Paragraph(f"<b>Status:</b> {self.receipt_data['transaction']['status']}", normal_style))
        
        story.append(Spacer(1, 1*inch))
        story.append(Paragraph("This is a computer generated receipt.", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)))
        story.append(Paragraph("No signature required.", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)))
        
        doc.build(story)
        
        buffer.seek(0)
        return buffer