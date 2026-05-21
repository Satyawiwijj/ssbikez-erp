from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import NumberPlateOrderForm, RTORegistrationForm
from .models import NumberPlateOrder, RTORegistration


@login_required
def registration_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = RTORegistration.objects.select_related(
        'sales_order__customer', 'sales_order__vehicle__bike_model'
    ).all()
    if q:
        qs = qs.filter(
            Q(registration_number__icontains=q) |
            Q(form20_number__icontains=q) |
            Q(sales_order__customer__full_name__icontains=q)
        )
    if status_filter:
        qs = qs.filter(registration_status=status_filter)
    return render(request, 'rto/registration_list.html', {
        'registrations':  qs,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': RTORegistration.RegistrationStatus.choices,
    })


@login_required
def registration_detail(request, pk):
    rto   = get_object_or_404(
        RTORegistration.objects.select_related(
            'sales_order__customer', 'sales_order__vehicle__bike_model'
        ),
        pk=pk
    )
    plate = getattr(rto, 'number_plate_order', None)
    return render(request, 'rto/registration_detail.html', {'rto': rto, 'plate': plate})


@login_required
def registration_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = RTORegistrationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        rto = form.save()
        messages.success(request, 'RTO registration created successfully.')
        return redirect('rto:registration_detail', pk=rto.pk)
    return render(request, 'rto/registration_form.html',
                  {'form': form, 'title': 'New RTO Registration'})


@login_required
def registration_update(request, pk):
    rto  = get_object_or_404(RTORegistration, pk=pk)
    form = RTORegistrationForm(request.POST or None, instance=rto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'RTO registration updated successfully.')
        return redirect('rto:registration_detail', pk=rto.pk)
    return render(request, 'rto/registration_form.html',
                  {'form': form, 'title': 'Edit RTO Registration'})


@login_required
@require_POST
def registration_status_update(request, pk):
    rto        = get_object_or_404(RTORegistration, pk=pk)
    new_status = request.POST.get('registration_status')
    if new_status in dict(RTORegistration.RegistrationStatus.choices):
        rto.registration_status = new_status
        rto.save(update_fields=['registration_status'])
        messages.success(request, f'RTO status updated to {rto.get_registration_status_display()}.')
    return redirect('rto:registration_detail', pk=rto.pk)


@login_required
def plate_create(request):
    initial = {}
    if request.GET.get('rto'):
        initial['rto'] = request.GET['rto']
    form = NumberPlateOrderForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        plate = form.save()
        messages.success(request, 'Number plate order created successfully.')
        return redirect('rto:registration_detail', pk=plate.rto_id)
    return render(request, 'rto/plate_form.html',
                  {'form': form, 'title': 'Add Number Plate Order'})


@login_required
def plate_update(request, pk):
    plate = get_object_or_404(NumberPlateOrder, pk=pk)
    form  = NumberPlateOrderForm(request.POST or None, instance=plate)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Number plate order updated successfully.')
        return redirect('rto:registration_detail', pk=plate.rto_id)
    return render(request, 'rto/plate_form.html',
                  {'form': form, 'title': 'Edit Number Plate Order'})
