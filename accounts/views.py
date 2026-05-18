from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BranchForm, LoginForm, RoleForm, UserCreationForm, UserUpdateForm
from .models import Branch, Role, User


def login_view(request):
    # context: form — LoginForm
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(request.GET.get('next', 'accounts:dashboard'))

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def dashboard(request):
    # context: user — request.user (has .role and .branch)
    return render(request, 'accounts/dashboard.html', {'user': request.user})


@login_required
def user_list(request):
    # context: users — queryset of all User objects with role and branch
    users = User.objects.select_related('role', 'branch').all()
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_create(request):
    # context: form — UserCreationForm, title — str
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
def user_update(request, pk):
    # context: form — UserUpdateForm, title — str
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Update User'})


@login_required
def branch_list(request):
    # context: branches — queryset of all Branch objects
    branches = Branch.objects.all()
    return render(request, 'accounts/branch_list.html', {'branches': branches})


@login_required
def branch_create(request):
    # context: form — BranchForm, title — str
    form = BranchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:branch_list')
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Create Branch'})


@login_required
def branch_update(request, pk):
    # context: form — BranchForm, title — str
    branch = get_object_or_404(Branch, pk=pk)
    form   = BranchForm(request.POST or None, instance=branch)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:branch_list')
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Edit Branch'})


@login_required
def role_list(request):
    # context: roles — queryset of all Role objects
    roles = Role.objects.all()
    return render(request, 'accounts/role_list.html', {'roles': roles})
