# SSBikez ERP — Setup Guide

## Mac / Linux

```
git clone https://github.com/Satyawiwijj/ssbikez-erp.git
cd ssbikez-erp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000

Note: Uses SQLite by default. No PostgreSQL needed for local testing.

## Windows

```
git clone https://github.com/Satyawiwijj/ssbikez-erp.git
cd ssbikez-erp
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Python version
Use Python 3.11 or 3.12. Do NOT use Python 3.14.

## Default login
After createsuperuser, use the credentials you set.
Or run: python manage.py create_default_superuser
Default: username=admin password=SSBikez@2026
