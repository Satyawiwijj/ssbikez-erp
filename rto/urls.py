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
    path('<int:pk>/form20/',              views.form20_print,               name='form20_print'),

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

    # Phase 6 — masters
    path('registration-areas/',            views.registration_area_list,        name='registration_area_list'),
    path('registration-areas/create/',     views.registration_area_create,      name='registration_area_create'),
    path('regpay-base-amounts/',           views.regpay_base_amount_list,       name='regpay_base_amount_list'),
    path('regpay-base-amounts/create/',    views.regpay_base_amount_create,     name='regpay_base_amount_create'),
    path('register-numbers/',              views.register_number_master_list,   name='register_number_master_list'),
    path('register-numbers/create/',       views.register_number_master_create, name='register_number_master_create'),

    # Phase 6 — RC Hand Over
    path('rc-hand-over/create/',          views.rc_hand_over_create, name='rc_hand_over_create'),
    path('rc-hand-over/<int:pk>/',        views.rc_hand_over_detail, name='rc_hand_over_detail'),
    path('rc-hand-over/<int:pk>/submit/', views.rc_hand_over_submit, name='rc_hand_over_submit'),
    path('rc-hand-over/<int:pk>/cancel/', views.rc_hand_over_cancel, name='rc_hand_over_cancel'),

    # Phase 6 — Form 20 Creation
    path('form20-creation/create/',          views.form20_creation_create, name='form20_creation_create'),
    path('form20-creation/<int:pk>/',        views.form20_creation_detail, name='form20_creation_detail'),
    path('form20-creation/<int:pk>/submit/', views.form20_creation_submit, name='form20_creation_submit'),
    path('form20-creation/<int:pk>/cancel/', views.form20_creation_cancel, name='form20_creation_cancel'),

    # Phase 6 — Registration No Creation
    path('registration-no/create/',          views.registration_no_creation_create, name='registration_no_creation_create'),
    path('registration-no/<int:pk>/',        views.registration_no_creation_detail, name='registration_no_creation_detail'),
    path('registration-no/<int:pk>/submit/', views.registration_no_creation_submit, name='registration_no_creation_submit'),
    path('registration-no/<int:pk>/cancel/', views.registration_no_creation_cancel, name='registration_no_creation_cancel'),

    # Phase 6 — RTO Payment
    path('rto-payment/create/',          views.rto_payment_create, name='rto_payment_create'),
    path('rto-payment/<int:pk>/',        views.rto_payment_detail, name='rto_payment_detail'),
    path('rto-payment/<int:pk>/submit/', views.rto_payment_submit, name='rto_payment_submit'),
    path('rto-payment/<int:pk>/cancel/', views.rto_payment_cancel, name='rto_payment_cancel'),

    # Phase 6 — Regpay Creation
    path('regpay-creation/create/',          views.regpay_creation_create, name='regpay_creation_create'),
    path('regpay-creation/<int:pk>/',        views.regpay_creation_detail, name='regpay_creation_detail'),
    path('regpay-creation/<int:pk>/submit/', views.regpay_creation_submit, name='regpay_creation_submit'),
    path('regpay-creation/<int:pk>/cancel/', views.regpay_creation_cancel, name='regpay_creation_cancel'),

    # Phase 6 — Number Plate 3-stage flow
    path('number-order-entry/create/',          views.number_order_entry_create, name='number_order_entry_create'),
    path('number-order-entry/<int:pk>/',        views.number_order_entry_detail, name='number_order_entry_detail'),
    path('number-order-entry/<int:pk>/submit/', views.number_order_entry_submit, name='number_order_entry_submit'),
    path('number-order-entry/<int:pk>/cancel/', views.number_order_entry_cancel, name='number_order_entry_cancel'),

    path('number-receipt-entry/create/',          views.number_receipt_entry_create, name='number_receipt_entry_create'),
    path('number-receipt-entry/<int:pk>/',        views.number_receipt_entry_detail, name='number_receipt_entry_detail'),
    path('number-receipt-entry/<int:pk>/submit/', views.number_receipt_entry_submit, name='number_receipt_entry_submit'),
    path('number-receipt-entry/<int:pk>/cancel/', views.number_receipt_entry_cancel, name='number_receipt_entry_cancel'),

    path('number-plate-issue/create/',          views.number_plate_issue_create, name='number_plate_issue_create'),
    path('number-plate-issue/<int:pk>/',        views.number_plate_issue_detail, name='number_plate_issue_detail'),
    path('number-plate-issue/<int:pk>/submit/', views.number_plate_issue_submit, name='number_plate_issue_submit'),
    path('number-plate-issue/<int:pk>/cancel/', views.number_plate_issue_cancel, name='number_plate_issue_cancel'),

    # Phase 6 — RC Book Creation / Issue
    path('rc-book-creation/create/',          views.rc_book_creation_create, name='rc_book_creation_create'),
    path('rc-book-creation/<int:pk>/',        views.rc_book_creation_detail, name='rc_book_creation_detail'),
    path('rc-book-creation/<int:pk>/submit/', views.rc_book_creation_submit, name='rc_book_creation_submit'),
    path('rc-book-creation/<int:pk>/cancel/', views.rc_book_creation_cancel, name='rc_book_creation_cancel'),

    path('rc-book-issue/create/',          views.rc_book_issue_create, name='rc_book_issue_create'),
    path('rc-book-issue/<int:pk>/',        views.rc_book_issue_detail, name='rc_book_issue_detail'),
    path('rc-book-issue/<int:pk>/submit/', views.rc_book_issue_submit, name='rc_book_issue_submit'),
    path('rc-book-issue/<int:pk>/cancel/', views.rc_book_issue_cancel, name='rc_book_issue_cancel'),
]
