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
            'payment_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_date'].input_formats = ['%Y-%m-%dT%H:%M']


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
        fields = ('sales_order', 'bank_name', 'loan_amount',
                  'interest_rate', 'tenure_months', 'emi_amount', 'loan_status')
