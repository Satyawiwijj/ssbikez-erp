"""
reference_erp_spec/tools/check_supplier_fields.py

One-shot re-check of the reference server's Supplier doctype field list.
The original bulk extraction failed for this specific doctype (recorded
in reference_erp_spec/26_Master.md as "NOT FOUND on server"); this pulls
it directly so the client's "important fields are missing" report can be
checked against real data instead of guessed from screenshots.

Run: python reference_erp_spec/tools/check_supplier_fields.py
"""
import json
import os
import sys

import requests


def load_env(path='.env'):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            values[key.strip()] = value.strip()
    return values


def main():
    env = {**load_env(), **os.environ}
    base_url = env.get('REFERENCE_ERP_URL')
    user = env.get('REFERENCE_ERP_USER')
    password = env.get('REFERENCE_ERP_PASSWORD')
    if not (base_url and user and password):
        print('Missing REFERENCE_ERP_URL / REFERENCE_ERP_USER / REFERENCE_ERP_PASSWORD in .env')
        sys.exit(1)

    site_root = base_url.split('/app/')[0]
    session = requests.Session()
    login = session.post(f'{site_root}/api/method/login', data={'usr': user, 'pwd': password}, timeout=30)
    login.raise_for_status()

    resp = session.get(f'{site_root}/api/resource/DocType/Supplier', timeout=60)
    resp.raise_for_status()
    data = resp.json().get('data', {})
    fields = data.get('fields', [])

    print(f'Supplier doctype: {len(fields)} fields')
    for f in fields:
        print(f"  {f.get('fieldname')} | {f.get('fieldtype')} | {f.get('label')} | reqd={f.get('reqd')}")

    out_path = os.path.join(os.path.dirname(__file__), '..', '_raw_api_data', 'std_doctypes_full', 'Supplier.json')
    with open(out_path, 'w', encoding='utf-8') as out:
        json.dump({'data': data}, out, indent=2)
    print(f'Wrote full field data to {out_path}')


if __name__ == '__main__':
    main()
