"""GAP 19, 20 RTO views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegPaymentForm, RTOIncomeForm
from .models import RegPayment, RTOIncome, RTORegistration


@login_required
def reg_payment_create(request, rto_pk):
    reg = get_object_or_404(RTORegistration, pk=rto_pk)
    form = RegPaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.rto_registration = reg
        obj.save()
        messages.success(request, 'Registration payment recorded.')
        return redirect('rto:registration_detail', pk=reg.pk)
    return render(request, 'rto/reg_payment_form.html', {'form': form, 'reg': reg})


@login_required
def rto_income_create(request, rto_pk):
    reg = get_object_or_404(RTORegistration, pk=rto_pk)
    form = RTOIncomeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.rto_registration = reg
        obj.save()
        messages.success(request, 'RTO income recorded.')
        return redirect('rto:registration_detail', pk=reg.pk)
    return render(request, 'rto/rto_income_form.html', {'form': form, 'reg': reg})
