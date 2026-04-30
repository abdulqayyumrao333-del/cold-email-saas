# MailForge — Hyper-Personalized Cold Email Generator
## Complete Setup Guide (Step-by-Step, Simple English)

---

## WHAT THIS APP DOES

MailForge is a SaaS web app where users:
1. Sign up / log in
2. Paste a company URL + their target role + their service
3. The app scrapes the website, finds real problems, and uses AI to write a personalized cold email
4. Free users get 5 emails. Paid users ($29 one-time via Stripe) get unlimited.

---

## STEP 1 — INSTALL PYTHON

Make sure you have Python 3.9 or newer installed.

Check by typing this in your terminal:
```
python --version
```

If it shows Python 3.x.x, you're good. If not, download it from: https://www.python.org/downloads/

---

## STEP 2 — DOWNLOAD THE PROJECT

Put all project files in one folder. Your folder should look like this:

```
cold-email-saas/
├── app.py
├── database.py
├── init_database.py
├── requirements.txt
├── .env.example
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    └── upgrade.html
```

---

## STEP 3 — CREATE A VIRTUAL ENVIRONMENT

A virtual environment keeps all packages separate from your system Python.

Open your terminal, go to the project folder, and run:

**On Mac/Linux:**
```
cd cold-email-saas
python -m venv venv
source venv/bin/activate
```

**On Windows:**
```
cd cold-email-saas
python -m venv venv
venv\Scripts\activate
```

You'll see `(venv)` at the start of your terminal line. That means it's working.

---

## STEP 4 — INSTALL ALL PACKAGES

With your virtual environment active, run:
```
pip install -r requirements.txt
```

This installs Flask, Stripe, Groq, BeautifulSoup, and everything else.
Wait for it to finish (takes about 1-2 minutes).

---

## STEP 5 — GET YOUR GROQ API KEY (FREE)

Groq is the AI that writes the emails. It's FREE to use.

1. Go to: https://console.groq.com
2. Click "Sign Up" and create an account
3. After logging in, click "API Keys" in the left menu
4. Click "Create API Key"
5. Copy the key — it starts with `gsk_`

Keep this key safe. You'll need it in Step 7.

---

## STEP 6 — SET UP STRIPE (FOR PAYMENTS)

Stripe handles the $29 payment. We use TEST MODE (no real money).

### 6A — Create a Stripe Account
1. Go to: https://stripe.com
2. Click "Start now" and sign up
3. You don't need to verify your identity for test mode

### 6B — Get Your Test Secret Key
1. In Stripe dashboard, click "Developers" at the top right
2. Click "API keys"
3. Find "Secret key" and click "Reveal test key"
4. Copy it — it starts with `sk_test_`

### 6C — Create a Product and Price
1. In Stripe dashboard, click "Products" in the left menu
2. Click "+ Add product"
3. Name: "MailForge Pro"
4. Price: $29.00, one-time payment
5. Click "Save product"
6. On the product page, you'll see a "Price ID" — it starts with `price_`
7. Copy that Price ID

---

## STEP 7 — CREATE YOUR .env FILE

In the project folder, create a file called `.env` (no extension, just `.env`).

You can copy from `.env.example`:

**On Mac/Linux:**
```
cp .env.example .env
```

**On Windows:**
```
copy .env.example .env
```

Now open `.env` in any text editor (Notepad, VS Code, etc.) and fill in your values:

```
SECRET_KEY=any-long-random-string-like-abc123xyz987

GROQ_API_KEY=gsk_your_actual_groq_key_here

STRIPE_SECRET_KEY=sk_test_your_actual_stripe_key_here

STRIPE_PRICE_ID=price_your_actual_price_id_here

STRIPE_WEBHOOK_SECRET=whsec_leave_this_for_now
```

**IMPORTANT:**
- Replace each value with your actual keys
- Don't use quotes around the values
- Don't share this file with anyone

---

## STEP 8 — CREATE THE DATABASE

Run this command once to create the SQLite database:

```
python init_database.py
```

You should see:
```
✅ Database initialized successfully.
✅ Database created successfully at instance/saas.db
```

This creates a file called `saas.db` inside an `instance/` folder. That's your database!

---

## STEP 9 — RUN THE APP

```
python app.py
```

You'll see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

## STEP 10 — OPEN IN BROWSER

Go to: http://localhost:5000

You'll see the MailForge landing page!

---

## HOW TO USE THE APP

1. Click "Get Started Free"
2. Create an account with any email + password
3. You'll land on the Dashboard
4. Fill in:
   - Company URL (e.g., https://stripe.com)
   - Target Role (e.g., CEO)
   - Your Service (e.g., Facebook Ads)
5. Click "Generate Cold Email"
6. Wait ~5-10 seconds while we scrape + generate
7. Your personalized email appears on the right!

---

## HOW TO TEST STRIPE PAYMENTS

When you click "Upgrade Now", you'll be taken to Stripe's test checkout.

Use these fake test card details:
- **Card number:** 4242 4242 4242 4242
- **Expiry:** Any future date (e.g., 12/28)
- **CVC:** Any 3 digits (e.g., 123)
- **Name/ZIP:** Anything

After payment, you'll be redirected back and upgraded to Pro automatically.

---

## TROUBLESHOOTING

### "ModuleNotFoundError"
→ Run `pip install -r requirements.txt` again with venv activated

### "Website could not be accessed"
→ Some websites block scraping. Try a different URL like https://basecamp.com

### "AI generation failed"
→ Check your GROQ_API_KEY in .env — make sure it's correct

### "Payment error"
→ Check your STRIPE_SECRET_KEY and STRIPE_PRICE_ID in .env

### Database errors
→ Delete the `instance/` folder and run `python init_database.py` again

---

## FILE EXPLAINED

| File | What it does |
|------|-------------|
| `app.py` | Main Flask app — all routes and logic |
| `database.py` | Database models (User table) |
| `init_database.py` | Creates the database (run once) |
| `requirements.txt` | All Python packages needed |
| `.env` | Your secret keys (never share this) |
| `templates/` | HTML pages for the UI |

---

## ADMIN: MANUALLY UPGRADE A USER

If you want to manually upgrade a user to paid (e.g., for testing), open Python:

```
python
>>> from app import app
>>> from database import db, User
>>> with app.app_context():
...     user = User.query.filter_by(email='test@example.com').first()
...     user.plan = 'paid'
...     db.session.commit()
...     print('Done!')
```

---

## STOP THE SERVER

Press `Ctrl + C` in the terminal to stop the Flask server.

---

That's it! You have a fully working SaaS product. 🎉