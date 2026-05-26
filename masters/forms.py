from django import forms
from .models import SparesCategory, Supplier, Warehouse, Rack, Bin


class SparesCategoryForm(forms.ModelForm):
    class Meta:
        model = SparesCategory
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'})}


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        exclude = ['created_at', 'updated_at', 'created_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_fields = [
            'supplier_name', 'contact_person', 'phone', 'gstin', 'gst_category',
            'address_line1', 'address_line2', 'city', 'state', 'pincode', 'place_of_supply'
        ]
        for f in text_fields:
            if f in self.fields:
                self.fields[f].widget.attrs['class'] = 'form-control'
        if 'email' in self.fields:
            self.fields['email'].widget.attrs['class'] = 'form-control'
        if 'is_active' in self.fields:
            self.fields['is_active'].widget.attrs['class'] = 'form-check-input'


class WarehouseForm(forms.ModelForm):
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


class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = ['name', 'warehouse']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['warehouse'].widget.attrs['class'] = 'form-select'


class BinForm(forms.ModelForm):
    class Meta:
        model = Bin
        fields = ['name', 'rack']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['rack'].widget.attrs['class'] = 'form-select'
