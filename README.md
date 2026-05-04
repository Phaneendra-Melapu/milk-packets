# Milk Counter

A daily milk packet tracker for Gold, Blue, and Green packets.

## Features

- Tap packet cards to add daily milk purchases.
- Prices are built in:
  - Gold: Rs 38
  - Blue: Rs 30
  - Green: Rs 33
- Shows daily packet count, total, average price, cart, and recent history.
- Upload packet pictures once. The app saves them and locks the upload control.
- Works on laptop and mobile when hosted.
- Uses SQLite locally and can use PostgreSQL in the cloud with `DATABASE_URL`.

## Run Locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_server.py
```

Open:

```text
http://127.0.0.1:8000
```

For mobile on the same Wi-Fi, open:

```text
http://<your-laptop-ip>:8000
```

## Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md).

Recommended beginner setup:

```text
GitHub + Render + Supabase Postgres
```

## Tests

Keep the backend running, then:

```powershell
cd tests
npm install
npm test
```
