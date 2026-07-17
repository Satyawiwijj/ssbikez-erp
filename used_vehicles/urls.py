from django.urls import path

from . import views

app_name = 'used_vehicles'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard),

    # Masters
    path('models/', views.model_list, name='model_list'),
    path('models/create/', views.model_create, name='model_create'),
    path('register-no/', views.register_no_list, name='register_no_list'),
    path('register-no/create/', views.register_no_create, name='register_no_create'),

    # Purchase Invoice
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/create/', views.purchase_create, name='purchase_create'),
    path('purchases/<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('purchases/<int:pk>/submit/', views.purchase_submit, name='purchase_submit'),
    path('purchases/<int:pk>/cancel/', views.purchase_cancel, name='purchase_cancel'),
    path('purchases/<int:pk>/amend/', views.purchase_amend, name='purchase_amend'),

    # Phase 10 — Purchase Order -> Purchase Receipt
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/submit/', views.purchase_order_submit, name='purchase_order_submit'),
    path('purchase-orders/<int:pk>/cancel/', views.purchase_order_cancel, name='purchase_order_cancel'),
    path('purchase-orders/<int:pk>/amend/', views.purchase_order_amend, name='purchase_order_amend'),

    path('purchase-receipts/', views.purchase_receipt_list, name='purchase_receipt_list'),
    path('purchase-receipts/create/', views.purchase_receipt_create, name='purchase_receipt_create'),
    path('purchase-receipts/<int:pk>/', views.purchase_receipt_detail, name='purchase_receipt_detail'),
    path('purchase-receipts/<int:pk>/submit/', views.purchase_receipt_submit, name='purchase_receipt_submit'),
    path('purchase-receipts/<int:pk>/cancel/', views.purchase_receipt_cancel, name='purchase_receipt_cancel'),
    path('purchase-receipts/<int:pk>/amend/', views.purchase_receipt_amend, name='purchase_receipt_amend'),

    # Sale
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/create/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/submit/', views.sale_submit, name='sale_submit'),
    path('sales/<int:pk>/cancel/', views.sale_cancel, name='sale_cancel'),
    path('sales/<int:pk>/amend/', views.sale_amend, name='sale_amend'),

    # Finance
    path('loans/create/', views.loan_create, name='loan_create'),

    # Delivery
    path('delivery/create/', views.delivery_create, name='delivery_create'),
    path('delivery/<int:pk>/', views.delivery_detail, name='delivery_detail'),
    path('delivery/<int:pk>/submit/', views.delivery_submit, name='delivery_submit'),
    path('delivery/<int:pk>/cancel/', views.delivery_cancel, name='delivery_cancel'),

    # Invoice
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/submit/', views.invoice_submit, name='invoice_submit'),
    path('invoices/<int:pk>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('invoices/<int:pk>/md-approve/', views.invoice_md_approve, name='invoice_md_approve'),

    # RC Hand Over / RC Book Issue
    path('rc-handover/', views.rc_handover_list, name='rc_handover_list'),
    path('rc-handover/create/', views.rc_handover_create, name='rc_handover_create'),
    path('rc-handover/<int:pk>/', views.rc_handover_detail, name='rc_handover_detail'),
    path('rc-handover/<int:pk>/submit/', views.rc_handover_submit, name='rc_handover_submit'),
    path('rc-handover/<int:pk>/cancel/', views.rc_handover_cancel, name='rc_handover_cancel'),
    path('rc-handover/<int:pk>/amend/', views.rc_handover_amend, name='rc_handover_amend'),

    path('rc-book-issue/', views.rc_book_issue_list, name='rc_book_issue_list'),
    path('rc-book-issue/create/', views.rc_book_issue_create, name='rc_book_issue_create'),
    path('rc-book-issue/<int:pk>/', views.rc_book_issue_detail, name='rc_book_issue_detail'),
    path('rc-book-issue/<int:pk>/submit/', views.rc_book_issue_submit, name='rc_book_issue_submit'),
    path('rc-book-issue/<int:pk>/cancel/', views.rc_book_issue_cancel, name='rc_book_issue_cancel'),
    path('rc-book-issue/<int:pk>/amend/', views.rc_book_issue_amend, name='rc_book_issue_amend'),

    # Phase 3b — Job Card
    path('jobcards/', views.jobcard_list, name='jobcard_list'),
    path('jobcards/create/', views.jobcard_create, name='jobcard_create'),
    path('jobcards/<int:pk>/', views.jobcard_detail, name='jobcard_detail'),
    path('jobcards/<int:pk>/edit/', views.jobcard_update, name='jobcard_update'),

    # Phase 3b — Bay In
    path('uv-bay-in/create/', views.uv_bay_in_create, name='uv_bay_in_create'),
    path('uv-bay-in/<int:pk>/', views.uv_bay_in_detail, name='uv_bay_in_detail'),
    path('uv-bay-in/<int:pk>/submit/', views.uv_bay_in_submit, name='uv_bay_in_submit'),
    path('uv-bay-in/<int:pk>/cancel/', views.uv_bay_in_cancel, name='uv_bay_in_cancel'),

    # Phase 3b — Bay Out
    path('uv-bay-out/create/', views.uv_bay_out_create, name='uv_bay_out_create'),
    path('uv-bay-out/<int:pk>/', views.uv_bay_out_detail, name='uv_bay_out_detail'),
    path('uv-bay-out/<int:pk>/submit/', views.uv_bay_out_submit, name='uv_bay_out_submit'),
    path('uv-bay-out/<int:pk>/cancel/', views.uv_bay_out_cancel, name='uv_bay_out_cancel'),

    # Phase 3b — Final Inspection
    path('uv-final-inspection/create/', views.uv_final_inspection_create, name='uv_final_inspection_create'),
    path('uv-final-inspection/<int:pk>/', views.uv_final_inspection_detail, name='uv_final_inspection_detail'),
    path('uv-final-inspection/<int:pk>/submit/', views.uv_final_inspection_submit, name='uv_final_inspection_submit'),
    path('uv-final-inspection/<int:pk>/cancel/', views.uv_final_inspection_cancel, name='uv_final_inspection_cancel'),

    # Phase 3b — Outwork Entry Issue
    path('uv-outwork-issue/create/', views.uv_outwork_issue_create, name='uv_outwork_issue_create'),
    path('uv-outwork-issue/<int:pk>/', views.uv_outwork_issue_detail, name='uv_outwork_issue_detail'),
    path('uv-outwork-issue/<int:pk>/submit/', views.uv_outwork_issue_submit, name='uv_outwork_issue_submit'),
    path('uv-outwork-issue/<int:pk>/cancel/', views.uv_outwork_issue_cancel, name='uv_outwork_issue_cancel'),

    # Phase 3b — Outwork Entry Return
    path('uv-outwork-return/create/', views.uv_outwork_return_create, name='uv_outwork_return_create'),
    path('uv-outwork-return/<int:pk>/', views.uv_outwork_return_detail, name='uv_outwork_return_detail'),
    path('uv-outwork-return/<int:pk>/submit/', views.uv_outwork_return_submit, name='uv_outwork_return_submit'),
    path('uv-outwork-return/<int:pk>/cancel/', views.uv_outwork_return_cancel, name='uv_outwork_return_cancel'),

    # Phase 3b — Labor Charge
    path('uv-labor-charge/create/', views.uv_labor_charge_create, name='uv_labor_charge_create'),
    path('uv-labor-charge/<int:pk>/', views.uv_labor_charge_detail, name='uv_labor_charge_detail'),
    path('uv-labor-charge/<int:pk>/submit/', views.uv_labor_charge_submit, name='uv_labor_charge_submit'),
    path('uv-labor-charge/<int:pk>/cancel/', views.uv_labor_charge_cancel, name='uv_labor_charge_cancel'),

    # Phase 3b — Service Invoice
    path('uv-service-invoice/create/', views.uv_service_invoice_create, name='uv_service_invoice_create'),
    path('uv-service-invoice/<int:pk>/', views.uv_service_invoice_detail, name='uv_service_invoice_detail'),

    # Phase 8c — Used Vehicle Master Settings
    path('master-settings/', views.used_vehicle_master_settings_list, name='used_vehicle_master_settings_list'),
    path('master-settings/create/', views.used_vehicle_master_settings_create, name='used_vehicle_master_settings_create'),
    path('master-settings/<int:pk>/', views.used_vehicle_master_settings_detail, name='used_vehicle_master_settings_detail'),
    path('master-settings/<int:pk>/submit/', views.used_vehicle_master_settings_submit, name='used_vehicle_master_settings_submit'),
    path('master-settings/<int:pk>/cancel/', views.used_vehicle_master_settings_cancel, name='used_vehicle_master_settings_cancel'),

    # Phase 8d — Used Vehicle Sales Setting
    path('sales-settings/', views.used_vehicle_sales_setting_list, name='used_vehicle_sales_setting_list'),
    path('sales-settings/create/', views.used_vehicle_sales_setting_create, name='used_vehicle_sales_setting_create'),
    path('sales-settings/<int:pk>/', views.used_vehicle_sales_setting_detail, name='used_vehicle_sales_setting_detail'),
    path('sales-settings/<int:pk>/edit/', views.used_vehicle_sales_setting_update, name='used_vehicle_sales_setting_update'),

    # Round-3 sweep — Used Vehicle Insurance Update
    path('insurance-updates/', views.used_vehicle_insurance_update_list, name='used_vehicle_insurance_update_list'),
    path('insurance-updates/create/', views.used_vehicle_insurance_update_create, name='used_vehicle_insurance_update_create'),
    path('insurance-updates/<int:pk>/', views.used_vehicle_insurance_update_detail, name='used_vehicle_insurance_update_detail'),
    path('insurance-updates/<int:pk>/edit/', views.used_vehicle_insurance_update_update, name='used_vehicle_insurance_update_update'),
    path('insurance-updates/<int:pk>/submit/', views.used_vehicle_insurance_update_submit, name='used_vehicle_insurance_update_submit'),
    path('insurance-updates/<int:pk>/cancel/', views.used_vehicle_insurance_update_cancel, name='used_vehicle_insurance_update_cancel'),
]
