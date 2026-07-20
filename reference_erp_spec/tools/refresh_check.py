"""
reference_erp_spec/tools/refresh_check.py

One-shot check: log into the live reference server via Frappe's REST API
and compare its current doctype/client-script counts against the baseline
recorded in reference_erp_spec/README.md (429 custom doctypes, 201 client
scripts). If they match, the existing spec docs are trustworthy as-is for
tonight's comparison. If they don't, print exactly which counts moved so
the affected module file(s) can be re-pulled before use.

Run: python reference_erp_spec/tools/refresh_check.py
"""
import os
import sys

import requests

BASELINE_DOCTYPE_COUNT = 429
BASELINE_CLIENT_SCRIPT_COUNT = 201


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
    login = session.post(
        f'{site_root}/api/method/login',
        data={'usr': user, 'pwd': password},
        timeout=30,
    )
    login.raise_for_status()

    doctype_resp = session.get(
        f'{site_root}/api/resource/DocType',
        params={'filters': '[["module","=","Ssbikez"],["custom","=",1]]', 'limit_page_length': 0},
        timeout=60,
    )
    doctype_resp.raise_for_status()
    live_doctype_count = len(doctype_resp.json().get('data', []))

    script_resp = session.get(
        f'{site_root}/api/resource/Client Script',
        params={'limit_page_length': 0},
        timeout=60,
    )
    script_resp.raise_for_status()
    live_script_count = len(script_resp.json().get('data', []))

    print(f'Live custom doctype count (Ssbikez module): {live_doctype_count} (baseline: {BASELINE_DOCTYPE_COUNT})')
    print(f'Live client script count: {live_script_count} (baseline: {BASELINE_CLIENT_SCRIPT_COUNT})')

    drifted = (live_doctype_count != BASELINE_DOCTYPE_COUNT) or (live_script_count != BASELINE_CLIENT_SCRIPT_COUNT)
    print('DRIFT DETECTED — re-pull affected spec files before trusting them.' if drifted else 'Baseline confirmed current.')
    sys.exit(1 if drifted else 0)


if __name__ == '__main__':
    main()
