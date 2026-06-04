from django.urls import path

from . import views

app_name = 'service'

urlpatterns = [
    # Dashboard
    path('dashboard/',                          views.dashboard,              name='dashboard'),

    # Appointment list
    path('appointments/',                       views.appointment_list,       name='appointment_list'),

    # LaborCharge list
    path('labor-charges/',                      views.labor_charge_list,      name='labor_charge_list'),

    # ServiceEnquiry
    path('',                                    views.enquiry_list,           name='enquiry_list'),
    path('enquiries/',                          views.enquiry_list),           # alias
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

    # Print
    path('jobcards/<int:pk>/print/',            views.jobcard_print,   name='jobcard_print'),

    # GAP 4 — Job Card workflow
    path('jobcards/<int:pk>/advance/',          views.jobcard_advance_status, name='jobcard_advance_status'),

    # GAP 5 — Issue Spare from Job Card
    path('jobcards/<int:pk>/issue-spare/',      views.jobcard_issue_spare,    name='jobcard_issue_spare'),

    # GAP 9 — Warranty Claims
    path('warranty-claims/',                    views.warranty_claim_list,    name='warranty_claim_list'),
    path('warranty-claims/create/',             views.warranty_claim_create,  name='warranty_claim_create'),
    path('jobcards/<int:jc_pk>/warranty-claim/', views.warranty_claim_create, name='warranty_claim_create_for_jc'),
    path('warranty-claims/<int:pk>/',           views.warranty_claim_detail,  name='warranty_claim_detail'),
    path('warranty-claims/<int:pk>/edit/',      views.warranty_claim_update,  name='warranty_claim_update'),

    # GAP 10 — Insurance Estimation
    path('insurance-estimations/create/',       views.insurance_estimation_create, name='insurance_estimation_create'),
    path('jobcards/<int:jc_pk>/insurance-estimation/', views.insurance_estimation_create, name='insurance_estimation_create_for_jc'),
    path('insurance-estimations/<int:pk>/',     views.insurance_estimation_detail, name='insurance_estimation_detail'),
    path('insurance-estimations/<int:pk>/edit/', views.insurance_estimation_update, name='insurance_estimation_update'),

    # GAP 11 — Service Discount Master
    path('discount-master/',                    views.discount_master_list,   name='discount_master_list'),
    path('discount-master/create/',             views.discount_master_create, name='discount_master_create'),
    path('discount-master/<int:pk>/edit/',      views.discount_master_create, name='discount_master_update'),

    # GAP 14 — Job Card Revisit
    path('jobcards/<int:jc_pk>/revisit/',       views.revisit_create,         name='revisit_create'),

    # GAP 15 — Job Card Service Childs (sub-tasks)
    path('jobcards/<int:jc_pk>/childs/add/',    views.service_child_add,      name='service_child_add'),
    path('service-childs/<int:pk>/toggle/',     views.service_child_toggle,   name='service_child_toggle'),

    # GAP 22 — Service Enquiry Bulk Import
    path('bulk-import/',                        views.service_enquiry_bulk_import, name='enquiry_bulk_import'),

    # GAP 23 — Customer Call Log
    path('calls/',                              views.call_list,              name='call_list'),
    path('calls/create/',                       views.call_create,            name='call_create'),
    path('customer-vehicles/<int:cv_pk>/call/', views.call_create,            name='call_create_for_cv'),

    # GAP 24 — Update Customer from Job Card
    path('jobcards/<int:pk>/update-customer/',  views.jobcard_update_customer, name='jobcard_update_customer'),

    # GAP 26 — Insurance Claims
    path('insurance-claims/',                   views.insurance_claim_list,   name='insurance_claim_list'),
    path('jobcards/<int:jc_pk>/insurance-claim/', views.insurance_claim_create, name='insurance_claim_create'),
    path('insurance-claims/<int:pk>/',          views.insurance_claim_detail, name='insurance_claim_detail'),
    path('insurance-claims/<int:pk>/edit/',     views.insurance_claim_update, name='insurance_claim_update'),

    # GAP 30 — Additional Work Approval
    path('jobcards/<int:jc_pk>/additional-work/create/', views.additional_work_create, name='additional_work_create'),
    path('additional-work/<int:pk>/send/',      views.additional_work_send,   name='additional_work_send'),
    path('additional-work/<int:pk>/approve/',   views.additional_work_approve, name='additional_work_approve'),
    path('additional-work/<int:pk>/reject/',    views.additional_work_reject, name='additional_work_reject'),

    # FEATURE 4 — Service Reminders
    path('reminders/',                          views.reminder_list,          name='reminder_list'),
    path('reminders/<int:pk>/update/',          views.reminder_update,        name='reminder_update'),

    # FEATURE 7 — Technician Report
    path('technician-report/',                  views.technician_report,      name='technician_report'),
]
