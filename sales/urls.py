from django.urls import path

from . import views

app_name = 'sales'

urlpatterns = [
    # SalesEnquiry
    path('enquiries/',                        views.enquiry_list,          name='enquiry_list'),
    path('enquiries/create/',                 views.enquiry_create,        name='enquiry_create'),
    path('enquiries/<int:pk>/',               views.enquiry_detail,        name='enquiry_detail'),
    path('enquiries/<int:pk>/edit/',          views.enquiry_update,        name='enquiry_update'),
    path('enquiries/<int:pk>/status/',        views.enquiry_status_update, name='enquiry_status_update'),

    # SalesAppointment
    path('enquiries/<int:enquiry_pk>/appointments/', views.appointment_list,   name='appointment_list'),
    path('appointments/create/',              views.appointment_create,    name='appointment_create'),
    path('appointments/<int:pk>/edit/',       views.appointment_update,    name='appointment_update'),
    path('appointments/<int:pk>/cancel/',     views.appointment_cancel,    name='appointment_cancel'),

    # SalesFeedback
    path('enquiries/<int:enquiry_pk>/feedback/', views.feedback_list,      name='feedback_list'),
    path('feedback/create/',                  views.feedback_create,       name='feedback_create'),

    # VehicleSalesOrder
    path('orders/',                           views.order_list,            name='order_list'),
    path('orders/create/',                    views.order_create,          name='order_create'),
    path('orders/<int:pk>/',                  views.order_detail,          name='order_detail'),
    path('orders/<int:pk>/edit/',             views.order_update,          name='order_update'),

    # ExchangeVehicle
    path('exchange/create/',                  views.exchange_create,       name='exchange_create'),
    path('exchange/<int:pk>/edit/',           views.exchange_update,       name='exchange_update'),
]
