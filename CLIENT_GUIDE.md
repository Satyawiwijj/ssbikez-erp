# SSBikez ERP — Complete Setup, Deployment & Workflow Guide

This is the single reference document for running, deploying, and using this system.
If you only read one file in this repo, read this one.

## Table of contents

1. [What this system is](#1-what-this-system-is)
2. [Local setup, from zero](#2-local-setup-from-zero)
3. [Deploying to Render](#3-deploying-to-render)
4. [Environment variables — complete reference](#4-environment-variables--complete-reference)
5. [User roles & permissions](#5-user-roles--permissions)
6. [Module-by-module workflow guide](#6-module-by-module-workflow-guide)
7. [Troubleshooting — every known error and its fix](#7-troubleshooting--every-known-error-and-its-fix)
8. [Testing & CI](#8-testing--ci)
9. [Known limitations and accepted risks](#9-known-limitations-and-accepted-risks)
10. [Day-to-day maintenance](#10-day-to-day-maintenance)

---

## 1. What this system is

SSBikez ERP is a Django-based dealership management system for a motorcycle dealership,
covering new-vehicle sales, used-vehicle sales, service/workshop, spares inventory,
RTO (vehicle registration) paperwork, value-added services (AMC/RSA/warranty), billing,
and a wholesale "dealer" resale channel for traded-in vehicles.

It is built as 11 Django apps, each owning one business area:

| App | URL prefix | Covers |
|---|---|---|
| `accounts` | `/accounts/` | Login, users, roles, branches, dashboard, global search, audit log, admin settings |
| `customers` | `/customers/` | Customer profiles, bike model catalog, vehicle stock |
| `customer_vehicles` | `/customer-vehicles/` | The bridge table linking a customer to a vehicle they own |
| `sales` | `/sales/` | Enquiries, appointments, sales orders, deliveries, exchange vehicles, the dealer resale sub-module |
| `billing` | `/billing/` | Invoices, payments, loans, insurance, journal entries, PDF generation |
| `service` | `/service/` | Job cards and the full workshop pipeline (water wash → bay in → outwork → final inspection → invoice) |
| `spares` | `/spares/` | Spare parts inventory, purchase orders, counter sales, stock reconciliation |
| `rto` | `/rto/` | Vehicle registration, number plates, RC books, RTO payments |
| `vas` | `/vas/` | AMC / RSA / Protection Plus packages |
| `used_vehicles` | `/used-vehicles/` | The entire used-vehicle side: purchase → sale → delivery → invoice → service |
| `masters` | `/masters/` | Shared reference data: suppliers, warehouses, pricing masters, numbering series |

Every business document (Sales Order, Invoice, Job Card, AMC Package, etc.) follows the same
**Draft → Submitted → Cancelled → Amended** lifecycle (a `docstatus` field), matching how the
reference ERP this was built from behaves. A Draft can be freely edited; a Submitted document
is locked; Cancelling a Submitted document lets you Amend it into a fresh linked Draft rather
than editing history.

---

## 2. Local setup, from zero

### Requirements
- Python 3.12+ (the deployed environment pins 3.12 via `runtime.txt`)
- Git

### Steps

```bash
# 1. Clone
git clone https://github.com/Satyawiwijj/ssbikez-erp.git
cd ssbikez-erp

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional for local dev — see section 4)
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
# With no .env at all, the app still runs: DEBUG defaults to True and the
# database falls back to a local db.sqlite3 file automatically.

# 5. Apply migrations
python manage.py migrate

# 6. Create your first admin login
python manage.py create_default_superuser
# Creates a user "admin" if (and only if) no superuser exists yet.
# Set DJANGO_SUPERUSER_PASSWORD in your environment first, or it generates
# a random one and prints it once — copy it down immediately, it is not
# shown again.

# 7. Run the dev server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` — it redirects to the login page.

### Logging in for the first time

This system requires email-based two-factor login (OTP) for every account, including
superusers. That means **email sending must work**, even locally, or you cannot log in at all.
With no `EMAIL_*` variables set, Django uses its console backend and prints the OTP code to
your terminal instead of emailing it — that's normal for local development, just watch the
terminal output after submitting your password.

### Optional: seed realistic demo data

```bash
python manage.py seed_vehicle_master
```

Populates bike models and vehicle stock so you have something to click through immediately.
There is also a `seed_real_data.py` script at the repo root (`python seed_real_data.py`) that
populates a much larger, cross-module demo dataset — **do not run this against a real client
database**, it's for local demos/training only.

---

## 3. Deploying to Render

This repo ships a ready-to-use `render.yaml` (Render's "Infrastructure as Code" format), so
deployment is mostly point-and-click.

### Step by step

1. **Push this repo to the GitHub account/org your Render account can see.**
2. In the Render dashboard, choose **New → Blueprint**, and point it at this repo. Render reads
   `render.yaml` automatically and proposes two resources: a **web service** (`ssbikez-erp`) and
   a **PostgreSQL database** (`ssbikez-db`).
3. Before the first deploy, Render will prompt you for every environment variable marked
   `sync: false` in `render.yaml` — these are deliberately **not** stored in the repo:
   - `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` — see section 4 for how to
     get a Gmail App Password. **Login will not work at all until these are set correctly**,
     since OTP codes can't be delivered.
   - `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` — the first admin account's real
     login. Pick a strong password; this is a real production credential.
   - `DJANGO_SECRET_KEY` is auto-generated by Render (`generateValue: true`) — you don't need to
     set this yourself.
4. Click **Apply**. Render provisions the Postgres database, then runs the build command:
   ```
   pip install -r requirements.txt
   python manage.py collectstatic --noinput
   python manage.py migrate
   python manage.py create_default_superuser
   ```
   then starts the app with `gunicorn ssbikez.wsgi`.
5. Once the deploy finishes, visit `https://<your-service-name>.onrender.com/` and log in with
   the `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` you set in step 3 (username is
   `admin`).
6. **First thing to do after logging in**: go to `Admin → Roles` and `Admin → Users` and create
   real accounts for real staff, with the correct role for each person (see section 5). Don't
   hand out the `admin` superuser login for daily use.

### Redeploying after future code changes

Render auto-deploys on every push to the branch it's connected to (`main`, by default), as long
as the GitHub Actions CI workflow (section 8) has already told you the change is safe. There is
no separate manual deploy step needed for ordinary code changes — Render picks up the push,
reruns the build command above (including `migrate`, so new migrations apply automatically),
and restarts the service.

### If you need a different hosting provider instead of Render

Nothing in this codebase is Render-specific except `render.yaml` itself. The app is a standard
Django + Gunicorn + WhiteNoise + `dj-database-url` stack — it runs identically on Railway,
Fly.io, a plain VPS, etc. You'd need to translate the env vars in section 4 into that platform's
own configuration format and run the same 3 build-command steps (`collectstatic`, `migrate`,
`create_default_superuser`) yourself.

---

## 4. Environment variables — complete reference

| Variable | Required? | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes in production** | Django's cryptographic signing key. Auto-generated by Render; if hosting elsewhere, generate a long random string yourself and never reuse the repo's dev fallback. |
| `DEBUG` | Yes | `True` locally (default), `False` in production. With `DEBUG=False`, the app refuses to start unless `DJANGO_SECRET_KEY` and a real `ALLOWED_HOSTS` are also set — this is an intentional safety guard against the most common Django misconfiguration. |
| `ALLOWED_HOSTS` | Yes in production | Comma-separated list of domains allowed to serve this app, e.g. `ssbikez-erp.onrender.com,localhost`. |
| `CSRF_TRUSTED_ORIGINS` | Yes in production | Comma-separated full origins (with `https://`) allowed to submit forms, e.g. `https://ssbikez-erp.onrender.com`. |
| `DATABASE_URL` | No (falls back to SQLite) | A `postgres://user:pass@host:port/dbname` connection string. Render sets this automatically from the linked database. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | Yes in production | SMTP server details. Defaults are pre-filled for Gmail (`smtp.gmail.com`, `587`, `True`). |
| `EMAIL_HOST_USER` | **Yes — login is broken without this** | The sending email address. |
| `EMAIL_HOST_PASSWORD` | **Yes — login is broken without this** | For Gmail: **not your normal password.** Enable 2-Step Verification on the Google account, then generate a 16-character App Password at `myaccount.google.com/apppasswords` and use that. |
| `DEFAULT_FROM_EMAIL` | Yes in production | The "From" address shown on OTP/password-reset emails, e.g. `SSBikez ERP <you@gmail.com>`. |
| `DJANGO_SUPERUSER_USERNAME` | No (defaults to `admin`) | Username for the auto-created first superuser. |
| `DJANGO_SUPERUSER_EMAIL` | Yes in production | Email for the first superuser — must be real and reachable, since login requires OTP. |
| `DJANGO_SUPERUSER_PASSWORD` | Recommended | If unset, `create_default_superuser` generates a random password and prints it once to the deploy log — copy it immediately. Only ever takes effect if no superuser already exists; running it again later is always a safe no-op. |

---

## 5. User roles & permissions

Access control has two independent layers, both already built and tested:

1. **Namespace access** (which of the 11 modules a role can open at all) — configured in code
   (`accounts/permissions.py`), not editable from the UI. The matrix:

   | Role | Modules it can access |
   |---|---|
   | Managing Director | Everything (wildcard) |
   | Sales Manager | Sales, Customers, Customer Vehicles, Billing, RTO, VAS, Accounts, Used Vehicles |
   | Sales Executive | Sales, Customers, Customer Vehicles, Accounts, Used Vehicles |
   | Cashier | Billing, RTO, Customers, Sales, VAS, Accounts, Used Vehicles |
   | Accounts | Billing, RTO, Accounts |
   | Spares | Spares, Masters, Accounts |
   | CRE Telecaller / CRE | Service, Customer Vehicles, Accounts, Used Vehicles |
   | Supervisor | Service, Accounts, Used Vehicles |
   | Floor Supervisor | Service, Spares, Accounts, Used Vehicles |
   | Service Advisor | Service, Spares, Customer Vehicles, Accounts, Used Vehicles |
   | Service Billing | Service, Billing, Spares, Accounts, Used Vehicles |
   | Service Manager | Service, Spares, Customer Vehicles, Accounts, Used Vehicles |

   A role not in this table (or a user with no role assigned) can only reach the login/logout/
   profile/dashboard/search pages — everything else 403s. **If you create a new role name that
   isn't in this list, it will have almost no access anywhere** — add it to `ROLE_PERMISSIONS`
   in `accounts/permissions.py` and redeploy.

2. **Create/View/Edit/Delete matrix per module**, editable live from **Admin → Module Access**
   without a code change or redeploy — narrows what a role can do *within* a module it already
   has namespace access to (e.g. a role can be allowed to view Spares but not create/edit there).

3. **Record-level ownership**: on documents with a personal owner (Sales Orders, Job Cards,
   Sales Enquiries, etc.), only the record's own creator/assigned staff member — or a
   "manager" role (Managing Director, Sales Manager, Floor Supervisor, Service Manager,
   Supervisor) — can submit, cancel, or otherwise mutate it. Everyone with namespace access can
   still *view* department records; only *changing* someone else's record requires manager
   standing. This is enforced on every submit/cancel/edit/delete view, not just the obvious
   ones — including secondary "quick action" buttons that touch the same underlying record.

### Setting up your staff

Go to **Admin → Roles** to see/create role names (must match the table above to get useful
access), then **Admin → Users** to create one login per staff member, assigning the correct
role and branch. Every account requires a working, reachable email address — that's how they
receive their login OTP code.

---

## 6. Module-by-module workflow guide

### 6.1 Sales — new-vehicle sales chain

The core flow: **Enquiry → Appointment → Feedback → Sales Order → Delivery → Invoice**.

- **Sales Enquiry**: log a walk-in/phone lead, including a full trade-in pre-assessment section
  if the customer says they have a vehicle to exchange.
- **Appointment**: schedule a test ride or follow-up visit against an enquiry.
- **Sales Order**: the core order document — vehicle, customer, pricing, fittings, helmet,
  exchange-vehicle summary, advance payment. Has its own **Fittings**, **Items**, and
  **Advance Payment** sub-tables. Submitting locks the order; only the assigned sales
  executive (or a manager) can submit/cancel it afterward.
- **Vehicle Allotment**: a downstream fulfillment step after a submitted order — reserves the
  physical chassis for this customer.
- **Delivery**: the handover checklist (accessories fitted, fuel, documents handed over),
  approval gates (Manager/Finance), and its own item/payment sub-tables. Submitting a Delivery
  automatically advances the parent Sales Order's status and creates the linked
  `CustomerVehicle` record that Service/RTO/VAS all depend on.
- **Invoice**: GST auto-calculated from Company Settings' tax rate. If the customer's **State**
  (set on their profile) differs from the company's own state, the full GST amount is charged as
  **IGST** (interstate); otherwise it's split CGST/SGST as usual (intrastate) — a customer with no
  state set falls back to the CGST/SGST split. Gated behind an MD-approval step before it can be
  submitted.
- **Exchange Vehicle / Dealer resale**: if a customer trades in a vehicle, `ExchangeVehicle`
  captures its details. If that traded-in vehicle is then resold wholesale to another dealer,
  the **Dealers** sub-module (`Dealer`, `Exchange Vehicle Dealer`, `Exchange Dealer Payment`,
  `Dealer RC Hand Over`) tracks that separately, including flipping the vehicle's stock status
  to Sold once the wholesale transfer is submitted.
- **Sales Targets / Leaderboard**: set per-executive revenue/conversion targets and see live
  standings.

### 6.2 Used Vehicles — the parallel pre-owned bike pipeline

Structurally mirrors the new-vehicle flow, but for pre-owned stock:

- **Purchase**: a full 3-stage cycle — **Purchase Order → Purchase Receipt → Purchase
  Invoice**. Submitting the *Invoice* (not the earlier stages) is what actually creates
  available stock (a `UsedVehicleRegisterNo` row) for each chassis/registration number on the
  invoice. A simpler "own purchase" path (trade-in bought directly from a walk-in customer, no
  PO/Receipt) is also supported and skips straight to a standalone Invoice.
- **Sale → Delivery → Invoice**: same shape as the new-vehicle chain, its own docstatus
  lifecycle, its own GST handling.
- **Job Card service pipeline**: used bikes get serviced too — Bay In → Outwork (if needed) →
  Final Inspection → Labor Charge → Service Invoice. No "Water Wash" stage on this side (the
  reference system doesn't have one for used bikes).
- **Insurance Update**: track purchasing/renewing insurance on a used-stock unit that currently
  has none or expired cover.
- **RC Hand Over / RC Book Issue**: both follow the same real Draft → Submitted → Cancelled →
  Amended lifecycle as every other document in this system — create as a Draft, click Submit to
  lock it in with a proper audit trail (who/when), Cancel and Amend if a correction is needed
  later, rather than just flipping a status flag with no history.
- **Master Settings**: a batch intake screen — generate multiple chassis/registration rows at
  once instead of one at a time; submitting creates the real stock rows, skipping (not
  crashing on) any chassis number that already exists.

### 6.3 Service — the workshop pipeline

Every Job Card advances through: **Pending → Water Wash → In Bay → In Progress → Outwork (if
needed) → Final Inspection → Ready → Invoiced**. Each stage is its own real document with its
own Draft/Submit/Cancel lifecycle (Water Wash Done, Bay In, Bay Out, Outwork Entry Issue/Return,
Final Inspection, Labor Charges), all linked back to one parent Job Card — the Job Card's own
detail page has a "Workshop Stage Documents" card cross-linking every stage instance for that
vehicle. Spares consumed during service are recorded via **Spares Issue Alteration** (in the
`spares` app, linked back to the Job Card), and the final **Service Invoice** rolls up labor +
spares + outwork costs with GST.

Also in this module: Service Enquiries/Appointments (the service-side equivalent of Sales
Enquiries), Warranty Claims, Insurance Claims/Estimations, Reminders (follow-ups for upcoming
services), and a CSV bulk-import for enquiries.

### 6.4 Spares — parts inventory

- **Item catalog**: part number, HSN code, MRP, selling rate, reorder level.
- **Purchase**: Request Supplier Quote → Supplier Quote → Purchase Order → Purchase Invoice
  (submitting a Purchase Invoice posts real stock). A **Spares Purchase Estimation Master**
  can precede a PO for cost planning.
- **Stock Reconciliation**: Stock Transfer (move quantity between rack/bin/warehouse locations)
  and Stock Count Update (correct system stock to a physically-counted value).
- **Counter Sale / Counter Sale Return**: walk-in retail spares sales, independent of any
  vehicle service.
- **Issue Alteration**: spares issued against a Job Card (new or used vehicle), with its own
  return-tracking sibling document.
- **MRP Price Revision**: bulk price-revision batches that write back to the item catalog on
  submit.
- **Service Spares Warranty**: supplier warranty-claim tracking for defective parts.

### 6.5 RTO — vehicle registration & number plates

Per new-vehicle sales order: RC Hand Over checklist → Form 20 Creation → Registration No
Creation (both snapshot their result back onto a single rollup `RTO Registration` record for
that order) → RTO Payment / Regpay Creation (both are **batch documents** — one payment run
can cover several vehicles at once, so each has a header + a list of per-vehicle rows) →
Number Plate 3-stage flow (Order Entry → Receipt Entry → Issue, the last of which can deduct a
physical frame from spares stock) → RC Book Creation → RC Book Issue.

### 6.6 VAS — AMC / RSA / Protection Plus

Each of the three plan types (AMC, RSA, Warranty/"Protection Plus") has its own type master
(pricing, validity, HSN code) and its own sale-side package document, but shares one stock
ledger/movement system and one supplier-invoice document across all three. Two safety
mechanisms run automatically on submit: (1) **stock-safety** — a package cannot be submitted if
its plan type currently has zero stock; (2) **auto-invoice** — submitting a package with a
linked Sales Order automatically creates a matching Draft billing Invoice from the package's
own price fields (still subject to the normal MD-approval gate before it can itself be
submitted).

### 6.7 Billing

Invoices (both new- and used-vehicle), Payments (cash/UPI/finance/cheque with balance
tracking), Finance Loans/EMI tracking, Insurance Policies, Journal Entries (real double-entry
accounting with debit/credit line validation), and the Daily Collection / General Ledger
reports. PDF generation (tax invoices, service invoices, payment receipts) uses `xhtml2pdf` —
see the troubleshooting section if PDFs come back as plain HTML instead.

**General Ledger auto-posting**: submitting an Invoice, or recording a completed Payment,
automatically posts a balanced Journal Entry to the General Ledger — you don't need to
hand-enter these as manual Journal Entries too. Cancelling an Invoice now automatically posts a
reversing Journal Entry for its already-posted ledger entry (swapped debit/credit, same
accounts), so no manual correcting entry is needed for that case. A Payment marked Completed via
the bulk **Payment Reconciliation** screen now also auto-posts its Journal Entry the same way an
individually-recorded Payment does — this was a gap until the 2026-07-20 parity audit found and
closed it (see `docs/audit/DEVIATIONS.md`); no manual correcting entry is needed for this case
either anymore.

### 6.8 Masters — shared reference data

Suppliers, Warehouses, Racks/Bins, Categories, and the pricing masters (Model and Price,
Customer Price, Dealer Price List). Also owns the **Order Form Series** numbering-series
generator — a Settings screen where you configure a prefix/digit-count/batch-size and click
Generate to mint a pool of pre-numbered order-form slots that other documents can optionally
reference.

### 6.9 Accounts — admin & system

User/Role/Branch management, Module Access permission matrix, Company Settings (name, GST rate,
address), global search (searches across customers, vehicles, orders, job cards, spare parts
simultaneously), the audit log (every create/update/delete/status-change, with user/IP/
timestamp), fuel expense tracking, and the reporting dashboards (Sales/Service/Spares reports).

---

## 7. Troubleshooting — every known error and its fix

### "Could not send the OTP email" / can't log in at all
**Cause**: `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` are unset or wrong. Login is deliberately
fail-closed — the system will never let anyone in without proving they received a real emailed
code, so a broken email configuration means *nobody* can log in, including the superuser.
**Fix**: set the 4 email variables correctly (section 4). For Gmail specifically, you must use
an **App Password**, not the account's normal login password — a normal password will
authenticate to Gmail's SMTP server but silently fail in a way that looks identical to a wrong
password.

### "Too many failed login attempts. Please try again in a few minutes."
**Not a bug.** After 5 wrong password attempts, the account locks for 15 minutes (protects
against brute-forcing). Wait, or a manager can look up the account and confirm it'll unlock
itself once the window passes — no manual reset is needed, it clears automatically.

### 403 "Access Denied" on a page a user expects to see
Check, in order: (1) does their **Role** include that namespace in the table in section 5?
(2) does **Admin → Module Access** have an explicit Deny override for their role+module? (3) if
it's a specific record (not a whole page), are they the record's own creator/assigned staff, or
a manager-tier role? Regular staff genuinely cannot edit/submit/cancel a colleague's individual
sales order, job card, etc. — that's enforced by design, not a bug.

### PDF download comes back as an `.html` file instead of a real PDF
Means the `xhtml2pdf`/`openpyxl` PDF toolchain isn't installed in that environment (this exact
issue happened once during development — the app has a deliberate fallback that serves readable
HTML instead of crashing, but it means the toolchain needs attention). Fix: confirm
`requirements.txt` installed cleanly (`pip install -r requirements.txt` with no errors) — Render
always does this correctly since it's a fresh install every deploy; this is only a risk in a
manually-managed local/VPS environment where a previous partial install may be stale.

### "Migrations pending" / model changes not showing up
Run `python manage.py migrate`. On Render this happens automatically on every deploy (it's in
the build command); locally, run it yourself after pulling new code.

### A new page/template change isn't showing up after editing it locally
If you're running with `DEBUG=False` locally (not the normal case, but possible if you copied a
production `.env`), Django caches templates — restart the dev server after any template edit.
With `DEBUG=True` (the default), this isn't an issue.

### CSV bulk-import (Spares, Service Enquiries) rejects a file
Both bulk-import screens cap uploads at 5MB and automatically neutralize any cell starting with
`=`, `+`, `-`, or `@` (prefixes it with a quote) to prevent a spreadsheet-formula-injection
attack if the file is later reopened in Excel — if a legitimate value looks like it's been
mangled with a leading `'`, that's this protection working as intended, not a bug.

### A newly-created role has almost no access anywhere
Role names are matched literally against the table in section 5 — a typo'd or new role name
that isn't in that list gets zero module access by default. Add it to `ROLE_PERMISSIONS` in
`accounts/permissions.py` (a plain Python dict) and redeploy, or reuse one of the existing role
names exactly as spelled.

### "UNIQUE constraint failed" on a document number (order/invoice/job-card number, etc.)
Should not happen under normal use — every auto-numbered field in this system uses a
database-locked, race-safe numbering scheme specifically to prevent this. If it ever does occur,
it indicates two requests tried to create the same document number at the exact same instant;
simply retrying the create is safe and will succeed with the next number.

---

## 8. Testing & CI

A real automated test suite (138 tests) covers the highest-risk parts of all 11 apps —
RBAC/permission enforcement, ownership checks, auto-numbering uniqueness, financial-validation
rules, and the specific bugs found and fixed during development. Run it any time with:

```bash
python manage.py test
```

Every push and pull request also runs this automatically via GitHub Actions
(`.github/workflows/tests.yml`) — it runs `manage.py check`, a check for missing migrations, and
the full test suite. **Check the Actions tab on GitHub before trusting a change is safe to
deploy** — a red X there means something regressed.

This is real, meaningful coverage of the riskiest mechanisms, not exhaustive coverage of every
line of the app — treat it as a strong regression floor, not a guarantee that every possible
workflow has been automatically verified.

---

## 9. Known limitations and accepted risks

Recorded here plainly so nothing is a surprise later:

- **Test coverage is targeted, not exhaustive.** All 11 apps have real tests, but this is a
  strong regression floor on the riskiest mechanisms — not a guarantee every workflow is
  automatically verified (see section 8).
- **Pagination**: most list pages load their full result set at once rather than paginating.
  Not a problem at today's data volumes; worth revisiting if any single list grows into the
  thousands of rows.
- **Accessibility**: the large majority of WCAG issues found during an accessibility pass were
  fixed; one remaining item (table-row-stripe color contrast against link-blue text) is a
  deliberate, not-yet-made design trade-off, not an oversight.
- **A historical credential string** briefly existed in this repository's public git history
  before being rotated to a new, unrelated value — the old value is permanently dead and grants
  no access anywhere, but the string itself may still be visible if someone browses old commits.
  This was a considered decision, not an unresolved bug.
- **No load/performance testing has been done.** The stack (Django + Gunicorn + Postgres) scales
  in the conventional ways (more Gunicorn workers, a bigger Postgres plan) if usage grows, but
  that hasn't been benchmarked against this specific app's query patterns.

---

## 10. Day-to-day maintenance

- **Backups**: Render's managed Postgres includes automatic daily backups on paid plans — confirm
  this is enabled and that you know how to trigger a restore before you need one.
- **Monitoring errors in production**: application errors are streamed to stdout (visible in
  Render's log viewer) even with `DEBUG=False`, specifically so production issues are diagnosable
  without needing to enable debug mode on a live client-facing system.
- **Adding a new staff role**: create the `Role` row in Admin, add a matching entry to
  `ROLE_PERMISSIONS` in `accounts/permissions.py`, redeploy.
- **Rotating the admin password**: log in as an existing superuser, go to that user's account
  in Admin → Users, and change the password there — no code change needed.
- **Keeping dependencies current**: `requirements.txt` pins exact versions. Periodically check
  for new Django/Pillow/lxml security releases (these three have had real CVEs patched during
  this project) and update deliberately, running the full test suite before deploying an update.
