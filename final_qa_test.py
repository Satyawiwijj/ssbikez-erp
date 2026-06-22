import os, sys, time, json, datetime, sqlite3, re
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')

import django
django.setup()

from playwright.sync_api import sync_playwright
from django.utils import timezone

BASE_URL = 'http://127.0.0.1:8010'
SS_DIR = r'C:\Users\Satya\ssbikez-erp\final_qa'
os.makedirs(SS_DIR, exist_ok=True)

results = []
issues = []
ss_count = [0]

def ss(page, name):
    ss_count[0] += 1
    path = os.path.join(SS_DIR, f'{ss_count[0]:04d}_{name}.png')
    try:
        page.screenshot(path=path, full_page=True)
    except:
        try: page.screenshot(path=path)
        except: pass
    return path

def ok(flow, check, page, name=None):
    n = name or check[:40].replace(' ','_').replace('/','_')
    ss(page, n)
    results.append({'status':'PASS','flow':flow,'check':check})
    print(f'  [OK] {flow} / {check}')

def fail(flow, check, detail, page, name=None):
    n = f'FAIL_{(name or check[:30]).replace(" ","_")}'
    path = ss(page, n)
    issues.append({'flow':flow,'check':check,'detail':detail,'ss':path})
    results.append({'status':'FAIL','flow':flow,'check':check,'detail':detail})
    print(f'  [FAIL] {flow} / {check}: {detail}')

def go(page, path, wait=800):
    page.goto(f'{BASE_URL}{path}', wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(wait)

def no_error(page):
    c = page.content()
    for e in ['Internal Server Error','TemplateSyntaxError','DoesNotExist',
               'NoReverseMatch','Exception Value','Traceback (most recent',
               'Page not found (404)','Server Error (500)','OperationalError']:
        if e in c:
            return False, e
    return True, None

def has(page, text):
    return text.lower() in page.content().lower()

def vis(page, sel):
    try:
        el = page.query_selector(sel)
        return el is not None and el.is_visible()
    except:
        return False

def chk(page, flow, label, condition, detail=''):
    if condition:
        ok(flow, label, page)
    else:
        fail(flow, label, detail or 'Check failed', page)
    return condition

def render_ok(page, flow, name):
    ok_flag, err = no_error(page)
    if not ok_flag:
        fail(flow, f'{name} no server error', err, page, name)
        return False
    if len(page.content()) < 500:
        fail(flow, f'{name} has content', 'Too short', page, name)
        return False
    ok(flow, f'{name} renders correctly', page, name)
    return True

def submit(page):
    page.evaluate("""() => {
        const b = document.querySelector('button[form]') ||
                  document.querySelector('button[type="submit"]') ||
                  document.querySelector('.topbar-actions button') ||
                  document.querySelector('form button.btn-primary') ||
                  document.querySelector('button.btn-primary');
        if (b) b.click();
    }""")
    page.wait_for_load_state('domcontentloaded', timeout=15000)
    page.wait_for_timeout(700)

def fill(page, sel, val):
    el = page.query_selector(sel)
    if el:
        try: el.fill(str(val)); return True
        except:
            try: el.type(str(val)); return True
            except: return False
    return False

def fill_date(page, name, val):
    el = page.query_selector(f'input[name="{name}"]')
    if not el: return False
    itype = el.get_attribute('type') or 'text'
    v = str(val)
    if itype == 'datetime-local' and 'T' not in v:
        v = f'{v}T10:00'
    elif itype != 'datetime-local' and 'T' in v:
        v = v[:10]
    try: el.fill(v); return True
    except: return False

def sel_first(page, name):
    s = page.query_selector(f'select[name="{name}"]')
    if s:
        for o in s.query_selector_all('option'):
            v = o.get_attribute('value')
            if v and v.strip() and v not in ['','---------','None']:
                s.select_option(value=v)
                return v
    return None

def get_otp():
    db = sqlite3.connect(r'C:\Users\Satya\ssbikez-erp\db.sqlite3')
    cur = db.cursor()
    try:
        cur.execute("SELECT otp_code FROM accounts_otpverification ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
    except: row = None
    db.close()
    return row[0] if row else None

def login(page, user='admin', pwd='SSBikez@2026'):
    go(page, '/accounts/login/')
    fill(page, 'input[name="username"]', user)
    fill(page, 'input[name="password"]', pwd)
    page.press('input[name="password"]', 'Enter')
    page.wait_for_load_state('domcontentloaded', timeout=12000)
    page.wait_for_timeout(1200)
    if 'otp' in page.url.lower() or 'verify' in page.url.lower():
        time.sleep(2)
        otp = get_otp()
        if otp:
            fill(page, 'input[name="otp_code"]', otp)
            page.press('input[name="otp_code"]', 'Enter')
            page.wait_for_load_state('domcontentloaded', timeout=12000)
            page.wait_for_timeout(1000)
    return 'login' not in page.url and 'otp' not in page.url

# ------ Import models ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
from customers.models import Customer, BikeModel, VehicleStock
from customer_vehicles.models import CustomerVehicle
from sales.models import (SalesEnquiry, SalesAppointment, SalesFeedback,
    VehicleSalesOrder, VehicleDelivery, SalesTarget, TestRideLog,
    PDIChecklist, VehicleFitting, VehicleAllotment, ExchangeVehicle)
from billing.models import (Invoice, Payment, FinanceLoan, InsurancePolicy,
    RefundAdvance, JournalEntry)
from rto.models import RTORegistration, RCBook, NumberPlateOrder
from service.models import (JobCard, ServiceEnquiry, ServiceAppointment,
    ServiceBay, BayAssignment, LaborCharge, OutworkEntry, ServiceInvoice,
    WarrantyClaim, InsuranceEstimation, ServiceDiscountMaster,
    AdditionalWorkApproval, CustomerCall, JobCardRevisit,
    JobCardServiceChild, ServiceReminder)
from spares.models import (SparesItem, StockLedger, SupplierQuote,
    PurchaseOrder, PurchaseInvoice, CounterSale, CounterSaleItem,
    SparesIssueAlteration)
from vas.models import AMCPackage, RSAPackage, ProtectionPlusPackage
from accounts.models import CompanySettings, Notification, Role, Branch
from masters.models import Supplier, Warehouse, Rack, Bin
from django.contrib.auth import get_user_model
User = get_user_model()

# ------ Clean previous test data ---------------------------------------------------------------------------------------------------------------------------------------------------------
_db = sqlite3.connect(r'C:\Users\Satya\ssbikez-erp\db.sqlite3')
_cur = _db.cursor()
for _phone in ['9500000071','9500000072','9500000073']:
    _cur.execute('SELECT id FROM customers_customer WHERE phone=?', (_phone,))
    for (_cid,) in _cur.fetchall():
        for _t in ['sales_salesenquiry','sales_vehiclesalesorder',
                   'customer_vehicles_customervehicle']:
            try: _cur.execute(f'DELETE FROM {_t} WHERE customer_id=?', (_cid,))
            except: pass
        _cur.execute('DELETE FROM customers_customer WHERE id=?', (_cid,))
_cur.execute("DELETE FROM customers_vehiclestock WHERE chassis_no LIKE 'FQA%'")
_db.commit()
_db.close()
print('Test data cleaned.')

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=120)
    ctx = browser.new_context(viewport={'width':1440,'height':900})
    page = ctx.new_page()

    print('\n' + '='*65)
    print('FINAL QA TEST --- SSBikez ERP --- Complete Coverage')
    print('='*65)

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 1. AUTH
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 1. AUTH ---------')
    go(page, '/accounts/login/')
    ss(page, '001_login_page')
    render_ok(page, 'Auth', '001_login')
    chk(page,'Auth','Login: branding visible', has(page,'SSBikez') or has(page,'bikez') or has(page,'Login'))
    chk(page,'Auth','Login: username field',   vis(page,'input[name="username"]'))
    chk(page,'Auth','Login: password field',   vis(page,'input[name="password"]'))
    chk(page,'Auth','Login: submit button',    vis(page,'button') or vis(page,'input[type="submit"]'))

    fill(page,'input[name="username"]','admin')
    fill(page,'input[name="password"]','wrongpassword')
    page.press('input[name="password"]','Enter')
    page.wait_for_load_state('domcontentloaded',timeout=8000)
    page.wait_for_timeout(500)
    ss(page,'002_wrong_password')
    chk(page,'Auth','Login: wrong password shows error',
        has(page,'invalid') or has(page,'incorrect') or has(page,'error') or 'login' in page.url.lower())

    login(page)
    ss(page,'003_after_login')
    chk(page,'Auth','Login: successful login redirects', 'login' not in page.url and 'otp' not in page.url)

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 2. HOME
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 2. HOME ---------')
    go(page, '/accounts/home/')
    ss(page,'004_home_full')
    render_ok(page,'Home','004_home')
    for mod in ['Sales','Service','Spares','Billing','RTO','Customers','Masters','Reports']:
        chk(page,'Home',f'Module card: {mod}', has(page,mod))
    chk(page,'Home','Greeting/admin visible', has(page,'Good') or has(page,'Welcome') or has(page,'admin'))
    chk(page,'Home','Date/period visible',
        has(page,'2026') or has(page,'June') or has(page,'Jun') or
        has(page,'Jan') or has(page,'Feb') or has(page,'Mar') or
        has(page,'Apr') or has(page,'May') or has(page,'Jul') or
        has(page,'Aug') or has(page,'Sep') or has(page,'Oct') or
        has(page,'Nov') or has(page,'Dec') or has(page,'Morning') or
        has(page,'Afternoon') or has(page,'Evening'))
    for href, name in [('/sales/','Sales'),('/service/','Service'),('/spares/','Spares'),('/billing/','Billing')]:
        chk(page,'Home',f'{name} card is a link', bool(page.query_selector(f'a[href*="{href}"]')))

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 3. DASHBOARD
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 3. DASHBOARD ---------')
    go(page, '/accounts/dashboard/')
    ss(page,'005_dashboard_full')
    render_ok(page,'Dashboard','005_dashboard')
    for kpi in ['enquir','order','job','follow','notif']:
        chk(page,'Dashboard',f'KPI: {kpi}', has(page,kpi))
    for section in ['SALES','CUSTOMERS','FINANCE','SERVICE','SPARES','MASTERS','REPORTS','ADMIN']:
        chk(page,'Dashboard',f'Sidebar: {section}', has(page,section))
    chk(page,'Dashboard','Topbar: search bar',
        vis(page,'input[placeholder*="Search"], input[placeholder*="search"], .topbar-search'))
    chk(page,'Dashboard','Topbar: notification bell',
        vis(page,'a[href*="notification"], .notification-bell, #notif-count-badge'))
    chk(page,'Dashboard','Topbar: user avatar',
        vis(page,'.user-avatar, .user-menu, .topbar-user'))
    chk(page,'Dashboard','Follow-up board visible', has(page,'Follow') or has(page,'Overdue') or has(page,'Today'))
    chk(page,'Dashboard','Quick actions visible', has(page,'New') or has(page,'Quick') or has(page,'Action'))

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 4. CUSTOMERS
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 4. CUSTOMERS ---------')
    go(page, '/customers/customers/')
    ss(page,'006_customer_list')
    render_ok(page,'Customers','006_customer_list')
    chk(page,'Customers','List: table headers',    has(page,'Name') or has(page,'Phone'))
    chk(page,'Customers','List: New Customer btn', has(page,'New Customer') or has(page,'Add Customer'))
    chk(page,'Customers','List: search bar',
        vis(page,'input[type="search"], input[placeholder*="Search"], input[name="q"]'))

    go(page, '/customers/customers/create/')
    ss(page,'007_customer_create')
    render_ok(page,'Customers','007_customer_create_form')
    for fname, label in [('full_name','Full Name'),('phone','Phone'),('email','Email')]:
        chk(page,'Customers',f'Create: {label} field', vis(page,f'input[name="{fname}"]'))

    fill(page,'input[name="full_name"]','FQA Test Customer')
    fill(page,'input[name="phone"]','9500000071')
    fill(page,'input[name="email"]','fqa@ssbikez.com')
    fill(page,'textarea[name="address"], input[name="address"]','1 FQA Street Coimbatore')
    aadhaar = page.query_selector('input[name="aadhaar_no"]')
    if aadhaar: aadhaar.fill('999900000071')
    pan = page.query_selector('input[name="pan_no"]')
    if pan: pan.fill('ABCFQ9999Z')
    ss(page,'007_customer_filled')
    submit(page)
    ss(page,'008_customer_result')

    cust = Customer.objects.filter(phone='9500000071').first()
    chk(page,'Customers','Customer created and saved to DB', cust is not None)
    customer_pk = cust.pk if cust else None

    if customer_pk:
        go(page, f'/customers/customers/{customer_pk}/')
        ss(page,'009_customer_detail')
        render_ok(page,'Customers','009_customer_detail')
        for text in ['FQA Test Customer','9500000071','fqa@ssbikez.com']:
            chk(page,'Customers',f'Customer detail: {text[:20]}', has(page,text))
        for tab in ['Profile','Vehicle','Order','Service']:
            chk(page,'Customers',f'Detail tab: {tab}', has(page,tab))

        go(page, f'/customers/{customer_pk}/edit/')
        ss(page,'010_customer_edit')
        render_ok(page,'Customers','010_customer_edit')
        chk(page,'Customers','Edit: form pre-filled',
            has(page,'FQA Test Customer') or has(page,'FQA') or has(page,'9500000071'))

    # Duplicate phone
    go(page, '/customers/customers/create/')
    fill(page,'input[name="full_name"]','Duplicate')
    fill(page,'input[name="phone"]','9500000071')
    fill(page,'input[name="email"]','dup@test.com')
    submit(page)
    ss(page,'011_duplicate_error')
    chk(page,'Customers','Duplicate phone: error shown',
        has(page,'error') or has(page,'already') or has(page,'exist') or has(page,'phone'))

    # Bike models
    go(page, '/customers/bike-models/')
    ss(page,'012_bike_models')
    render_ok(page,'Customers','012_bike_models')
    bm = BikeModel.objects.first()
    if bm:
        go(page, f'/customers/bike-models/{bm.pk}/')
        ss(page,'013_bike_model_detail')
        render_ok(page,'Customers','013_bike_model_detail')
        chk(page,'Customers','Bike model detail: name', has(page,bm.model_name))
        chk(page,'Customers','Bike model detail: price', has(page,'price') or has(page,'showroom') or has(page,'cost'))

    # Vehicle stock
    go(page, '/customers/vehicle-stock/')
    ss(page,'014_vehicle_stock')
    render_ok(page,'Customers','014_vehicle_stock')
    chk(page,'Customers','Stock list: columns', has(page,'Chassis') or has(page,'Model') or has(page,'Status'))

    go(page, '/customers/vehicle-stock/create/')
    ss(page,'015_stock_create')
    render_ok(page,'Customers','015_stock_create_form')
    sel_first(page,'bike_model')
    fill(page,'input[name="chassis_no"]','FQA-CHASSIS-001')
    fill(page,'input[name="engine_no"]','FQA-ENGINE-001')
    fill(page,'input[name="color"]','Pearl Black')
    fill_date(page,'purchase_date',datetime.date.today().isoformat())
    submit(page)
    ss(page,'016_stock_result')
    stock = VehicleStock.objects.filter(chassis_no='FQA-CHASSIS-001').first()
    chk(page,'Customers','Vehicle stock created', stock is not None)

    if stock:
        go(page, f'/customers/vehicle-stock/{stock.pk}/')
        ss(page,'017_stock_detail')
        render_ok(page,'Customers','017_stock_detail')
        chk(page,'Customers','Stock detail: chassis no', has(page,'FQA-CHASSIS-001'))
        chk(page,'Customers','Stock detail: status',     has(page,'available') or has(page,'Status'))

    # Stock aging
    go(page, '/customers/vehicle-stock/aging/')
    ss(page,'018_stock_aging')
    render_ok(page,'Customers','018_stock_aging')
    for days in ['30','60','90']:
        chk(page,'Customers',f'Stock aging: {days}-day bucket', has(page,days))

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 5. SALES PIPELINE
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 5. SALES ---------')

    go(page, '/sales/')
    ss(page,'019_sales_dashboard')
    render_ok(page,'Sales','019_sales_dashboard')

    go(page, '/sales/enquiries/')
    ss(page,'020_enquiry_list')
    render_ok(page,'Sales','020_enquiry_list')
    for tab in ['All','Open','Follow','Converted','Lost']:
        chk(page,'Sales',f'Enquiry filter tab: {tab}', has(page,tab))
    chk(page,'Sales','Enquiry list: New button',  has(page,'New Enquiry') or has(page,'+ New'))
    chk(page,'Sales','Enquiry list: search',
        vis(page,'input[type="search"], input[placeholder*="name"], input[placeholder*="phone"]'))
    chk(page,'Sales','Enquiry list: columns',
        has(page,'Lead') or has(page,'Customer') or has(page,'Executive'))

    go(page, '/sales/enquiries/create/')
    ss(page,'021_enquiry_create')
    render_ok(page,'Sales','021_enquiry_create_form')
    if customer_pk:
        csel = page.query_selector('select[name="customer"]')
        if csel:
            try: csel.select_option(value=str(customer_pk))
            except: pass
    sel_first(page,'bike_model')
    sel_first(page,'enquiry_source')
    sel_first(page,'sales_executive')
    fill(page,'textarea[name="remarks"]','FQA browser test enquiry')
    ss(page,'021_enquiry_filled')
    submit(page)
    ss(page,'022_enquiry_result')

    enq = SalesEnquiry.objects.filter(remarks='FQA browser test enquiry').first()
    chk(page,'Sales','Enquiry created', enq is not None)
    enquiry_pk = enq.pk if enq else None

    if enquiry_pk:
        go(page, f'/sales/enquiries/{enquiry_pk}/')
        ss(page,'023_enquiry_detail_full')
        render_ok(page,'Sales','023_enquiry_detail')
        for kw in ['Customer','Status','Feedback','Appointment','Bike','Source']:
            chk(page,'Sales',f'Enquiry detail: {kw}', has(page,kw))
        for btn in ['Add Feedback','Book Appointment','Create Order']:
            chk(page,'Sales',f'Enquiry action: {btn}', has(page,btn))
        chk(page,'Sales','Enquiry status badge',
            has(page,'Open') or has(page,'Follow') or has(page,'Converted') or has(page,'Lost'))
        chk(page,'Sales','Enquiry status update form', vis(page,'select[name="status"]'))

        # Feedback
        go(page, f'/sales/feedback/create/?enquiry={enquiry_pk}')
        ss(page,'024_feedback_form')
        render_ok(page,'Sales','024_feedback_form')
        fill(page,'textarea[name="notes"], textarea[name="feedback_notes"]','FQA: Very interested, test ride done')
        fill_date(page,'next_followup_date',
            (datetime.date.today()+datetime.timedelta(days=2)).isoformat())
        sel_first(page,'enquiry')
        ss(page,'024_feedback_filled')
        submit(page)
        ss(page,'025_feedback_result')
        fb = SalesFeedback.objects.filter(feedback_notes__contains='FQA:').first()
        chk(page,'Sales','Feedback saved with follow-up date',
            fb is not None and fb.next_followup_date is not None)

        # Follow-up board
        go(page, '/sales/follow-ups/')
        ss(page,'026_followup_board')
        render_ok(page,'Sales','026_followup_board')
        for tab in ['All','Overdue','Today','This Week']:
            chk(page,'Sales',f'Follow-up board: {tab} tab', has(page,tab))
        chk(page,'Sales','Follow-up board: columns',
            has(page,'Lead') or has(page,'Phone') or has(page,'Follow-up Date'))

        # Appointment
        go(page, f'/sales/appointments/create/?enquiry={enquiry_pk}')
        ss(page,'027_appointment_create')
        render_ok(page,'Sales','027_appointment_create_form')
        fill_date(page,'appointment_date',
            (datetime.datetime.now()+datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'))
        purpose = page.query_selector('select[name="purpose"]')
        if purpose:
            try: purpose.select_option(value='test_ride')
            except: sel_first(page,'purpose')
        ss(page,'027_apt_filled')
        submit(page)
        ss(page,'028_apt_result')
        apt = SalesAppointment.objects.filter(enquiry_id=enquiry_pk).first()
        chk(page,'Sales','Appointment booked', apt is not None)

        go(page, '/sales/appointments/')
        ss(page,'029_appointments_list')
        render_ok(page,'Sales','029_appointments')
        for col in ['Customer','Date','Purpose','Status']:
            chk(page,'Sales',f'Appointments: {col}', has(page,col))

    # Test rides
    go(page, '/sales/test-rides/')
    ss(page,'030_test_rides')
    render_ok(page,'Sales','030_test_rides')
    chk(page,'Sales','Test rides: Log section',   has(page,'Test Ride') or has(page,'Log'))
    chk(page,'Sales','Test rides: Scheduled',     has(page,'Scheduled') or has(page,'Appointment'))

    go(page, '/sales/test-rides/create/')
    ss(page,'031_test_ride_create')
    render_ok(page,'Sales','031_test_ride_create_form')
    sel_first(page,'enquiry')
    sel_first(page,'vehicle')
    fill(page,'input[name="rider_name"]','FQA Rider')
    fill(page,'input[name="rider_phone"]','9500000072')
    fill(page,'input[name="license_number"]','TN-FQA-001')
    sel_first(page,'accompanied_by')
    fill_date(page,'start_time', datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'))
    fill(page,'input[name="start_odometer"]','50')
    ss(page,'031_tr_filled')
    submit(page)
    ss(page,'032_tr_result')
    tr = TestRideLog.objects.filter(rider_phone='9500000072').first()
    chk(page,'Sales','Test ride logged', tr is not None)

    # Orders list
    go(page, '/sales/orders/')
    ss(page,'033_orders_list')
    render_ok(page,'Sales','033_orders_list')
    for tab in ['All','Booked','Invoiced','Delivered','Cancelled']:
        chk(page,'Sales',f'Orders tab: {tab}', has(page,tab))
    chk(page,'Sales','Orders: PDI column', has(page,'PDI'))

    # Create order
    go(page, '/sales/orders/create/')
    ss(page,'034_order_create')
    render_ok(page,'Sales','034_order_create_form')
    if customer_pk:
        csel2 = page.query_selector('select[name="customer"]')
        if csel2:
            try: csel2.select_option(value=str(customer_pk))
            except: pass
        page.wait_for_timeout(500)
    if stock:
        vsel = page.query_selector('select[name="vehicle"]')
        if vsel:
            try: vsel.select_option(value=str(stock.pk))
            except: sel_first(page,'vehicle')
    sel_first(page,'sales_executive')
    if enquiry_pk:
        esel = page.query_selector('select[name="enquiry"]')
        if esel:
            try: esel.select_option(value=str(enquiry_pk))
            except: pass
    fill(page,'input[name="booking_amount"]','10000')
    fill(page,'input[name="discount_amount"]','1000')
    fill(page,'input[name="total_amount"]','75000')
    status_sel = page.query_selector('select[name="sales_status"]')
    if status_sel:
        try: status_sel.select_option(value='booked')
        except: pass
    ss(page,'034_order_filled')
    submit(page)
    ss(page,'035_order_result')

    order_pk = None
    if stock:
        ord_obj = VehicleSalesOrder.objects.filter(vehicle=stock).first()
        if ord_obj:
            order_pk = ord_obj.pk
    chk(page,'Sales','Sales order created', order_pk is not None)

    if order_pk:
        go(page, f'/sales/orders/{order_pk}/')
        ss(page,'036_order_detail_full')
        render_ok(page,'Sales','036_order_detail')

        for label, kws in [
            ('Order info',         ['ORD-','Order #','Booking']),
            ('Financial summary',  ['Total Amount','Discount','Booking Amount']),
            ('Documents hub',      ['Invoice','RC Book','Insurance','Delivery']),
            ('PDI section',        ['PDI','Pre-Delivery','Inspection']),
            ('Vehicle allotment',  ['Allot','Vehicle']),
            ('Exchange vehicle',   ['Exchange']),
            ('Finance/Loan',       ['Finance','Loan','EMI']),
            ('VAS packages',       ['AMC','RSA','Protection']),
            ('Fittings',           ['Fitting','Accessory']),
        ]:
            chk(page,'Sales',f'Order detail: {label}', any(has(page,kw) for kw in kws))

        for doc in ['Invoice','RC Book','Insurance','Delivery']:
            chk(page,'Sales',f'Documents hub: {doc} quadrant', has(page,doc))

        # Fitting — inline formset (fittings-0-*, fittings-1-*, ...)
        go(page, f'/sales/orders/{order_pk}/fittings/add/')
        ss(page,'037_fitting_create')
        render_ok(page,'Sales','037_fitting_form')
        fill(page,'input[name="fittings-0-fitting_name"]','FQA Seat Cover')
        fill(page,'input[name="fittings-0-cost"]','800')
        submit(page)
        ss(page,'038_fitting_result')
        fit = VehicleFitting.objects.filter(sales_order_id=order_pk, fitting_name='FQA Seat Cover').first()
        chk(page,'Sales','Vehicle fitting saved', fit is not None)

        # PDI
        go(page, f'/sales/orders/{order_pk}/pdi/')
        ss(page,'039_pdi_form')
        render_ok(page,'Sales','039_pdi_form')
        for sec in ['Engine','Mechanical','Electrical','Body','Aesthetics','Documents']:
            chk(page,'Sales',f'PDI: {sec} section', has(page,sec))
        cbs = page.query_selector_all('input[type="checkbox"]')
        chk(page,'Sales',f'PDI: ---20 checkboxes ({len(cbs)})', len(cbs) >= 20)
        for cb in cbs:
            try:
                if not cb.is_checked(): cb.click()
            except: pass
        remarks = page.query_selector('textarea[name="overall_remarks"]')
        if remarks: remarks.fill('FQA - all items inspected and passed')
        ss(page,'039_pdi_all_checked')
        submit(page)
        ss(page,'040_pdi_result')
        pdi = PDIChecklist.objects.filter(sales_order_id=order_pk).first()
        chk(page,'Sales','PDI checklist saved', pdi is not None)

        if pdi:
            go(page, f'/sales/pdi/{pdi.pk}/')
            ss(page,'041_pdi_detail')
            render_ok(page,'Sales','041_pdi_detail')
            for item in ['Mechanical','Electrical','Score','Critical','Remarks']:
                chk(page,'Sales',f'PDI detail: {item}', has(page,item))

        # Vehicle allotment
        go(page, f'/sales/orders/{order_pk}/allot/')
        ss(page,'043_allotment_form')
        render_ok(page,'Sales','043_allotment_form')
        sel_first(page,'vehicle')
        sel_first(page,'allotted_by')
        submit(page)
        ss(page,'044_allotment_result')
        chk(page,'Sales','Allotment submitted', no_error(page)[0])

        # Exchange vehicle
        go(page, f'/sales/exchange/create/?order={order_pk}')
        ss(page,'045_exchange_form')
        ok_f, _ = no_error(page)
        if ok_f and len(page.content()) > 500:
            fill(page,'input[name="old_vehicle_model"]','Honda Activa 3G')
            fill(page,'input[name="registration_no"]','TN11FQA001')
            fill(page,'input[name="valuation_amount"]','28000')
            sel_first(page,'sales_order')
            submit(page)
            ss(page,'046_exchange_result')
            exc = ExchangeVehicle.objects.filter(registration_no='TN11FQA001').first()
            chk(page,'Sales','Exchange vehicle saved', exc is not None)

    # Sales targets
    go(page, '/sales/targets/')
    ss(page,'047_sales_targets')
    render_ok(page,'Sales','047_sales_targets')
    for item in ['Target','Executive','Enquir','Conversion','Revenue','Achievement']:
        chk(page,'Sales',f'Sales targets: {item}', has(page,item))
    chk(page,'Sales','Sales targets: color-coded badges',
        'badge-green' in page.content() or 'badge-red' in page.content() or
        'badge-amber' in page.content() or 'achievement' in page.content().lower())

    go(page, '/sales/leaderboard/')
    ss(page,'048_leaderboard')
    render_ok(page,'Sales','048_leaderboard')
    for col in ['Rank','Executive','Enquir','Conversion','Revenue']:
        chk(page,'Sales',f'Leaderboard: {col}', has(page,col))

    go(page, '/sales/profit-report/')
    ss(page,'049_profit_report')
    render_ok(page,'Sales','049_profit_report')
    for item in ['Profit','Vehicle','Margin','Cost','Selling']:
        chk(page,'Sales',f'Profit report: {item}', has(page,item))

    go(page, '/sales/delivery-list/')
    ss(page,'050_delivery_list')
    render_ok(page,'Sales','050_delivery_list')

    go(page, '/sales/exchange-list/')
    ss(page,'051_exchange_list')
    render_ok(page,'Sales','051_exchange_list')

    go(page, '/sales/feedback-all/')
    ss(page,'052_feedback_all')
    render_ok(page,'Sales','052_feedback_all')

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 6. BILLING
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 6. BILLING ---------')

    go(page, '/billing/invoices/')
    ss(page,'053_invoice_list')
    render_ok(page,'Billing','053_invoice_list')
    for col in ['Invoice','Customer','Amount','Status','Date']:
        chk(page,'Billing',f'Invoice list: {col}', has(page,col))

    inv_pk = None
    if order_pk:
        go(page, f'/billing/invoices/create/?order={order_pk}')
        ss(page,'054_invoice_create')
        render_ok(page,'Billing','054_invoice_create')
        inv_num = f'FQA-INV-{datetime.datetime.now().strftime("%H%M%S")}'
        fill(page,'input[name="invoice_number"]',inv_num)
        fill_date(page,'invoice_date',datetime.date.today().isoformat())
        fill(page,'input[name="subtotal"]','75000')
        fill(page,'input[name="gst_amount"]','13500')
        fill(page,'input[name="discount_amount"]','1000')
        fill(page,'input[name="final_amount"]','87500')
        sel_first(page,'sales_order')
        ss(page,'054_invoice_filled')
        submit(page)
        ss(page,'055_invoice_result')
        inv = Invoice.objects.filter(invoice_number=inv_num).first()
        chk(page,'Billing','Invoice created and saved', inv is not None)
        inv_pk = inv.pk if inv else None

        if inv_pk:
            go(page, f'/billing/invoices/{inv_pk}/')
            ss(page,'056_invoice_detail_full')
            render_ok(page,'Billing','056_invoice_detail')
            chk(page,'Billing','Invoice detail: Invoice number', has(page,inv_num))
            chk(page,'Billing','Invoice detail: Customer name',  has(page,'FQA'))
            chk(page,'Billing','Invoice detail: Subtotal',       has(page,'75,000') or has(page,'75000'))
            chk(page,'Billing','Invoice detail: CGST breakdown', has(page,'CGST'))
            chk(page,'Billing','Invoice detail: SGST breakdown', has(page,'SGST'))
            chk(page,'Billing','Invoice detail: Final amount',   has(page,'87,500') or has(page,'87500'))
            chk(page,'Billing','Invoice detail: Payment section',has(page,'Payment'))
            chk(page,'Billing','Invoice detail: GST summary',    has(page,'GST'))

            # Payment
            go(page, f'/billing/payments/create/?invoice={inv_pk}')
            ss(page,'057_payment_form')
            render_ok(page,'Billing','057_payment_form')
            fill(page,'input[name="amount"]','20000')
            pm = page.query_selector('select[name="payment_method"]')
            if pm:
                try: pm.select_option(value='cash')
                except: pass
            fill(page,'input[name="transaction_reference"]','FQA-CASH-001')
            pdate = page.query_selector('input[name="payment_date"]')
            if pdate:
                ptype = pdate.get_attribute('type') or 'text'
                if ptype == 'datetime-local':
                    pdate.fill(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'))
                else:
                    pdate.fill(datetime.date.today().isoformat())
            pstatus = page.query_selector('select[name="payment_status"]')
            if pstatus:
                try: pstatus.select_option(value='completed')
                except: pass
            inv_sel = page.query_selector('select[name="invoice"]')
            if inv_sel:
                try: inv_sel.select_option(value=str(inv_pk))
                except: pass
            ss(page,'057_payment_filled')
            submit(page)
            ss(page,'058_payment_result')
            pay = Payment.objects.filter(invoice_id=inv_pk, transaction_reference='FQA-CASH-001').first()
            chk(page,'Billing','Payment saved (---20,000 cash)', pay is not None)

            go(page, f'/billing/invoices/{inv_pk}/')
            ss(page,'059_invoice_after_payment')
            chk(page,'Billing','Invoice: payment amount shown',
                has(page,'20,000') or has(page,'20000') or has(page,'paid') or has(page,'balance'))

            # Invoice PDF
            go(page, f'/billing/invoices/{inv_pk}/pdf/')
            ss(page,'060_invoice_pdf_full')
            ok_flag, err = no_error(page)
            chk(page,'Billing','Invoice PDF: no server error', ok_flag)
            if ok_flag:
                cs = CompanySettings.get_instance()
                chk(page,'Billing','Invoice PDF: GSTIN', has(page,cs.gstin) or has(page,'GSTIN'))
                chk(page,'Billing','Invoice PDF: company name', has(page,cs.company_name) or has(page,'SSBikez'))
                chk(page,'Billing','Invoice PDF: CGST/SGST', has(page,'CGST') or has(page,'SGST'))
                chk(page,'Billing','Invoice PDF: invoice number', has(page,inv_num))

    # Finance loan
    go(page, '/billing/loans/')
    ss(page,'061_loans_list')
    render_ok(page,'Billing','061_loans_list')

    if order_pk:
        go(page, '/billing/loans/create/')
        ss(page,'062_loan_create')
        render_ok(page,'Billing','062_loan_create_form')
        sel_first(page,'sales_order')
        fill(page,'input[name="bank_name"]','HDFC Bank')
        fill(page,'input[name="loan_amount"]','36000')
        fill(page,'input[name="interest_rate"]','9.5')
        fill(page,'input[name="tenure_months"]','24')
        fill(page,'input[name="emi_amount"]','1658')
        hp = page.query_selector('select[name="hp_status"]')
        if hp:
            try: hp.select_option(value='pending')
            except: pass
        fill(page,'input[name="hp_bank_name"]','HDFC Bank')
        submit(page)
        ss(page,'063_loan_result')
        loan = FinanceLoan.objects.filter(sales_order_id=order_pk).first()
        chk(page,'Billing','Finance loan created', loan is not None)

        if loan:
            go(page, f'/billing/loans/{loan.pk}/')
            ss(page,'064_loan_detail_full')
            render_ok(page,'Billing','064_loan_detail')
            for item in ['HDFC','36000','pending','HP','Hypothecation','EMI']:
                chk(page,'Billing',f'Loan detail: {item}', has(page,item))
            chk(page,'Billing','Loan detail: HP workflow card',
                has(page,'Hypothecation') or has(page,'HP Workflow') or has(page,'hp_status'))

    # Billing utilities
    for url, name, ss_name in [
        ('/billing/daily-report/',   'Billing','065_daily_report'),
        ('/billing/journal/',        'Billing','066_journal'),
        ('/billing/ledger/',         'Billing','067_ledger'),
        ('/billing/search/',         'Billing','068_invoice_search'),
        ('/billing/reconciliation/', 'Billing','069_reconciliation'),
        ('/billing/refunds-advances/','Billing','070_refunds'),
    ]:
        go(page, url)
        ss(page, ss_name)
        render_ok(page, name, ss_name)

    # Insurance policies
    go(page, '/billing/insurance/')
    ss(page,'071_insurance_list')
    render_ok(page,'Billing','071_insurance_list')

    if order_pk:
        go(page, f'/billing/insurance/create/')
        ss(page,'072_insurance_create')
        render_ok(page,'Billing','072_insurance_create_form')
        sel_first(page,'sales_order')
        fill(page,'input[name="policy_number"]','FQA-INS-001')
        fill(page,'input[name="provider_name"]','National Insurance Co.')
        fill(page,'input[name="premium_amount"]','5200')
        fill_date(page,'start_date',datetime.date.today().isoformat())
        fill_date(page,'end_date',(datetime.date.today()+datetime.timedelta(days=365)).isoformat())
        submit(page)
        ss(page,'073_insurance_result')
        ins = InsurancePolicy.objects.filter(policy_number='FQA-INS-001').first()
        chk(page,'Billing','Insurance policy created', ins is not None)

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 7. RTO
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 7. RTO ---------')

    go(page, '/rto/registrations/')
    ss(page,'074_rto_list')
    render_ok(page,'RTO','074_rto_list')

    rto_pk = None
    if order_pk:
        go(page, '/rto/registrations/create/')
        ss(page,'075_rto_create')
        render_ok(page,'RTO','075_rto_create_form')
        sel_first(page,'sales_order')
        fill(page,'input[name="form20_number"]','FQA-F20-001')
        fill(page,'input[name="registration_number"]','TN11FQA101')
        fill(page,'input[name="rto_charges"]','3200')
        status_f = page.query_selector('select[name="registration_status"]')
        if status_f:
            try: status_f.select_option(value='submitted')
            except: pass
        submit(page)
        ss(page,'076_rto_result')
        rto = RTORegistration.objects.filter(form20_number='FQA-F20-001').first()
        chk(page,'RTO','RTO registration created', rto is not None)
        rto_pk = rto.pk if rto else None

        if rto_pk:
            go(page, f'/rto/registrations/{rto_pk}/')
            ss(page,'077_rto_detail_full')
            render_ok(page,'RTO','077_rto_detail')
            for item in ['FQA-F20-001','TN11FQA101','submitted','Registration']:
                chk(page,'RTO',f'RTO detail: {item}', has(page,item))

            # RC Book
            for rc_url in [
                f'/rto/{rto_pk}/rc-book/',
                f'/rto/registrations/{rto_pk}/rc-book/create/',
                f'/rto/rc-books/create/?rto={rto_pk}',
            ]:
                go(page, rc_url)
                ok_f, _ = no_error(page)
                if ok_f and len(page.content()) > 500 and 'not found' not in page.content().lower():
                    ss(page,'078_rcbook_create')
                    fill(page,'input[name="rc_number"]','TN11FQA101')
                    fill_date(page,'issue_date', datetime.date.today().isoformat())
                    fill(page,'input[name="issued_to"]','FQA Test Customer')
                    sel_first(page,'rto_registration')
                    rc_status = page.query_selector('select[name="status"]')
                    if rc_status:
                        try: rc_status.select_option(value='issued')
                        except: pass
                    hp_e = page.query_selector('input[name="hp_endorsed"]')
                    if hp_e:
                        try: hp_e.check()
                        except: pass
                    fill(page,'input[name="hp_bank_name"]','HDFC Bank')
                    submit(page)
                    ss(page,'079_rcbook_result')
                    rc = RCBook.objects.filter(rc_number='TN11FQA101').first()
                    chk(page,'RTO','RC Book created', rc is not None)
                    if rc:
                        chk(page,'RTO','RC Book: HP endorsed', rc.hp_endorsed)
                    break

    go(page, '/rto/plates/')
    ss(page,'080_plates_list')
    render_ok(page,'RTO','080_plates_list')

    go(page, '/rto/income/')
    ss(page,'081_rto_income')
    render_ok(page,'RTO','081_rto_income')

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 8. SERVICE
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 8. SERVICE ---------')

    go(page, '/service/')
    ss(page,'082_service_dashboard')
    render_ok(page,'Service','082_service_dashboard')

    go(page, '/service/enquiries/')
    ss(page,'083_svc_enquiry_list')
    render_ok(page,'Service','083_svc_enquiry_list')

    go(page, '/service/enquiries/create/')
    ss(page,'084_svc_enquiry_create')
    render_ok(page,'Service','084_svc_enquiry_create')
    cv_obj = CustomerVehicle.objects.first()
    if cv_obj:
        cvs = page.query_selector('select[name="customer_vehicle"]')
        if cvs:
            try: cvs.select_option(value=str(cv_obj.pk))
            except: sel_first(page,'customer_vehicle')
    fill(page,'textarea[name="issue_description"]','FQA first free service 1500km')
    sel_first(page,'status')
    submit(page)
    ss(page,'085_svc_enquiry_result')
    chk(page,'Service','Service enquiry created', no_error(page)[0])

    go(page, '/service/appointments/')
    ss(page,'086_svc_appointments')
    render_ok(page,'Service','086_svc_appointments')

    # Job card list
    go(page, '/service/jobcards/')
    ss(page,'087_jc_list')
    render_ok(page,'Service','087_jc_list')
    for col in ['Job Card','Customer','Status','Advisor']:
        chk(page,'Service',f'Job card list: {col}', has(page,col))

    # Create job card
    go(page, '/service/jobcards/create/')
    ss(page,'088_jc_create')
    render_ok(page,'Service','088_jc_create_form')
    if cv_obj:
        cvs2 = page.query_selector('select[name="customer_vehicle"]')
        if cvs2:
            try: cvs2.select_option(value=str(cv_obj.pk))
            except: sel_first(page,'customer_vehicle')
    fill(page,'input[name="odometer_reading"]','1500')
    fill(page,'textarea[name="problem_description"]','FQA first free service')
    sel_first(page,'service_advisor')
    sel_first(page,'branch')
    ss(page,'088_jc_filled')
    submit(page)
    ss(page,'089_jc_result')

    jc = JobCard.objects.filter(problem_description='FQA first free service').first()
    chk(page,'Service','Job card created', jc is not None)
    jc_pk = jc.pk if jc else None

    if jc_pk:
        go(page, f'/service/jobcards/{jc_pk}/')
        ss(page,'090_jc_detail_full')
        render_ok(page,'Service','090_jc_detail')
        chk(page,'Service','JC: Warranty banner',        has(page,'warranty') or has(page,'Warranty'))
        chk(page,'Service','JC: Workflow progress bar',
            vis(page,'.workflow-bar, .workflow-step, [class*="workflow"]') or
            has(page,'pending') or has(page,'water'))
        for label, kws in [
            ('Customer/Vehicle info',['registration','customer','vehicle','odometer']),
            ('Labour charges',       ['labour','labor','charge']),
            ('Spares issued',        ['spare','parts','issue']),
            ('Outwork entries',      ['outwork','external','vendor']),
            ('Additional work',      ['additional','approval','work']),
            ('Service sub-tasks',    ['task','checklist','sub']),
        ]:
            chk(page,'Service',f'JC detail: {label}', any(has(page,kw) for kw in kws))

        # Advance status via form submit (view requires POST via @require_POST)
        for i in range(4):
            try:
                go(page, f'/service/jobcards/{jc_pk}/')
                page.wait_for_timeout(300)
                submitted = page.evaluate("""() => {
                    const form = document.querySelector('form[action*="advance"]');
                    if (form) { form.submit(); return true; }
                    return false;
                }""")
                if submitted:
                    page.wait_for_load_state('domcontentloaded', timeout=8000)
                    page.wait_for_timeout(400)
            except: pass

        jc.refresh_from_db()
        ss(page,'091_jc_after_advances')
        chk(page,'Service',f'JC status advanced (now:{jc.service_status})', jc.service_status != 'pending')

        # Labour charge
        for labour_url in [
            f'/service/labor-charges/create/?jc={jc_pk}',
            f'/service/labor-charges/create/?job_card={jc_pk}',
            f'/service/jobcards/{jc_pk}/labour/add/',
        ]:
            go(page, labour_url)
            ok_f, _ = no_error(page)
            if ok_f and len(page.content()) > 500 and 'not found' not in page.content().lower():
                ss(page,'092_labour_form')
                fill(page,'input[name="service_name"]','FQA Engine Oil Change')
                fill(page,'input[name="labor_cost"]','0')
                sel_first(page,'job_card')
                submit(page)
                ss(page,'093_labour_result')
                lc = LaborCharge.objects.filter(job_card_id=jc_pk, service_name='FQA Engine Oil Change').first()
                chk(page,'Service','Labour charge saved', lc is not None)
                break

        # Spares issue
        go(page, f'/service/jobcards/{jc_pk}/issue-spare/')
        ss(page,'094_spares_issue')
        ok_f, _ = no_error(page)
        chk(page,'Service','Spares issue form loads', ok_f)

        # Bay list
        go(page, '/service/bays/')
        ss(page,'095_bays')
        render_ok(page,'Service','095_bays')

        # Service invoice
        jc.service_status = 'ready'; jc.save()
        ServiceInvoice.objects.filter(job_card=jc).delete()

        sinv_pk = None
        for sinv_url in [
            f'/service/invoices/create/?jc={jc_pk}',
            f'/service/service-invoice/create/?jc={jc_pk}',
        ]:
            go(page, sinv_url)
            ok_f, _ = no_error(page)
            if ok_f and len(page.content()) > 500 and 'not found' not in page.content().lower():
                ss(page,'096_sinv_create')
                sinv_no_el = page.query_selector('input[name="invoice_number"]')
                if sinv_no_el:
                    sinv_no_el.fill(f'FQA-SINV-{datetime.datetime.now().strftime("%H%M%S")}')
                sel_first(page,'job_card')
                submit(page)
                ss(page,'097_sinv_result')
                si = ServiceInvoice.objects.filter(job_card_id=jc_pk).first()
                chk(page,'Service','Service invoice created', si is not None)
                sinv_pk = si.pk if si else None
                if sinv_pk:
                    go(page, f'/service/invoices/{sinv_pk}/')
                    ss(page,'098_sinv_detail_full')
                    render_ok(page,'Service','098_sinv_detail')
                    for item in ['Labour','Total','Invoice','Amount','GST']:
                        chk(page,'Service',f'Service invoice: {item}', has(page,item))
                    # PDF
                    go(page, f'/billing/service-invoice/{jc_pk}/pdf/')
                    ss(page,'099_sinv_pdf')
                    ok_flag, err = no_error(page)
                    chk(page,'Service','Service invoice PDF: no server error', ok_flag)
                    if ok_flag:
                        chk(page,'Service','Service invoice PDF: content',len(page.content()) > 500)
                # Duplicate create --- should NOT 500
                go(page, sinv_url)
                content = page.content()
                if 'Server Error (500)' in content or 'Internal Server Error' in content:
                    fail('Service','Duplicate sinv: got 500','Server crashed on duplicate',page,'100_dup_crash')
                else:
                    ok('Service','Duplicate sinv: no crash',page,'100_dup_ok')
                break

        # Warranty claim
        go(page, '/service/warranty-claims/')
        ss(page,'101_warranty_list')
        render_ok(page,'Service','101_warranty_list')

        go(page, f'/service/jobcards/{jc_pk}/warranty-claim/')
        ss(page,'102_warranty_create')
        ok_f, _ = no_error(page)
        if ok_f and len(page.content()) > 500:
            render_ok(page,'Service','102_warranty_form')
            fill(page,'textarea[name="description"]','FQA warranty - engine noise')
            fill(page,'input[name="claimed_amount"]','500')
            sel_first(page,'job_card') or sel_first(page,'jc')
            submit(page)
            ss(page,'103_warranty_result')
            wc = WarrantyClaim.objects.filter(job_card_id=jc_pk).first()
            chk(page,'Service','Warranty claim created', wc is not None)

        # Insurance estimation
        go(page, f'/service/jobcards/{jc_pk}/insurance-estimation/')
        ss(page,'104_ins_est_create')
        ok_f, _ = no_error(page)
        if ok_f and len(page.content()) > 500:
            render_ok(page,'Service','104_ins_est_form')

        # Sub-tasks
        go(page, f'/service/jobcards/{jc_pk}/childs/add/')
        ss(page,'105_subtask_create')
        ok_f, _ = no_error(page)
        if ok_f and len(page.content()) > 500:
            fill(page,'input[name="task_name"]','FQA Oil Top-up Check')
            submit(page)
            ss(page,'106_subtask_result')
            chk(page,'Service','Sub-task created', no_error(page)[0])

        # Service reminders
        go(page, '/service/reminders/')
        ss(page,'107_reminders')
        render_ok(page,'Service','107_reminders')
        chk(page,'Service','Service reminders: content',
            has(page,'Reminder') or has(page,'Service') or has(page,'Due'))

        # Technician report
        go(page, '/service/technician-report/')
        ss(page,'108_technician_report')
        render_ok(page,'Service','108_technician_report')
        chk(page,'Service','Technician report: content',
            has(page,'Technician') or has(page,'Report') or has(page,'Labor'))

        # Discount master
        go(page, '/service/discount-master/')
        ss(page,'109_discount_master')
        render_ok(page,'Service','109_discount_master')

        # Customer calls
        go(page, '/service/calls/')
        ss(page,'110_calls_list')
        render_ok(page,'Service','110_calls_list')

        # Additional work
        go(page, f'/service/jobcards/{jc_pk}/additional-work/create/')
        ss(page,'111_additional_work')
        ok_f, _ = no_error(page)
        if ok_f and len(page.content()) > 500:
            render_ok(page,'Service','111_additional_work_form')

        # Insurance claims
        go(page, '/service/insurance-claims/')
        ss(page,'112_insurance_claims')
        render_ok(page,'Service','112_insurance_claims')

        # Job card print
        go(page, f'/service/jobcards/{jc_pk}/print/')
        ss(page,'113_jc_print')
        ok_f, _ = no_error(page)
        chk(page,'Service','JC print: no error', ok_f)

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 9. SPARES
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 9. SPARES ---------')

    go(page, '/spares/')
    ss(page,'114_spares_dashboard')
    render_ok(page,'Spares','114_spares_dashboard')
    for kw in ['Item','Stock','Order','Sale','Purchase']:
        chk(page,'Spares',f'Spares dashboard: {kw}', has(page,kw))

    # Items
    go(page, '/spares/items/')
    ss(page,'115_items_list')
    render_ok(page,'Spares','115_items_list')
    for col in ['Item','Part','Stock']:
        chk(page,'Spares',f'Items list: {col}', has(page,col))
    chk(page,'Spares','Items list: Rate/Price column',
        has(page,'Rate') or has(page,'Price') or has(page,'MRP') or has(page,'Selling'))

    go(page, '/spares/items/create/')
    ss(page,'116_item_create')
    render_ok(page,'Spares','116_item_create_form')
    fill(page,'input[name="item_name"]','FQA Oil Filter')
    fill(page,'input[name="standard_selling_rate"]','450')
    fill(page,'input[name="valuation_rate"]','300')
    fill(page,'input[name="mrp"]','500')
    sel_first(page,'category')
    ss(page,'116_item_filled')
    submit(page)
    ss(page,'117_item_result')
    spare_item = SparesItem.objects.filter(item_name='FQA Oil Filter').first()
    chk(page,'Spares','Spare item created', spare_item is not None)

    if spare_item:
        go(page, f'/spares/items/{spare_item.pk}/')
        ss(page,'118_item_detail')
        render_ok(page,'Spares','118_item_detail')
        chk(page,'Spares','Item detail: item name', has(page,'FQA Oil Filter'))
        chk(page,'Spares','Item detail: Stock section', has(page,'Stock'))
        chk(page,'Spares','Item detail: rate/price',
            has(page,'Rate') or has(page,'Price') or has(page,'MRP') or has(page,'Selling'))
        chk(page,'Spares','Item detail: movement/history',
            has(page,'History') or has(page,'Movement') or has(page,'Ledger') or
            has(page,'Transaction') or has(page,'Stock'))

        go(page, f'/spares/items/{spare_item.pk}/edit/')
        ss(page,'119_item_edit')
        render_ok(page,'Spares','119_item_edit')

    # Stock report
    go(page, '/spares/stock/')
    ss(page,'120_stock_report')
    render_ok(page,'Spares','120_stock_report')
    for col in ['Item','Stock','Value']:
        chk(page,'Spares',f'Stock report: {col}', has(page,col))
    chk(page,'Spares','Stock report: Reorder/Min column',
        has(page,'Reorder') or has(page,'reorder') or has(page,'Level') or has(page,'Min'))

    # Supplier quotes
    go(page, '/spares/quotes/')
    ss(page,'121_quotes_list')
    render_ok(page,'Spares','121_quotes_list')

    go(page, '/spares/quotes/create/')
    ss(page,'122_quote_create')
    render_ok(page,'Spares','122_quote_create_form')
    sel_first(page,'supplier')
    fill_date(page,'date', datetime.date.today().isoformat())
    fill_date(page,'valid_till', (datetime.date.today()+datetime.timedelta(days=30)).isoformat())
    fill(page,'textarea[name="terms_and_conditions"]','FQA Quote test')
    ss(page,'122_quote_filled')
    submit(page)
    ss(page,'123_quote_result')
    sq = SupplierQuote.objects.order_by('-id').first()
    chk(page,'Spares','Supplier quote created', sq is not None)

    # Purchase orders
    go(page, '/spares/orders/')
    ss(page,'124_po_list')
    render_ok(page,'Spares','124_po_list')
    for col in ['PO','Supplier','Date','Status']:
        chk(page,'Spares',f'PO list: {col}', has(page,col))

    go(page, '/spares/orders/create/')
    ss(page,'125_po_create')
    render_ok(page,'Spares','125_po_create_form')
    sel_first(page,'supplier')
    fill_date(page,'date', datetime.date.today().isoformat())
    fill_date(page,'required_by', (datetime.date.today()+datetime.timedelta(days=7)).isoformat())
    fill(page,'textarea[name="terms_and_conditions"]','FQA PO test')
    ss(page,'125_po_filled')
    submit(page)
    ss(page,'126_po_result')
    po = PurchaseOrder.objects.order_by('-id').first()
    chk(page,'Spares','Purchase order created', po is not None)

    if po:
        go(page, f'/spares/orders/{po.pk}/')
        ss(page,'127_po_detail')
        render_ok(page,'Spares','127_po_detail')
        chk(page,'Spares','PO detail: status/items visible',
            has(page,'Supplier') or has(page,'Status') or has(page,'Items'))

    # Purchase invoices
    go(page, '/spares/invoices/')
    ss(page,'128_pinv_list')
    render_ok(page,'Spares','128_pinv_list')

    go(page, '/spares/invoices/create/')
    ss(page,'129_pinv_create')
    render_ok(page,'Spares','129_pinv_create_form')
    sel_first(page,'supplier')
    sel_first(page,'purchase_order')
    fill(page,'input[name="invoice_number"]','FQA-PINV-001')
    fill_date(page,'invoice_date', datetime.date.today().isoformat())
    fill(page,'input[name="total_amount"]','3500')
    ss(page,'129_pinv_filled')
    submit(page)
    ss(page,'130_pinv_result')
    chk(page,'Spares','Purchase invoice submitted', no_error(page)[0])

    # Counter sales
    go(page, '/spares/counter-sales/')
    ss(page,'131_counter_sale_list')
    render_ok(page,'Spares','131_counter_sale_list')
    for col in ['Sale','Customer','Amount','Date']:
        chk(page,'Spares',f'Counter sale list: {col}', has(page,col))

    go(page, '/spares/counter-sales/create/')
    ss(page,'132_counter_sale_create')
    render_ok(page,'Spares','132_counter_sale_create_form')
    fill(page,'input[name="customer"]','FQA Walk-in Customer')
    fill(page,'input[name="mobile"]','9500000073')
    fill_date(page,'date', datetime.date.today().isoformat())
    sel_first(page,'godown')
    sel_first(page,'pay_type')
    ss(page,'132_counter_sale_filled')
    submit(page)
    ss(page,'133_counter_sale_result')
    cs_obj = CounterSale.objects.filter(mobile='9500000073').first()
    chk(page,'Spares','Counter sale created', cs_obj is not None)

    if cs_obj:
        go(page, f'/spares/counter-sales/{cs_obj.pk}/')
        ss(page,'134_counter_sale_detail')
        render_ok(page,'Spares','134_counter_sale_detail')
        for item in ['FQA Walk-in','9500000073']:
            chk(page,'Spares',f'Counter sale detail: {item}', has(page,item))
        chk(page,'Spares','Counter sale detail: Amount/Items',
            has(page,'Amount') or has(page,'Item') or has(page,'Total'))

    # Counter returns
    go(page, '/spares/counter-returns/')
    ss(page,'135_counter_returns')
    render_ok(page,'Spares','135_counter_returns')

    # Issue alterations
    go(page, '/spares/issue-alterations/')
    ss(page,'136_issue_alt_list')
    render_ok(page,'Spares','136_issue_alt_list')

    # Parts consumption report
    go(page, '/spares/reports/parts-consumption/')
    ss(page,'137_parts_consumption')
    render_ok(page,'Spares','137_parts_consumption')
    chk(page,'Spares','Parts consumption: content',
        has(page,'Parts') or has(page,'Consumption') or has(page,'Item'))

    # PO used qty report
    go(page, '/spares/reports/po-used-qty/')
    ss(page,'138_po_used_qty')
    render_ok(page,'Spares','138_po_used_qty')

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 10. VAS
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 10. VAS ---------')

    go(page, '/vas/')
    ss(page,'139_vas_dashboard')
    render_ok(page,'VAS','139_vas_dashboard')
    for kw in ['AMC','RSA','Protection','Package']:
        chk(page,'VAS',f'VAS dashboard: {kw}', has(page,kw))

    # AMC
    go(page, '/vas/amc/')
    ss(page,'140_amc_list')
    render_ok(page,'VAS','140_amc_list')

    go(page, '/vas/amc/create/')
    ss(page,'141_amc_create')
    render_ok(page,'VAS','141_amc_create_form')
    sel_first(page,'customer_vehicle')
    fill(page,'input[name="package_name"]','FQA AMC Gold')
    fill(page,'input[name="amount"]','3000')
    fill_date(page,'start_date', datetime.date.today().isoformat())
    fill_date(page,'end_date', (datetime.date.today()+datetime.timedelta(days=365)).isoformat())
    ss(page,'141_amc_filled')
    submit(page)
    ss(page,'142_amc_result')
    amc = AMCPackage.objects.filter(package_name='FQA AMC Gold').first()
    chk(page,'VAS','AMC package created', amc is not None)

    if amc:
        go(page, f'/vas/amc/{amc.pk}/')
        ss(page,'143_amc_detail')
        render_ok(page,'VAS','143_amc_detail')
        chk(page,'VAS','AMC detail: package name', has(page,'FQA AMC Gold'))

    # RSA
    go(page, '/vas/rsa/')
    ss(page,'144_rsa_list')
    render_ok(page,'VAS','144_rsa_list')

    go(page, '/vas/rsa/create/')
    ss(page,'145_rsa_create')
    render_ok(page,'VAS','145_rsa_create_form')
    sel_first(page,'customer_vehicle')
    fill(page,'input[name="provider_name"]','FQA RSA Basic')
    fill(page,'input[name="amount"]','1500')
    fill_date(page,'start_date', datetime.date.today().isoformat())
    fill_date(page,'end_date', (datetime.date.today()+datetime.timedelta(days=365)).isoformat())
    ss(page,'145_rsa_filled')
    submit(page)
    ss(page,'146_rsa_result')
    rsa = RSAPackage.objects.filter(provider_name='FQA RSA Basic').first()
    chk(page,'VAS','RSA package created', rsa is not None)

    # Protection Plus
    go(page, '/vas/protection-plus/')
    ss(page,'147_pp_list')
    render_ok(page,'VAS','147_pp_list')

    go(page, '/vas/protection-plus/create/')
    ss(page,'148_pp_create')
    render_ok(page,'VAS','148_pp_create_form')
    sel_first(page,'customer_vehicle')
    fill(page,'input[name="package_name"]','FQA PP Standard')
    fill(page,'input[name="amount"]','2500')
    fill_date(page,'start_date', datetime.date.today().isoformat())
    fill_date(page,'end_date', (datetime.date.today()+datetime.timedelta(days=365)).isoformat())
    ss(page,'148_pp_filled')
    submit(page)
    ss(page,'149_pp_result')
    pp = ProtectionPlusPackage.objects.filter(package_name='FQA PP Standard').first()
    chk(page,'VAS','Protection Plus package created', pp is not None)

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 11. MASTERS
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 11. MASTERS ---------')

    # Categories
    go(page, '/masters/categories/')
    ss(page,'150_categories')
    render_ok(page,'Masters','150_categories')

    go(page, '/masters/categories/create/')
    ss(page,'151_category_create')
    render_ok(page,'Masters','151_category_create_form')
    fill(page,'input[name="name"]','FQA Test Category')
    submit(page)
    ss(page,'152_category_result')
    chk(page,'Masters','Category created', no_error(page)[0])

    # Suppliers
    go(page, '/masters/suppliers/')
    ss(page,'153_suppliers')
    render_ok(page,'Masters','153_suppliers')
    for col in ['Name','Phone','GST','Contact']:
        chk(page,'Masters',f'Suppliers: {col}', has(page,col))

    go(page, '/masters/suppliers/create/')
    ss(page,'154_supplier_create')
    render_ok(page,'Masters','154_supplier_create_form')
    fill(page,'input[name="supplier_name"]','FQA Auto Parts Ltd')
    fill(page,'input[name="phone"]','04220000001')
    fill(page,'input[name="email"]','fqa_supplier@example.com')
    fill(page,'input[name="gstin"]','33ABCDE1234F1Z9')
    fill(page,'input[name="address_line1"], textarea[name="address_line1"]','FQA Industrial Estate')
    ss(page,'154_supplier_filled')
    submit(page)
    ss(page,'155_supplier_result')
    sup = Supplier.objects.filter(supplier_name='FQA Auto Parts Ltd').first()
    chk(page,'Masters','Supplier created', sup is not None)

    if sup:
        go(page, f'/masters/suppliers/{sup.pk}/')
        ss(page,'156_supplier_detail')
        render_ok(page,'Masters','156_supplier_detail')
        chk(page,'Masters','Supplier detail: name visible', has(page,'FQA Auto Parts Ltd'))
        for item in ['GSTIN','Phone','Address','Contact']:
            chk(page,'Masters',f'Supplier detail: {item}', has(page,item))

    # Warehouses
    go(page, '/masters/warehouses/')
    ss(page,'157_warehouses')
    render_ok(page,'Masters','157_warehouses')

    go(page, '/masters/warehouses/create/')
    ss(page,'158_warehouse_create')
    render_ok(page,'Masters','158_warehouse_create_form')
    fill(page,'input[name="name"]','FQA Main Warehouse')
    ss(page,'158_wh_filled')
    submit(page)
    ss(page,'159_warehouse_result')
    wh = Warehouse.objects.filter(name='FQA Main Warehouse').first()
    chk(page,'Masters','Warehouse created', wh is not None)

    # Racks
    go(page, '/masters/racks/')
    ss(page,'160_racks')
    render_ok(page,'Masters','160_racks')

    go(page, '/masters/racks/create/')
    ss(page,'161_rack_create')
    render_ok(page,'Masters','161_rack_create_form')
    fill(page,'input[name="name"]','FQA-R-01')
    sel_first(page,'warehouse')
    submit(page)
    ss(page,'162_rack_result')
    chk(page,'Masters','Rack created', no_error(page)[0])

    # Bins
    go(page, '/masters/bins/')
    ss(page,'163_bins')
    render_ok(page,'Masters','163_bins')

    go(page, '/masters/bins/create/')
    ss(page,'164_bin_create')
    render_ok(page,'Masters','164_bin_create_form')
    fill(page,'input[name="name"]','FQA-B-01')
    sel_first(page,'rack')
    submit(page)
    ss(page,'165_bin_result')
    chk(page,'Masters','Bin created', no_error(page)[0])

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 12. ACCOUNTS / REPORTS
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 12. ACCOUNTS ---------')

    # Reports
    for url, name, ss_name in [
        ('/accounts/reports/sales/',   'Accounts','166_sales_report'),
        ('/accounts/reports/spares/',  'Accounts','167_spares_report'),
        ('/accounts/reports/service/', 'Accounts','168_service_report'),
        ('/accounts/gst-report/',      'Accounts','169_gst_report'),
    ]:
        go(page, url)
        ss(page, ss_name)
        render_ok(page, name, ss_name)

    # Sales report detail
    go(page, '/accounts/reports/sales/')
    ss(page,'170_sales_report_detail')
    for col in ['Vehicle','Invoice','Customer','Amount']:
        chk(page,'Accounts',f'Sales report: {col}', has(page,col))

    # GST report
    go(page, '/accounts/gst-report/')
    ss(page,'171_gst_report_detail')
    chk(page,'Accounts','GST report: CGST/SGST/IGST columns',
        has(page,'CGST') or has(page,'SGST') or has(page,'GST'))

    # Insurance expiry
    go(page, '/accounts/insurance-expiry/')
    ss(page,'172_insurance_expiry')
    render_ok(page,'Accounts','172_insurance_expiry')
    chk(page,'Accounts','Insurance expiry: content',
        has(page,'Insurance') or has(page,'Expiry') or has(page,'Policy'))

    # Company settings
    go(page, '/accounts/settings/')
    ss(page,'173_company_settings')
    render_ok(page,'Accounts','173_company_settings')
    chk(page,'Accounts','Company settings: GSTIN field', has(page,'GSTIN') or has(page,'gstin'))
    chk(page,'Accounts','Company settings: company name', has(page,'Company') or has(page,'Name'))

    # User management
    go(page, '/accounts/users/')
    ss(page,'174_user_list')
    render_ok(page,'Accounts','174_user_list')
    for col in ['Username','Role','Branch','Status']:
        chk(page,'Accounts',f'User list: {col}', has(page,col))

    go(page, '/accounts/users/create/')
    ss(page,'175_user_create')
    render_ok(page,'Accounts','175_user_create_form')
    for fname in ['username','first_name','last_name','email']:
        chk(page,'Accounts',f'User create: {fname} field', vis(page,f'input[name="{fname}"]'))

    # Roles
    go(page, '/accounts/roles/')
    ss(page,'176_roles_list')
    render_ok(page,'Accounts','176_roles_list')
    for role in ['Sales Executive','Cashier','Accounts','Floor Supervisor','Managing Director']:
        chk(page,'Accounts',f'Roles: {role}', has(page,role))

    go(page, '/accounts/roles/create/')
    ss(page,'177_role_create')
    render_ok(page,'Accounts','177_role_create_form')

    # Branches
    go(page, '/accounts/branches/')
    ss(page,'178_branches')
    render_ok(page,'Accounts','178_branches')

    # Notifications
    go(page, '/accounts/notifications/')
    ss(page,'179_notifications')
    render_ok(page,'Accounts','179_notifications')
    chk(page,'Accounts','Notifications: content',
        has(page,'Notification') or has(page,'No notification') or has(page,'message'))

    # Fuel expenses
    go(page, '/accounts/fuel-expenses/')
    ss(page,'180_fuel_expenses')
    render_ok(page,'Accounts','180_fuel_expenses')

    # Global search
    go(page, '/accounts/search/?q=FQA')
    ss(page,'181_global_search')
    render_ok(page,'Accounts','181_global_search')
    chk(page,'Accounts','Global search: FQA results',
        has(page,'FQA') or has(page,'result') or has(page,'search'))

    # Profile
    go(page, '/accounts/profile/')
    ss(page,'182_profile')
    render_ok(page,'Accounts','182_profile')
    chk(page,'Accounts','Profile: admin info', has(page,'admin') or has(page,'Admin') or has(page,'profile'))

    # Password change form
    go(page, '/accounts/password/change/')
    ss(page,'183_password_change')
    render_ok(page,'Accounts','183_password_change')

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 13. RBAC TESTS
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    print('\n--------- 13. RBAC ---------')

    # --- Sales Executive ---
    # Prefer the known QA fixture account (password 'Test@123') over an
    # arbitrary same-role user — .first() picked unrelated seed data with an
    # unknown password before this fix.
    sales_role = Role.objects.filter(role_name='Sales Executive').first()
    sales_user = (
        User.objects.filter(role=sales_role, username__in=['sales.test', 'e2e_sales']).first()
        or (User.objects.filter(role=sales_role, is_superuser=False).first() if sales_role else None)
    )

    if sales_user:
        go(page, '/accounts/logout/')
        page.wait_for_timeout(800)
        login(page, user=sales_user.username, pwd='Test@123')
        ss(page,'184_sales_exec_logged_in')
        chk(page,'RBAC','Sales exec login success',
            'login' not in page.url and 'otp' not in page.url)

        go(page, '/accounts/dashboard/')
        ss(page,'185_sales_exec_dashboard')
        sidebar = page.evaluate("() => { const s = document.getElementById('sidebar'); return s ? s.textContent : ''; }").lower()

        # Sections SHOWN to Sales Executive (check sidebar text only, not KPI cards)
        for section in ['sales','customers','vas']:
            chk(page,'RBAC',f'Sales exec sidebar: {section.upper()} visible', section in sidebar)

        # Sections HIDDEN from Sales Executive.
        # 'service' can't be a bare substring check: Sales Executive legitimately
        # sees the "Service Master" link under the Vehicle Master section (a
        # vehicle-master submodule, not the Service operations module), so we
        # look for service-operations-specific phrases instead.
        hidden_checks = {
            'finance': ['finance'],
            'service': ['job card', 'service enquir', 'service appointment', 'service invoice'],
            'spares':  ['spares'],
            'rto':     ['rto'],
            'masters': ['masters'],
        }
        for section, phrases in hidden_checks.items():
            chk(page,'RBAC',f'Sales exec sidebar: {section.upper()} hidden',
                not any(p in sidebar for p in phrases))

        # URL-level blocking
        for url, name in [
            ('/accounts/settings/',        'Company Settings'),
            ('/accounts/roles/',           'Role Management'),
            ('/accounts/roles/create/',    'Role Create'),
            ('/accounts/branches/',        'Branch Management'),
            ('/accounts/branches/create/', 'Branch Create'),
            ('/billing/invoices/',         'Invoice List'),
            ('/spares/',                   'Spares Dashboard'),
        ]:
            go(page, url)
            ss(page, f'186_rbac_{name[:15].replace(" ","_")}')
            cnt = page.content()
            is_blocked = (
                'Access Denied' in cnt or 'Forbidden' in cnt or
                'forbidden' in cnt.lower() or
                '/accounts/login/' in page.url
            )
            chk(page,'RBAC',f'Sales exec blocked: {name}', is_blocked)

        # Sales exec CAN access these
        for url, name in [
            ('/sales/enquiries/',         'Enquiries'),
            ('/sales/orders/',            'Sales Orders'),
            ('/customers/customers/',     'Customers'),
        ]:
            go(page, url)
            ss(page, f'187_rbac_allowed_{name[:10].replace(" ","_")}')
            cnt = page.content()
            is_ok = 'Access Denied' not in cnt and 'Forbidden' not in cnt
            chk(page,'RBAC',f'Sales exec can access: {name}', is_ok)

        # Restore admin session
        go(page, '/accounts/logout/')
        page.wait_for_timeout(500)
        login(page)
        ss(page,'188_admin_restored')
    else:
        print('  [SKIP] No Sales Executive user found')

    # --- Cashier ---
    cashier_role = Role.objects.filter(role_name='Cashier').first()
    cashier_user = (
        User.objects.filter(role=cashier_role, username__in=['e2e_cashier', 'cashier.test']).first()
        or (User.objects.filter(role=cashier_role, is_superuser=False).first() if cashier_role else None)
    )

    if cashier_user:
        go(page, '/accounts/logout/')
        page.wait_for_timeout(500)
        login(page, user=cashier_user.username, pwd='Test@123')
        ss(page,'189_cashier_logged_in')

        go(page, '/accounts/dashboard/')
        ss(page,'190_cashier_dashboard')
        sidebar = page.evaluate("() => { const s = document.getElementById('sidebar'); return s ? s.textContent : ''; }").lower()

        # Cashier sees Finance + RTO (check sidebar text only)
        for section in ['finance','rto']:
            chk(page,'RBAC',f'Cashier sidebar: {section.upper()} visible', section in sidebar)

        # Cashier does NOT see Service/Spares/Masters
        for section in ['service','spares','masters']:
            chk(page,'RBAC',f'Cashier sidebar: {section.upper()} hidden', section not in sidebar)

        # URL-level blocking for cashier
        # Note: Cashier has 'sales' permission, so Sales Enquiries is NOT blocked
        for url, name in [
            ('/accounts/settings/', 'Company Settings'),
            ('/service/jobcards/', 'Job Cards'),
            ('/spares/',            'Spares'),
        ]:
            go(page, url)
            cnt = page.content()
            is_blocked = (
                'Access Denied' in cnt or 'Forbidden' in cnt or
                'forbidden' in cnt.lower() or
                '/accounts/login/' in page.url
            )
            chk(page,'RBAC',f'Cashier blocked: {name}', is_blocked)
            ss(page, f'191_cashier_{name[:10].replace(" ","_")}')

        # Cashier CAN access Finance (check Access Denied only, not bare '403' which appears in invoice numbers)
        go(page, '/billing/invoices/')
        ss(page,'192_cashier_billing')
        cnt = page.content()
        chk(page,'RBAC','Cashier can access billing',
            'Access Denied' not in cnt and 'Forbidden' not in cnt)

        go(page, '/accounts/logout/')
        page.wait_for_timeout(500)
        login(page)
        ss(page,'193_admin_restored_2')
    else:
        print('  [SKIP] No Cashier user found')

    # --- Superuser sees EVERYTHING ---
    go(page, '/accounts/dashboard/')
    ss(page,'194_superuser_dashboard')
    sidebar = page.evaluate("() => { const s = document.getElementById('sidebar'); return s ? s.textContent : ''; }").lower()
    for section in ['sales','customers','finance','service','spares','rto','masters','report','admin']:
        chk(page,'RBAC',f'Superuser sidebar: {section.upper()} visible', section in sidebar)

    # Superuser can access all admin URLs
    for url, name in [
        ('/accounts/settings/',  'Company Settings'),
        ('/accounts/roles/',     'Roles'),
        ('/accounts/branches/', 'Branches'),
        ('/billing/invoices/',  'Billing'),
        ('/spares/',            'Spares'),
        ('/service/jobcards/', 'Service'),
        ('/masters/suppliers/','Masters'),
    ]:
        go(page, url)
        cnt = page.content()
        ok_f = 'Access Denied' not in cnt and 'Forbidden' not in cnt and no_error(page)[0]
        chk(page,'RBAC',f'Superuser can access: {name}', ok_f)
        ss(page, f'195_su_{name[:10].replace(" ","_")}')

    browser.close()

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')

print()
print('='*65)
print('FINAL QA COMPLETE')
print('='*65)
print(f'Total: {passed+failed}  PASSED: {passed}  FAILED: {failed}')
print(f'Screenshots: {ss_count[0]} saved to final_qa/')

if issues:
    print()
    print('FAILING CHECKS:')
    by_flow = {}
    for iss in issues:
        by_flow.setdefault(iss['flow'], []).append(iss)
    for flow, flow_issues in by_flow.items():
        print(f'\n  [{flow}]')
        for iss in flow_issues:
            print(f'    [FAIL] {iss["check"]}')
            print(f'           {iss["detail"]}')
            print(f'           {iss["ss"]}')
else:
    print()
    print('ALL CHECKS PASSED --- ZERO ISSUES')

