from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AMCPackageForm, ProtectionPlusPackageForm, RSAPackageForm
from .models import AMCPackage, ProtectionPlusPackage, RSAPackage


# ---------------------------------------------------------------------------
# AMCPackage
# ---------------------------------------------------------------------------

@login_required
def amc_list(request):
    # context: packages — filtered queryset; q — search string;
    #          status_filter — active tab; status_choices — list
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
    # context: package — AMCPackage
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
    # context: form — AMCPackageForm; title — str
    # Pre-fills customer_vehicle from GET ?cv=<pk>
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = AMCPackageForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pkg = form.save()
        return redirect('vas:amc_detail', pk=pkg.pk)
    return render(request, 'vas/amc_form.html',
                  {'form': form, 'title': 'New AMC Package'})


@login_required
def amc_update(request, pk):
    # context: form — AMCPackageForm; title — str
    package = get_object_or_404(AMCPackage, pk=pk)
    form    = AMCPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('vas:amc_detail', pk=package.pk)
    return render(request, 'vas/amc_form.html',
                  {'form': form, 'title': 'Edit AMC Package'})


# ---------------------------------------------------------------------------
# RSAPackage
# ---------------------------------------------------------------------------

@login_required
def rsa_list(request):
    # context: packages — filtered queryset; q — search string;
    #          status_filter — active tab; status_choices — list
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
    # context: package — RSAPackage
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
    # context: form — RSAPackageForm; title — str
    # Pre-fills customer_vehicle from GET ?cv=<pk>
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = RSAPackageForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pkg = form.save()
        return redirect('vas:rsa_detail', pk=pkg.pk)
    return render(request, 'vas/rsa_form.html',
                  {'form': form, 'title': 'New RSA Package'})


@login_required
def rsa_update(request, pk):
    # context: form — RSAPackageForm; title — str
    package = get_object_or_404(RSAPackage, pk=pk)
    form    = RSAPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('vas:rsa_detail', pk=package.pk)
    return render(request, 'vas/rsa_form.html',
                  {'form': form, 'title': 'Edit RSA Package'})


# ---------------------------------------------------------------------------
# ProtectionPlusPackage
# ---------------------------------------------------------------------------

@login_required
def pp_list(request):
    # context: packages — filtered queryset; q — search string;
    #          status_filter — active tab; status_choices — list
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
    # context: package — ProtectionPlusPackage
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
    # context: form — ProtectionPlusPackageForm; title — str
    # Pre-fills customer_vehicle from GET ?cv=<pk>
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = ProtectionPlusPackageForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pkg = form.save()
        return redirect('vas:pp_detail', pk=pkg.pk)
    return render(request, 'vas/pp_form.html',
                  {'form': form, 'title': 'New Protection Plus Package'})


@login_required
def pp_update(request, pk):
    # context: form — ProtectionPlusPackageForm; title — str
    package = get_object_or_404(ProtectionPlusPackage, pk=pk)
    form    = ProtectionPlusPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('vas:pp_detail', pk=package.pk)
    return render(request, 'vas/pp_form.html',
                  {'form': form, 'title': 'Edit Protection Plus Package'})
