# SSBikez ERP

A full-featured, production-ready ERP system for an authorised motorcycle dealership, built with Django 6 and Python 3.14.

---

## Features

### Sales & CRM
- **Enquiry management** — track leads with status workflow (New → Follow-Up → Test Ride → Negotiation → Won/Lost)
- **Sales appointments** — schedule test rides and follow-up visits
- **Sales orders** — end-to-end order lifecycle with status tracking
- **Delivery management** — record PDI, accessories fitted, and handover details

### Customer Management
- Customer profiles with contact details and purchase history
- Bike model catalogue (manufacturer, variants, on-road pricing)
- Vehicle stock inventory (chassis/engine numbers, colour, branch)
- Customer-vehicle registry linking owners to registered bikes

### Finance & Billing
- **Tax invoices** (PDF) — sales invoices with CGST/SGST split, amount in words, discount support
- **Service invoices** (PDF) — labor + parts + outwork with full GST breakdown
- Payment tracking (cash, UPI, finance, cheque) with balance calculation
- Loan and EMI tracking (bank, sanctioned amount, EMI details)
- Insurance policy management

### RTO / Registration
- Vehicle registration records linked to sales orders
- Number plate assignment and tracking

### Service Department
- **Job cards** — full service workflow (Pending → Water Wash → In Bay → In Progress → Outwork → Final Inspection → Ready → Invoiced)
- Bay management — assign mechanics to service bays with time tracking
- Labor charge recording per job card
- Spares issue / return tracking (net quantity, unit price, line total)
- **Outwork (subcontracting)** — send work to external vendors, track return and cost
- **Print job card** — standalone print-friendly layout with signature blocks

### Spares & Inventory
- Part catalogue with category, supplier, HSN code, MRP, stock quantity
- Purchase orders with receive workflow
- Counter sales (walk-in retail)
- Spares issue to job cards with return tracking
- Low-stock alerts (threshold-based badge in search and UI)

### Value-Added Services (VAS)
- AMC packages (Annual Maintenance Contract)
- RSA packages (Roadside Assistance)
- Protection Plus packages

### Reporting
- Sales report (orders, revenue, by date range)
- Spares report (issues, counter sales, stock value)
- Service report (job cards, job completion rates, revenue)

### Admin & System
- Multi-user with role-based access (Admin, Sales Executive, Service Advisor, Mechanic, etc.)
- Multi-branch support
- Fuel expense tracking
- **Global search** — instant search across customers, vehicles, orders, job cards, spare parts
- **Audit logging** — every create/update/delete/status-change recorded with user, module, action, IP
- User profile management (self-service name/email/phone update)
- Admin branding (Django admin customised with SSBikez ERP identity)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.1, Python 3.14 |
| Database | SQLite (dev) / PostgreSQL (prod via `dj-database-url`) |
| PDF generation | xhtml2pdf (pisa) |
| Static files | WhiteNoise (compressed + cached) |
| WSGI server | Gunicorn |
| Deployment | Railway / any PaaS supporting Procfile |

---

## Local Setup

```bash
# 1. Clone
git clone https://github.com/yourorg/ssbikez-erp.git
cd ssbikez-erp

# 2. Create and activate virtualenv
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env      # Windows
# cp .env.example .env       # Linux/macOS
# Edit .env — set SECRET_KEY at minimum

# 5. Apply migrations
python manage.py migrate

# 6. Create a superuser
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/accounts/login/` to log in.

---

## Production Deployment (Railway)

1. Push to GitHub
2. Create a new Railway project → **Deploy from GitHub repo**
3. Add a PostgreSQL plugin in Railway — it auto-sets `DATABASE_URL`
4. Set environment variables in Railway dashboard:
   - `SECRET_KEY` — a long random string
   - `DEBUG` — `False`
   - `ALLOWED_HOSTS` — your Railway domain (e.g. `ssbikez-erp.up.railway.app`)
   - Email variables as needed
5. Railway will build using Nixpacks and start with `gunicorn ssbikez.wsgi`
6. Run migrations via Railway's shell or add a `release` command to `Procfile`

---

## Project Structure

```
ssbikez-erp/
├── accounts/           # Users, roles, branches, audit log, dashboard, search, reports
├── billing/            # Invoices, payments, loans, insurance, PDF views
├── customers/          # Customer profiles, bike models, vehicle stock
├── customer_vehicles/  # Customer-vehicle registry
├── rto/                # RTO registrations, number plates
├── sales/              # Enquiries, appointments, orders, deliveries
├── service/            # Job cards, bays, labor, outwork, service invoices
├── spares/             # Parts, categories, suppliers, POs, counter sales, issues
├── vas/                # AMC, RSA, Protection Plus packages
├── templates/          # All HTML templates (base.html + per-app)
├── ssbikez/            # Django project settings, URLs, WSGI
├── Procfile            # Gunicorn start command
├── railway.json        # Railway deployment config
├── .env.example        # Environment variable template
└── requirements.txt    # Python dependencies
```

---

## Key URLs

| URL | Description |
|---|---|
| `/accounts/login/` | Login page |
| `/accounts/dashboard/` | Main dashboard with live stats |
| `/accounts/search/?q=...` | Global search |
| `/accounts/profile/` | User profile |
| `/customers/` | Customer list |
| `/sales/enquiries/` | Sales enquiries |
| `/sales/orders/` | Sales orders |
| `/billing/invoices/` | Tax invoices |
| `/billing/invoices/<id>/pdf/` | Download sales invoice PDF |
| `/service/jobcards/` | Job cards |
| `/service/jobcards/<id>/print/` | Print job card |
| `/billing/service-invoice/<jc_id>/pdf/` | Download service invoice PDF |
| `/spares/parts/` | Spare parts inventory |
| `/admin/` | Django admin |

---

## License

Proprietary — SSBikez. All rights reserved.
