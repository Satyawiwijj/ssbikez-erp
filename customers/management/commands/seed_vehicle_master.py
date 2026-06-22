from decimal import Decimal

from django.core.management.base import BaseCommand

from customers.models import BikeModel, VehicleStock


BIKE_MODELS = [
    # brand, model_name, variant, fuel_type, ex_showroom_price, dealer_cost_price
    ('Honda',    'Shine',      'Standard', 'petrol', Decimal('79900'),  Decimal('72000')),
    ('Honda',    'Activa 6G',  'Standard', 'petrol', Decimal('84900'),  Decimal('76500')),
    ('Hero',     'Splendor+',  'Standard', 'petrol', Decimal('74900'),  Decimal('67500')),
    ('Hero',     'HF Deluxe',  'Standard', 'petrol', Decimal('69900'),  Decimal('63000')),
    ('TVS',      'Jupiter',    'Standard', 'petrol', Decimal('89900'),  Decimal('81000')),
    ('Bajaj',    'Pulsar 150', 'Single Disc', 'petrol', Decimal('124900'), Decimal('113000')),
    ('Ather',    '450X',       'Standard', 'electric', Decimal('149900'), Decimal('138000')),
]

COLORS = ['Red', 'Black', 'Blue', 'White', 'Grey']


class Command(BaseCommand):
    help = (
        'Seeds demo Bike Models and available Vehicle Stock so Customer Vehicle, '
        'Sales Order, Exchange Vehicle, RTO Registration and Sales Enquiry flows '
        'have data to work against. Safe to re-run — uses get_or_create.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--units-per-model', type=int, default=2,
            help='Number of in-stock units to create per bike model (default: 2)',
        )

    def handle(self, *args, **options):
        units_per_model = options['units_per_model']
        created_models = 0
        created_units = 0

        for brand, model_name, variant, fuel_type, ex_price, dealer_price in BIKE_MODELS:
            bike_model, created = BikeModel.objects.get_or_create(
                brand=brand, model_name=model_name, variant=variant,
                defaults={
                    'fuel_type': fuel_type,
                    'ex_showroom_price': ex_price,
                    'dealer_cost_price': dealer_price,
                    'available_colors': ', '.join(COLORS),
                },
            )
            created_models += int(created)

            for i in range(units_per_model):
                chassis_no = f'SEED-{brand[:3].upper()}-{model_name[:4].upper()}-CH{i+1:03d}'
                engine_no = f'SEED-{brand[:3].upper()}-{model_name[:4].upper()}-EN{i+1:03d}'
                _, unit_created = VehicleStock.objects.get_or_create(
                    chassis_no=chassis_no,
                    defaults={
                        'bike_model': bike_model,
                        'engine_no': engine_no,
                        'color': COLORS[i % len(COLORS)],
                        'stock_status': VehicleStock.StockStatus.AVAILABLE,
                    },
                )
                created_units += int(unit_created)

        self.stdout.write(self.style.SUCCESS(
            f'Done. Bike Models created: {created_models}. Vehicle Stock units created: {created_units}.'
        ))
