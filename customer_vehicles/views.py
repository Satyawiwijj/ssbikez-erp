from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from service.models import JobCard
from vas.models import AMCPackage, ProtectionPlusPackage, RSAPackage

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
    #   job_cards       — JobCard queryset for this vehicle
    #   amc_packages    — AMCPackage queryset for this vehicle
    #   rsa_packages    — RSAPackage queryset for this vehicle
    #   protection_plus — ProtectionPlusPackage queryset for this vehicle
    cv = get_object_or_404(
        CustomerVehicle.objects.select_related('customer', 'vehicle__bike_model', 'vehicle__branch'),
        pk=pk
    )
    return render(request, 'customer_vehicles/customervehicle_detail.html', {
        'cv':              cv,
        'job_cards':       JobCard.objects.filter(customer_vehicle=cv).select_related('service_advisor', 'branch'),
        'amc_packages':    AMCPackage.objects.filter(customer_vehicle=cv),
        'rsa_packages':    RSAPackage.objects.filter(customer_vehicle=cv),
        'protection_plus': ProtectionPlusPackage.objects.filter(customer_vehicle=cv),
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
