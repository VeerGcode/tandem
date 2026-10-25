# Tandem App

Verified service hours. Hosts post events, volunteers scan a QR code, and hosts approve the hours.

## Run it

```
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
flask run --debug
```

Then open http://127.0.0.1:5000

## Layout

| File | What it does |
|---|---|
| `app.py` | Creates the app and registers the route files |
| `config.py` | Settings (secret key, database location) |
| `extensions.py` | Shared `db` and `login_manager` objects |
| `models.py` | Database tables: User, Opportunity, Signup, HourRequest |
| `routes/auth.py` | Register, log in, log out (done) |
| `routes/opportunities.py` | Browse, post, QR image (done), sign up (TODO) |
| `routes/hours.py` | QR scan, host dashboard, approve and deny (TODO) |
| `templates/` | HTML pages (Bootstrap) |

## How the hours flow works

1. Host posts an event. The event gets a random `qr_token`.
2. Host opens the event page and shows the QR code (it links to `/scan/<token>`).
3. Volunteer scans it with their phone camera, logs in if needed, and a **pending** HourRequest is created.
4. Volunteer scans again when leaving, which sets the check-out time.
5. Host sees the request on their dashboard and approves (sets hours) or denies.
6. Approved hours count toward the volunteer's total on My hours.

## Build order

1. Sign-up for events (`routes/opportunities.py`)
2. QR scan logic (`routes/hours.py`, `scan`)
3. Approve and deny (`routes/hours.py`)
4. Safety: parent consent for minors, host verification
5. CSV / PDF export of hours
6. Styling, then deploy
