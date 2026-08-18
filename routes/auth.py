import os
import json
import base64
import uuid
import urllib.request
import urllib.parse
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from services.auth_service import (
    get_or_create_google_user, authenticate_admin, login_session, logout_session,
    get_current_user, login_required
)
from services.product_service import get_product_by_id, get_all_products
from services.enrollment_service import (
    get_or_create_enrollment, get_enrollment_by_id, get_student_enrollments,
    update_master_student_profile, submit_enrollment_payment_proof
)

auth_bp = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_google_redirect_uri():
    """Generates exact redirect URI matching Google Console configuration dynamically for Local and Production."""
    config_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
    if config_uri:
        return config_uri

    host = request.host.lower()
    
    # 1. Localhost development environment
    if 'localhost' in host or '127.0.0.1' in host:
        port_suffix = f":{host.split(':')[1]}" if ':' in host else ''
        return f"http://localhost{port_suffix}/auth/google/callback"

    # 2. Production environment (e.g., learnovaa.pythonanywhere.com)
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    if 'pythonanywhere' in host or scheme != 'https':
        scheme = 'https'

    return f"{scheme}://{request.host}/auth/google/callback"


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
        elif session.get('role') == 'mentor':
            return redirect(url_for('mentor.dashboard'))
        elif session.get('role') == 'student':
            flash(f"Welcome back, {user.get('full_name') or user.get('name')}! Explore our engineering programs below.", "success")
            return redirect(url_for('public.index'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET'])
def register():
    return redirect(url_for('auth.login'))


@auth_bp.route('/auth/google/redirect', methods=['GET'])
def google_redirect():
    """Redirects user to official Google OAuth 2.0 consent screen."""
    client_id = (current_app.config.get('GOOGLE_CLIENT_ID') or '').strip()
    
    if not client_id or 'YOUR_GOOGLE_CLIENT_ID' in client_id.upper():
        flash("Google OAuth Client ID is not configured yet. Please configure GOOGLE_CLIENT_ID in your .env file.", "warning")
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


@auth_bp.route('/auth/email-login', methods=['POST'])
def email_login():
    """Disabled direct email login for security - users must sign in via Google OAuth."""
    flash("Direct email login is disabled for security. Please sign in with Google.", "warning")
    return redirect(url_for('auth.login'))


@auth_bp.route('/auth/dev-login', methods=['POST'])
def dev_login():
    """Disabled dev bypass login for security."""
    flash("Developer login bypass is disabled. Please sign in with Google.", "warning")
    return redirect(url_for('auth.login'))


@auth_bp.route('/auth/google/callback', methods=['GET', 'POST'])
def google_callback():
    """Callback handler for Google OAuth code exchange."""
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description') or error
        flash(f"Google Sign-In notice: {error_desc}. You can sign in using your email below.", "warning")
        return redirect(url_for('auth.login'))

    google_info = {}

    credential = request.form.get('credential')
    if credential:
        google_info = parse_google_id_token(credential)

    if not google_info.get('email'):
        code = request.args.get('code')
        if code:
            redirect_uri = get_google_redirect_uri()
            google_info = exchange_google_code_for_user_info(code, redirect_uri)

    email = google_info.get('email', '').strip().lower()
    if not email:
        flash("Google Authentication failed to retrieve email. Please sign in using your email address below.", "warning")
        return redirect(url_for('auth.login'))

    success, msg, user_data, role = get_or_create_google_user(google_info)
    if success:
        login_session(user_data, role=role)
        if role == 'admin':
            flash(f"Welcome Admin, {user_data.get('name') or user_data.get('full_name')}!", "success")
            return redirect(url_for('admin.dashboard'))
        elif role == 'mentor':
            flash(f"Welcome Mentor, {user_data.get('full_name') or user_data.get('name')}!", "success")
            return redirect(url_for('mentor.dashboard'))
        else:
            flash(f"Signed in successfully as {user_data.get('email')}!", "success")
            return redirect(url_for('public.index'))
    else:
        flash(msg, "danger")
        return redirect(url_for('auth.login'))



@auth_bp.route('/enroll/<product_id>', methods=['GET'])
@login_required
def enroll_program(product_id):
    """Render multi-program enrollment page for a selected program."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    product = get_product_by_id(product_id)
    if not product:
        flash("Selected program not found.", "warning")
        return redirect(url_for('public.programs_catalog'))

    enrollment = get_or_create_enrollment(user['id'], product['id'])

    # Access control & Re-registration rules
    p_status = enrollment.get('payment_status')
    if p_status in ['Confirmed', 'Approved', 'Paid']:
        flash(f"You are already registered and enrolled in {product['name']}! Payment is confirmed.", "success")
        return redirect(url_for('student.dashboard'))

    if p_status in ['Proof Submitted', 'Pending']:
        flash(f"Your payment proof for {product['name']} has been submitted and is currently pending verification.", "info")
        return redirect(url_for('auth.payment_success_page', enrollment_id=enrollment['id']))

    # If payment was Rejected, allow student to re-register/resubmit
    if p_status == 'Rejected':
        flash("Your previous payment proof was rejected. Please review your details and resubmit a valid payment screenshot & UTR number.", "warning")

    return render_template('student/enroll.html', user=user, product=product, enrollment=enrollment)


@auth_bp.route('/enroll/<product_id>/process', methods=['POST'])
@login_required
def process_enrollment(product_id):
    """Processes Master Student Profile, Program-Specific details, and Payment Proof with 100 KB file validation."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    product = get_product_by_id(product_id)
    if not product:
        flash("Program not found.", "danger")
        return redirect(url_for('public.programs_catalog'))

    enrollment = get_or_create_enrollment(user['id'], product['id'])

    # 1. Update Master Student Profile (reused across all programs)
    profile_data = {
        'full_name': request.form.get('full_name', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'gender': request.form.get('gender', '').strip(),
        'dob': request.form.get('dob', '').strip(),
        'address': request.form.get('address', '').strip(),
        'branch': request.form.get('branch', '').strip(),
        'custom_branch': request.form.get('custom_branch', '').strip(),
        'academic_year': request.form.get('academic_year', '').strip(),
        'custom_academic_year': request.form.get('custom_academic_year', '').strip()
    }

    if not profile_data['full_name']:
        flash("Full name is required.", "danger")
        return redirect(url_for('auth.enroll_program', product_id=product_id))

    if not profile_data['phone'] or len(profile_data['phone'].replace('-', '').replace(' ', '').replace('+', '')) < 8:
        flash("Please enter a valid phone contact number.", "danger")
        return redirect(url_for('auth.enroll_program', product_id=product_id))

    success, profile_res = update_master_student_profile(user['id'], profile_data)
    if not success:
        flash(profile_res, "danger")
        return redirect(url_for('auth.enroll_program', product_id=product_id))

    # 2. UTR & Payment Proof Screenshot Upload (STRICT 100 KB MAX VALIDATION)
    utr_number = request.form.get('utr_number', '').strip()
    screenshot_file = request.files.get('payment_screenshot')

    pay_success, pay_msg = submit_enrollment_payment_proof(
        enrollment_id=enrollment['id'],
        utr_number=utr_number,
        screenshot_file=screenshot_file,
        app_root_path=current_app.root_path
    )

    if pay_success:
        flash(pay_msg, "success")
        return redirect(url_for('auth.payment_success_page', enrollment_id=enrollment['id']))
    else:
        flash(pay_msg, "danger")
        return redirect(url_for('auth.enroll_program', product_id=product_id))


@auth_bp.route('/payment/success/<enrollment_id>', methods=['GET'])
@login_required
def payment_success_page(enrollment_id):
    """Displays Payment Proof Submitted Confirmation with PENDING VERIFICATION status."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    enrollment = get_enrollment_by_id(enrollment_id)
    if not enrollment:
        flash("Enrollment record not found.", "warning")
        return redirect(url_for('public.index'))

    return render_template('public/payment_success.html', user=user, enrollment=enrollment)


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if email and password:
            success, msg, admin_user = authenticate_admin(email, password)
            if success:
                login_session(admin_user, role='admin')
                flash(f"Welcome back, {admin_user.get('name')}!", "success")
                return redirect(url_for('admin.dashboard'))
            else:
                flash(msg, "danger")
                return render_template('auth/admin_login.html')
        elif email:
            google_info = {'email': email, 'name': 'Admin'}
            success, msg, user_data, role = get_or_create_google_user(google_info)
            if success and role == 'admin':
                login_session(user_data, role='admin')
                flash(f"Signed in as Admin ({email}).", "success")
                return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html')



@auth_bp.route('/logout')
def logout():
    logout_session()
    flash("You have been logged out safely.", "info")
    return redirect(url_for('public.index'))
