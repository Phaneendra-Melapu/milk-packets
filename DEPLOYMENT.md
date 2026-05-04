# Milk Counter Deployment

This app is ready for a cloud deployment.

## Recommended Free Setup

- Code hosting: GitHub
- Web app hosting: Render
- Database: Supabase Postgres

GitHub alone is not enough because this app needs a Python backend and a database.

## Step 1: Create Supabase Database

1. Go to Supabase and create a new project.
2. Open Project Settings.
3. Open Database.
4. Copy the connection string.
5. Replace the password placeholder with your real database password.

The app creates its own tables automatically when it starts.

## Step 2: Upload Code To GitHub

Create a new GitHub repository and upload this folder.

Important files for deployment:

```text
render.yaml
backend/requirements.txt
backend/run_server.py
backend/app/main.py
backend/app/database.py
frontend/index.html
frontend/app.js
frontend/styles.css
```

## Step 3: Deploy On Render

1. Go to Render.
2. Create a new Web Service.
3. Connect your GitHub repository.
4. Use these settings:

```text
Build Command:
pip install -r backend/requirements.txt

Start Command:
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. Add this environment variable:

```text
DATABASE_URL=<your Supabase connection string>
```

6. Deploy.

## Step 4: Open The App

Render will give you a public URL like:

```text
https://milk-counter.onrender.com
```

Open that URL from laptop or mobile.

## Notes

- Packet images are stored in the database, so you only upload each one once.
- Daily packet counts are stored in the database.
- Free hosting may sleep when unused, so the first open of the day can be slow.
- Keep your `DATABASE_URL` private. Do not paste it into public code.
