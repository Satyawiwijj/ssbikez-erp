# Data migration -- backfills return_qty on existing CounterSaleReturnItem
# rows that predate this field (all currently sit at the default 0), so the
# stock-reversal signal added in the previous round can stop guessing via a
# falsy-zero fallback (`return_qty if return_qty else quantity`), which
# incorrectly also fires for a genuinely-zero return, not just a legacy row.
#
# Mapping: return_qty=0 -> return_qty=quantity (the pre-existing convention,
# where quantity itself was the returned amount before this field existed).
# Any row with a real non-zero return_qty is left untouched.
from django.db import migrations
from django.db.models import F


def forwards(apps, schema_editor):
    CounterSaleReturnItem = apps.get_model('spares', 'CounterSaleReturnItem')
    CounterSaleReturnItem.objects.filter(return_qty=0).update(return_qty=F('quantity'))


def backwards(apps, schema_editor):
    # No-op: there's no way to distinguish "backfilled from quantity" from a
    # genuinely-equal-to-quantity value entered by a real user after this
    # migration ran, so reversing would be a guess -- leave data as-is.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('spares', '0014_countersale_stock_posted_countersale_stock_reversed_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
