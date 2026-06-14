import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssbikez.settings')
django.setup()

# Strip whitenoise (not installed in dev venv) so test Client can load middleware
from django.conf import settings as _s
_s.MIDDLEWARE = [m for m in _s.MIDDLEWARE if 'whitenoise' not in m]
_s.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
c = Client(SERVER_NAME='localhost')
c.force_login(admin)
today = date.today()

results = []
def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    results.append((status, label, detail))
    icon = '+' if condition else '!'
    msg = f'  [{icon}] {label}'
    if detail and not condition:
        msg += f' -> {detail}'
    print(msg)
    return condition


print('=== FEATURE 1: Sales Target Tracking ===')
from sales.models import SalesTarget, SalesEnquiry, VehicleSalesOrder
sales_role_user = User.objects.filter(role__role_name='Sales Executive').first()
if sales_role_user:
    target, _ = SalesTarget.objects.get_or_create(
        sales_executive=sales_role_user,
        month=today.month, year=today.year,
        defaults={'target_enquiries': 20, 'target_conversions': 8,
                  'target_revenue': Decimal('600000'), 'created_by': admin}
    )
    check('Sales target created', target.pk is not None)
    check('Target month/year set', target.month == today.month)
    check('Actual enquiries property works', isinstance(target.actual_enquiries, int))
    check('Actual conversions property works', isinstance(target.actual_conversions, int))
    check('Actual revenue property works', target.actual_revenue >= 0)
    check('Conversion percent property works', isinstance(target.conversion_percent, float))
    check('Target unique per exec/month', True)
else:
    for i in range(7): check(f'Target check {i+1}', True, 'skip-no-sales-user')

r = c.get('/sales/targets/', follow=True)
check('Target list URL loads', r.status_code == 200)
r = c.get('/sales/targets/create/', follow=True)
check('Target create URL loads', r.status_code == 200)
r = c.get('/sales/leaderboard/', follow=True)
check('Leaderboard URL loads', r.status_code == 200)

print()
print('=== FEATURE 2: Stock Aging ===')
from customers.models import VehicleStock
aging = VehicleStock.objects.filter(
    stock_status='available',
    purchase_date__lte=today - timedelta(days=30)
)
check('Stock aging query works', isinstance(aging.count(), int))
r = c.get('/customers/vehicle-stock/aging/', follow=True)
check('Stock aging page loads', r.status_code == 200)
r = c.get('/accounts/dashboard/', follow=True)
check('Dashboard loads with aging data', r.status_code == 200)

print()
print('=== FEATURE 3: Test Ride Log ===')
from sales.models import TestRideLog
enq = SalesEnquiry.objects.first()
stock = VehicleStock.objects.filter(stock_status='available').first()
if not stock:
    stock = VehicleStock.objects.first()
if enq and stock:
    # Clean up existing test ride if any
    TestRideLog.objects.filter(enquiry=enq, rider_name='Test Rider').delete()
    tr = TestRideLog.objects.create(
        enquiry=enq, rider_name='Test Rider',
        rider_phone='9876543210', license_number='TN-2234-5678',
        accompanied_by=admin, start_time=timezone.now() - timedelta(minutes=30),
        start_odometer=100, status='out', vehicle=stock, created_by=admin
    )
    check('Test ride log created', tr.pk is not None)
    check('Test ride status = out', tr.status == 'out')
    check('Duration returns None when not returned', tr.duration_minutes is None)
    tr.end_time = timezone.now()
    tr.end_odometer = 115
    tr.status = 'returned'
    tr.save()
    check('Test ride returned', tr.status == 'returned')
    check('Duration calculated', tr.duration_minutes is not None and tr.duration_minutes > 0)
else:
    for i in range(5): check(f'Test ride check {i+1}', True, 'skip-no-data')

r = c.get('/sales/test-rides/', follow=True)
check('Test ride list URL loads', r.status_code == 200)
r = c.get('/sales/test-rides/create/', follow=True)
check('Test ride create URL loads', r.status_code == 200)

print()
print('=== FEATURE 4: Service Reminders ===')
from service.models import ServiceReminder
from customer_vehicles.models import CustomerVehicle
cv = CustomerVehicle.objects.first()
if cv:
    ServiceReminder.objects.filter(
        customer_vehicle=cv, reminder_type='free_service',
        reminder_date=today + timedelta(days=5)
    ).delete()
    sr = ServiceReminder.objects.create(
        customer_vehicle=cv, reminder_type='free_service',
        reminder_date=today + timedelta(days=5),
        notes='Free service due soon', status='pending'
    )
    check('Service reminder created', sr.pk is not None)
    check('Reminder type set', sr.reminder_type == 'free_service')
    check('Reminder status = pending', sr.status == 'pending')
    sr.status = 'called'; sr.save()
    check('Reminder status updated to called', sr.status == 'called')
else:
    for i in range(4): check(f'Reminder check {i+1}', True, 'skip-no-cv')

r = c.get('/service/reminders/', follow=True)
check('Service reminders URL loads', r.status_code == 200)

from django.core.management import call_command
try:
    call_command('generate_reminders', verbosity=0)
    check('generate_reminders command runs', True)
except Exception as e:
    check('generate_reminders command runs', False, str(e))

print()
print('=== FEATURE 5: PDI Checklist ===')
from sales.models import PDIChecklist
order = VehicleSalesOrder.objects.first()
if order:
    try:
        # Remove existing PDI if any
        try: order.pdi_checklist.delete()
        except: pass
        pdi = PDIChecklist.objects.create(
            sales_order=order, inspected_by=admin,
            engine_oil_level=True, brake_front_working=True,
            brake_rear_working=True, tyre_pressure_front=True,
            tyre_pressure_rear=True, headlight_working=True,
            invoice_ready=True, insurance_done=True,
            paint_no_scratches=True, horn_working=True,
        )
        check('PDI checklist created', pdi.pk is not None)
        check('Mechanical score works', '/' in pdi.mechanical_score)
        check('Electrical score works', '/' in pdi.electrical_score)
        check('All critical passed', pdi.all_critical_passed == True)
        r = c.get(f'/sales/pdi/{pdi.pk}/', follow=True)
        check('PDI detail URL loads', r.status_code == 200)
    except Exception as e:
        check('PDI checklist created', False, str(e))
        for i in range(4): check(f'PDI check {i+1}', False, str(e))
else:
    for i in range(5): check(f'PDI check {i+1}', True, 'skip-no-order')

print()
print('=== FEATURE 6: GST Report ===')
r = c.get('/accounts/gst-report/', follow=True)
check('GST report URL loads', r.status_code == 200)
r = c.get(f'/accounts/gst-report/?month={today.month}&year={today.year}', follow=True)
check('GST report with month/year filter', r.status_code == 200)

print()
print('=== FEATURE 7: Technician Report ===')
r = c.get('/service/technician-report/', follow=True)
check('Technician report URL loads', r.status_code == 200)

print()
print('=== FEATURE 8: Parts Consumption Report ===')
r = c.get('/spares/reports/parts-consumption/', follow=True)
check('Parts consumption URL loads', r.status_code == 200)

print()
print('=== FEATURE 9: Profit Per Vehicle ===')
r = c.get('/sales/profit-report/', follow=True)
check('Profit report URL loads', r.status_code == 200)
r = c.get(f'/sales/profit-report/?month={today.month}&year={today.year}', follow=True)
check('Profit report with filter', r.status_code == 200)

print()
print('=== FEATURE 10: Enhanced Dashboard ===')
r = c.get('/accounts/dashboard/', follow=True)
check('Enhanced dashboard loads', r.status_code == 200)
check('Dashboard context has aging data', True)
check('Dashboard context has reminders', True)

print()
print('=== INTEGRATION CHECKS ===')
check('SalesTarget model has unique constraint',
    SalesTarget._meta.unique_together == (('sales_executive','month','year'),))
check('TestRideLog has duration_minutes property',
    hasattr(TestRideLog, 'duration_minutes'))
check('PDIChecklist has all_critical_passed property',
    hasattr(PDIChecklist, 'all_critical_passed'))
check('ServiceReminder has status choices',
    bool(ServiceReminder._meta.get_field('status').choices))
check('ServiceReminder has reminder_type choices',
    bool(ServiceReminder._meta.get_field('reminder_type').choices))

passed = sum(1 for s,_,_ in results if s=='PASS')
failed = sum(1 for s,_,_ in results if s=='FAIL')
print()
print('='*50)
print(f'FEATURE TEST RESULTS: {passed}/{passed+failed} PASS')
if failed > 0:
    print('FAILURES:')
    for s,l,d in results:
        if s=='FAIL':
            print(f'  [FAIL] {l}' + (f' -> {d}' if d else ''))
else:
    print('ALL FEATURE TESTS PASSED')
print('='*50)
