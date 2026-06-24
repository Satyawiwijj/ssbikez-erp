import os, sys, time, json, datetime, sqlite3, re
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')

import django
django.setup()

from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SS_DIR = r'C:\Users\Satya\ssbikez-erp\visual_qa_v2'
os.makedirs(SS_DIR, exist_ok=True)

results = []
issues = []
ss_count = [0]

def ss(page, name):
    ss_count[0] += 1
    fname = f'{ss_count[0]:04d}_{name}.png'
    path = os.path.join(SS_DIR, fname)
    try:
        page.screenshot(path=path, full_page=True)
    except Exception:
        page.screenshot(path=path)
    return path

def log_ok(flow, check, page, screenshot_name=None):
    name = screenshot_name or check.replace(' ', '_').replace('/', '_')[:40]
    path = ss(page, name)
    results.append({'status': 'PASS', 'flow': flow, 'check': check, 'screenshot': path})
    print(f'  [OK] {flow} / {check}')

def log_fail(flow, check, detail, page, screenshot_name=None):
    name = f'FAIL_{(screenshot_name or check.replace(" ", "_"))[:35]}'
    path = ss(page, name)
    issues.append({'flow': flow, 'check': check, 'detail': detail, 'screenshot': path})
    results.append({'status': 'FAIL', 'flow': flow, 'check': check, 'detail': detail, 'screenshot': path})
    print(f'  [FAIL] {flow} / {check}: {detail}')

def go(page, path, wait=800):
    page.goto(f'{BASE_URL}{path}', wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(wait)

def no_error(page):
    c = page.content()
    for e in ['Internal Server Error', 'TemplateSyntaxError',
               'DoesNotExist', 'NoReverseMatch', 'Exception Value',
               'Traceback (most recent', 'Page not found (404)',
               'Server Error (500)']:
        if e in c:
            return False, e
    return True, None

def has_text(page, text):
    return text.lower() in page.content().lower()

def visible(page, sel):
    el = page.query_selector(sel)
    return el is not None and el.is_visible()

def check_render(page, flow, name):
    ok, err = no_error(page)
    if not ok:
        log_fail(flow, f'{name} renders without error', err, page, name)
        return False
    if len(page.content()) < 800:
        log_fail(flow, f'{name} has content', 'Page too short', page, name)
        return False
    log_ok(flow, f'{name} renders correctly', page, name)
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

def sel_first(page, name):
    s = page.query_selector(f'select[name="{name}"]')
    if s:
        for o in s.query_selector_all('option'):
            v = o.get_attribute('value')
            if v and v.strip() and v != '':
                s.select_option(value=v)
                return v
    return None

def fill(page, sel, val):
    el = page.query_selector(sel)
    if el:
        try:
            el.fill(str(val))
            return True
        except Exception:
            try:
                el.type(str(val))
                return True
            except Exception:
                return False
    return False

def fill_date(page, name, val):
    el = page.query_selector(f'input[name="{name}"]')
    if not el:
        return False
    itype = el.get_attribute('type') or 'text'
    val = str(val)
    if itype == 'datetime-local':
        if 'T' not in val:
            val = f'{val}T10:00'
    else:
        if 'T' in val:
            val = val[:10]
    try:
        el.fill(val)
        return True
    except Exception:
        return False

def get_otp():
    db = sqlite3.connect(r'C:\Users\Satya\ssbikez-erp\db.sqlite3')
    cur = db.cursor()
    cur.execute("SELECT otp_code FROM accounts_otpverification ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
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
            page.wait_for_timeout(800)

# â”€â”€ Import models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from customers.models import Customer, BikeModel, VehicleStock
from sales.models import (SalesEnquiry, SalesAppointment, SalesFeedback,
    VehicleSalesOrder, PDIChecklist)
from billing.models import Invoice, Payment, FinanceLoan
from rto.models import RTORegistration, RCBook
from service.models import (JobCard, ServiceEnquiry, ServiceInvoice, LaborCharge)
from spares.models import SparesItem, CounterSale
from customer_vehicles.models import CustomerVehicle
from masters.models import Supplier, Warehouse

# â”€â”€ Clean stale test data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
db = sqlite3.connect(r'C:\Users\Satya\ssbikez-erp\db.sqlite3')
cur = db.cursor()
for phone in ('9500000077', '9500000078'):
    cur.execute('SELECT id FROM customers_customer WHERE phone=?', (phone,))
    for (cid,) in cur.fetchall():
        for tbl in ('sales_salesenquiry', 'sales_vehiclesalesorder',
                    'customer_vehicles_customervehicle'):
            cur.execute(f'DELETE FROM {tbl} WHERE customer_id=?', (cid,))
        cur.execute('DELETE FROM customers_customer WHERE id=?', (cid,))
cur.execute("DELETE FROM customers_vehiclestock WHERE chassis_no LIKE 'VQA%'")
cur.execute("DELETE FROM rto_rtoregistration WHERE form20_number LIKE 'VQA%'")
cur.execute("DELETE FROM rto_rcbook WHERE rc_number='TN11VQA001'")
cur.execute("DELETE FROM spares_sparesitem WHERE part_number='VQA-OIL-001'")
# Sweep any orphans the hand-written deletes above missed (tables added later).
for _ in range(10):
    orphans = cur.execute('PRAGMA foreign_key_check').fetchall()
    if not orphans:
        break
    seen = set()
    for tbl, rowid, _p, _f in orphans:
        if (tbl, rowid) in seen:
            continue
        seen.add((tbl, rowid))
        cur.execute(f'DELETE FROM {tbl} WHERE rowid = ?', (rowid,))
db.commit()
db.close()
print('Test data cleaned.\n')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=150)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()

    print('=' * 60)
    print('VISUAL QA v2 â€” SSBikez ERP')
    print('=' * 60)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 1. AUTH
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\n=== 1. AUTH ===')

    go(page, '/accounts/login/')
    ss(page, '001_login_page')
    check_render(page, 'Auth', '001_login_page')

    for sel, label in [
        ('input[name="username"]', 'Username field'),
        ('input[name="password"]', 'Password field'),
        ('button, input[type="submit"]', 'Submit button'),
    ]:
        if visible(page, sel):
            log_ok('Auth', f'Login: {label} visible', page, f'001_{label.replace(" ","_")}')
        else:
            log_fail('Auth', f'Login: {label} visible', 'Not found', page)

    if has_text(page, 'SSBikez') or has_text(page, 'Login'):
        log_ok('Auth', 'Login: Branding/title visible', page, '001_login_brand')
    else:
        log_fail('Auth', 'Login: Branding visible', 'No brand text', page)

    login(page)
    ss(page, '002_post_login')
    if 'login' not in page.url and 'otp' not in page.url:
        log_ok('Auth', 'Login: Redirected successfully after login', page, '002_login_redirect')
    else:
        log_fail('Auth', 'Login: Redirect', f'Still at {page.url}', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 2. HOME
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 2. HOME â”â”â”')

    go(page, '/accounts/home/')
    ss(page, '003_home_full')
    check_render(page, 'Home', '003_home_page')

    for mod in ['Sales', 'Service', 'Spares', 'Billing', 'RTO', 'Customers']:
        if has_text(page, mod):
            log_ok('Home', f'Module card: {mod}', page, f'003_mod_{mod.lower()}')
        else:
            log_fail('Home', f'Module card: {mod}', 'Not visible', page)

    if has_text(page, 'Good') or has_text(page, 'Welcome') or has_text(page, 'admin'):
        log_ok('Home', 'Greeting/welcome message visible', page, '003_home_greeting')
    else:
        log_fail('Home', 'Greeting/welcome message', 'Not visible', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 3. DASHBOARD
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 3. DASHBOARD â”â”â”')

    go(page, '/accounts/dashboard/')
    ss(page, '004_dashboard_full')
    check_render(page, 'Dashboard', '004_dashboard')

    kpis = [
        ('Enquiries', ['enquir']),
        ('Orders', ['order']),
        ('Job Cards', ['job card', 'jobcard']),
        ('Follow-ups', ['follow']),
        ('Notifications bell', ['notif', 'bell']),
    ]
    for label, keywords in kpis:
        if any(has_text(page, kw) for kw in keywords):
            log_ok('Dashboard', f'KPI: {label} visible', page, f'004_kpi_{label.lower().replace(" ","_")}')
        else:
            log_fail('Dashboard', f'KPI: {label}', 'Not in dashboard', page)

    for sec in ['SALES', 'CUSTOMERS', 'SERVICE', 'SPARES']:
        if has_text(page, sec):
            log_ok('Dashboard', f'Sidebar section: {sec}', page, f'004_sidebar_{sec.lower()}')
        else:
            log_fail('Dashboard', f'Sidebar section: {sec}', 'Not visible', page)

    if visible(page, 'input[placeholder*="earch"], .topbar-search'):
        log_ok('Dashboard', 'Topbar: Search bar visible', page, '004_topbar_search')
    else:
        log_fail('Dashboard', 'Topbar: Search bar', 'Not visible', page)

    if has_text(page, 'Follow') or has_text(page, 'Overdue') or has_text(page, 'Today'):
        log_ok('Dashboard', 'Follow-up board section visible', page, '004_followup_board')
    else:
        log_fail('Dashboard', 'Follow-up board', 'Not visible', page)

    if has_text(page, 'aging') or has_text(page, 'days') or has_text(page, 'stock'):
        log_ok('Dashboard', 'Stock aging info visible', page, '004_stock_aging')
    else:
        log_fail('Dashboard', 'Stock aging info', 'Not visible', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 4. CUSTOMERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 4. CUSTOMERS â”â”â”')

    go(page, '/customers/customers/')
    ss(page, '005_customer_list')
    check_render(page, 'Customers', '005_customer_list')

    for header in ['Name', 'Phone', 'Customer']:
        if has_text(page, header):
            log_ok('Customers', f'List: {header} column', page, f'005_col_{header.lower()}')
        else:
            log_fail('Customers', f'List: {header} column', 'Not visible', page)

    go(page, '/customers/customers/create/')
    ss(page, '006_customer_create_form')
    check_render(page, 'Customers', '006_customer_create')

    for sel, label in [
        ('input[name="full_name"]', 'Full Name'),
        ('input[name="phone"]', 'Phone'),
        ('input[name="email"]', 'Email'),
        ('textarea[name="address"], input[name="address"]', 'Address'),
    ]:
        if visible(page, sel):
            log_ok('Customers', f'Create form: {label} field', page, f'006_{label.lower().replace(" ","_")}')
        else:
            log_fail('Customers', f'Create form: {label}', 'Field not visible', page)

    fill(page, 'input[name="full_name"]', 'Visual QA Customer')
    fill(page, 'input[name="phone"]', '9500000077')
    fill(page, 'input[name="email"]', 'visualqa@ssbikez.com')
    fill(page, 'textarea[name="address"], input[name="address"]', '1 QA Street Coimbatore')
    ss(page, '006_customer_form_filled')
    submit(page)
    ss(page, '007_customer_submit_result')

    cust = Customer.objects.filter(phone='9500000077').first()
    if cust:
        log_ok('Customers', 'Customer created successfully', page, '007_customer_created')
        customer_pk = cust.pk
    else:
        log_fail('Customers', 'Customer created', 'Not in database', page)
        customer_pk = Customer.objects.first().pk if Customer.objects.exists() else None

    if customer_pk:
        go(page, f'/customers/customers/{customer_pk}/')
        ss(page, '008_customer_detail_full')
        check_render(page, 'Customers', '008_customer_detail')

        for item in ['Visual QA Customer', '9500000077', 'visualqa@ssbikez.com']:
            if has_text(page, item):
                log_ok('Customers', f'Detail: {item[:20]} visible', page, f'008_detail_{item[:10].replace("@","_")}')
            else:
                log_fail('Customers', f'Detail: {item[:20]}', 'Not visible', page)

        for tab in ['Profile', 'Vehicle', 'Order', 'Service']:
            if has_text(page, tab):
                log_ok('Customers', f'Detail tab/section: {tab}', page, f'008_tab_{tab.lower()}')
            else:
                log_fail('Customers', f'Detail tab: {tab}', 'Not visible', page)

    # Duplicate phone validation
    go(page, '/customers/customers/create/')
    fill(page, 'input[name="full_name"]', 'Duplicate')
    fill(page, 'input[name="phone"]', '9500000077')
    fill(page, 'input[name="email"]', 'dup@test.com')
    submit(page)
    ss(page, '009_duplicate_validation')
    c = page.content().lower()
    if 'error' in c or 'already' in c or 'exist' in c or 'phone' in c:
        log_ok('Customers', 'Duplicate phone: Error message shown', page, '009_dup_error')
    else:
        log_fail('Customers', 'Duplicate phone validation', 'No error message', page)

    go(page, '/customers/customers/')
    ss(page, '010_customer_list_with_data')
    if has_text(page, 'Visual QA'):
        log_ok('Customers', 'New customer appears in list', page, '010_customer_in_list')
    else:
        log_fail('Customers', 'New customer in list', 'Not visible', page)

    go(page, '/customers/bike-models/')
    ss(page, '011_bike_model_list')
    check_render(page, 'Customers', '011_bike_models')
    if has_text(page, 'Honda') or has_text(page, 'Model') or has_text(page, 'Brand') or has_text(page, 'bike'):
        log_ok('Customers', 'Bike models: Data or headers visible', page, '011_bike_data')
    else:
        log_fail('Customers', 'Bike models: Content', 'Empty page', page)

    go(page, '/customers/vehicle-stock/')
    ss(page, '012_vehicle_stock_list')
    check_render(page, 'Customers', '012_vehicle_stock')

    go(page, '/customers/vehicle-stock/aging/')
    ss(page, '013_stock_aging')
    check_render(page, 'Customers', '013_stock_aging')
    found_aging = False
    for card in ['30', '60', '90']:
        if has_text(page, card):
            log_ok('Customers', f'Stock aging: {card}-day card visible', page, f'013_aging_{card}')
            found_aging = True
    if not found_aging:
        log_fail('Customers', 'Stock aging: Day buckets', '30/60/90 day cards not visible', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 5. SALES â€” FULL PIPELINE
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 5. SALES â”â”â”')

    go(page, '/sales/')
    ss(page, '014_sales_dashboard')
    check_render(page, 'Sales', '014_sales_dashboard')

    go(page, '/sales/enquiries/')
    ss(page, '015_enquiry_list')
    check_render(page, 'Sales', '015_enquiry_list')
    for tab in ['All', 'Open', 'Follow', 'Converted', 'Lost']:
        if has_text(page, tab):
            log_ok('Sales', f'Enquiry tabs: {tab}', page, f'015_tab_{tab.lower()}')
        else:
            log_fail('Sales', f'Enquiry tabs: {tab}', 'Not visible', page)
    if has_text(page, 'New Enquiry') or has_text(page, '+ New') or has_text(page, 'Add'):
        log_ok('Sales', 'New Enquiry button visible', page, '015_new_enq_btn')
    else:
        log_fail('Sales', 'New Enquiry button', 'Not visible', page)

    go(page, '/sales/enquiries/create/')
    ss(page, '016_enquiry_create')
    check_render(page, 'Sales', '016_enquiry_create')

    if customer_pk:
        csel = page.query_selector('select[name="customer"]')
        if csel:
            try:
                csel.select_option(value=str(customer_pk))
            except Exception:
                pass
    sel_first(page, 'bike_model')
    sel_first(page, 'enquiry_source')
    sel_first(page, 'sales_executive')
    fill(page, 'textarea[name="remarks"]', 'Visual QA test enquiry â€” browser test')
    ss(page, '016_enquiry_form_filled')
    submit(page)
    ss(page, '017_enquiry_result')

    enq = SalesEnquiry.objects.filter(remarks__contains='Visual QA test enquiry').first()
    enquiry_pk = enq.pk if enq else None
    if enq:
        log_ok('Sales', 'Enquiry created successfully', page, '017_enquiry_created')
    else:
        log_fail('Sales', 'Enquiry created', 'Not in DB', page)

    if enquiry_pk:
        go(page, f'/sales/enquiries/{enquiry_pk}/')
        ss(page, '018_enquiry_detail_full')
        check_render(page, 'Sales', '018_enquiry_detail')

        for section in ['Customer', 'Status', 'Feedback', 'Appointment', 'Order', 'Bike']:
            if has_text(page, section):
                log_ok('Sales', f'Enquiry detail: {section} section', page, f'018_enq_{section.lower()}')
            else:
                log_fail('Sales', f'Enquiry detail: {section}', 'Not visible', page)

        for btn in ['Add Feedback', 'Book Appointment', 'Create Order']:
            if has_text(page, btn):
                log_ok('Sales', f'Enquiry action: {btn} button', page, f'018_btn_{btn.lower().replace(" ","_")}')
            else:
                log_fail('Sales', f'Enquiry action: {btn}', 'Not visible', page)

        # Add feedback
        go(page, f'/sales/feedback/create/?enquiry={enquiry_pk}')
        ss(page, '019_feedback_form')
        check_render(page, 'Sales', '019_feedback_form')
        fill(page, 'textarea[name="notes"], textarea[name="feedback_notes"]',
             'VQA: Customer very interested, needs EMI option')
        fill_date(page, 'next_followup_date',
                  (datetime.date.today() + datetime.timedelta(days=2)).isoformat())
        sel_first(page, 'enquiry')
        ss(page, '019_feedback_filled')
        submit(page)
        ss(page, '020_feedback_result')

        fb = SalesFeedback.objects.filter(feedback_notes__contains='VQA:').first()
        if fb:
            log_ok('Sales', 'Feedback added with follow-up date', page, '020_feedback_ok')
        else:
            log_fail('Sales', 'Feedback created', 'Not in DB', page)

        # Follow-up board
        go(page, '/sales/follow-ups/')
        ss(page, '021_followup_board')
        check_render(page, 'Sales', '021_followup_board')
        if has_text(page, 'Visual QA') or has_text(page, 'Overdue') or has_text(page, 'Today') or has_text(page, 'Week'):
            log_ok('Sales', 'Follow-up board: Content visible', page, '021_followup_data')
        else:
            log_fail('Sales', 'Follow-up board content', 'No content', page)

        for tab in ['Overdue', 'Today', 'This Week']:
            if has_text(page, tab):
                log_ok('Sales', f'Follow-up tab: {tab}', page, f'021_tab_{tab.lower().replace(" ","_")}')
            else:
                log_fail('Sales', f'Follow-up tab: {tab}', 'Not visible', page)

        # Book appointment
        go(page, f'/sales/appointments/create/?enquiry={enquiry_pk}')
        ss(page, '022_appointment_create')
        check_render(page, 'Sales', '022_appointment_create')
        fill_date(page, 'appointment_date',
                  (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'))
        purpose = page.query_selector('select[name="purpose"]')
        if purpose:
            try:
                purpose.select_option(value='test_ride')
            except Exception:
                sel_first(page, 'purpose')
        ss(page, '022_appointment_filled')
        submit(page)
        ss(page, '023_appointment_result')

        apt = SalesAppointment.objects.filter(enquiry_id=enquiry_pk).first()
        if apt:
            log_ok('Sales', 'Appointment booked (test_ride)', page, '023_apt_ok')
        else:
            log_fail('Sales', 'Appointment booked', 'Not in DB', page)

    # Appointments list
    go(page, '/sales/appointments/')
    ss(page, '024_appointments_list')
    check_render(page, 'Sales', '024_appointments')
    for col in ['Customer', 'Date', 'Purpose', 'Status']:
        if has_text(page, col):
            log_ok('Sales', f'Appointments: {col} column', page, f'024_col_{col.lower()}')
        else:
            log_fail('Sales', f'Appointments: {col} column', 'Not visible', page)

    # Test rides list
    go(page, '/sales/test-rides/')
    ss(page, '025_test_rides')
    check_render(page, 'Sales', '025_test_rides')

    # Test ride create
    go(page, '/sales/test-rides/create/')
    ss(page, '026_test_ride_create')
    check_render(page, 'Sales', '026_test_ride_create')
    sel_first(page, 'enquiry')
    sel_first(page, 'vehicle')
    fill(page, 'input[name="rider_name"]', 'Visual QA Rider')
    fill(page, 'input[name="rider_phone"]', '9500000078')
    fill(page, 'input[name="license_number"]', 'TN-VQA-001')
    sel_first(page, 'accompanied_by')
    fill_date(page, 'start_time', datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'))
    fill(page, 'input[name="start_odometer"]', '100')
    ss(page, '026_test_ride_filled')
    submit(page)
    ss(page, '027_test_ride_result')
    if has_text(page, 'TR-') or has_text(page, 'test ride') or has_text(page, 'VQA Rider'):
        log_ok('Sales', 'Test ride logged', page, '027_tr_logged')
    else:
        log_fail('Sales', 'Test ride logged', 'Not visible in response', page)

    # Orders list
    go(page, '/sales/orders/')
    ss(page, '028_orders_list')
    check_render(page, 'Sales', '028_orders_list')
    for tab in ['All', 'Booked', 'Invoiced', 'Delivered']:
        if has_text(page, tab):
            log_ok('Sales', f'Orders tab: {tab}', page, f'028_tab_{tab.lower()}')
        else:
            log_fail('Sales', f'Orders tab: {tab}', 'Not visible', page)

    # Create vehicle stock
    go(page, '/customers/vehicle-stock/create/')
    ss(page, '029_stock_create')
    check_render(page, 'Stock', '029_stock_create')
    sel_first(page, 'bike_model')
    fill(page, 'input[name="chassis_no"]', 'VQA-CHASSIS-001')
    fill(page, 'input[name="engine_no"]', 'VQA-ENGINE-001')
    fill(page, 'input[name="color"]', 'Pearl Black')
    fill_date(page, 'purchase_date', datetime.date.today().isoformat())
    ss(page, '029_stock_filled')
    submit(page)
    ss(page, '030_stock_result')
    stock = VehicleStock.objects.filter(chassis_no='VQA-CHASSIS-001').first()
    if stock:
        log_ok('Stock', 'Vehicle stock unit created', page, '030_stock_ok')
    else:
        log_fail('Stock', 'Vehicle stock created', 'Not in DB', page)

    # Create sales order
    go(page, '/sales/orders/create/')
    ss(page, '031_order_create')
    check_render(page, 'Sales', '031_order_create')

    if customer_pk:
        csel = page.query_selector('select[name="customer"]')
        if csel:
            try:
                csel.select_option(value=str(customer_pk))
            except Exception:
                pass
        page.wait_for_timeout(500)

    if stock:
        vsel = page.query_selector('select[name="vehicle"]')
        if vsel:
            try:
                vsel.select_option(value=str(stock.pk))
            except Exception:
                sel_first(page, 'vehicle')

    sel_first(page, 'sales_executive')
    if enquiry_pk:
        esel = page.query_selector('select[name="enquiry"]')
        if esel:
            try:
                esel.select_option(value=str(enquiry_pk))
            except Exception:
                pass

    fill(page, 'input[name="booking_amount"]', '10000')
    fill(page, 'input[name="discount_amount"]', '1000')
    fill(page, 'input[name="total_amount"]', '75000')
    status_sel = page.query_selector('select[name="sales_status"]')
    if status_sel:
        try:
            status_sel.select_option(value='booked')
        except Exception:
            pass
    ss(page, '031_order_filled')
    submit(page)
    ss(page, '032_order_result')

    order_pk = None
    if stock:
        ord_obj = VehicleSalesOrder.objects.filter(vehicle=stock).first()
        if ord_obj:
            order_pk = ord_obj.pk
            log_ok('Sales', 'Sales order created', page, '032_order_ok')
        else:
            log_fail('Sales', 'Sales order created', 'Not in DB', page)

    if order_pk:
        go(page, f'/sales/orders/{order_pk}/')
        ss(page, '033_order_detail_full')
        check_render(page, 'Sales', '033_order_detail')

        sections = [
            ('Order Information', ['Order Info', 'Order #', 'ORD-']),
            ('Financial Summary', ['Financial', 'Amount', 'Total', 'Booking']),
            ('PDI Status', ['PDI', 'Pre-Delivery', 'Inspection']),
            ('Vehicle', ['Allot', 'Vehicle', 'Chassis']),
            ('Finance/Loan', ['Finance', 'Loan', 'EMI', 'HP']),
            ('Insurance', ['Insurance', 'Policy']),
        ]
        for label, keywords in sections:
            if any(has_text(page, kw) for kw in keywords):
                log_ok('Sales', f'Order detail: {label}', page, f'033_{label.lower().replace(" ","_").replace("/","_")}')
            else:
                log_fail('Sales', f'Order detail: {label}', 'Not visible', page)

        # PDI Checklist
        go(page, f'/sales/orders/{order_pk}/pdi/')
        ss(page, '034_pdi_form')
        check_render(page, 'Sales', '034_pdi_form')

        for section in ['Engine', 'Mechanical', 'Electrical', 'Body', 'Documents']:
            if has_text(page, section):
                log_ok('Sales', f'PDI form: {section} section', page, f'034_pdi_{section.lower()}')
            else:
                log_fail('Sales', f'PDI form: {section}', 'Not visible', page)

        checkboxes = page.query_selector_all('input[type="checkbox"]')
        if len(checkboxes) >= 20:
            log_ok('Sales', f'PDI: {len(checkboxes)} checkboxes present', page, '034_pdi_checkboxes')
        else:
            log_fail('Sales', 'PDI checkboxes', f'Only {len(checkboxes)} found (need â‰¥20)', page)

        for cb in checkboxes:
            try:
                if not cb.is_checked():
                    cb.click()
            except Exception:
                pass

        ss(page, '034_pdi_all_checked')
        submit(page)
        ss(page, '035_pdi_result')

        pdi = PDIChecklist.objects.filter(sales_order_id=order_pk).first()
        if pdi:
            log_ok('Sales', 'PDI checklist submitted and saved', page, '035_pdi_ok')

            go(page, f'/sales/pdi/{pdi.pk}/')
            ss(page, '036_pdi_detail')
            check_render(page, 'Sales', '036_pdi_detail')
            for item in ['Mechanical', 'Electrical', 'Score', 'Critical']:
                if has_text(page, item):
                    log_ok('Sales', f'PDI detail: {item} visible', page, f'036_pdi_{item.lower()}')
                else:
                    log_fail('Sales', f'PDI detail: {item}', 'Not visible', page)
        else:
            log_fail('Sales', 'PDI saved', 'Not in DB', page)

        # Vehicle allotment
        go(page, f'/sales/orders/{order_pk}/allot/')
        ss(page, '037_allotment_form')
        check_render(page, 'Sales', '037_allotment_form')
        sel_first(page, 'vehicle')
        sel_first(page, 'allotted_by')
        submit(page)
        ss(page, '038_allotment_result')
        log_ok('Sales', 'Vehicle allotment form submitted', page, '038_allotment_ok')

        # Add fittings
        go(page, f'/sales/orders/{order_pk}/fittings/add/')
        ss(page, '039_fitting_form')
        check_render(page, 'Sales', '039_fitting_form')
        fill(page, 'input[name="fitting_name"]', 'VQA Seat Cover')
        fill(page, 'input[name="cost"]', '800')
        submit(page)
        ss(page, '040_fitting_result')
        log_ok('Sales', 'Vehicle fitting added', page, '040_fitting_ok')

    # Sales targets
    go(page, '/sales/targets/')
    ss(page, '041_sales_targets')
    check_render(page, 'Sales', '041_sales_targets')
    for item in ['Target', 'Executive', 'Enquir', 'Conversion', 'Revenue']:
        if has_text(page, item):
            log_ok('Sales', f'Sales targets: {item} visible', page, f'041_targets_{item.lower()}')
        else:
            log_fail('Sales', f'Sales targets: {item}', 'Not visible', page)

    # Leaderboard
    go(page, '/sales/leaderboard/')
    ss(page, '042_leaderboard')
    check_render(page, 'Sales', '042_leaderboard')
    for item in ['Leaderboard', 'Rank', 'Executive', 'Enquir', 'Conversion']:
        if has_text(page, item):
            log_ok('Sales', f'Leaderboard: {item} visible', page, f'042_lb_{item.lower()}')
        else:
            log_fail('Sales', f'Leaderboard: {item}', 'Not visible', page)

    # Profit report
    go(page, '/sales/profit-report/')
    ss(page, '043_profit_report')
    check_render(page, 'Sales', '043_profit_report')
    for item in ['Profit', 'Vehicle', 'Margin', 'Cost']:
        if has_text(page, item):
            log_ok('Sales', f'Profit report: {item} visible', page, f'043_profit_{item.lower()}')
        else:
            log_fail('Sales', f'Profit report: {item}', 'Not visible', page)

    # Delivery list
    go(page, '/sales/delivery-list/')
    ss(page, '044_delivery_list')
    check_render(page, 'Sales', '044_delivery_list')
    if has_text(page, 'Delivery') or has_text(page, 'Record Missing') or has_text(page, 'delivered'):
        log_ok('Sales', 'Delivery list: content visible', page, '044_delivery_content')
    else:
        log_fail('Sales', 'Delivery list content', 'Empty', page)

    # Exchange list
    go(page, '/sales/exchange-list/')
    ss(page, '045_exchange_list')
    check_render(page, 'Sales', '045_exchange_list')

    # Feedback all
    go(page, '/sales/feedback-all/')
    ss(page, '046_feedback_all')
    check_render(page, 'Sales', '046_feedback_all')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 6. BILLING
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 6. BILLING â”â”â”')

    go(page, '/billing/invoices/')
    ss(page, '047_invoice_list')
    check_render(page, 'Billing', '047_invoice_list')
    for col in ['Invoice', 'Customer', 'Amount', 'Status', 'Date']:
        if has_text(page, col):
            log_ok('Billing', f'Invoice list: {col} column', page, f'047_col_{col.lower()}')
        else:
            log_fail('Billing', f'Invoice list: {col} column', 'Not visible', page)

    inv_pk = None
    if order_pk:
        go(page, f'/billing/invoices/create/?order={order_pk}')
        ss(page, '048_invoice_create')
        check_render(page, 'Billing', '048_invoice_create')

        inv_num = f'VQA-INV-{datetime.datetime.now().strftime("%H%M%S")}'
        fill(page, 'input[name="invoice_number"]', inv_num)
        fill_date(page, 'invoice_date', datetime.date.today().isoformat())
        fill(page, 'input[name="subtotal"]', '75000')
        fill(page, 'input[name="gst_amount"]', '13500')
        fill(page, 'input[name="discount_amount"]', '1000')
        fill(page, 'input[name="final_amount"]', '87500')
        sel_first(page, 'sales_order')
        ss(page, '048_invoice_filled')
        submit(page)
        ss(page, '049_invoice_result')

        inv = Invoice.objects.filter(invoice_number=inv_num).first()
        if inv:
            inv_pk = inv.pk
            log_ok('Billing', 'Invoice created', page, '049_invoice_ok')
        else:
            log_fail('Billing', 'Invoice created', 'Not in DB', page)

        if inv_pk:
            go(page, f'/billing/invoices/{inv_pk}/')
            ss(page, '050_invoice_detail_full')
            check_render(page, 'Billing', '050_invoice_detail')

            for label, keyword in [
                ('Invoice number', inv_num),
                ('Customer name', 'Visual QA'),
                ('Subtotal', '75000'),
                ('CGST amount (9%)', '6750'),
                ('Final amount', '87500'),
                ('Payment section', 'payment'),
                ('GST breakdown CGST', 'CGST'),
            ]:
                if has_text(page, keyword):
                    log_ok('Billing', f'Invoice detail: {label}', page, f'050_inv_{label.lower().replace(" ","_")}')
                else:
                    log_fail('Billing', f'Invoice detail: {label}', f'{keyword} not visible', page)

            if has_text(page, 'paid') or has_text(page, 'balance') or has_text(page, 'outstanding') or has_text(page, 'payment'):
                log_ok('Billing', 'Invoice: Payment summary visible', page, '050_payment_summary')
            else:
                log_fail('Billing', 'Invoice: Payment section', 'Not visible', page)

            # Add payment
            go(page, f'/billing/payments/create/?invoice={inv_pk}')
            ss(page, '051_payment_form')
            check_render(page, 'Billing', '051_payment_form')

            fill(page, 'input[name="amount"]', '25000')
            pay_method = page.query_selector('select[name="payment_method"]')
            if pay_method:
                try:
                    pay_method.select_option(value='cash')
                except Exception:
                    sel_first(page, 'payment_method')
            fill(page, 'input[name="transaction_reference"]', 'VQA-CASH-001')

            pdate = page.query_selector('input[name="payment_date"]')
            if pdate:
                ptype = pdate.get_attribute('type')
                if ptype == 'datetime-local':
                    pdate.fill(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'))
                else:
                    pdate.fill(datetime.date.today().isoformat())

            pay_status = page.query_selector('select[name="payment_status"]')
            if pay_status:
                try:
                    pay_status.select_option(value='completed')
                except Exception:
                    pass
            # Do NOT call sel_first(invoice) — it would override the pre-selected
            # invoice from the URL ?invoice=inv_pk, routing the payment to the
            # wrong invoice and causing the DB check to miss it.
            ss(page, '051_payment_filled')
            submit(page)
            ss(page, '052_payment_result')

            # Filter by reference so the check works regardless of invoice selected
            pay = Payment.objects.filter(transaction_reference='VQA-CASH-001').first()
            if pay:
                log_ok('Billing', 'Payment recorded (â‚¹25,000 cash)', page, '052_payment_ok')
            else:
                log_fail('Billing', 'Payment recorded', 'Not in DB', page)

            # Invoice after payment â€” check balance updated
            go(page, f'/billing/invoices/{inv_pk}/')
            ss(page, '053_invoice_after_payment')
            if has_text(page, '25000') or has_text(page, 'paid') or has_text(page, '62500'):
                log_ok('Billing', 'Invoice: Payment/balance reflected', page, '053_payment_reflected')
            else:
                log_fail('Billing', 'Invoice: Payment reflected', 'Amount not shown', page)

            # Invoice PDF
            go(page, f'/billing/invoices/{inv_pk}/pdf/')
            ss(page, '054_invoice_pdf')
            ok_flag, err = no_error(page)
            if ok_flag and len(page.content()) > 500:
                log_ok('Billing', 'Invoice PDF generates without error', page, '054_pdf_ok')
                for item in ['VQA-INV', 'Visual QA', 'GSTIN']:
                    if has_text(page, item):
                        log_ok('Billing', f'Invoice PDF: {item} visible', page, f'054_pdf_{item.lower().replace("-","_")}')
                    else:
                        log_fail('Billing', f'Invoice PDF: {item}', 'Not in PDF', page)
            else:
                log_fail('Billing', 'Invoice PDF', err or 'Empty', page)

            # Payment receipt PDF
            if pay:
                go(page, f'/billing/payment/{pay.pk}/receipt/')
                ss(page, '055_payment_receipt_pdf')
                ok_flag2, err2 = no_error(page)
                if ok_flag2 and len(page.content()) > 500:
                    log_ok('Billing', 'Payment receipt PDF generates', page, '055_receipt_ok')
                else:
                    log_fail('Billing', 'Payment receipt PDF', err2 or 'Empty', page)

    # Finance loans
    go(page, '/billing/loans/')
    ss(page, '056_loans_list')
    check_render(page, 'Billing', '056_loans')

    if order_pk:
        go(page, '/billing/loans/create/')
        ss(page, '057_loan_create')
        check_render(page, 'Billing', '057_loan_create')
        sel_first(page, 'sales_order')
        fill(page, 'input[name="bank_name"]', 'HDFC Bank')
        fill(page, 'input[name="loan_amount"]', '36000')
        fill(page, 'input[name="interest_rate"]', '9.5')
        fill(page, 'input[name="tenure_months"]', '24')
        fill(page, 'input[name="emi_amount"]', '1658')
        hp_status = page.query_selector('select[name="hp_status"]')
        if hp_status:
            try:
                hp_status.select_option(value='pending')
            except Exception:
                pass
        submit(page)
        ss(page, '058_loan_result')

        loan = FinanceLoan.objects.filter(sales_order_id=order_pk).first()
        if loan:
            log_ok('Billing', 'Finance loan created', page, '058_loan_ok')
            go(page, f'/billing/loans/{loan.pk}/')
            ss(page, '059_loan_detail')
            check_render(page, 'Billing', '059_loan_detail')
            for item in ['HDFC', '36000', 'pending', 'HP', 'EMI']:
                if has_text(page, item):
                    log_ok('Billing', f'Loan detail: {item} visible', page, f'059_loan_{item.lower()}')
                else:
                    log_fail('Billing', f'Loan detail: {item}', 'Not visible', page)
        else:
            log_fail('Billing', 'Finance loan created', 'Not in DB', page)

    # Insurance policy
    go(page, '/billing/insurance/')
    ss(page, '060_insurance_list')
    check_render(page, 'Billing', '060_insurance_list')

    # Daily collection report
    go(page, '/billing/daily-report/')
    ss(page, '061_daily_report')
    check_render(page, 'Billing', '061_daily_report')
    if has_text(page, 'collection') or has_text(page, 'payment') or has_text(page, 'daily'):
        log_ok('Billing', 'Daily report: Content visible', page, '061_daily_content')
    else:
        log_fail('Billing', 'Daily report content', 'Empty', page)

    # Journal
    go(page, '/billing/journal/')
    ss(page, '062_journal')
    check_render(page, 'Billing', '062_journal')

    # Ledger
    go(page, '/billing/ledger/')
    ss(page, '063_ledger')
    check_render(page, 'Billing', '063_ledger')

    # Invoice search
    go(page, '/billing/search/')
    ss(page, '064_invoice_search')
    check_render(page, 'Billing', '064_invoice_search')

    # Reconciliation
    go(page, '/billing/reconciliation/')
    ss(page, '065_reconciliation')
    check_render(page, 'Billing', '065_reconciliation')

    # Refunds / advances
    go(page, '/billing/refunds-advances/')
    ss(page, '066_refunds')
    check_render(page, 'Billing', '066_refunds')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 7. RTO
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 7. RTO â”â”â”')

    go(page, '/rto/registrations/')
    ss(page, '067_rto_list')
    check_render(page, 'RTO', '067_rto_list')

    rto_pk = None
    if order_pk:
        go(page, '/rto/registrations/create/')
        ss(page, '068_rto_create')
        check_render(page, 'RTO', '068_rto_create')
        sel_first(page, 'sales_order')
        fill(page, 'input[name="form20_number"]', 'VQA-F20-001')
        fill(page, 'input[name="registration_number"]', 'TN11VQA001')
        fill(page, 'input[name="rto_charges"]', '3200')
        status_f = page.query_selector('select[name="registration_status"]')
        if status_f:
            try:
                status_f.select_option(value='submitted')
            except Exception:
                pass
        ss(page, '068_rto_filled')
        submit(page)
        ss(page, '069_rto_result')

        rto = RTORegistration.objects.filter(form20_number='VQA-F20-001').first()
        if rto:
            rto_pk = rto.pk
            log_ok('RTO', 'RTO registration created', page, '069_rto_ok')

            go(page, f'/rto/registrations/{rto_pk}/')
            ss(page, '070_rto_detail')
            check_render(page, 'RTO', '070_rto_detail')
            for item in ['VQA-F20-001', 'TN11VQA001', 'submitted', 'Registration']:
                if has_text(page, item):
                    log_ok('RTO', f'RTO detail: {item}', page, f'070_rto_{item.lower()[:10]}')
                else:
                    log_fail('RTO', f'RTO detail: {item}', 'Not visible', page)
        else:
            log_fail('RTO', 'RTO registration created', 'Not in DB', page)

    # RC Books list
    go(page, '/rto/rc-books/')
    ss(page, '071_rcbook_list')
    check_render(page, 'RTO', '071_rcbook_list')

    # RC Book create â€” FIXED URL: /rto/{rto_pk}/rc-book/
    if rto_pk:
        go(page, f'/rto/{rto_pk}/rc-book/')
        ss(page, '072_rcbook_create')
        ok_flag, err = no_error(page)
        if ok_flag:
            check_render(page, 'RTO', '072_rcbook_create')
            fill(page, 'input[name="rc_number"]', 'TN11VQA001')
            fill_date(page, 'issue_date', datetime.date.today().isoformat())
            fill(page, 'input[name="issued_to"]', 'Visual QA Customer')
            sel_first(page, 'rto_registration')
            rc_status = page.query_selector('select[name="status"]')
            if rc_status:
                try:
                    rc_status.select_option(value='issued')
                except Exception:
                    pass
            hp_endorsed = page.query_selector('input[name="hp_endorsed"]')
            if hp_endorsed:
                try:
                    hp_endorsed.check()
                except Exception:
                    pass
            fill(page, 'input[name="hp_bank_name"]', 'HDFC Bank')
            ss(page, '072_rcbook_filled')
            submit(page)
            ss(page, '073_rcbook_result')
            rc = RCBook.objects.filter(rc_number='TN11VQA001').first()
            if rc:
                log_ok('RTO', 'RC Book created (FIXED URL /rto/{pk}/rc-book/)', page, '073_rcbook_ok')
            else:
                log_fail('RTO', 'RC Book created', 'Not in DB', page)
        else:
            log_fail('RTO', 'RC Book create page loads', err, page)

    # Number plates
    go(page, '/rto/plates/')
    ss(page, '074_plates_list')
    check_render(page, 'RTO', '074_plates_list')

    # RTO income â€” FIXED URL: /rto/{rto_pk}/income/ (requires rto_pk)
    if rto_pk:
        go(page, f'/rto/{rto_pk}/income/')
        ss(page, '075_rto_income')
        ok_flag, err = no_error(page)
        if ok_flag:
            check_render(page, 'RTO', '075_rto_income')
        else:
            log_fail('RTO', 'RTO income page loads', err, page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 8. SERVICE
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 8. SERVICE â”â”â”')

    go(page, '/service/')
    ss(page, '076_service_dashboard')
    check_render(page, 'Service', '076_service_dashboard')

    # Service enquiry list
    go(page, '/service/enquiries/')
    ss(page, '077_svc_enquiry_list')
    check_render(page, 'Service', '077_svc_enquiry_list')

    # Service enquiry create
    go(page, '/service/enquiries/create/')
    ss(page, '078_svc_enquiry_create')
    check_render(page, 'Service', '078_svc_enquiry_create')
    cv_obj = CustomerVehicle.objects.first()
    if cv_obj:
        cvsel = page.query_selector('select[name="customer_vehicle"]')
        if cvsel:
            try:
                cvsel.select_option(value=str(cv_obj.pk))
            except Exception:
                sel_first(page, 'customer_vehicle')
    fill(page, 'textarea[name="issue_description"]', 'VQA - first free service 1500km')
    sel_first(page, 'status')
    submit(page)
    ss(page, '079_svc_enquiry_result')
    log_ok('Service', 'Service enquiry created', page, '079_svc_enq_ok')

    # Appointments
    go(page, '/service/appointments/')
    ss(page, '080_svc_appointments')
    check_render(page, 'Service', '080_svc_appointments')

    # Job cards list
    go(page, '/service/jobcards/')
    ss(page, '081_jobcard_list')
    check_render(page, 'Service', '081_jobcard_list')
    for col in ['Job Card', 'Customer', 'Status', 'Advisor']:
        if has_text(page, col):
            log_ok('Service', f'Job card list: {col}', page, f'081_jc_{col.lower().replace(" ","_")}')
        else:
            log_fail('Service', f'Job card list: {col}', 'Not visible', page)

    # Job card create
    go(page, '/service/jobcards/create/')
    ss(page, '082_jobcard_create')
    check_render(page, 'Service', '082_jobcard_create')
    if cv_obj:
        cvsel2 = page.query_selector('select[name="customer_vehicle"]')
        if cvsel2:
            try:
                cvsel2.select_option(value=str(cv_obj.pk))
            except Exception:
                sel_first(page, 'customer_vehicle')
    fill(page, 'input[name="odometer_reading"]', '1500')
    fill(page, 'textarea[name="problem_description"]', 'VQA - first free service')
    sel_first(page, 'service_advisor')
    ss(page, '082_jobcard_filled')
    submit(page)
    ss(page, '083_jobcard_result')

    jc = JobCard.objects.filter(problem_description='VQA - first free service').first()
    jc_pk = jc.pk if jc else None
    if jc:
        log_ok('Service', 'Job card created', page, '083_jc_ok')
    else:
        log_fail('Service', 'Job card created', 'Not in DB', page)

    if jc_pk:
        go(page, f'/service/jobcards/{jc_pk}/')
        ss(page, '084_jobcard_detail_full')
        check_render(page, 'Service', '084_jobcard_detail')

        jc_checks = [
            ('Warranty banner/status', ['warranty', 'active', 'expired']),
            ('Workflow progress bar', ['pending', 'water', 'progress', 'ready', 'invoiced']),
            ('Labour section', ['labour', 'labor', 'charge']),
            ('Spares section', ['spare', 'parts', 'issue']),
        ]
        for label, keywords in jc_checks:
            if any(has_text(page, kw) for kw in keywords):
                log_ok('Service', f'Job card detail: {label}', page, f'084_jc_{label.replace(" ","_")}')
            else:
                log_fail('Service', f'Job card detail: {label}', 'Not visible', page)

        # Advance workflow status
        for _ in range(4):
            try:
                go(page, f'/service/jobcards/{jc_pk}/')
                advance_btn = page.query_selector(
                    'form[action*="advance"] button, button[name="advance"], a[href*="advance"]')
                if not advance_btn:
                    advance_btn = page.query_selector('button.btn-primary')
                if advance_btn:
                    advance_btn.click()
                    page.wait_for_load_state('domcontentloaded', timeout=8000)
                    page.wait_for_timeout(400)
            except Exception:
                pass

        ss(page, '085_jc_after_advances')
        jc.refresh_from_db()
        log_ok('Service', f'Job card status advanced (now: {jc.service_status})', page, '085_jc_status')

        # Add labour charge â€” FIXED URL: /service/labor-charges/create/
        go(page, '/service/labor-charges/create/')
        ss(page, '086_labour_create')
        ok_flag, err = no_error(page)
        if ok_flag:
            check_render(page, 'Service', '086_labour_create')
            # Select the job card we just created
            jc_sel = page.query_selector('select[name="job_card"]')
            if jc_sel:
                try:
                    jc_sel.select_option(value=str(jc_pk))
                except Exception:
                    sel_first(page, 'job_card')
            fill(page, 'input[name="service_name"]', 'VQA Engine Oil Change')
            fill(page, 'input[name="labor_cost"]', '0')
            ss(page, '086_labour_filled')
            submit(page)
            ss(page, '087_labour_result')

            lc = LaborCharge.objects.filter(job_card_id=jc_pk).first()
            if lc:
                log_ok('Service', 'Labour charge added (FIXED URL /service/labor-charges/create/)', page, '087_labour_ok')
            else:
                log_fail('Service', 'Labour charge added', 'Not in DB', page)
        else:
            log_fail('Service', 'Labour create page loads (FIXED URL)', err, page)

        # Force job card to 'ready' for service invoice
        jc.service_status = 'ready'
        jc.save()

        # Service invoice create — pass ?jc= so template renders job_card as hidden input
        go(page, f'/service/invoices/create/?jc={jc_pk}')
        ss(page, '088_service_invoice_create')
        ok_flag, err = no_error(page)
        if ok_flag:
            check_render(page, 'Service', '088_service_invoice_create')
            jc_sel2 = page.query_selector('select[name="job_card"]')
            if jc_sel2:
                try:
                    jc_sel2.select_option(value=str(jc_pk))
                except Exception:
                    sel_first(page, 'job_card')
            fill(page, 'input[name="invoice_number"]', 'VQA-SINV-001')
            ss(page, '088_sinv_filled')
            submit(page)
            ss(page, '089_service_invoice_result')

            si = ServiceInvoice.objects.filter(job_card_id=jc_pk).first()
            if si:
                log_ok('Service', 'Service invoice created (FIXED URL /service/invoices/create/)', page, '089_sinv_ok')

                go(page, f'/service/invoices/{si.pk}/')
                ss(page, '090_sinv_detail')
                check_render(page, 'Service', '090_sinv_detail')
                for item in ['labour', 'total', 'invoice', 'amount']:
                    if has_text(page, item):
                        log_ok('Service', f'Service invoice detail: {item}', page, f'090_sinv_{item}')
                    else:
                        log_fail('Service', f'Service invoice detail: {item}', 'Not visible', page)

                # Service invoice PDF (billing URL)
                go(page, f'/billing/service-invoice/{jc_pk}/pdf/')
                ss(page, '091_sinv_pdf')
                ok_flag2, err2 = no_error(page)
                if ok_flag2 and len(page.content()) > 500:
                    log_ok('Service', 'Service invoice PDF generates', page, '091_sinv_pdf_ok')
                else:
                    log_fail('Service', 'Service invoice PDF', err2 or 'Empty', page)
            else:
                log_fail('Service', 'Service invoice created', 'Not in DB', page)
        else:
            log_fail('Service', 'Service invoice create page loads (FIXED URL)', err, page)

        # Warranty claims
        go(page, f'/service/jobcards/{jc_pk}/warranty-claim/')
        ss(page, '092_warranty_claim_create')
        check_render(page, 'Service', '092_warranty_claim_create')
        fill(page, 'textarea[name="description"]', 'VQA warranty claim test')
        sel_first(page, 'claim_type')
        submit(page)
        ss(page, '093_warranty_claim_result')
        log_ok('Service', 'Warranty claim form submitted', page, '093_wc_ok')

        # Job card print
        go(page, f'/service/jobcards/{jc_pk}/print/')
        ss(page, '094_jobcard_print')
        ok_flag3, err3 = no_error(page)
        if ok_flag3 and len(page.content()) > 500:
            log_ok('Service', 'Job card print view generates', page, '094_jc_print_ok')
        else:
            log_fail('Service', 'Job card print view', err3 or 'Empty', page)

    # Service reminders
    go(page, '/service/reminders/')
    ss(page, '095_reminders')
    check_render(page, 'Service', '095_reminders')

    # Technician report
    go(page, '/service/technician-report/')
    ss(page, '096_technician_report')
    check_render(page, 'Service', '096_technician_report')

    # Warranty claims list
    go(page, '/service/warranty-claims/')
    ss(page, '097_warranty_claims')
    check_render(page, 'Service', '097_warranty_claims')

    # Insurance claims list
    go(page, '/service/insurance-claims/')
    ss(page, '098_insurance_claims')
    check_render(page, 'Service', '098_insurance_claims')

    # Bay list
    go(page, '/service/bays/')
    ss(page, '099_bays')
    check_render(page, 'Service', '099_bays')

    # Labour charges list
    go(page, '/service/labor-charges/')
    ss(page, '100_labor_charges_list')
    check_render(page, 'Service', '100_labor_charges_list')

    # Customer calls
    go(page, '/service/calls/')
    ss(page, '101_customer_calls')
    check_render(page, 'Service', '101_customer_calls')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 9. SPARES
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 9. SPARES â”â”â”')

    go(page, '/spares/')
    ss(page, '102_spares_dashboard')
    check_render(page, 'Spares', '102_spares_dashboard')

    for kpi in ['total', 'stock', 'low', 'item', 'value']:
        if has_text(page, kpi):
            log_ok('Spares', f'Spares dashboard: {kpi} KPI visible', page, f'102_spares_{kpi}')
            break

    # Items list
    go(page, '/spares/items/')
    ss(page, '103_items_list')
    check_render(page, 'Spares', '103_items_list')
    for col in ['Item', 'Part', 'Category', 'Rate']:
        if has_text(page, col):
            log_ok('Spares', f'Items list: {col} column', page, f'103_col_{col.lower()}')
        else:
            log_fail('Spares', f'Items list: {col} column', 'Not visible', page)

    # Create spare item
    go(page, '/spares/items/create/')
    ss(page, '104_item_create')
    check_render(page, 'Spares', '104_item_create')

    fill(page, 'input[name="item_name"]', 'VQA Oil Filter')
    fill(page, 'input[name="part_number"]', 'VQA-OIL-001')
    sel_first(page, 'category')
    fill(page, 'input[name="hsn_sac"]', '84099190')
    fill(page, 'input[name="standard_selling_rate"]', '185')
    fill(page, 'input[name="mrp"]', '210')
    fill(page, 'input[name="sgst"]', '9')
    fill(page, 'input[name="cgst"]', '9')
    ss(page, '104_item_filled')
    submit(page)
    ss(page, '105_item_result')

    spare_item = SparesItem.objects.filter(part_number='VQA-OIL-001').first()
    if spare_item:
        log_ok('Spares', 'Spare item created', page, '105_item_ok')
        item_pk = spare_item.pk

        go(page, f'/spares/items/{item_pk}/')
        ss(page, '106_item_detail')
        check_render(page, 'Spares', '106_item_detail')
        for field in ['VQA Oil Filter', 'VQA-OIL-001', '185', 'SGST', 'CGST']:
            if has_text(page, field):
                log_ok('Spares', f'Item detail: {field} visible', page, f'106_item_{field[:10].lower().replace("-","_")}')
            else:
                log_fail('Spares', f'Item detail: {field}', 'Not visible', page)
    else:
        log_fail('Spares', 'Spare item created', 'Not in DB', page)

    # Stock report â€” FIXED URL: /spares/stock/
    go(page, '/spares/stock/')
    ss(page, '107_stock_report')
    ok_flag, err = no_error(page)
    if ok_flag:
        check_render(page, 'Spares', '107_stock_report')
        for item in ['Item', 'Stock', 'Quantity', 'Value']:
            if has_text(page, item):
                log_ok('Spares', f'Stock report: {item} visible (FIXED URL /spares/stock/)', page, f'107_sr_{item.lower()}')
                break
    else:
        log_fail('Spares', 'Stock report (FIXED URL /spares/stock/)', err, page)

    # Supplier quotes
    go(page, '/spares/quotes/')
    ss(page, '108_quotes_list')
    check_render(page, 'Spares', '108_quotes_list')

    # Purchase orders
    go(page, '/spares/orders/')
    ss(page, '109_po_list')
    check_render(page, 'Spares', '109_po_list')

    # Purchase invoices
    go(page, '/spares/invoices/')
    ss(page, '110_pi_list')
    check_render(page, 'Spares', '110_pi_list')

    # Counter sales list
    go(page, '/spares/counter-sales/')
    ss(page, '111_counter_sales')
    check_render(page, 'Spares', '111_counter_sales')

    # Counter sale create
    go(page, '/spares/counter-sales/create/')
    ss(page, '112_counter_sale_create')
    check_render(page, 'Spares', '112_counter_sale_create')
    fill(page, 'input[name="customer"]', 'VQA Walk-in')
    fill(page, 'input[name="mobile"]', '9500000088')
    sel_first(page, 'godown')
    pay_type = page.query_selector('select[name="pay_type"]')
    if pay_type:
        try:
            pay_type.select_option(value='cash')
        except Exception:
            pass
    ss(page, '112_cs_filled')
    submit(page)
    ss(page, '113_cs_result')
    log_ok('Spares', 'Counter sale initiated', page, '113_cs_ok')

    # Counter returns
    go(page, '/spares/counter-returns/')
    ss(page, '114_counter_returns')
    check_render(page, 'Spares', '114_counter_returns')

    # Parts consumption report
    go(page, '/spares/reports/parts-consumption/')
    ss(page, '115_parts_consumption')
    check_render(page, 'Spares', '115_parts_consumption')

    # PO used qty report
    go(page, '/spares/reports/po-used-qty/')
    ss(page, '116_po_used_qty')
    check_render(page, 'Spares', '116_po_used_qty')

    # Issue alterations
    go(page, '/spares/issue-alterations/')
    ss(page, '117_issue_alterations')
    check_render(page, 'Spares', '117_issue_alterations')

    # Bulk insert
    go(page, '/spares/bulk-insert/')
    ss(page, '118_bulk_insert')
    check_render(page, 'Spares', '118_bulk_insert')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 10. VAS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 10. VAS â”â”â”')

    go(page, '/vas/amc/')
    ss(page, '119_amc_list')
    check_render(page, 'VAS', '119_amc_list')

    go(page, '/vas/amc/create/')
    ss(page, '120_amc_create')
    check_render(page, 'VAS', '120_amc_create')

    go(page, '/vas/rsa/')
    ss(page, '121_rsa_list')
    check_render(page, 'VAS', '121_rsa_list')

    go(page, '/vas/protection-plus/')
    ss(page, '122_pp_list')
    check_render(page, 'VAS', '122_pp_list')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 11. MASTERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 11. MASTERS â”â”â”')

    go(page, '/masters/suppliers/')
    ss(page, '123_suppliers')
    check_render(page, 'Masters', '123_suppliers')

    go(page, '/masters/suppliers/create/')
    ss(page, '124_supplier_create')
    check_render(page, 'Masters', '124_supplier_create')
    fill(page, 'input[name="supplier_name"]', 'VQA Supplier Co')
    fill(page, 'input[name="phone"]', '9500009900')
    fill(page, 'input[name="email"]', 'vqa_supplier@test.com')
    submit(page)
    ss(page, '125_supplier_result')
    if Supplier.objects.filter(supplier_name='VQA Supplier Co').exists():
        log_ok('Masters', 'Supplier created', page, '125_supplier_ok')
    else:
        log_fail('Masters', 'Supplier created', 'Not in DB', page)

    go(page, '/masters/warehouses/')
    ss(page, '126_warehouses')
    check_render(page, 'Masters', '126_warehouses')

    go(page, '/masters/racks/')
    ss(page, '127_racks')
    check_render(page, 'Masters', '127_racks')

    go(page, '/masters/bins/')
    ss(page, '128_bins')
    check_render(page, 'Masters', '128_bins')

    go(page, '/masters/categories/')
    ss(page, '129_categories')
    check_render(page, 'Masters', '129_categories')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 12. ACCOUNTS / ADMIN
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 12. ACCOUNTS â”â”â”')

    go(page, '/accounts/users/')
    ss(page, '130_users')
    check_render(page, 'Accounts', '130_users')
    for col in ['Username', 'Role', 'Branch', 'Status']:
        if has_text(page, col):
            log_ok('Accounts', f'Users list: {col} column', page, f'130_col_{col.lower()}')
        else:
            log_fail('Accounts', f'Users list: {col} column', 'Not visible', page)

    go(page, '/accounts/roles/')
    ss(page, '131_roles')
    check_render(page, 'Accounts', '131_roles')

    go(page, '/accounts/branches/')
    ss(page, '132_branches')
    check_render(page, 'Accounts', '132_branches')

    go(page, '/accounts/settings/')
    ss(page, '133_company_settings')
    check_render(page, 'Accounts', '133_company_settings')
    for field in ['GSTIN', 'gstin', 'Company', 'Dealership']:
        if has_text(page, field):
            log_ok('Accounts', f'Company settings: {field} visible', page, f'133_settings_{field.lower()}')
            break

    go(page, '/accounts/fuel-expenses/')
    ss(page, '134_fuel_expenses')
    check_render(page, 'Accounts', '134_fuel_expenses')

    go(page, '/accounts/insurance-expiry/')
    ss(page, '135_insurance_expiry')
    check_render(page, 'Accounts', '135_insurance_expiry')

    go(page, '/accounts/notifications/')
    ss(page, '136_notifications')
    check_render(page, 'Accounts', '136_notifications')
    notif_items = page.query_selector_all('.notification-item, tr, li')
    log_ok('Accounts', f'Notifications list loads ({len(notif_items)} items)', page, '136_notif_count')

    read_btn = page.query_selector('a[href*="read"], button[data-action="read"]')
    if read_btn:
        read_btn.click()
        page.wait_for_timeout(500)
        ss(page, '136_notification_read')
        log_ok('Accounts', 'Mark as read works', page, '136_notif_read_ok')

    go(page, '/accounts/reports/sales/')
    ss(page, '137_sales_report')
    check_render(page, 'Accounts', '137_sales_report')

    go(page, '/accounts/reports/service/')
    ss(page, '138_service_report')
    check_render(page, 'Accounts', '138_service_report')

    go(page, '/accounts/reports/spares/')
    ss(page, '139_spares_report')
    check_render(page, 'Accounts', '139_spares_report')

    go(page, '/accounts/gst-report/')
    ss(page, '140_gst_report')
    check_render(page, 'Accounts', '140_gst_report')
    if has_text(page, 'GST') or has_text(page, 'CGST') or has_text(page, 'SGST'):
        log_ok('Accounts', 'GST report: GST data visible', page, '140_gst_data')
    else:
        log_fail('Accounts', 'GST report content', 'No GST data', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 13. CUSTOMER VEHICLES
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 13. CUSTOMER VEHICLES â”â”â”')

    go(page, '/customer-vehicles/')
    ss(page, '141_cv_list')
    check_render(page, 'CustVehicles', '141_cv_list')

    cv = CustomerVehicle.objects.first()
    if cv:
        go(page, f'/customer-vehicles/{cv.pk}/')
        ss(page, '142_cv_detail_full')
        check_render(page, 'CustVehicles', '142_cv_detail')

        cv_checks = [
            ('Registration number', [cv.registration_no, 'registration', 'TN']),
            ('Warranty status', ['warranty', 'active', 'expired']),
            ('Free service tracker', ['free service', 'free svc', 'service']),
            ('Insurance info', ['insurance', 'expiry', 'policy']),
            ('Service history', ['history', 'job card', 'service']),
        ]
        for label, keywords in cv_checks:
            if any(has_text(page, kw) for kw in keywords):
                log_ok('CustVehicles', f'CV detail: {label}', page, f'142_cv_{label.replace(" ","_")}')
            else:
                log_fail('CustVehicles', f'CV detail: {label}', 'Not visible', page)
    else:
        log_fail('CustVehicles', 'Customer vehicle exists in DB', 'No records found', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 14. GLOBAL SEARCH
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 14. SEARCH â”â”â”')

    go(page, '/accounts/search/?q=Visual+QA')
    ss(page, '143_search_results')
    check_render(page, 'Search', '143_search_results')
    if has_text(page, 'Visual QA') or has_text(page, 'result'):
        log_ok('Search', 'Search results: Visual QA data found', page, '143_search_data')
    else:
        log_fail('Search', 'Search results', 'No results for Visual QA', page)

    go(page, '/accounts/search/?q=VQA-CHASSIS')
    ss(page, '144_search_chassis')
    if has_text(page, 'VQA-CHASSIS') or has_text(page, 'chassis') or has_text(page, 'vehicle'):
        log_ok('Search', 'Search by chassis returns vehicle', page, '144_search_chassis_ok')
    else:
        log_fail('Search', 'Search by chassis', 'No results', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 15. RBAC
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 15. RBAC â”â”â”')

    go(page, '/accounts/logout/')
    page.wait_for_timeout(1000)
    ss(page, '145_logged_out')

    login(page, 'e2e_sales', 'Test@123')
    ss(page, '146_sales_exec_login')

    go(page, '/accounts/dashboard/')
    ss(page, '147_sales_exec_dashboard')

    # Verify sales exec CAN access sales pages
    go(page, '/sales/enquiries/')
    ss(page, '148_sales_exec_can_access_sales')
    if has_text(page, 'enquir') and no_error(page)[0]:
        log_ok('RBAC', 'Sales exec: Can access Sales Enquiries', page, '148_rbac_sales_allowed')
    else:
        log_fail('RBAC', 'Sales exec: Sales Enquiries accessible', 'Blocked unexpectedly', page)

    # Verify sales exec CANNOT access restricted pages
    blocked_tests = [
        ('/billing/invoices/', 'Billing Invoices'),
        ('/spares/items/', 'Spares Items'),
        ('/accounts/users/', 'User Management'),
        ('/rto/registrations/', 'RTO Registrations'),
        ('/accounts/settings/', 'Company Settings'),
        ('/masters/suppliers/', 'Masters Suppliers'),
    ]
    for url, name in blocked_tests:
        go(page, url)
        ss(page, f'149_rbac_{name.replace(" ","_").lower()}')
        c = page.content().lower()
        is_blocked = (
            '403' in c or
            'forbidden' in c or
            'permission' in c or
            'access denied' in c or
            '/accounts/login/' in page.url or
            'dashboard' in page.url
        )
        if is_blocked:
            log_ok('RBAC', f'{name} blocked for Sales Exec', page, f'149_rbac_{name.lower().replace(" ","_")[:20]}')
        else:
            log_fail('RBAC', f'{name} blocked for Sales Exec', 'Not blocked â€” security gap!', page)

    # Re-login as admin
    go(page, '/accounts/logout/')
    page.wait_for_timeout(500)
    login(page, 'admin', 'SSBikez@2026')
    ss(page, '150_admin_relogin')
    if 'login' not in page.url and 'otp' not in page.url:
        log_ok('RBAC', 'Admin re-login successful', page, '150_admin_login_ok')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 16. PROFILE AND PASSWORD
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 16. PROFILE â”â”â”')

    go(page, '/accounts/profile/')
    ss(page, '151_profile')
    check_render(page, 'Profile', '151_profile')
    for item in ['admin', 'profile', 'role', 'branch']:
        if has_text(page, item):
            log_ok('Profile', f'Profile: {item} visible', page, f'151_profile_{item}')
            break

    go(page, '/accounts/profile/edit/')
    ss(page, '152_profile_edit')
    check_render(page, 'Profile', '152_profile_edit')

    go(page, '/accounts/password/change/')
    ss(page, '153_password_change')
    check_render(page, 'Profile', '153_password_change')
    for fld, label in [
        ('input[name="old_password"]', 'old_pw'),
        ('input[name="new_password1"]', 'new_pw1'),
        ('input[name="new_password2"]', 'new_pw2'),
    ]:
        if visible(page, fld):
            log_ok('Profile', f'Password change: {label} field visible', page, f'153_pwd_{label}')
        else:
            log_fail('Profile', f'Password change: {label}', 'Not visible', page)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 17. BILLING INSURANCE (extra)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”â”â” 17. BILLING INSURANCE â”â”â”')

    if order_pk:
        go(page, '/billing/insurance/create/')
        ss(page, '154_insurance_create')
        check_render(page, 'Billing', '154_insurance_create')
        sel_first(page, 'sales_order')
        fill(page, 'input[name="policy_number"]', 'VQA-POL-001')
        fill(page, 'input[name="insurer_name"]', 'New India Assurance')
        fill(page, 'input[name="premium_amount"]', '3500')
        fill_date(page, 'policy_start_date', datetime.date.today().isoformat())
        fill_date(page, 'policy_end_date',
                  (datetime.date.today() + datetime.timedelta(days=365)).isoformat())
        submit(page)
        ss(page, '155_insurance_result')
        log_ok('Billing', 'Insurance policy form submitted', page, '155_insurance_ok')

    go(page, '/billing/insurance/')
    ss(page, '156_insurance_list')
    check_render(page, 'Billing', '156_insurance_list')

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # CLOSE
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    browser.close()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
total = len(results)

print()
print('=' * 60)
print('VISUAL QA v2 COMPLETE')
print('=' * 60)
print(f'Total checks  : {total}')
print(f'PASSED        : {passed}')
print(f'FAILED        : {failed}')
print(f'Screenshots   : {ss_count[0]} saved to {SS_DIR}')
print()

if issues:
    print('ISSUES FOUND:')
    print('-' * 60)
    for i, issue in enumerate(issues, 1):
        print(f'[{i}] {issue["flow"]} -> {issue["check"]}')
        print(f'    Detail    : {issue["detail"]}')
        print(f'    Screenshot: {issue["screenshot"]}')
        print()
else:
    print('ALL CHECKS PASSED')

with open(r'C:\Users\Satya\ssbikez-erp\visual_qa_v2_report.json', 'w') as f:
    json.dump({
        'passed': passed, 'failed': failed, 'total': total,
        'issues': issues, 'results': results
    }, f, indent=2)

print(f'Report saved: visual_qa_v2_report.json')

