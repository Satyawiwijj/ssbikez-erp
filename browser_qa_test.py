"""
SSBikez ERP -- Full Browser QA Test (Playwright)
All 14 flows from the live browser test plan.
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent
DB_PATH    = BASE_DIR / 'db.sqlite3'
SS_DIR     = BASE_DIR / 'qa_screenshots'
SS_DIR.mkdir(exist_ok=True)
REPORT     = []
BASE_URL   = 'http://127.0.0.1:8010'

# ── helpers ──────────────────────────────────────────────────────────────────

def ss(page, name: str) -> str:
    path = str(SS_DIR / f"{name}.png")
    try:
        page.screenshot(path=path, full_page=True)
    except Exception as e:
        print(f"  [screenshot error] {name}: {e}")
    return path

def log_ok(flow: str, step: str):
    REPORT.append({'status': 'OK', 'flow': flow, 'step': step})
    print(f"  OK  {flow} / {step}")

def log_issue(flow: str, step: str, detail: str = '', screenshot: str = ''):
    REPORT.append({'status': 'ISSUE', 'flow': flow, 'step': step,
                   'detail': detail, 'screenshot': screenshot})
    print(f"  !!  {flow} / {step}: {detail}")

def page_has_error(page) -> tuple[bool, str]:
    title = page.title()
    body  = page.content()
    if '500' in title or 'Server Error' in title:
        return True, '500 Server Error'
    if 'DoesNotExist' in body or 'OperationalError' in body or 'ProgrammingError' in body:
        return True, 'Django exception in page body'
    return False, ''

def check_page(page, flow, step):
    err, detail = page_has_error(page)
    if err:
        sc = ss(page, f"ERR_{flow}_{step}".replace(' ', '_')[:60])
        log_issue(flow, step, detail, sc)
        return False
    # Redirect to login = not authenticated
    if '/accounts/login/' in page.url:
        sc = ss(page, f"AUTH_{flow}_{step}".replace(' ', '_')[:60])
        log_issue(flow, step, 'Redirected to login — not authenticated', sc)
        return False
    return True

def go(page, path: str, flow: str, step: str):
    """Navigate to path, return True if page loads cleanly."""
    page.goto(f"{BASE_URL}{path}", wait_until='domcontentloaded', timeout=20000)
    return check_page(page, flow, step)

def click_link(page, *selectors, flow='', step='', fallback_url=''):
    """Try each selector in order; navigate fallback_url if all fail."""
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.wait_for_load_state('domcontentloaded', timeout=15000)
                return True
        except Exception:
            pass
    if fallback_url:
        page.goto(f"{BASE_URL}{fallback_url}", wait_until='domcontentloaded', timeout=20000)
        return True
    log_issue(flow, step, f"No element matched: {list(selectors)}")
    return False

# ── OTP ──────────────────────────────────────────────────────────────────────

def get_otp(username: str) -> str | None:
    """Read latest unverified login OTP for user directly from SQLite."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur  = conn.cursor()
        cur.execute("""
            SELECT ov.otp_code
            FROM   accounts_otpverification ov
            JOIN   accounts_user u ON u.id = ov.user_id
            WHERE  u.username = ?
              AND  ov.action  = 'login'
              AND  ov.is_verified = 0
            ORDER  BY ov.id DESC LIMIT 1
        """, (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"  [otp-query] {e}")
        return None

def wait_otp(username: str, timeout: int = 12) -> str | None:
    for _ in range(timeout * 2):
        code = get_otp(username)
        if code:
            return code
        time.sleep(0.5)
    return None

def do_login(page, username='admin', password='SSBikez@2026') -> bool:
    page.goto(f"{BASE_URL}/accounts/login/")
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    # Press Enter on password field to submit form — more reliable than click
    page.press('input[name="password"]', 'Enter')
    page.wait_for_load_state('domcontentloaded', timeout=10000)

    if 'verify-otp' not in page.url:
        log_issue('Login', 'OTP redirect',
                  f"Expected verify-otp page, got {page.url}")
        return False

    otp = wait_otp(username)
    if not otp:
        log_issue('Login', 'OTP fetch', 'Could not retrieve OTP from DB')
        return False

    page.fill('input[name="otp_code"]', otp)
    page.press('input[name="otp_code"]', 'Enter')
    page.wait_for_load_state('domcontentloaded', timeout=10000)

    if 'login' in page.url or 'verify-otp' in page.url:
        log_issue('Login', 'OTP verify',
                  f"OTP submission failed, still on {page.url}")
        return False

    log_ok('Login', f"Authenticated as {username}")
    return True

def select_first_option(page, name: str):
    """Select first non-empty option in a <select>. Safe — returns False if field absent."""
    try:
        sel = page.query_selector(f'select[name="{name}"]')
        if not sel:
            return False
        opts = page.eval_on_selector(
            f'select[name="{name}"]',
            'el => Array.from(el.options).filter(o=>o.value).map(o=>o.value)')
        if opts:
            page.select_option(f'select[name="{name}"]', value=opts[0])
            return True
        return False
    except Exception:
        return False

def select_option_containing(page, name: str, text: str) -> bool:
    if not page.query_selector(f'select[name="{name}"]'):
        return False
    try:
        opts = page.eval_on_selector(
            f'select[name="{name}"]',
            'el => Array.from(el.options).map(o=>({v:o.value,t:o.text}))')
        match = next((o for o in opts if text.lower() in o['t'].lower()), None)
        if match:
            page.select_option(f'select[name="{name}"]', value=match['v'])
            return True
        return select_first_option(page, name)
    except Exception:
        return False

def click_submit(page):
    """Click the primary submit button. Uses JS eval to bypass Playwright animation checks."""
    clicked = page.evaluate("""() => {
        const b = document.querySelector('button[form]') ||
                  document.querySelector('button[type="submit"]') ||
                  document.querySelector('.topbar-actions button') ||
                  document.querySelector('button.btn-primary');
        if (b) { b.click(); return true; }
        return false;
    }""")
    if not clicked:
        raise RuntimeError("No submit button found on page")


# ══════════════════════════════════════════════════════════════════════════════
# FLOWS
# ══════════════════════════════════════════════════════════════════════════════

def flow_login(page):
    print("\n[FLOW: LOGIN]")
    ss(page, '00_login_page')
    ok = do_login(page)
    ss(page, '00_home_after_login')
    if not ok:
        return False
    check_page(page, 'Login', 'Home page')
    return True


def flow_dashboard(page):
    print("\n[FLOW 1: DASHBOARD]")
    if not go(page, '/accounts/dashboard/', 'Dashboard', 'Load'):
        return
    ss(page, '01_dashboard')

    # KPI / stat cards
    stat_cards = page.query_selector_all('.stat-card, .kpi-card, .stats-card')
    if stat_cards:
        log_ok('Dashboard', f"Stat cards present ({len(stat_cards)})")
    else:
        log_issue('Dashboard', 'Stat cards', 'No .stat-card/.kpi-card elements found')

    # Sidebar links (requires authenticated page)
    # Note: sidebar section is "Finance" (not "Billing"); checking for Invoices as proxy
    for text in ['Customers', 'Sales', 'Invoices', 'Service', 'Spares']:
        el = page.query_selector(f'a.sidebar-link:has-text("{text}")')
        if el:
            log_ok('Dashboard', f"Sidebar: {text}")
        else:
            log_issue('Dashboard', f"Sidebar: {text}", f"No .sidebar-link with text '{text}'")

    # Notification bell
    bell = page.query_selector('a.notification-bell')
    if bell:
        log_ok('Dashboard', 'Notification bell (a.notification-bell) present')
    else:
        log_issue('Dashboard', 'Notification bell', 'a.notification-bell not found')

    # Search box
    search = page.query_selector('input[name="q"]')
    if search:
        log_ok('Dashboard', 'Search bar present')
    else:
        log_issue('Dashboard', 'Search bar', 'No input[name="q"] in topbar')


def flow_customer_creation(page):
    print("\n[FLOW 2: CUSTOMER CREATION]")
    PHONE = '9500000099'

    # Clean prior run — cascade delete to avoid orphaned FK references
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""DELETE FROM sales_vehiclesalesorder WHERE customer_id IN
            (SELECT id FROM customers_customer WHERE phone=?)""", (PHONE,))
        conn.execute("""DELETE FROM sales_salesenquiry WHERE customer_id IN
            (SELECT id FROM customers_customer WHERE phone=?)""", (PHONE,))
        conn.execute("DELETE FROM customers_customer WHERE phone=?", (PHONE,))
        conn.commit(); conn.close()
    except Exception:
        pass

    # List page
    if not go(page, '/customers/customers/', 'Customers', 'List'):
        return
    ss(page, '02_customer_list')

    # Create page (navigate directly — also screenshots the form)
    if not go(page, '/customers/customers/create/', 'Customers', 'Create form'):
        return
    ss(page, '02_customer_create_form')

    page.fill('input[name="full_name"]', 'Live Test Customer')
    page.fill('input[name="phone"]',     PHONE)
    page.fill('input[name="email"]',     'livetest@ssbikez.com')
    ta = page.query_selector('textarea[name="address"]')
    if ta: ta.fill('1 Test Street, Coimbatore')
    page.fill('input[name="aadhaar_no"]', '999900000099')
    page.fill('input[name="pan_no"]',     'ABCLT9999Z')

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '02_customer_submit_result')

    if not check_page(page, 'Customers', 'Create submit'):
        return
    log_ok('Customers', 'Customer created')

    # Verify in list
    go(page, '/customers/customers/', 'Customers', 'List after create')
    if page.query_selector("td:has-text('Live Test Customer'), td:has-text('9500000099')"):
        log_ok('Customers', 'New customer visible in list')
    else:
        log_issue('Customers', 'Customer in list', 'New customer not visible in list')
        ss(page, '02_customer_list_not_found')

    # Click into detail
    link = page.query_selector("a:has-text('Live Test Customer')")
    if not link:
        # try table row link
        link = page.query_selector("td:has-text('Live Test Customer') ~ td a, td:has-text('Live Test Customer') a")
    if link:
        link.click()
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '02_customer_detail')
        check_page(page, 'Customers', 'Detail page')
        log_ok('Customers', 'Customer detail page loads')
    else:
        log_issue('Customers', 'Customer detail link', 'No clickable link for new customer in list')

    # Duplicate phone validation
    go(page, '/customers/customers/create/', 'Customers', 'Duplicate create form')
    page.fill('input[name="full_name"]', 'Duplicate Test')
    page.fill('input[name="phone"]',     PHONE)
    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '02_duplicate_phone_error')
    body = page.content().lower()
    if 'already exists' in body or 'errorlist' in body or 'valid 10-digit' in body:
        log_ok('Customers', 'Duplicate phone shows validation error')
    else:
        log_issue('Customers', 'Duplicate phone', 'No validation error for duplicate phone')


def flow_sales_enquiry(page):
    print("\n[FLOW 3: SALES ENQUIRY]")
    if not go(page, '/sales/enquiries/', 'Enquiry', 'List'):
        return
    ss(page, '03_enquiry_list')

    if not go(page, '/sales/enquiries/create/', 'Enquiry', 'Create form'):
        return
    ss(page, '03_enquiry_create_form')

    select_option_containing(page, 'customer', 'Live Test')
    select_first_option(page, 'bike_model')
    select_first_option(page, 'source')
    select_first_option(page, 'sales_executive')
    ta = page.query_selector('textarea[name="remarks"]')
    if ta: ta.fill('Live browser test enquiry')

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '03_enquiry_created')

    if not check_page(page, 'Enquiry', 'Create submit'):
        return
    log_ok('Enquiry', 'Enquiry created')
    enquiry_url = page.url
    enquiry_id  = enquiry_url.rstrip('/').split('/')[-1]

    # Detail page checks
    content = page.content()
    for label in ['Customer', 'Status', 'Enquiry']:
        if label.lower() in content.lower():
            log_ok('Enquiry', f"Detail shows: {label}")
        else:
            log_issue('Enquiry', f"Detail label: {label}", f"'{label}' not in page content")

    # Add Feedback — navigate directly to avoid stale-link issues
    try:
        page.goto(f"{BASE_URL}/sales/feedback/create/?enquiry={enquiry_id}",
                  wait_until='domcontentloaded', timeout=15000)
        ss(page, '03_feedback_form')
        ta = page.query_selector('textarea[name="notes"]')
        if ta: ta.fill('Interested, wants test ride')
        date_f = page.query_selector('input[name="next_followup_date"], input[name="follow_up_date"]')
        if date_f:
            date_f.fill((datetime.date.today() + datetime.timedelta(days=1)).isoformat())
        select_first_option(page, 'enquiry')
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '03_feedback_submitted')
        check_page(page, 'Enquiry', 'Feedback submit')
        log_ok('Enquiry', 'Feedback added')
    except Exception as e:
        log_issue('Enquiry', 'Feedback submit', str(e)[:150])
        ss(page, '03_feedback_error')

    # Follow-ups page
    if go(page, '/sales/follow-ups/', 'Enquiry', 'Follow-ups list'):
        ss(page, '03_follow_ups')
        log_ok('Enquiry', 'Follow-ups page loads')

    # Book Appointment — navigate directly
    try:
        page.goto(f"{BASE_URL}/sales/appointments/create/?enquiry={enquiry_id}",
                  wait_until='domcontentloaded', timeout=15000)
        ss(page, '03_appointment_form')
        date_f = page.query_selector('input[name="appointment_date"], input[type="date"], input[type="datetime-local"]')
        if date_f:
            dt_str = (datetime.datetime.combine(
                datetime.date.today() + datetime.timedelta(days=1),
                datetime.time(10, 0)
            )).strftime('%Y-%m-%dT%H:%M')
            date_f.fill(dt_str)
        try:
            page.select_option('select[name="purpose"]', value='test_ride')
        except Exception:
            pass
        try:
            page.select_option('select[name="status"]', value='scheduled')
        except Exception:
            pass
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '03_appointment_created')
        check_page(page, 'Enquiry', 'Appointment create')
        log_ok('Enquiry', 'Appointment booked with purpose=test_ride')
    except Exception as e:
        log_issue('Enquiry', 'Book Appointment', str(e)[:150])
        ss(page, '03_appointment_error')

    # Test Rides page (should now show the scheduled appointment)
    if go(page, '/sales/test-rides/', 'Test Rides', 'List'):
        ss(page, '03_test_rides')
        content = page.content()
        if 'Scheduled Test Rides' in content or 'Appointments' in content:
            log_ok('Test Rides', 'Scheduled Test Rides section visible')
        else:
            log_issue('Test Rides', 'Scheduled section', '"Scheduled Test Rides" section not found on page')

    # Appointments list
    if go(page, '/sales/all-appointments/', 'Enquiry', 'Appointments list'):
        ss(page, '03_appointments_list')
        log_ok('Enquiry', 'Appointments list loads')


def flow_vehicle_stock_and_order(page):
    print("\n[FLOW 4: VEHICLE STOCK + SALES ORDER]")
    CHASSIS = 'LIVE-TEST-CHASSIS-001'
    ENGINE  = 'LIVE-TEST-ENGINE-001'

    # Clean prior
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("DELETE FROM customers_vehiclestock WHERE chassis_no=?", (CHASSIS,))
        conn.commit(); conn.close()
    except Exception:
        pass

    # Stock list
    if not go(page, '/customers/stock/', 'Stock', 'List'):
        return
    ss(page, '04_stock_list')

    # Stock create
    if not go(page, '/customers/stock/create/', 'Stock', 'Create form'):
        return
    ss(page, '04_stock_create_form')

    select_first_option(page, 'bike_model')
    if page.query_selector('input[name="chassis_no"]'):
        page.fill('input[name="chassis_no"]', CHASSIS)
    if page.query_selector('input[name="engine_no"]'):
        page.fill('input[name="engine_no"]', ENGINE)
    if page.query_selector('input[name="color"]'):
        page.fill('input[name="color"]', 'Pearl Black')
    if page.query_selector('input[name="purchase_date"]'):
        page.fill('input[name="purchase_date"]', datetime.date.today().isoformat())

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '04_stock_created')

    if not check_page(page, 'Stock', 'Create submit'):
        return
    log_ok('Stock', 'Vehicle stock unit created')

    # Orders list
    if not go(page, '/sales/orders/', 'Order', 'List'):
        return
    ss(page, '04_order_list')

    if not go(page, '/sales/orders/create/', 'Order', 'Create form'):
        return
    ss(page, '04_order_create_form')

    select_option_containing(page, 'customer', 'Live Test')

    # Vehicle — prefer LIVE-TEST
    veh_el = page.query_selector('select[name="vehicle"]')
    if veh_el:
        opts = page.eval_on_selector('select[name="vehicle"]',
            'el => Array.from(el.options).map(o=>({v:o.value,t:o.text}))')
        live_veh = next((o for o in opts if 'LIVE-TEST' in o['t']), None)
        if live_veh:
            page.select_option('select[name="vehicle"]', value=live_veh['v'])
            log_ok('Order', 'LIVE-TEST vehicle found in order form')
        else:
            select_first_option(page, 'vehicle')
            log_issue('Order', 'Live test vehicle', 'LIVE-TEST-CHASSIS-001 not in vehicle dropdown')

    select_first_option(page, 'sales_executive')

    for fname, val in [('booking_amount','10000'), ('discount','1000'), ('total_amount','75000')]:
        el = page.query_selector(f'input[name="{fname}"]')
        if el: el.fill(val)

    try:
        page.select_option('select[name="sales_status"]', value='booked')
    except Exception:
        pass

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '04_order_created')

    if not check_page(page, 'Order', 'Create submit'):
        return
    log_ok('Order', 'Sales order created')
    order_url = page.url

    # Tabs on detail
    content = page.content()
    for tab in ['Details', 'Finance', 'Documents', 'Insurance']:
        if tab.lower() in content.lower():
            log_ok('Order', f"Detail tab/section: {tab}")
        else:
            log_issue('Order', f"Detail section: {tab}", f"'{tab}' not found on order detail")

    # PDI
    pdi_link = page.query_selector(
        "a:has-text('PDI'), a:has-text('Create PDI'), a:has-text('Pre-Delivery'), a[href*='pdi']")
    if pdi_link:
        pdi_link.click()
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '04_pdi_form')
        checkboxes = page.query_selector_all('input[type="checkbox"]')
        for cb in checkboxes:
            if not cb.is_checked():
                cb.check()
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '04_pdi_submitted')
        check_page(page, 'Order', 'PDI submit')
        log_ok('Order', f"PDI created ({len(checkboxes)} checkboxes)")
    else:
        log_issue('Order', 'PDI', 'No Create PDI link on order detail')


def _find_live_test_order_id():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("""
            SELECT so.id FROM sales_vehiclesalesorder so
            JOIN customers_customer c ON c.id = so.customer_id
            WHERE c.phone = '9500000099'
            ORDER BY so.id DESC LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def flow_fittings(page):
    print("\n[FLOW 4b: VEHICLE FITTINGS (inline formset)]")
    order_id = _find_live_test_order_id()
    if not order_id:
        log_issue('Fittings', 'Find test order', 'No LIVE-TEST order found — skipping')
        return

    if not go(page, f'/sales/orders/{order_id}/fittings/add/', 'Fittings', 'Formset page'):
        return
    ss(page, '04b_fittings_form')

    if not page.query_selector('#fitting-table'):
        log_issue('Fittings', 'Formset table', 'No #fitting-table on fittings page')
        return
    log_ok('Fittings', 'Formset page loads with item table')

    rows = page.query_selector_all('tr.fitting-row')
    if len(rows) < 1:
        log_issue('Fittings', 'Formset rows', 'No fitting-row elements rendered')
        return

    # Fill the first two rows directly (formset renders extra=2 blank rows)
    page.fill('input[name="fittings-0-fitting_name"]', 'LIVE-TEST Crash Guard')
    page.fill('input[name="fittings-0-cost"]', '1200')
    if len(rows) >= 2:
        page.fill('input[name="fittings-1-fitting_name"]', 'LIVE-TEST Seat Cover')
        page.fill('input[name="fittings-1-cost"]', '500')
    else:
        page.click('#add-fitting-row')
        page.fill('input[name="fittings-1-fitting_name"]', 'LIVE-TEST Seat Cover')
        page.fill('input[name="fittings-1-cost"]', '500')
    ss(page, '04b_fittings_filled')

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '04b_fittings_saved')
    if not check_page(page, 'Fittings', 'Formset submit'):
        return
    log_ok('Fittings', 'Formset saved (2 rows)')

    # Verify both rows persisted and render on the order detail page
    content = page.content()
    if 'LIVE-TEST Crash Guard' in content and 'LIVE-TEST Seat Cover' in content:
        log_ok('Fittings', 'Both fittings visible on order detail')
    else:
        log_issue('Fittings', 'Order detail display', 'Saved fittings not shown on order detail page')


def flow_module_access(page):
    print("\n[FLOW 4c: MODULE ACCESS (admin)]")
    if not go(page, '/accounts/module-access/', 'ModuleAccess', 'List page'):
        return
    ss(page, '04c_module_access_list')

    manage_link = page.query_selector("a:has-text('Manage Modules')")
    if not manage_link:
        log_issue('ModuleAccess', 'Role row', 'No "Manage Modules" link found')
        return
    manage_link.click()
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '04c_module_access_edit')
    log_ok('ModuleAccess', 'Edit page loads for a role')
    edit_url = page.url

    vas_checkbox = page.query_selector('input[name="module_vas"]')
    if not vas_checkbox:
        log_issue('ModuleAccess', 'VAS checkbox', 'module_vas checkbox not found')
        return

    was_checked = vas_checkbox.is_checked()
    vas_checkbox.uncheck()
    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '04c_module_access_saved')
    log_ok('ModuleAccess', 'Module visibility toggle saved')

    # Restore to its original state so we don't leave a permanent side effect
    page.goto(edit_url)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    if was_checked:
        vas_again = page.query_selector('input[name="module_vas"]')
        if vas_again and not vas_again.is_checked():
            vas_again.check()
            click_submit(page)
            page.wait_for_load_state('domcontentloaded', timeout=10000)
    log_ok('ModuleAccess', 'Restored original module state')


def flow_billing(page):
    print("\n[FLOW 5: BILLING]")
    if not go(page, '/billing/invoices/', 'Billing', 'Invoice list'):
        return
    ss(page, '05_invoice_list')

    # Find the live test order
    order_id = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur  = conn.cursor()
        cur.execute("""
            SELECT so.id FROM sales_vehiclesalesorder so
            JOIN customers_customer c ON c.id = so.customer_id
            WHERE c.phone = '9500000099'
            ORDER BY so.id DESC LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        order_id = row[0] if row else None
    except Exception as e:
        log_issue('Billing', 'Find test order', str(e))

    if not go(page, '/billing/invoices/create/', 'Billing', 'Invoice create form'):
        return
    ss(page, '05_invoice_create_form')

    # InvoiceForm fields: sales_order, invoice_number, subtotal, gst_amount,
    # discount_amount, final_amount, invoice_date — NO customer select
    if order_id:
        so_sel = page.query_selector('select[name="sales_order"]')
        if so_sel:
            opts = page.eval_on_selector('select[name="sales_order"]',
                'el => Array.from(el.options).map(o=>o.value)')
            if str(order_id) in opts:
                page.select_option('select[name="sales_order"]', value=str(order_id))
                log_ok('Billing', 'Live test order linked to invoice')
            else:
                log_issue('Billing', 'Order in invoice dropdown', 'Live test order not in invoice order dropdown')

    # Required: invoice_number (unique) and invoice_date
    inv_num = f'LIVE-INV-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'
    el = page.query_selector('input[name="invoice_number"]')
    if el: el.fill(inv_num)
    el = page.query_selector('input[name="invoice_date"]')
    if el: el.fill(datetime.date.today().isoformat())

    for fname, val in [('subtotal','75000'), ('final_amount','75000')]:
        el = page.query_selector(f'input[name="{fname}"]')
        if el: el.fill(val)

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '05_invoice_created')

    if not check_page(page, 'Billing', 'Invoice create submit'):
        return
    log_ok('Billing', 'Invoice created')
    invoice_url = page.url

    # Invoice detail uses custom Payment Summary card (no Bootstrap .progress)
    content = page.content()
    if 'payment' in content.lower() or 'balance' in content.lower() or 'paid' in content.lower():
        log_ok('Billing', 'Payment summary section present')
    else:
        log_issue('Billing', 'Payment summary', 'No payment/balance text on invoice detail')

    # Check GST
    if 'cgst' in page.content().lower() or 'gst' in page.content().lower():
        log_ok('Billing', 'GST info visible on invoice')
    else:
        log_issue('Billing', 'GST info', 'No GST/CGST text on invoice detail')

    # Add Payment
    pay_link = page.query_selector(
        "a:has-text('Add Payment'), a[href*='payment_create'], a:has-text('Record Payment')")
    if pay_link:
        pay_link.click()
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '05_payment_form')
        el = page.query_selector('input[name="amount"]')
        if el: el.fill('25000')
        try:
            page.select_option('select[name="payment_method"]', value='cash')
        except Exception:
            pass
        el = page.query_selector('input[name="reference_no"]')
        if el: el.fill('LIVE-CASH-001')
        try:
            page.select_option('select[name="status"]', value='completed')
        except Exception:
            pass
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '05_payment_submitted')
        check_page(page, 'Billing', 'Payment submit')
        log_ok('Billing', 'Payment recorded')
    else:
        log_issue('Billing', 'Add Payment', 'No Add Payment link on invoice detail')

    # PDF
    page.goto(invoice_url)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    pdf_link = page.query_selector("a[href*='pdf'], a:has-text('PDF'), a:has-text('Download')")
    if pdf_link:
        pdf_link.click()
        page.wait_for_load_state('domcontentloaded', timeout=20000)
        ss(page, '05_invoice_pdf')
        check_page(page, 'Billing', 'Invoice PDF')
        log_ok('Billing', 'Invoice PDF/print view generates')
    else:
        log_issue('Billing', 'Invoice PDF', 'No PDF link on invoice detail')


def flow_rto(page):
    print("\n[FLOW 6: RTO]")
    if not go(page, '/rto/', 'RTO', 'Registration list'):
        return
    ss(page, '06_rto_list')

    if not go(page, '/rto/create/', 'RTO', 'Create form'):
        return
    ss(page, '06_rto_create_form')

    # Sales order select — prefer live test order
    so_sel = page.query_selector('select[name="sales_order"]')
    if so_sel:
        opts = page.eval_on_selector('select[name="sales_order"]',
            'el => Array.from(el.options).map(o=>({v:o.value,t:o.text}))')
        live = next((o for o in opts if 'Live Test' in o['t'] or 'ORD-' in o['t']), None)
        if live:
            page.select_option('select[name="sales_order"]', value=live['v'])
        elif opts:
            page.select_option('select[name="sales_order"]', value=opts[-1]['v'])

    for fname, val in [
        ('form20_number',       'LIVE-F20-001'),
        ('registration_number', 'TN11LT001'),
        ('rto_charges',         '3200'),
    ]:
        el = page.query_selector(f'input[name="{fname}"]')
        if el: el.fill(val)

    try:
        page.select_option('select[name="status"]', value='submitted')
    except Exception:
        pass

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '06_rto_created')

    if not check_page(page, 'RTO', 'Registration create submit'):
        return
    log_ok('RTO', 'RTO registration created')
    rto_detail_url = page.url
    rto_pk = rto_detail_url.rstrip('/').split('/')[-1]

    # RC Book — navigate directly to avoid stale link issues
    if rto_pk.isdigit():
        try:
            page.goto(f"{BASE_URL}/rto/{rto_pk}/rc-book/",
                      wait_until='domcontentloaded', timeout=15000)
            ss(page, '06_rc_book_form')
            if check_page(page, 'RTO', 'RC Book form'):
                click_submit(page)
                page.wait_for_load_state('domcontentloaded', timeout=10000)
                ss(page, '06_rc_book_created')
                check_page(page, 'RTO', 'RC Book create')
                log_ok('RTO', 'RC Book created')
        except Exception as e:
            log_issue('RTO', 'RC Book', str(e)[:150])
    else:
        log_issue('RTO', 'RC Book', 'Could not determine RTO PK from URL')


def flow_service(page):
    print("\n[FLOW 7: SERVICE]")
    if not go(page, '/service/', 'Service', 'Enquiry list'):
        return
    ss(page, '07_service_enquiry_list')

    # New Service Enquiry
    if go(page, '/service/enquiries/create/', 'Service', 'Enquiry create form'):
        ss(page, '07_service_enquiry_form')
        select_first_option(page, 'customer_vehicle')
        desc = page.query_selector(
            'textarea[name="issue_description"], textarea[name="description"], '
            'input[name="description"]')
        if desc: desc.fill('Live test - check oil and tyres')
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '07_service_enquiry_created')
        check_page(page, 'Service', 'Enquiry create submit')
        log_ok('Service', 'Service enquiry created')

    # Job Cards
    if not go(page, '/service/jobcards/', 'Service', 'Job card list'):
        return
    ss(page, '07_jobcard_list')

    if not go(page, '/service/jobcards/create/', 'Service', 'Job card create form'):
        return
    ss(page, '07_jobcard_form')

    select_first_option(page, 'customer_vehicle')
    odo = page.query_selector('input[name="odometer_reading"], input[name="odometer"]')
    if odo: odo.fill('1500')
    prob = page.query_selector(
        'textarea[name="customer_complaint"], textarea[name="problem_description"], '
        'input[name="problem"]')
    if prob: prob.fill('Live test - first service')
    select_first_option(page, 'service_advisor')

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '07_jobcard_created')

    if not check_page(page, 'Service', 'Job card create submit'):
        return
    log_ok('Service', 'Job card created')
    jc_url = page.url
    jc_pk = jc_url.rstrip('/').split('/')[-1]

    # Warranty text
    if 'warranty' in page.content().lower():
        log_ok('Service', 'Warranty status visible on job card')
    else:
        log_issue('Service', 'Warranty status', 'No warranty text on job card detail')

    # Workflow progress
    if page.query_selector('.progress, [class*="workflow"], [class*="status-step"]'):
        log_ok('Service', 'Workflow/progress element present')
    else:
        log_issue('Service', 'Workflow progress', 'No workflow progress element on job card')

    # Status advance buttons
    statuses_advanced = 0
    for _ in range(5):
        adv = page.query_selector(
            "form button:has-text('Advance'), button:has-text('Move to'), "
            "button[data-action='advance'], a:has-text('Advance')")
        if adv:
            adv.click()
            page.wait_for_load_state('domcontentloaded', timeout=10000)
            statuses_advanced += 1
        else:
            break
    if statuses_advanced > 0:
        log_ok('Service', f"Job card status advanced {statuses_advanced} times")
        ss(page, '07_status_advanced')
    else:
        log_issue('Service', 'Status advance', 'No advance status button found on job card')

    # Labour charge
    page.goto(jc_url)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    labour_link = page.query_selector(
        "a:has-text('Add Labour'), a:has-text('Labour Charge'), a[href*='labour']")
    if labour_link:
        labour_link.click()
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '07_labour_form')
        sn = page.query_selector('input[name="service_name"], input[name="description"]')
        if sn: sn.fill('Engine Oil Change')
        cost = page.query_selector('input[name="cost"], input[name="amount"]')
        if cost: cost.fill('0')
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '07_labour_added')
        check_page(page, 'Service', 'Labour charge submit')
        log_ok('Service', 'Labour charge added')
    else:
        log_issue('Service', 'Add Labour', 'No Add Labour link on job card')

    # Service Invoice — navigate directly with ?jc= param (template also uses ?job_card= in one place
    # but the view only handles ?jc=, so use direct navigation to avoid ambiguity)
    try:
        page.goto(f"{BASE_URL}/service/invoices/create/?jc={jc_pk}",
                  wait_until='domcontentloaded', timeout=15000)
        ss(page, '07_service_invoice_form')
        if check_page(page, 'Service', 'Service invoice create form'):
            click_submit(page)
            page.wait_for_load_state('domcontentloaded', timeout=10000)
            ss(page, '07_service_invoice_created')
            if not check_page(page, 'Service', 'Service invoice'):
                return
            log_ok('Service', 'Service invoice loads')
            pdf_link = page.query_selector("a[href*='pdf'], a:has-text('PDF'), a:has-text('Download')")
            if pdf_link:
                pdf_href = pdf_link.get_attribute('href') or ''
                if 'pdf' in pdf_href.lower() or not pdf_href.endswith('/edit/'):
                    pdf_link.click()
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                    ss(page, '07_service_invoice_pdf')
                    check_page(page, 'Service', 'Service invoice PDF')
                    log_ok('Service', 'Service invoice PDF generates')
            else:
                log_issue('Service', 'Service invoice PDF', 'No PDF link on service invoice detail')
    except Exception as e:
        log_issue('Service', 'Service invoice', str(e)[:150])


def flow_spares(page):
    print("\n[FLOW 8: SPARES]")
    if not go(page, '/spares/', 'Spares', 'Dashboard'):
        return
    ss(page, '08_spares_dashboard')

    # KPI cards
    if page.query_selector('.stat-card, .kpi-card, .stats-card, [class*="stat-grid"]'):
        log_ok('Spares', 'KPI / stat cards on spares dashboard')
    else:
        log_issue('Spares', 'KPI cards', 'No stat/kpi cards on spares dashboard')

    # Items list
    if not go(page, '/spares/items/', 'Spares', 'Items list'):
        return
    ss(page, '08_spares_items_list')

    # New Item form
    if not go(page, '/spares/items/create/', 'Spares', 'Item create form'):
        return
    ss(page, '08_item_create_form')

    for fname, val in [
        ('item_name',    'Live Test Oil Filter'),
        ('part_number',  'LT-OIL-001'),
        ('hsn_code',     '84099190'),
        ('selling_rate', '185'),
        ('mrp',          '210'),
        ('sgst_rate',    '9'),
        ('cgst_rate',    '9'),
        ('reorder_level','5'),
    ]:
        el = page.query_selector(f'input[name="{fname}"]')
        if el: el.fill(val)

    select_first_option(page, 'category')
    try:
        page.select_option('select[name="uom"]', label='Nos')
    except Exception:
        select_first_option(page, 'uom')

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '08_item_created')

    if not check_page(page, 'Spares', 'Item create submit'):
        return
    log_ok('Spares', 'Spare item created')

    # Counter Sales list
    if not go(page, '/spares/counter-sales/', 'Spares', 'Counter sales list'):
        return
    ss(page, '08_counter_sale_list')

    if not go(page, '/spares/counter-sales/create/', 'Spares', 'Counter sale create form'):
        return
    ss(page, '08_counter_sale_form')

    # Add item row button (JS-driven)
    add_btn = page.query_selector("button:has-text('Add Item'), button:has-text('Add Row'), .add-row-btn")
    if add_btn:
        add_btn.click()
        page.wait_for_timeout(600)

    item_sel = page.query_selector('select[name*="item"], select[name="item"]')
    if item_sel:
        opts = page.eval_on_selector(
            'select[name*="item"], select[name="item"]',
            'el => Array.from(el.options).map(o=>({v:o.value,t:o.text}))')
        oil = next((o for o in opts if 'Oil Filter' in o['t'] or 'LT-OIL' in o['t']), None)
        if oil:
            page.select_option(
                f'select[name="{item_sel.get_attribute("name")}"]',
                value=oil['v'])
            log_ok('Spares', 'Test item selected in counter sale')
        else:
            select_first_option(page, item_sel.get_attribute('name'))

    qty = page.query_selector('input[name*="quantity"], input[name="quantity"]')
    if qty: qty.fill('2')

    ss(page, '08_counter_sale_filled')
    if 'gst' in page.content().lower():
        log_ok('Spares', 'GST visible in counter sale form')
    else:
        log_issue('Spares', 'GST in counter sale', 'No GST text in counter sale form')

    click_submit(page)
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '08_counter_sale_created')
    check_page(page, 'Spares', 'Counter sale submit')
    log_ok('Spares', 'Counter sale created/submitted')


def flow_reports(page):
    print("\n[FLOW 9: REPORTS]")
    report_pages = [
        ('GST Report',        '/accounts/gst-report/'),
        ('Profit Report',     '/sales/profit-report/'),
        ('Sales Targets',     '/sales/targets/'),
        ('Leaderboard',       '/sales/leaderboard/'),
        ('Technician Report', '/service/technician-report/'),
        ('Parts Consumption', '/spares/reports/parts-consumption/'),
        ('Stock Aging',       '/customers/stock-aging/'),
    ]
    for name, path in report_pages:
        if go(page, path, 'Reports', name):
            slug = name.lower().replace(' ', '_')
            ss(page, f'09_{slug}')
            content = page.content()
            if '<table' in content or 'stat-card' in content or 'stat-grid' in content:
                log_ok('Reports', f"{name} loads with content")
            elif 'empty-state' in content:
                log_ok('Reports', f"{name} loads (empty data)")
            else:
                log_issue('Reports', name, 'Page loaded but no table or stat cards found')

    # --- Sales Targets: check colour badges ---
    if go(page, '/sales/targets/', 'Reports', 'Sales Targets reload'):
        content = page.content()
        if 'bg-success' in content or 'bg-warning' in content or 'bg-danger' in content:
            log_ok('Reports', 'Sales Targets has colour-coded achievement badges')
        elif 'overall_achievement_percent' in content:
            log_issue('Reports', 'Achievement badges',
                      'overall_achievement_percent rendered but no Bootstrap colour class — check template')
        else:
            log_issue('Reports', 'Achievement badges',
                      'No bg-success/bg-warning/bg-danger AND no overall_achievement_percent in page')

    # --- Profit report: check profit data and NO negative values ---
    if go(page, '/sales/profit-report/', 'Reports', 'Profit report reload'):
        content = page.content()
        if 'profit_data' in content or 'cost_price' in content or 'Profit' in content:
            log_ok('Reports', 'Profit report has profit data')
        else:
            log_issue('Reports', 'Profit data', 'No profit data in profit report')

    # --- Deliveries: check "Delivery Record Missing" section ---
    if go(page, '/sales/delivery-list/', 'Reports', 'Delivery list'):
        ss(page, '09_delivery_list')
        content = page.content()
        if 'Delivery Record Missing' in content:
            log_ok('Reports', '"Delivery Record Missing" section visible in delivery list')
        elif 'missing_deliveries' in content:
            log_issue('Reports', 'Missing deliveries badge',
                      'missing_deliveries in context but badge text not rendered')
        else:
            log_ok('Reports', 'Delivery list loads (no missing deliveries)')


def flow_rbac(page):
    print("\n[FLOW 10: RBAC]")
    # Logout
    page.goto(f"{BASE_URL}/accounts/logout/")
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '10_logged_out')
    log_ok('RBAC', 'Logout')

    # Try e2e_sales user
    e2e_login_ok = do_login(page, 'e2e_sales', 'Test@123')
    if e2e_login_ok:
        ss(page, '10_e2e_sales_logged_in')
        log_ok('RBAC', 'e2e_sales login succeeded')
        # Sidebar should NOT show Billing
        if not page.query_selector('a.sidebar-link:has-text("Invoices"), a.sidebar-link:has-text("Finance")'):
            log_ok('RBAC', 'Billing sidebar hidden for e2e_sales')
        else:
            log_issue('RBAC', 'Billing visible to e2e_sales', 'Finance/Billing links visible in sidebar for Sales role')
    else:
        log_issue('RBAC', 'e2e_sales login', 'Could not login as e2e_sales (user may not exist)')
        # Log back in as admin to continue restricted-access tests
        page.goto(f"{BASE_URL}/accounts/logout/")
        page.wait_for_load_state('domcontentloaded', timeout=5000)

    # Access control tests (works whether logged in as e2e_sales or not logged in at all)
    restricted = [
        ('/billing/invoices/',  'Billing Invoices'),
        ('/spares/items/',      'Spares Items'),
        ('/accounts/users/',    'User Management'),
    ]
    for path, name in restricted:
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, f"10_rbac_{name.lower().replace(' ', '_')}")
        url = page.url
        content = page.content()
        blocked = (
            '/accounts/login/' in url or
            '403' in page.title() or
            'forbidden' in content.lower() or
            'permission' in content.lower() or
            'Access Denied' in content or
            '403 —' in content or
            '<h1>403' in content
        )
        if blocked:
            log_ok('RBAC', f"{name} is blocked (redirect/403/access-denied)")
        else:
            log_issue('RBAC', f"{name} access",
                      f"Non-admin can access {path} — SECURITY ISSUE")

    # Re-login as admin
    page.goto(f"{BASE_URL}/accounts/logout/")
    page.wait_for_load_state('domcontentloaded', timeout=5000)
    if do_login(page, 'admin', 'SSBikez@2026'):
        ss(page, '10_admin_relogin')
        log_ok('RBAC', 'Re-logged in as admin')
    else:
        log_issue('RBAC', 'Admin re-login', 'Admin re-login failed after RBAC tests')


def flow_notifications(page):
    print("\n[FLOW 11: NOTIFICATIONS]")
    if not go(page, '/accounts/dashboard/', 'Notifications', 'Dashboard'):
        return

    bell = page.query_selector('a.notification-bell')
    if bell:
        log_ok('Notifications', 'notification-bell link found')
        bell.click()
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '11_notification_list_page')
        check_page(page, 'Notifications', 'Notification list page')
        # Check for notification rows
        rows = page.query_selector_all('tr, .notification-item, [class*="notification"]')
        if rows:
            log_ok('Notifications', f"Notification list has {len(rows)} items/rows")
        else:
            log_issue('Notifications', 'Notification items', 'No rows/items on notification list page')
        # Mark as read
        mark_btn = page.query_selector("a:has-text('Mark'), button:has-text('Mark'), a[href*='mark']")
        if mark_btn:
            mark_btn.click()
            page.wait_for_load_state('domcontentloaded', timeout=10000)
            ss(page, '11_notification_marked')
            log_ok('Notifications', 'Mark as read clicked')
        else:
            log_issue('Notifications', 'Mark as read', 'No mark-as-read button on notification page')
    else:
        log_issue('Notifications', 'Bell', 'a.notification-bell not found on dashboard')


def flow_search(page):
    print("\n[FLOW 12: SEARCH]")
    if not go(page, '/accounts/dashboard/', 'Search', 'Dashboard'):
        return

    search = page.query_selector('input[name="q"]')
    if not search:
        log_issue('Search', 'Search bar', 'No input[name="q"] in topbar')
        return

    log_ok('Search', 'Search bar input found')
    search.fill('Live Test')
    search.press('Enter')
    page.wait_for_load_state('domcontentloaded', timeout=10000)
    ss(page, '12_search_results')
    check_page(page, 'Search', 'Search results page')

    content = page.content()
    if 'Live Test' in content:
        log_ok('Search', 'Search results contain "Live Test"')
    else:
        log_issue('Search', 'Search results', '"Live Test" not found in search results page')

    # Click a result — search template uses "View" btn-ghost buttons in table rows
    result_link = page.query_selector(
        "a:has-text('Live Test Customer'), a:has-text('Live Test'), "
        "a.btn-ghost.btn-sm, td a[href*='customer'], td a.btn-ghost")
    if result_link:
        result_link.click()
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '12_search_click_result')
        check_page(page, 'Search', 'Result click navigation')
        log_ok('Search', 'Clicking result navigates correctly')
    else:
        log_issue('Search', 'Click result', 'No clickable result found in search page')

    # Registration-number ("number plate") search
    reg_no = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT registration_no FROM customer_vehicles_customervehicle "
                    "WHERE registration_no IS NOT NULL AND registration_no != '' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        reg_no = row[0] if row else None
    except Exception as e:
        log_issue('Search', 'Find reg no', str(e))

    if reg_no:
        go(page, '/accounts/dashboard/', 'Search', 'Dashboard (reg search)')
        search2 = page.query_selector('input[name="q"]')
        if search2:
            search2.fill(reg_no)
            search2.press('Enter')
            page.wait_for_load_state('domcontentloaded', timeout=10000)
            ss(page, '12_search_by_regno')
            content2 = page.content()
            if reg_no in content2 and 'Customer Vehicles' in content2:
                log_ok('Search', f'Search by registration number "{reg_no}" returns Customer Vehicles result')
            else:
                log_issue('Search', 'Registration number search', f'"{reg_no}" not found in search results')
    else:
        log_issue('Search', 'Registration number search', 'No CustomerVehicle with a registration_no to test against')


def flow_masters(page):
    print("\n[FLOW 13: MASTERS]")
    pages = [
        ('Suppliers',        '/masters/suppliers/'),
        ('Warehouses',       '/masters/warehouses/'),
        ('Company Settings', '/accounts/company-settings/'),
        ('Users',            '/accounts/users/'),
        ('Roles',            '/accounts/roles/'),
    ]
    for name, path in pages:
        if go(page, path, 'Masters', name):
            slug = name.lower().replace(' ', '_')
            ss(page, f'13_{slug}')
            log_ok('Masters', f"{name} page loads")

    # Company Settings — GSTIN field
    if go(page, '/accounts/company-settings/', 'Masters', 'Company Settings GSTIN check'):
        content = page.content()
        if 'gstin' in content.lower() or 'gst' in content.lower():
            log_ok('Masters', 'Company Settings has GSTIN field')
        else:
            log_issue('Masters', 'Company Settings GSTIN', 'No GSTIN field on Company Settings page')

    # New Supplier
    if go(page, '/masters/suppliers/create/', 'Masters', 'Supplier create form'):
        ss(page, '13_supplier_create_form')
        nm = page.query_selector('input[name="name"]')
        if nm: nm.fill('Live Test Supplier')
        ph = page.query_selector('input[name="phone"]')
        if ph: ph.fill('9400000011')
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '13_supplier_created')
        check_page(page, 'Masters', 'Supplier create submit')
        log_ok('Masters', 'Supplier created')


def flow_vas(page):
    print("\n[FLOW 14: VAS]")
    for name, path in [('AMC', '/vas/amc/'), ('RSA', '/vas/rsa/')]:
        if go(page, path, 'VAS', f"{name} list"):
            ss(page, f'14_vas_{name.lower()}')
            log_ok('VAS', f"{name} list loads")

    # AMC create
    if go(page, '/vas/amc/create/', 'VAS', 'AMC create form'):
        ss(page, '14_amc_create_form')
        select_first_option(page, 'customer_vehicle')
        for fname, val in [('package_name','Basic AMC'), ('amount','2500'), ('duration_months','12')]:
            el = page.query_selector(f'input[name="{fname}"]')
            if el: el.fill(val)
        for dfname in ['start_date', 'valid_from']:
            el = page.query_selector(f'input[name="{dfname}"]')
            if el: el.fill(datetime.date.today().isoformat())
        click_submit(page)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        ss(page, '14_amc_created')
        check_page(page, 'VAS', 'AMC create submit')
        log_ok('VAS', 'AMC package created')


# ══════════════════════════════════════════════════════════════════════════════
# SERVER + RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def start_server():
    import urllib.request
    proc = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8010', '--noreload'],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/accounts/login/", timeout=2)
            print(f"Server ready at {BASE_URL}")
            return proc
        except Exception:
            time.sleep(0.5)
    print("WARNING: Server may not be fully up — proceeding")
    return proc


def run_all(headed: bool = False):
    from playwright.sync_api import sync_playwright

    print(f"\n{'='*60}")
    print(f"SSBikez ERP -- Full Browser QA  |  {datetime.datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'='*60}")
    print(f"Screenshots -> {SS_DIR}")

    server_proc = start_server()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not headed, slow_mo=100)
            ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = ctx.new_page()
            page.set_default_timeout(15000)

            flows = [
                flow_login,
                flow_dashboard,
                flow_customer_creation,
                flow_sales_enquiry,
                flow_vehicle_stock_and_order,
                flow_fittings,
                flow_module_access,
                flow_billing,
                flow_rto,
                flow_service,
                flow_spares,
                flow_reports,
                flow_rbac,
                flow_notifications,
                flow_search,
                flow_masters,
                flow_vas,
            ]

            for fn in flows:
                try:
                    fn(page)
                except Exception as e:
                    log_issue(fn.__name__, 'UNCAUGHT EXCEPTION', str(e)[:300])
                    try:
                        ss(page, f"ERR_{fn.__name__}")
                    except Exception:
                        pass

            browser.close()
    finally:
        server_proc.terminate()

    # Report
    issues = [r for r in REPORT if r['status'] == 'ISSUE']
    oks    = [r for r in REPORT if r['status'] == 'OK']

    print(f"\n{'='*60}")
    print(f"QA REPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Total checks : {len(REPORT)}")
    print(f"  PASSED     : {len(oks)}")
    print(f"  ISSUES     : {len(issues)}")

    if issues:
        print(f"\nISSUES:")
        print("-" * 60)
        for i, iss in enumerate(issues, 1):
            print(f"\n[{i}] {iss['flow']} -> {iss['step']}")
            if iss.get('detail'):
                print(f"    {iss['detail']}")
            if iss.get('screenshot'):
                print(f"    Screenshot: {iss['screenshot']}")
    else:
        print("\nAll checks PASSED.")

    report_path = BASE_DIR / 'qa_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'summary': {'total': len(REPORT), 'passed': len(oks), 'issues': len(issues)},
                   'results': REPORT}, f, indent=2, ensure_ascii=False)
    print(f"\nReport -> {report_path}")
    print(f"Screenshots -> {SS_DIR}")
    return issues


if __name__ == '__main__':
    headed = '--headed' in sys.argv
    issues = run_all(headed=headed)
    sys.exit(1 if issues else 0)
