"""
Invoice generation service for MultinotesAI.

This module provides:
- Invoice PDF generation
- Invoice data management
- Email delivery of invoices
"""

import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# =============================================================================
# Invoice Configuration
# =============================================================================

class InvoiceConfig:
    """Invoice configuration settings."""

    # Company details
    COMPANY_NAME = "MultinotesAI"
    COMPANY_ADDRESS = """
    MultinotesAI Private Limited
    123 Tech Park, Sector 5
    City, State - 123456
    India
    """
    COMPANY_EMAIL = "billing@multinotesai.com"
    COMPANY_PHONE = "+91 123 456 7890"
    COMPANY_GST = "GSTIN: 12XXXXX1234X1ZX"
    COMPANY_PAN = "PAN: XXXXX1234X"

    # Invoice settings
    INVOICE_PREFIX = "MNAI"
    CURRENCY = "INR"
    CURRENCY_SYMBOL = "₹"
    TAX_RATE = Decimal("18.0")  # GST 18%

    # Template
    INVOICE_TEMPLATE = "invoices/invoice_template.html"


# =============================================================================
# Invoice Data Model
# =============================================================================

class InvoiceData:
    """Data structure for invoice generation."""

    def __init__(
        self,
        invoice_number: str,
        customer_name: str,
        customer_email: str,
        customer_address: str = "",
        items: list = None,
        subtotal: Decimal = Decimal("0"),
        tax_amount: Decimal = Decimal("0"),
        total: Decimal = Decimal("0"),
        payment_method: str = "",
        payment_id: str = "",
        invoice_date: datetime = None,
        due_date: datetime = None,
        notes: str = "",
    ):
        self.invoice_number = invoice_number
        self.customer_name = customer_name
        self.customer_email = customer_email
        self.customer_address = customer_address
        self.items = items or []
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total = total
        self.payment_method = payment_method
        self.payment_id = payment_id
        self.invoice_date = invoice_date or datetime.now()
        self.due_date = due_date
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_address': self.customer_address,
            'items': self.items,
            'subtotal': str(self.subtotal),
            'tax_amount': str(self.tax_amount),
            'total': str(self.total),
            'payment_method': self.payment_method,
            'payment_id': self.payment_id,
            'invoice_date': self.invoice_date.strftime('%B %d, %Y'),
            'due_date': self.due_date.strftime('%B %d, %Y') if self.due_date else None,
            'notes': self.notes,
        }


# =============================================================================
# Invoice Generator
# =============================================================================

class InvoiceGenerator:
    """
    Generate invoices for subscription payments.

    Usage:
        generator = InvoiceGenerator()
        pdf_bytes = generator.generate_pdf(invoice_data)
    """

    def __init__(self):
        self.config = InvoiceConfig

    def generate_invoice_number(self, subscription_id: int) -> str:
        """Generate unique invoice number."""
        date_part = datetime.now().strftime('%Y%m')
        return f"{self.config.INVOICE_PREFIX}-{date_part}-{subscription_id:06d}"

    def calculate_tax(self, amount: Decimal) -> Dict[str, Decimal]:
        """
        Calculate tax breakdown.

        Args:
            amount: Base amount before tax

        Returns:
            Dict with subtotal, tax_amount, total
        """
        tax_rate = self.config.TAX_RATE / 100
        tax_amount = amount * tax_rate
        total = amount + tax_amount

        return {
            'subtotal': amount,
            'tax_rate': self.config.TAX_RATE,
            'tax_amount': tax_amount.quantize(Decimal('0.01')),
            'total': total.quantize(Decimal('0.01')),
        }

    def create_invoice_data(
        self,
        subscription,
        payment=None,
    ) -> InvoiceData:
        """
        Create invoice data from subscription and payment.

        Args:
            subscription: Subscription model instance
            payment: Optional payment model instance

        Returns:
            InvoiceData object
        """
        user = subscription.user
        plan = subscription.plan

        # Calculate amounts
        base_amount = Decimal(str(plan.price))
        tax_info = self.calculate_tax(base_amount)

        # Build line items
        items = [{
            'description': f"{plan.name} Subscription",
            'period': f"{subscription.start_date.strftime('%b %d')} - {subscription.end_date.strftime('%b %d, %Y')}",
            'quantity': 1,
            'unit_price': str(base_amount),
            'amount': str(base_amount),
        }]

        # Create invoice data
        invoice_data = InvoiceData(
            invoice_number=self.generate_invoice_number(subscription.id),
            customer_name=user.get_full_name() or user.email,
            customer_email=user.email,
            customer_address="",  # Can be fetched from user profile
            items=items,
            subtotal=tax_info['subtotal'],
            tax_amount=tax_info['tax_amount'],
            total=tax_info['total'],
            payment_method=payment.payment_method if payment else "Razorpay",
            payment_id=payment.razorpay_payment_id if payment else "",
            invoice_date=datetime.now(),
            notes="Thank you for your subscription!",
        )

        return invoice_data

    def generate_html(self, invoice_data: InvoiceData) -> str:
        """
        Generate HTML invoice.

        Args:
            invoice_data: InvoiceData object

        Returns:
            HTML string
        """
        context = {
            'invoice': invoice_data.to_dict(),
            'company': {
                'name': self.config.COMPANY_NAME,
                'address': self.config.COMPANY_ADDRESS,
                'email': self.config.COMPANY_EMAIL,
                'phone': self.config.COMPANY_PHONE,
                'gst': self.config.COMPANY_GST,
                'pan': self.config.COMPANY_PAN,
            },
            'currency': self.config.CURRENCY_SYMBOL,
            'tax_rate': str(self.config.TAX_RATE),
        }

        # Try to render template, fall back to inline HTML
        try:
            html = render_to_string(self.config.INVOICE_TEMPLATE, context)
        except Exception:
            html = self._generate_inline_html(context)

        return html

    def _generate_inline_html(self, context: Dict) -> str:
        """Generate inline HTML when template is not available."""
        invoice = context['invoice']
        company = context['company']
        currency = context['currency']

        items_html = ""
        for item in invoice['items']:
            items_html += f"""
            <tr>
                <td>{item['description']}<br><small>{item.get('period', '')}</small></td>
                <td style="text-align: center;">{item['quantity']}</td>
                <td style="text-align: right;">{currency}{item['unit_price']}</td>
                <td style="text-align: right;">{currency}{item['amount']}</td>
            </tr>
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Invoice {invoice['invoice_number']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 40px; }}
        .company-info {{ text-align: left; }}
        .invoice-info {{ text-align: right; }}
        .company-name {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .invoice-title {{ font-size: 28px; color: #3498db; margin-bottom: 10px; }}
        .customer-info {{ margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #3498db; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        .totals {{ margin-top: 20px; text-align: right; }}
        .totals table {{ width: 300px; margin-left: auto; }}
        .totals td {{ border: none; }}
        .total-row {{ font-weight: bold; font-size: 18px; color: #2c3e50; }}
        .footer {{ margin-top: 40px; text-align: center; color: #666; font-size: 12px; }}
        .paid-stamp {{ color: #27ae60; font-size: 24px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="company-info">
            <div class="company-name">{company['name']}</div>
            <pre style="margin: 10px 0; font-family: Arial;">{company['address']}</pre>
            <div>{company['email']}</div>
            <div>{company['gst']}</div>
        </div>
        <div class="invoice-info">
            <div class="invoice-title">INVOICE</div>
            <div><strong>Invoice #:</strong> {invoice['invoice_number']}</div>
            <div><strong>Date:</strong> {invoice['invoice_date']}</div>
            <div class="paid-stamp">PAID</div>
        </div>
    </div>

    <div class="customer-info">
        <strong>Bill To:</strong><br>
        {invoice['customer_name']}<br>
        {invoice['customer_email']}<br>
        {invoice['customer_address']}
    </div>

    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th style="text-align: center;">Qty</th>
                <th style="text-align: right;">Unit Price</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {items_html}
        </tbody>
    </table>

    <div class="totals">
        <table>
            <tr>
                <td>Subtotal:</td>
                <td style="text-align: right;">{currency}{invoice['subtotal']}</td>
            </tr>
            <tr>
                <td>GST ({context['tax_rate']}%):</td>
                <td style="text-align: right;">{currency}{invoice['tax_amount']}</td>
            </tr>
            <tr class="total-row">
                <td>Total:</td>
                <td style="text-align: right;">{currency}{invoice['total']}</td>
            </tr>
        </table>
    </div>

    <div style="margin-top: 30px; padding: 15px; background: #f0f0f0; border-radius: 5px;">
        <strong>Payment Information:</strong><br>
        Method: {invoice['payment_method']}<br>
        Transaction ID: {invoice['payment_id']}
    </div>

    <div class="footer">
        <p>{invoice['notes']}</p>
        <p>This is a computer-generated invoice and does not require a signature.</p>
        <p>{company['name']} | {company['email']} | {company['phone']}</p>
    </div>
</body>
</html>
        """
        return html

    def generate_pdf(self, invoice_data: InvoiceData) -> bytes:
        """
        Generate PDF invoice.

        Args:
            invoice_data: InvoiceData object

        Returns:
            PDF bytes
        """
        try:
            from weasyprint import HTML
        except ImportError:
            logger.error("WeasyPrint not installed")
            raise ImportError("PDF generation requires WeasyPrint: pip install weasyprint")

        html_content = self.generate_html(invoice_data)
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return pdf_bytes


# =============================================================================
# Invoice Service
# =============================================================================

class InvoiceService:
    """
    High-level invoice service for the application.

    Usage:
        service = InvoiceService()
        pdf = service.generate_subscription_invoice(subscription)
        service.send_invoice_email(subscription, pdf)
    """

    def __init__(self):
        self.generator = InvoiceGenerator()

    def generate_subscription_invoice(
        self,
        subscription,
        payment=None,
    ) -> tuple:
        """
        Generate invoice for subscription payment.

        Args:
            subscription: Subscription instance
            payment: Optional payment instance

        Returns:
            tuple: (pdf_bytes, invoice_number)
        """
        invoice_data = self.generator.create_invoice_data(subscription, payment)
        pdf_bytes = self.generator.generate_pdf(invoice_data)

        return pdf_bytes, invoice_data.invoice_number

    def send_invoice_email(
        self,
        subscription,
        pdf_bytes: bytes,
        invoice_number: str,
    ) -> bool:
        """
        Send invoice via email.

        Args:
            subscription: Subscription instance
            pdf_bytes: PDF invoice content
            invoice_number: Invoice number

        Returns:
            bool: Success status
        """
        try:
            from django.core.mail import EmailMessage

            user = subscription.user
            plan = subscription.plan

            subject = f"Invoice {invoice_number} - {InvoiceConfig.COMPANY_NAME}"
            body = f"""
Dear {user.get_full_name() or user.email},

Thank you for your subscription to {plan.name}!

Please find your invoice attached to this email.

Invoice Number: {invoice_number}
Plan: {plan.name}
Amount: ₹{plan.price}

If you have any questions, please contact us at {InvoiceConfig.COMPANY_EMAIL}.

Best regards,
{InvoiceConfig.COMPANY_NAME} Team
            """

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach(
                f"invoice_{invoice_number}.pdf",
                pdf_bytes,
                'application/pdf'
            )
            email.send()

            logger.info(f"Invoice {invoice_number} sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

invoice_service = InvoiceService()
