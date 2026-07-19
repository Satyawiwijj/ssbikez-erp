"""
Minimal, self-contained test-data builders for E2E flows.

StaticLiveServerTestCase runs against Django's *test* database (migrated
fresh, empty), not the dev database used during manual QA this session --
so every flow test builds exactly the fixture chain it needs from scratch
rather than assuming any row already exists.
"""
from datetime import date

from accounts.models import CompanySettings
from customers.models import Customer
from used_vehicles.models import (
    ManufacturingCompany,
    UsedVehicleColor,
    UsedVehicleModel,
    UsedVehicleRegisterNo,
    UsedVehicleSale,
    UsedVehicleSubGroup,
)


def make_customer(full_name='E2E Test Customer', phone='9000000001', state=''):
    return Customer.objects.create(full_name=full_name, phone=phone, state=state)


def make_company_settings(state='Tamil Nadu', cgst_rate=9, sgst_rate=9):
    settings_ = CompanySettings.get_instance()
    settings_.state = state
    settings_.cgst_rate = cgst_rate
    settings_.sgst_rate = sgst_rate
    settings_.save()
    return settings_


def make_used_vehicle_register_no(chassis_no='E2ECHASSIS001', registration_no='TN01E2E0001'):
    manufacturer = ManufacturingCompany.objects.create(name='E2E Test Manufacturer')
    sub_group = UsedVehicleSubGroup.objects.create(name='E2E Test Sub Group')
    model = UsedVehicleModel.objects.create(
        code='E2E-MODEL-001',
        manufacturer=manufacturer,
        used_vehicle_name='E2E Test Model',
        sub_group=sub_group,
    )
    color = UsedVehicleColor.objects.create(name='E2E Red')
    return UsedVehicleRegisterNo.objects.create(
        used_vehicle=model,
        color=color,
        chassis_no=chassis_no,
        engine_no='E2EENGINE001',
        registration_no=registration_no,
        stock_status=UsedVehicleRegisterNo.StockStatus.AVAILABLE,
    )


def make_used_vehicle_sale(customer=None):
    customer = customer or make_customer()
    register_no = make_used_vehicle_register_no()
    return UsedVehicleSale.objects.create(
        customer=customer,
        vehicle_number=register_no,
        sale_amount=50000,
        delivery_date=date.today(),
    )
