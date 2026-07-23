"""Phase 6 — new-vehicle RTO stage documents (RC Hand Over, Form 20,
Registration No, RTO Payment, Regpay, Number Plate 3-stage flow, RC Book
Creation/Issue), plus their small masters. Split into its own module the
same way GAP 19/20's views live in _gap_views.py, imported via
`from rto._phase6_views import *` at the bottom of views.py."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.permissions import require_module_action

from .forms import (Form20CreationForm, NumberOrderEntryCreationForm,
                    NumberPlateIssueForm, NumberReceiptEntryCreationForm,
                    RCBookCreationForm, RCBookIssueForm, RCBookIssueItemFormSet,
                    RCHandOverForm, RegisterNumberMasterForm, RegistrationAreaForm,
                    RegistrationNoCreationForm, RegpayCreationForm, RegpayCreationItemFormSet,
                    RegPayBaseAmountForm, RTOPaymentForm, RTOPaymentItemFormSet)
from .models import (Form20Creation, NumberOrderEntryCreation, NumberPlateIssue,
                     NumberReceiptEntryCreation, RCBookCreation, RCBookIssue,
                     RCHandOver, RegisterNumberMaster, RegistrationArea,
                     RegistrationNoCreation, RegpayCreation, RegPayBaseAmount, RTOPayment)


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------

@login_required
def registration_area_list(request):
    return render(request, 'rto/registration_area_list.html', {
        'objs': RegistrationArea.objects.all(),
    })


@login_required
@require_module_action('rto', 'create')
def registration_area_create(request):
    form = RegistrationAreaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Registration Area', 'create', obj.pk)
        messages.success(request, 'Registration Area created successfully.')
        return redirect('rto:registration_area_list')
    return render(request, 'rto/registration_area_form.html', {'form': form, 'title': 'New Registration Area'})


@login_required
def regpay_base_amount_list(request):
    return render(request, 'rto/regpay_base_amount_list.html', {
        'objs': RegPayBaseAmount.objects.select_related('vehicle').all(),
    })


@login_required
@require_module_action('rto', 'create')
def regpay_base_amount_create(request):
    form = RegPayBaseAmountForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'RegPay Base Amount', 'create', obj.pk)
        messages.success(request, 'RegPay Base Amount created successfully.')
        return redirect('rto:regpay_base_amount_list')
    return render(request, 'rto/regpay_base_amount_form.html', {'form': form, 'title': 'New RegPay Base Amount'})


@login_required
def register_number_master_list(request):
    return render(request, 'rto/register_number_master_list.html', {
        'objs': RegisterNumberMaster.objects.all(),
    })


@login_required
@require_module_action('rto', 'create')
def register_number_master_create(request):
    form = RegisterNumberMasterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Register Number Master', 'create', obj.pk)
        messages.success(request, 'Register Number created successfully.')
        return redirect('rto:register_number_master_list')
    return render(request, 'rto/register_number_master_form.html', {'form': form, 'title': 'New Register Number'})


# ---------------------------------------------------------------------------
# RC Hand Over
# ---------------------------------------------------------------------------

@login_required
def rc_hand_over_detail(request, pk):
    obj = get_object_or_404(RCHandOver.objects.select_related('sales_order__customer'), pk=pk)
    return render(request, 'rto/rc_hand_over_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def rc_hand_over_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = RCHandOverForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'RC Hand Over', 'create', obj.pk)
        messages.success(request, f'RCH-{obj.pk} created.')
        return redirect('rto:rc_hand_over_detail', pk=obj.pk)
    return render(request, 'rto/rc_hand_over_form.html', {'form': form, 'title': 'New RC Hand Over'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rc_hand_over_submit(request, pk):
    obj = get_object_or_404(RCHandOver, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'RC Hand Over', 'update', pk)
        messages.success(request, f'RCH-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rc_hand_over_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rc_hand_over_cancel(request, pk):
    obj = get_object_or_404(RCHandOver, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'RC Hand Over', 'update', pk)
        messages.success(request, f'RCH-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rc_hand_over_detail', pk=pk)


# ---------------------------------------------------------------------------
# Form 20 Creation
# ---------------------------------------------------------------------------

@login_required
def form20_creation_detail(request, pk):
    obj = get_object_or_404(Form20Creation.objects.select_related('sales_order__customer'), pk=pk)
    return render(request, 'rto/form20_creation_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def form20_creation_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = Form20CreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Form 20 Creation', 'create', obj.pk)
        messages.success(request, f'FORM20-{obj.pk} created.')
        return redirect('rto:form20_creation_detail', pk=obj.pk)
    return render(request, 'rto/form20_creation_form.html', {'form': form, 'title': 'New Form 20 Creation'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def form20_creation_submit(request, pk):
    obj = get_object_or_404(Form20Creation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Form 20 Creation', 'update', pk)
        messages.success(request, f'FORM20-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:form20_creation_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def form20_creation_cancel(request, pk):
    obj = get_object_or_404(Form20Creation, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Form 20 Creation', 'update', pk)
        messages.success(request, f'FORM20-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:form20_creation_detail', pk=pk)


# ---------------------------------------------------------------------------
# Registration No Creation
# ---------------------------------------------------------------------------

@login_required
def registration_no_creation_detail(request, pk):
    obj = get_object_or_404(RegistrationNoCreation.objects.select_related('sales_order__customer'), pk=pk)
    return render(request, 'rto/registration_no_creation_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def registration_no_creation_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = RegistrationNoCreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Registration No Creation', 'create', obj.pk)
        messages.success(request, f'REGNO-{obj.pk} created.')
        return redirect('rto:registration_no_creation_detail', pk=obj.pk)
    return render(request, 'rto/registration_no_creation_form.html', {'form': form, 'title': 'New Registration No Creation'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def registration_no_creation_submit(request, pk):
    obj = get_object_or_404(RegistrationNoCreation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Registration No Creation', 'update', pk)
        messages.success(request, f'REGNO-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:registration_no_creation_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def registration_no_creation_cancel(request, pk):
    obj = get_object_or_404(RegistrationNoCreation, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Registration No Creation', 'update', pk)
        messages.success(request, f'REGNO-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:registration_no_creation_detail', pk=pk)


# ---------------------------------------------------------------------------
# RTO Payment
# ---------------------------------------------------------------------------

@login_required
def rto_payment_detail(request, pk):
    obj = get_object_or_404(RTOPayment, pk=pk)
    items = obj.items.select_related('sales_order__customer', 'branch')
    return render(request, 'rto/rto_payment_detail.html', {'obj': obj, 'items': items})


@login_required
@require_module_action('rto', 'create')
def rto_payment_create(request):
    form = RTOPaymentForm(request.POST or None)
    formset = RTOPaymentItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        obj.total_amount = sum((i.total_amount for i in obj.items.all()), start=0)
        obj.save()
        log_action(request, 'RTO Payment', 'create', obj.pk)
        messages.success(request, f'RTOPAY-{obj.pk} created.')
        return redirect('rto:rto_payment_detail', pk=obj.pk)
    return render(request, 'rto/rto_payment_form.html', {
        'form': form, 'formset': formset, 'title': 'New RTO Payment',
    })


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rto_payment_submit(request, pk):
    obj = get_object_or_404(RTOPayment, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'RTO Payment', 'update', pk)
        messages.success(request, f'RTOPAY-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rto_payment_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rto_payment_cancel(request, pk):
    obj = get_object_or_404(RTOPayment, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'RTO Payment', 'update', pk)
        messages.success(request, f'RTOPAY-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rto_payment_detail', pk=pk)


# ---------------------------------------------------------------------------
# Regpay Creation
# ---------------------------------------------------------------------------

@login_required
def regpay_creation_detail(request, pk):
    obj = get_object_or_404(RegpayCreation, pk=pk)
    items = obj.items.select_related('sales_order__customer', 'vehicle_type')
    return render(request, 'rto/regpay_creation_detail.html', {'obj': obj, 'items': items})


@login_required
@require_module_action('rto', 'create')
def regpay_creation_create(request):
    form = RegpayCreationForm(request.POST or None)
    formset = RegpayCreationItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        obj.total_amount = sum((i.amount for i in obj.items.all()), start=0)
        obj.save()
        log_action(request, 'Regpay Creation', 'create', obj.pk)
        messages.success(request, f'REGPAY-{obj.pk} created.')
        return redirect('rto:regpay_creation_detail', pk=obj.pk)
    return render(request, 'rto/regpay_creation_form.html', {
        'form': form, 'formset': formset, 'title': 'New Regpay Creation',
    })


@login_required
@require_POST
@require_module_action('rto', 'edit')
def regpay_creation_submit(request, pk):
    obj = get_object_or_404(RegpayCreation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Regpay Creation', 'update', pk)
        messages.success(request, f'REGPAY-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:regpay_creation_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def regpay_creation_cancel(request, pk):
    obj = get_object_or_404(RegpayCreation, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Regpay Creation', 'update', pk)
        messages.success(request, f'REGPAY-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:regpay_creation_detail', pk=pk)


# ---------------------------------------------------------------------------
# Number Order Entry Creation
# ---------------------------------------------------------------------------

@login_required
def number_order_entry_detail(request, pk):
    obj = get_object_or_404(NumberOrderEntryCreation.objects.select_related('sales_order__customer', 'agent'), pk=pk)
    return render(request, 'rto/number_order_entry_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def number_order_entry_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = NumberOrderEntryCreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Number Order Entry Creation', 'create', obj.pk)
        messages.success(request, f'NUMORD-{obj.pk} created.')
        return redirect('rto:number_order_entry_detail', pk=obj.pk)
    return render(request, 'rto/number_order_entry_form.html', {'form': form, 'title': 'New Number Order Entry'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def number_order_entry_submit(request, pk):
    obj = get_object_or_404(NumberOrderEntryCreation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Number Order Entry Creation', 'update', pk)
        messages.success(request, f'NUMORD-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:number_order_entry_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def number_order_entry_cancel(request, pk):
    obj = get_object_or_404(NumberOrderEntryCreation, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Number Order Entry Creation', 'update', pk)
        messages.success(request, f'NUMORD-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:number_order_entry_detail', pk=pk)


# ---------------------------------------------------------------------------
# Number Receipt Entry Creation
# ---------------------------------------------------------------------------

@login_required
def number_receipt_entry_detail(request, pk):
    obj = get_object_or_404(NumberReceiptEntryCreation.objects.select_related('order_entry', 'agent'), pk=pk)
    return render(request, 'rto/number_receipt_entry_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def number_receipt_entry_create(request):
    initial = {}
    if request.GET.get('order_entry'):
        initial['order_entry'] = request.GET['order_entry']
    form = NumberReceiptEntryCreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Number Receipt Entry Creation', 'create', obj.pk)
        messages.success(request, f'NUMREC-{obj.pk} created.')
        return redirect('rto:number_receipt_entry_detail', pk=obj.pk)
    return render(request, 'rto/number_receipt_entry_form.html', {'form': form, 'title': 'New Number Receipt Entry'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def number_receipt_entry_submit(request, pk):
    obj = get_object_or_404(NumberReceiptEntryCreation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Number Receipt Entry Creation', 'update', pk)
        messages.success(request, f'NUMREC-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:number_receipt_entry_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def number_receipt_entry_cancel(request, pk):
    obj = get_object_or_404(NumberReceiptEntryCreation, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Number Receipt Entry Creation', 'update', pk)
        messages.success(request, f'NUMREC-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:number_receipt_entry_detail', pk=pk)


# ---------------------------------------------------------------------------
# Number Plate Issue
# ---------------------------------------------------------------------------

@login_required
def number_plate_issue_detail(request, pk):
    obj = get_object_or_404(
        NumberPlateIssue.objects.select_related('receipt_entry', 'frame', 'warehouse', 'rack', 'bin'),
        pk=pk,
    )
    return render(request, 'rto/number_plate_issue_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def number_plate_issue_create(request):
    initial = {}
    if request.GET.get('receipt_entry'):
        initial['receipt_entry'] = request.GET['receipt_entry']
    form = NumberPlateIssueForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Number Plate Issue', 'create', obj.pk)
        messages.success(request, f'NUMISS-{obj.pk} created.')
        return redirect('rto:number_plate_issue_detail', pk=obj.pk)
    return render(request, 'rto/number_plate_issue_form.html', {'form': form, 'title': 'New Number Plate Issue'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def number_plate_issue_submit(request, pk):
    obj = get_object_or_404(NumberPlateIssue, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Number Plate Issue', 'update', pk)
        messages.success(request, f'NUMISS-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:number_plate_issue_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def number_plate_issue_cancel(request, pk):
    obj = get_object_or_404(NumberPlateIssue, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Number Plate Issue', 'update', pk)
        messages.success(request, f'NUMISS-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:number_plate_issue_detail', pk=pk)


# ---------------------------------------------------------------------------
# RC Book Creation
# ---------------------------------------------------------------------------

@login_required
def rc_book_creation_detail(request, pk):
    obj = get_object_or_404(
        RCBookCreation.objects.select_related('rto_registration__sales_order__customer', 'agent'),
        pk=pk,
    )
    return render(request, 'rto/rc_book_creation_detail.html', {'obj': obj})


@login_required
@require_module_action('rto', 'create')
def rc_book_creation_create(request):
    initial = {}
    if request.GET.get('rto'):
        initial['rto_registration'] = request.GET['rto']
    form = RCBookCreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'RC Book Creation', 'create', obj.pk)
        messages.success(request, f'RCBC-{obj.pk} created.')
        return redirect('rto:rc_book_creation_detail', pk=obj.pk)
    return render(request, 'rto/rc_book_creation_form.html', {'form': form, 'title': 'New RC Book Creation'})


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rc_book_creation_submit(request, pk):
    obj = get_object_or_404(RCBookCreation, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'RC Book Creation', 'update', pk)
        messages.success(request, f'RCBC-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rc_book_creation_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rc_book_creation_cancel(request, pk):
    obj = get_object_or_404(RCBookCreation, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'RC Book Creation', 'update', pk)
        messages.success(request, f'RCBC-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rc_book_creation_detail', pk=pk)


# ---------------------------------------------------------------------------
# RC Book Issue
# ---------------------------------------------------------------------------

@login_required
def rc_book_issue_detail(request, pk):
    obj = get_object_or_404(RCBookIssue.objects.select_related('rc_book_creation'), pk=pk)
    return render(request, 'rto/rc_book_issue_detail.html', {
        'obj': obj, 'items': obj.items.select_related('exchange_vehicle').all(),
    })


@login_required
@require_module_action('rto', 'create')
def rc_book_issue_create(request):
    initial = {}
    if request.GET.get('rc_book_creation'):
        initial['rc_book_creation'] = request.GET['rc_book_creation']
    form = RCBookIssueForm(request.POST or None, initial=initial)
    items_formset = RCBookIssueItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and items_formset.is_valid():
            has_exchange_vehicle = any(
                item.get('exchange_vehicle') for item in items_formset.cleaned_data if not item.get('DELETE')
            )
            if not has_exchange_vehicle and not form.cleaned_data.get('rc_book_creation'):
                form.add_error('rc_book_creation', 'This field is required unless issuing an exchange vehicle\'s own RC book.')
            else:
                obj = form.save()
                items_formset.instance = obj
                items_formset.save()
                log_action(request, 'RC Book Issue', 'create', obj.pk)
                messages.success(request, f'RCBI-{obj.pk} created.')
                return redirect('rto:rc_book_issue_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'rto/rc_book_issue_form.html', {
        'form': form, 'title': 'New RC Book Issue', 'items_formset': items_formset,
    })


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rc_book_issue_submit(request, pk):
    obj = get_object_or_404(RCBookIssue, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'RC Book Issue', 'update', pk)
        messages.success(request, f'RCBI-{obj.pk} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rc_book_issue_detail', pk=pk)


@login_required
@require_POST
@require_module_action('rto', 'edit')
def rc_book_issue_cancel(request, pk):
    obj = get_object_or_404(RCBookIssue, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'RC Book Issue', 'update', pk)
        messages.success(request, f'RCBI-{obj.pk} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('rto:rc_book_issue_detail', pk=pk)
