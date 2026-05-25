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


class PaymentForm(forms.ModelForm):
    class Meta:
        model  = Payment
        fields = ('invoice', 'payment_method', 'transaction_reference',
                  'amount', 'payment_status', 'payment_date')
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

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
        date = self.cleaned_data.get('payment_date')
        if date and date > timezone.now().date():
            raise forms.ValidationError('Payment date cannot be in the future.')
        return date

    def clean(self):
        from decimal import Decimal
        cleaned_data = super().clean()
        amount  = cleaned_data.get('amount')
        invoice = cleaned_data.get('invoice')
        if amount is not None and invoice is not None:
            if amount > invoice.final_amount:
                self.add_error('amount',
                               f'Payment amount (₹{amount}) cannot exceed invoice total '
                               f'(₹{invoice.final_amount}).')
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
                  'first_emi_date', 'loan_status')
        widgets = {
            'sanctioned_date': forms.DateInput(attrs={'type': 'date'}),
            'first_emi_date':  forms.DateInput(attrs={'type': 'date'}),
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
