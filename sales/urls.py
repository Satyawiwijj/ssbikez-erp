from django.urls import path

from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('',                                   views.dashboard,             name='dashboard'),

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

    # VehicleDelivery
    path('delivery/create/',                  views.delivery_create,       name='delivery_create'),
    path('delivery/<int:pk>/',                views.delivery_detail,       name='delivery_detail'),
    path('delivery/<int:pk>/edit/',           views.delivery_update,       name='delivery_update'),

    # ExchangeVehicle
    path('exchange/create/',                  views.exchange_create,       name='exchange_create'),
    path('exchange/<int:pk>/edit/',           views.exchange_update,       name='exchange_update'),
    path('exchange-list/',                    views.exchange_list,         name='exchange_list'),

    # Delivery list
    path('delivery-list/',                    views.delivery_list,         name='delivery_list'),
    path('delivery/',                         views.delivery_list),         # alias

    # All appointments (alias: /sales/appointments/ for compatibility)
    path('all-appointments/',                 views.all_appointments,      name='all_appointments'),
    path('appointments/',                     views.all_appointments,      name='appointments'),

    # Feedback all
    path('feedback-all/',                     views.feedback_all,          name='feedback_all'),

    # Follow-Up Board
    path('follow-ups/',                       views.follow_up_list,        name='follow_up_list'),

    # Vehicle Allotment (per order)
    path('orders/<int:order_pk>/allot/',      views.allotment_create,      name='allotment_create'),

    # Vehicle Fittings (per order)
    path('orders/<int:order_pk>/fittings/add/', views.fitting_create,      name='fitting_create'),
    path('fittings/<int:pk>/delete/',         views.fitting_delete,        name='fitting_delete'),

    # FEATURE 1 — Sales Targets & Leaderboard
    path('targets/',                          views.target_list,           name='target_list'),
    path('targets/create/',                   views.target_create,         name='target_create'),
    path('targets/<int:pk>/',                 views.target_detail,         name='target_detail'),
    path('leaderboard/',                      views.leaderboard,           name='leaderboard'),

    # FEATURE 3 — Test Ride Log
    path('test-rides/',                       views.test_ride_list,        name='test_ride_list'),
    path('test-rides/create/',                views.test_ride_create,      name='test_ride_create'),
    path('test-rides/<int:pk>/return/',       views.test_ride_return,      name='test_ride_return'),

    # FEATURE 5 — PDI Checklist
    path('orders/<int:pk>/pdi/',              views.pdi_create,            name='pdi_create'),
    path('pdi/<int:pk>/',                     views.pdi_detail,            name='pdi_detail'),
    path('pdi/<int:pk>/approve/',             views.pdi_approve,           name='pdi_approve'),

    # FEATURE 9 — Profit Report
    path('profit-report/',                    views.sale_profit_report,    name='profit_report'),
]
