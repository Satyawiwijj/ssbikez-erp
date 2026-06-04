from django.urls import path

from . import views

app_name = 'rto'

urlpatterns = [
    # Dashboard
    path('dashboard/',                    views.dashboard,                  name='dashboard'),

    # NumberPlate list
    path('plates/',                       views.plate_list,                 name='plate_list'),

    # RTORegistration
    path('',                              views.registration_list,          name='registration_list'),
    path('registrations/',                views.registration_list),          # alias
    path('create/',                       views.registration_create,        name='registration_create'),
    # Alias: /rto/registrations/create/ for compatibility
    path('registrations/create/',         views.registration_create,        name='registrations_create'),
    path('<int:pk>/',                     views.registration_detail,        name='registration_detail'),
    path('registrations/<int:pk>/',       views.registration_detail),        # alias
    path('<int:pk>/edit/',                views.registration_update,        name='registration_update'),
    path('<int:pk>/status/',              views.registration_status_update, name='registration_status_update'),

    # NumberPlateOrder
    path('plates/create/',                views.plate_create,               name='plate_create'),
    path('plates/<int:pk>/edit/',         views.plate_update,               name='plate_update'),

    # RC Book
    path('rc-books/',                     views.rc_book_list,               name='rc_book_list'),
    path('rc-books/<int:pk>/',            views.rc_book_detail,             name='rc_book_detail'),
    path('<int:rto_pk>/rc-book/',         views.rc_book_create,             name='rc_book_create'),

    # GAP 19 — Registration Payment
    path('<int:rto_pk>/reg-payment/',     views.reg_payment_create,         name='reg_payment_create'),

    # GAP 20 — RTO Income
    path('<int:rto_pk>/income/',          views.rto_income_create,          name='rto_income_create'),
]
