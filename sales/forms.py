from django import forms
from accounts.forms import AccessibleFormMixin
from django.db.models import Q
from django.utils import timezone

from customers.models import VehicleStock

from django.forms import inlineformset_factory

from .models import (AdditionalVehicleFitting, DeliveryNoteAdvancePayment,
                     DeliveryNoteItem, DeliveryNotePaymentEntry, ExchangeVehicle,
                     Prospect, SalesAppointment, SalesFeedback, SalesEnquiry,
                     SalesEnquiryCallLog, SalesEnquiryHistory, SalesFeedbackItem,
                     SalesOrderAdvancePayment, VehicleAllotment, VehicleDelivery,
                     VehicleFitting, VehicleSalesOrder, VehicleSaleItem,
                     Dealer, ExchangeVehicleDealer, ExchangeVehicleDealerItem,
                     ExchangeDealerPayment, ExchangeDealerPaymentItem,
                     DealerRCHandOver, DealerRCHandOverItem)


class SalesEnquiryForm(AccessibleFormMixin, forms.ModelForm):
    """
    Handles both:
      • New prospect enquiry  — fill prospect_name + prospect_phone (customer optional)
      • Existing customer enquiry — select customer (prospect fields optional)
    On save, creates a Prospect record when no customer is supplied.
    """
    prospect_name  = forms.CharField(
        max_length=200, required=False, label='Prospect Name',
        widget=forms.TextInput(attrs={'placeholder': 'Full name of walk-in visitor'}),
        help_text='Fill if the visitor is not yet a registered customer.'
    )
    prospect_phone = forms.CharField(
        max_length=15, required=False, label='Prospect Phone',
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number'}),
    )

    class Meta:
        model  = SalesEnquiry
        fields = (
            'customer', 'sales_executive', 'bike_model', 'branch',
            'enquiry_source', 'status', 'whatsapp_no', 'email',
            'purpose', 'expected_purchase_date',
            # ERP alignment
            'customer_enquiry_date', 'customer_type', 'gender', 'enquiry_type',
            'test_ride_taken', 'payment_type', 'customer_interested_in_exchange',
            'source_of_information',
            'address_line1', 'address_line2', 'address_line3', 'address_line4',
            'district', 'city', 'state', 'pincode',
            'remarks',
            # Trade-in pre-assessment
            'exchange_type', 'exchange_vehicle_model_and_make', 'exchange_year_of_manufacturing',
            'exchange_owner_type', 'exchange_valid_insurance', 'exchange_original_rc_available',
            'exchange_customer_expected_price', 'exchange_price_offer_by_dealer',
        )
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'expected_purchase_date':  forms.DateInput(attrs={'type': 'date'}),
            'customer_enquiry_date':   forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].required = False
        self.fields['customer'].help_text = (
            'Select an existing customer, OR fill Prospect Name + Phone above.'
        )
        # If editing an existing enquiry that has a prospect, pre-fill the fields
        if self.instance and self.instance.pk and self.instance.prospect:
            p = self.instance.prospect
            self.fields['prospect_name'].initial  = p.full_name
            self.fields['prospect_phone'].initial = p.phone

    def clean(self):
        cleaned_data   = super().clean()
        customer       = cleaned_data.get('customer')
        prospect_name  = (cleaned_data.get('prospect_name') or '').strip()
        prospect_phone = (cleaned_data.get('prospect_phone') or '').strip()
        if not customer and not (prospect_name and prospect_phone):
            raise forms.ValidationError(
                'Please either select an existing Customer '
                'or enter a Prospect Name and Phone Number.'
            )
        if not customer and prospect_name and prospect_phone:
            # Resolve the prospect/customer here, not in save(): Django's
            # ModelForm._post_clean() runs instance.full_clean() (which enforces
            # SalesEnquiry.clean()'s "customer or prospect required" rule) right
            # after this method returns, before save() is ever called — so
            # instance.customer/instance.prospect must already be set by now.
            # Setting cleaned_data['customer'] (not self.instance.customer
            # directly) matters: construct_instance() overwrites instance.customer
            # from cleaned_data right after this method returns.
            from customers.models import Customer
            existing_customer = Customer.objects.filter(phone=prospect_phone).first()
            if existing_customer:
                cleaned_data['customer'] = existing_customer
            else:
                prospect, _ = Prospect.objects.get_or_create(
                    phone=prospect_phone,
                    defaults={
                        'full_name':           prospect_name,
                        'vehicle_of_interest': cleaned_data.get('bike_model'),
                        'enquiry_source':      cleaned_data.get('enquiry_source') or '',
                    }
                )
                self.instance.prospect = prospect
        return cleaned_data


class SalesAppointmentForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = SalesAppointment
        fields = (
            'enquiry', 'appointment_date', 'purpose', 'status',
            'vehicle_code', 'vehicle_name', 'gender', 'phone_no', 'address',
            'whatsapp_no', 'is_cancelled_postponed', 'cancel_reason',
        )
        widgets = {
            'appointment_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'address':       forms.Textarea(attrs={'rows': 2}),
            'cancel_reason': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment_date'].input_formats = ['%Y-%m-%dT%H:%M']
        # Auto-fill phone/vehicle from enquiry on new forms
        if not self.instance.pk and 'enquiry' not in (self.data or {}):
            pass
        for field in ('vehicle_code', 'vehicle_name', 'gender', 'address', 'whatsapp_no', 'cancel_reason'):
            self.fields[field].required = False

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date:
            instance_date = getattr(self.instance, 'appointment_date', None)
            if not self.instance.pk or instance_date != date:
                if date < timezone.now():
                    raise forms.ValidationError('Appointment date cannot be in the past.')
        return date


class SalesFeedbackForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = SalesFeedback
        fields = (
            'enquiry', 'appointment', 'vehicle_name', 'phone_no',
            'feedback_notes', 'next_followup_date', 'feed_back_date', 'created_by',
        )
        widgets = {
            'feedback_notes':     forms.Textarea(attrs={'rows': 3}),
            'next_followup_date': forms.DateInput(attrs={'type': 'date'}),
            'feed_back_date':     forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('vehicle_name', 'phone_no', 'feed_back_date', 'appointment'):
            self.fields[field].required = False


class VehicleChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        parts = [str(obj.bike_model)]
        if obj.chassis_no:
            parts.append(obj.chassis_no)
        if obj.color:
            parts.append(obj.color)
        return ' — '.join(parts)


class VehicleSalesOrderForm(AccessibleFormMixin, forms.ModelForm):
    vehicle = VehicleChoiceField(
        queryset=VehicleStock.objects.none(),
        required=False,
        help_text='Only available (unsold) vehicles are listed. Leave blank for orders that are not for a specific vehicle (e.g. spares/accessories-only orders).',
    )

    class Meta:
        model  = VehicleSalesOrder
        fields = (
            'enquiry', 'customer', 'vehicle', 'sales_executive', 'branch',
            'order_form_series',
            'insurance_name', 'sales_finance', 'gst_category', 'delivery_date',
            'special_helmet', 'helmet_name', 'helmet_price', 'special_helmet_warehouse', 'default_helmet',
            'has_vehicle_exchange', 'finance_closing', 'exchange_amount',
            'temp_charges_applied', 'temp_charges', 'temp_area',
            'booking_amount', 'discount_amount', 'total_amount', 'sales_status',
            'invoice_discount', 'is_finance_done', 'table_charges_total', 'delivery_discount',
            'finance_amount', 'additional_discount_amount', 'payment_reference',
            'number_plate_amount', 'balance_payment', 'payment_status', 'customer_refund',
        )
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'temp_area':     forms.TextInput(attrs={'placeholder': 'e.g. within city / outstation'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status=VehicleStock.StockStatus.AVAILABLE
        ).select_related('bike_model').order_by('bike_model__model_name')
        self.fields['total_amount'].help_text  = 'Full on-road / ex-showroom price. Minimum ₹50,000.'
        self.fields['booking_amount'].help_text = 'Advance collected at booking. Minimum ₹1,000.'
        self.fields['discount_amount'].help_text = 'Maximum discount is 20% of total amount.'
        self.fields['order_form_series'].required = False
        # total_amount is always derived from the items formset in the view
        # (VehicleSalesOrder.recompute_totals) — same pattern InvoiceForm
        # already uses for gst_amount/final_amount. Don't force the user to
        # guess a number before the items formset has even been saved.
        self.fields['total_amount'].required = False
        # Not required at the widget level: when the linked enquiry only has a
        # Prospect (no Customer yet), clean() below auto-creates/links the
        # Customer instead of requiring the user to pick one that doesn't exist.
        self.fields['customer'].required = False

    def clean(self):
        from decimal import Decimal
        cleaned_data    = super().clean()
        customer        = cleaned_data.get('customer')
        enquiry         = cleaned_data.get('enquiry')
        branch          = cleaned_data.get('branch')
        booking_amount  = cleaned_data.get('booking_amount')
        total_amount    = cleaned_data.get('total_amount')
        discount_amount = cleaned_data.get('discount_amount')

        if branch and not branch.allow_without_enquiry_form and not enquiry:
            self.add_error(
                'enquiry',
                'This branch requires a linked Sales Enquiry before a Sales Order can be created.'
            )

        if not customer and enquiry and enquiry.prospect_id and not enquiry.customer_id:
            # Auto-create/link a Customer from the Prospect on save only
            # (never as a GET side effect — see order_create view). Mirrors
            # the SalesEnquiryForm.clean() prospect->customer resolution:
            # cleaned_data['customer'] is what construct_instance() picks up
            # for self.instance.customer right after this method returns.
            from customers.models import Customer
            prospect = enquiry.prospect
            existing = Customer.objects.filter(phone=prospect.phone).first()
            if existing:
                customer = existing
            else:
                # Copy every field that actually overlaps between the
                # Prospect/Enquiry data captured so far and the Customer
                # model: full_name + phone (from Prospect), email + address
                # (only captured on the Enquiry, not on Prospect itself).
                # Customer has no gender field, so gender cannot be copied.
                address_parts = [p for p in [
                    enquiry.address_line1, enquiry.address_line2,
                    enquiry.address_line3, enquiry.address_line4,
                    enquiry.city, enquiry.district, enquiry.state, enquiry.pincode,
                ] if p]
                customer = Customer.objects.create(
                    full_name=prospect.full_name,
                    phone=prospect.phone,
                    email=enquiry.email or '',
                    address=', '.join(address_parts),
                    # Carry the enquiry's state through so the new Customer's
                    # GST locality (used by billing.split_gst for CGST/SGST
                    # vs. IGST) is populated instead of always defaulting to
                    # blank/intrastate.
                    state=enquiry.state or '',
                )
            SalesEnquiry.objects.filter(pk=enquiry.pk).update(customer=customer)
            cleaned_data['customer'] = customer
        elif not customer:
            self.add_error(
                'customer',
                'Select a Customer, or select an Enquiry that has a linked Prospect '
                'so one can be auto-created.'
            )

        if total_amount is not None and total_amount < Decimal('50000'):
            self.add_error('total_amount', 'Total amount must be at least ₹50,000.')

        if booking_amount is not None and booking_amount < Decimal('1000'):
            self.add_error('booking_amount', 'Booking amount must be at least ₹1,000.')

        if booking_amount is not None and total_amount is not None:
            if booking_amount > total_amount:
                self.add_error('booking_amount',
                               'Booking amount cannot exceed the total order amount.')

        if discount_amount is not None and discount_amount < 0:
            self.add_error('discount_amount', 'Discount amount cannot be negative.')

        if discount_amount is not None and total_amount is not None and total_amount > 0:
            max_discount = total_amount * Decimal('0.20')
            if discount_amount > max_discount:
                self.add_error('discount_amount',
                               f'Discount cannot exceed 20% of total amount (₹{max_discount:.0f}).')

        # total_amount is optional here (see __init__) because it's always
        # recomputed from the items formset right after save — but the
        # column itself is NOT NULL, so the initial order.save() (before the
        # items formset even exists yet) needs a placeholder, not None.
        if cleaned_data.get('total_amount') is None:
            cleaned_data['total_amount'] = Decimal('0')

        return cleaned_data


class VehicleDeliveryForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleDelivery
        fields = (
            'sales_order', 'delivery_date', 'delivered_by', 'remarks',
            'checklist_insurance', 'checklist_rc_book', 'checklist_warranty',
            'checklist_toolkit', 'checklist_accessories', 'issue_gate_pass',
            'manager_approval_requested', 'manager_approved', 'finance_approved',
            'offer_petrol', 'petrol_type', 'petrol_litre', 'petrol_amount', 'bunk_name',
            'total_quantity', 'invoice_discount', 'table_charges_total', 'finance_amount',
            'additional_discount', 'total_amount', 'sales_order_additional_discount',
            'pending_amount', 'advance_amount', 'refund_amount', 'payment_status',
        )
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks':       forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A Delivery Note can only be raised against an order that's actually
        # Submitted — a Draft order isn't a confirmed sale yet. Restrict the
        # picker instead of only catching it after the fact.
        qs = VehicleSalesOrder.objects.filter(
            docstatus=VehicleSalesOrder.DocStatus.SUBMITTED
        ).select_related('customer', 'vehicle__bike_model').order_by('-created_at')
        instance_order_id = getattr(self.instance, 'sales_order_id', None)
        if instance_order_id and not qs.filter(pk=instance_order_id).exists():
            # Editing an existing delivery whose order somehow isn't in the
            # restricted set (e.g. legacy data) — keep it selectable so the
            # existing record doesn't become uneditable.
            qs = VehicleSalesOrder.objects.filter(
                Q(pk=instance_order_id) | Q(docstatus=VehicleSalesOrder.DocStatus.SUBMITTED)
            ).select_related('customer', 'vehicle__bike_model').order_by('-created_at')
        self.fields['sales_order'].queryset = qs

    def clean_sales_order(self):
        order = self.cleaned_data.get('sales_order')
        if order and order.docstatus != VehicleSalesOrder.DocStatus.SUBMITTED:
            raise forms.ValidationError(
                'Cannot create a delivery against an order that has not been Submitted yet.'
            )
        return order


class ExchangeVehicleForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = ExchangeVehicle
        fields = ('sales_order', 'old_vehicle_model', 'manufacturing_company', 'colour',
                  'vehicle_category', 'sub_group', 'registration_no', 'chassis_no', 'engine_no',
                  'year_of_make', 'valuation_amount', 'hp_endorsement', 'rc_handed_over',
                  'rc_handover_date', 'insurance_valid_upto', 'target_warehouse', 'payment_status')
        widgets = {
            'registration_no':      forms.TextInput(attrs={'placeholder': 'e.g. TN11CD5678'}),
            'rc_handover_date':     forms.DateInput(attrs={'type': 'date'}),
            'insurance_valid_upto': forms.DateInput(attrs={'type': 'date'}),
            'year_of_make':         forms.NumberInput(attrs={'placeholder': 'e.g. 2019'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_vehicle_model'].required = True
        self.fields['registration_no'].required   = True
        self.fields['valuation_amount'].required  = True
        self.fields['registration_no'].help_text  = 'Vehicle registration number, e.g. TN11CD5678'
        self.fields['valuation_amount'].help_text = 'Assessed trade-in value in ₹'

    def clean_registration_no(self):
        import re
        value = (self.cleaned_data.get('registration_no') or '').strip().upper()
        if not value:
            raise forms.ValidationError('Registration number is required.')
        if not re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$', value):
            raise forms.ValidationError(
                'Enter a valid registration number, e.g. TN11CD5678.'
            )
        return value

    def clean_valuation_amount(self):
        from decimal import Decimal
        amount = self.cleaned_data.get('valuation_amount')
        if amount is None:
            raise forms.ValidationError('Valuation amount is required.')
        if amount <= Decimal('0'):
            raise forms.ValidationError('Valuation amount must be greater than zero.')
        return amount


class VehicleAllotmentForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleAllotment
        fields = ('sales_order', 'vehicle', 'notes')
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this allotment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only available or reserved vehicles can be allotted
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status__in=['available', 'reserved']
        ).select_related('bike_model')


class VehicleFittingForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleFitting
        fields = ('sales_order', 'fitting_name', 'description', 'cost')
        widgets = {
            'description':  forms.Textarea(attrs={'rows': 2}),
            'fitting_name': forms.TextInput(attrs={'placeholder': 'e.g. Crash Guard, Seat Cover, Side Box'}),
        }

    def clean_cost(self):
        from decimal import Decimal
        cost = self.cleaned_data.get('cost')
        if cost is None or cost < Decimal('0'):
            raise forms.ValidationError('Cost cannot be negative.')
        return cost


class VehicleFittingLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleFitting
        fields = ('fitting_name', 'description', 'cost')
        widgets = {
            'fitting_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Crash Guard, Seat Cover, Side Box'}),
            'description':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional details'}),
            'cost':         forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


VehicleFittingFormSet = inlineformset_factory(
    VehicleSalesOrder, VehicleFitting,
    form=VehicleFittingLineForm, extra=2, can_delete=True
)


# ---------------------------------------------------------------------------
# Reference-parity child tables — Additional Fittings, Items, Advance Payments
# (Sales Order) and Delivery Note Items / Advance Payments / Payment Entries
# (Vehicle Delivery)
# ---------------------------------------------------------------------------

class AdditionalVehicleFittingLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = AdditionalVehicleFitting
        fields = ('item_code', 'item_name', 'quantity', 'rate')
        widgets = {
            'item_code': forms.TextInput(attrs={'class': 'form-control'}),
            'item_name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rate':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


AdditionalVehicleFittingFormSet = inlineformset_factory(
    VehicleSalesOrder, AdditionalVehicleFitting,
    form=AdditionalVehicleFittingLineForm, extra=1, can_delete=True
)


class VehicleSaleItemLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleSaleItem
        fields = ('item_name', 'quantity', 'rate')
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rate':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


VehicleSaleItemFormSet = inlineformset_factory(
    VehicleSalesOrder, VehicleSaleItem,
    form=VehicleSaleItemLineForm, extra=1, can_delete=True
)


class SalesOrderAdvancePaymentLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = SalesOrderAdvancePayment
        fields = ('mode_of_payment', 'draft_type', 'date', 'amount', 'to_account')
        widgets = {
            'mode_of_payment': forms.TextInput(attrs={'class': 'form-control'}),
            'draft_type':      forms.TextInput(attrs={'class': 'form-control'}),
            'date':            forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'to_account':      forms.TextInput(attrs={'class': 'form-control'}),
        }


SalesOrderAdvancePaymentFormSet = inlineformset_factory(
    VehicleSalesOrder, SalesOrderAdvancePayment,
    form=SalesOrderAdvancePaymentLineForm, extra=1, can_delete=True
)


class DeliveryNoteItemLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = DeliveryNoteItem
        fields = ('item_code', 'warranty_rsa_amc', 'rate', 'actual_amount')
        widgets = {
            'item_code':        forms.TextInput(attrs={'class': 'form-control'}),
            'warranty_rsa_amc': forms.Select(attrs={'class': 'form-select'}),
            'rate':             forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'actual_amount':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


DeliveryNoteItemFormSet = inlineformset_factory(
    VehicleDelivery, DeliveryNoteItem,
    form=DeliveryNoteItemLineForm, extra=1, can_delete=True
)


class DeliveryNoteAdvancePaymentLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = DeliveryNoteAdvancePayment
        fields = ('mode_of_payment', 'date', 'amount', 'to_account')
        widgets = {
            'mode_of_payment': forms.TextInput(attrs={'class': 'form-control'}),
            'date':            forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'to_account':      forms.TextInput(attrs={'class': 'form-control'}),
        }


DeliveryNoteAdvancePaymentFormSet = inlineformset_factory(
    VehicleDelivery, DeliveryNoteAdvancePayment,
    form=DeliveryNoteAdvancePaymentLineForm, extra=1, can_delete=True
)


class DeliveryNotePaymentEntryLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = DeliveryNotePaymentEntry
        fields = ('date', 'amount', 'mode_of_payment')
        widgets = {
            'date':            forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mode_of_payment': forms.TextInput(attrs={'class': 'form-control'}),
        }


DeliveryNotePaymentEntryFormSet = inlineformset_factory(
    VehicleDelivery, DeliveryNotePaymentEntry,
    form=DeliveryNotePaymentEntryLineForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# ERP Alignment — inline formsets for call logs, history, feedback items
# ---------------------------------------------------------------------------

class CallLogForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = SalesEnquiryCallLog
        fields = ('unique_id', 'call_from', 'bill_sec', 'start_time', 'audio_url', 'notes')
        widgets = {
            'unique_id':  forms.TextInput(attrs={'class': 'form-control'}),
            'call_from':  forms.TextInput(attrs={'class': 'form-control'}),
            'bill_sec':   forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'audio_url':  forms.URLInput(attrs={'class': 'form-control'}),
            'notes':      forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class HistoryForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = SalesEnquiryHistory
        fields = ('update_date', 'remarks', 'status')
        widgets = {
            'update_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks':     forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status':      forms.Select(attrs={'class': 'form-select'}),
        }


class FeedbackItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = SalesFeedbackItem
        fields = ('points', 'feedback_type', 'response', 'rating')
        widgets = {
            'points':        forms.TextInput(attrs={'class': 'form-control'}),
            'feedback_type': forms.Select(attrs={'class': 'form-select'}),
            'response':      forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'rating':        forms.Select(attrs={'class': 'form-select'}),
        }


CallLogFormSet = inlineformset_factory(
    SalesEnquiry, SalesEnquiryCallLog,
    form=CallLogForm, extra=1, can_delete=True
)

HistoryFormSet = inlineformset_factory(
    SalesEnquiry, SalesEnquiryHistory,
    form=HistoryForm, extra=1, can_delete=True
)

FeedbackItemFormSet = inlineformset_factory(
    SalesFeedback, SalesFeedbackItem,
    form=FeedbackItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# FEATURE 1 — Sales Target Form
# ---------------------------------------------------------------------------

from .models import SalesTarget, TestRideLog, PDIChecklist


class SalesTargetForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SalesTarget
        fields = ('sales_executive', 'month', 'year', 'target_enquiries',
                  'target_test_rides', 'target_conversions', 'target_revenue')
        widgets = {
            'month': forms.NumberInput(attrs={'min': 1, 'max': 12}),
            'year':  forms.NumberInput(attrs={'min': 2024, 'max': 2035}),
        }


class TestRideLogForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = TestRideLog
        fields = ('enquiry', 'vehicle', 'rider_name', 'rider_phone',
                  'license_number', 'accompanied_by', 'start_time',
                  'start_odometer', 'feedback_after_ride')
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'feedback_after_ride': forms.Textarea(attrs={'rows': 2}),
        }


class PDIChecklistForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = PDIChecklist
        exclude = ('sales_order', 'inspected_by', 'inspection_date',
                   'is_approved', 'approved_by')
        widgets = {'overall_remarks': forms.Textarea(attrs={'rows': 3})}


# ---------------------------------------------------------------------------
# Phase 13 -- Dealer sub-module
# ---------------------------------------------------------------------------

class DealerForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = Dealer
        fields = ('dealer_name', 'gstin', 'mobile_number', 'gst_category', 'warehouse',
                  'email', 'branch', 'address_type', 'address_line1', 'state', 'country',
                  'citytown', 'pincode')


class ExchangeVehicleDealerForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ExchangeVehicleDealer
        fields = ('date', 'from_warehouse', 'to_warehouse', 'dealer', 'branch',
                  'hp_endorsement', 'insurance_received')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


class ExchangeVehicleDealerItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ExchangeVehicleDealerItem
        fields = ('vehicle_name', 'engine_number', 'registration_number', 'party_name',
                  'rc_book_received', 'rc_book_number', 'noc', 'to_received',
                  'vehicle_amount', 'color', 'vehicle_value', 'vehicle_code')


ExchangeVehicleDealerItemFormSet = inlineformset_factory(
    ExchangeVehicleDealer, ExchangeVehicleDealerItem, form=ExchangeVehicleDealerItemForm,
    extra=1, can_delete=True
)


class ExchangeDealerPaymentForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ExchangeDealerPayment
        fields = ('date', 'dealer', 'exchange_vehicle_dealer', 'branch', 'payment_mode',
                  'total_amount', 'pending_amount', 'payment_status')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['exchange_vehicle_dealer'].required = False


class ExchangeDealerPaymentItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ExchangeDealerPaymentItem
        fields = ('register_number', 'vehicle_name', 'vehicle_amount', 'allow_permission', 'date')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


ExchangeDealerPaymentItemFormSet = inlineformset_factory(
    ExchangeDealerPayment, ExchangeDealerPaymentItem, form=ExchangeDealerPaymentItemForm,
    extra=1, can_delete=True
)


class DealerRCHandOverForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = DealerRCHandOver
        fields = ('dealer',)


class DealerRCHandOverItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = DealerRCHandOverItem
        fields = ('register_number', 'noc', 'to_received', 'rc_book_received',
                  'vehicle_received', 'rc_book_number', 'date')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


DealerRCHandOverItemFormSet = inlineformset_factory(
    DealerRCHandOver, DealerRCHandOverItem, form=DealerRCHandOverItemForm,
    extra=1, can_delete=True
)
