from django.urls import path

from . import views

app_name = 'vas'

urlpatterns = [
    # Dashboard
    path('',                           views.dashboard,  name='dashboard'),

    # AMCPackage
    path('amc/',                      views.amc_list,   name='amc_list'),
    path('amc/create/',               views.amc_create, name='amc_create'),
    path('amc/<int:pk>/',             views.amc_detail, name='amc_detail'),
    path('amc/<int:pk>/edit/',        views.amc_update, name='amc_update'),
    path('amc/<int:pk>/submit/',      views.amc_submit, name='amc_submit'),
    path('amc/<int:pk>/cancel/',      views.amc_cancel, name='amc_cancel'),
    path('amc/<int:pk>/amend/',       views.amc_amend,  name='amc_amend'),

    # RSAPackage
    path('rsa/',                      views.rsa_list,   name='rsa_list'),
    path('rsa/create/',               views.rsa_create, name='rsa_create'),
    path('rsa/<int:pk>/',             views.rsa_detail, name='rsa_detail'),
    path('rsa/<int:pk>/edit/',        views.rsa_update, name='rsa_update'),
    path('rsa/<int:pk>/submit/',      views.rsa_submit, name='rsa_submit'),
    path('rsa/<int:pk>/cancel/',      views.rsa_cancel, name='rsa_cancel'),
    path('rsa/<int:pk>/amend/',       views.rsa_amend,  name='rsa_amend'),

    # ProtectionPlusPackage
    path('protection-plus/',          views.pp_list,    name='pp_list'),
    path('protection-plus/create/',   views.pp_create,  name='pp_create'),
    path('protection-plus/<int:pk>/', views.pp_detail,  name='pp_detail'),
    path('protection-plus/<int:pk>/edit/',   views.pp_update, name='pp_update'),
    path('protection-plus/<int:pk>/submit/', views.pp_submit, name='pp_submit'),
    path('protection-plus/<int:pk>/cancel/', views.pp_cancel, name='pp_cancel'),
    path('protection-plus/<int:pk>/amend/',  views.pp_amend,  name='pp_amend'),

    # Type masters
    path('amc-types/',                views.amc_type_list,      name='amc_type_list'),
    path('amc-types/create/',         views.amc_type_create,    name='amc_type_create'),
    path('rsa-types/',                views.rsa_type_list,      name='rsa_type_list'),
    path('rsa-types/create/',         views.rsa_type_create,    name='rsa_type_create'),
    path('warranty-types/',           views.warranty_type_list,   name='warranty_type_list'),
    path('warranty-types/create/',    views.warranty_type_create, name='warranty_type_create'),

    # RSA Creation
    path('rsa-creation/',                views.rsa_creation_list,   name='rsa_creation_list'),
    path('rsa-creation/create/',         views.rsa_creation_create, name='rsa_creation_create'),
    path('rsa-creation/<int:pk>/',       views.rsa_creation_detail, name='rsa_creation_detail'),
    path('rsa-creation/<int:pk>/submit/', views.rsa_creation_submit, name='rsa_creation_submit'),
    path('rsa-creation/<int:pk>/cancel/', views.rsa_creation_cancel, name='rsa_creation_cancel'),

    # VAS Supplier Invoice
    path('supplier-invoice/',                 views.vas_invoice_list,   name='vas_invoice_list'),
    path('supplier-invoice/create/',          views.vas_invoice_create, name='vas_invoice_create'),
    path('supplier-invoice/<int:pk>/',        views.vas_invoice_detail, name='vas_invoice_detail'),
    path('supplier-invoice/<int:pk>/edit/',   views.vas_invoice_update, name='vas_invoice_update'),
    path('supplier-invoice/<int:pk>/submit/', views.vas_invoice_submit, name='vas_invoice_submit'),
    path('supplier-invoice/<int:pk>/cancel/', views.vas_invoice_cancel, name='vas_invoice_cancel'),
    path('supplier-invoice/<int:pk>/amend/',  views.vas_invoice_amend,  name='vas_invoice_amend'),
]
