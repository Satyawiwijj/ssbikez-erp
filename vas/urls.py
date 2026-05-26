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

    # RSAPackage
    path('rsa/',                      views.rsa_list,   name='rsa_list'),
    path('rsa/create/',               views.rsa_create, name='rsa_create'),
    path('rsa/<int:pk>/',             views.rsa_detail, name='rsa_detail'),
    path('rsa/<int:pk>/edit/',        views.rsa_update, name='rsa_update'),

    # ProtectionPlusPackage
    path('protection-plus/',          views.pp_list,    name='pp_list'),
    path('protection-plus/create/',   views.pp_create,  name='pp_create'),
    path('protection-plus/<int:pk>/', views.pp_detail,  name='pp_detail'),
    path('protection-plus/<int:pk>/edit/', views.pp_update, name='pp_update'),
]
