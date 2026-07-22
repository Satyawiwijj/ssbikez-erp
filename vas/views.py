from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.permissions import require_module_action, user_is_manager, user_owns

from .forms import (AMCPackageForm, AMCTypeForm, ProtectionPlusPackageForm, RSAPackageForm,
                    RSATypeForm, RSACreationForm, VASSupplierInvoiceForm,
                    VASSupplierInvoiceItemFormSet, WarrantyTypeForm)
from .models import (AMCPackage, AMCType, ProtectionPlusPackage, RSAPackage, RSAType,
                     RSACreation, VASSupplierInvoice, WarrantyType)


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
@require_module_action('vas', 'create')
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
@require_module_action('vas', 'edit')
def amc_update(request, pk):
    package = get_object_or_404(AMCPackage, pk=pk)
    if package.docstatus != AMCPackage.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('vas:amc_detail', args=[package.pk]))
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
@require_module_action('vas', 'create')
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
@require_module_action('vas', 'edit')
def rsa_update(request, pk):
    package = get_object_or_404(RSAPackage, pk=pk)
    if package.docstatus != RSAPackage.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('vas:rsa_detail', args=[package.pk]))
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
@require_module_action('vas', 'create')
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
@require_module_action('vas', 'edit')
def pp_update(request, pk):
    package = get_object_or_404(ProtectionPlusPackage, pk=pk)
    if package.docstatus != ProtectionPlusPackage.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('vas:pp_detail', args=[package.pk]))
    form    = ProtectionPlusPackageForm(request.POST or None, instance=package)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Protection Plus', 'update', pk)
        messages.success(request, 'Protection Plus package updated successfully.')
        return redirect('vas:pp_detail', pk=package.pk)
    return render(request, 'vas/pp_form.html',
                  {'form': form, 'title': 'Edit Protection Plus Package'})


# ---------------------------------------------------------------------------
# Submit / Cancel / Amend -- AMCPackage
# ---------------------------------------------------------------------------

@login_required
@require_POST
@require_module_action('vas', 'edit')
def amc_submit(request, pk):
    package = get_object_or_404(AMCPackage, pk=pk)
    if not user_owns(request.user, package):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        package.submit(request.user)
        log_action(request, 'AMC Package', 'update', pk)
        messages.success(request, f'AMC-{package.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:amc_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'edit')
def amc_cancel(request, pk):
    package = get_object_or_404(AMCPackage, pk=pk)
    if not user_is_manager(request.user):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        package.cancel(request.user)
        log_action(request, 'AMC Package', 'update', pk)
        messages.success(request, f'AMC-{package.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:amc_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'create')
def amc_amend(request, pk):
    package = get_object_or_404(AMCPackage, pk=pk)
    if not user_owns(request.user, package):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        new_package = package.amend()
        log_action(request, 'AMC Package', 'create', new_package.pk)
        messages.success(request, f'Amended as AMC-{new_package.pk}.')
        return redirect('vas:amc_detail', pk=new_package.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('vas:amc_detail', pk=pk)


# ---------------------------------------------------------------------------
# Submit / Cancel / Amend -- RSAPackage
# ---------------------------------------------------------------------------

@login_required
@require_POST
@require_module_action('vas', 'edit')
def rsa_submit(request, pk):
    package = get_object_or_404(RSAPackage, pk=pk)
    if not user_owns(request.user, package):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        package.submit(request.user)
        log_action(request, 'RSA Package', 'update', pk)
        messages.success(request, f'RSA-{package.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:rsa_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'edit')
def rsa_cancel(request, pk):
    package = get_object_or_404(RSAPackage, pk=pk)
    if not user_is_manager(request.user):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        package.cancel(request.user)
        log_action(request, 'RSA Package', 'update', pk)
        messages.success(request, f'RSA-{package.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:rsa_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'create')
def rsa_amend(request, pk):
    package = get_object_or_404(RSAPackage, pk=pk)
    if not user_owns(request.user, package):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        new_package = package.amend()
        log_action(request, 'RSA Package', 'create', new_package.pk)
        messages.success(request, f'Amended as RSA-{new_package.pk}.')
        return redirect('vas:rsa_detail', pk=new_package.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('vas:rsa_detail', pk=pk)


# ---------------------------------------------------------------------------
# Submit / Cancel / Amend -- ProtectionPlusPackage
# ---------------------------------------------------------------------------

@login_required
@require_POST
@require_module_action('vas', 'edit')
def pp_submit(request, pk):
    package = get_object_or_404(ProtectionPlusPackage, pk=pk)
    if not user_owns(request.user, package):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        package.submit(request.user)
        log_action(request, 'Protection Plus', 'update', pk)
        messages.success(request, f'PP-{package.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:pp_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'edit')
def pp_cancel(request, pk):
    package = get_object_or_404(ProtectionPlusPackage, pk=pk)
    if not user_is_manager(request.user):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        package.cancel(request.user)
        log_action(request, 'Protection Plus', 'update', pk)
        messages.success(request, f'PP-{package.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:pp_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'create')
def pp_amend(request, pk):
    package = get_object_or_404(ProtectionPlusPackage, pk=pk)
    if not user_owns(request.user, package):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        new_package = package.amend()
        log_action(request, 'Protection Plus', 'create', new_package.pk)
        messages.success(request, f'Amended as PP-{new_package.pk}.')
        return redirect('vas:pp_detail', pk=new_package.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('vas:pp_detail', pk=pk)


# ---------------------------------------------------------------------------
# Type masters
# ---------------------------------------------------------------------------

@login_required
def amc_type_list(request):
    return render(request, 'vas/amc_type_list.html', {'types': AMCType.objects.all()})


@login_required
@require_module_action('vas', 'create')
def amc_type_create(request):
    form = AMCTypeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'AMC Type', 'create', obj.pk)
        messages.success(request, 'AMC Type created successfully.')
        return redirect('vas:amc_type_list')
    return render(request, 'vas/amc_type_form.html', {'form': form, 'title': 'New AMC Type'})


@login_required
def rsa_type_list(request):
    return render(request, 'vas/rsa_type_list.html', {'types': RSAType.objects.all()})


@login_required
@require_module_action('vas', 'create')
def rsa_type_create(request):
    form = RSATypeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'RSA Type', 'create', obj.pk)
        messages.success(request, 'RSA Type created successfully.')
        return redirect('vas:rsa_type_list')
    return render(request, 'vas/rsa_type_form.html', {'form': form, 'title': 'New RSA Type'})


@login_required
def warranty_type_list(request):
    return render(request, 'vas/warranty_type_list.html', {'types': WarrantyType.objects.all()})


@login_required
@require_module_action('vas', 'create')
def warranty_type_create(request):
    form = WarrantyTypeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Warranty Type', 'create', obj.pk)
        messages.success(request, 'Warranty Type created successfully.')
        return redirect('vas:warranty_type_list')
    return render(request, 'vas/warranty_type_form.html', {'form': form, 'title': 'New Warranty Type'})


# ---------------------------------------------------------------------------
# RSA Creation
# ---------------------------------------------------------------------------

@login_required
def rsa_creation_list(request):
    return render(request, 'vas/rsa_creation_list.html', {
        'objs': RSACreation.objects.select_related('rsa_type', 'supplier').all(),
    })


@login_required
def rsa_creation_detail(request, pk):
    obj = get_object_or_404(RSACreation, pk=pk)
    return render(request, 'vas/rsa_creation_detail.html', {'obj': obj})


@login_required
@require_module_action('vas', 'create')
def rsa_creation_create(request):
    form = RSACreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'RSA Creation', 'create', obj.pk)
        messages.success(request, f'RSA-CRE-{obj.pk} created.')
        return redirect('vas:rsa_creation_detail', pk=obj.pk)
    return render(request, 'vas/rsa_creation_form.html', {'form': form, 'title': 'New RSA Creation'})


@login_required
@require_POST
@require_module_action('vas', 'edit')
def rsa_creation_submit(request, pk):
    obj = get_object_or_404(RSACreation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'RSA Creation', 'update', pk)
        messages.success(request, f'RSA-CRE-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:rsa_creation_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'edit')
def rsa_creation_cancel(request, pk):
    obj = get_object_or_404(RSACreation, pk=pk)
    if not user_is_manager(request.user):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        log_action(request, 'RSA Creation', 'update', pk)
        messages.success(request, f'RSA-CRE-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:rsa_creation_detail', pk=pk)


# ---------------------------------------------------------------------------
# VAS Supplier Invoice
# ---------------------------------------------------------------------------

@login_required
def vas_invoice_list(request):
    return render(request, 'vas/vas_invoice_list.html', {
        'invoices': VASSupplierInvoice.objects.select_related('supplier', 'branch').all(),
    })


@login_required
def vas_invoice_detail(request, pk):
    invoice = get_object_or_404(
        VASSupplierInvoice.objects.select_related('supplier', 'branch'), pk=pk
    )
    return render(request, 'vas/vas_invoice_detail.html', {
        'invoice': invoice,
        'items': invoice.items.select_related('amc_type', 'rsa_type', 'warranty_type').all(),
    })


@login_required
@require_module_action('vas', 'create')
def vas_invoice_create(request):
    form  = VASSupplierInvoiceForm(request.POST or None)
    items_formset = VASSupplierInvoiceItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and items_formset.is_valid():
            invoice = form.save()
            items_formset.instance = invoice
            items_formset.save()
            log_action(request, 'VAS Supplier Invoice', 'create', invoice.pk)
            messages.success(request, f'{invoice.invoice_number} created.')
            return redirect('vas:vas_invoice_detail', pk=invoice.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'vas/vas_invoice_form.html', {
        'form': form, 'title': 'New VAS Supplier Invoice', 'items_formset': items_formset,
    })


@login_required
@require_module_action('vas', 'edit')
def vas_invoice_update(request, pk):
    invoice = get_object_or_404(VASSupplierInvoice, pk=pk)
    if invoice.docstatus != VASSupplierInvoice.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('vas:vas_invoice_detail', args=[invoice.pk]))
    form = VASSupplierInvoiceForm(request.POST or None, instance=invoice)
    items_formset = VASSupplierInvoiceItemFormSet(request.POST or None, instance=invoice, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and items_formset.is_valid():
            form.save()
            items_formset.save()
            log_action(request, 'VAS Supplier Invoice', 'update', pk)
            messages.success(request, f'{invoice.invoice_number} updated.')
            return redirect('vas:vas_invoice_detail', pk=invoice.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'vas/vas_invoice_form.html', {
        'form': form, 'title': 'Edit VAS Supplier Invoice', 'items_formset': items_formset,
    })


@login_required
@require_POST
@require_module_action('vas', 'edit')
def vas_invoice_submit(request, pk):
    invoice = get_object_or_404(VASSupplierInvoice, pk=pk)
    try:
        invoice.submit(request.user)
        log_action(request, 'VAS Supplier Invoice', 'update', pk)
        messages.success(request, f'{invoice.invoice_number} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:vas_invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'edit')
def vas_invoice_cancel(request, pk):
    invoice = get_object_or_404(VASSupplierInvoice, pk=pk)
    if not user_is_manager(request.user):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        invoice.cancel(request.user)
        log_action(request, 'VAS Supplier Invoice', 'update', pk)
        messages.success(request, f'{invoice.invoice_number} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('vas:vas_invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('vas', 'create')
def vas_invoice_amend(request, pk):
    invoice = get_object_or_404(VASSupplierInvoice, pk=pk)
    try:
        new_invoice = invoice.amend()
        for item in invoice.items.all():
            item.pk = None
            item.invoice = new_invoice
            item.save()
        log_action(request, 'VAS Supplier Invoice', 'create', new_invoice.pk)
        messages.success(request, f'Amended as {new_invoice.invoice_number}.')
        return redirect('vas:vas_invoice_detail', pk=new_invoice.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('vas:vas_invoice_detail', pk=pk)
