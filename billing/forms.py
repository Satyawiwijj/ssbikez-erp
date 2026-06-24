from django import forms

from .models import FinanceLoan, InsurancePolicy, Invoice, Payment


class InvoiceForm(forms.ModelForm):
    class Meta:
        model  = Invoice
        fields = ('sales_order', 'invoice_number', 'subtotal',
                  'gst_amount', 'discount_amount', 'final_amount', 'invoice_date')
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        from decimal import Decimal
        cleaned = super().clean()
        subtotal        = cleaned.get('subtotal') or Decimal('0')
        gst_amount      = cleaned.get('gst_amount') or Decimal('0')
        discount_amount = cleaned.get('discount_amount') or Decimal('0')

        if subtotal < Decimal('0'):
            self.add_error('subtotal', 'Subtotal cannot be negative.')

        # Auto-calculate GST at 18% if not supplied
        if gst_amount == Decimal('0') and subtotal > Decimal('0'):
            try:
                from accounts.models import CompanySettings
                rate = Decimal(str(CompanySettings.get_instance().gst_rate or 18))
            except Exception:
                rate = Decimal('18')
            gst_amount = (subtotal * rate / Decimal('100')).quantize(Decimal('0.01'))
            cleaned['gst_amount'] = gst_amount

        # Always derive final_amount from components
        expected_final = subtotal + gst_amount - discount_amount
        if expected_final < Decimal('0'):
            self.add_error('discount_amount', 'Discount cannot exceed subtotal + GST.')
        else:
            cleaned['final_amount'] = expected_final

        return cleaned


class PaymentForm(forms.ModelForm):
    class Meta:
        model  = Payment
        fields = ('invoice', 'payment_method', 'transaction_reference',
                  'amount', 'payment_status', 'payment_date')
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self._invoice = kwargs.pop('invoice', None)
        super().__init__(*args, **kwargs)
        if self._invoice:
            self.fields['invoice'].initial = self._invoice
        # <input type="date"> submits "YYYY-MM-DD"; ensure DateTimeField accepts
        # it regardless of USE_L10N locale format settings.
        self.fields['payment_date'].input_formats = [
            '%Y-%m-%d', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S',
        ]

    def clean_amount(self):
        from decimal import Decimal
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError('Payment amount is required.')
        if amount <= Decimal('0'):
            raise forms.ValidationError('Payment amount must be greater than zero.')
        return amount

    def clean_payment_date(self):
        from django.utils import timezone
        import datetime
        date = self.cleaned_data.get('payment_date')
        if date:
            now = timezone.now()
            cmp = date.date() if isinstance(date, datetime.datetime) else date
            # Use local timezone date (not UTC) so IST users don't get a false
            # "in the future" error when the UTC date is still the previous day.
            local_today = timezone.localtime(now).date()
            if cmp > local_today:
                raise forms.ValidationError('Payment date cannot be in the future.')
        return date

    def clean(self):
        from decimal import Decimal
        from django.db.models import Sum
        cleaned_data = super().clean()
        amount  = cleaned_data.get('amount')
        invoice = cleaned_data.get('invoice')
        if amount is not None and invoice is not None:
            existing_paid = invoice.payments.exclude(
                payment_status=Payment.PaymentStatus.FAILED,
            )
            if self.instance and self.instance.pk:
                existing_paid = existing_paid.exclude(pk=self.instance.pk)
            existing_paid = existing_paid.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            outstanding = invoice.final_amount - existing_paid
            if amount > outstanding:
                self.add_error('amount',
                               f'Payment amount (₹{amount}) exceeds the outstanding balance '
                               f'(₹{outstanding}) on this invoice.')
        return cleaned_data


class InsurancePolicyForm(forms.ModelForm):
    class Meta:
        model  = InsurancePolicy
        fields = ('sales_order', 'provider_name', 'policy_number',
                  'premium_amount', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date':   forms.DateInput(attrs={'type': 'date'}),
        }


class FinanceLoanForm(forms.ModelForm):
    class Meta:
        model  = FinanceLoan
        fields = ('sales_order', 'bank_name', 'sanctioned_date', 'loan_amount',
                  'interest_rate', 'tenure_months', 'emi_amount',
                  'first_emi_date', 'loan_status',
                  # GAP 29 - HP workflow
                  'hp_status', 'hp_bank_name', 'hp_submission_date',
                  'hp_endorsement_date', 'hp_release_date')
        widgets = {
            'sanctioned_date':     forms.DateInput(attrs={'type': 'date'}),
            'first_emi_date':      forms.DateInput(attrs={'type': 'date'}),
            'hp_submission_date':  forms.DateInput(attrs={'type': 'date'}),
            'hp_endorsement_date': forms.DateInput(attrs={'type': 'date'}),
            'hp_release_date':     forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_name'].help_text      = 'Name of the financing bank or NBFC.'
        self.fields['loan_amount'].help_text    = 'Sanctioned loan principal amount in ₹.'
        self.fields['interest_rate'].help_text  = 'Annual interest rate (5% – 25%).'
        self.fields['tenure_months'].help_text  = 'Loan duration in months (6 – 84).'
        self.fields['emi_amount'].help_text     = 'Monthly EMI amount. Use the calculator below to auto-fill.'
        self.fields['sanctioned_date'].help_text = 'Date the loan was sanctioned by the bank.'
        self.fields['first_emi_date'].help_text  = 'Date the first EMI payment is due.'

    def clean_loan_amount(self):
        from decimal import Decimal
        amount = self.cleaned_data.get('loan_amount')
        if amount is None:
            raise forms.ValidationError('Loan amount is required.')
        if amount <= Decimal('0'):
            raise forms.ValidationError('Loan amount must be greater than zero.')
        return amount

    def clean_interest_rate(self):
        from decimal import Decimal
        rate = self.cleaned_data.get('interest_rate')
        if rate is not None:
            if rate < Decimal('5') or rate > Decimal('25'):
                raise forms.ValidationError('Interest rate must be between 5% and 25%.')
        return rate

    def clean_tenure_months(self):
        tenure = self.cleaned_data.get('tenure_months')
        if tenure is not None:
            if tenure < 6 or tenure > 84:
                raise forms.ValidationError('Tenure must be between 6 and 84 months.')
        return tenure

    def clean_emi_amount(self):
        from decimal import Decimal
        emi = self.cleaned_data.get('emi_amount')
        if emi is not None and emi <= Decimal('0'):
            raise forms.ValidationError('EMI amount must be greater than zero.')
        return emi

    def clean(self):
        from decimal import Decimal
        cleaned_data  = super().clean()
        loan_amount   = cleaned_data.get('loan_amount')
        sales_order   = cleaned_data.get('sales_order')
        tenure_months = cleaned_data.get('tenure_months')
        emi_amount    = cleaned_data.get('emi_amount')

        # Loan cannot exceed order total
        if loan_amount and sales_order:
            try:
                order_total = sales_order.total_amount
                if order_total and loan_amount > order_total:
                    self.add_error('loan_amount',
                                   f'Loan amount (₹{loan_amount}) cannot exceed the '
                                   f'order total (₹{order_total}).')
            except Exception:
                pass

        # EMI sanity check (non-blocking warning if suspiciously low)
        if loan_amount and tenure_months and emi_amount and tenure_months > 0:
            expected_emi = loan_amount / Decimal(str(tenure_months))
            if emi_amount < expected_emi * Decimal('0.60'):
                self.add_error(
                    'emi_amount',
                    f'EMI seems very low. Expected roughly ₹{expected_emi:.0f}/month '
                    f'for a ₹{loan_amount} loan over {tenure_months} months.'
                )
        return cleaned_data


# ===========================================================================
# GAP 18, 25 forms
# ===========================================================================

from django.forms import inlineformset_factory

from .models import JournalEntry, JournalEntryLine, RefundAdvance


class RefundAdvanceForm(forms.ModelForm):
    class Meta:
        model = RefundAdvance
        fields = ('customer', 'transaction_type', 'amount', 'reference_invoice',
                  'reason', 'payment_method', 'status')
        widgets = {'reason': forms.Textarea(attrs={'rows': 3})}


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ('entry_date', 'description', 'is_vehicle_purchase', 'company_gstin',
                  'reference_doctype', 'reference_docname', 'reference_number',
                  'reference_date', 'number_plate_amount', 'multi_currency', 'reference')
        widgets = {
            'entry_date':          forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description':         forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'is_vehicle_purchase': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'company_gstin':       forms.TextInput(attrs={'class': 'form-control'}),
            'reference_doctype':   forms.TextInput(attrs={'class': 'form-control'}),
            'reference_docname':   forms.TextInput(attrs={'class': 'form-control'}),
            'reference_number':    forms.TextInput(attrs={'class': 'form-control'}),
            'reference_date':      forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'number_plate_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'multi_currency':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reference':           forms.TextInput(attrs={'class': 'form-control'}),
        }


class JournalEntryLineForm(forms.ModelForm):
    class Meta:
        model = JournalEntryLine
        fields = ('account', 'party_type', 'party', 'debit', 'credit')
        widgets = {
            'account':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account name'}),
            'party_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Customer, Supplier'}),
            'party':      forms.TextInput(attrs={'class': 'form-control'}),
            'debit':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'credit':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry, JournalEntryLine,
    form=JournalEntryLineForm, extra=2, can_delete=True,
)
