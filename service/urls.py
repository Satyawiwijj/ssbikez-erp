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
    path('follow-ups/',                         views.follow_up_list,         name='follow_up_list'),

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

    # Delete endpoints
    path('enquiries/<int:pk>/delete/',          views.enquiry_delete,         name='enquiry_delete'),
    path('appointments/<int:pk>/delete/',       views.appointment_delete,     name='appointment_delete'),
    path('jobcards/<int:pk>/delete/',           views.jobcard_delete,         name='jobcard_delete'),

    # Vehicle Service Master — ERP Alignment
    path('vehicle-service-master/',              views.vehicle_service_master_list,   name='vehicle_service_master_list'),
    path('vehicle-service-master/create/',       views.vehicle_service_master_create, name='vehicle_service_master_create'),
    path('vehicle-service-master/<int:pk>/',     views.vehicle_service_master_detail, name='vehicle_service_master_detail'),
    path('vehicle-service-master/<int:pk>/edit/', views.vehicle_service_master_update, name='vehicle_service_master_update'),

    # Phase 2 — Water Wash Done
    path('water-wash/create/',                  views.water_wash_create,  name='water_wash_create'),
    path('water-wash/<int:pk>/',                views.water_wash_detail,  name='water_wash_detail'),
    path('water-wash/<int:pk>/submit/',         views.water_wash_submit,  name='water_wash_submit'),
    path('water-wash/<int:pk>/cancel/',         views.water_wash_cancel,  name='water_wash_cancel'),

    # Phase 2 — Bay In Creation
    path('bay-in/create/',                      views.bay_in_create,      name='bay_in_create'),
    path('bay-in/<int:pk>/',                    views.bay_in_detail,      name='bay_in_detail'),
    path('bay-in/<int:pk>/submit/',             views.bay_in_submit,      name='bay_in_submit'),
    path('bay-in/<int:pk>/cancel/',              views.bay_in_cancel,      name='bay_in_cancel'),

    # Phase 2 — Bay Out Creation
    path('bay-out/create/',                     views.bay_out_create,     name='bay_out_create'),
    path('bay-out/<int:pk>/',                   views.bay_out_detail,     name='bay_out_detail'),
    path('bay-out/<int:pk>/submit/',            views.bay_out_submit,     name='bay_out_submit'),
    path('bay-out/<int:pk>/cancel/',             views.bay_out_cancel,     name='bay_out_cancel'),

    # Phase 2 — Final Inspection
    path('final-inspection/create/',            views.final_inspection_create, name='final_inspection_create'),
    path('final-inspection/<int:pk>/',          views.final_inspection_detail, name='final_inspection_detail'),
    path('final-inspection/<int:pk>/submit/',   views.final_inspection_submit, name='final_inspection_submit'),
    path('final-inspection/<int:pk>/cancel/',    views.final_inspection_cancel, name='final_inspection_cancel'),

    # Phase 2 — Outwork Entry Issue
    path('outwork-issue/create/',               views.outwork_issue_create, name='outwork_issue_create'),
    path('outwork-issue/<int:pk>/',             views.outwork_issue_detail, name='outwork_issue_detail'),
    path('outwork-issue/<int:pk>/submit/',      views.outwork_issue_submit, name='outwork_issue_submit'),
    path('outwork-issue/<int:pk>/cancel/',       views.outwork_issue_cancel, name='outwork_issue_cancel'),

    # Phase 2 — Outwork Entry Return
    path('outwork-return/create/',              views.outwork_return_create, name='outwork_return_create'),
    path('outwork-return/<int:pk>/',            views.outwork_return_detail, name='outwork_return_detail'),
    path('outwork-return/<int:pk>/submit/',     views.outwork_return_submit, name='outwork_return_submit'),
    path('outwork-return/<int:pk>/cancel/',      views.outwork_return_cancel, name='outwork_return_cancel'),

    # Phase 2 — Labor Charges Alteration
    path('labor-alteration/create/',            views.labor_alteration_create, name='labor_alteration_create'),
    path('labor-alteration/<int:pk>/',          views.labor_alteration_detail, name='labor_alteration_detail'),
    path('labor-alteration/<int:pk>/submit/',   views.labor_alteration_submit, name='labor_alteration_submit'),
    path('labor-alteration/<int:pk>/cancel/',    views.labor_alteration_cancel, name='labor_alteration_cancel'),
]
