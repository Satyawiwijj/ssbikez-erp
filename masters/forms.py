from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory
from .models import (
    SparesCategory, Supplier, Warehouse, Rack, Bin, OrderFormSettings,
    ModelAndPrice, CustomerPrice, CustomerPriceItem, DealerPriceList, DealerPriceItem,
    VehicleFittingSpares, VehicleFittingSpareItem,
)


class SparesCategoryForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesCategory
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'})}


class SupplierForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        exclude = ['created_at', 'updated_at', 'created_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_fields = [
            'supplier_name', 'supplier_group', 'country', 'contact_person', 'phone', 'gstin', 'gst_category',
            'address_line1', 'address_line2', 'city', 'state', 'pincode', 'place_of_supply',
            'supplier_limit_amount', 'default_currency', 'payment_terms', 'tax_id',
        ]
        for f in text_fields:
            if f in self.fields:
                self.fields[f].widget.attrs['class'] = 'form-control'
        if 'email' in self.fields:
            self.fields['email'].widget.attrs['class'] = 'form-control'
        if 'supplier_type' in self.fields:
            self.fields['supplier_type'].widget.attrs['class'] = 'form-select'
        for f in ('is_active', 'is_transporter', 'is_prepaid_supplier'):
            if f in self.fields:
                self.fields[f].widget.attrs['class'] = 'form-check-input'


class WarehouseForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = Warehouse
        exclude = ['created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_parent_warehouse(self):
        parent = self.cleaned_data.get('parent_warehouse')
        if parent and self.instance and self.instance.pk:
            if parent.pk == self.instance.pk:
                raise forms.ValidationError('A warehouse cannot be its own parent.')
            # Walk up the ancestor chain to reject a cycle.
            seen = {self.instance.pk}
            node = parent
            for _ in range(20):
                if node.pk in seen:
                    raise forms.ValidationError('This would create a circular warehouse hierarchy.')
                seen.add(node.pk)
                node = node.parent_warehouse
                if node is None:
                    break
        return parent


class RackForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = Rack
        fields = ['name', 'warehouse']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['warehouse'].widget.attrs['class'] = 'form-select'


class BinForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = Bin
        fields = ['name', 'rack']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['rack'].widget.attrs['class'] = 'form-select'


class OrderFormSettingsForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = OrderFormSettings
        fields = ['new_vehicle', 'used_vehicle', 'branch', 'prefix', 'digits', 'count']
        widgets = {
            'new_vehicle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'used_vehicle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'digits': forms.NumberInput(attrs={'class': 'form-control'}),
            'count': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# ---------------------------------------------------------------------------
# Phase 8b — Vehicle Pricing Masters
# ---------------------------------------------------------------------------

class ModelAndPriceForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ModelAndPrice
        fields = ['model_code', 'sub_group', 'color', 'color_code', 'percentage',
                  'ex_show_room', 'pdi', 'rsa', 'insurance', 'updated_insurance_rate',
                  'amc', 'warranty', 'charge_1', 'charge_2', 'charge_3']
        widgets = {
            'model_code': forms.Select(attrs={'class': 'form-select'}),
            'sub_group': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'color_code': forms.TextInput(attrs={'class': 'form-control'}),
            'percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'ex_show_room': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pdi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rsa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'insurance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'updated_insurance_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'warranty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'charge_1': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'charge_2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'charge_3': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class CustomerPriceForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerPrice
        fields = ['branch', 'disable', 'model_code', 'sub_group', 'color']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'disable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'model_code': forms.Select(attrs={'class': 'form-select'}),
            'sub_group': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CustomerPriceItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerPriceItem
        fields = ['price_type', 'amount']
        widgets = {
            'price_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ex-showroom, LTRT, Insurance, PDI, Other, Discount, Protection Plus'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


CustomerPriceItemFormSet = inlineformset_factory(
    CustomerPrice, CustomerPriceItem, form=CustomerPriceItemForm, extra=1, can_delete=True
)


class DealerPriceListForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = DealerPriceList
        fields = ['dealer_name', 'model_code', 'sub_group', 'color']
        widgets = {
            'dealer_name': forms.Select(attrs={'class': 'form-select'}),
            'model_code': forms.Select(attrs={'class': 'form-select'}),
            'sub_group': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
        }


class DealerPriceItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = DealerPriceItem
        fields = ['price_type', 'amount']
        widgets = {
            'price_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ex-showroom, LTRT, Insurance, PDI, Other, Discount, PP'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


DealerPriceItemFormSet = inlineformset_factory(
    DealerPriceList, DealerPriceItem, form=DealerPriceItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 8c — Vehicle Fitting Spares (Vehicle Service Master already exists in
# service/models.py -- not duplicated, see masters/models.py note)
# ---------------------------------------------------------------------------

class VehicleFittingSparesForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = VehicleFittingSpares
        fields = ['vehicle', 'branch']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }


class VehicleFittingSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = VehicleFittingSpareItem
        fields = ['item', 'quantity', 'rate', 'uom', 'gst']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'uom': forms.TextInput(attrs={'class': 'form-control'}),
            'gst': forms.TextInput(attrs={'class': 'form-control'}),
        }


VehicleFittingSpareItemFormSet = inlineformset_factory(
    VehicleFittingSpares, VehicleFittingSpareItem, form=VehicleFittingSpareItemForm, extra=1, can_delete=True
)
