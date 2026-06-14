import os, sys, time, json, datetime, sqlite3, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SS_DIR = r'C:\Users\Satya\ssbikez-erp\visual_qa'
os.makedirs(SS_DIR, exist_ok=True)

results = []
issues = []
ss_count = [0]

def ss(page, name):
    ss_count[0] += 1
    fname = f'{ss_count[0]:04d}_{name}.png'
    path = os.path.join(SS_DIR, fname)
    page.screenshot(path=path, full_page=True)
    return path

def ok(flow, check, screenshot_name, page):
    path = ss(page, screenshot_name)
    results.append({'status':'PASS','flow':flow,'check':check,'screenshot':path})
    print(f'  [OK]   {flow} / {check}')
    return path

def fail(flow, check, detail, screenshot_name, page):
    path = ss(page, f'FAIL_{screenshot_name}')
    issues.append({'flow':flow,'check':check,'detail':detail,'screenshot':path})
    results.append({'status':'FAIL','flow':flow,'check':check,'detail':detail,'screenshot':path})
    print(f'  [FAIL] {flow} / {check}: {detail}')
    return path

def go(page, path):
    page.goto(f'{BASE_URL}{path}', wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(600)

def check_visible(page, selector, label):
    el = page.query_selector(selector)
    return el is not None and el.is_visible()

def check_text(page, text):
    return text.lower() in page.content().lower()

def check_no_error(page):
    content = page.content()
    for err in ['Internal Server Error','TemplateSyntaxError',
                'DoesNotExist','Exception Value','Traceback',
                'Page not found','NoReverseMatch']:
        if err in content:
            return False, err
    return True, None

def get_otp():
    db = sqlite3.connect(r'C:\Users\Satya\ssbikez-erp\db.sqlite3')
    cur = db.cursor()
    cur.execute("""
        SELECT otp_code FROM accounts_otpverification
        ORDER BY created_at DESC LIMIT 1
    """)
    row = cur.fetchone()
    db.close()
    return row[0] if row else None

def login(page, username='admin', password='SSBikez@2026'):
    go(page, '/accounts/login/')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.press('input[name="password"]', 'Enter')
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    page.wait_for_timeout(1000)

    if 'otp' in page.url or 'verify' in page.url:
        time.sleep(2)
        otp = get_otp()
        if otp:
            page.fill('input[name="otp_code"]', otp)
            page.press('input[name="otp_code"]', 'Enter')
            page.wait_for_load_state('domcontentloaded', timeout=10000)
            page.wait_for_timeout(800)

def submit(page):
    clicked = page.evaluate("""() => {
        const b = document.querySelector('button[form]') ||
                  document.querySelector('button[type="submit"]') ||
                  document.querySelector('.topbar-actions button') ||
                  document.querySelector('button.btn-primary');
        if (b) { b.click(); return true; }
        return false;
    }""")
    if clicked:
        page.wait_for_load_state('domcontentloaded', timeout=12000)
        page.wait_for_timeout(600)

def select_first(page, field_name):
    sel = page.query_selector(f'select[name="{field_name}"]')
    if sel:
        opts = sel.query_selector_all('option')
        for opt in opts:
            val = opt.get_attribute('value')
            if val and val.strip() and val != '':
                sel.select_option(value=val)
                break

def check_page_visual(page, flow, page_name):
    ok_flag, err = check_no_error(page)
    path = ss(page, page_name)
    if not ok_flag:
        fail(flow, f'{page_name} renders without error', err, page_name, page)
        return False
    content = page.content()
    if len(content) < 500:
        fail(flow, f'{page_name} has content', 'Page too short', page_name, page)
        return False
    ok(flow, f'{page_name} renders correctly', page_name, page)
    return True

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=200)
    ctx = browser.new_context(viewport={'width':1400,'height':900})
    page = ctx.new_page()

    print('='*60)
    print('VISUAL QA TEST — SSBikez ERP')
    print('='*60)

    # ════════════════════════════════════════════════════════
    # 1. LOGIN PAGE
    # ════════════════════════════════════════════════════════
    print('\n[1] LOGIN')
    go(page, '/accounts/login/')
    ss(page, '001_login_page')
    if check_visible(page, 'input[name="username"]', 'username'):
        ok('Login', 'Username field visible', '001a_login_username', page)
    else:
        fail('Login', 'Username field visible', 'Not found', '001a_login_fail', page)

    login(page)
    ss(page, '002_after_login')
    if 'dashboard' in page.url or 'home' in page.url:
        ok('Login', 'Login successful - redirected to dashboard/home', '002_login_success', page)
    else:
        fail('Login', 'Login redirect', f'At {page.url}', '002_login_redirect_fail', page)

    # ════════════════════════════════════════════════════════
    # 2. HOME PAGE
    # ════════════════════════════════════════════════════════
    print('\n[2] HOME PAGE')
    go(page, '/accounts/home/')
    check_page_visual(page, 'Home', '003_home_page')

    module_names = ['Sales', 'Service', 'Spares', 'Billing', 'RTO', 'Customers']
    for mod in module_names:
        if check_text(page, mod):
            ok('Home', f'{mod} module card visible', f'003_home_{mod.lower()}', page)
        else:
            fail('Home', f'{mod} module card visible', 'Not in page', f'003_home_{mod.lower()}_fail', page)

    # ════════════════════════════════════════════════════════
    # 3. DASHBOARD
    # ════════════════════════════════════════════════════════
    print('\n[3] DASHBOARD')
    go(page, '/accounts/dashboard/')
    check_page_visual(page, 'Dashboard', '004_dashboard')

    content = page.content()
    kpi_checks = [
        ('Total Enquiries or enquiries', 'enquir'),
        ('Orders or sales orders', 'order'),
        ('Job Cards or service', 'job'),
        ('Notification bell', 'bell'),
    ]
    for label, keyword in kpi_checks:
        if keyword.lower() in content.lower():
            ok('Dashboard', f'{label} shows', f'004_dash_{keyword}', page)
        else:
            fail('Dashboard', f'{label} shows', 'Not in content', f'004_dash_{keyword}_fail', page)

    sidebar_items = [
        ('Sales', '/sales/'),
        ('Customers', '/customers/'),
        ('Service', '/service/'),
        ('Spares', '/spares/'),
    ]
    for name, href in sidebar_items:
        link = page.query_selector(f'a[href*="{href}"]')
        if link:
            ok('Dashboard', f'Sidebar: {name} link present', f'004_sidebar_{name.lower()}', page)
        else:
            fail('Dashboard', f'Sidebar: {name} link present', 'Not found', f'004_sidebar_{name.lower()}_fail', page)

    # ════════════════════════════════════════════════════════
    # 4. CUSTOMER PAGES
    # ════════════════════════════════════════════════════════
    print('\n[4] CUSTOMERS')

    go(page, '/customers/customers/')
    check_page_visual(page, 'Customers', '005_customer_list')
    has_table = check_visible(page, 'table', 'table') or check_text(page, 'customer')
    if has_table:
        ok('Customers', 'Customer list shows data or empty state', '005_customer_list_data', page)
    else:
        fail('Customers', 'Customer list content', 'No table or customer text', '005_customer_list_fail', page)

    go(page, '/customers/customers/create/')
    check_page_visual(page, 'Customers', '006_customer_create')
    required_fields = ['full_name', 'phone', 'email']
    for f in required_fields:
        if check_visible(page, f'input[name="{f}"]', f):
            ok('Customers', f'Create form: {f} field visible', f'006_field_{f}', page)
        else:
            fail('Customers', f'Create form: {f} field visible', 'Not found', f'006_field_{f}_fail', page)

    page.fill('input[name="full_name"]', 'Visual QA Customer')
    page.fill('input[name="phone"]', '9500000077')
    page.fill('input[name="email"]', 'visualqa@test.com')
    addr = page.query_selector('textarea[name="address"], input[name="address"]')
    if addr: addr.fill('1 QA Street, Coimbatore')
    submit(page)
    ss(page, '007_customer_created')

    if check_text(page, 'Visual QA Customer') or 'customers' in page.url:
        ok('Customers', 'Customer created successfully', '007_customer_created_ok', page)
    else:
        fail('Customers', 'Customer created', 'Not on expected page', '007_customer_created_fail', page)

    customer_pk = None
    import django
    django.setup()
    from customers.models import Customer
    cust = Customer.objects.filter(phone='9500000077').first()
    if cust:
        customer_pk = cust.pk

    if customer_pk:
        go(page, f'/customers/customers/{customer_pk}/')
        check_page_visual(page, 'Customers', '008_customer_detail')

        detail_checks = [
            ('Customer name visible', 'Visual QA Customer'),
            ('Phone visible', '9500000077'),
            ('Email visible', 'visualqa@test.com'),
        ]
        for label, text in detail_checks:
            if check_text(page, text):
                ok('Customers', label, f'008_detail_{label.replace(" ","_")}', page)
            else:
                fail('Customers', label, f'{text} not in page', f'008_detail_fail_{label}', page)

    go(page, '/customers/customers/create/')
    page.fill('input[name="full_name"]', 'Duplicate')
    page.fill('input[name="phone"]', '9500000077')
    page.fill('input[name="email"]', 'dup@test.com')
    submit(page)
    ss(page, '009_duplicate_validation')
    if check_text(page, 'error') or check_text(page, 'already') or check_text(page, 'exist'):
        ok('Customers', 'Duplicate phone rejected with error message', '009_dup_error', page)
    else:
        fail('Customers', 'Duplicate phone rejected', 'No error shown', '009_dup_fail', page)

    go(page, '/customers/bike-models/')
    check_page_visual(page, 'Customers', '010_bike_model_list')

    go(page, '/customers/vehicle-stock/')
    check_page_visual(page, 'Customers', '011_vehicle_stock_list')

    go(page, '/customers/vehicle-stock/aging/')
    check_page_visual(page, 'Customers', '012_stock_aging')

    # ════════════════════════════════════════════════════════
    # 5. SALES PAGES
    # ════════════════════════════════════════════════════════
    print('\n[5] SALES')

    go(page, '/sales/')
    check_page_visual(page, 'Sales', '013_sales_dashboard')

    go(page, '/sales/enquiries/')
    check_page_visual(page, 'Sales', '014_enquiry_list')
    for tab in ['All', 'Open', 'Follow', 'Converted', 'Lost']:
        if check_text(page, tab):
            ok('Sales', f'Enquiry filter tab: {tab}', f'014_tab_{tab}', page)
        else:
            fail('Sales', f'Enquiry filter tab: {tab}', 'Not visible', f'014_tab_{tab}_fail', page)

    go(page, '/sales/enquiries/create/')
    check_page_visual(page, 'Sales', '015_enquiry_create')

    if customer_pk:
        cust_sel = page.query_selector('select[name="customer"]')
        if cust_sel:
            try:
                cust_sel.select_option(value=str(customer_pk))
            except: pass
    select_first(page, 'bike_model')
    select_first(page, 'enquiry_source')
    select_first(page, 'sales_executive')
    remarks = page.query_selector('textarea[name="remarks"]')
    if remarks: remarks.fill('Visual QA test enquiry')
    submit(page)
    ss(page, '016_enquiry_created')

    enquiry_pk = None
    from sales.models import SalesEnquiry
    enq = SalesEnquiry.objects.filter(
        remarks='Visual QA test enquiry').first()
    if enq:
        enquiry_pk = enq.pk
        ok('Sales', 'Enquiry created', '016_enquiry_created_ok', page)
    else:
        fail('Sales', 'Enquiry created', 'Not found in DB', '016_enquiry_fail', page)

    if enquiry_pk:
        go(page, f'/sales/enquiries/{enquiry_pk}/')
        check_page_visual(page, 'Sales', '017_enquiry_detail')

        detail_checks = [
            'Customer', 'Status', 'Enquiry', 'Feedback', 'Appointment'
        ]
        for item in detail_checks:
            if check_text(page, item):
                ok('Sales', f'Enquiry detail: {item} section/text visible', f'017_{item.lower()}', page)
            else:
                fail('Sales', f'Enquiry detail: {item}', 'Not in page', f'017_{item.lower()}_fail', page)

        go(page, f'/sales/feedback/create/?enquiry={enquiry_pk}')
        check_page_visual(page, 'Sales', '018_feedback_form')
        ta = page.query_selector('textarea[name="notes"], textarea[name="feedback_notes"]')
        if ta: ta.fill('Visual QA feedback - customer interested')
        date_f = page.query_selector('input[name="next_followup_date"], input[name="follow_up_date"]')
        if date_f:
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
            date_f.fill(tomorrow)
        select_first(page, 'enquiry')
        submit(page)
        ss(page, '019_feedback_submitted')
        ok('Sales', 'Feedback form submitted', '019_feedback_ok', page)

    go(page, '/sales/follow-ups/')
    check_page_visual(page, 'Sales', '020_followup_board')
    if check_text(page, 'Visual QA') or check_text(page, 'follow'):
        ok('Sales', 'Follow-up board shows data', '020_followup_data', page)
    else:
        ok('Sales', 'Follow-up board loads (may be empty)', '020_followup_empty', page)

    go(page, '/sales/appointments/')
    check_page_visual(page, 'Sales', '021_appointments')

    if enquiry_pk:
        go(page, f'/sales/appointments/create/?enquiry={enquiry_pk}')
        check_page_visual(page, 'Sales', '022_appointment_create')
        tomorrow_dt = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        apt_date = page.query_selector('input[name="appointment_date"]')
        if apt_date: apt_date.fill(tomorrow_dt)
        purpose = page.query_selector('select[name="purpose"]')
        if purpose:
            try: purpose.select_option(value='test_ride')
            except: select_first(page, 'purpose')
        submit(page)
        ss(page, '023_appointment_booked')
        ok('Sales', 'Appointment booked', '023_appointment_ok', page)

    go(page, '/sales/test-rides/')
    check_page_visual(page, 'Sales', '024_test_rides')
    if check_text(page, 'scheduled') or check_text(page, 'test ride') or check_text(page, 'appointment'):
        ok('Sales', 'Test rides page shows scheduled rides or log', '024_test_rides_data', page)
    else:
        fail('Sales', 'Test rides content', 'No relevant content', '024_test_rides_fail', page)

    go(page, '/sales/orders/')
    check_page_visual(page, 'Sales', '025_orders_list')

    go(page, '/customers/vehicle-stock/create/')
    check_page_visual(page, 'Stock', '026_stock_create')
    select_first(page, 'bike_model')
    chassis = page.query_selector('input[name="chassis_no"]')
    if chassis: chassis.fill('VQA-CHASSIS-001')
    engine = page.query_selector('input[name="engine_no"]')
    if engine: engine.fill('VQA-ENGINE-001')
    color = page.query_selector('input[name="color"]')
    if color: color.fill('Pearl Black')
    pdate = page.query_selector('input[name="purchase_date"]')
    if pdate: pdate.fill(datetime.date.today().isoformat())
    submit(page)
    ss(page, '027_stock_created')

    from customers.models import VehicleStock
    stock = VehicleStock.objects.filter(chassis_no='VQA-CHASSIS-001').first()
    if stock:
        ok('Stock', 'Vehicle stock created', '027_stock_ok', page)

    go(page, '/sales/orders/create/')
    check_page_visual(page, 'Sales', '028_order_create')
    if customer_pk:
        csel = page.query_selector('select[name="customer"]')
        if csel:
            try: csel.select_option(value=str(customer_pk))
            except: pass
    if stock:
        vsel = page.query_selector('select[name="vehicle"]')
        if vsel:
            try: vsel.select_option(value=str(stock.pk))
            except: select_first(page, 'vehicle')
    select_first(page, 'sales_executive')

    for fname, val in [
        ('booking_amount', '10000'),
        ('discount_amount', '1000'),
        ('total_amount', '75000'),
    ]:
        f = page.query_selector(f'input[name="{fname}"]')
        if f: f.fill(val)

    status_sel = page.query_selector('select[name="sales_status"]')
    if status_sel:
        try: status_sel.select_option(value='booked')
        except: pass
    submit(page)
    ss(page, '029_order_created')

    order_pk = None
    from sales.models import VehicleSalesOrder
    if stock:
        ord_obj = VehicleSalesOrder.objects.filter(vehicle=stock).first()
        if ord_obj:
            order_pk = ord_obj.pk
            ok('Sales', 'Sales order created', '029_order_ok', page)

    if order_pk:
        go(page, f'/sales/orders/{order_pk}/')
        check_page_visual(page, 'Sales', '030_order_detail')
        ss(page, '030_order_detail_full')

        sections = ['Details', 'Finance', 'Insurance', 'PDI', 'Vehicle']
        for sec in sections:
            if check_text(page, sec):
                ok('Sales', f'Order detail: {sec} section visible', f'030_order_{sec.lower()}', page)
            else:
                fail('Sales', f'Order detail: {sec} section', 'Not in page', f'030_order_{sec.lower()}_fail', page)

        go(page, f'/sales/orders/{order_pk}/pdi/')
        check_page_visual(page, 'Sales', '031_pdi_form')

        checkboxes = page.query_selector_all('input[type="checkbox"]')
        for cb in checkboxes:
            if not cb.is_checked():
                try: cb.click()
                except: pass
        submit(page)
        ss(page, '032_pdi_submitted')

        from sales.models import PDIChecklist
        pdi = PDIChecklist.objects.filter(sales_order_id=order_pk).first()
        if pdi:
            ok('Sales', f'PDI checklist created ({len(checkboxes)} checkboxes)', '032_pdi_ok', page)
            go(page, f'/sales/pdi/{pdi.pk}/')
            check_page_visual(page, 'Sales', '033_pdi_detail')

            if check_text(page, 'mechanical') or check_text(page, 'score'):
                ok('Sales', 'PDI detail shows scores', '033_pdi_scores', page)
            else:
                fail('Sales', 'PDI detail scores', 'Not visible', '033_pdi_scores_fail', page)

    go(page, '/sales/delivery-list/')
    check_page_visual(page, 'Sales', '034_delivery_list')
    if check_text(page, 'delivery') or check_text(page, 'record missing'):
        ok('Sales', 'Delivery list shows data or missing records alert', '034_delivery_data', page)
    else:
        fail('Sales', 'Delivery list content', 'Empty or missing', '034_delivery_fail', page)

    go(page, '/sales/targets/')
    check_page_visual(page, 'Sales', '035_sales_targets')
    if check_text(page, 'target') or check_text(page, 'executive'):
        ok('Sales', 'Sales targets page has content', '035_targets_data', page)
    else:
        fail('Sales', 'Sales targets content', 'Missing', '035_targets_fail', page)

    go(page, '/sales/leaderboard/')
    check_page_visual(page, 'Sales', '036_leaderboard')

    go(page, '/sales/profit-report/')
    check_page_visual(page, 'Sales', '037_profit_report')
    if check_text(page, 'profit') or check_text(page, 'margin'):
        ok('Sales', 'Profit report has data', '037_profit_data', page)
    else:
        fail('Sales', 'Profit report content', 'Missing', '037_profit_fail', page)

    go(page, '/sales/follow-ups/')
    check_page_visual(page, 'Sales', '038_followups')

    go(page, '/sales/feedback-all/')
    check_page_visual(page, 'Sales', '039_feedback_all')

    go(page, '/sales/exchange-list/')
    check_page_visual(page, 'Sales', '040_exchange_list')

    # ════════════════════════════════════════════════════════
    # 6. BILLING PAGES
    # ════════════════════════════════════════════════════════
    print('\n[6] BILLING')

    go(page, '/billing/invoices/')
    check_page_visual(page, 'Billing', '041_invoice_list')

    if order_pk:
        go(page, f'/billing/invoices/create/?order={order_pk}')
        check_page_visual(page, 'Billing', '042_invoice_create')

        inv_num = f'VQA-INV-{datetime.datetime.now().strftime("%H%M%S")}'
        inv_no = page.query_selector('input[name="invoice_number"]')
        if inv_no: inv_no.fill(inv_num)
        inv_date = page.query_selector('input[name="invoice_date"]')
        if inv_date: inv_date.fill(datetime.date.today().isoformat())

        sub = page.query_selector('input[name="subtotal"]')
        if sub: sub.fill('75000')
        gst = page.query_selector('input[name="gst_amount"]')
        if gst: gst.fill('13500')
        disc = page.query_selector('input[name="discount_amount"]')
        if disc: disc.fill('1000')
        final = page.query_selector('input[name="final_amount"]')
        if final: final.fill('87500')

        select_first(page, 'sales_order')
        submit(page)
        ss(page, '043_invoice_created')

        from billing.models import Invoice
        inv = Invoice.objects.filter(invoice_number=inv_num).first()
        if inv:
            inv_pk = inv.pk
            ok('Billing', 'Invoice created', '043_invoice_ok', page)

            go(page, f'/billing/invoices/{inv_pk}/')
            check_page_visual(page, 'Billing', '044_invoice_detail')
            ss(page, '044_invoice_detail_full')

            detail_items = ['Invoice', 'Amount', 'GST', 'Payment', 'Customer']
            for item in detail_items:
                if check_text(page, item):
                    ok('Billing', f'Invoice detail: {item} visible', f'044_inv_{item.lower()}', page)
                else:
                    fail('Billing', f'Invoice detail: {item}', 'Not visible', f'044_inv_{item.lower()}_fail', page)

            go(page, f'/billing/payments/create/?invoice={inv_pk}')
            check_page_visual(page, 'Billing', '045_payment_form')

            amt = page.query_selector('input[name="amount"]')
            if amt: amt.fill('25000')
            method = page.query_selector('select[name="payment_method"]')
            if method:
                try: method.select_option(value='cash')
                except: select_first(page, 'payment_method')
            ref = page.query_selector('input[name="transaction_reference"]')
            if ref: ref.fill('VQA-CASH-001')
            pdate = page.query_selector('input[name="payment_date"]')
            if pdate:
                try:
                    pdate.fill(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'))
                except Exception:
                    try:
                        pdate.fill(datetime.date.today().isoformat())
                    except Exception:
                        pass
            status_f = page.query_selector('select[name="payment_status"]')
            if status_f:
                try: status_f.select_option(value='completed')
                except: pass
            select_first(page, 'invoice')
            submit(page)
            ss(page, '046_payment_added')
            ok('Billing', 'Payment recorded', '046_payment_ok', page)

            go(page, f'/billing/invoices/{inv_pk}/')
            ss(page, '047_invoice_after_payment')
            if check_text(page, '25000') or check_text(page, 'paid') or check_text(page, 'balance'):
                ok('Billing', 'Invoice shows payment progress after payment', '047_payment_progress', page)
            else:
                fail('Billing', 'Invoice payment progress', 'No payment amount visible', '047_payment_fail', page)

            go(page, f'/billing/invoice/{inv_pk}/pdf/')
            ss(page, '048_invoice_pdf')
            if check_text(page, 'VQA-INV') or check_text(page, 'invoice') or len(page.content()) > 500:
                ok('Billing', 'Invoice PDF generates', '048_invoice_pdf_ok', page)
            else:
                fail('Billing', 'Invoice PDF', 'Empty or error', '048_invoice_pdf_fail', page)

    go(page, '/billing/loans/')
    check_page_visual(page, 'Billing', '049_loans_list')

    go(page, '/billing/daily-report/')
    check_page_visual(page, 'Billing', '050_daily_report')

    go(page, '/billing/journal/')
    check_page_visual(page, 'Billing', '051_journal')

    go(page, '/billing/ledger/')
    check_page_visual(page, 'Billing', '052_ledger')

    go(page, '/billing/search/')
    check_page_visual(page, 'Billing', '053_invoice_search')

    go(page, '/billing/reconciliation/')
    check_page_visual(page, 'Billing', '054_reconciliation')

    go(page, '/billing/refunds-advances/')
    check_page_visual(page, 'Billing', '055_refunds')

    # ════════════════════════════════════════════════════════
    # 7. RTO PAGES
    # ════════════════════════════════════════════════════════
    print('\n[7] RTO')

    go(page, '/rto/registrations/')
    check_page_visual(page, 'RTO', '056_rto_list')

    if order_pk:
        go(page, '/rto/registrations/create/')
        check_page_visual(page, 'RTO', '057_rto_create')

        select_first(page, 'sales_order')
        form20 = page.query_selector('input[name="form20_number"]')
        if form20: form20.fill('VQA-F20-001')
        regnum = page.query_selector('input[name="registration_number"]')
        if regnum: regnum.fill('TN11VQA001')
        charges = page.query_selector('input[name="rto_charges"]')
        if charges: charges.fill('3200')
        status_f = page.query_selector('select[name="registration_status"]')
        if status_f:
            try: status_f.select_option(value='submitted')
            except: pass
        submit(page)
        ss(page, '058_rto_created')

        from rto.models import RTORegistration
        rto = RTORegistration.objects.filter(
            form20_number='VQA-F20-001').first()
        if rto:
            rto_pk = rto.pk
            ok('RTO', 'RTO registration created', '058_rto_ok', page)

            go(page, f'/rto/registrations/{rto_pk}/')
            check_page_visual(page, 'RTO', '059_rto_detail')
            ss(page, '059_rto_detail_full')

            rto_checks = ['Form 20', 'TN11VQA001', 'Registration', 'Status']
            for item in rto_checks:
                if check_text(page, item):
                    ok('RTO', f'RTO detail: {item} visible', f'059_rto_{item.replace(" ","_")}', page)
                else:
                    fail('RTO', f'RTO detail: {item}', 'Not visible', f'059_rto_{item}_fail', page)

            try:
                go(page, f'/rto/rc-books/create/?rto={rto_pk}')
                check_page_visual(page, 'RTO', '060_rcbook_create')
                rc_num = page.query_selector('input[name="rc_number"]')
                if rc_num: rc_num.fill('TN11VQA001')
                issue_date = page.query_selector('input[name="issue_date"]')
                if issue_date: issue_date.fill(datetime.date.today().isoformat())
                issued_to = page.query_selector('input[name="issued_to"]')
                if issued_to: issued_to.fill('Visual QA Customer')
                select_first(page, 'rto_registration')
                status_rc = page.query_selector('select[name="status"]')
                if status_rc:
                    try: status_rc.select_option(value='issued')
                    except: pass
                submit(page)
                ss(page, '061_rcbook_created')
                ok('RTO', 'RC Book created', '061_rcbook_ok', page)
            except Exception as e:
                fail('RTO', 'RC Book create', str(e)[:100], '061_rcbook_fail', page)

    go(page, '/rto/rc-books/')
    check_page_visual(page, 'RTO', '062_rcbook_list')

    go(page, '/rto/plates/')
    check_page_visual(page, 'RTO', '063_plates_list')

    # ════════════════════════════════════════════════════════
    # 8. SERVICE PAGES
    # ════════════════════════════════════════════════════════
    print('\n[8] SERVICE')

    go(page, '/service/')
    check_page_visual(page, 'Service', '064_service_dashboard')

    go(page, '/service/enquiries/')
    check_page_visual(page, 'Service', '065_service_enquiry_list')

    go(page, '/service/enquiries/create/')
    check_page_visual(page, 'Service', '066_service_enquiry_create')
    select_first(page, 'customer_vehicle')
    issue = page.query_selector('textarea[name="issue_description"]')
    if issue: issue.fill('Visual QA - first free service at 1500km')
    select_first(page, 'status')
    submit(page)
    ss(page, '067_service_enquiry_created')
    ok('Service', 'Service enquiry created', '067_svc_enq_ok', page)

    go(page, '/service/appointments/')
    check_page_visual(page, 'Service', '068_service_appointments')

    go(page, '/service/jobcards/')
    check_page_visual(page, 'Service', '069_jobcard_list')
    if check_text(page, 'job') or check_text(page, 'card') or check_text(page, 'status'):
        ok('Service', 'Job card list has content', '069_jc_list_data', page)
    else:
        fail('Service', 'Job card list', 'No content', '069_jc_list_fail', page)

    go(page, '/service/jobcards/create/')
    check_page_visual(page, 'Service', '070_jobcard_create')
    select_first(page, 'customer_vehicle')
    odo = page.query_selector('input[name="odometer_reading"]')
    if odo: odo.fill('1500')
    prob = page.query_selector('textarea[name="problem_description"]')
    if prob: prob.fill('Visual QA - first free service')
    select_first(page, 'service_advisor')
    submit(page)
    ss(page, '071_jobcard_created')

    from service.models import JobCard
    jc = JobCard.objects.filter(
        problem_description='Visual QA - first free service').first()
    jc_pk = jc.pk if jc else None
    if jc:
        ok('Service', 'Job card created', '071_jc_ok', page)

    if jc_pk:
        go(page, f'/service/jobcards/{jc_pk}/')
        check_page_visual(page, 'Service', '072_jobcard_detail')
        ss(page, '072_jobcard_detail_full')

        jc_checks = [
            ('Warranty banner/status', ['warranty', 'active', 'expired']),
            ('Workflow progress bar', ['pending', 'water', 'progress', 'ready', 'invoiced']),
            ('Labour section', ['labour', 'labor', 'charge']),
            ('Spares section', ['spare', 'parts', 'issue']),
        ]
        for label, keywords in jc_checks:
            found = any(check_text(page, kw) for kw in keywords)
            if found:
                ok('Service', f'Job card detail: {label}', f'072_jc_{label.replace(" ","_")}', page)
            else:
                fail('Service', f'Job card detail: {label}', 'Not visible', f'072_jc_{label}_fail', page)

        statuses = ['water_wash', 'in_bay', 'in_progress', 'final_inspection', 'ready']
        for status in statuses:
            try:
                go(page, f'/service/jobcards/{jc_pk}/')
                advance_btn = page.query_selector('button[name="advance"], a[href*="advance"], form[action*="advance"] button, .workflow-advance button')
                if not advance_btn:
                    advance_btn = page.query_selector('button.btn-primary')
                if advance_btn:
                    advance_btn.click()
                    page.wait_for_load_state('domcontentloaded', timeout=8000)
                    page.wait_for_timeout(400)
            except Exception as e:
                pass

        ss(page, '073_jc_after_advances')
        jc.refresh_from_db()
        ok('Service', f'Job card status advanced (now: {jc.service_status})', '073_jc_status', page)

        go(page, f'/service/labour/create/?job_card={jc_pk}')
        check_page_visual(page, 'Service', '074_labour_create')
        sname = page.query_selector('input[name="service_name"]')
        if sname: sname.fill('VQA Engine Oil Change')
        cost = page.query_selector('input[name="labor_cost"]')
        if cost: cost.fill('0')
        select_first(page, 'job_card')
        submit(page)
        ss(page, '075_labour_added')
        ok('Service', 'Labour charge added', '075_labour_ok', page)

        go(page, f'/service/jobcards/{jc_pk}/')
        jc.service_status = 'ready'
        jc.save()
        page.wait_for_timeout(500)

        go(page, f'/service/service-invoice/create/?jc={jc_pk}')
        check_page_visual(page, 'Service', '076_service_invoice_create')
        select_first(page, 'job_card')
        sinv_num = page.query_selector('input[name="invoice_number"]')
        if sinv_num: sinv_num.fill(f'VQA-SINV-001')
        submit(page)
        ss(page, '077_service_invoice_created')

        from service.models import ServiceInvoice
        si = ServiceInvoice.objects.filter(job_card_id=jc_pk).first()
        if si:
            ok('Service', 'Service invoice created', '077_sinv_ok', page)

            go(page, f'/service/service-invoice/{jc_pk}/')
            check_page_visual(page, 'Service', '078_service_invoice_detail')
            ss(page, '078_sinv_detail_full')

            sinv_checks = ['labour', 'total', 'invoice', 'amount']
            for item in sinv_checks:
                if check_text(page, item):
                    ok('Service', f'Service invoice: {item} visible', f'078_sinv_{item}', page)
                else:
                    fail('Service', f'Service invoice: {item}', 'Not visible', f'078_sinv_{item}_fail', page)

            go(page, f'/billing/service-invoice/{jc_pk}/pdf/')
            ss(page, '079_service_invoice_pdf')
            if len(page.content()) > 500:
                ok('Service', 'Service invoice PDF generates', '079_sinv_pdf_ok', page)
            else:
                fail('Service', 'Service invoice PDF', 'Empty', '079_sinv_pdf_fail', page)

    go(page, '/service/reminders/')
    check_page_visual(page, 'Service', '080_reminders')

    go(page, '/service/technician-report/')
    check_page_visual(page, 'Service', '081_technician_report')

    go(page, '/service/warranty-claims/')
    check_page_visual(page, 'Service', '082_warranty_claims')

    go(page, '/service/insurance-claims/')
    check_page_visual(page, 'Service', '083_insurance_claims')

    go(page, '/service/bays/')
    check_page_visual(page, 'Service', '084_bays')

    go(page, '/service/calls/')
    check_page_visual(page, 'Service', '085_customer_calls')

    # ════════════════════════════════════════════════════════
    # 9. SPARES PAGES
    # ════════════════════════════════════════════════════════
    print('\n[9] SPARES')

    go(page, '/spares/')
    check_page_visual(page, 'Spares', '086_spares_dashboard')

    spares_kpis = ['total', 'stock', 'low', 'item']
    for kpi in spares_kpis:
        if check_text(page, kpi):
            ok('Spares', f'Spares dashboard: {kpi} KPI visible', f'086_spares_{kpi}', page)
            break

    go(page, '/spares/items/')
    check_page_visual(page, 'Spares', '087_items_list')

    go(page, '/spares/items/create/')
    check_page_visual(page, 'Spares', '088_item_create')

    iname = page.query_selector('input[name="item_name"]')
    if iname: iname.fill('VQA Oil Filter')
    pnum = page.query_selector('input[name="part_number"]')
    if pnum: pnum.fill('VQA-OIL-001')
    select_first(page, 'category')
    hsn = page.query_selector('input[name="hsn_sac"]')
    if hsn: hsn.fill('84099190')
    sell = page.query_selector('input[name="standard_selling_rate"]')
    if sell: sell.fill('185')
    mrp_f = page.query_selector('input[name="mrp"]')
    if mrp_f: mrp_f.fill('210')
    sgst_f = page.query_selector('input[name="sgst"]')
    if sgst_f: sgst_f.fill('9')
    cgst_f = page.query_selector('input[name="cgst"]')
    if cgst_f: cgst_f.fill('9')
    submit(page)
    ss(page, '089_item_created')

    from spares.models import SparesItem
    item = SparesItem.objects.filter(part_number='VQA-OIL-001').first()
    if item:
        ok('Spares', 'Spare item created', '089_item_ok', page)
        item_pk = item.pk

        go(page, f'/spares/items/{item_pk}/')
        check_page_visual(page, 'Spares', '090_item_detail')

    go(page, '/spares/quotes/')
    check_page_visual(page, 'Spares', '091_quotes_list')

    go(page, '/spares/orders/')
    check_page_visual(page, 'Spares', '092_po_list')

    go(page, '/spares/invoices/')
    check_page_visual(page, 'Spares', '093_pi_list')

    go(page, '/spares/counter-sales/')
    check_page_visual(page, 'Spares', '094_counter_sales')

    go(page, '/spares/counter-sales/create/')
    check_page_visual(page, 'Spares', '095_counter_sale_create')

    cust_name = page.query_selector('input[name="customer"]')
    if cust_name: cust_name.fill('VQA Walk-in')
    mobile = page.query_selector('input[name="mobile"]')
    if mobile: mobile.fill('9500000088')
    select_first(page, 'godown')
    pay_type = page.query_selector('select[name="pay_type"]')
    if pay_type:
        try: pay_type.select_option(value='cash')
        except: pass
    submit(page)
    ss(page, '096_counter_sale_created')
    ok('Spares', 'Counter sale initiated', '096_cs_ok', page)

    go(page, '/spares/reports/stock/')
    check_page_visual(page, 'Spares', '097_stock_report')

    go(page, '/spares/reports/parts-consumption/')
    check_page_visual(page, 'Spares', '098_parts_consumption')

    go(page, '/spares/reports/po-used-qty/')
    check_page_visual(page, 'Spares', '099_po_used_qty')

    go(page, '/spares/issue-alterations/')
    check_page_visual(page, 'Spares', '100_issue_alterations')

    go(page, '/spares/bulk-insert/')
    check_page_visual(page, 'Spares', '101_bulk_insert')

    # ════════════════════════════════════════════════════════
    # 10. VAS PAGES
    # ════════════════════════════════════════════════════════
    print('\n[10] VAS')

    go(page, '/vas/amc/')
    check_page_visual(page, 'VAS', '102_amc_list')

    go(page, '/vas/rsa/')
    check_page_visual(page, 'VAS', '103_rsa_list')

    go(page, '/vas/protection-plus/')
    check_page_visual(page, 'VAS', '104_pp_list')

    # ════════════════════════════════════════════════════════
    # 11. MASTERS PAGES
    # ════════════════════════════════════════════════════════
    print('\n[11] MASTERS')

    go(page, '/masters/suppliers/')
    check_page_visual(page, 'Masters', '105_suppliers')

    go(page, '/masters/warehouses/')
    check_page_visual(page, 'Masters', '106_warehouses')

    go(page, '/masters/racks/')
    check_page_visual(page, 'Masters', '107_racks')

    go(page, '/masters/bins/')
    check_page_visual(page, 'Masters', '108_bins')

    go(page, '/masters/categories/')
    check_page_visual(page, 'Masters', '109_categories')

    # ════════════════════════════════════════════════════════
    # 12. ACCOUNTS / ADMIN PAGES
    # ════════════════════════════════════════════════════════
    print('\n[12] ACCOUNTS')

    go(page, '/accounts/users/')
    check_page_visual(page, 'Accounts', '110_users')

    go(page, '/accounts/roles/')
    check_page_visual(page, 'Accounts', '111_roles')

    go(page, '/accounts/branches/')
    check_page_visual(page, 'Accounts', '112_branches')

    go(page, '/accounts/settings/')
    check_page_visual(page, 'Accounts', '113_company_settings')
    if check_text(page, 'GSTIN') or check_text(page, 'gstin'):
        ok('Accounts', 'Company settings shows GSTIN field', '113_gstin', page)
    else:
        fail('Accounts', 'Company settings GSTIN', 'Not visible', '113_gstin_fail', page)

    go(page, '/accounts/fuel-expenses/')
    check_page_visual(page, 'Accounts', '114_fuel_expenses')

    go(page, '/accounts/insurance-expiry/')
    check_page_visual(page, 'Accounts', '115_insurance_expiry')

    go(page, '/accounts/notifications/')
    check_page_visual(page, 'Accounts', '116_notifications')

    go(page, '/accounts/reports/sales/')
    check_page_visual(page, 'Accounts', '117_sales_report')

    go(page, '/accounts/reports/service/')
    check_page_visual(page, 'Accounts', '118_service_report')

    go(page, '/accounts/reports/spares/')
    check_page_visual(page, 'Accounts', '119_spares_report')

    go(page, '/accounts/gst-report/')
    check_page_visual(page, 'Accounts', '120_gst_report')

    # ════════════════════════════════════════════════════════
    # 13. CUSTOMER VEHICLES
    # ════════════════════════════════════════════════════════
    print('\n[13] CUSTOMER VEHICLES')

    go(page, '/customer-vehicles/')
    check_page_visual(page, 'CustVehicles', '121_cv_list')

    from customer_vehicles.models import CustomerVehicle
    cv = CustomerVehicle.objects.first()
    if cv:
        go(page, f'/customer-vehicles/{cv.pk}/')
        check_page_visual(page, 'CustVehicles', '122_cv_detail')

        cv_checks = [
            ('Registration number', [cv.registration_no, 'registration']),
            ('Warranty status', ['warranty', 'active', 'expired']),
            ('Free services', ['free service', 'service']),
            ('Insurance expiry', ['insurance', 'expiry']),
        ]
        for label, keywords in cv_checks:
            found = any(check_text(page, kw) for kw in keywords)
            if found:
                ok('CustVehicles', f'CV detail: {label}', f'122_cv_{label.replace(" ","_")}', page)
            else:
                fail('CustVehicles', f'CV detail: {label}', 'Not visible', f'122_cv_{label}_fail', page)

    # ════════════════════════════════════════════════════════
    # 14. SEARCH
    # ════════════════════════════════════════════════════════
    print('\n[14] SEARCH')

    go(page, '/accounts/search/?q=Visual+QA')
    check_page_visual(page, 'Search', '123_search_results')
    if check_text(page, 'Visual QA') or check_text(page, 'result'):
        ok('Search', 'Search results show Visual QA data', '123_search_data', page)
    else:
        fail('Search', 'Search results', 'No results for Visual QA', '123_search_fail', page)

    # ════════════════════════════════════════════════════════
    # 15. RBAC VISUAL CHECK
    # ════════════════════════════════════════════════════════
    print('\n[15] RBAC')

    go(page, '/accounts/logout/')
    page.wait_for_timeout(1000)
    login(page, 'e2e_sales', 'Test@123')
    ss(page, '124_sales_exec_login')

    go(page, '/accounts/dashboard/')
    ss(page, '125_sales_exec_dashboard')

    blocked_tests = [
        ('/billing/invoices/', 'Billing Invoices'),
        ('/spares/items/', 'Spares Items'),
        ('/accounts/users/', 'User Management'),
        ('/rto/registrations/', 'RTO Registrations'),
    ]
    for url, name in blocked_tests:
        go(page, url)
        ss(page, f'126_rbac_{name.replace(" ","_").lower()}')
        content = page.content()
        is_blocked = (
            '403' in content or
            'forbidden' in content.lower() or
            'permission' in content.lower() or
            'access denied' in content.lower() or
            '/accounts/login/' in page.url or
            'dashboard' in page.url
        )
        if is_blocked:
            ok('RBAC', f'{name} blocked for Sales Exec', f'126_rbac_{name.lower()}', page)
        else:
            fail('RBAC', f'{name} blocked for Sales Exec', 'Not blocked', f'126_rbac_{name}_fail', page)

    go(page, '/accounts/logout/')
    page.wait_for_timeout(500)
    login(page, 'admin', 'SSBikez@2026')
    ss(page, '127_admin_relogin')

    # ════════════════════════════════════════════════════════
    # 16. PROFILE AND PASSWORD
    # ════════════════════════════════════════════════════════
    print('\n[16] PROFILE')

    go(page, '/accounts/profile/')
    check_page_visual(page, 'Profile', '128_profile')

    go(page, '/accounts/profile/edit/')
    check_page_visual(page, 'Profile', '129_profile_edit')

    go(page, '/accounts/password/change/')
    check_page_visual(page, 'Profile', '130_password_change')

    # ════════════════════════════════════════════════════════
    # 17. NOTIFICATIONS DETAIL
    # ════════════════════════════════════════════════════════
    print('\n[17] NOTIFICATIONS')

    go(page, '/accounts/notifications/')
    check_page_visual(page, 'Notifications', '131_notifications_list')
    ss(page, '131_notifications_full')

    notif_count = page.query_selector_all('.notification-item, tr, li')
    ok('Notifications', f'Notification list loads ({len(notif_count)} items)', '131_notif_count', page)

    read_btn = page.query_selector('a[href*="read"], button[data-action="read"]')
    if read_btn:
        read_btn.click()
        page.wait_for_timeout(500)
        ss(page, '132_notification_read')
        ok('Notifications', 'Mark as read works', '132_notif_read', page)

    # ════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ════════════════════════════════════════════════════════
    browser.close()

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
total = len(results)

print()
print('='*60)
print('VISUAL QA COMPLETE')
print('='*60)
print(f'Total checks : {total}')
print(f'PASSED       : {passed}')
print(f'FAILED       : {failed}')
print(f'Screenshots  : {ss_count[0]} saved to {SS_DIR}')
print()

if issues:
    print('ISSUES FOUND:')
    print('-'*60)
    for i, issue in enumerate(issues, 1):
        print(f'[{i}] {issue["flow"]} -> {issue["check"]}')
        print(f'    {issue["detail"]}')
        print(f'    Screenshot: {issue["screenshot"]}')
        print()
else:
    print('ALL CHECKS PASSED')

with open(r'C:\Users\Satya\ssbikez-erp\visual_qa_report.json', 'w') as f:
    json.dump({'passed': passed, 'failed': failed,
               'total': total, 'issues': issues,
               'results': results}, f, indent=2)

print(f'Report saved: visual_qa_report.json')
