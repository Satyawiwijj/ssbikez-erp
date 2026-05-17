from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomerVehicleForm
from .models import CustomerVehicle


@login_required
def customervehicle_list(request):
    # context: customer_vehicles — filtered queryset; q — current search string
    q = request.GET.get('q', '').strip()
    qs = CustomerVehicle.objects.select_related(
        'customer', 'vehicle__bike_model'
    ).all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) |
            Q(customer__phone__icontains=q) |
            Q(registration_no__icontains=q)
        )
    return render(request, 'customer_vehicles/customervehicle_list.html',
                  {'customer_vehicles': qs, 'q': q})


@login_required
def customervehicle_detail(request, pk):
    # context:
    #   cv              — CustomerVehicle instance
    #   job_cards       — TODO: wire in service.JobCard queryset (Team 2)
    #   amc_packages    — TODO: wire in vas.AMCPackage queryset (Team 2)
    #   rsa_packages    — TODO: wire in vas.RSAPackage queryset (Team 2)
    #   protection_plus — TODO: wire in vas.ProtectionPlusPackage queryset (Team 2)
    cv = get_object_or_404(
        CustomerVehicle.objects.select_related('customer', 'vehicle__bike_model', 'vehicle__branch'),
        pk=pk
    )
    return render(request, 'customer_vehicles/customervehicle_detail.html', {
        'cv':              cv,
        'job_cards':       [],   # TODO: cv.job_cards.all() once service app is wired
        'amc_packages':    [],   # TODO: cv.amc_packages.all() once vas app is wired
        'rsa_packages':    [],   # TODO: cv.rsa_packages.all() once vas app is wired
        'protection_plus': [],   # TODO: cv.protection_plus_packages.all() once vas app is wired
    })


@login_required
def customervehicle_create(request):
    # context: form — CustomerVehicleForm; title — str
    form = CustomerVehicleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cv = form.save()
        return redirect('customer_vehicles:customervehicle_detail', pk=cv.pk)
    return render(request, 'customer_vehicles/customervehicle_form.html',
                  {'form': form, 'title': 'Add Customer Vehicle'})


@login_required
def customervehicle_update(request, pk):
    # context: form — CustomerVehicleForm; title — str
    cv = get_object_or_404(CustomerVehicle, pk=pk)
    form = CustomerVehicleForm(request.POST or None, instance=cv)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('customer_vehicles:customervehicle_detail', pk=cv.pk)
    return render(request, 'customer_vehicles/customervehicle_form.html',
                  {'form': form, 'title': 'Edit Customer Vehicle'})
