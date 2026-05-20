from django.urls import path

from . import views

app_name = 'service'

urlpatterns = [
    # ServiceEnquiry
    path('',                                    views.enquiry_list,           name='enquiry_list'),
    path('enquiries/create/',                   views.enquiry_create,         name='enquiry_create'),
    path('enquiries/<int:pk>/',                 views.enquiry_detail,         name='enquiry_detail'),
    path('enquiries/<int:pk>/edit/',            views.enquiry_update,         name='enquiry_update'),

    # ServiceAppointment
    path('appointments/create/',                views.appointment_create,     name='appointment_create'),
    path('appointments/<int:pk>/edit/',         views.appointment_update,     name='appointment_update'),
    path('appointments/<int:pk>/cancel/',       views.appointment_cancel,     name='appointment_cancel'),

    # JobCard
    path('jobcards/',                           views.jobcard_list,           name='jobcard_list'),
    path('jobcards/create/',                    views.jobcard_create,         name='jobcard_create'),
    path('jobcards/<int:pk>/',                  views.jobcard_detail,         name='jobcard_detail'),
    path('jobcards/<int:pk>/edit/',             views.jobcard_update,         name='jobcard_update'),
    path('jobcards/<int:pk>/status/',           views.jobcard_status_update,  name='jobcard_status_update'),

    # ServiceBay
    path('bays/',                               views.bay_list,               name='bay_list'),
    path('bays/create/',                        views.bay_create,             name='bay_create'),
    path('bays/<int:pk>/edit/',                 views.bay_update,             name='bay_update'),

    # BayAssignment
    path('bay-assignments/create/',             views.bay_assignment_create,  name='bay_assignment_create'),
    path('bay-assignments/<int:pk>/edit/',      views.bay_assignment_update,  name='bay_assignment_update'),

    # LaborCharge
    path('labor-charges/create/',               views.labor_charge_create,    name='labor_charge_create'),
    path('labor-charges/<int:pk>/edit/',        views.labor_charge_update,    name='labor_charge_update'),
    path('labor-charges/<int:pk>/delete/',      views.labor_charge_delete,    name='labor_charge_delete'),

    # ServiceInvoice
    path('invoices/create/',                    views.service_invoice_create, name='service_invoice_create'),
    path('invoices/<int:pk>/',                  views.service_invoice_detail, name='service_invoice_detail'),
    path('invoices/<int:pk>/edit/',             views.service_invoice_update, name='service_invoice_update'),

    # OutworkEntry
    path('outwork/create/',                     views.outwork_create,  name='outwork_create'),
    path('outwork/<int:pk>/edit/',              views.outwork_update,  name='outwork_update'),
    path('outwork/<int:pk>/return/',            views.outwork_return,  name='outwork_return'),
]
