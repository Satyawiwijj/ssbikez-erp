from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.audit import log_action

from .forms import AMCPackageForm, ProtectionPlusPackageForm, RSAPackageForm
from .models import AMCPackage, ProtectionPlusPackage, RSAPackage


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    def safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

    total_amc = safe_count(AMCPackage.objects.all())
    total_rsa = safe_count(RSAPackage.objects.all())
    total_pp  = safe_count(ProtectionPlusPackage.objects.all())
    active_amc = safe_count(AMCPackage.objects.filter(status='active'))
    active_rsa = safe_count(RSAPackage.objects.filter(status='active'))

    return render(request, 'vas/dashboard.html', {
        'total_amc':  total_amc,
        'total_rsa':  total_rsa,
        'total_pp':   total_pp,
        'active_amc': active_amc,
        'active_rsa': active_rsa,
    })


# ---------------------------------------------------------------------------
# AMCPackage
# ---------------------------------------------------------------------------

@login_required
def amc_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = AMCPackage.objects.select_related(
        'customer_vehicle__customer',
        'customer_vehicle__vehicle__bike_model',
    ).all()
    if q:
        qs = qs.filter(
            Q(customer_vehicle__customer__full_name__icontains=q) |
            Q(customer_vehicle__registration_no__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'vas/amc_list.html', {
        'packages':       qs,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': AMCPackage.Status.choices,
    })


@login_required
def amc_detail(request, pk):
    package = get_object_or_404(
        AMCPackage.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
        ),
        pk=pk,
    )
    return render(request, 'vas/amc_detail.html', {'package': package})


@login_required
def amc_create(request):
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = AMCPackageForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pkg = form.save()
        log_action(request, 'AMC Package', 'create', pkg.pk)
        messages.success(request, 'AMC package created successfully.')
        return redirect('vas:amc_detail', pk=pkg.pk)
    return render(request, 'vas/amc_form.html',
                  {'form': form, 'title': 'New AMC Package'})


@login_required
def amc_update(request, pk):
    package = get_object_or_404(AMCPackage, pk=pk)
    form    = AMCPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'AMC Package', 'update', pk)
        messages.success(request, 'AMC package updated successfully.')
        return redirect('vas:amc_detail', pk=package.pk)
    return render(request, 'vas/amc_form.html',
                  {'form': form, 'title': 'Edit AMC Package'})


# ---------------------------------------------------------------------------
# RSAPackage
# ---------------------------------------------------------------------------

@login_required
def rsa_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = RSAPackage.objects.select_related(
        'customer_vehicle__customer',
        'customer_vehicle__vehicle__bike_model',
    ).all()
    if q:
        qs = qs.filter(
            Q(customer_vehicle__customer__full_name__icontains=q) |
            Q(customer_vehicle__registration_no__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'vas/rsa_list.html', {
        'packages':       qs,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': RSAPackage.Status.choices,
    })


@login_required
def rsa_detail(request, pk):
    package = get_object_or_404(
        RSAPackage.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
        ),
        pk=pk,
    )
    return render(request, 'vas/rsa_detail.html', {'package': package})


@login_required
def rsa_create(request):
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = RSAPackageForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pkg = form.save()
        log_action(request, 'RSA Package', 'create', pkg.pk)
        messages.success(request, 'RSA package created successfully.')
        return redirect('vas:rsa_detail', pk=pkg.pk)
    return render(request, 'vas/rsa_form.html',
                  {'form': form, 'title': 'New RSA Package'})


@login_required
def rsa_update(request, pk):
    package = get_object_or_404(RSAPackage, pk=pk)
    form    = RSAPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'RSA Package', 'update', pk)
        messages.success(request, 'RSA package updated successfully.')
        return redirect('vas:rsa_detail', pk=package.pk)
    return render(request, 'vas/rsa_form.html',
                  {'form': form, 'title': 'Edit RSA Package'})


# ---------------------------------------------------------------------------
# ProtectionPlusPackage
# ---------------------------------------------------------------------------

@login_required
def pp_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = ProtectionPlusPackage.objects.select_related(
        'customer_vehicle__customer',
        'customer_vehicle__vehicle__bike_model',
    ).all()
    if q:
        qs = qs.filter(
            Q(customer_vehicle__customer__full_name__icontains=q) |
            Q(customer_vehicle__registration_no__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'vas/pp_list.html', {
        'packages':       qs,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': ProtectionPlusPackage.Status.choices,
    })


@login_required
def pp_detail(request, pk):
    package = get_object_or_404(
        ProtectionPlusPackage.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
        ),
        pk=pk,
    )
    return render(request, 'vas/pp_detail.html', {'package': package})


@login_required
def pp_create(request):
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = ProtectionPlusPackageForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pkg = form.save()
        log_action(request, 'Protection Plus', 'create', pkg.pk)
        messages.success(request, 'Protection Plus package created successfully.')
        return redirect('vas:pp_detail', pk=pkg.pk)
    return render(request, 'vas/pp_form.html',
                  {'form': form, 'title': 'New Protection Plus Package'})


@login_required
def pp_update(request, pk):
    package = get_object_or_404(ProtectionPlusPackage, pk=pk)
    form    = ProtectionPlusPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Protection Plus', 'update', pk)
        messages.success(request, 'Protection Plus package updated successfully.')
        return redirect('vas:pp_detail', pk=package.pk)
    return render(request, 'vas/pp_form.html',
                  {'form': form, 'title': 'Edit Protection Plus Package'})
