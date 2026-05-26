"""
PDF generation for sales invoices and service invoices.
Uses xhtml2pdf (pisa) to render HTML templates to PDF.
"""
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False

from .models import Invoice


# ---------------------------------------------------------------------------
# Amount-in-words helper
# ---------------------------------------------------------------------------

_ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen',
]
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _below_hundred(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + (' ' + _ONES[n % 10] if n % 10 else '')


def _below_thousand(n):
    if n < 100:
        return _below_hundred(n)
    return _ONES[n // 100] + ' Hundred' + (' and ' + _below_hundred(n % 100) if n % 100 else '')


def amount_in_words(amount):
    """Convert a Decimal/float amount to Indian-style words, e.g. '1,23,456 → One Lakh ...'"""
    try:
        amount  = float(amount)
    except (TypeError, ValueError):
        return 'Zero Rupees Only'

    rupees = int(amount)
    paise  = round((amount - rupees) * 100)

    if rupees == 0 and paise == 0:
        return 'Zero Rupees Only'

    parts = []
    n = rupees
    if n >= 10_000_000:
        parts.append(_below_thousand(n // 10_000_000) + ' Crore')
        n %= 10_000_000
    if n >= 100_000:
        parts.append(_below_thousand(n // 100_000) + ' Lakh')
        n %= 100_000
    if n >= 1_000:
        parts.append(_below_thousand(n // 1_000) + ' Thousand')
        n %= 1_000
    if n > 0:
        parts.append(_below_thousand(n))

    words = ' '.join(parts) + ' Rupees'
    if paise:
        words += ' and ' + _below_hundred(paise) + ' Paise'
    return words + ' Only'


# ---------------------------------------------------------------------------
# Core renderer
# ---------------------------------------------------------------------------

def _html_to_pdf(html_string):
    """Render an HTML string to PDF bytes using xhtml2pdf."""
    buf = BytesIO()
    pisa_status = pisa.pisaDocument(BytesIO(html_string.encode('UTF-8')), buf)
    if pisa_status.err:
        return None
    return buf.getvalue()


def _pdf_response(template_name, context, filename):
    """Render template → PDF → HttpResponse. Falls back to HTTP 503 if pisa missing."""
    if not XHTML2PDF_AVAILABLE:
        return HttpResponse('PDF generation unavailable (xhtml2pdf not installed).', status=503)
    html = render_to_string(template_name, context)
    pdf  = _html_to_pdf(html)
    if pdf is None:
        return HttpResponse('PDF generation failed.', status=500)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# Sales Invoice PDF
# ---------------------------------------------------------------------------

@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            'sales_order__customer',
            'sales_order__vehicle__bike_model',
            'sales_order__branch',
            'sales_order__sales_executive',
        ),
        pk=pk,
    )
    order    = invoice.sales_order
    payments = list(invoice.payments.filter(payment_status='completed').order_by('payment_date'))
    loan     = getattr(order, 'loan', None)

    # GST breakdown: 9% CGST + 9% SGST on ex-showroom (subtotal)
    gst_half = (invoice.gst_amount / Decimal('2')).quantize(Decimal('0.01'))

    # Total paid breakdown
    from decimal import Decimal as D
    total_paid = sum(p.amount for p in payments) + (loan.loan_amount if loan else D('0'))
    balance    = invoice.final_amount - total_paid

    context = {
        'invoice':       invoice,
        'order':         order,
        'payments':      payments,
        'loan':          loan,
        'gst_half':      gst_half,
        'amount_words':  amount_in_words(invoice.final_amount),
        'total_paid':    total_paid,
        'balance':       balance,
        'hsn_code':      '87112000',   # HSN for two-wheelers
    }
    return _pdf_response(
        'billing/invoice_pdf.html',
        context,
        f'Invoice-{invoice.invoice_number}.pdf',
    )


# ---------------------------------------------------------------------------
# Service Invoice PDF
# ---------------------------------------------------------------------------

@login_required
def service_invoice_pdf(request, job_card_id):
    from service.models import JobCard

    job_card = get_object_or_404(
        JobCard.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
            'service_invoice',
            'branch',
        ),
        pk=job_card_id,
    )

    try:
        invoice = job_card.service_invoice
    except Exception:
        return HttpResponse('No service invoice found for this job card.', status=404)

    labor_charges   = job_card.labor_charges.all()
    spares_issues   = []
    outwork_entries = job_card.outwork_entries.all()
    gst_half        = (invoice.gst_amount / Decimal('2')).quantize(Decimal('0.01'))

    context = {
        'job_card':       job_card,
        'invoice':        invoice,
        'labor_charges':  labor_charges,
        'spares_issues':  spares_issues,
        'outwork_entries': outwork_entries,
        'gst_half':       gst_half,
        'amount_words':   amount_in_words(invoice.final_amount),
    }
    return _pdf_response(
        'billing/service_invoice_pdf.html',
        context,
        f'ServiceInvoice-JC{job_card_id}.pdf',
    )


# ---------------------------------------------------------------------------
# GAP 27 — Payment Receipt PDF
# ---------------------------------------------------------------------------

from .models import Payment


@login_required
def payment_receipt_pdf(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related('invoice__sales_order__customer'), pk=pk
    )
    try:
        from accounts.models import CompanySettings
        company = CompanySettings.get_instance()
    except Exception:
        company = None

    context = {
        'payment': payment,
        'invoice': payment.invoice,
        'customer': payment.invoice.sales_order.customer,
        'company': company,
        'amount_in_words': amount_in_words(payment.amount),
    }
    html = render_to_string('billing/payment_receipt_pdf.html', context)
    if not XHTML2PDF_AVAILABLE:
        return HttpResponse(html, content_type='text/html')
    buf = BytesIO()
    pisa.CreatePDF(html, dest=buf)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receipt-{payment.pk}.pdf"'
    return response
