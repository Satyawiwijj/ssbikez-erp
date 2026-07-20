"""
reference_erp_spec/tools/build_matrix_skeleton.py

Turns the already-extracted reference-server field data into the starting
rows of docs/audit/PARITY_MATRIX.csv. Reference-side columns are filled
from the per-doctype raw API dumps in doctypes_raw/; the Django-side and
status columns are left blank for the manual walkthrough (Task 3/7 of the
audit plan) to fill in.

Run: python reference_erp_spec/tools/build_matrix_skeleton.py
"""
import csv
import glob
import json
import os

RAW_DOCTYPES_DIR = os.path.join(os.path.dirname(__file__), '..', '_raw_api_data', 'doctypes_raw')
OUT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'audit', 'PARITY_MATRIX.csv')

COLUMNS = [
    'module', 'doctype', 'field', 'fieldtype', 'mandatory', 'reference_note',
    'django_app', 'django_model', 'django_field', 'status', 'evidence',
]


def main():
    rows = []
    doctype_files = sorted(glob.glob(os.path.join(RAW_DOCTYPES_DIR, '*.json')))
    for path in doctype_files:
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)
        dt = raw.get('data', raw)
        name = dt.get('name', os.path.splitext(os.path.basename(path))[0])
        module = dt.get('module', 'Ssbikez')
        fields = dt.get('fields', [])
        if not fields:
            rows.append([module, name, '', '', '', 'no fields recorded (istable/issingle config doctype?)', '', '', '', '', ''])
            continue
        for field in fields:
            rows.append([
                module, name,
                field.get('fieldname', ''), field.get('fieldtype', ''),
                'yes' if field.get('reqd') else 'no',
                (field.get('label') or '').strip(),
                '', '', '', '', '',
            ])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f'Wrote {len(rows)} rows from {len(doctype_files)} doctype files to {OUT_PATH}')


if __name__ == '__main__':
    main()
