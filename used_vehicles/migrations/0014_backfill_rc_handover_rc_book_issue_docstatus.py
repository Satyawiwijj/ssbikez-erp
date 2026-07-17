# Data migration -- backfills docstatus on existing UsedVehicleRCHandOver /
# UsedVechileRCBookIssue rows from their pre-existing flat `status` field, so
# rows created before the Phase-13 DocStatusMixin restructure don't silently
# reset to Draft. Same forwards/backwards RunPython shape as
# billing/migrations/0007_journal_entry_lines_data.py (the one other
# data-preserving migration in this codebase).
#
# Mapping: status='handed_over' / 'issued' (the terminal, "done" values) ->
# docstatus=SUBMITTED, so pre-existing completed handovers/issues read as
# Submitted rather than Draft. status='pending' -> docstatus stays DRAFT
# (the AddField default), since nothing happened yet on those rows.
#
# submitted_by/submitted_at are deliberately left null on backfilled rows --
# no historical actor/timestamp exists to attribute the pre-migration state
# to, and fabricating one would be worse than an honest gap. The audit trail
# starts fresh from this migration forward.
from django.db import migrations


def forwards(apps, schema_editor):
    UsedVehicleRCHandOver = apps.get_model('used_vehicles', 'UsedVehicleRCHandOver')
    UsedVechileRCBookIssue = apps.get_model('used_vehicles', 'UsedVechileRCBookIssue')

    SUBMITTED = 1

    UsedVehicleRCHandOver.objects.filter(status='handed_over').update(docstatus=SUBMITTED)
    UsedVechileRCBookIssue.objects.filter(status='issued').update(docstatus=SUBMITTED)


def backwards(apps, schema_editor):
    # No-op: docstatus is a new field with no prior meaning to restore --
    # reversing just leaves it at the AddField default (Draft), same
    # no-op-on-reverse rationale as the billing/0007 precedent.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('used_vehicles', '0013_docstatus_rc_handover_rc_book_issue'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
