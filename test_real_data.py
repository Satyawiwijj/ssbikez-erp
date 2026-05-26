"""
test_real_data.py
=================
Comprehensive real dealership data population for ssbikez-erp.
Run once to seed all 10 apps with realistic demo data.
Idempotent — safe to run multiple times (uses get_or_create throughout).
Data is intentionally LEFT in the DB as client demo sample.
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Django setup
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')
django.setup()

# Allow all hosts for test script
from django.conf import settings as django_settings
django_settings.ALLOWED_HOSTS = ['*']

from django.utils import timezone

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = 0
FAIL = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  [OK]  {msg}")

def fail(msg, exc=None):
    global FAIL
    FAIL += 1
    errmsg = f"  [FAIL] {msg}"
    if exc:
        errmsg += f"  ERROR: {exc}"
    print(errmsg)

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ---------------------------------------------------------------------------
# STEP 1: Accounts — Roles, Branches, Users
# ---------------------------------------------------------------------------
section("STEP 1: Accounts")

from accounts.models import Branch, Role, User

try:
    role_sales, _ = Role.objects.get_or_create(
        role_name='Sales Executive',
        defaults={'description': 'Handles vehicle sales and customer enquiries'}
    )
    role_service, _ = Role.objects.get_or_create(
        role_name='Service Advisor',
        defaults={'description': 'Handles service bookings and job cards'}
    )
    role_supervisor, _ = Role.objects.get_or_create(
        role_name='Floor Supervisor',
        defaults={'description': 'Supervises workshop floor operations'}
    )
    role_cashier, _ = Role.objects.get_or_create(
        role_name='Cashier',
        defaults={'description': 'Manages billing and payments'}
    )
    role_cre, _ = Role.objects.get_or_create(
        role_name='CRE',
        defaults={'description': 'Customer Relationship Executive'}
    )
    ok(f"5 Roles created/verified")
except Exception as e:
    fail("Roles", e)

try:
    branch1, _ = Branch.objects.get_or_create(
        branch_name='SSBikez Coimbatore',
        defaults={
            'address': '14, Avinashi Road, Peelamedu, Coimbatore - 641004',
            'phone': '0422-4567890',
            'gstin': '33AABCS1234D1Z5',
            'is_active': True,
        }
    )
    branch2, _ = Branch.objects.get_or_create(
        branch_name='SSBikez Tirupur',
        defaults={
            'address': '56, Palladam Road, Tirupur - 641601',
            'phone': '0421-2345678',
            'gstin': '33AABCS1234D2Z4',
            'is_active': True,
        }
    )
    ok(f"2 Branches created/verified")
except Exception as e:
    fail("Branches", e)

try:
    user_arjun, _ = User.objects.get_or_create(
        username='arjun.kumar',
        defaults={
            'first_name': 'Arjun',
            'last_name': 'Kumar',
            'email': 'arjun.kumar@ssbikez.com',
            'role': role_sales,
            'branch': branch1,
            'phone': '9876543210',
            'status': 'active',
            'is_staff': False,
        }
    )
    if not user_arjun.has_usable_password():
        user_arjun.set_password('SSBikez@2024')
        user_arjun.save()

    user_priya, _ = User.objects.get_or_create(
        username='priya.service',
        defaults={
            'first_name': 'Priya',
            'last_name': 'Devi',
            'email': 'priya.devi@ssbikez.com',
            'role': role_service,
            'branch': branch1,
            'phone': '9876543211',
            'status': 'active',
        }
    )
    if not user_priya.has_usable_password():
        user_priya.set_password('SSBikez@2024')
        user_priya.save()

    user_rajan, _ = User.objects.get_or_create(
        username='rajan.supervisor',
        defaults={
            'first_name': 'Rajan',
            'last_name': 'Pillai',
            'email': 'rajan.pillai@ssbikez.com',
            'role': role_supervisor,
            'branch': branch1,
            'phone': '9876543212',
            'status': 'active',
        }
    )
    if not user_rajan.has_usable_password():
        user_rajan.set_password('SSBikez@2024')
        user_rajan.save()

    user_meena, _ = User.objects.get_or_create(
        username='meena.cashier',
        defaults={
            'first_name': 'Meena',
            'last_name': 'Sundaram',
            'email': 'meena.sundaram@ssbikez.com',
            'role': role_cashier,
            'branch': branch1,
            'phone': '9876543213',
            'status': 'active',
        }
    )
    if not user_meena.has_usable_password():
        user_meena.set_password('SSBikez@2024')
        user_meena.save()

    user_divya, _ = User.objects.get_or_create(
        username='divya.cre',
        defaults={
            'first_name': 'Divya',
            'last_name': 'Krishnan',
            'email': 'divya.krishnan@ssbikez.com',
            'role': role_cre,
            'branch': branch2,
            'phone': '9876543214',
            'status': 'active',
        }
    )
    if not user_divya.has_usable_password():
        user_divya.set_password('SSBikez@2024')
        user_divya.save()

    ok(f"5 Users created/verified (arjun, priya, rajan, meena, divya)")
except Exception as e:
    fail("Users", e)

# ---------------------------------------------------------------------------
# STEP 2: Masters — Categories, Suppliers, Warehouses, Racks, Bins
# ---------------------------------------------------------------------------
section("STEP 2: Masters")

from masters.models import SparesCategory, Supplier, Warehouse, Rack, Bin

try:
    cat_engine, _ = SparesCategory.objects.get_or_create(name='Engine Parts')
    cat_elect, _  = SparesCategory.objects.get_or_create(name='Electrical & Ignition')
    cat_body, _   = SparesCategory.objects.get_or_create(name='Body & Frame')
    cat_lubri, _  = SparesCategory.objects.get_or_create(name='Lubricants & Oils')
    cat_brake, _  = SparesCategory.objects.get_or_create(name='Brake & Suspension')
    ok("5 SparesCategories created/verified")
except Exception as e:
    fail("SparesCategories", e)

try:
    sup1, _ = Supplier.objects.get_or_create(
        supplier_name='Honda Motorcycle & Scooter India',
        defaults={
            'contact_person': 'Venkat Raman',
            'phone': '044-28101234',
            'email': 'parts@hmsi.co.in',
            'gstin': '29AAACH0997E1ZL',
            'gst_category': 'Regular',
            'address_line1': '32, Rajiv Gandhi Salai',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600096',
            'place_of_supply': 'Tamil Nadu',
            'is_active': True,
        }
    )
    sup2, _ = Supplier.objects.get_or_create(
        supplier_name='Castrol India Ltd',
        defaults={
            'contact_person': 'Suresh Babu',
            'phone': '044-45671234',
            'email': 'orders@castrolindia.com',
            'gstin': '33AAACI1234F1Z3',
            'gst_category': 'Regular',
            'address_line1': '45, Anna Salai',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600002',
            'place_of_supply': 'Tamil Nadu',
            'is_active': True,
        }
    )
    ok("2 Suppliers created/verified")
except Exception as e:
    fail("Suppliers", e)

try:
    wh_main, _ = Warehouse.objects.get_or_create(
        name='Main Stores - Coimbatore',
        defaults={
            'warehouse_type': 'stores',
            'is_group': False,
            'address_line1': '14, Avinashi Road',
            'city': 'Coimbatore',
            'state': 'Tamil Nadu',
            'pin': '641004',
            'is_active': True,
        }
    )
    wh_service, _ = Warehouse.objects.get_or_create(
        name='Service Bay Stores',
        defaults={
            'warehouse_type': 'wip',
            'is_group': False,
            'address_line1': '14, Avinashi Road',
            'city': 'Coimbatore',
            'state': 'Tamil Nadu',
            'pin': '641004',
            'is_active': True,
        }
    )
    ok("2 Warehouses created/verified")
except Exception as e:
    fail("Warehouses", e)

try:
    rack_a, _ = Rack.objects.get_or_create(name='Rack-A', warehouse=wh_main)
    rack_b, _ = Rack.objects.get_or_create(name='Rack-B', warehouse=wh_main)
    rack_s, _ = Rack.objects.get_or_create(name='Rack-S', warehouse=wh_service)
    ok("3 Racks created/verified")
except Exception as e:
    fail("Racks", e)

try:
    bin_a1, _ = Bin.objects.get_or_create(name='Bin-A1', rack=rack_a)
    bin_a2, _ = Bin.objects.get_or_create(name='Bin-A2', rack=rack_a)
    bin_b1, _ = Bin.objects.get_or_create(name='Bin-B1', rack=rack_b)
    bin_s1, _ = Bin.objects.get_or_create(name='Bin-S1', rack=rack_s)
    ok("4 Bins created/verified")
except Exception as e:
    fail("Bins", e)

# ---------------------------------------------------------------------------
# STEP 3: Customers — Customers, BikeModels, VehicleStock
# ---------------------------------------------------------------------------
section("STEP 3: Customers")

from customers.models import Customer, BikeModel, VehicleStock

try:
    cust1, _ = Customer.objects.get_or_create(
        phone='9944112233',
        defaults={
            'full_name': 'Karthikeyan Murugan',
            'email': 'karthik.murugan@gmail.com',
            'address': '22/5, Bharathi Street, RS Puram, Coimbatore - 641002',
            'aadhaar_no': '4567 8901 2345',
            'pan_no': 'ABCPK1234M',
        }
    )
    cust2, _ = Customer.objects.get_or_create(
        phone='9944556677',
        defaults={
            'full_name': 'Lakshmi Narayanan',
            'email': 'lakshmi.n@yahoo.com',
            'address': '8, Gandhipuram Main Road, Coimbatore - 641012',
            'aadhaar_no': '5678 9012 3456',
            'pan_no': 'ABCPL5678N',
        }
    )
    cust3, _ = Customer.objects.get_or_create(
        phone='9944998877',
        defaults={
            'full_name': 'Selvam Perumal',
            'email': 'selvam.p@hotmail.com',
            'address': '3, Kamarajar Street, Tirupur - 641602',
            'aadhaar_no': '6789 0123 4567',
            'pan_no': 'ABCPS9012S',
        }
    )
    ok(f"3 Customers created/verified: {cust1}, {cust2}, {cust3}")
except Exception as e:
    fail("Customers", e)

try:
    bm1, _ = BikeModel.objects.get_or_create(
        brand='Honda', model_name='Shine', variant='DLX',
        defaults={
            'fuel_type': 'petrol',
            'available_colors': 'Imperial Red Metallic, Matte Axis Grey, Pearl Amazing White',
            'ex_showroom_price': Decimal('82500.00'),
        }
    )
    bm2, _ = BikeModel.objects.get_or_create(
        brand='Honda', model_name='SP 125', variant='CBS',
        defaults={
            'fuel_type': 'petrol',
            'available_colors': 'Athletic Blue Metallic, Sports Red, Pearl Sparkling Black',
            'ex_showroom_price': Decimal('94000.00'),
        }
    )
    bm3, _ = BikeModel.objects.get_or_create(
        brand='Honda', model_name='Activa 6G', variant='Standard',
        defaults={
            'fuel_type': 'petrol',
            'available_colors': 'Rebel Red Metallic, Pearl Amazing White, Matte Axis Grey',
            'ex_showroom_price': Decimal('79500.00'),
        }
    )
    bm4, _ = BikeModel.objects.get_or_create(
        brand='Honda', model_name='Hornet 2.0', variant='MT',
        defaults={
            'fuel_type': 'petrol',
            'available_colors': 'Matte Sangria Red Metallic, Matte Steel Black Metallic',
            'ex_showroom_price': Decimal('135000.00'),
        }
    )
    ok(f"4 BikeModels created/verified")
except Exception as e:
    fail("BikeModels", e)

try:
    vs1, _ = VehicleStock.objects.get_or_create(
        chassis_no='ME4JF502CCB123456',
        defaults={
            'bike_model': bm1,
            'branch': branch1,
            'engine_no': 'JF50E1CB123456',
            'color': 'Imperial Red Metallic',
            'stock_status': 'sold',
            'warehouse_location': 'Showroom Floor',
            'purchase_date': date(2025, 10, 1),
        }
    )
    vs2, _ = VehicleStock.objects.get_or_create(
        chassis_no='ME4JF502DDB234567',
        defaults={
            'bike_model': bm2,
            'branch': branch1,
            'engine_no': 'JF50E1DB234567',
            'color': 'Athletic Blue Metallic',
            'stock_status': 'sold',
            'warehouse_location': 'Showroom Floor',
            'purchase_date': date(2025, 10, 5),
        }
    )
    vs3, _ = VehicleStock.objects.get_or_create(
        chassis_no='ME4JF651ECB345678',
        defaults={
            'bike_model': bm3,
            'branch': branch1,
            'engine_no': 'JF65E1CB345678',
            'color': 'Pearl Amazing White',
            'stock_status': 'available',
            'warehouse_location': 'Rear Yard',
            'purchase_date': date(2025, 11, 1),
        }
    )
    vs4, _ = VehicleStock.objects.get_or_create(
        chassis_no='ME4KC1320PB456789',
        defaults={
            'bike_model': bm4,
            'branch': branch2,
            'engine_no': 'KC13E1PB456789',
            'color': 'Matte Steel Black Metallic',
            'stock_status': 'available',
            'warehouse_location': 'Showroom Floor',
            'purchase_date': date(2025, 11, 15),
        }
    )
    ok(f"4 VehicleStock records created/verified")
except Exception as e:
    fail("VehicleStock", e)

# ---------------------------------------------------------------------------
# STEP 4: Sales — Enquiries, Appointments, Feedback, Orders, Exchange
# ---------------------------------------------------------------------------
section("STEP 4: Sales")

from sales.models import (
    SalesEnquiry, SalesAppointment, SalesFeedback,
    VehicleSalesOrder, ExchangeVehicle
)

try:
    enq1, _ = SalesEnquiry.objects.get_or_create(
        customer=cust1,
        bike_model=bm1,
        defaults={
            'sales_executive': user_arjun,
            'branch': branch1,
            'enquiry_source': 'walk_in',
            'status': 'converted',
            'remarks': 'Customer walked in, test ride done, booked Honda Shine DLX in Red',
        }
    )
    enq2, _ = SalesEnquiry.objects.get_or_create(
        customer=cust2,
        bike_model=bm2,
        defaults={
            'sales_executive': user_arjun,
            'branch': branch1,
            'enquiry_source': 'phone',
            'status': 'converted',
            'remarks': 'Called for SP 125 CBS, EMI option discussed with HDFC Bank',
        }
    )
    enq3, _ = SalesEnquiry.objects.get_or_create(
        customer=cust3,
        bike_model=bm3,
        defaults={
            'sales_executive': user_divya,
            'branch': branch2,
            'enquiry_source': 'referral',
            'status': 'follow_up',
            'remarks': 'Referred by existing customer, interested in Activa 6G, follow up next week',
        }
    )
    ok(f"3 SalesEnquiries created/verified")
except Exception as e:
    fail("SalesEnquiries", e)

try:
    apt1, _ = SalesAppointment.objects.get_or_create(
        enquiry=enq1,
        defaults={
            'appointment_date': timezone.make_aware(
                timezone.datetime(2025, 11, 10, 10, 0)
            ),
            'purpose': 'test_ride',
            'status': 'completed',
        }
    )
    apt2, _ = SalesAppointment.objects.get_or_create(
        enquiry=enq2,
        defaults={
            'appointment_date': timezone.make_aware(
                timezone.datetime(2025, 11, 12, 11, 30)
            ),
            'purpose': 'delivery',
            'status': 'completed',
        }
    )
    ok(f"2 SalesAppointments created/verified")
except Exception as e:
    fail("SalesAppointments", e)

try:
    fb1, _ = SalesFeedback.objects.get_or_create(
        enquiry=enq3,
        defaults={
            'feedback_notes': 'Customer is comparing with TVS Jupiter. Price and mileage are key concerns.',
            'next_followup_date': date.today() + timedelta(days=7),
            'created_by': user_divya,
        }
    )
    ok(f"1 SalesFeedback created/verified")
except Exception as e:
    fail("SalesFeedback", e)

try:
    order1, _ = VehicleSalesOrder.objects.get_or_create(
        customer=cust1,
        vehicle=vs1,
        defaults={
            'enquiry': enq1,
            'sales_executive': user_arjun,
            'branch': branch1,
            'booking_amount': Decimal('5000.00'),
            'discount_amount': Decimal('2000.00'),
            'total_amount': Decimal('82500.00'),
            'sales_status': 'delivered',
        }
    )
    order2, _ = VehicleSalesOrder.objects.get_or_create(
        customer=cust2,
        vehicle=vs2,
        defaults={
            'enquiry': enq2,
            'sales_executive': user_arjun,
            'branch': branch1,
            'booking_amount': Decimal('10000.00'),
            'discount_amount': Decimal('1000.00'),
            'total_amount': Decimal('94000.00'),
            'sales_status': 'invoiced',
        }
    )
    ok(f"2 VehicleSalesOrders created/verified")
except Exception as e:
    fail("VehicleSalesOrders", e)

try:
    exch, _ = ExchangeVehicle.objects.get_or_create(
        sales_order=order1,
        defaults={
            'old_vehicle_model': 'TVS Star City Plus 110',
            'registration_no': 'TN 37 AB 1234',
            'valuation_amount': Decimal('25000.00'),
        }
    )
    ok(f"1 ExchangeVehicle created/verified")
except Exception as e:
    fail("ExchangeVehicle", e)

# ---------------------------------------------------------------------------
# STEP 5: Customer Vehicles
# ---------------------------------------------------------------------------
section("STEP 5: Customer Vehicles")

from customer_vehicles.models import CustomerVehicle

try:
    cv1, _ = CustomerVehicle.objects.get_or_create(
        customer=cust1,
        vehicle=vs1,
        defaults={
            'registration_no': 'TN 37 BH 5678',
            'purchase_date': date(2025, 11, 15),
            'insurance_expiry': date.today() + timedelta(days=340),
        }
    )
    cv2, _ = CustomerVehicle.objects.get_or_create(
        customer=cust2,
        vehicle=vs2,
        defaults={
            'registration_no': 'TN 37 BK 9012',
            'purchase_date': date(2025, 11, 20),
            # insurance expiring in 25 days — triggers alert
            'insurance_expiry': date.today() + timedelta(days=25),
        }
    )
    cv3, _ = CustomerVehicle.objects.get_or_create(
        customer=cust3,
        vehicle=vs3,
        defaults={
            'registration_no': 'TN 43 CM 3456',
            'purchase_date': date(2024, 5, 10),
            'insurance_expiry': date.today() + timedelta(days=180),
        }
    )
    ok(f"3 CustomerVehicles created/verified (cv2 insurance expires in 25 days)")
except Exception as e:
    fail("CustomerVehicles", e)

# ---------------------------------------------------------------------------
# STEP 6: Billing — Invoice, Payments, FinanceLoan, InsurancePolicy
# ---------------------------------------------------------------------------
section("STEP 6: Billing")

from billing.models import Invoice, Payment, InsurancePolicy, FinanceLoan

try:
    inv_no = f"INV-{date.today().year}-001"
    inv1, _ = Invoice.objects.get_or_create(
        invoice_number=inv_no,
        defaults={
            'sales_order': order1,
            'subtotal': Decimal('82500.00'),
            'gst_amount': Decimal('0.00'),
            'discount_amount': Decimal('2000.00'),
            'final_amount': Decimal('80500.00'),
            'invoice_date': date(2025, 11, 15),
        }
    )
    ok(f"1 Invoice created/verified: {inv_no}")
except Exception as e:
    fail("Invoice", e)

try:
    pay1, _ = Payment.objects.get_or_create(
        invoice=inv1,
        payment_method='cash',
        defaults={
            'transaction_reference': 'CASH-20251115-001',
            'amount': Decimal('30500.00'),
            'payment_status': 'completed',
            'payment_date': timezone.make_aware(
                timezone.datetime(2025, 11, 15, 14, 30)
            ),
        }
    )
    pay2, _ = Payment.objects.get_or_create(
        invoice=inv1,
        payment_method='neft',
        defaults={
            'transaction_reference': 'NEFT20251115HDFC001234',
            'amount': Decimal('50000.00'),
            'payment_status': 'completed',
            'payment_date': timezone.make_aware(
                timezone.datetime(2025, 11, 16, 10, 0)
            ),
        }
    )
    ok(f"2 Payments created/verified (cash + NEFT)")
except Exception as e:
    fail("Payments", e)

try:
    loan1, _ = FinanceLoan.objects.get_or_create(
        sales_order=order2,
        defaults={
            'bank_name': 'HDFC Bank',
            'loan_amount': Decimal('70000.00'),
            'interest_rate': Decimal('8.50'),
            'tenure_months': 36,
            'emi_amount': Decimal('2203.00'),
            'loan_status': 'active',
        }
    )
    ok(f"1 FinanceLoan created/verified (HDFC)")
except Exception as e:
    fail("FinanceLoan", e)

try:
    insure1, _ = InsurancePolicy.objects.get_or_create(
        policy_number='BJ-2025-TN-4521890',
        defaults={
            'sales_order': order1,
            'provider_name': 'Bajaj Allianz General Insurance',
            'premium_amount': Decimal('4850.00'),
            'start_date': date(2025, 11, 15),
            'end_date': date(2026, 11, 14),
        }
    )
    ok(f"1 InsurancePolicy created/verified (Bajaj Allianz)")
except Exception as e:
    fail("InsurancePolicy", e)

# ---------------------------------------------------------------------------
# STEP 7: RTO — RTORegistration, NumberPlateOrder
# ---------------------------------------------------------------------------
section("STEP 7: RTO")

from rto.models import RTORegistration, NumberPlateOrder

try:
    rto1, _ = RTORegistration.objects.get_or_create(
        sales_order=order1,
        defaults={
            'form20_number': 'FORM20-CBE-2025-45678',
            'registration_number': 'TN 37 BH 5678',
            'rto_charges': Decimal('3200.00'),
            'registration_status': 'registered',
        }
    )
    ok(f"1 RTORegistration created/verified")
except Exception as e:
    fail("RTORegistration", e)

try:
    plate1, _ = NumberPlateOrder.objects.get_or_create(
        rto=rto1,
        defaults={
            'plate_number': 'TN 37 BH 5678',
            'vendor_name': 'HSRP Solutions Coimbatore',
            'issue_date': date(2025, 11, 20),
            'status': 'issued',
        }
    )
    ok(f"1 NumberPlateOrder created/verified (HSRP)")
except Exception as e:
    fail("NumberPlateOrder", e)

# ---------------------------------------------------------------------------
# STEP 8: VAS — AMC, RSA, ProtectionPlus
# ---------------------------------------------------------------------------
section("STEP 8: Value Added Services")

from vas.models import AMCPackage, RSAPackage, ProtectionPlusPackage

try:
    amc1, _ = AMCPackage.objects.get_or_create(
        customer_vehicle=cv1,
        package_name='Honda AMC Gold 3yr',
        defaults={
            'start_date': date(2025, 11, 15),
            'end_date': date(2028, 11, 14),
            'amount': Decimal('6500.00'),
            'status': 'active',
        }
    )
    ok(f"1 AMCPackage created/verified")
except Exception as e:
    fail("AMCPackage", e)

try:
    rsa1, _ = RSAPackage.objects.get_or_create(
        customer_vehicle=cv1,
        provider_name='Honda RSA Plus',
        defaults={
            'start_date': date(2025, 11, 15),
            'end_date': date(2026, 11, 14),
            'amount': Decimal('1200.00'),
            'status': 'active',
        }
    )
    ok(f"1 RSAPackage created/verified")
except Exception as e:
    fail("RSAPackage", e)

try:
    pp1, _ = ProtectionPlusPackage.objects.get_or_create(
        customer_vehicle=cv1,
        package_name='Honda Scratch Guard',
        defaults={
            'provider_name': 'Honda Genuine Accessories',
            'start_date': date(2025, 11, 15),
            'end_date': date(2027, 11, 14),
            'amount': Decimal('3500.00'),
            'status': 'active',
        }
    )
    ok(f"1 ProtectionPlusPackage created/verified")
except Exception as e:
    fail("ProtectionPlusPackage", e)

# ---------------------------------------------------------------------------
# STEP 9: Service — Enquiries, Appointments, Bays, JobCard, etc.
# ---------------------------------------------------------------------------
section("STEP 9: Service")

from service.models import (
    ServiceEnquiry, ServiceAppointment, JobCard,
    ServiceBay, BayAssignment, ServiceInvoice, LaborCharge, OutworkEntry
)

try:
    senq1, _ = ServiceEnquiry.objects.get_or_create(
        customer_vehicle=cv1,
        defaults={
            'created_by': user_priya,
            'issue_description': '1st free service at 700 km — oil change, chain lubrication, brake adjustment',
            'status': 'closed',
        }
    )
    senq2, _ = ServiceEnquiry.objects.get_or_create(
        customer_vehicle=cv2,
        defaults={
            'created_by': user_priya,
            'issue_description': 'Engine vibration at idle, front brake spongy, horn not working',
            'status': 'scheduled',
        }
    )
    ok(f"2 ServiceEnquiries created/verified")
except Exception as e:
    fail("ServiceEnquiries", e)

try:
    sapt1, _ = ServiceAppointment.objects.get_or_create(
        service_enquiry=senq1,
        defaults={
            'appointment_date': timezone.make_aware(
                timezone.datetime(2026, 1, 10, 9, 0)
            ),
            'service_type': 'free_service',
            'status': 'completed',
        }
    )
    ok(f"1 ServiceAppointment created/verified")
except Exception as e:
    fail("ServiceAppointment", e)

try:
    bay1, _ = ServiceBay.objects.get_or_create(
        bay_name='Bay 1 — General Service',
        defaults={'status': 'available'}
    )
    bay2, _ = ServiceBay.objects.get_or_create(
        bay_name='Bay 2 — Engine Work',
        defaults={'status': 'available'}
    )
    bay3, _ = ServiceBay.objects.get_or_create(
        bay_name='Bay 3 — Electrical',
        defaults={'status': 'occupied'}
    )
    ok(f"3 ServiceBays created/verified")
except Exception as e:
    fail("ServiceBays", e)

try:
    jc1, _ = JobCard.objects.get_or_create(
        customer_vehicle=cv1,
        service_appointment=sapt1,
        defaults={
            'service_advisor': user_priya,
            'floor_supervisor': user_rajan,
            'branch': branch1,
            'odometer_reading': 712,
            'problem_description': '1st free service: engine oil + filter change, chain lube, brake check, tyre pressure, nuts & bolts tightening',
            'service_status': 'ready',
        }
    )
    ok(f"1 JobCard created/verified: JC-{jc1.pk}")
except Exception as e:
    fail("JobCard", e)

try:
    ba1, _ = BayAssignment.objects.get_or_create(
        job_card=jc1,
        bay=bay1,
        defaults={
            'mechanic': user_rajan,
            'start_time': timezone.make_aware(timezone.datetime(2026, 1, 10, 9, 30)),
            'end_time': timezone.make_aware(timezone.datetime(2026, 1, 10, 12, 0)),
            'assignment_status': 'completed',
        }
    )
    ok(f"1 BayAssignment created/verified")
except Exception as e:
    fail("BayAssignment", e)

try:
    lc1, _ = LaborCharge.objects.get_or_create(
        job_card=jc1, service_name='Engine Oil Change',
        defaults={'labor_cost': Decimal('150.00')}
    )
    lc2, _ = LaborCharge.objects.get_or_create(
        job_card=jc1, service_name='Air Filter Cleaning',
        defaults={'labor_cost': Decimal('75.00')}
    )
    lc3, _ = LaborCharge.objects.get_or_create(
        job_card=jc1, service_name='Chain Lubrication & Adjustment',
        defaults={'labor_cost': Decimal('100.00')}
    )
    lc4, _ = LaborCharge.objects.get_or_create(
        job_card=jc1, service_name='General Inspection & Tightening',
        defaults={'labor_cost': Decimal('200.00')}
    )
    ok(f"4 LaborCharges created/verified — total Rs.525")
except Exception as e:
    fail("LaborCharges", e)

try:
    ow1, _ = OutworkEntry.objects.get_or_create(
        job_card=jc1,
        vendor_name='Coimbatore Wheel Alignment Centre',
        defaults={
            'work_description': 'Front wheel alignment and balancing',
            'cost': Decimal('350.00'),
            'status': 'returned',
        }
    )
    ok(f"1 OutworkEntry created/verified")
except Exception as e:
    fail("OutworkEntry", e)

try:
    sinv1, _ = ServiceInvoice.objects.get_or_create(
        job_card=jc1,
        defaults={
            'invoice_number': f'SINV-{date.today().year}-001',
            'discount_amount': Decimal('50.00'),
            'status': 'issued',
        }
    )
    sinv1.calculate_totals()
    sinv1.refresh_from_db()
    ok(f"1 ServiceInvoice created/verified — final Rs.{sinv1.final_amount}")
except Exception as e:
    fail("ServiceInvoice", e)

# ---------------------------------------------------------------------------
# STEP 10: Spares — Items, ItemRackBin, Quotes, PO, PI, StockLedger, Sales
# ---------------------------------------------------------------------------
section("STEP 10: Spares")

from spares.models import (
    SparesItem, ItemRackBin, StockLedger,
    SupplierQuote, SupplierQuoteItem,
    PurchaseOrder, PurchaseOrderItem,
    PurchaseInvoice, PurchaseInvoiceItem,
    CounterSale, CounterSaleItem,
    CounterSaleReturn, CounterSaleReturnItem,
    SparesIssueAlteration, SparesIssueAlterationItem,
)

try:
    stock_item1, _ = SparesItem.objects.get_or_create(
        item_name='Honda Shine Engine Oil 1L SAE 10W-30',
        defaults={
            'category': cat_engine,
            'item_sub_group': 'Engine Oils',
            'hsn_sac': '27101980',
            'uom': 'Nos',
            'part_number': 'OIL-SHINE-10W30',
            'brand': 'Honda Genuine',
            'description': 'Genuine Honda 4-stroke engine oil for Shine series',
            'maintain_stock': True,
            'allow_negative_stock': False,
            'opening_stock': Decimal('50.000'),
            'valuation_rate': Decimal('310.00'),
            'standard_selling_rate': Decimal('380.00'),
            'mrp': Decimal('400.00'),
            'max_discount': Decimal('5.00'),
            'sgst': Decimal('9.00'),
            'cgst': Decimal('9.00'),
            'reorder_level': Decimal('10.000'),
            'reorder_qty': Decimal('50.000'),
            'warranty_period_days': 0,
            'is_active': True,
            'created_by': user_meena,
        }
    )
    stock_item2, _ = SparesItem.objects.get_or_create(
        item_name='Honda Shine Air Filter Element',
        defaults={
            'category': cat_engine,
            'item_sub_group': 'Filters',
            'hsn_sac': '84212300',
            'uom': 'Nos',
            'part_number': 'AIR-FILT-SHINE-001',
            'brand': 'Honda Genuine',
            'description': 'OEM air filter for Honda Shine 125cc',
            'maintain_stock': True,
            'opening_stock': Decimal('25.000'),
            'valuation_rate': Decimal('180.00'),
            'standard_selling_rate': Decimal('230.00'),
            'mrp': Decimal('250.00'),
            'max_discount': Decimal('5.00'),
            'sgst': Decimal('9.00'),
            'cgst': Decimal('9.00'),
            'reorder_level': Decimal('5.000'),
            'reorder_qty': Decimal('20.000'),
            'is_active': True,
            'created_by': user_meena,
        }
    )
    stock_item3, _ = SparesItem.objects.get_or_create(
        item_name='Honda Spark Plug CPR8EA-9',
        defaults={
            'category': cat_elect,
            'item_sub_group': 'Ignition',
            'hsn_sac': '85111000',
            'uom': 'Nos',
            'part_number': 'PLUG-CPR8EA9',
            'brand': 'NGK',
            'description': 'NGK Spark Plug for Honda 125cc engines',
            'maintain_stock': True,
            'opening_stock': Decimal('30.000'),
            'valuation_rate': Decimal('95.00'),
            'standard_selling_rate': Decimal('130.00'),
            'mrp': Decimal('145.00'),
            'max_discount': Decimal('10.00'),
            'sgst': Decimal('9.00'),
            'cgst': Decimal('9.00'),
            'reorder_level': Decimal('8.000'),
            'reorder_qty': Decimal('30.000'),
            'is_active': True,
            'created_by': user_meena,
        }
    )
    stock_item4, _ = SparesItem.objects.get_or_create(
        item_name='Castrol Activ 4T 20W-40 1L',
        defaults={
            'category': cat_lubri,
            'item_sub_group': 'Engine Oils',
            'hsn_sac': '27101980',
            'uom': 'Nos',
            'part_number': 'CASTROL-ACTIV-20W40-1L',
            'brand': 'Castrol',
            'description': 'Castrol Activ 4T fully mineral oil for 4-stroke bikes',
            'maintain_stock': True,
            'opening_stock': Decimal('40.000'),
            'valuation_rate': Decimal('260.00'),
            'standard_selling_rate': Decimal('325.00'),
            'mrp': Decimal('345.00'),
            'max_discount': Decimal('5.00'),
            'sgst': Decimal('9.00'),
            'cgst': Decimal('9.00'),
            'reorder_level': Decimal('12.000'),
            'reorder_qty': Decimal('48.000'),
            'is_active': True,
            'created_by': user_meena,
        }
    )
    ok(f"4 SparesItems created/verified: {stock_item1.item_code}, {stock_item2.item_code}, {stock_item3.item_code}, {stock_item4.item_code}")
except Exception as e:
    fail("SparesItems", e)

try:
    irb1, _ = ItemRackBin.objects.get_or_create(
        item=stock_item1, rack=rack_a,
        defaults={'bin': bin_a1, 'is_active': True}
    )
    ok(f"1 ItemRackBin created/verified")
except Exception as e:
    fail("ItemRackBin", e)

# Supplier Quote
try:
    sq = SupplierQuote.objects.filter(supplier=sup1, quotation_number='HMSI-SQ-2025-4521').first()
    if not sq:
        sq = SupplierQuote.objects.create(
            supplier=sup1,
            date=date(2025, 11, 1),
            valid_till=date(2025, 12, 31),
            quotation_number='HMSI-SQ-2025-4521',
            status='submitted',
            total_quantity=Decimal('75.000'),
            total_amount=Decimal('27250.00'),
            grand_total=Decimal('27250.00'),
            terms_and_conditions='Payment within 30 days. Delivery ex-Depot Chennai.',
            created_by=user_meena,
        )
    ok(f"1 SupplierQuote created/verified: {sq.quote_no}")
except Exception as e:
    fail("SupplierQuote", e)

try:
    sqi1, _ = SupplierQuoteItem.objects.get_or_create(
        quote=sq, item=stock_item1,
        defaults={'quantity': Decimal('50.000'), 'uom': 'Nos', 'rate': Decimal('310.00')}
    )
    sqi2, _ = SupplierQuoteItem.objects.get_or_create(
        quote=sq, item=stock_item2,
        defaults={'quantity': Decimal('25.000'), 'uom': 'Nos', 'rate': Decimal('180.00')}
    )
    ok(f"2 SupplierQuoteItems created/verified")
except Exception as e:
    fail("SupplierQuoteItems", e)

# Purchase Order
try:
    po = PurchaseOrder.objects.filter(supplier=sup1, supplier_quote=sq).first()
    if not po:
        po = PurchaseOrder.objects.create(
            supplier=sup1,
            supplier_quote=sq,
            date=date(2025, 11, 5),
            required_by=date(2025, 11, 20),
            status='received',
            supplier_gstin='29AAACH0997E1ZL',
            gst_category='Regular',
            place_of_supply='Tamil Nadu',
            total_quantity=Decimal('75.000'),
            total_amount=Decimal('27250.00'),
            total_taxes=Decimal('4905.00'),
            grand_total=Decimal('32155.00'),
            terms_and_conditions='Deliver to Coimbatore depot.',
            created_by=user_meena,
        )
    ok(f"1 PurchaseOrder created/verified: {po.po_no}")
except Exception as e:
    fail("PurchaseOrder", e)

try:
    poi1, _ = PurchaseOrderItem.objects.get_or_create(
        order=po, item=stock_item1,
        defaults={
            'warehouse': wh_main,
            'quantity': Decimal('50.000'),
            'uom': 'Nos',
            'rate': Decimal('310.00'),
            'received_qty': Decimal('50.000'),
        }
    )
    poi2, _ = PurchaseOrderItem.objects.get_or_create(
        order=po, item=stock_item2,
        defaults={
            'warehouse': wh_main,
            'quantity': Decimal('25.000'),
            'uom': 'Nos',
            'rate': Decimal('180.00'),
            'received_qty': Decimal('25.000'),
        }
    )
    ok(f"2 PurchaseOrderItems created/verified")
except Exception as e:
    fail("PurchaseOrderItems", e)

# Purchase Invoice
try:
    pi = PurchaseInvoice.objects.filter(supplier=sup1, purchase_order=po).first()
    if not pi:
        pi = PurchaseInvoice.objects.create(
            supplier=sup1,
            purchase_order=po,
            date=date(2025, 11, 20),
            due_date=date(2025, 12, 20),
            status='submitted',
            supplier_gstin='29AAACH0997E1ZL',
            gst_category='Regular',
            place_of_supply='Tamil Nadu',
            total_quantity=Decimal('75.000'),
            total_amount=Decimal('27250.00'),
            total_sgst=Decimal('2452.50'),
            total_cgst=Decimal('2452.50'),
            total_taxes=Decimal('4905.00'),
            grand_total=Decimal('32155.00'),
            payment_status='Unpaid',
            remarks='HMSI Invoice #HMSI-2025-11-4521',
            created_by=user_meena,
        )
    ok(f"1 PurchaseInvoice created/verified: {pi.invoice_no}")
except Exception as e:
    fail("PurchaseInvoice", e)

try:
    pii1, _ = PurchaseInvoiceItem.objects.get_or_create(
        invoice=pi, item=stock_item1,
        defaults={
            'warehouse': wh_main,
            'rack': rack_a,
            'bin': bin_a1,
            'quantity': Decimal('50.000'),
            'uom': 'Nos',
            'rate': Decimal('310.00'),
            'sgst': Decimal('9.00'),
            'cgst': Decimal('9.00'),
        }
    )
    pii2, _ = PurchaseInvoiceItem.objects.get_or_create(
        invoice=pi, item=stock_item2,
        defaults={
            'warehouse': wh_main,
            'rack': rack_a,
            'bin': bin_a2,
            'quantity': Decimal('25.000'),
            'uom': 'Nos',
            'rate': Decimal('180.00'),
            'sgst': Decimal('9.00'),
            'cgst': Decimal('9.00'),
        }
    )
    ok(f"2 PurchaseInvoiceItems created/verified")
except Exception as e:
    fail("PurchaseInvoiceItems", e)

# Stock Ledger — manually update since view logic won't run in script
try:
    sl1, created = StockLedger.objects.get_or_create(
        item=stock_item1, warehouse=wh_main, rack=rack_a, bin=bin_a1,
        defaults={'quantity': Decimal('50.000')}
    )
    if not created and sl1.quantity == 0:
        sl1.quantity = Decimal('50.000')
        sl1.save()

    sl2, created = StockLedger.objects.get_or_create(
        item=stock_item2, warehouse=wh_main, rack=rack_a, bin=bin_a2,
        defaults={'quantity': Decimal('25.000')}
    )
    if not created and sl2.quantity == 0:
        sl2.quantity = Decimal('25.000')
        sl2.save()

    sl1.refresh_from_db()
    if sl1.quantity > 0:
        ok(f"StockLedger verified: {stock_item1.item_code} qty={sl1.quantity}")
    else:
        fail(f"StockLedger quantity is 0 for {stock_item1.item_code}")
except Exception as e:
    fail("StockLedger", e)

# Counter Sale
try:
    cs = CounterSale.objects.filter(mobile='9876500001').first()
    if not cs:
        cs = CounterSale.objects.create(
            customer='Rajesh Selvakumar',
            mobile='9876500001',
            gst_category='Regular',
            godown=wh_main,
            date=date.today(),
            is_warranty=False,
            status='submitted',
            total_qty=Decimal('3.000'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('1495.00'),
            payment_status='Paid',
            pay_type='upi',
            created_by=user_meena,
        )
    ok(f"1 CounterSale created/verified: {cs.sale_no}")
except Exception as e:
    fail("CounterSale", e)

try:
    csi1, _ = CounterSaleItem.objects.get_or_create(
        sale=cs, item=stock_item1,
        defaults={
            'rack': rack_a,
            'bin': bin_a1,
            'quantity': Decimal('2.000'),
            'rate': Decimal('380.00'),
            'gst_percent': Decimal('18.00'),
        }
    )
    csi2, _ = CounterSaleItem.objects.get_or_create(
        sale=cs, item=stock_item3,
        defaults={
            'rack': rack_a,
            'bin': bin_a1,
            'quantity': Decimal('1.000'),
            'rate': Decimal('130.00'),
            'gst_percent': Decimal('18.00'),
        }
    )
    ok(f"2 CounterSaleItems created/verified")
except Exception as e:
    fail("CounterSaleItems", e)

# Counter Sale Return
try:
    csr = CounterSaleReturn.objects.filter(original_sale=cs).first()
    if not csr:
        csr = CounterSaleReturn.objects.create(
            original_sale=cs,
            return_date=date.today(),
            reason='Customer purchased wrong model oil by mistake',
            stock_return_done=True,
            amount_refund_done=True,
            total_amount=Decimal('447.40'),
            created_by=user_meena,
        )
    ok(f"1 CounterSaleReturn created/verified: {csr.return_no}")
except Exception as e:
    fail("CounterSaleReturn", e)

try:
    csri1, _ = CounterSaleReturnItem.objects.get_or_create(
        sale_return=csr, item=stock_item1,
        defaults={
            'quantity': Decimal('1.000'),
            'rate': Decimal('380.00'),
        }
    )
    ok(f"1 CounterSaleReturnItem created/verified")
except Exception as e:
    fail("CounterSaleReturnItem", e)

# Spares Issue Alteration
try:
    sia = SparesIssueAlteration.objects.filter(job_card=str(jc1.pk)).first()
    if not sia:
        sia = SparesIssueAlteration.objects.create(
            job_card=str(jc1.pk),
            godown=wh_service,
            job_type='service',
            date=date.today(),
            spares_total=Decimal('760.00'),
            labour_total=Decimal('525.00'),
            outwork_total=Decimal('350.00'),
            total=Decimal('1635.00'),
            discount=Decimal('50.00'),
            updated_total=Decimal('1585.00'),
            created_by=user_priya,
        )
    ok(f"1 SparesIssueAlteration created/verified: SIA-{sia.pk:05d}")
except Exception as e:
    fail("SparesIssueAlteration", e)

try:
    siai1, _ = SparesIssueAlterationItem.objects.get_or_create(
        alteration=sia, item=stock_item1,
        defaults={
            'quantity': Decimal('2.000'),
            'rack': rack_s,
            'bin': bin_s1,
            'rate': Decimal('310.00'),
            'discount_percent': Decimal('0.00'),
        }
    )
    siai2, _ = SparesIssueAlterationItem.objects.get_or_create(
        alteration=sia, item=stock_item2,
        defaults={
            'quantity': Decimal('1.000'),
            'rack': rack_s,
            'bin': bin_s1,
            'rate': Decimal('140.00'),
            'discount_percent': Decimal('0.00'),
        }
    )
    ok(f"2 SparesIssueAlterationItems created/verified")
except Exception as e:
    fail("SparesIssueAlterationItems", e)

# ---------------------------------------------------------------------------
# STEP 11: Cross-app relationship verification
# ---------------------------------------------------------------------------
section("STEP 11: Cross-App Relationship Verification")

checks = [
    ("cust1.enquiries count",        cust1.enquiries.count() >= 1),
    ("enq1.orders count",            enq1.orders.count() >= 1),
    ("order1.invoice exists",        hasattr(order1, 'invoice') and Invoice.objects.filter(sales_order=order1).exists()),
    ("order1.loan exists",           FinanceLoan.objects.filter(sales_order=order2).exists()),
    ("order1.rto_registration",      RTORegistration.objects.filter(sales_order=order1).exists()),
    ("rto1.number_plate_order",      NumberPlateOrder.objects.filter(rto=rto1).exists()),
    ("cv1.amc_packages",             cv1.amc_packages.count() >= 1),
    ("cv1.rsa_packages",             cv1.rsa_packages.count() >= 1),
    ("cv1.protection_plus_packages", cv1.protection_plus_packages.count() >= 1),
    ("cv1.service_enquiries",        cv1.service_enquiries.count() >= 1),
    ("jc1.labor_charges count",      jc1.labor_charges.count() == 4),
    ("jc1.outwork_entries count",    jc1.outwork_entries.count() >= 1),
    ("jc1 service_invoice exists",   ServiceInvoice.objects.filter(job_card=jc1).exists()),
    ("sinv1.final_amount > 0",       sinv1.final_amount > 0),
    ("sq has items",                 sq.items.count() == 2),
    ("po has items",                 po.items.count() == 2),
    ("pi has items",                 pi.items.count() == 2),
    ("pii1.sgst_amount > 0",         pii1.sgst_amount > 0),
    ("pii1.total > 0",               pii1.total > 0),
    ("cs has items",                 cs.items.count() == 2),
    ("csr has items",                csr.items.count() == 1),
    ("sia has items",                sia.items.count() == 2),
    ("stock_item1 in StockLedger",   StockLedger.objects.filter(item=stock_item1).exists()),
    ("sl1.quantity > 0",             sl1.quantity > 0),
    ("cv2 insurance expiry < 30d",   cv2.insurance_expiry <= date.today() + timedelta(days=30)),
    ("enq3 follow_up status",        enq3.status == 'follow_up'),
]

for label, condition in checks:
    if condition:
        ok(label)
    else:
        fail(label)

# ---------------------------------------------------------------------------
# STEP 12: Data summary
# ---------------------------------------------------------------------------
section("STEP 12: Data Summary")

from accounts.models import AuditLog
from django.contrib.contenttypes.models import ContentType

summary_rows = [
    ("Roles",                    Role.objects.count()),
    ("Branches",                 Branch.objects.count()),
    ("Users",                    User.objects.count()),
    ("SparesCategories",         SparesCategory.objects.count()),
    ("Suppliers",                Supplier.objects.count()),
    ("Warehouses",               Warehouse.objects.count()),
    ("Racks",                    Rack.objects.count()),
    ("Bins",                     Bin.objects.count()),
    ("Customers",                Customer.objects.count()),
    ("BikeModels",               BikeModel.objects.count()),
    ("VehicleStock",             VehicleStock.objects.count()),
    ("SalesEnquiries",           SalesEnquiry.objects.count()),
    ("SalesAppointments",        SalesAppointment.objects.count()),
    ("SalesFeedback",            SalesFeedback.objects.count()),
    ("VehicleSalesOrders",       VehicleSalesOrder.objects.count()),
    ("ExchangeVehicles",         ExchangeVehicle.objects.count()),
    ("CustomerVehicles",         CustomerVehicle.objects.count()),
    ("Invoices",                 Invoice.objects.count()),
    ("Payments",                 Payment.objects.count()),
    ("FinanceLoans",             FinanceLoan.objects.count()),
    ("InsurancePolicies",        InsurancePolicy.objects.count()),
    ("RTORegistrations",         RTORegistration.objects.count()),
    ("NumberPlateOrders",        NumberPlateOrder.objects.count()),
    ("AMCPackages",              AMCPackage.objects.count()),
    ("RSAPackages",              RSAPackage.objects.count()),
    ("ProtectionPlusPackages",   ProtectionPlusPackage.objects.count()),
    ("ServiceEnquiries",         ServiceEnquiry.objects.count()),
    ("ServiceAppointments",      ServiceAppointment.objects.count()),
    ("JobCards",                 JobCard.objects.count()),
    ("ServiceBays",              ServiceBay.objects.count()),
    ("BayAssignments",           BayAssignment.objects.count()),
    ("LaborCharges",             LaborCharge.objects.count()),
    ("OutworkEntries",           OutworkEntry.objects.count()),
    ("ServiceInvoices",          ServiceInvoice.objects.count()),
    ("SparesItems",              SparesItem.objects.count()),
    ("ItemRackBins",             ItemRackBin.objects.count()),
    ("StockLedger entries",      StockLedger.objects.count()),
    ("SupplierQuotes",           SupplierQuote.objects.count()),
    ("SupplierQuoteItems",       SupplierQuoteItem.objects.count()),
    ("PurchaseOrders",           PurchaseOrder.objects.count()),
    ("PurchaseOrderItems",       PurchaseOrderItem.objects.count()),
    ("PurchaseInvoices",         PurchaseInvoice.objects.count()),
    ("PurchaseInvoiceItems",     PurchaseInvoiceItem.objects.count()),
    ("CounterSales",             CounterSale.objects.count()),
    ("CounterSaleItems",         CounterSaleItem.objects.count()),
    ("CounterSaleReturns",       CounterSaleReturn.objects.count()),
    ("CounterSaleReturnItems",   CounterSaleReturnItem.objects.count()),
    ("SparesIssueAlterations",   SparesIssueAlteration.objects.count()),
    ("SparesIssueAlterationItems", SparesIssueAlterationItem.objects.count()),
]

print(f"\n{'Model':<35} {'Count':>6}")
print(f"{'-'*35} {'-'*6}")
for model_name, count in summary_rows:
    print(f"  {model_name:<33} {count:>6}")

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"  FINAL RESULT: {PASS} PASS  |  {FAIL} FAIL")
print(f"{'='*60}")

if FAIL == 0:
    print("  All checks passed. Demo data is ready!")
else:
    print(f"  {FAIL} check(s) failed — review output above.")

sys.exit(0 if FAIL == 0 else 1)
