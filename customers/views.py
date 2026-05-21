from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BikeModelForm, CustomerForm, VehicleStockForm
from .models import BikeModel, Customer, VehicleStock


@login_required
def customer_list(request):
    q = request.GET.get('q', '').strip()
    qs = Customer.objects.all()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q))
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'customers/customer_list.html',
                  {'customers': page_obj, 'page_obj': page_obj, 'q': q})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    vehicles = customer.vehicles.select_related('vehicle__bike_model').all()
    return render(request, 'customers/customer_detail.html',
                  {'customer': customer, 'vehicles': vehicles})


@login_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save()
        messages.success(request, 'Customer added successfully.')
        return redirect('customers:customer_detail', pk=customer.pk)
    return render(request, 'customers/customer_form.html',
                  {'form': form, 'title': 'Add Customer'})


@login_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Customer updated successfully.')
        return redirect('customers:customer_detail', pk=customer.pk)
    return render(request, 'customers/customer_form.html',
                  {'form': form, 'title': 'Edit Customer'})


@login_required
def bike_model_list(request):
    bike_models = BikeModel.objects.all()
    return render(request, 'customers/bike_model_list.html', {'bike_models': bike_models})


@login_required
def bike_model_detail(request, pk):
    bike_model = get_object_or_404(BikeModel, pk=pk)
    stock = bike_model.stock.select_related('branch').all()
    return render(request, 'customers/bike_model_detail.html',
                  {'bike_model': bike_model, 'stock': stock})


@login_required
def bike_model_create(request):
    form = BikeModelForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        bike_model = form.save()
        messages.success(request, 'Bike model added successfully.')
        return redirect('customers:bike_model_detail', pk=bike_model.pk)
    return render(request, 'customers/bike_model_form.html',
                  {'form': form, 'title': 'Add Bike Model'})


@login_required
def bike_model_update(request, pk):
    bike_model = get_object_or_404(BikeModel, pk=pk)
    form = BikeModelForm(request.POST or None, instance=bike_model)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bike model updated successfully.')
        return redirect('customers:bike_model_detail', pk=bike_model.pk)
    return render(request, 'customers/bike_model_form.html',
                  {'form': form, 'title': 'Edit Bike Model'})


@login_required
def vehicle_stock_list(request):
    stock_list = VehicleStock.objects.select_related('bike_model', 'branch').all()
    return render(request, 'customers/vehicle_stock_list.html', {'stock_list': stock_list})


@login_required
def vehicle_stock_detail(request, pk):
    stock = get_object_or_404(
        VehicleStock.objects.select_related('bike_model', 'branch'), pk=pk
    )
    return render(request, 'customers/vehicle_stock_detail.html', {'stock': stock})


@login_required
def vehicle_stock_create(request):
    form = VehicleStockForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        stock = form.save()
        messages.success(request, 'Vehicle stock entry added successfully.')
        return redirect('customers:vehicle_stock_detail', pk=stock.pk)
    return render(request, 'customers/vehicle_stock_form.html',
                  {'form': form, 'title': 'Add Vehicle Stock'})


@login_required
def vehicle_stock_update(request, pk):
    stock = get_object_or_404(VehicleStock, pk=pk)
    form = VehicleStockForm(request.POST or None, instance=stock)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Vehicle stock updated successfully.')
        return redirect('customers:vehicle_stock_detail', pk=stock.pk)
    return render(request, 'customers/vehicle_stock_form.html',
                  {'form': form, 'title': 'Edit Vehicle Stock'})
