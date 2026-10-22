# Canteen Inventory Management

A Django app for tracking canteen stock: items, categories, stock in/out transactions, and a dashboard.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the dashboard and http://127.0.0.1:8000/admin/ for the Django admin.

## Deploy on Vercel

Set these environment variables in the Vercel project settings:

- `SECRET_KEY` – a long random string
- `DATABASE_URL` – a hosted Postgres URL (Vercel can't keep SQLite data)
