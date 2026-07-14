"""
Comprehensive automated test suite for SSBikez ERP.
Uses Django's test client — calls views through the WSGI layer directly.
"""
import os, sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
os.environ.setdefault('DEBUG', 'True')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()

PASS_RESULTS = []
FAIL_RESULTS = []
SKIP_RESULTS = []
WARN_RESULTS = []

def record(status, name, detail=""):
    entry = {"name": name, "detail": detail}
    if status == "PASS":
        PASS_RESULTS.append(entry)
        print(f"  PASS  {name}")
    elif status == "FAIL":
        FAIL_RESULTS.append(entry)
        print(f"  FAIL  {name} -- {detail}")
    elif status == "WARN":
        WARN_RESULTS.append(entry)
        print(f"  WARN  {name} -- {detail}")
    elif status == "SKIP":
        SKIP_RESULTS.append(entry)
        print(f"  SKIP  {name} -- {detail}")

def make_client(username):
    """Return a Django test client logged in as the given user."""
    c = Client()
    user = User.objects.filter(username=username).first()
    if not user:
        return None, None
    c.force_login(user)
    return c, user

def check_get(client, url, name, expected=200):
    try:
        r = client.get(url, follow=True)
        code = r.status_code
        final_url = r.redirect_chain[-1][0] if r.redirect_chain else url
        if code == expected:
            # Make sure we're not quietly redirected to login
            if "login" in final_url and url != "/accounts/login/":
                record("WARN", name, f"Redirected to login -- permission denied")
            else:
                record("PASS", name)
        elif code == 403:
            record("WARN", name, "403 Forbidden - RBAC blocked")
        elif code == 404:
            record("FAIL", name, "404 Not Found")
        elif code == 500:
            record("FAIL", name, "500 Server Error")
            # Extract traceback hint
            content = r.content.decode("utf-8", errors="replace")
            for line in content.split("\n"):
                if "Exception" in line or "Error" in line:
                    record("FAIL", f"  +- {name}", line.strip()[:120])
                    break
        else:
            record("WARN", name, f"HTTP {code}")
        return r
    except Exception as e:
        record("FAIL", name, str(e)[:120])
        return None

def check_post(client, url, name, data, expected_codes=(200, 302)):
    try:
        r = client.post(url, data=data, follow=False)
        code = r.status_code
        if code in expected_codes:
            record("PASS", name)
        else:
            record("FAIL", name, f"HTTP {code}")
        return r
    except Exception as e:
        record("FAIL", name, str(e)[:120])
        return None

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ──────────────────────────────────────────────────────────────
#  MAIN TEST RUNNER
# ──────────────────────────────────────────────────────────────
print("\nSSBikez ERP - Comprehensive Test Suite")
print("="*60)

# ── Setup ─────────────────────────────────────────────────────
# Note: 'admin' is intentionally excluded — it's the real persistent
# superuser account other QA scripts and manual testing rely on with a
# known password; resetting it here as a side effect broke those scripts.
section("0. Setup")
for uname, pwd in {
    "arjun.kumar": "Admin@123",
    "divya.cre": "Admin@123",
    "meena.cashier": "Admin@123",
    "priya.service": "Admin@123",
}.items():
    u = User.objects.filter(username=uname).first()
    if u:
        u.set_password(pwd); u.save()
        print(f"  Password set for {uname}")

# Create clients
admin_c, admin_user = make_client("admin")
sales_c, sales_user = make_client("arjun.kumar")
cre_c, cre_user     = make_client("divya.cre")
cashier_c, cashier_user = make_client("meena.cashier")
service_c, service_user = make_client("priya.service")

if not admin_c:
    print("FATAL: admin user not found"); sys.exit(1)

# ── Auth ──────────────────────────────────────────────────────
section("1. Authentication & OTP Flow")
from accounts.models import OTPVerification

# Test OTP generation
u = User.objects.get(username="admin")
OTPVerification.objects.filter(user=u, action="login").delete()
otp_obj = OTPVerification(user=u, action="login")
otp_obj.generate_otp()
if otp_obj.otp_code and len(otp_obj.otp_code) == 6:
    record("PASS", "OTP generation (6-digit)")
else:
    record("FAIL", "OTP generation", f"Got: {otp_obj.otp_code!r}")

# Test OTP expiry logic
if otp_obj.expires_at > timezone.now():
    record("PASS", "OTP expiry set in future")
else:
    record("FAIL", "OTP expiry", "OTP already expired on creation")

# Test OTP login flow end-to-end via test client
anon = Client()
r = anon.get("/accounts/login/")
record("PASS" if r.status_code == 200 else "FAIL", "Login page accessible (anon)")

ADMIN_PASSWORD = os.environ.get("QA_ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("Set the QA_ADMIN_PASSWORD environment variable before running this script.")

r = anon.post("/accounts/login/", {"username": "admin", "password": ADMIN_PASSWORD}, follow=False)
if r.status_code in (301, 302) and "verify-otp" in (r.get("Location") or ""):
    record("PASS", "Login POST redirects to OTP page")
    # Verify OTP record was created
    otp = OTPVerification.objects.filter(user=u, action="login", is_verified=False).first()
    if otp:
        record("PASS", "OTP record created in DB after login")
        # Submit correct OTP
        r2 = anon.post("/accounts/verify-otp/", {"otp_code": otp.otp_code}, follow=False)
        if r2.status_code in (301, 302):
            record("PASS", "Correct OTP accepted and redirects")
        else:
            record("FAIL", "Correct OTP verification", f"HTTP {r2.status_code}")
        # Try wrong OTP on new login
        anon2 = Client()
        anon2.post("/accounts/login/", {"username": "admin", "password": ADMIN_PASSWORD}, follow=False)
        r3 = anon2.post("/accounts/verify-otp/", {"otp_code": "000000"}, follow=False)
        r3b = anon2.get("/accounts/verify-otp/", follow=True)  # re-render with error
        if b"Invalid" in r3b.content or b"expired" in r3b.content or r3.status_code == 200:
            record("PASS", "Wrong OTP rejected")
        else:
            record("WARN", "Wrong OTP rejection", "May have accepted wrong OTP")
    else:
        record("FAIL", "OTP record created in DB", "No OTP found")
else:
    record("FAIL", "Login POST OTP redirect", f"Status {r.status_code}, Location: {r.get('Location')}")

record("PASS", "Admin force_login (used for remaining tests)")

# ── Accounts Module ───────────────────────────────────────────
section("2. Accounts Module")
check_get(admin_c, "/accounts/dashboard/", "Dashboard")
check_get(admin_c, "/accounts/home/", "Home")
check_get(admin_c, "/accounts/users/", "User List")
check_get(admin_c, "/accounts/users/create/", "User Create Form")
check_get(admin_c, f"/accounts/users/{admin_user.pk}/edit/", "User Edit Form")
check_get(admin_c, "/accounts/branches/", "Branch List")
check_get(admin_c, "/accounts/branches/create/", "Branch Create Form")
check_get(admin_c, "/accounts/roles/", "Role List")
check_get(admin_c, "/accounts/roles/create/", "Role Create Form")
check_get(admin_c, "/accounts/fuel-expenses/", "Fuel Expense List")
check_get(admin_c, "/accounts/fuel-expenses/create/", "Fuel Expense Create Form")
check_get(admin_c, "/accounts/profile/", "Profile View")
check_get(admin_c, "/accounts/profile/edit/", "Profile Edit Form")
check_get(admin_c, "/accounts/search/?q=test", "Global Search")
check_get(admin_c, "/accounts/insurance-expiry/", "Insurance Expiry List")
check_get(admin_c, "/accounts/settings/", "Company Settings")
check_get(admin_c, "/accounts/notifications/", "Notification List")
check_get(admin_c, "/accounts/notifications/count/", "Notification Count API")
check_get(admin_c, "/accounts/gst-report/", "GST Report")
check_get(admin_c, "/accounts/reports/sales/", "Sales Report")
check_get(admin_c, "/accounts/reports/spares/", "Spares Report")
check_get(admin_c, "/accounts/reports/service/", "Service Report")

from accounts.models import Branch, Role
first_branch = Branch.objects.first()
if first_branch:
    check_get(admin_c, f"/accounts/branches/{first_branch.pk}/edit/", "Branch Edit Form")
first_role = Role.objects.first()
if first_role:
    check_get(admin_c, f"/accounts/roles/{first_role.pk}/edit/", "Role Edit Form")

# ── Customers Module ──────────────────────────────────────────
section("3. Customers Module")
check_get(admin_c, "/customers/", "Customer List")
check_get(admin_c, "/customers/create/", "Customer Create Form")
check_get(admin_c, "/customers/bikes/", "Bike Model List")
check_get(admin_c, "/customers/bikes/create/", "Bike Model Create Form")
check_get(admin_c, "/customers/stock/", "Vehicle Stock List")
check_get(admin_c, "/customers/stock/create/", "Vehicle Stock Create Form")
check_get(admin_c, "/customers/vehicle-stock/aging/", "Stock Aging Report")

from customers.models import Customer, VehicleStock, BikeModel
first_customer = Customer.objects.first()
if first_customer:
    check_get(admin_c, f"/customers/{first_customer.pk}/", "Customer Detail")
    check_get(admin_c, f"/customers/{first_customer.pk}/edit/", "Customer Edit Form")
else:
    record("SKIP", "Customer Detail/Edit", "No customers in DB")

first_stock = VehicleStock.objects.first()
if first_stock:
    check_get(admin_c, f"/customers/stock/{first_stock.pk}/", "Vehicle Stock Detail")
    check_get(admin_c, f"/customers/stock/{first_stock.pk}/edit/", "Vehicle Stock Edit")
else:
    record("SKIP", "Vehicle Stock Detail/Edit", "No stock in DB")

first_bike = BikeModel.objects.first()
if first_bike:
    check_get(admin_c, f"/customers/bikes/{first_bike.pk}/", "Bike Model Detail")
    check_get(admin_c, f"/customers/bikes/{first_bike.pk}/edit/", "Bike Model Edit")
else:
    record("SKIP", "Bike Model Detail/Edit", "No bike models in DB")

# Validation: invalid phone must be rejected (form re-rendered)
r = admin_c.post("/customers/create/", {
    "full_name": "Test Val User", "phone": "123", "email": "val@test.com"
})
if r.status_code == 200 and (b"phone" in r.content.lower() or b"error" in r.content.lower() or b"invalid" in r.content.lower()):
    record("PASS", "Customer - invalid phone rejected by form validation")
else:
    record("WARN", "Customer - phone validation", f"Expected form error, got HTTP {r.status_code}")

# ── Sales Module ──────────────────────────────────────────────
section("4. Sales Module")
check_get(sales_c, "/sales/", "Sales Dashboard (as sales exec)")
check_get(admin_c, "/sales/enquiries/", "Enquiry List")
check_get(admin_c, "/sales/enquiries/create/", "Enquiry Create Form")
check_get(admin_c, "/sales/orders/", "Order List")
check_get(admin_c, "/sales/orders/create/", "Order Create Form")
check_get(admin_c, "/sales/delivery-list/", "Delivery List")
check_get(admin_c, "/sales/delivery/create/", "Delivery Create Form")
check_get(admin_c, "/sales/exchange-list/", "Exchange List")
check_get(admin_c, "/sales/exchange/create/", "Exchange Create Form")
check_get(admin_c, "/sales/all-appointments/", "All Appointments")
check_get(admin_c, "/sales/feedback-all/", "All Feedback")
check_get(admin_c, "/sales/follow-ups/", "Follow-up List")
check_get(admin_c, "/sales/targets/", "Sales Target List")
check_get(admin_c, "/sales/targets/create/", "Sales Target Create Form")
check_get(admin_c, "/sales/leaderboard/", "Sales Leaderboard")
check_get(admin_c, "/sales/test-rides/", "Test Ride List")
check_get(admin_c, "/sales/test-rides/create/", "Test Ride Create Form")
check_get(admin_c, "/sales/profit-report/", "Profit Report")

from sales.models import SalesEnquiry, VehicleSalesOrder, VehicleDelivery, SalesTarget, TestRideLog, PDIChecklist
first_enquiry = SalesEnquiry.objects.first()
if first_enquiry:
    check_get(admin_c, f"/sales/enquiries/{first_enquiry.pk}/", "Enquiry Detail")
    check_get(admin_c, f"/sales/enquiries/{first_enquiry.pk}/edit/", "Enquiry Edit")
    check_get(admin_c, f"/sales/enquiries/{first_enquiry.pk}/appointments/", "Enquiry Appointments")
    check_get(admin_c, f"/sales/enquiries/{first_enquiry.pk}/feedback/", "Enquiry Feedback")
else:
    record("SKIP", "Enquiry Detail/subviews", "No enquiries in DB")

first_order = VehicleSalesOrder.objects.first()
if first_order:
    check_get(admin_c, f"/sales/orders/{first_order.pk}/", "Order Detail")
    check_get(admin_c, f"/sales/orders/{first_order.pk}/edit/", "Order Edit")
    check_get(admin_c, f"/sales/orders/{first_order.pk}/allot/", "Vehicle Allotment")
    check_get(admin_c, f"/sales/orders/{first_order.pk}/pdi/", "PDI Create Form")
    check_get(admin_c, f"/sales/orders/{first_order.pk}/fittings/add/", "Fittings Create Form")
else:
    record("SKIP", "Order detail/PDI/Allotment", "No orders in DB")

first_target = SalesTarget.objects.first()
if first_target:
    check_get(admin_c, f"/sales/targets/{first_target.pk}/", "Sales Target Detail")
else:
    record("SKIP", "Sales Target Detail", "No targets in DB")

first_pdi = PDIChecklist.objects.first()
if first_pdi:
    check_get(admin_c, f"/sales/pdi/{first_pdi.pk}/", "PDI Detail")
else:
    record("SKIP", "PDI Checklist Detail", "No PDI records in DB")

first_delivery = VehicleDelivery.objects.first()
if first_delivery:
    check_get(admin_c, f"/sales/delivery/{first_delivery.pk}/", "Delivery Detail")
    check_get(admin_c, f"/sales/delivery/{first_delivery.pk}/edit/", "Delivery Edit")
else:
    record("SKIP", "Delivery Detail/Edit", "No deliveries in DB")

# Test ride return (POST)
first_tr = TestRideLog.objects.first()
if first_tr and not first_tr.end_time:
    r = admin_c.post(f"/sales/test-rides/{first_tr.pk}/return/", {}, follow=False)
    record("PASS" if r.status_code in (200, 302) else "FAIL",
           "Test Ride Return (POST)", f"HTTP {r.status_code}")
else:
    record("SKIP", "Test Ride Return", "No pending test rides")

check_get(admin_c, "/sales/appointment/create/" if False else "/sales/appointments/create/", "Appointment Create") if False else None
check_get(admin_c, "/sales/feedback/create/", "Sales Feedback Create Form")
check_get(admin_c, "/sales/appointments/create/", "Appointment Create Form")

# ── Billing Module ────────────────────────────────────────────
section("5. Billing Module")
check_get(admin_c, "/billing/", "Billing Dashboard")
check_get(admin_c, "/billing/invoices/", "Invoice List")
check_get(admin_c, "/billing/invoices/create/", "Invoice Create Form")
check_get(admin_c, "/billing/insurance/", "Insurance Policy List")
check_get(admin_c, "/billing/insurance/create/", "Insurance Create Form")
check_get(admin_c, "/billing/loans/", "Loan List")
check_get(admin_c, "/billing/loans/create/", "Loan Create Form")
check_get(admin_c, "/billing/daily-report/", "Daily Collection Report")
check_get(admin_c, "/billing/reconciliation/", "Payment Reconciliation")
check_get(admin_c, "/billing/search/", "Invoice Search")
check_get(admin_c, "/billing/refunds-advances/", "Refunds & Advances List")
check_get(admin_c, "/billing/refunds-advances/create/", "Refund/Advance Create Form")
check_get(admin_c, "/billing/journal/", "Journal Entry List")
check_get(admin_c, "/billing/journal/create/", "Journal Entry Create Form")
check_get(admin_c, "/billing/ledger/", "General Ledger")

from billing.models import Invoice, FinanceLoan, InsurancePolicy, Payment, RefundAdvance
first_invoice = Invoice.objects.first()
if first_invoice:
    check_get(admin_c, f"/billing/invoices/{first_invoice.pk}/", "Invoice Detail")
    check_get(admin_c, f"/billing/invoices/{first_invoice.pk}/edit/", "Invoice Edit")
    check_get(admin_c, f"/billing/invoices/{first_invoice.pk}/pdf/", "Invoice PDF")
    check_get(admin_c, f"/billing/invoices/{first_invoice.pk}/payments/", "Invoice Payments")
    check_get(admin_c, f"/billing/payments/create/", "Payment Create Form")
else:
    record("SKIP", "Invoice detail/PDF/payments", "No invoices in DB")

first_loan = FinanceLoan.objects.first()
if first_loan:
    check_get(admin_c, f"/billing/loans/{first_loan.pk}/", "Loan Detail")
    check_get(admin_c, f"/billing/loans/{first_loan.pk}/edit/", "Loan Edit")
else:
    record("SKIP", "Loan Detail/Edit", "No loans in DB")

first_ins = InsurancePolicy.objects.first()
if first_ins:
    check_get(admin_c, f"/billing/insurance/{first_ins.pk}/", "Insurance Policy Detail")
    check_get(admin_c, f"/billing/insurance/{first_ins.pk}/edit/", "Insurance Edit")
else:
    record("SKIP", "Insurance Policy Detail/Edit", "No policies in DB")

first_ra = RefundAdvance.objects.first()
if first_ra:
    check_get(admin_c, f"/billing/refunds-advances/{first_ra.pk}/", "Refund/Advance Detail")
else:
    record("SKIP", "Refund/Advance Detail", "No refunds in DB")

# Service invoice PDF via billing — requires a JC that has a service invoice
from service.models import JobCard, ServiceInvoice as SvcInv
svc_inv_for_pdf = SvcInv.objects.select_related('job_card').first()
if svc_inv_for_pdf:
    check_get(admin_c, f"/billing/service-invoice/{svc_inv_for_pdf.job_card_id}/pdf/", "Service Invoice PDF")
else:
    record("SKIP", "Service Invoice PDF", "No service invoices in DB")

# ── Service Module ────────────────────────────────────────────
section("6. Service Module")
check_get(admin_c, "/service/dashboard/", "Service Dashboard")
check_get(admin_c, "/service/", "Service Enquiry List")
check_get(admin_c, "/service/enquiries/create/", "Service Enquiry Create")
check_get(admin_c, "/service/appointments/", "Service Appointment List")
check_get(admin_c, "/service/appointments/create/", "Service Appointment Create")
check_get(admin_c, "/service/jobcards/", "Job Card List")
check_get(admin_c, "/service/jobcards/create/", "Job Card Create Form")
check_get(admin_c, "/service/bays/", "Bay List")
check_get(admin_c, "/service/bays/create/", "Bay Create Form")
check_get(admin_c, "/service/labor-charges/", "Labor Charge List")
check_get(admin_c, "/service/labor-charges/create/", "Labor Charge Create Form")
check_get(admin_c, "/service/warranty-claims/", "Warranty Claim List")
check_get(admin_c, "/service/warranty-claims/create/", "Warranty Claim Create")
check_get(admin_c, "/service/insurance-estimations/create/", "Insurance Estimation Create")
check_get(admin_c, "/service/insurance-claims/", "Insurance Claim List")
check_get(admin_c, "/service/discount-master/", "Discount Master List")
check_get(admin_c, "/service/discount-master/create/", "Discount Master Create")
check_get(admin_c, "/service/calls/", "Customer Call List")
check_get(admin_c, "/service/calls/create/", "Customer Call Create")
check_get(admin_c, "/service/reminders/", "Service Reminder List")
check_get(admin_c, "/service/technician-report/", "Technician Report")
check_get(admin_c, "/service/bulk-import/", "Bulk Import Form")

from service.models import JobCard, ServiceReminder, ServiceEnquiry, ServiceInvoice, WarrantyClaim, InsuranceClaim
first_jc = JobCard.objects.first()
if first_jc:
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/", "Job Card Detail")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/edit/", "Job Card Edit")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/print/", "Job Card Print")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/revisit/", "Revisit Form")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/childs/add/", "Service Child Add")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/additional-work/create/", "Additional Work Create")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/insurance-estimation/", "Insurance Estimation for JC")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/warranty-claim/", "Warranty Claim for JC")
    check_get(admin_c, f"/service/jobcards/{first_jc.pk}/insurance-claim/", "Insurance Claim for JC")
else:
    record("SKIP", "Job Card Detail/subviews", "No job cards in DB")

first_svc_enq = ServiceEnquiry.objects.first()
if first_svc_enq:
    check_get(admin_c, f"/service/enquiries/{first_svc_enq.pk}/", "Service Enquiry Detail")
    check_get(admin_c, f"/service/enquiries/{first_svc_enq.pk}/edit/", "Service Enquiry Edit")
else:
    record("SKIP", "Service Enquiry Detail/Edit", "No service enquiries in DB")

first_reminder = ServiceReminder.objects.first()
if first_reminder:
    check_get(admin_c, f"/service/reminders/{first_reminder.pk}/update/", "Reminder Update Form")
else:
    record("SKIP", "Service Reminder Update", "No reminders in DB")

first_svc_inv = ServiceInvoice.objects.first()
if first_svc_inv:
    check_get(admin_c, f"/service/invoices/{first_svc_inv.pk}/", "Service Invoice Detail")
    check_get(admin_c, f"/service/invoices/{first_svc_inv.pk}/edit/", "Service Invoice Edit")
else:
    record("SKIP", "Service Invoice Detail/Edit", "No service invoices in DB")

first_wc = WarrantyClaim.objects.first()
if first_wc:
    check_get(admin_c, f"/service/warranty-claims/{first_wc.pk}/", "Warranty Claim Detail")
    check_get(admin_c, f"/service/warranty-claims/{first_wc.pk}/edit/", "Warranty Claim Edit")
else:
    record("SKIP", "Warranty Claim Detail/Edit", "No warranty claims in DB")

first_ic = InsuranceClaim.objects.first()
if first_ic:
    check_get(admin_c, f"/service/insurance-claims/{first_ic.pk}/", "Insurance Claim Detail")
    check_get(admin_c, f"/service/insurance-claims/{first_ic.pk}/edit/", "Insurance Claim Edit")
else:
    record("SKIP", "Insurance Claim Detail/Edit", "No insurance claims in DB")

# ── Spares Module ─────────────────────────────────────────────
section("7. Spares Module")
check_get(admin_c, "/spares/", "Spares Dashboard")
check_get(admin_c, "/spares/items/", "Item List")
check_get(admin_c, "/spares/items/create/", "Item Create Form")
check_get(admin_c, "/spares/stock/", "Stock Report")
check_get(admin_c, "/spares/quotes/", "Quote List")
check_get(admin_c, "/spares/quotes/create/", "Quote Create Form")
check_get(admin_c, "/spares/orders/", "Purchase Order List")
check_get(admin_c, "/spares/orders/create/", "Purchase Order Create Form")
check_get(admin_c, "/spares/invoices/", "Spares Invoice List")
check_get(admin_c, "/spares/invoices/create/", "Spares Invoice Create Form")
check_get(admin_c, "/spares/counter-sales/", "Counter Sale List")
check_get(admin_c, "/spares/counter-sales/create/", "Counter Sale Create Form")
check_get(admin_c, "/spares/counter-returns/", "Counter Return List")
check_get(admin_c, "/spares/counter-returns/create/", "Counter Return Create Form")
check_get(admin_c, "/spares/issue-alterations/", "Issue Alteration List")
check_get(admin_c, "/spares/issue-alterations/create/", "Issue Alteration Create")
check_get(admin_c, "/spares/issue/create/", "Spares Issue Create")
check_get(admin_c, "/spares/bulk-insert/", "Bulk Insert Form")
check_get(admin_c, "/spares/reports/po-used-qty/", "PO Used Qty Report")
check_get(admin_c, "/spares/reports/parts-consumption/", "Parts Consumption Report")

from spares.models import SparesItem, PurchaseOrder, CounterSale, SupplierQuote as SparesQuote
first_item = SparesItem.objects.first()
if first_item:
    check_get(admin_c, f"/spares/items/{first_item.pk}/", "Spares Item Detail")
    check_get(admin_c, f"/spares/items/{first_item.pk}/edit/", "Spares Item Edit")
else:
    record("SKIP", "Spares Item Detail/Edit", "No spares in DB")

first_po = PurchaseOrder.objects.first()
if first_po:
    check_get(admin_c, f"/spares/orders/{first_po.pk}/", "PO Detail")
    check_get(admin_c, f"/spares/orders/{first_po.pk}/edit/", "PO Edit")
else:
    record("SKIP", "PO Detail/Edit", "No POs in DB")

first_cs = CounterSale.objects.first()
if first_cs:
    check_get(admin_c, f"/spares/counter-sales/{first_cs.pk}/", "Counter Sale Detail")
else:
    record("SKIP", "Counter Sale Detail", "No counter sales in DB")

first_quote = SparesQuote.objects.first()
if first_quote:
    check_get(admin_c, f"/spares/quotes/{first_quote.pk}/", "Quote Detail")
    check_get(admin_c, f"/spares/quotes/{first_quote.pk}/edit/", "Quote Edit")
else:
    record("SKIP", "Quote Detail/Edit", "No quotes in DB")

# AJAX endpoints
r = admin_c.get("/spares/ajax/item-details/?item_id=1")
record("PASS" if r.status_code in (200, 404) else "FAIL", "AJAX Item Details endpoint", f"HTTP {r.status_code}")
r = admin_c.get("/spares/ajax/supplier-details/?supplier_id=1")
record("PASS" if r.status_code in (200, 404) else "FAIL", "AJAX Supplier Details endpoint", f"HTTP {r.status_code}")
r = admin_c.get("/spares/ajax/rack-bins/?rack_id=1")
record("PASS" if r.status_code in (200, 404) else "FAIL", "AJAX Rack Bins endpoint", f"HTTP {r.status_code}")

# ── RTO Module ────────────────────────────────────────────────
section("8. RTO Module")
check_get(admin_c, "/rto/dashboard/", "RTO Dashboard")
check_get(admin_c, "/rto/", "RTO Registration List")
check_get(admin_c, "/rto/create/", "RTO Registration Create")
check_get(admin_c, "/rto/plates/", "Number Plate List")
check_get(admin_c, "/rto/plates/create/", "Number Plate Create")
check_get(admin_c, "/rto/rc-books/", "RC Book List")

from rto.models import RTORegistration, NumberPlateOrder as NumberPlate, RCBook
first_rto = RTORegistration.objects.first()
if first_rto:
    check_get(admin_c, f"/rto/{first_rto.pk}/", "RTO Registration Detail")
    check_get(admin_c, f"/rto/{first_rto.pk}/edit/", "RTO Registration Edit")
    check_get(admin_c, f"/rto/{first_rto.pk}/rc-book/", "RC Book Create Form")
    check_get(admin_c, f"/rto/{first_rto.pk}/reg-payment/", "Reg Payment Create Form")
    check_get(admin_c, f"/rto/{first_rto.pk}/income/", "RTO Income Create Form")
else:
    record("SKIP", "RTO Detail/subviews", "No RTO registrations in DB")

first_plate = NumberPlate.objects.first()
if first_plate:
    check_get(admin_c, f"/rto/plates/{first_plate.pk}/edit/", "Number Plate Edit")
else:
    record("SKIP", "Number Plate Edit", "No plates in DB")

first_rcbook = RCBook.objects.first()
if first_rcbook:
    check_get(admin_c, f"/rto/rc-books/{first_rcbook.pk}/", "RC Book Detail")
else:
    record("SKIP", "RC Book Detail", "No RC books in DB")

# ── VAS Module ────────────────────────────────────────────────
section("9. VAS Module")
check_get(admin_c, "/vas/", "VAS Dashboard")
check_get(admin_c, "/vas/amc/", "AMC List")
check_get(admin_c, "/vas/amc/create/", "AMC Create Form")
check_get(admin_c, "/vas/rsa/", "RSA List")
check_get(admin_c, "/vas/rsa/create/", "RSA Create Form")
check_get(admin_c, "/vas/protection-plus/", "Protection Plus List")
check_get(admin_c, "/vas/protection-plus/create/", "Protection Plus Create Form")

from vas.models import AMCPackage as AMCPolicy, RSAPackage as RSAPolicy, ProtectionPlusPackage as ProtectionPlusPolicy
first_amc = AMCPolicy.objects.first()
if first_amc:
    check_get(admin_c, f"/vas/amc/{first_amc.pk}/", "AMC Detail")
    check_get(admin_c, f"/vas/amc/{first_amc.pk}/edit/", "AMC Edit")
else:
    record("SKIP", "AMC Detail/Edit", "No AMC policies in DB")

first_rsa = RSAPolicy.objects.first()
if first_rsa:
    check_get(admin_c, f"/vas/rsa/{first_rsa.pk}/", "RSA Detail")
    check_get(admin_c, f"/vas/rsa/{first_rsa.pk}/edit/", "RSA Edit")
else:
    record("SKIP", "RSA Detail/Edit", "No RSA policies in DB")

first_pp = ProtectionPlusPolicy.objects.first()
if first_pp:
    check_get(admin_c, f"/vas/protection-plus/{first_pp.pk}/", "Protection Plus Detail")
    check_get(admin_c, f"/vas/protection-plus/{first_pp.pk}/edit/", "Protection Plus Edit")
else:
    record("SKIP", "Protection Plus Detail/Edit", "No PP policies in DB")

# ── Masters Module ────────────────────────────────────────────
section("10. Masters Module")
check_get(admin_c, "/masters/categories/", "Category List")
check_get(admin_c, "/masters/categories/create/", "Category Create Form")
check_get(admin_c, "/masters/suppliers/", "Supplier List")
check_get(admin_c, "/masters/suppliers/create/", "Supplier Create Form")
check_get(admin_c, "/masters/warehouses/", "Warehouse List")
check_get(admin_c, "/masters/warehouses/create/", "Warehouse Create Form")
check_get(admin_c, "/masters/racks/", "Rack List")
check_get(admin_c, "/masters/racks/create/", "Rack Create Form")
check_get(admin_c, "/masters/bins/", "Bin List")
check_get(admin_c, "/masters/bins/create/", "Bin Create Form")

from masters.models import SparesCategory as Category, Supplier, Warehouse, Rack
first_cat = Category.objects.first()
if first_cat:
    check_get(admin_c, f"/masters/categories/{first_cat.pk}/edit/", "Category Edit")
first_supplier = Supplier.objects.first()
if first_supplier:
    check_get(admin_c, f"/masters/suppliers/{first_supplier.pk}/", "Supplier Detail")
    check_get(admin_c, f"/masters/suppliers/{first_supplier.pk}/edit/", "Supplier Edit")
else:
    record("SKIP", "Supplier Detail/Edit", "No suppliers in DB")

# ── Customer Vehicles ─────────────────────────────────────────
section("11. Customer Vehicles Module")
check_get(admin_c, "/customer-vehicles/", "Customer Vehicle List")
check_get(admin_c, "/customer-vehicles/create/", "Customer Vehicle Create Form")

from customer_vehicles.models import CustomerVehicle
first_cv = CustomerVehicle.objects.first()
if first_cv:
    check_get(admin_c, f"/customer-vehicles/{first_cv.pk}/", "Customer Vehicle Detail")
    check_get(admin_c, f"/customer-vehicles/{first_cv.pk}/edit/", "Customer Vehicle Edit")
else:
    record("SKIP", "Customer Vehicle Detail/Edit", "No customer vehicles in DB")

# ── RBAC Checks ───────────────────────────────────────────────
section("12. Role-Based Access Control")

# Sales exec should be able to access sales
if sales_c:
    r = sales_c.get("/sales/", follow=True)
    record("PASS" if r.status_code == 200 and "login" not in (r.redirect_chain[-1][0] if r.redirect_chain else "") else "WARN",
           "Sales Exec - can access Sales module")
    # Sales exec should NOT access billing (403 or redirect to login)
    r2 = sales_c.get("/billing/", follow=True)
    final = r2.redirect_chain[-1][0] if r2.redirect_chain else ""
    if r2.status_code == 403 or "login" in final:
        record("PASS", "Sales Exec - blocked from Billing module")
    else:
        record("WARN", "Sales Exec - billing access", "No RBAC block detected - check permissions")
    # Sales exec should NOT access user management
    r3 = sales_c.get("/accounts/users/", follow=True)
    final3 = r3.redirect_chain[-1][0] if r3.redirect_chain else ""
    if r3.status_code == 403 or "login" in final3:
        record("PASS", "Sales Exec - blocked from User Management")
    else:
        record("WARN", "Sales Exec - user management", "No RBAC block detected")
else:
    record("SKIP", "Sales Exec RBAC", "No sales user found")

# Service advisor should access service
if service_c:
    r = service_c.get("/service/", follow=True)
    record("PASS" if r.status_code == 200 else "WARN",
           "Service Advisor - can access Service module")
else:
    record("SKIP", "Service Advisor RBAC", "No service user found")

# CRE user
if cre_c:
    r = cre_c.get("/accounts/dashboard/", follow=True)
    record("PASS" if r.status_code == 200 else "WARN", "CRE user - can access dashboard")
else:
    record("SKIP", "CRE RBAC", "No CRE user found")

# ── Data Integrity ────────────────────────────────────────────
section("13. Data Integrity Checks")
from django.db import connection

# Orphaned job cards
try:
    with connection.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM service_jobcard
            WHERE customer_vehicle_id NOT IN (SELECT id FROM customer_vehicles_customervehicle)
        """)
        orphaned = cur.fetchone()[0]
    record("PASS" if orphaned == 0 else "WARN", "Job cards - no orphaned FK",
           f"{orphaned} orphaned" if orphaned else "")
except Exception as e:
    record("WARN", "Job card FK check", str(e)[:80])

# Negative stock
try:
    from spares.models import StockLedger
    neg = StockLedger.objects.filter(quantity__lt=0).count()
    record("PASS" if neg == 0 else "WARN", "Stock - no negative quantities",
           f"{neg} items negative" if neg else "")
except Exception as e:
    record("WARN", "Stock check", str(e)[:80])

# Zero-amount invoices
try:
    zero_inv = Invoice.objects.filter(final_amount__lte=0).count()
    record("PASS" if zero_inv == 0 else "WARN", "Invoices - no zero-amount",
           f"{zero_inv} zero-amount invoices" if zero_inv else "")
except Exception as e:
    record("WARN", "Invoice amount check", str(e)[:80])

# Unverified OTPs older than 15 minutes (stale test data)
try:
    from django.utils import timezone as tz
    from datetime import timedelta
    stale = OTPVerification.objects.filter(
        is_verified=False,
        expires_at__lt=tz.now()
    ).count()
    record("PASS" if stale == 0 else "WARN", "No stale/expired OTPs",
           f"{stale} expired unverified OTPs in DB" if stale else "")
except Exception as e:
    record("WARN", "OTP stale check", str(e)[:80])

# Check migrations are all applied
try:
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    record("PASS" if not plan else "FAIL", "All migrations applied",
           f"{len(plan)} unapplied migrations" if plan else "")
except Exception as e:
    record("WARN", "Migration check", str(e)[:80])

# ── Data Counts (informational) ───────────────────────────────
section("14. Database Counts (informational)")
counts = {}
try:
    counts = {
        "Customers": Customer.objects.count(),
        "Bike Models": BikeModel.objects.count(),
        "Vehicle Stock": VehicleStock.objects.count(),
        "Customer Vehicles": CustomerVehicle.objects.count(),
        "Sales Enquiries": SalesEnquiry.objects.count(),
        "Sales Orders": VehicleSalesOrder.objects.count(),
        "Job Cards": JobCard.objects.count(),
        "Spares Items": SparesItem.objects.count(),
        "Invoices": Invoice.objects.count(),
        "RTO Registrations": RTORegistration.objects.count(),
        "Service Reminders": ServiceReminder.objects.count(),
        "Test Rides": TestRideLog.objects.count(),
        "PDI Checklists": PDIChecklist.objects.count(),
        "Sales Targets": SalesTarget.objects.count(),
    }
    for k, v in counts.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(f"  Count error: {e}")

# ── Final Report ──────────────────────────────────────────────
section("FINAL REPORT")
total = len(PASS_RESULTS) + len(FAIL_RESULTS) + len(WARN_RESULTS) + len(SKIP_RESULTS)
print(f"""
  Total checks  : {total}
  PASS          : {len(PASS_RESULTS)}
  FAIL          : {len(FAIL_RESULTS)}
  WARN          : {len(WARN_RESULTS)}
  SKIP (no data): {len(SKIP_RESULTS)}
""")

if FAIL_RESULTS:
    print("FAILURES:")
    for f in FAIL_RESULTS:
        print(f"  - {f['name']}: {f['detail']}")

if WARN_RESULTS:
    print("\nWARNINGS:")
    for w in WARN_RESULTS:
        print(f"  - {w['name']}: {w['detail']}")

if SKIP_RESULTS:
    print(f"\nSKIPPED (no existing DB records to test detail/edit views):")
    for sk in SKIP_RESULTS:
        print(f"  - {sk['name']}")

results = {
    "summary": {"total": total, "pass": len(PASS_RESULTS),
                 "fail": len(FAIL_RESULTS), "warn": len(WARN_RESULTS),
                 "skip": len(SKIP_RESULTS)},
    "db_counts": counts,
    "pass": PASS_RESULTS, "fail": FAIL_RESULTS,
    "warn": WARN_RESULTS, "skip": SKIP_RESULTS,
}
with open("test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nFull results saved to test_results.json")
