from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    # Invoice
    path('invoices/',                   views.invoice_list,   name='invoice_list'),
    path('invoices/create/',            views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/',          views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/',     views.invoice_update, name='invoice_update'),

    # Payment
    path('payments/create/',            views.payment_create, name='payment_create'),
    path('payments/<int:pk>/edit/',     views.payment_update, name='payment_update'),
    path('invoices/<int:invoice_pk>/payments/', views.payment_list, name='payment_list'),

    # InsurancePolicy
    path('insurance/',                       views.insurance_policy_list,   name='insurance_policy_list'),
    path('insurance/create/',                views.insurance_policy_create, name='insurance_policy_create'),
    path('insurance/<int:pk>/',              views.insurance_policy_detail, name='insurance_policy_detail'),
    path('insurance/<int:pk>/edit/',         views.insurance_policy_update, name='insurance_policy_update'),

    # FinanceLoan
    path('loans/create/',               views.loan_create,    name='loan_create'),
    path('loans/<int:pk>/',             views.loan_detail,    name='loan_detail'),
    path('loans/<int:pk>/edit/',        views.loan_update,    name='loan_update'),
]
