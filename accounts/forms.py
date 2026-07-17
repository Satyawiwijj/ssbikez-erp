from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.forms.utils import pretty_name
from django.utils.text import capfirst

from .models import Branch, CompanySettings, FuelExpense, Role, User, DiscountPercentageMaster, LedgerCreationDateMaster


class AccessibleFormMixin:
    """
    Gives every field an accessible name via aria-label, derived from the field's
    own label (falling back to a prettified field name, same as Django's own
    BoundField.label logic) -- a backstop for templates that render a field with
    no associated <label for="..."> at all (e.g. formset table rows that rely
    only on a <th> column header).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('aria-label', field.label or capfirst(pretty_name(name)))


class CompanySettingsForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = CompanySettings
        fields = ('company_name', 'tagline', 'address_line1', 'address_line2',
                  'city', 'state', 'pincode', 'phone', 'email',
                  'gstin', 'pan_number', 'logo_url',
                  'gst_rate', 'cgst_rate', 'sgst_rate', 'igst_rate')


class DiscountPercentageMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = DiscountPercentageMaster
        fields = ('labor_charge_discount', 'out_work_return_discount', 'spares_issue_alteration_discount')


class LedgerCreationDateMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = LedgerCreationDateMaster
        fields = ('allowed_days',)


class BranchForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = Branch
        fields = ('branch_name', 'address', 'phone', 'gstin', 'is_active')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class RoleForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = Role
        fields = ('role_name', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class UserCreationForm(BaseUserCreationForm):
    role   = forms.ModelChoiceField(queryset=Role.objects.all(), required=False)
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(is_active=True), required=False)
    phone  = forms.CharField(max_length=15, required=False)
    status = forms.ChoiceField(choices=User.Status.choices, initial=User.Status.ACTIVE)

    class Meta(BaseUserCreationForm.Meta):
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'role', 'branch', 'phone', 'status',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Login requires an emailed OTP — every user must have an address.
        self.fields['email'].required = True


class UserUpdateForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'role', 'branch', 'phone', 'status', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        # Login requires an emailed OTP — every user must have an address.
        self.fields['email'].required = True


class ProfileUpdateForm(AccessibleFormMixin, forms.ModelForm):
    """
    Allows the current user to update their own basic info.
    Role and branch are intentionally excluded (admin-only).
    """
    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'phone')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name':  forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone':      forms.TextInput(attrs={'placeholder': 'Phone number'}),
        }


class FuelExpenseForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = FuelExpense
        fields = ('vehicle', 'amount', 'fuel_date', 'voucher_number', 'remarks')
        widgets = {
            'fuel_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks':   forms.Textarea(attrs={'rows': 3}),
        }


class LoginForm(AuthenticationForm):
    pass
