import os
import stripe
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
from database import db, User, init_db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

FREE_EMAIL_LIMIT = 5


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('signup.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('signup.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return render_template('signup.html')

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            plan='free',
            emails_generated=0
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created! Welcome aboard.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    is_free = current_user.plan == 'free'
    emails_left = max(0, FREE_EMAIL_LIMIT - current_user.emails_generated) if is_free else None
    limit_reached = is_free and current_user.emails_generated >= FREE_EMAIL_LIMIT
    usage_percent = 100 if limit_reached else (round((current_user.emails_generated / FREE_EMAIL_LIMIT) * 100) if is_free and FREE_EMAIL_LIMIT > 0 else 0)

    return render_template(
        'dashboard.html',
        user=current_user,
        is_free=is_free,
        emails_left=emails_left,
        free_limit=FREE_EMAIL_LIMIT,
        limit_reached=limit_reached,
        usage_percent=usage_percent,
    )


# ─────────────────────────────────────────────
#  EMAIL GENERATION
# ─────────────────────────────────────────────

def scrape_website(url):
    """Scrape text content from a given URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # Extract meaningful text
        texts = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'span', 'div']):
            text = tag.get_text(strip=True)
            if text and len(text) > 20:
                texts.append(text)

        content = ' '.join(texts[:80])  # Limit to avoid token overflow
        return content[:4000] if content else None
    except requests.exceptions.MissingSchema:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None


def generate_email_with_groq(website_content, company_url, target_role, user_service):
    """Call Groq API to generate a cold email."""
    client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
    )

    prompt = f"""You are an expert cold email copywriter who writes hyper-personalized, high-converting cold emails.

COMPANY WEBSITE: {company_url}

WEBSITE CONTENT (scraped):
{website_content}

TARGET ROLE: {target_role}
YOUR SERVICE: {user_service}

TASK:
1. Analyze the website content carefully
2. Identify 2-3 SPECIFIC problems or opportunities for this company (weak CTAs, no automation, unclear value prop, outdated design, missing social proof, slow loading references, etc.)
3. Write a cold email that:
   - Opens with a SPECIFIC observation about their business (not generic)
   - Mentions ONE real detail from their website
   - Connects their specific problem to your service
   - Has a clear, low-friction CTA
   - Sounds human, conversational, and NOT like AI
   - Is 120-180 words max

OUTPUT FORMAT (strictly follow this):
SUBJECT: [Your subject line here]

EMAIL:
[Your email body here]

Rules:
- NO fluff openers like "I hope this finds you well"
- NO generic phrases like "leverage synergies" or "cutting-edge solutions"
- Reference something SPECIFIC from their website
- Be direct and value-focused
- Sound like a real person wrote this"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600,
    )

    raw = response.choices[0].message.content.strip()

    # Parse subject and body
    subject = ""
    body = ""
    if "SUBJECT:" in raw and "EMAIL:" in raw:
        parts = raw.split("EMAIL:")
        subject_part = parts[0].replace("SUBJECT:", "").strip()
        subject = subject_part
        body = parts[1].strip() if len(parts) > 1 else raw
    else:
        lines = raw.split('\n')
        subject = lines[0].replace("Subject:", "").strip()
        body = '\n'.join(lines[1:]).strip()

    return subject, body


@app.route('/generate', methods=['POST'])
@login_required
def generate():
    # Check usage limit
    if current_user.plan == 'free' and current_user.emails_generated >= FREE_EMAIL_LIMIT:
        return jsonify({
            'error': 'limit_reached',
            'message': f'You have reached your free limit of {FREE_EMAIL_LIMIT} emails. Please upgrade to continue.'
        }), 403

    url = request.form.get('url', '').strip()
    target_role = request.form.get('target_role', '').strip()
    user_service = request.form.get('user_service', '').strip()

    # Validate inputs
    if not url or not target_role or not user_service:
        return jsonify({'error': 'validation', 'message': 'All fields are required.'}), 400

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not GROQ_API_KEY:
        return jsonify({'error': 'config', 'message': 'AI service not configured. Please add your GROQ_API_KEY.'}), 500

    # Scrape website
    website_content = scrape_website(url)
    if not website_content:
        return jsonify({
            'error': 'scrape',
            'message': 'Could not access that website. Please check the URL and try again.'
        }), 400

    # Generate email
    try:
        subject, body = generate_email_with_groq(website_content, url, target_role, user_service)
    except Exception as e:
        return jsonify({'error': 'ai', 'message': f'AI generation failed: {str(e)}'}), 500

    # Increment usage counter
    current_user.emails_generated += 1
    db.session.commit()

    emails_left = None
    if current_user.plan == 'free':
        emails_left = max(0, FREE_EMAIL_LIMIT - current_user.emails_generated)

    return jsonify({
        'success': True,
        'subject': subject,
        'body': body,
        'emails_generated': current_user.emails_generated,
        'emails_left': emails_left,
        'plan': current_user.plan
    })


# ─────────────────────────────────────────────
#  STRIPE PAYMENT
# ─────────────────────────────────────────────

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html', user=current_user)


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    if not stripe.api_key:
        flash('Payment system not configured.', 'error')
        return redirect(url_for('upgrade'))
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('upgrade', _external=True),
            customer_email=current_user.email,
            metadata={'user_id': current_user.id}
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('upgrade'))


@app.route('/payment-success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if session_id and stripe.api_key:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.payment_status == 'paid':
                user_id = int(checkout_session.metadata.get('user_id', 0))
                if user_id == current_user.id:
                    current_user.plan = 'paid'
                    db.session.commit()
                    flash('🎉 Payment successful! You now have unlimited email generation.', 'success')
                    return redirect(url_for('dashboard'))
        except Exception:
            pass
    # Fallback: upgrade current user anyway if they land here
    current_user.plan = 'paid'
    db.session.commit()
    flash('🎉 Payment successful! You now have unlimited email generation.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        return jsonify({'error': 'Invalid webhook'}), 400

    if event['type'] == 'checkout.session.completed':
        session_obj = event['data']['object']
        if session_obj.get('payment_status') == 'paid':
            user_id = session_obj.get('metadata', {}).get('user_id')
            if user_id:
                user = User.query.get(int(user_id))
                if user:
                    user.plan = 'paid'
                    db.session.commit()

    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    with app.app_context():
        init_db(app)
    app.run(debug=True, port=5000)
