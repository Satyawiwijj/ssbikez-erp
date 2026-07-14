from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory

from .models import (ManufacturingCompany, UsedVehicleAdvancePayment, UsedVehicleBayIn,
                     UsedVehicleBayOut, UsedVehicleChasisDetailRow, UsedVehicleColor,
                     UsedVehicleComplaintDetail, UsedVehicleDelivery, UsedVehicleEngineDetailRow,
                     UsedVehicleFinalInspection, UsedVehicleFinanceLoan, UsedVehicleFitting,
                     UsedVehicleInvoice, UsedVehicleInvoiceItem, UsedVehicleJobCard,
                     UsedVehicleLaborCharge, UsedVehicleLaborDetailLine,
                     UsedVehicleLaborSpareItem, UsedVehicleLightDetail, UsedVehicleModel,
                     UsedVehicleOthersDetail,
                     UsedVehicleOutworkEntryIssue, UsedVehicleOutworkEntryReturn,
                     UsedVehicleOutworkReturnDetail, UsedVehicleOutworkSpareItem,
                     UsedVehicleOutworkWorkDetail, UsedVehiclePartsCheckItem,
                     UsedVehiclePurchaseInvoice,
                     UsedVehiclePurchaseItem, UsedVehicleRCHandOver, UsedVehicleRegisterNo,
                     UsedVehicleSale, UsedVehicleSaleItem, UsedVehicleServiceInvoice,
                     UsedVehicleSubGroup, UsedVehicleSupervisorObservation, UsedVechileRCBookIssue,
                     UsedVehicleMasterSettings, UsedVehicleMasterSettingsItem,
                     UsedVehicleSalesSetting, UsedVehicleSalesSettingItem,
                     UsedVehicleInsuranceUpdate,
                     UsedVehicleDeliveryItem, UsedVehicleDeliveryAdvancePayment,
                     UsedVehicleLaborChargeRemoveItem,
                     UsedVehicleFinalInspectionLaborCharge, UsedVehicleFinalInspectionSpareItem,
                     UsedVehiclePurchaseOrder, UsedVehiclePurchaseOrderItem,
                     UsedVehiclePurchaseReceipt, UsedVehiclePurchaseReceiptItem)


class UsedVehicleModelForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleModel
        fields = ('disabled', 'code', 'manufacturer', 'vehicle_category',
                  'used_vehicle_name', 'model', 'sub_group')


class UsedVehicleRegisterNoForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleRegisterNo
        fields = ('registration_no', 'used_vehicle', 'color', 'chassis_no',
                  'engine_no', 'branch', 'stock_status', 'purchase_date',
                  'warehouse_status', 'status', 'vehicle_status', 'customer')
        widgets = {'purchase_date': forms.DateInput(attrs={'type': 'date'})}


# ---------------------------------------------------------------------------
# Purchase
# ---------------------------------------------------------------------------

class UsedVehiclePurchaseInvoiceForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePurchaseInvoice
        fields = ('own_purchase', 'supplier_purchase', 'supplier', 'purchase_receipt',
                  'required_date', 'branch', 'payment_type', 'invoice_date', 'customer_name',
                  'phone_number', 'address', 'target_warehouse', 'vehicle_status',
                  'total_quantity', 'total_amount', 'discount', 'grand_total',
                  'pending_amount', 'payment_status')
        widgets = {
            'required_date': forms.DateInput(attrs={'type': 'date'}),
            'invoice_date':  forms.DateInput(attrs={'type': 'date'}),
            'address':       forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_receipt'].required = False


# ---------------------------------------------------------------------------
# Phase 10 — Purchase Order -> Purchase Receipt
# ---------------------------------------------------------------------------

class UsedVehiclePurchaseOrderForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePurchaseOrder
        fields = ('supplier', 'required_date', 'branch', 'target_warehouse',
                  'total_quantity', 'total_amount', 'discount', 'grand_total')
        widgets = {'required_date': forms.DateInput(attrs={'type': 'date'})}


class UsedVehiclePurchaseOrderItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePurchaseOrderItem
        fields = ('item_code', 'register_number', 'engine_number', 'chasis_number', 'color',
                  'quantity', 'uom', 'rate', 'noc', 'insurance', 'to_received', 'model',
                  'rc_book_number', 'customer', 'sub_group')


UsedVehiclePurchaseOrderItemFormSet = inlineformset_factory(
    UsedVehiclePurchaseOrder, UsedVehiclePurchaseOrderItem,
    form=UsedVehiclePurchaseOrderItemForm, extra=1, can_delete=True
)


class UsedVehiclePurchaseReceiptForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePurchaseReceipt
        fields = ('purchase_order', 'supplier', 'branch', 'required_date', 'target_warehouse',
                  'total_quantity', 'total_amount', 'discount', 'grand_total',
                  'payment_bending_amount')
        widgets = {'required_date': forms.DateInput(attrs={'type': 'date'})}


class UsedVehiclePurchaseReceiptItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePurchaseReceiptItem
        fields = ('item_code', 'register_number', 'engine_number', 'chasis_number', 'color',
                  'quantity', 'uom', 'rate', 'rc_book_number', 'to_received', 'noc',
                  'insurance', 'model', 'customer')


UsedVehiclePurchaseReceiptItemFormSet = inlineformset_factory(
    UsedVehiclePurchaseReceipt, UsedVehiclePurchaseReceiptItem,
    form=UsedVehiclePurchaseReceiptItemForm, extra=1, can_delete=True
)


class UsedVehiclePurchaseItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePurchaseItem
        fields = ('used_vehicle', 'registration_no', 'chassis_no', 'engine_no',
                  'color', 'quantity', 'rate', 'amount')


UsedVehiclePurchaseItemFormSet = inlineformset_factory(
    UsedVehiclePurchaseInvoice, UsedVehiclePurchaseItem,
    form=UsedVehiclePurchaseItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Sale
# ---------------------------------------------------------------------------

class UsedVehicleSaleForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleSale
        fields = ('customer', 'sales_executive', 'vehicle_number', 'branch', 'phone_number',
                  'gst_category', 'delivery_date', 'vehicle_value', 'sale_amount',
                  'vehicle_amount', 'has_exchange', 'finance_closing', 'exchange_amount',
                  'items_qty', 'total', 'tax_amount', 'base_rate', 'additional_discount',
                  'advance_payment', 'balance_amount', 'sale_status')
        widgets = {'delivery_date': forms.DateInput(attrs={'type': 'date'})}


class UsedVehicleFittingForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleFitting
        fields = ('item_code', 'item_name', 'quantity', 'rate', 'amount')


UsedVehicleFittingFormSet = inlineformset_factory(
    UsedVehicleSale, UsedVehicleFitting, form=UsedVehicleFittingForm, extra=1, can_delete=True
)


class UsedVehicleSaleItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleSaleItem
        fields = ('item_name', 'rate', 'quantity', 'amount')


UsedVehicleSaleItemFormSet = inlineformset_factory(
    UsedVehicleSale, UsedVehicleSaleItem, form=UsedVehicleSaleItemForm, extra=1, can_delete=True
)


class UsedVehicleAdvancePaymentForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleAdvancePayment
        fields = ('mode_of_payment', 'date', 'amount', 'to_account')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


UsedVehicleAdvancePaymentFormSet = inlineformset_factory(
    UsedVehicleSale, UsedVehicleAdvancePayment, form=UsedVehicleAdvancePaymentForm,
    extra=1, can_delete=True
)


class UsedVehicleFinanceLoanForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleFinanceLoan
        fields = ('sale', 'bank_name', 'loan_amount', 'interest_rate', 'tenure_months',
                  'emi_amount', 'loan_status', 'sanctioned_date', 'first_emi_date',
                  'hp_status', 'hp_bank_name', 'hp_submission_date',
                  'hp_endorsement_date', 'hp_release_date')
        widgets = {
            'sanctioned_date':     forms.DateInput(attrs={'type': 'date'}),
            'first_emi_date':      forms.DateInput(attrs={'type': 'date'}),
            'hp_submission_date':  forms.DateInput(attrs={'type': 'date'}),
            'hp_endorsement_date': forms.DateInput(attrs={'type': 'date'}),
            'hp_release_date':     forms.DateInput(attrs={'type': 'date'}),
        }


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

class UsedVehicleDeliveryForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleDelivery
        fields = ('sale', 'delivery_date', 'delivered_by', 'remarks',
                  'checklist_rc_book', 'checklist_warranty', 'checklist_toolkit',
                  'checklist_accessories', 'issue_gate_pass',
                  'manager_approval_requested', 'manager_approved', 'finance_approved',
                  'total_amount', 'payment_status',
                  'warehouse', 'gst_category', 'has_exchange', 'finance_closing',
                  'exchange_amount', 'offer_petrol', 'petrol_type', 'petrol_litre',
                  'petrol_amount', 'item_qty', 'finance_amount', 'delivery_discount',
                  'base_rate', 'additional_discount', 'advance_payment', 'balance_amount')
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks':       forms.Textarea(attrs={'rows': 2}),
        }


class UsedVehicleDeliveryItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleDeliveryItem
        fields = ('item_code', 'warranty_rsa_amc', 'rate')


UsedVehicleDeliveryItemFormSet = inlineformset_factory(
    UsedVehicleDelivery, UsedVehicleDeliveryItem, form=UsedVehicleDeliveryItemForm,
    extra=1, can_delete=True
)


class UsedVehicleDeliveryAdvancePaymentForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleDeliveryAdvancePayment
        fields = ('mode_of_payment', 'date', 'amount', 'to_account', 'draft_type')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


UsedVehicleDeliveryAdvancePaymentFormSet = inlineformset_factory(
    UsedVehicleDelivery, UsedVehicleDeliveryAdvancePayment, form=UsedVehicleDeliveryAdvancePaymentForm,
    extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class UsedVehicleInvoiceForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleInvoice
        fields = ('sale', 'subtotal', 'gst_amount', 'gst_category', 'discount_amount',
                  'final_amount', 'invoice_date', 'payment_type', 'payment_due_date',
                  'md_approval_requested', 'md_approved', 'status')
        widgets = {
            'invoice_date':     forms.DateInput(attrs={'type': 'date'}),
            'payment_due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # gst_amount and final_amount are derived in clean() below -- same fix as
        # billing.InvoiceForm from Phase 1 (don't require them before we compute them).
        self.fields['gst_amount'].required = False
        self.fields['final_amount'].required = False

    def clean(self):
        from decimal import Decimal
        cleaned = super().clean()
        subtotal        = cleaned.get('subtotal') or Decimal('0')
        gst_amount      = cleaned.get('gst_amount') or Decimal('0')
        discount_amount = cleaned.get('discount_amount') or Decimal('0')

        if subtotal < Decimal('0'):
            self.add_error('subtotal', 'Subtotal cannot be negative.')

        if gst_amount == Decimal('0') and subtotal > Decimal('0'):
            try:
                from accounts.models import CompanySettings
                rate = Decimal(str(CompanySettings.get_instance().gst_rate or 18))
            except Exception:
                rate = Decimal('18')
            gst_amount = (subtotal * rate / Decimal('100')).quantize(Decimal('0.01'))
            cleaned['gst_amount'] = gst_amount

        expected_final = subtotal + gst_amount - discount_amount
        if expected_final < Decimal('0'):
            self.add_error('discount_amount', 'Discount cannot exceed subtotal + GST.')
        else:
            cleaned['final_amount'] = expected_final
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.gst_amount = self.cleaned_data['gst_amount']
        instance.final_amount = self.cleaned_data['final_amount']
        if commit:
            instance.save()
        return instance


class UsedVehicleInvoiceItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleInvoiceItem
        fields = ('item_code', 'rate', 'discount', 'total')


UsedVehicleInvoiceItemFormSet = inlineformset_factory(
    UsedVehicleInvoice, UsedVehicleInvoiceItem, form=UsedVehicleInvoiceItemForm,
    extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# RC Hand Over / RC Book Issue
# ---------------------------------------------------------------------------

class UsedVehicleRCHandOverForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleRCHandOver
        fields = ('sale', 'rc_number', 'handover_date', 'handed_over_by', 'status', 'notes',
                  'rc_book_received', 'noc', 'vehicle_received', 'to_received')
        widgets = {
            'handover_date': forms.DateInput(attrs={'type': 'date'}),
            'notes':         forms.Textarea(attrs={'rows': 2}),
        }


class UsedVechileRCBookIssueForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVechileRCBookIssue
        fields = ('sale', 'rc_number', 'issue_date', 'issued_to', 'status', 'notes')
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'notes':      forms.Textarea(attrs={'rows': 2}),
        }


# ---------------------------------------------------------------------------
# Used Vehicle Insurance Update
# ---------------------------------------------------------------------------

class UsedVehicleInsuranceUpdateForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleInsuranceUpdate
        fields = ('register_no', 'insurance_status', 'insurance_name', 'policy_number',
                  'start_date', 'end_date', 'amount', 'payment_method', 'from_account',
                  'to_account', 'ref_no', 'ref_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date':   forms.DateInput(attrs={'type': 'date'}),
            'ref_date':   forms.DateInput(attrs={'type': 'date'}),
        }


# ---------------------------------------------------------------------------
# Phase 3b — Used Vehicle Job Card service pipeline
# ---------------------------------------------------------------------------

_DT_WIDGET = forms.DateTimeInput(attrs={'type': 'datetime-local'})


class UsedVehicleJobCardForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleJobCard
        fields = ('register_no', 'service_advisor', 'km', 'customer_name', 'phone_no', 'email',
                  'address', 'super_visor', 'service_status',
                  'date', 'frame_no', 'model', 'vehicle_name', 'service', 'engine_no', 'colour',
                  'total_estimated_cost', 'opening_time', 'in_time', 'closing_time', 'e_cost',
                  'p_date', 'p_time')
        widgets = {
            'address':      forms.Textarea(attrs={'rows': 2}),
            'date':         forms.DateInput(attrs={'type': 'date'}),
            'p_date':       forms.DateInput(attrs={'type': 'date'}),
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'in_time':      forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
            'p_time':       forms.TimeInput(attrs={'type': 'time'}),
        }


class UsedVehicleBayInForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleBayIn
        fields = ('job_card', 'mechanic', 'vehicle_name', 'register_no', 'date')
        widgets = {'date': _DT_WIDGET}


class UsedVehicleBayOutForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleBayOut
        fields = ('job_card', 'mechanic', 'vehicle_name', 'vehicle_number', 'remarks', 'date')
        widgets = {
            'date':    forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }


class UsedVehicleFinalInspectionForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleFinalInspection
        fields = ('job_card', 'rework', 'vehicle_name', 'chasis_number', 'mechanic_name',
                  'register_number', 'final_inspection_remarks',
                  'out_work_charge_form', 'out_work_remarks')
        widgets = {'final_inspection_remarks': forms.Textarea(attrs={'rows': 3})}


class UsedVehicleFinalInspectionComplaintDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleComplaintDetail
        fields = ('customer_complaint', 'details', 'status', 'complaint_check_box', 'estimated_amount')


UsedVehicleFinalInspectionComplaintDetailFormSet = inlineformset_factory(
    UsedVehicleFinalInspection, UsedVehicleComplaintDetail,
    form=UsedVehicleFinalInspectionComplaintDetailForm, extra=1, can_delete=True
)


class UsedVehicleFinalInspectionSupervisorObservationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleSupervisorObservation
        fields = ('complaint', 'details', 'complaint_check_box', 'estimated_amount')


UsedVehicleFinalInspectionSupervisorObservationFormSet = inlineformset_factory(
    UsedVehicleFinalInspection, UsedVehicleSupervisorObservation,
    form=UsedVehicleFinalInspectionSupervisorObservationForm, extra=1, can_delete=True
)


class UsedVehicleFinalInspectionLaborChargeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleFinalInspectionLaborCharge
        fields = ('date', 'labor_work', 'quantity', 'amount', 'sgst', 'cgst', 'total')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


UsedVehicleFinalInspectionLaborChargeFormSet = inlineformset_factory(
    UsedVehicleFinalInspection, UsedVehicleFinalInspectionLaborCharge,
    form=UsedVehicleFinalInspectionLaborChargeForm, extra=1, can_delete=True
)


class UsedVehicleFinalInspectionSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleFinalInspectionSpareItem
        fields = ('item', 'qty', 'rate', 'amount')


UsedVehicleFinalInspectionSpareItemFormSet = inlineformset_factory(
    UsedVehicleFinalInspection, UsedVehicleFinalInspectionSpareItem,
    form=UsedVehicleFinalInspectionSpareItemForm, extra=1, can_delete=True
)


class UsedVehicleOutworkEntryIssueForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleOutworkEntryIssue
        fields = ('job_card', 'vendor_name', 'godown', 'gate_pass')


class UsedVehicleOutworkWorkDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleOutworkWorkDetail
        fields = ('work_name', 'quantity', 'amount', 'total_amount')


UsedVehicleOutworkWorkDetailFormSet = inlineformset_factory(
    UsedVehicleOutworkEntryIssue, UsedVehicleOutworkWorkDetail,
    form=UsedVehicleOutworkWorkDetailForm, extra=1, can_delete=True
)


class UsedVehicleOutworkSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleOutworkSpareItem
        fields = ('item', 'quantity', 'rate', 'total')


UsedVehicleOutworkSpareItemFormSet = inlineformset_factory(
    UsedVehicleOutworkEntryIssue, UsedVehicleOutworkSpareItem,
    form=UsedVehicleOutworkSpareItemForm, extra=1, can_delete=True
)


class UsedVehicleOutworkEntryReturnForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleOutworkEntryReturn
        fields = ('outwork_issue', 'job_card', 'rework', 'payment_type', 'supplier',
                  'actual_amount', 'billing_amount', 'pending_amount',
                  'invoice_no', 'discount', 'payment_status')


class UsedVehicleOutworkReturnDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleOutworkReturnDetail
        fields = ('work_name', 'quantity', 'amount')


UsedVehicleOutworkReturnDetailFormSet = inlineformset_factory(
    UsedVehicleOutworkEntryReturn, UsedVehicleOutworkReturnDetail,
    form=UsedVehicleOutworkReturnDetailForm, extra=1, can_delete=True
)


class UsedVehicleLaborChargeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleLaborCharge
        fields = ('job_card', 'labour_name', 'discount', 'updated_total')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['updated_total'].required = False


class UsedVehicleLaborChargeRemoveItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleLaborChargeRemoveItem
        fields = ('labor_work', 'amount', 'sgst', 'cgst', 'total')


UsedVehicleLaborChargeRemoveItemFormSet = inlineformset_factory(
    UsedVehicleLaborCharge, UsedVehicleLaborChargeRemoveItem,
    form=UsedVehicleLaborChargeRemoveItemForm, extra=1, can_delete=True
)


class UsedVehicleLaborDetailLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleLaborDetailLine
        fields = ('labor_work', 'quantity', 'amount', 'sgst', 'cgst', 'total')


UsedVehicleLaborDetailLineFormSet = inlineformset_factory(
    UsedVehicleLaborCharge, UsedVehicleLaborDetailLine,
    form=UsedVehicleLaborDetailLineForm, extra=1, can_delete=True
)


class UsedVehicleLaborSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleLaborSpareItem
        fields = ('item', 'quantity', 'rate', 'total')


UsedVehicleLaborSpareItemFormSet = inlineformset_factory(
    UsedVehicleLaborCharge, UsedVehicleLaborSpareItem,
    form=UsedVehicleLaborSpareItemForm, extra=1, can_delete=True
)


class UsedVehicleServiceInvoiceForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleServiceInvoice
        fields = ('job_card', 'labor_total', 'spares_total', 'outwork_total',
                  'discount_amount', 'invoice_date')
        widgets = {'invoice_date': forms.DateInput(attrs={'type': 'date'})}


# ---------------------------------------------------------------------------
# Phase 4 — Used Vehicle Job Card inspection-checklist child tables
# ---------------------------------------------------------------------------

class UsedVehicleComplaintDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleComplaintDetail
        fields = ('customer_complaint', 'details', 'status', 'complaint_check_box', 'estimated_amount')


UsedVehicleComplaintDetailFormSet = inlineformset_factory(
    UsedVehicleJobCard, UsedVehicleComplaintDetail, form=UsedVehicleComplaintDetailForm,
    extra=1, can_delete=True
)


class UsedVehicleSupervisorObservationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleSupervisorObservation
        fields = ('complaint', 'details', 'complaint_check_box', 'estimated_amount')


UsedVehicleSupervisorObservationFormSet = inlineformset_factory(
    UsedVehicleJobCard, UsedVehicleSupervisorObservation, form=UsedVehicleSupervisorObservationForm,
    extra=1, can_delete=True
)


class UsedVehicleEngineDetailRowForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleEngineDetailRow
        fields = ('items', 'yes', 'no', 'ok', 'high', 'low', 'area_mention',
                  'yes_status', 'no_status', 'ok_status', 'high_status', 'low_status', 'mention_status')


UsedVehicleEngineDetailRowFormSet = inlineformset_factory(
    UsedVehicleJobCard, UsedVehicleEngineDetailRow, form=UsedVehicleEngineDetailRowForm,
    extra=1, can_delete=True
)


class UsedVehicleLightDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleLightDetail
        fields = ('items', 'yes', 'no')


UsedVehicleLightDetailFormSet = inlineformset_factory(
    UsedVehicleJobCard, UsedVehicleLightDetail, form=UsedVehicleLightDetailForm,
    extra=1, can_delete=True
)


class UsedVehicleChasisDetailRowForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleChasisDetailRow
        fields = ('items', 'yes', 'no', 'ok', 'high', 'low', 'good', 'bad', 'na',
                  'yes_status', 'no_status', 'good_status', 'bad_status', 'na_status',
                  'ok_status', 'high_status')


UsedVehicleChasisDetailRowFormSet = inlineformset_factory(
    UsedVehicleJobCard, UsedVehicleChasisDetailRow, form=UsedVehicleChasisDetailRowForm,
    extra=1, can_delete=True
)


class UsedVehicleOthersDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehicleOthersDetail
        fields = ('items', 'others_check_box')


UsedVehicleOthersDetailFormSet = inlineformset_factory(
    UsedVehicleJobCard, UsedVehicleOthersDetail, form=UsedVehicleOthersDetailForm,
    extra=1, can_delete=True
)


class UsedVehiclePartsCheckItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = UsedVehiclePartsCheckItem
        fields = ('spares', 'change_need_yes', 'change_need_no')


def _parts_check_formset_factory(category):
    """One inline formset per collapsed-category section: filters the queryset
    to that category and stamps new rows with it, so the 14 reference
    doctypes' distinct sections render from one shared model (see
    UsedVehiclePartsCheckItem docstring in models.py)."""
    from django.forms.models import BaseInlineFormSet

    class _CategoryFormSet(BaseInlineFormSet):
        def get_queryset(self):
            return super().get_queryset().filter(category=category)

        def save_new(self, form, commit=True):
            form.instance.category = category
            return super().save_new(form, commit=commit)

    return inlineformset_factory(
        UsedVehicleJobCard, UsedVehiclePartsCheckItem, form=UsedVehiclePartsCheckItemForm,
        formset=_CategoryFormSet, extra=1, can_delete=True
    )


_PC = UsedVehiclePartsCheckItem.Category

BrakeDetailFormSet         = _parts_check_formset_factory(_PC.BRAKE)
ForkDetailFormSet          = _parts_check_formset_factory(_PC.FORK)
CablesDetailFormSet        = _parts_check_formset_factory(_PC.CABLES)
BulbDetailFormSet          = _parts_check_formset_factory(_PC.BULB)
IndicatorDetailFormSet     = _parts_check_formset_factory(_PC.INDICATOR)
RubbersDetailFormSet       = _parts_check_formset_factory(_PC.RUBBERS)
FootRestDetailFormSet      = _parts_check_formset_factory(_PC.FOOT_REST)
OilSealsDetailFormSet      = _parts_check_formset_factory(_PC.OIL_SEALS)
PackingDetailFormSet       = _parts_check_formset_factory(_PC.PACKING)
HandleBarMountDetailFormSet = _parts_check_formset_factory(_PC.HANDLE_BAR)
NumberPlateDetailFormSet   = _parts_check_formset_factory(_PC.NUMBER_PLATE)
ChainDetailFormSet         = _parts_check_formset_factory(_PC.CHAIN)
ClutchDetailFormSet        = _parts_check_formset_factory(_PC.CLUTCH)
BodyPartsDetailFormSet     = _parts_check_formset_factory(_PC.BODY_PARTS)

# Keyed lookup for looping in views/templates instead of naming all 14 by hand.
PARTS_CHECK_FORMSET_MAP = {
    _PC.BRAKE:        BrakeDetailFormSet,
    _PC.FORK:         ForkDetailFormSet,
    _PC.CABLES:       CablesDetailFormSet,
    _PC.BULB:         BulbDetailFormSet,
    _PC.INDICATOR:    IndicatorDetailFormSet,
    _PC.RUBBERS:      RubbersDetailFormSet,
    _PC.FOOT_REST:    FootRestDetailFormSet,
    _PC.OIL_SEALS:    OilSealsDetailFormSet,
    _PC.PACKING:      PackingDetailFormSet,
    _PC.HANDLE_BAR:   HandleBarMountDetailFormSet,
    _PC.NUMBER_PLATE: NumberPlateDetailFormSet,
    _PC.CHAIN:        ChainDetailFormSet,
    _PC.CLUTCH:       ClutchDetailFormSet,
    _PC.BODY_PARTS:   BodyPartsDetailFormSet,
}


# ---------------------------------------------------------------------------
# Phase 8c — Used Vehicle Master Settings
# ---------------------------------------------------------------------------

class UsedVehicleMasterSettingsForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = UsedVehicleMasterSettings
        fields = ('vehicle', 'has_exchange_vehicle', 'service_settings', 'exchange_vehicle_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_settings'].required = False
        self.fields['exchange_vehicle_id'].required = False


class UsedVehicleMasterSettingsItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = UsedVehicleMasterSettingsItem
        fields = ('vehicle_name', 'model', 'register_number', 'chasis_no', 'engine', 'color', 'color_code')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle_name'].required = False
        self.fields['chasis_no'].required = False


UsedVehicleMasterSettingsItemFormSet = inlineformset_factory(
    UsedVehicleMasterSettings, UsedVehicleMasterSettingsItem,
    form=UsedVehicleMasterSettingsItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 8d — Used Vehicle Sales Setting
# ---------------------------------------------------------------------------

class UsedVehicleSalesSettingForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = UsedVehicleSalesSetting
        fields = ('gst_percent',)


class UsedVehicleSalesSettingItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = UsedVehicleSalesSettingItem
        fields = ('vehicle_no', 'purchase_cost', 'maintain_cost', 'base_rate')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle_no'].required = False


UsedVehicleSalesSettingItemFormSet = inlineformset_factory(
    UsedVehicleSalesSetting, UsedVehicleSalesSettingItem,
    form=UsedVehicleSalesSettingItemForm, extra=1, can_delete=True
)
