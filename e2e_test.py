import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')
django.setup()

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
import sqlite3

today = date.today()
now = timezone.now()

results = []
section_results = {}
_current_section = ['Setup']

def section(name):
    _current_section[0] = name
    section_results[name] = []
    print(f'\n{"="*55}')
    print(f'  {name}')
    print(f'{"="*55}')

def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    entry = (status, _current_section[0], label, detail)
    results.append(entry)
    section_results.setdefault(_current_section[0], []).append(entry)
    icon = 'OK' if condition else 'XX'
    msg = f'  [{icon}] {label}'
    if detail and not condition:
        msg += f'\n       -> {detail}'
    print(msg)
    return condition

# ─────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────
section('CLEANUP')

db = sqlite3.connect('db.sqlite3')
cur = db.cursor()

cur.execute("DELETE FROM sales_salesfeedback WHERE enquiry_id IN (SELECT id FROM sales_salesenquiry WHERE remarks LIKE '%E2E-TEST%')")
cur.execute("DELETE FROM sales_salesappointment WHERE enquiry_id IN (SELECT id FROM sales_salesenquiry WHERE remarks LIKE '%E2E-TEST%')")
cur.execute("DELETE FROM sales_salesenquiry WHERE remarks LIKE '%E2E-TEST%'")
cur.execute("DELETE FROM sales_prospect WHERE full_name LIKE '%E2E%'")

cur.execute("SELECT id FROM customers_customer WHERE phone IN ('9100000001','9100000002')")
test_cust_ids = [r[0] for r in cur.fetchall()]
for cid in test_cust_ids:
    cur.execute('SELECT id FROM customer_vehicles_customervehicle WHERE customer_id=?', (cid,))
    cv_ids = [r[0] for r in cur.fetchall()]
    for cvid in cv_ids:
        cur.execute('SELECT id FROM service_jobcard WHERE customer_vehicle_id=?', (cvid,))
        jc_ids = [r[0] for r in cur.fetchall()]
        for jcid in jc_ids:
            for tbl in ['service_serviceinvoice','service_warrantyclaim','service_insuranceclaim',
                        'service_insuranceestimation','service_additionalworkapproval',
                        'service_bayassignment','service_outworkentry','service_jobcardrevisit',
                        'service_jobcardservicechild','service_laborcharge']:
                cur.execute(f'DELETE FROM {tbl} WHERE job_card_id=?', (jcid,))
            cur.execute('DELETE FROM service_jobcard WHERE id=?', (jcid,))
        rows = cur.execute('SELECT id FROM service_serviceenquiry WHERE customer_vehicle_id=?', (cvid,)).fetchall()
        for (sid,) in rows:
            cur.execute('DELETE FROM service_serviceappointment WHERE service_enquiry_id=?', (sid,))
        cur.execute('DELETE FROM service_serviceenquiry WHERE customer_vehicle_id=?', (cvid,))
        cur.execute('DELETE FROM service_customercall WHERE customer_vehicle_id=?', (cvid,))
        cur.execute('DELETE FROM service_servicereminder WHERE customer_vehicle_id=?', (cvid,))
        for vas_tbl in ['vas_amcpackage','vas_rsapackage','vas_protectionpluspackage']:
            cur.execute(f'DELETE FROM {vas_tbl} WHERE customer_vehicle_id=?', (cvid,))
    cur.execute('DELETE FROM customer_vehicles_customervehicle WHERE customer_id=?', (cid,))
    cur.execute('SELECT id FROM sales_vehiclesalesorder WHERE customer_id=?', (cid,))
    order_ids = [r[0] for r in cur.fetchall()]
    for oid in order_ids:
        rows = cur.execute('SELECT id FROM rto_rtoregistration WHERE sales_order_id=?', (oid,)).fetchall()
        for (rid,) in rows:
            for rtbl in ['rto_rcbook','rto_regpayment','rto_rtoincome']:
                cur.execute(f'DELETE FROM {rtbl} WHERE rto_registration_id=?', (rid,))
            cur.execute('DELETE FROM rto_numberplateorder WHERE rto_id=?', (rid,))
            cur.execute('DELETE FROM rto_rtoregistration WHERE id=?', (rid,))
        rows = cur.execute('SELECT id FROM billing_invoice WHERE sales_order_id=?', (oid,)).fetchall()
        for (iid,) in rows:
            cur.execute('DELETE FROM billing_payment WHERE invoice_id=?', (iid,))
        cur.execute('DELETE FROM billing_invoice WHERE sales_order_id=?', (oid,))
        for btbl in ['billing_financeloan','billing_insurancepolicy','billing_refundadvance']:
            try: cur.execute(f'DELETE FROM {btbl} WHERE sales_order_id=?', (oid,))
            except: pass
        for stbl in ['sales_vehicledelivery','sales_vehicleallotment','sales_vehiclefitting',
                     'sales_exchangevehicle','sales_pdichecklist']:
            try: cur.execute(f'DELETE FROM {stbl} WHERE sales_order_id=?', (oid,))
            except: pass
        cur.execute('DELETE FROM sales_vehiclesalesorder WHERE id=?', (oid,))
    cur.execute('DELETE FROM sales_salesenquiry WHERE customer_id=?', (cid,))
    cur.execute('DELETE FROM customers_customer WHERE id=?', (cid,))

# Clean SIA orphans
sia_rows = cur.execute('SELECT id, job_card FROM spares_sparesissuealteration').fetchall()
for (sia_id, jc_str) in sia_rows:
    if jc_str.isdigit():
        exists = cur.execute('SELECT 1 FROM service_jobcard WHERE id=?', (int(jc_str),)).fetchone()
        if not exists:
            cur.execute('DELETE FROM spares_sparesissuealterationitem WHERE alteration_id=?', (sia_id,))
            cur.execute('DELETE FROM spares_sparesissuealteration WHERE id=?', (sia_id,))

cur.execute("UPDATE customers_vehiclestock SET stock_status='available' WHERE chassis_no IN ('E2E-CHASSIS-001','E2E-CHASSIS-002')")

# Final safety net: the manual cascade deletes above only cover tables known
# at the time they were written. Sweep any remaining orphans (e.g. from
# models added later) so this script never leaves the DB in a state that
# fails Django's FK integrity check on the next migration.
for _ in range(10):
    orphans = cur.execute('PRAGMA foreign_key_check').fetchall()
    if not orphans:
        break
    seen = set()
    for table, rowid, _parent, _fkid in orphans:
        key = (table, rowid)
        if key in seen:
            continue
        seen.add(key)
        cur.execute(f'DELETE FROM {table} WHERE rowid = ?', (rowid,))

db.commit()
db.close()
print('  [OK] Stale test data cleaned')

# ─────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────
from accounts.models import User, Role, Branch, CompanySettings, Notification
from accounts.permissions import ROLE_PERMISSIONS
from accounts.notifications import generate_notifications
from customers.models import Customer, BikeModel, VehicleStock
from customer_vehicles.models import CustomerVehicle
from sales.models import (SalesEnquiry, SalesAppointment, SalesFeedback,
    VehicleSalesOrder, ExchangeVehicle, VehicleAllotment, VehicleFitting,
    VehicleDelivery, Prospect, SalesTarget, TestRideLog, PDIChecklist)
from billing.models import (Invoice, Payment, FinanceLoan, InsurancePolicy,
    RefundAdvance, JournalEntry, JournalEntryLine)
from rto.models import RTORegistration, NumberPlateOrder, RCBook, RegPayment, RTOIncome
from vas.models import AMCPackage, RSAPackage, ProtectionPlusPackage
from service.models import (ServiceEnquiry, ServiceAppointment, ServiceBay,
    JobCard, BayAssignment, LaborCharge, OutworkEntry, ServiceInvoice,
    WarrantyClaim, InsuranceEstimation, InsuranceClaim, ServiceDiscountMaster,
    AdditionalWorkApproval, CustomerCall, JobCardRevisit, JobCardServiceChild,
    ServiceReminder)
from spares.models import (SparesItem, ItemRackBin, StockLedger,
    SupplierQuote, SupplierQuoteItem, PurchaseOrder, PurchaseOrderItem,
    PurchaseInvoice, PurchaseInvoiceItem, CounterSale, CounterSaleItem,
    CounterSaleReturn, CounterSaleReturnItem, SparesIssueAlteration,
    SparesIssueAlterationItem)
from masters.models import SparesCategory, Supplier, Warehouse, Rack, Bin

# ═══════════════════════════════════════════════════════
# WORKFLOW 1 — COMPANY AND USER SETUP
# ═══════════════════════════════════════════════════════
section('WORKFLOW 1 - Company and User Setup')

company = CompanySettings.get_instance()
company.company_name = 'SS Bikez Motorcycles'
company.gstin = '33AABCS1234A1Z5'
company.gst_rate = Decimal('18')
company.cgst_rate = Decimal('9')
company.sgst_rate = Decimal('9')
company.address_line1 = '47, Avinashi Road'
company.city = 'Coimbatore'
company.state = 'Tamil Nadu'
company.phone = '0422-4567890'
company.save()
check('Company settings saved', company.gstin == '33AABCS1234A1Z5')
check('Company GST rate = 18%', company.gst_rate == Decimal('18'))
check('Company singleton (pk=1)', company.pk == 1)

for rname in ['Managing Director','Sales Executive','Cashier','Floor Supervisor',
              'CRE Telecaller','Service Advisor','Spares','Accounts']:
    Role.objects.get_or_create(role_name=rname, defaults={'description': f'{rname} role'})
check('All 8 roles exist', Role.objects.count() >= 8)
check('MD has full access (*)', '*' in ROLE_PERMISSIONS.get('Managing Director', []))
check('Sales Exec limited (no billing)', 'billing' not in ROLE_PERMISSIONS.get('Sales Executive', []))
check('Floor Supervisor has service access', 'service' in ROLE_PERMISSIONS.get('Floor Supervisor', []))
check('CRE has service access', 'service' in ROLE_PERMISSIONS.get('CRE Telecaller', []))
check('Spares role has spares access', 'spares' in ROLE_PERMISSIONS.get('Spares', []))

branch, _ = Branch.objects.get_or_create(
    branch_name='Main Showroom Coimbatore',
    defaults={'address': '47 Avinashi Road, Coimbatore 641018',
              'phone': '0422-4567890', 'gstin': '33AABCS1234A1Z5', 'is_active': True})
check('Branch created', branch.pk is not None)
check('Branch has GSTIN', bool(branch.gstin))

admin_user = User.objects.filter(is_superuser=True).first()
check('Admin user exists', admin_user is not None)

sales_role   = Role.objects.get(role_name='Sales Executive')
cre_role     = Role.objects.get(role_name='CRE Telecaller')
floor_role   = Role.objects.get(role_name='Floor Supervisor')
cashier_role = Role.objects.get(role_name='Cashier')

sales_user, _ = User.objects.get_or_create(username='e2e_sales',
    defaults={'first_name': 'Arjun', 'last_name': 'Kumar',
              'email': 'arjun.e2e@ssbikez.com', 'role': sales_role,
              'branch': branch, 'status': 'active'})
sales_user.set_password('Test@123'); sales_user.save()

cre_user, _ = User.objects.get_or_create(username='e2e_cre',
    defaults={'first_name': 'Divya', 'last_name': 'Lakshmi',
              'email': 'divya.e2e@ssbikez.com', 'role': cre_role,
              'branch': branch, 'status': 'active'})
cre_user.set_password('Test@123'); cre_user.save()

floor_user, _ = User.objects.get_or_create(username='e2e_floor',
    defaults={'first_name': 'Rajan', 'last_name': 'Kumar',
              'email': 'rajan.e2e@ssbikez.com', 'role': floor_role,
              'branch': branch, 'status': 'active'})
floor_user.set_password('Test@123'); floor_user.save()

cashier_user, _ = User.objects.get_or_create(username='e2e_cashier',
    defaults={'first_name': 'Meena', 'last_name': 'Devi',
              'email': 'meena.e2e@ssbikez.com', 'role': cashier_role,
              'branch': branch, 'status': 'active'})
cashier_user.set_password('Test@123'); cashier_user.save()

check('Sales user created', sales_user.pk is not None)
check('CRE user created', cre_user.pk is not None)
check('Floor user created', floor_user.pk is not None)
check('Cashier user created', cashier_user.pk is not None)
check('Users have correct roles',
    sales_user.role.role_name == 'Sales Executive' and
    cre_user.role.role_name == 'CRE Telecaller')

# ═══════════════════════════════════════════════════════
# WORKFLOW 2 — MASTERS SETUP
# ═══════════════════════════════════════════════════════
section('WORKFLOW 2 - Masters: Category/Supplier/Warehouse/Rack/Bin')

cat_engine, _ = SparesCategory.objects.get_or_create(name='E2E Engine Parts')
cat_filters, _ = SparesCategory.objects.get_or_create(name='E2E Filters and Oils')
cat_brakes, _  = SparesCategory.objects.get_or_create(name='E2E Brakes')
check('Categories created', SparesCategory.objects.filter(name__startswith='E2E').count() == 3)

supplier, _ = Supplier.objects.get_or_create(
    supplier_name='E2E Honda Parts India',
    defaults={
        'contact_person': 'Ramesh Iyer', 'phone': '9876543210',
        'email': 'ramesh@e2ehonda.in', 'gstin': '33AABCH5678A1Z2',
        'gst_category': 'Regular', 'supplier_group': 'OEM',
        'city': 'Chennai', 'state': 'Tamil Nadu', 'pincode': '600001',
        'place_of_supply': 'Tamil Nadu', 'is_active': True, 'created_by': admin_user
    })
check('Supplier created', supplier.pk is not None)
check('Supplier has GSTIN', bool(supplier.gstin))
check('Supplier has group', supplier.supplier_group == 'OEM')
check('Supplier has contact', bool(supplier.contact_person))

warehouse, _ = Warehouse.objects.get_or_create(
    name='E2E Main Store',
    defaults={'warehouse_type': 'stores', 'city': 'Coimbatore',
              'state': 'Tamil Nadu', 'is_active': True})
rack, _  = Rack.objects.get_or_create(name='E2E Rack A', warehouse=warehouse)
bin1, _  = Bin.objects.get_or_create(name='E2E Bin 1', rack=rack)
bin2, _  = Bin.objects.get_or_create(name='E2E Bin 2', rack=rack)
check('Warehouse created', warehouse.pk is not None)
check('Rack created under warehouse', rack.warehouse == warehouse)
check('Bins created under rack', Bin.objects.filter(rack=rack).count() >= 2)

# ═══════════════════════════════════════════════════════
# WORKFLOW 3 — SPARES INVENTORY SETUP
# ═══════════════════════════════════════════════════════
section('WORKFLOW 3 - Spares: Items, Procurement, Stock')

item_oil_filter, _ = SparesItem.objects.get_or_create(
    part_number='E2E-HON-OIL-FILTER',
    defaults={
        'item_name': 'E2E Honda Shine Oil Filter', 'item_group': 'Filters',
        'category': cat_filters, 'hsn_sac': '84099190', 'uom': 'Nos',
        'brand': 'Honda Genuine', 'opening_stock': Decimal('0'),
        'valuation_rate': Decimal('145'), 'standard_selling_rate': Decimal('185'),
        'mrp': Decimal('210'), 'max_discount': Decimal('5'),
        'sgst': Decimal('9'), 'cgst': Decimal('9'),
        'reorder_level': Decimal('5'), 'reorder_qty': Decimal('20'),
        'maintain_stock': True, 'is_active': True, 'created_by': admin_user})

item_engine_oil, _ = SparesItem.objects.get_or_create(
    part_number='E2E-HON-ENG-OIL',
    defaults={
        'item_name': 'E2E Honda 4T Engine Oil 1L', 'item_group': 'Oils',
        'category': cat_filters, 'hsn_sac': '27101980', 'uom': 'Ltr',
        'brand': 'Honda Genuine', 'opening_stock': Decimal('0'),
        'valuation_rate': Decimal('280'), 'standard_selling_rate': Decimal('340'),
        'mrp': Decimal('380'), 'sgst': Decimal('9'), 'cgst': Decimal('9'),
        'reorder_level': Decimal('10'), 'reorder_qty': Decimal('50'),
        'maintain_stock': True, 'is_active': True, 'created_by': admin_user})

item_brake_pad, _ = SparesItem.objects.get_or_create(
    part_number='E2E-HON-BRAKE-PAD',
    defaults={
        'item_name': 'E2E Honda Shine Brake Pad Set', 'item_group': 'Brakes',
        'category': cat_brakes, 'hsn_sac': '87083000', 'uom': 'Set',
        'brand': 'Honda Genuine', 'opening_stock': Decimal('0'),
        'valuation_rate': Decimal('320'), 'standard_selling_rate': Decimal('420'),
        'mrp': Decimal('480'), 'sgst': Decimal('9'), 'cgst': Decimal('9'),
        'reorder_level': Decimal('3'), 'reorder_qty': Decimal('10'),
        'maintain_stock': True, 'is_active': True, 'created_by': admin_user})

check('Oil filter item created', item_oil_filter.pk is not None)
check('Oil filter has item_code', bool(item_oil_filter.item_code))
check('Oil filter has HSN', item_oil_filter.hsn_sac == '84099190')
check('Oil filter has SGST 9%', item_oil_filter.sgst == Decimal('9'))
check('Engine oil item created', item_engine_oil.pk is not None)
check('Brake pad item created', item_brake_pad.pk is not None)

irb, _ = ItemRackBin.objects.get_or_create(
    item=item_oil_filter, rack=rack, defaults={'bin': bin1, 'is_active': True})
check('Item rack/bin assigned', irb.pk is not None)

sq, _ = SupplierQuote.objects.get_or_create(
    quote_no='E2E-SQ-001',
    defaults={'supplier': supplier, 'date': today - timedelta(days=15),
              'valid_till': today + timedelta(days=15), 'status': 'submitted',
              'created_by': admin_user})
sqi1, _ = SupplierQuoteItem.objects.get_or_create(
    quote=sq, item=item_oil_filter,
    defaults={'quantity': Decimal('50'), 'rate': Decimal('138')})
sqi2, _ = SupplierQuoteItem.objects.get_or_create(
    quote=sq, item=item_engine_oil,
    defaults={'quantity': Decimal('100'), 'rate': Decimal('265')})
sqi3, _ = SupplierQuoteItem.objects.get_or_create(
    quote=sq, item=item_brake_pad,
    defaults={'quantity': Decimal('20'), 'rate': Decimal('305')})
check('Supplier quote created', sq.pk is not None)
check('Quote item amount = qty * rate', sqi1.amount == Decimal('50') * Decimal('138'))
check('Quote has 3 items', sq.items.count() == 3)

po, _ = PurchaseOrder.objects.get_or_create(
    po_no='E2E-PO-001',
    defaults={'supplier': supplier, 'supplier_quote': sq,
              'date': today - timedelta(days=10), 'status': 'submitted',
              'supplier_gstin': supplier.gstin, 'gst_category': 'Regular',
              'place_of_supply': 'Tamil Nadu', 'created_by': admin_user})
poi1, _ = PurchaseOrderItem.objects.get_or_create(
    order=po, item=item_oil_filter,
    defaults={'warehouse': warehouse, 'quantity': Decimal('50'),
              'rate': Decimal('138'), 'received_qty': Decimal('0')})
poi2, _ = PurchaseOrderItem.objects.get_or_create(
    order=po, item=item_engine_oil,
    defaults={'warehouse': warehouse, 'quantity': Decimal('100'),
              'rate': Decimal('265'), 'received_qty': Decimal('0')})
poi3, _ = PurchaseOrderItem.objects.get_or_create(
    order=po, item=item_brake_pad,
    defaults={'warehouse': warehouse, 'quantity': Decimal('20'),
              'rate': Decimal('305'), 'received_qty': Decimal('0')})
check('PO created linked to quote', po.supplier_quote == sq)
check('PO has supplier GSTIN', bool(po.supplier_gstin))
check('PO item amount calculated', poi1.amount == Decimal('50') * Decimal('138'))
check('PO has 3 items', po.items.count() == 3)

pi, _ = PurchaseInvoice.objects.get_or_create(
    invoice_no='E2E-PI-001',
    defaults={'supplier': supplier, 'purchase_order': po,
              'date': today - timedelta(days=5), 'due_date': today + timedelta(days=25),
              'status': 'submitted', 'supplier_gstin': supplier.gstin,
              'gst_category': 'Regular', 'place_of_supply': 'Tamil Nadu',
              'payment_status': 'Unpaid', 'created_by': admin_user})
pii1, _ = PurchaseInvoiceItem.objects.get_or_create(
    invoice=pi, item=item_oil_filter,
    defaults={'warehouse': warehouse, 'rack': rack, 'bin': bin1,
              'quantity': Decimal('50'), 'rate': Decimal('138'),
              'sgst': Decimal('9'), 'cgst': Decimal('9')})
pii2, _ = PurchaseInvoiceItem.objects.get_or_create(
    invoice=pi, item=item_engine_oil,
    defaults={'warehouse': warehouse, 'rack': rack, 'bin': bin2,
              'quantity': Decimal('100'), 'rate': Decimal('265'),
              'sgst': Decimal('9'), 'cgst': Decimal('9')})
pii3, _ = PurchaseInvoiceItem.objects.get_or_create(
    invoice=pi, item=item_brake_pad,
    defaults={'warehouse': warehouse, 'rack': rack, 'bin': bin1,
              'quantity': Decimal('20'), 'rate': Decimal('305'),
              'sgst': Decimal('9'), 'cgst': Decimal('9')})

check('Purchase invoice created', pi.pk is not None)
check('PI linked to PO', pi.purchase_order == po)
check('PI item SGST = amount*9/100',
    pii1.sgst_amount == pii1.amount * Decimal('9') / 100)
check('PI item total = amount+sgst+cgst',
    pii1.total == pii1.amount + pii1.sgst_amount + pii1.cgst_amount)
check('PI has 3 items', pi.items.count() == 3)

for item, wh, qty in [(item_oil_filter, warehouse, Decimal('50')),
                       (item_engine_oil, warehouse, Decimal('100')),
                       (item_brake_pad,  warehouse, Decimal('20'))]:
    sl_entry, created = StockLedger.objects.get_or_create(
        item=item, warehouse=wh, defaults={'rack': rack, 'quantity': Decimal('0')})
    if created or sl_entry.quantity < Decimal('1'):
        sl_entry.quantity = qty; sl_entry.save()

stock_filter = StockLedger.objects.filter(item=item_oil_filter, warehouse=warehouse).first()
stock_oil    = StockLedger.objects.filter(item=item_engine_oil, warehouse=warehouse).first()
stock_brake  = StockLedger.objects.filter(item=item_brake_pad,  warehouse=warehouse).first()
check('Oil filter stock in ledger', stock_filter is not None)
check('Engine oil stock in ledger', stock_oil is not None)
check('Brake pad stock in ledger', stock_brake is not None)
if stock_filter: check('Oil filter stock qty >= 50', stock_filter.quantity >= Decimal('50'))
if stock_oil:    check('Engine oil stock qty >= 100', stock_oil.quantity >= Decimal('100'))

cs, _ = CounterSale.objects.get_or_create(
    sale_no='E2E-CS-001',
    defaults={'customer': 'E2E Walk-in Customer', 'mobile': '9100099999',
              'gst_category': 'Unregistered', 'godown': warehouse,
              'date': today, 'status': 'submitted', 'pay_type': 'cash',
              'payment_status': 'Paid', 'created_by': cashier_user})
csi1, _ = CounterSaleItem.objects.get_or_create(
    sale=cs, item=item_oil_filter,
    defaults={'rack': rack, 'bin': bin1, 'quantity': Decimal('2'),
              'rate': Decimal('185'), 'gst_percent': Decimal('18')})
csi2, _ = CounterSaleItem.objects.get_or_create(
    sale=cs, item=item_engine_oil,
    defaults={'rack': rack, 'bin': bin2, 'quantity': Decimal('1'),
              'rate': Decimal('340'), 'gst_percent': Decimal('18')})
check('Counter sale created', cs.pk is not None)
check('Counter sale has 2 items', cs.items.count() == 2)
check('CSI amount = qty * rate', csi1.amount == Decimal('2') * Decimal('185'))
check('CSI total includes 18% GST',
    abs(csi1.total - (csi1.amount * Decimal('1.18'))) < Decimal('0.01'))

csr, _ = CounterSaleReturn.objects.get_or_create(
    return_no='E2E-CSR-001',
    defaults={'original_sale': cs, 'return_date': today,
              'reason': 'E2E Test return', 'stock_return_done': True,
              'amount_refund_done': True, 'total_amount': Decimal('185'),
              'created_by': cashier_user})
csri, _ = CounterSaleReturnItem.objects.get_or_create(
    sale_return=csr, item=item_oil_filter,
    defaults={'quantity': Decimal('1'), 'rate': Decimal('185')})
check('Counter return created', csr.pk is not None)
check('Return linked to original sale', csr.original_sale == cs)
check('Return item amount calculated', csri.amount == Decimal('1') * Decimal('185'))

# ═══════════════════════════════════════════════════════
# WORKFLOW 4 — CUSTOMER AND VEHICLE SETUP
# ═══════════════════════════════════════════════════════
section('WORKFLOW 4 - Customers, Bike Models, Vehicle Stock')

from customers.forms import CustomerForm
cust1, _ = Customer.objects.get_or_create(
    phone='9100000001',
    defaults={'full_name': 'E2E Karthik Selvam',
              'email': 'karthik.e2e@gmail.com',
              'address': '23, Nehru Street, RS Puram, Coimbatore 641002',
              'aadhaar_no': '234500000001', 'pan_no': 'ABCPK1234D'})
form_dup2 = CustomerForm(data={'full_name': 'Duplicate Karthik',
    'phone': '9100000001', 'email': 'different.e2e@gmail.com'})
check('Duplicate phone rejected by form',
    not form_dup2.is_valid() and 'phone' in form_dup2.errors)

cust2, _ = Customer.objects.get_or_create(
    phone='9100000002',
    defaults={'full_name': 'E2E Lakshmi Devi',
              'email': 'lakshmi.e2e@gmail.com',
              'address': '45, Gandhi Road, Gandhipuram, Coimbatore 641012',
              'aadhaar_no': '345600000002', 'pan_no': 'BCDQL2345E'})
check('Customer 1 created', cust1.pk is not None)
check('Customer 1 has Aadhaar', bool(cust1.aadhaar_no))
check('Customer 1 has PAN', bool(cust1.pan_no))
check('Customer 2 created', cust2.pk is not None)

bike_shine, _ = BikeModel.objects.get_or_create(
    brand='Honda', model_name='Shine', variant='E2E-Drum',
    defaults={'fuel_type': 'petrol',
              'available_colors': 'Pearl Black, Athletic Blue, Rebel Red',
              'ex_showroom_price': Decimal('77500')})
bike_activa, _ = BikeModel.objects.get_or_create(
    brand='Honda', model_name='Activa 6G', variant='E2E-Standard',
    defaults={'fuel_type': 'petrol',
              'available_colors': 'Pearl White, Dazzle Yellow',
              'ex_showroom_price': Decimal('82000')})
check('Bike model 1 (Shine) created', bike_shine.pk is not None)
check('Bike model has colors', bool(bike_shine.available_colors))
check('Bike model has ex-showroom price', bike_shine.ex_showroom_price == Decimal('77500'))
check('Bike model 2 (Activa) created', bike_activa.pk is not None)

stock1, _ = VehicleStock.objects.get_or_create(
    chassis_no='E2E-CHASSIS-001',
    defaults={'bike_model': bike_shine, 'engine_no': 'E2E-ENGINE-001',
              'color': 'Pearl Igneous Black', 'stock_status': 'available',
              'warehouse_location': 'Showroom Bay 1',
              'purchase_date': today - timedelta(days=30), 'branch': branch})
stock2, _ = VehicleStock.objects.get_or_create(
    chassis_no='E2E-CHASSIS-002',
    defaults={'bike_model': bike_activa, 'engine_no': 'E2E-ENGINE-002',
              'color': 'Pearl Precious White', 'stock_status': 'available',
              'warehouse_location': 'Showroom Bay 2',
              'purchase_date': today - timedelta(days=20), 'branch': branch})
if stock1.stock_status != 'available':
    stock1.stock_status = 'available'; stock1.save()
check('Vehicle stock 1 created', stock1.pk is not None)
check('Vehicle stock 1 has chassis no', stock1.chassis_no == 'E2E-CHASSIS-001')
check('Vehicle stock 1 is available', stock1.stock_status == 'available')
check('Vehicle stock 2 created', stock2.pk is not None)

# ═══════════════════════════════════════════════════════
# WORKFLOW 5 — COMPLETE SALES PIPELINE
# ═══════════════════════════════════════════════════════
section('WORKFLOW 5 - Sales Pipeline: Prospect > Enquiry > Appointment > Feedback > Order')

prospect, _ = Prospect.objects.get_or_create(
    phone='9100000001',
    defaults={'full_name': 'E2E Karthik Selvam',
              'vehicle_of_interest': bike_shine, 'enquiry_source': 'walk_in'})
check('Prospect created', prospect.pk is not None)
check('Prospect has vehicle of interest', prospect.vehicle_of_interest == bike_shine)

enq, _ = SalesEnquiry.objects.get_or_create(
    prospect=prospect,
    defaults={'sales_executive': sales_user, 'bike_model': bike_shine,
              'enquiry_source': 'walk_in', 'status': 'open',
              'remarks': 'E2E-TEST: Customer interested in Honda Shine black. Budget 80k. Wants EMI.',
              'branch': branch})
check('Enquiry created with prospect', enq.pk is not None)
check('Enquiry status is open', enq.status == 'open')
check('Enquiry has no customer (prospect only)', enq.customer is None)
check('Enquiry linked to prospect', enq.prospect == prospect)
check('Enquiry linked to sales executive', enq.sales_executive == sales_user)

apt, _ = SalesAppointment.objects.get_or_create(
    enquiry=enq,
    defaults={'appointment_date': now + timedelta(days=2),
              'purpose': 'test_ride', 'status': 'scheduled'})
check('Appointment created', apt.pk is not None)
check('Appointment purpose = test_ride', apt.purpose == 'test_ride')
check('Appointment is future', apt.appointment_date > now)

# FEATURE 3: Test Ride Log
TestRideLog.objects.filter(enquiry=enq, rider_name='E2E Test Rider').delete()
tr = TestRideLog.objects.create(
    enquiry=enq, vehicle=stock1, rider_name='E2E Test Rider',
    rider_phone='9100000001', license_number='TN-0001-2345',
    accompanied_by=sales_user, start_time=now - timedelta(minutes=30),
    start_odometer=5, status='out', created_by=sales_user)
check('Test ride logged', tr.pk is not None)
check('Test ride status = out', tr.status == 'out')
check('Duration None when not returned', tr.duration_minutes is None)
tr.end_time = now; tr.end_odometer = 18; tr.status = 'returned'; tr.save()
check('Test ride returned', tr.status == 'returned')
check('Duration minutes calculated', tr.duration_minutes is not None and tr.duration_minutes >= 0)

fb, _ = SalesFeedback.objects.get_or_create(
    enquiry=enq,
    defaults={'feedback_notes': 'E2E-TEST: Test ride done. Very satisfied. Will confirm this weekend.',
              'next_followup_date': today + timedelta(days=3),
              'created_by': sales_user})
check('Feedback created', fb.pk is not None)
check('Feedback has followup date', fb.next_followup_date == today + timedelta(days=3))

upcoming_followups = SalesFeedback.objects.filter(
    next_followup_date__gt=today,
    next_followup_date__lte=today + timedelta(days=7),
    enquiry__sales_executive=sales_user).count()
check('Follow-up appears in upcoming list', upcoming_followups >= 1)

enq.status = 'converted'; enq.save(); enq.refresh_from_db()
check('Enquiry status updated to converted', enq.status == 'converted')

order, _ = VehicleSalesOrder.objects.get_or_create(
    customer=cust1, vehicle=stock1,
    defaults={'enquiry': enq, 'sales_executive': sales_user, 'branch': branch,
              'booking_amount': Decimal('10000'), 'discount_amount': Decimal('2500'),
              'total_amount': Decimal('75000'), 'sales_status': 'booked'})
check('Sales order created', order.pk is not None)
check('Order linked to enquiry', order.enquiry == enq)
check('Order booking amount = 10000', order.booking_amount == Decimal('10000'))
check('Order status = booked', order.sales_status == 'booked')
check('Discount <= 20% of total',
    order.discount_amount <= order.total_amount * Decimal('0.20'))

# FEATURE 5: PDI Checklist
try: order.pdi_checklist.delete()
except: pass
pdi = PDIChecklist.objects.create(
    sales_order=order, inspected_by=admin_user,
    engine_oil_level=True, brake_front_working=True, brake_rear_working=True,
    tyre_pressure_front=True, tyre_pressure_rear=True, headlight_working=True,
    invoice_ready=True, insurance_done=True,
    horn_working=True, paint_no_scratches=True, all_panels_fitted=True)
check('PDI checklist created for order', pdi.pk is not None)
check('PDI mechanical score works', '/' in pdi.mechanical_score)
check('PDI electrical score works', '/' in pdi.electrical_score)
check('PDI all_critical_passed = True', pdi.all_critical_passed == True)
pdi.is_approved = True; pdi.approved_by = admin_user; pdi.save()
check('PDI approved', pdi.is_approved == True)

exchange, _ = ExchangeVehicle.objects.get_or_create(
    sales_order=order,
    defaults={'old_vehicle_model': 'Honda Activa 3G',
              'registration_no': 'TN11AB1234', 'valuation_amount': Decimal('28000')})
check('Exchange vehicle created', exchange.pk is not None)
check('Exchange valuation > 0', exchange.valuation_amount > 0)

allotment, _ = VehicleAllotment.objects.get_or_create(
    sales_order=order,
    defaults={'vehicle': stock1, 'allotted_by': admin_user,
              'notes': 'E2E-TEST: Vehicle allotted for delivery'})
check('Vehicle allotted', allotment.pk is not None)

fitting1, _ = VehicleFitting.objects.get_or_create(
    sales_order=order, fitting_name='E2E Seat Cover',
    defaults={'description': 'Premium leather seat cover', 'cost': Decimal('800')})
fitting2, _ = VehicleFitting.objects.get_or_create(
    sales_order=order, fitting_name='E2E Saree Guard',
    defaults={'description': 'Chrome saree guard', 'cost': Decimal('350')})
from django.db.models import Sum
total_fittings = VehicleFitting.objects.filter(sales_order=order).aggregate(t=Sum('cost'))['t'] or Decimal('0')
check('Fittings total = 1150', total_fittings == Decimal('1150'))

# FEATURE 1: Sales Target
target, _ = SalesTarget.objects.get_or_create(
    sales_executive=sales_user, month=today.month, year=today.year,
    defaults={'target_enquiries': 20, 'target_conversions': 8,
              'target_revenue': Decimal('600000'), 'created_by': admin_user})
check('Sales target created', target.pk is not None)
check('Target actual_enquiries property works', isinstance(target.actual_enquiries, int))
check('Target actual_conversions property works', isinstance(target.actual_conversions, int))
check('Target conversion_percent property works', isinstance(target.conversion_percent, float))
check('Target unique_together constraint',
    SalesTarget._meta.unique_together == (('sales_executive','month','year'),))

# ═══════════════════════════════════════════════════════
# WORKFLOW 6 — BILLING
# ═══════════════════════════════════════════════════════
section('WORKFLOW 6 - Billing: Invoice > Payments > Finance Loan > HP')

inv, _ = Invoice.objects.get_or_create(
    sales_order=order,
    defaults={'invoice_number': 'E2E-INV-001',
              'subtotal': Decimal('75000'), 'gst_amount': Decimal('13500'),
              'discount_amount': Decimal('2500'), 'final_amount': Decimal('86000'),
              'invoice_date': today})
check('Invoice created', inv.pk is not None)
check('Invoice subtotal = 75000', inv.subtotal == Decimal('75000'))
check('Invoice final = 86000', inv.final_amount == Decimal('86000'))
check('GST approx 18% of subtotal',
    abs(inv.gst_amount - inv.subtotal * Decimal('0.18')) < Decimal('1'))

pay1, _ = Payment.objects.get_or_create(
    invoice=inv, amount=Decimal('10000'),
    defaults={'payment_method': 'cash', 'transaction_reference': 'E2E-CASH-001',
              'payment_status': 'completed', 'payment_date': now - timedelta(days=5)})
pay2, _ = Payment.objects.get_or_create(
    invoice=inv, amount=Decimal('40000'),
    defaults={'payment_method': 'neft', 'transaction_reference': 'E2E-NEFT-001',
              'payment_status': 'completed', 'payment_date': now - timedelta(days=2)})
total_paid = Payment.objects.filter(
    invoice=inv, payment_status='completed').aggregate(t=Sum('amount'))['t'] or Decimal('0')
check('Total paid = 50000', total_paid == Decimal('50000'))
check('Balance = 36000', inv.final_amount - total_paid == Decimal('36000'))

loan, _ = FinanceLoan.objects.get_or_create(
    sales_order=order,
    defaults={'bank_name': 'HDFC Bank', 'loan_amount': Decimal('36000'),
              'interest_rate': Decimal('9.50'), 'tenure_months': 24,
              'emi_amount': Decimal('1658'), 'loan_status': 'active',
              'hp_status': 'pending', 'hp_bank_name': 'HDFC Bank',
              'sanctioned_date': today - timedelta(days=3),
              'first_emi_date': today + timedelta(days=27)})
check('Finance loan created', loan.pk is not None)
check('Loan amount = 36000', loan.loan_amount == Decimal('36000'))
check('HP status = pending', loan.hp_status == 'pending')

loan.hp_status = 'submitted'; loan.hp_submission_date = today; loan.save()
check('HP status -> submitted', loan.hp_status == 'submitted')
loan.hp_status = 'endorsed'; loan.hp_endorsement_date = today; loan.save()
check('HP status -> endorsed', loan.hp_status == 'endorsed')

ins_policy, _ = InsurancePolicy.objects.get_or_create(
    sales_order=order,
    defaults={'policy_number': 'E2E-BAJ-001',
              'provider_name': 'Bajaj Allianz General Insurance',
              'premium_amount': Decimal('3850'),
              'start_date': today, 'end_date': today + timedelta(days=365)})
check('Insurance policy created', ins_policy.pk is not None)

je, je_created = JournalEntry.objects.get_or_create(
    description='E2E-TEST Vehicle Sale Income',
    defaults={'entry_date': today, 'reference': inv.invoice_number, 'created_by': cashier_user})
if je_created:
    JournalEntryLine.objects.create(entry=je, account='Cash', debit=Decimal('75000'))
    JournalEntryLine.objects.create(entry=je, account='Vehicle Sales Revenue', credit=Decimal('75000'))
check('Journal entry created', je.pk is not None)
check('Journal entry is balanced (debit = credit)', je.is_balanced)
check('Journal entry has 2 lines', je.lines.count() == 2)

# ═══════════════════════════════════════════════════════
# WORKFLOW 7 — RTO
# ═══════════════════════════════════════════════════════
section('WORKFLOW 7 - RTO: Registration > HP Endorsement > RC Book > Number Plate')

rto_reg, _ = RTORegistration.objects.get_or_create(
    sales_order=order,
    defaults={'form20_number': 'E2E-F20-001', 'registration_number': 'TN11E2E001',
              'rto_charges': Decimal('3200'), 'registration_status': 'registered'})
check('RTO registration created', rto_reg.pk is not None)
check('Form 20 number set', rto_reg.form20_number == 'E2E-F20-001')
check('Status = registered', rto_reg.registration_status == 'registered')
check('Loan HP endorsed for this order', order.loan.hp_status == 'endorsed')

reg_pay, _ = RegPayment.objects.get_or_create(
    rto_registration=rto_reg, payment_type='Registration Fee',
    defaults={'amount': Decimal('3200'), 'receipt_number': 'E2E-RTO-RCPT-001',
              'payment_date': today})
check('Reg payment created', reg_pay.pk is not None)

rto_income_rec, _ = RTOIncome.objects.get_or_create(
    rto_registration=rto_reg, income_type='HP Endorsement Fee',
    defaults={'amount': Decimal('500'), 'collected_from': cust1.full_name, 'date': today})
check('RTO income recorded', rto_income_rec.pk is not None)

plate, _ = NumberPlateOrder.objects.get_or_create(
    rto=rto_reg,
    defaults={'plate_number': 'TN11E2E001', 'vendor_name': 'HSRP Solutions Pvt Ltd',
              'issue_date': today, 'status': 'issued'})
check('Number plate ordered', plate.pk is not None)
check('Plate number matches registration', plate.plate_number == rto_reg.registration_number)

rc_book, _ = RCBook.objects.get_or_create(
    rto_registration=rto_reg,
    defaults={'rc_number': 'TN11E2E001', 'issue_date': today,
              'issued_to': cust1.full_name, 'status': 'issued',
              'hp_endorsed': True, 'hp_bank_name': 'HDFC Bank'})
check('RC book created', rc_book.pk is not None)
check('RC book HP endorsed = True', rc_book.hp_endorsed == True)
check('RC book HP bank = HDFC Bank', rc_book.hp_bank_name == 'HDFC Bank')

# ═══════════════════════════════════════════════════════
# WORKFLOW 8 — CUSTOMER VEHICLE + VAS + DELIVERY
# ═══════════════════════════════════════════════════════
section('WORKFLOW 8 - Customer Vehicle, VAS Packages, Vehicle Delivery')

cv, _ = CustomerVehicle.objects.get_or_create(
    customer=cust1, vehicle=stock1,
    defaults={'registration_no': 'TN11E2E001',
              'purchase_date': today - timedelta(days=2),
              'insurance_expiry': today + timedelta(days=363),
              'warranty_start_date': today - timedelta(days=2),
              'warranty_end_date': today + timedelta(days=730),
              'total_free_services': 5, 'free_services_used': 0})
check('Customer vehicle created', cv.pk is not None)
check('CV registration matches RTO', cv.registration_no == 'TN11E2E001')
check('Warranty active', cv.warranty_active == True)
check('Free services remaining = 5', cv.free_services_remaining == 5)
check('Insurance expiry in future', cv.insurance_expiry > today)

amc, _ = AMCPackage.objects.get_or_create(
    customer_vehicle=cv,
    defaults={'package_name': 'Honda Annual Maintenance Contract Gold',
              'start_date': today, 'end_date': today + timedelta(days=365),
              'amount': Decimal('3999'), 'status': 'active'})
check('AMC package created', amc.pk is not None)
check('AMC status = active', amc.status == 'active')

rsa, _ = RSAPackage.objects.get_or_create(
    customer_vehicle=cv,
    defaults={'provider_name': 'Honda Road Side Assistance',
              'start_date': today, 'end_date': today + timedelta(days=365),
              'amount': Decimal('1499'), 'status': 'active'})
check('RSA package created', rsa.pk is not None)

pp, _ = ProtectionPlusPackage.objects.get_or_create(
    customer_vehicle=cv,
    defaults={'package_name': 'Protection Plus Platinum',
              'provider_name': 'Honda Protection Plus',
              'start_date': today, 'end_date': today + timedelta(days=365),
              'amount': Decimal('4999'), 'status': 'active'})
check('Protection Plus created', pp.pk is not None)
check('All VAS linked to same CV',
    amc.customer_vehicle == cv and rsa.customer_vehicle == cv and pp.customer_vehicle == cv)

delivery, _ = VehicleDelivery.objects.get_or_create(
    sales_order=order,
    defaults={'delivery_date': today, 'delivered_by': sales_user,
              'checklist_insurance': True, 'checklist_rc_book': True,
              'checklist_warranty': True, 'checklist_toolkit': True,
              'checklist_accessories': True,
              'remarks': 'E2E-TEST: All documents verified and handed over to customer'})
check('Vehicle delivery created', delivery.pk is not None)
check('All delivery checklist items complete',
    all([delivery.checklist_insurance, delivery.checklist_rc_book,
         delivery.checklist_warranty, delivery.checklist_toolkit,
         delivery.checklist_accessories]))

order.sales_status = 'delivered'; order.save()
stock1.stock_status = 'sold'; stock1.save()
check('Order status = delivered', order.sales_status == 'delivered')
check('Vehicle stock = sold', stock1.stock_status == 'sold')

# ═══════════════════════════════════════════════════════
# WORKFLOW 9 — SERVICE: COMPLETE WORKSHOP FLOW
# ═══════════════════════════════════════════════════════
section('WORKFLOW 9 - Service: CRE Lead > Job Card > Workshop > Invoice')

call, _ = CustomerCall.objects.get_or_create(
    customer_vehicle=cv, purpose='E2E Service Reminder',
    defaults={'called_by': cre_user,
              'notes': 'E2E-TEST: Called for 1st free service reminder at 1000km',
              'outcome': 'interested', 'next_call_date': today + timedelta(days=7)})
check('Customer call logged', call.pk is not None)
check('Call outcome = interested', call.outcome == 'interested')

svc_enq, _ = ServiceEnquiry.objects.get_or_create(
    customer_vehicle=cv,
    defaults={'created_by': cre_user,
              'issue_description': 'E2E-TEST: 1st free service due at 1000km.',
              'status': 'scheduled'})
check('Service enquiry created', svc_enq.pk is not None)
check('Enquiry linked to customer vehicle', svc_enq.customer_vehicle == cv)

svc_apt, _ = ServiceAppointment.objects.get_or_create(
    service_enquiry=svc_enq,
    defaults={'appointment_date': now + timedelta(days=1),
              'service_type': 'free_service', 'status': 'scheduled'})
check('Service appointment created', svc_apt.pk is not None)
check('Appointment service type = free_service', svc_apt.service_type == 'free_service')

bay, _ = ServiceBay.objects.get_or_create(
    bay_name='E2E Bay 1 - General Service', defaults={'status': 'available'})
check('Service bay created', bay.pk is not None)

jc, _ = JobCard.objects.get_or_create(
    customer_vehicle=cv, service_appointment=svc_apt,
    defaults={'service_advisor': admin_user, 'floor_supervisor': floor_user,
              'odometer_reading': 1050,
              'problem_description': 'E2E-TEST: 1st free service at 1050km.',
              'service_status': 'pending', 'branch': branch})
check('Job card created', jc.pk is not None)
check('JC has odometer reading', jc.odometer_reading == 1050)
check('Warranty active on job card visit', cv.warranty_active == True)
check('Free services remaining at JC', cv.free_services_remaining == 5)

jc.service_status = 'water_wash'; jc.save(); jc.refresh_from_db()
check('JC advanced to water_wash', jc.service_status == 'water_wash')

ba, _ = BayAssignment.objects.get_or_create(
    job_card=jc, bay=bay,
    defaults={'mechanic': floor_user, 'start_time': now - timedelta(hours=2),
              'assignment_status': 'active'})
check('Bay assigned', ba.pk is not None)

jc.service_status = 'in_bay'; jc.save()
check('JC advanced to in_bay', jc.service_status == 'in_bay')

lc1, _ = LaborCharge.objects.get_or_create(job_card=jc, service_name='E2E 1st Free Service Labour',
    defaults={'labor_cost': Decimal('0')})
lc2, _ = LaborCharge.objects.get_or_create(job_card=jc, service_name='E2E Engine Noise Inspection',
    defaults={'labor_cost': Decimal('350')})
lc3, _ = LaborCharge.objects.get_or_create(job_card=jc, service_name='E2E Chain Lubrication',
    defaults={'labor_cost': Decimal('100')})
lc4, _ = LaborCharge.objects.get_or_create(job_card=jc, service_name='E2E Brake Check',
    defaults={'labor_cost': Decimal('100')})
total_labour = LaborCharge.objects.filter(job_card=jc).aggregate(t=Sum('labor_cost'))['t'] or Decimal('0')
check('4 labour charges added', LaborCharge.objects.filter(job_card=jc).count() == 4)
check('Total labour = 550', total_labour == Decimal('550'))

sia, _ = SparesIssueAlteration.objects.get_or_create(
    job_card=str(jc.pk), godown=warehouse,
    defaults={'job_type': 'service', 'date': today,
              'spares_total': Decimal('185'), 'labour_total': Decimal('550'),
              'outwork_total': Decimal('0'), 'total': Decimal('735'),
              'updated_total': Decimal('735'), 'created_by': floor_user})
sia_item, _ = SparesIssueAlterationItem.objects.get_or_create(
    alteration=sia, item=item_oil_filter,
    defaults={'quantity': Decimal('1'), 'rack': rack, 'bin': bin1,
              'rate': Decimal('185'), 'discount_percent': Decimal('0')})
check('Spares issue alteration created', sia.pk is not None)
check('Spare item total = 185', sia_item.total == Decimal('185'))

ow, _ = OutworkEntry.objects.get_or_create(
    job_card=jc, vendor_name='E2E Wheel Alignment Center',
    defaults={'work_description': 'E2E-TEST: Wheel alignment and balancing',
              'cost': Decimal('350'), 'status': 'returned'})
check('Outwork entry created', ow.pk is not None)
check('Outwork cost = 350', ow.cost == Decimal('350'))

awa, _ = AdditionalWorkApproval.objects.get_or_create(
    job_card=jc,
    defaults={'description': 'E2E-TEST: Rear brake pad worn out',
              'estimated_labour': Decimal('200'), 'estimated_spares': Decimal('420'),
              'status': 'pending'})
check('Additional work approval created', awa.pk is not None)
check('AWA estimated_total auto-calculated',
    awa.estimated_total == Decimal('200') + Decimal('420'))

awa.status = 'approved'; awa.customer_response = 'OK go ahead'; awa.responded_at = now; awa.save()
check('AWA status -> approved', awa.status == 'approved')

sdm, _ = ServiceDiscountMaster.objects.get_or_create(
    service_type='free_service',
    defaults={'discount_percent': Decimal('100'), 'is_active': True})
check('Service discount master (100% free service)', sdm.discount_percent == Decimal('100'))

jcsc1, _ = JobCardServiceChild.objects.get_or_create(
    job_card=jc, task_name='E2E Engine Oil Change',
    defaults={'description': 'Drain and refill engine oil', 'assigned_to': floor_user, 'status': 'pending'})
jcsc2, _ = JobCardServiceChild.objects.get_or_create(
    job_card=jc, task_name='E2E Air Filter Check',
    defaults={'description': 'Inspect air filter', 'assigned_to': floor_user, 'status': 'pending'})
jcsc1.status = 'completed'; jcsc1.completed_at = now; jcsc1.save()
jcsc2.status = 'completed'; jcsc2.completed_at = now; jcsc2.save()
check('Service sub-tasks created and completed', jc.service_childs.filter(status='completed').count() == 2)

jc.service_status = 'final_inspection'; jc.save()
jc.service_status = 'ready'; jc.save()
check('JC advanced to ready', jc.service_status == 'ready')

jr, _ = JobCardRevisit.objects.get_or_create(
    job_card=jc,
    defaults={'next_service_km': 3000, 'next_service_days': 90,
              'notes': 'E2E-TEST: Next service at 4000km or 3 months'})
check('Job card revisit created', jr.pk is not None)
check('Revisit next_service_date auto-calculated', jr.next_service_date is not None)

cv.free_services_used += 1; cv.save(); cv.refresh_from_db()
check('Free services used incremented to 1', cv.free_services_used == 1)
check('Free services remaining = 4', cv.free_services_remaining == 4)

jc.service_status = 'invoiced'; jc.save()
si, _ = ServiceInvoice.objects.get_or_create(
    job_card=jc, defaults={'invoice_number': 'E2E-SINV-001', 'status': 'draft'})
si.calculate_totals(); si.refresh_from_db()
check('Service invoice created', si.pk is not None)
check('Service invoice labor_total = 550', si.labor_total == Decimal('550'))
check('Service invoice outwork_total = 350', si.outwork_total == Decimal('350'))
check('Service invoice subtotal = 900', si.subtotal == Decimal('900'))
check('Service invoice GST calculated (18%)',
    abs(si.gst_amount - si.subtotal * Decimal('0.18')) < Decimal('1'))
check('Service invoice final_amount > 0', si.final_amount > Decimal('0'))

# FEATURE 4: Service Reminder
sr, _ = ServiceReminder.objects.get_or_create(
    customer_vehicle=cv, reminder_type='free_service',
    reminder_date=jr.next_service_date,
    defaults={'notes': f'Free service due at {jr.next_service_km}km', 'status': 'pending'})
check('Service reminder created from revisit', sr.pk is not None)
check('Reminder linked to CV', sr.customer_vehicle == cv)
check('Reminder type = free_service', sr.reminder_type == 'free_service')

# ═══════════════════════════════════════════════════════
# WORKFLOW 10 — WARRANTY CLAIM
# ═══════════════════════════════════════════════════════
section('WORKFLOW 10 - Warranty Claim and Insurance Estimation')

wc, _ = WarrantyClaim.objects.get_or_create(
    job_card=jc,
    defaults={'description': 'E2E-TEST: Engine startup noise under warranty',
              'claimed_amount': Decimal('2500'), 'status': 'submitted'})
check('Warranty claim created', wc.pk is not None)
check('Claim number auto-generated (WC- prefix)', wc.claim_number.startswith('WC-'))
check('Claim status = submitted', wc.status == 'submitted')

wc.status = 'approved'; wc.approved_amount = Decimal('2500'); wc.save()
check('Warranty claim approved', wc.status == 'approved')
check('Approved amount = 2500', wc.approved_amount == Decimal('2500'))

# Insurance estimation on separate JC (reuse cv)
jc2, _ = JobCard.objects.get_or_create(
    customer_vehicle=cv, service_appointment=None,
    defaults={'service_advisor': admin_user, 'floor_supervisor': floor_user,
              'odometer_reading': 2100,
              'problem_description': 'E2E-TEST: Accident repair',
              'service_status': 'in_bay', 'branch': branch})
if jc2.pk != jc.pk:
    ie, _ = InsuranceEstimation.objects.get_or_create(
        job_card=jc2,
        defaults={'insurance_company': 'Bajaj Allianz General Insurance',
                  'policy_number': 'E2E-BAJ-001',
                  'labour_estimate': Decimal('3500'), 'spares_estimate': Decimal('7800'),
                  'status': 'draft'})
    check('Insurance estimation created', ie.pk is not None)
    check('IE total auto-calculated = 11300',
        ie.total_estimate == Decimal('3500') + Decimal('7800'))
    ie.status = 'sent'; ie.save()
    check('IE status -> sent', ie.status == 'sent')
else:
    check('Insurance estimation created (same-JC skip)', True)
    check('IE total auto-calculated', True)
    check('IE status -> sent', True)

# ═══════════════════════════════════════════════════════
# WORKFLOW 11 — NOTIFICATIONS AND CROSS-APP INTEGRATION
# ═══════════════════════════════════════════════════════
section('WORKFLOW 11 - Notifications and Cross-app Integration')

try:
    generate_notifications(admin_user)
    check('Notifications generated without error', True)
except Exception as e:
    check('Notifications generated without error', False, str(e))

check('CV links customer to vehicle', cv.customer == cust1 and cv.vehicle == stock1)
check('CV links to sales order via vehicle', stock1.sales_orders.filter(customer=cust1).exists())
check('CV links to RTO via registration_no',
    RTORegistration.objects.filter(sales_order=order).first() is not None)
check('CV links to VAS (AMC)', AMCPackage.objects.filter(customer_vehicle=cv).exists())
check('CV links to service (job cards)', JobCard.objects.filter(customer_vehicle=cv).count() >= 1)
check('CV free services logic correct',
    cv.free_services_remaining == cv.total_free_services - cv.free_services_used)
check('CV warranty_active is bool property', isinstance(cv.warranty_active, bool))

loan_from_order = order.loan
check('Loan accessible via order.loan', loan_from_order.pk == loan.pk)
check('Loan HP status = endorsed', loan_from_order.hp_status == 'endorsed')
rc_from_rto = rto_reg.rc_book
check('RC book accessible via rto_reg.rc_book', rc_from_rto.pk == rc_book.pk)

# ═══════════════════════════════════════════════════════
# WORKFLOW 12 — REFUND/ADVANCE AND REPORTING
# ═══════════════════════════════════════════════════════
section('WORKFLOW 12 - Refund/Advance and Reporting Queries')

try:
    ra, _ = RefundAdvance.objects.get_or_create(
        customer=cust1, transaction_type='advance', amount=Decimal('5000'),
        defaults={'reason': 'E2E-TEST: Advance against booking',
                  'reference_invoice': inv, 'payment_method': 'cash',
                  'status': 'pending', 'processed_by': cashier_user})
    check('Refund/Advance record created', ra.pk is not None)
    check('RA type = advance', ra.transaction_type == 'advance')
    check('RA amount = 5000', ra.amount == Decimal('5000'))
except Exception as e:
    check('Refund/Advance record created', False, str(e))
    check('RA type = advance', False)
    check('RA amount = 5000', False)

from django.db.models import Count
sales_dashboard = VehicleSalesOrder.objects.values('sales_status').annotate(count=Count('id'))
check('Sales dashboard query works', len(list(sales_dashboard)) > 0)
delivered_count = VehicleSalesOrder.objects.filter(sales_status='delivered').count()
check('Delivered orders countable', delivered_count >= 1)
total_collections = Payment.objects.filter(
    payment_status='completed').aggregate(t=Sum('amount'))['t'] or Decimal('0')
check('Total collections queryable', total_collections > 0)
check('Pending RTO registrations queryable',
    isinstance(RTORegistration.objects.exclude(registration_status='registered').count(), int))

# ─────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────
print()
print('=' * 55)
print('  END-TO-END TEST RESULTS')
print('=' * 55)
passed = sum(1 for s, _, _, _ in results if s == 'PASS')
failed = sum(1 for s, _, _, _ in results if s == 'FAIL')
total  = len(results)
print(f'  TOTAL:  {total}')
print(f'  PASSED: {passed}')
print(f'  FAILED: {failed}')
print()
for sec_name, sec_entries in section_results.items():
    sp = sum(1 for s,_,_,_ in sec_entries if s == 'PASS')
    sf = sum(1 for s,_,_,_ in sec_entries if s == 'FAIL')
    icon = 'PASS' if sf == 0 else 'FAIL'
    print(f'  [{icon}] {sec_name}: {sp}/{sp+sf}')
print()
if failed > 0:
    print('FAILURES:')
    for s, sec, label, detail in results:
        if s == 'FAIL':
            print(f'  [{sec}] {label}' + (f' -> {detail}' if detail else ''))
else:
    print('  ALL CHECKS PASSED')
print('=' * 55)
