"""
Complete production-level health check for ssbikez-erp.
Tests every GET endpoint with real data in the DB.
Run: python check_all.py
"""
import os, sys, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from decimal import Decimal
from django.conf import settings
from django.test import Client
from django.utils import timezone

if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from accounts.models import Branch, FuelExpense, Role, User
from customers.models import BikeModel, Customer, VehicleStock
from customer_vehicles.models import CustomerVehicle
from sales.models import (ExchangeVehicle, SalesAppointment, SalesFeedback,
                          SalesEnquiry, VehicleDelivery, VehicleSalesOrder)
from billing.models import FinanceLoan, InsurancePolicy, Invoice, Payment
from rto.models import NumberPlateOrder, RTORegistration
from service.models import (BayAssignment, JobCard, LaborCharge,
                             ServiceAppointment, ServiceBay, ServiceEnquiry,
                             ServiceInvoice)
from spares.models import (CounterSale, CounterSaleItem, PurchaseOrder,
                           PurchaseOrderItem, SparePart, SparesCategory,
                           SparesIssue, Supplier)
from vas.models import AMCPackage, ProtectionPlusPackage, RSAPackage

print("Creating test data...")
today     = datetime.date.today()
now       = timezone.now()
next_year = today.replace(year=today.year + 1)

branch, _   = Branch.objects.get_or_create(branch_name='_CheckBranch', defaults={'phone': '9999999999', 'gstin': '29ZZZZZ9999Z9Z9', 'is_active': True})
role, _     = Role.objects.get_or_create(role_name='_CheckRole')
User.objects.filter(username='_checkuser').delete()
user = User.objects.create_superuser(username='_checkuser', password='Ch3ck@pass99', email='check@ssbikez.test', first_name='Check', last_name='User')
user.branch = branch; user.role = role; user.save()

bike, _  = BikeModel.objects.get_or_create(brand='CheckBrand', model_name='CheckModel', defaults={'ex_showroom_price': Decimal('99999'), 'fuel_type': BikeModel.FuelType.PETROL})
stock, _ = VehicleStock.objects.get_or_create(chassis_no='CHKCH0001', defaults={'bike_model': bike, 'engine_no': 'CHKEN0001', 'color': 'Blue', 'stock_status': VehicleStock.StockStatus.AVAILABLE, 'branch': branch})
customer, _ = Customer.objects.get_or_create(phone='9000000001', defaults={'full_name': 'Check Customer'})
cv, _ = CustomerVehicle.objects.get_or_create(customer=customer, vehicle=stock, defaults={'registration_no': 'TN99CK0001'})

enquiry, _ = SalesEnquiry.objects.get_or_create(customer=customer, defaults={'sales_executive': user, 'bike_model': bike, 'branch': branch, 'status': SalesEnquiry.Status.OPEN})
appt, _ = SalesAppointment.objects.get_or_create(enquiry=enquiry, defaults={'appointment_date': now, 'purpose': SalesAppointment.Purpose.TEST_RIDE, 'status': SalesAppointment.Status.SCHEDULED})
SalesFeedback.objects.get_or_create(enquiry=enquiry, defaults={'feedback_notes': 'Check feedback', 'created_by': user})
order, _ = VehicleSalesOrder.objects.get_or_create(customer=customer, vehicle=stock, defaults={'enquiry': enquiry, 'sales_executive': user, 'branch': branch, 'booking_amount': Decimal('10000'), 'total_amount': Decimal('99999'), 'sales_status': VehicleSalesOrder.SalesStatus.BOOKED})
delivery, _ = VehicleDelivery.objects.get_or_create(sales_order=order, defaults={'delivery_date': today, 'delivered_by': user, 'remarks': 'Check delivery'})
exchange, _ = ExchangeVehicle.objects.get_or_create(sales_order=order, defaults={'old_vehicle_model': 'OldBike', 'registration_no': 'TN00XX0000', 'valuation_amount': Decimal('15000')})

invoice, _ = Invoice.objects.get_or_create(sales_order=order, defaults={'invoice_number': 'CHKINV001', 'subtotal': Decimal('94999'), 'gst_amount': Decimal('5000'), 'discount_amount': Decimal('0'), 'final_amount': Decimal('99999'), 'invoice_date': today})
payment, _ = Payment.objects.get_or_create(invoice=invoice, defaults={'payment_method': Payment.Method.CASH, 'amount': Decimal('99999'), 'payment_status': Payment.PaymentStatus.COMPLETED, 'payment_date': now})
loan, _ = FinanceLoan.objects.get_or_create(sales_order=order, defaults={'bank_name': 'CheckBank', 'loan_amount': Decimal('70000'), 'interest_rate': Decimal('9.0'), 'tenure_months': 24, 'emi_amount': Decimal('3200'), 'loan_status': FinanceLoan.LoanStatus.ACTIVE})
policy, _ = InsurancePolicy.objects.get_or_create(policy_number='CHKPOL001', defaults={'sales_order': order, 'provider_name': 'CheckInsure', 'premium_amount': Decimal('4500'), 'start_date': today, 'end_date': next_year})

rto, _ = RTORegistration.objects.get_or_create(sales_order=order, defaults={'form20_number': 'CHKF20001', 'rto_charges': Decimal('3000'), 'registration_status': RTORegistration.RegistrationStatus.PENDING})
plate, _ = NumberPlateOrder.objects.get_or_create(rto=rto, defaults={'status': NumberPlateOrder.Status.PENDING})

senq, _ = ServiceEnquiry.objects.get_or_create(customer_vehicle=cv, defaults={'created_by': user, 'issue_description': 'Check issue', 'status': ServiceEnquiry.Status.OPEN})
sapt, _ = ServiceAppointment.objects.get_or_create(service_enquiry=senq, defaults={'appointment_date': now, 'service_type': ServiceAppointment.ServiceType.PAID_SERVICE, 'status': ServiceAppointment.Status.SCHEDULED})
jc, _ = JobCard.objects.get_or_create(customer_vehicle=cv, defaults={'service_appointment': sapt, 'service_advisor': user, 'floor_supervisor': user, 'branch': branch, 'odometer_reading': 5000, 'problem_description': 'Check problem', 'service_status': JobCard.ServiceStatus.PENDING})
bay, _  = ServiceBay.objects.get_or_create(bay_name='CheckBay1', defaults={'status': ServiceBay.Status.AVAILABLE})
ba, _   = BayAssignment.objects.get_or_create(job_card=jc, bay=bay, defaults={'mechanic': user, 'assignment_status': BayAssignment.AssignmentStatus.ACTIVE})
labor, _ = LaborCharge.objects.get_or_create(job_card=jc, service_name='CheckService', defaults={'labor_cost': Decimal('500')})
sinv, _ = ServiceInvoice.objects.get_or_create(job_card=jc, defaults={'subtotal': Decimal('1500'), 'gst_amount': Decimal('270'), 'discount_amount': Decimal('0'), 'final_amount': Decimal('1770'), 'invoice_date': today})

cat, _      = SparesCategory.objects.get_or_create(category_name='_CheckCat')
part, _     = SparePart.objects.get_or_create(part_number='CHKPART001', defaults={'category': cat, 'part_name': 'CheckPart', 'mrp': Decimal('200'), 'stock_quantity': 50})
supplier, _ = Supplier.objects.get_or_create(supplier_name='_CheckSupplier', defaults={'phone': '9111111111'})
po, _  = PurchaseOrder.objects.get_or_create(supplier=supplier, defaults={'total_amount': Decimal('10000'), 'status': PurchaseOrder.Status.DRAFT})
poi, _ = PurchaseOrderItem.objects.get_or_create(purchase_order=po, spare_part=part, defaults={'quantity': 10, 'price': Decimal('180')})
cs, _  = CounterSale.objects.get_or_create(invoice_number='CHKCS001', defaults={'customer': customer, 'branch': branch, 'total_amount': Decimal('400'), 'created_by': user})
csi, _ = CounterSaleItem.objects.get_or_create(counter_sale=cs, spare_part=part, defaults={'quantity': 2, 'unit_price': Decimal('200'), 'total_price': Decimal('400')})
issue, _ = SparesIssue.objects.get_or_create(job_card=jc, spare_part=part, defaults={'quantity_issued': 2, 'quantity_returned': 0, 'unit_price': Decimal('200'), 'total_price': Decimal('400'), 'issued_by': user})

amc, _ = AMCPackage.objects.get_or_create(customer_vehicle=cv, package_name='_CheckAMC', defaults={'start_date': today, 'end_date': next_year, 'amount': Decimal('3000'), 'status': AMCPackage.Status.ACTIVE})
rsa, _ = RSAPackage.objects.get_or_create(customer_vehicle=cv, defaults={'provider_name': '_CheckRSA', 'start_date': today, 'end_date': next_year, 'amount': Decimal('1500'), 'status': RSAPackage.Status.ACTIVE})
pp, _  = ProtectionPlusPackage.objects.get_or_create(customer_vehicle=cv, package_name='_CheckPP', defaults={'provider_name': '_CheckPP Co', 'start_date': today, 'end_date': next_year, 'amount': Decimal('2000'), 'status': ProtectionPlusPackage.Status.ACTIVE})
fuel, _ = FuelExpense.objects.get_or_create(vehicle=stock, fuel_date=today, defaults={'amount': Decimal('500'), 'voucher_number': 'CHKV001', 'created_by': user})

print("Test data ready. Running checks...\n")

client = Client()
assert client.login(username='_checkuser', password='Ch3ck@pass99'), "Login failed!"

PASS = []; FAIL = []

def chk(url, label):
    try:
        resp = client.get(url, follow=True)
        code = resp.status_code
        body = resp.content.decode('utf-8', errors='replace')
        error_hint = ''
        if code != 200:
            error_hint = f'HTTP {code}'
        elif any(x in body for x in ('Exception Value', 'TemplateSyntaxError', 'FieldError', 'AttributeError', 'DoesNotExist', 'Server Error')):
            for line in body.split('\n'):
                l = line.strip()
                if any(x in l for x in ('Exception Value', 'TemplateSyntaxError', 'FieldError', 'AttributeError', 'DoesNotExist')):
                    error_hint = l[:150]; break
            if not error_hint: error_hint = 'Django error page detected'
        if error_hint: FAIL.append((label, url, error_hint))
        else: PASS.append(label)
    except Exception as e:
        FAIL.append((label, url, str(e)[:150]))

chk('/accounts/dashboard/', 'accounts > dashboard')
chk('/accounts/users/', 'accounts > user_list')
chk('/accounts/users/create/', 'accounts > user_create')
chk(f'/accounts/users/{user.pk}/edit/', 'accounts > user_update')
chk('/accounts/branches/', 'accounts > branch_list')
chk('/accounts/branches/create/', 'accounts > branch_create')
chk(f'/accounts/branches/{branch.pk}/edit/', 'accounts > branch_update')
chk('/accounts/roles/', 'accounts > role_list')
chk('/accounts/fuel-expenses/', 'accounts > fuel_expense_list')
chk('/accounts/fuel-expenses/create/', 'accounts > fuel_expense_create')
chk(f'/accounts/fuel-expenses/{fuel.pk}/edit/', 'accounts > fuel_expense_update')
chk('/customers/', 'customers > customer_list')
chk(f'/customers/{customer.pk}/', 'customers > customer_detail')
chk('/customers/create/', 'customers > customer_create')
chk(f'/customers/{customer.pk}/edit/', 'customers > customer_update')
chk('/customers/bikes/', 'customers > bike_model_list')
chk(f'/customers/bikes/{bike.pk}/', 'customers > bike_model_detail')
chk('/customers/bikes/create/', 'customers > bike_model_create')
chk(f'/customers/bikes/{bike.pk}/edit/', 'customers > bike_model_update')
chk('/customers/stock/', 'customers > vehicle_stock_list')
chk(f'/customers/stock/{stock.pk}/', 'customers > vehicle_stock_detail')
chk('/customers/stock/create/', 'customers > vehicle_stock_create')
chk(f'/customers/stock/{stock.pk}/edit/', 'customers > vehicle_stock_update')
chk('/customer-vehicles/', 'customer_vehicles > list')
chk(f'/customer-vehicles/{cv.pk}/', 'customer_vehicles > detail')
chk('/customer-vehicles/create/', 'customer_vehicles > create')
chk(f'/customer-vehicles/{cv.pk}/edit/', 'customer_vehicles > update')
chk('/sales/enquiries/', 'sales > enquiry_list')
chk('/sales/enquiries/create/', 'sales > enquiry_create')
chk(f'/sales/enquiries/{enquiry.pk}/', 'sales > enquiry_detail')
chk(f'/sales/enquiries/{enquiry.pk}/edit/', 'sales > enquiry_update')
chk(f'/sales/enquiries/{enquiry.pk}/appointments/', 'sales > appointment_list')
chk('/sales/appointments/create/', 'sales > appointment_create')
chk(f'/sales/appointments/{appt.pk}/edit/', 'sales > appointment_update')
chk(f'/sales/enquiries/{enquiry.pk}/feedback/', 'sales > feedback_list')
chk('/sales/feedback/create/', 'sales > feedback_create')
chk('/sales/orders/', 'sales > order_list')
chk('/sales/orders/create/', 'sales > order_create')
chk(f'/sales/orders/{order.pk}/', 'sales > order_detail')
chk(f'/sales/orders/{order.pk}/edit/', 'sales > order_update')
chk('/sales/delivery/create/', 'sales > delivery_create')
chk(f'/sales/delivery/{delivery.pk}/', 'sales > delivery_detail')
chk(f'/sales/delivery/{delivery.pk}/edit/', 'sales > delivery_update')
chk('/sales/exchange/create/', 'sales > exchange_create')
chk(f'/sales/exchange/{exchange.pk}/edit/', 'sales > exchange_update')
chk('/billing/invoices/', 'billing > invoice_list')
chk('/billing/invoices/create/', 'billing > invoice_create')
chk(f'/billing/invoices/{invoice.pk}/', 'billing > invoice_detail')
chk(f'/billing/invoices/{invoice.pk}/edit/', 'billing > invoice_update')
chk('/billing/payments/create/', 'billing > payment_create')
chk(f'/billing/payments/{payment.pk}/edit/', 'billing > payment_update')
chk(f'/billing/invoices/{invoice.pk}/payments/', 'billing > payment_list')
chk('/billing/loans/create/', 'billing > loan_create')
chk(f'/billing/loans/{loan.pk}/', 'billing > loan_detail')
chk(f'/billing/loans/{loan.pk}/edit/', 'billing > loan_update')
chk('/billing/insurance/', 'billing > insurance_policy_list')
chk('/billing/insurance/create/', 'billing > insurance_policy_create')
chk(f'/billing/insurance/{policy.pk}/', 'billing > insurance_policy_detail')
chk(f'/billing/insurance/{policy.pk}/edit/', 'billing > insurance_policy_update')
chk('/rto/', 'rto > registration_list')
chk('/rto/create/', 'rto > registration_create')
chk(f'/rto/{rto.pk}/', 'rto > registration_detail')
chk(f'/rto/{rto.pk}/edit/', 'rto > registration_update')
chk('/rto/plates/create/', 'rto > plate_create')
chk(f'/rto/plates/{plate.pk}/edit/', 'rto > plate_update')
chk('/service/', 'service > enquiry_list')
chk('/service/enquiries/create/', 'service > enquiry_create')
chk(f'/service/enquiries/{senq.pk}/', 'service > enquiry_detail')
chk(f'/service/enquiries/{senq.pk}/edit/', 'service > enquiry_update')
chk('/service/appointments/create/', 'service > appointment_create')
chk(f'/service/appointments/{sapt.pk}/edit/', 'service > appointment_update')
chk('/service/jobcards/', 'service > jobcard_list')
chk('/service/jobcards/create/', 'service > jobcard_create')
chk(f'/service/jobcards/{jc.pk}/', 'service > jobcard_detail')
chk(f'/service/jobcards/{jc.pk}/edit/', 'service > jobcard_update')
chk('/service/bays/', 'service > bay_list')
chk('/service/bays/create/', 'service > bay_create')
chk(f'/service/bays/{bay.pk}/edit/', 'service > bay_update')
chk('/service/bay-assignments/create/', 'service > bay_assignment_create')
chk(f'/service/bay-assignments/{ba.pk}/edit/', 'service > bay_assignment_update')
chk('/service/labor-charges/create/', 'service > labor_charge_create')
chk(f'/service/labor-charges/{labor.pk}/edit/', 'service > labor_charge_update')
chk('/service/invoices/create/', 'service > service_invoice_create')
chk(f'/service/invoices/{sinv.pk}/', 'service > service_invoice_detail')
chk(f'/service/invoices/{sinv.pk}/edit/', 'service > service_invoice_update')
chk('/spares/categories/', 'spares > category_list')
chk('/spares/categories/create/', 'spares > category_create')
chk(f'/spares/categories/{cat.pk}/edit/', 'spares > category_update')
chk('/spares/parts/', 'spares > part_list')
chk(f'/spares/parts/{part.pk}/', 'spares > part_detail')
chk('/spares/parts/create/', 'spares > part_create')
chk(f'/spares/parts/{part.pk}/edit/', 'spares > part_update')
chk('/spares/suppliers/', 'spares > supplier_list')
chk(f'/spares/suppliers/{supplier.pk}/', 'spares > supplier_detail')
chk('/spares/suppliers/create/', 'spares > supplier_create')
chk(f'/spares/suppliers/{supplier.pk}/edit/', 'spares > supplier_update')
chk('/spares/purchase-orders/', 'spares > po_list')
chk(f'/spares/purchase-orders/{po.pk}/', 'spares > po_detail')
chk('/spares/purchase-orders/create/', 'spares > po_create')
chk(f'/spares/purchase-orders/{po.pk}/edit/', 'spares > po_update')
chk('/spares/po-items/create/', 'spares > po_item_create')
chk(f'/spares/po-items/{poi.pk}/edit/', 'spares > po_item_update')
chk('/spares/counter-sales/', 'spares > counter_sale_list')
chk(f'/spares/counter-sales/{cs.pk}/', 'spares > counter_sale_detail')
chk('/spares/counter-sales/create/', 'spares > counter_sale_create')
chk(f'/spares/counter-sales/{cs.pk}/edit/', 'spares > counter_sale_update')
chk('/spares/counter-sale-items/create/', 'spares > counter_sale_item_create')
chk('/spares/issues/', 'spares > issue_list')
chk('/spares/issues/create/', 'spares > issue_create')
chk(f'/spares/issues/{issue.pk}/edit/', 'spares > issue_update')
chk('/vas/amc/', 'vas > amc_list')
chk('/vas/amc/create/', 'vas > amc_create')
chk(f'/vas/amc/{amc.pk}/', 'vas > amc_detail')
chk(f'/vas/amc/{amc.pk}/edit/', 'vas > amc_update')
chk('/vas/rsa/', 'vas > rsa_list')
chk('/vas/rsa/create/', 'vas > rsa_create')
chk(f'/vas/rsa/{rsa.pk}/', 'vas > rsa_detail')
chk(f'/vas/rsa/{rsa.pk}/edit/', 'vas > rsa_update')
chk('/vas/protection-plus/', 'vas > pp_list')
chk('/vas/protection-plus/create/', 'vas > pp_create')
chk(f'/vas/protection-plus/{pp.pk}/', 'vas > pp_detail')
chk(f'/vas/protection-plus/{pp.pk}/edit/', 'vas > pp_update')

total = len(PASS) + len(FAIL)
print('=' * 60)
print(f'  RESULTS: {len(PASS)}/{total} passed  |  {len(FAIL)} failed')
print('=' * 60)

if FAIL:
    print(f'\n{"FAILURES":^60}')
    print('-' * 60)
    for label, url, hint in FAIL:
        print(f'  FAIL  {label}')
        print(f'        {url}')
        print(f'        {hint}\n')

print(f'\n{"PASSED":^60}')
print('-' * 60)
for label in PASS:
    print(f'  OK  {label}')

print('\nCleaning up...')
User.objects.filter(username='_checkuser').delete()
print('Done.')
