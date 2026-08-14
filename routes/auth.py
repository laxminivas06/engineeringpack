import os
import json
import base64
import uuid
import urllib.request
import urllib.parse
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from services.auth_service import (
    get_or_create_google_user, complete_user_onboarding, complete_user_payment,
    submit_user_payment_proof, authenticate_admin, login_session, logout_session,
    get_current_user, login_required
)

auth_bp = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_google_redirect_uri():
    """Generates exact redirect URI matching Google Console configuration."""
    config_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
    if config_uri:
        return config_uri
    return f"{request.scheme}://{request.host}/auth/google/callback"


def parse_google_id_token(id_token: str) -> dict:
    """Decodes Google JWT ID token payload without external libraries."""
    try:
        parts = id_token.split('.')
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        remainder = len(payload_b64) % 4
        if remainder > 0:
            payload_b64 += '=' * (4 - remainder)
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Error parsing Google ID Token: {e}")
        return {}


def exchange_google_code_for_user_info(code: str, redirect_uri: str) -> dict:
    """Exchanges Google OAuth authorization code for user info via Google token API."""
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET', '')
    token_url = 'https://oauth2.googleapis.com/token'
    data = urllib.parse.urlencode({
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }).encode('utf-8')

    try:
        req = urllib.request.Request(token_url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            id_token = res_body.get('id_token')
            if id_token:
                return parse_google_id_token(id_token)
            
            access_token = res_body.get('access_token')
            if access_token:
                userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
                ui_req = urllib.request.Request(userinfo_url, headers={'Authorization': f'Bearer {access_token}'})
                with urllib.request.urlopen(ui_req) as ui_res:
                    return json.loads(ui_res.read().decode('utf-8'))
    except Exception as e:
        print(f"Error exchanging Google authorization code: {e}")
    return {}


@auth_bp.route('/login', methods=['GET'])
def login():
    user = get_current_user()
    if user:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('role') == 'student':
            if user.get('enrollment_status') == 'Pending Onboarding':
                return redirect(url_for('auth.onboarding'))
            elif user.get('payment_status') == 'Unpaid':
                return redirect(url_for('auth.payment'))
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET'])
def register():
    return redirect(url_for('auth.login'))


@auth_bp.route('/auth/google/redirect', methods=['GET'])
def google_redirect():
    """Redirects user to official Google OAuth 2.0 consent screen."""
    client_id = (current_app.config.get('GOOGLE_CLIENT_ID') or '').strip()
    
    if not client_id or 'YOUR_GOOGLE_CLIENT_ID' in client_id.upper():
        flash(
            "Google OAuth Client ID is not configured yet. Please set your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the .env file. "
            "For local testing, you can use the Dev Quick Login below.",
            "warning"
        )
        return redirect(url_for('auth.login'))

    redirect_uri = get_google_redirect_uri()
    google_oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        "prompt=select_account"
    )
    return redirect(google_oauth_url)


@auth_bp.route('/auth/dev-login', methods=['POST'])
def dev_login():
    """Developer bypass login for local testing when Google OAuth credentials are not set."""
    email = request.form.get('email', '').strip().lower()

    if not email:
        flash("Please enter an email address for Dev Quick Sign-In.", "danger")
        return redirect(url_for('auth.login'))

    google_info = {
        'email': email,
        'name': email.split('@')[0].replace('.', ' ').replace('_', ' ').title(),
        'sub': f'dev_{uuid.uuid4().hex[:8]}'
    }

    success, msg, user_data, role = get_or_create_google_user(google_info)
    if success:
        login_session(user_data, role=role)
        flash(f"Signed in via Dev Quick Login as {email} ({role.upper()}).", "success")
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            if user_data.get('enrollment_status') == 'Pending Onboarding':
                return redirect(url_for('auth.onboarding'))
            elif user_data.get('payment_status') == 'Unpaid':
                return redirect(url_for('auth.payment'))
            return redirect(url_for('student.dashboard'))
    else:
        flash(msg, "danger")
        return redirect(url_for('auth.login'))



@auth_bp.route('/auth/google/callback', methods=['GET', 'POST'])
def google_callback():
    """Receives callback from real Google OAuth 2.0 authorization code OR GIS credential form."""
    google_info = {}

    # 1. Check GIS ID token credential in POST body
    credential = request.form.get('credential')
    if credential:
        google_info = parse_google_id_token(credential)

    # 2. Check OAuth authorization code in GET query string
    if not google_info.get('email'):
        code = request.args.get('code')
        if code:
            redirect_uri = get_google_redirect_uri()
            google_info = exchange_google_code_for_user_info(code, redirect_uri)

    email = google_info.get('email', '').strip().lower()
    if not email:
        flash("Google Authentication failed or was cancelled by user. Please try signing in again.", "danger")
        return redirect(url_for('auth.login'))

    # Authenticate via real Google info
    success, msg, user_data, role = get_or_create_google_user(google_info)
    if success:
        login_session(user_data, role=role)
        if role == 'admin':
            flash(f"Welcome Admin, {user_data.get('name') or user_data.get('full_name')}!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash(f"Signed in with Google as {user_data.get('email')}.", "success")
            if user_data.get('enrollment_status') == 'Pending Onboarding':
                return redirect(url_for('auth.onboarding'))
            elif user_data.get('payment_status') == 'Unpaid':
                return redirect(url_for('auth.payment'))
            return redirect(url_for('student.dashboard'))
    else:
        flash(msg, "danger")
        return redirect(url_for('auth.login'))


@auth_bp.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    if user.get('enrollment_status') != 'Pending Onboarding' and user.get('user_type'):
        if user.get('payment_status') == 'Unpaid':
            return redirect(url_for('auth.payment'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        user_type = request.form.get('user_type', '').strip()
        custom_user_type = request.form.get('custom_user_type', '').strip()
        branch = request.form.get('branch', '').strip()
        custom_branch = request.form.get('custom_branch', '').strip()
        academic_year = request.form.get('academic_year', '').strip()

        if not full_name:
            flash("Please enter your full name.", "danger")
            return render_template('auth/onboarding.html', user=user)

        if not phone or len(phone.replace(' ', '').replace('-', '').replace('+', '')) < 8:
            flash("Please enter a valid mobile phone number.", "danger")
            return render_template('auth/onboarding.html', user=user)

        if not user_type:
            flash("Please select your current role ('You Are').", "danger")
            return render_template('auth/onboarding.html', user=user)

        if not branch:
            flash("Please select or enter your branch/department.", "danger")
            return render_template('auth/onboarding.html', user=user)

        if not academic_year:
            flash("Please select your academic year.", "danger")
            return render_template('auth/onboarding.html', user=user)

        onboarding_data = {
            'full_name': full_name,
            'phone': phone,
            'user_type': user_type,
            'custom_user_type': custom_user_type,
            'branch': branch,
            'custom_branch': custom_branch,
            'academic_year': academic_year
        }

        success, updated_user = complete_user_onboarding(user['id'], onboarding_data)
        if success:
            session['name'] = full_name
            flash("Profile details saved! Please complete your PhonePe UPI payment below.", "success")
            return redirect(url_for('auth.payment'))
        else:
            flash(updated_user, "danger")

    return render_template('auth/onboarding.html', user=user)


@auth_bp.route('/payment')
@login_required
def payment():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    if user.get('payment_status') == 'Paid' and user.get('enrollment_status') == 'Enrolled':
        return redirect(url_for('student.dashboard'))

    return render_template('public/payment.html', user=user)


@auth_bp.route('/payment/process', methods=['POST'])
@login_required
def process_payment():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    utr_number = request.form.get('utr_number', '').strip()
    screenshot_file = request.files.get('payment_screenshot')

    if not utr_number or len(utr_number) < 6:
        flash("Please enter a valid PhonePe / UPI UTR / Transaction Reference Number (min 6 digits).", "danger")
        return redirect(url_for('auth.payment'))

    filename = ""
    if screenshot_file and screenshot_file.filename and allowed_file(screenshot_file.filename):
        sec_name = secure_filename(screenshot_file.filename)
        filename = f"pay_{user['id']}_{uuid.uuid4().hex[:6]}_{sec_name}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'payments')
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)
        screenshot_file.save(save_path)
    else:
        flash("Please upload a valid payment screenshot (PNG, JPG, JPEG, WEBP).", "danger")
        return redirect(url_for('auth.payment'))

    success, result = submit_user_payment_proof(user['id'], utr_number, filename)
    if success:
        flash("Payment proof submitted successfully! Your enrollment has been activated.", "success")
        return redirect(url_for('auth.payment_success'))
    else:
        flash(result, "danger")
        return redirect(url_for('auth.payment'))


@auth_bp.route('/payment/success')
@login_required
def payment_success():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    return render_template('public/payment_success.html', user=user)


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if email:
            admin_res = get_or_create_google_user({'email': email})
            if admin_res[0] and admin_res[3] == 'admin':
                login_session(admin_res[2], role='admin')
                flash(f"Logged in as Administrator ({email}).", "success")
                return redirect(url_for('admin.dashboard'))

        if not email or not password:
            flash("Please enter admin email and password.", "danger")
            return render_template('auth/admin_login.html')

        success, msg, admin_data = authenticate_admin(email, password)
        if success:
            login_session(admin_data, role='admin')
            flash("Logged in as Administrator.", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash(msg, "danger")

    return render_template('auth/admin_login.html')


@auth_bp.route('/logout')
def logout():
    logout_session()
    flash("You have been logged out safely.", "info")
    return redirect(url_for('public.index'))
