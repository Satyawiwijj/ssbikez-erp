from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from .models import Branch, FuelExpense, Role, User


class BranchForm(forms.ModelForm):
    class Meta:
        model  = Branch
        fields = ('branch_name', 'address', 'phone', 'gstin', 'is_active')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class RoleForm(forms.ModelForm):
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


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'role', 'branch', 'phone', 'status', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)


class FuelExpenseForm(forms.ModelForm):
    class Meta:
        model  = FuelExpense
        fields = ('vehicle', 'amount', 'fuel_date', 'voucher_number', 'remarks', 'created_by')
        widgets = {
            'fuel_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks':   forms.Textarea(attrs={'rows': 3}),
        }


class LoginForm(AuthenticationForm):
    pass
