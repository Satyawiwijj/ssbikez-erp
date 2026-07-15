# SSBikez ERP

A full-featured, production-ready ERP system for a motorcycle dealership, built with Django 6
and Python 3.12. Covers new-vehicle sales, used-vehicle sales, service/workshop, spares
inventory, RTO registration, value-added services (AMC/RSA/warranty), billing, and a wholesale
dealer-resale channel.

**→ See [CLIENT_GUIDE.md](CLIENT_GUIDE.md) for the complete setup, deployment, module-by-module
workflow, troubleshooting, and role/permissions guide.**

---

## Quick start

```bash
git clone https://github.com/Satyawiwijj/ssbikez-erp.git
cd ssbikez-erp
python -m venv venv
venv\Scripts\activate          # Windows — or: source venv/bin/activate on Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py create_default_superuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. Full details — including why login requires a working email
configuration even locally — are in [CLIENT_GUIDE.md](CLIENT_GUIDE.md#2-local-setup-from-zero).

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.7, Python 3.12 |
| Database | SQLite (dev, default) / PostgreSQL (prod, via `dj-database-url`) |
| PDF generation | xhtml2pdf |
| Static files | WhiteNoise |
| WSGI server | Gunicorn |
| Deployment | Render (`render.yaml` included) — see [CLIENT_GUIDE.md](CLIENT_GUIDE.md#3-deploying-to-render) |

## Project structure

```
ssbikez-erp/
├── accounts/           # Users, roles, branches, audit log, dashboard, search, admin settings
├── billing/             # Invoices, payments, loans, insurance, journal entries, PDF views
├── customers/           # Customer profiles, bike model catalog, vehicle stock
├── customer_vehicles/   # Customer-to-vehicle registry (bridge table)
├── masters/              # Shared reference data: suppliers, warehouses, pricing masters
├── rto/                  # Vehicle registration, number plates, RC books
├── sales/                # Enquiries, appointments, sales orders, deliveries, dealer resale
├── service/              # Job cards and the full workshop pipeline
├── spares/               # Parts inventory, purchase orders, counter sales
├── used_vehicles/        # The full used-vehicle sales/service pipeline
├── vas/                   # AMC / RSA / Protection Plus packages
├── templates/            # All HTML templates (base.html + per-app)
├── ssbikez/               # Django project settings, URLs, WSGI
├── render.yaml            # Render deployment blueprint
├── .github/workflows/     # CI (runs the test suite on every push/PR)
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies
```

## Testing

```bash
python manage.py test
```

58 automated tests cover RBAC/permissions, ownership checks, and the specific bugs found and
fixed during development, across 10 of the 11 apps. Runs automatically in CI on every push/PR.

## License

Proprietary — SSBikez. All rights reserved.
