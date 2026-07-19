# E2E Tests

Real-browser tests driven with Playwright against a live copy of the app
(`django.contrib.staticfiles.testing.StaticLiveServerTestCase`), the same
"drive the actual UI" idea as a Next.js + Playwright setup, adapted to how
this project already runs its other 138 tests: `python manage.py test`, no
pytest, no npm/package.json.

## One-time setup

```
pip install -r requirements-e2e.txt
python -m playwright install chromium
```

## Running

```
python manage.py test e2e              # whole suite
python manage.py test e2e.test_sales_order_flow   # one flow
```

## Structure

- `base.py` — `PlaywrightTestCase`: launches Chromium once per test class,
  a fresh browser context per test method, and a `login_as(user)` helper
  that injects a real Django session cookie (bypassing the OTP screen —
  2FA itself is covered separately by `accounts/tests.py`).
- `fixtures.py` — minimal ORM-based fixture builders. `StaticLiveServerTestCase`
  runs against Django's *test* database (fresh/empty per run), not the dev
  database, so every flow builds exactly the data chain it needs.
- `test_*.py` — one file per user flow. Each seeds just enough state via the
  ORM, then drives the parts that matter through the real browser (clicking
  Submit/Cancel, reading rendered badges/GST amounts) — this is what catches
  wiring bugs (dead button, missing template block, JS console error) that a
  `Client()`-based Django test can't see.

## Adding a new flow

1. Add any new fixture builders to `fixtures.py`.
2. Subclass `PlaywrightTestCase`, call `self.login_as(user)` in `setUp`.
3. Use `self.goto(path)` to navigate and `self.page` (a Playwright `Page`)
   to interact — prefer `get_by_role`/`get_by_label`/`get_by_text` locators
   over CSS selectors (this app's forms already carry real `aria-label`s via
   `AccessibleFormMixin`, so accessible-name locators work reliably).

## Known gotcha

Playwright's sync API runs its own event loop, which makes Django's
async-safety check misfire on ordinary synchronous ORM calls in the test
thread. `base.py` sets `DJANGO_ALLOW_ASYNC_UNSAFE=true` at import time to
work around this — the same escape hatch Django documents for
Jupyter/IPython-style embedded event loops. This is safe here: each thread
still has its own DB connection, nothing is actually running concurrently.
