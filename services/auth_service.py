import uuid
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from services.json_database import JSONDatabase

users_db = JSONDatabase('users')
admins_db = JSONDatabase('admins')


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def get_or_create_google_user(google_info: dict):
    email = google_info.get('email', '').strip().lower()
    google_id = google_info.get('sub') or google_info.get('id') or ''
    name = google_info.get('name', '').strip() or 'User'
    picture = google_info.get('picture', '')

    if not email:
        return False, "Failed to retrieve email from Google profile.", None, 'student'

    # Check if this email belongs to an Admin account (e.g. laxminivasmorishetty143@gmail.com)
    admin_user = admins_db.find_one(email=email)
    if admin_user:
        updates = {}
        if not admin_user.get('google_id') and google_id:
            updates['google_id'] = google_id
        if updates:
            admin_user = admins_db.update(admin_user['id'], updates)
        return True, "Admin Google authentication successful.", admin_user, 'admin'

    # Check existing student by google_id or email
    user = users_db.find_one(google_id=google_id)
    if not user:
        user = users_db.find_one(email=email)

    if user:
        updates = {}
        if not user.get('google_id') and google_id:
            updates['google_id'] = google_id
        if not user.get('picture') and picture:
            updates['picture'] = picture
        if updates:
            user = users_db.update(user['id'], updates)
        return True, "Google authentication successful.", user, 'student'

    # Create new Google student
    new_user = {
        'id': uuid.uuid4().hex[:12],
        'google_id': google_id,
        'email': email,
        'full_name': name,
        'picture': picture,
        'phone': '',
        'user_type': '',
        'custom_user_type': '',
        'branch': '',
        'custom_branch': '',
        'academic_year': '',
        'role': 'student',
        'status': 'Active',
        'enrollment_status': 'Pending Onboarding',
        'payment_status': 'Unpaid',
        'payment_screenshot': '',
        'utr_number': '',
        'created_at': '2026-08-14T19:00:00Z',
        'current_phase': 'Phase 1: Engineer Mindset',
        'current_day': 1,
        'progress_pct': 0,
        'completed_projects': 0
    }
    created = users_db.create(new_user)
    return True, "Google registration successful.", created, 'student'


def complete_user_onboarding(user_id: str, data: dict):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    updates = {
        'full_name': data.get('full_name', '').strip(),
        'phone': data.get('phone', '').strip(),
        'user_type': data.get('user_type', '').strip(),
        'custom_user_type': data.get('custom_user_type', '').strip(),
        'branch': data.get('branch', '').strip(),
        'custom_branch': data.get('custom_branch', '').strip(),
        'academic_year': data.get('academic_year', '').strip(),
        'enrollment_status': 'Pending Payment'
    }

    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def submit_user_payment_proof(user_id: str, utr_number: str, screenshot_filename: str):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    updates = {
        'utr_number': utr_number,
        'payment_screenshot': screenshot_filename,
        'payment_status': 'Paid',
        'enrollment_status': 'Enrolled'
    }
    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def complete_user_payment(user_id: str):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    updates = {
        'payment_status': 'Paid',
        'enrollment_status': 'Enrolled'
    }
    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def approve_student_payment(user_id: str):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    updates = {
        'payment_status': 'Paid',
        'enrollment_status': 'Enrolled'
    }
    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def reject_student_payment(user_id: str):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    updates = {
        'payment_status': 'Unpaid',
        'enrollment_status': 'Pending Payment'
    }
    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def authenticate_admin(email: str, password: str):
    email_clean = email.strip().lower()
    admin = admins_db.find_one(email=email_clean)
    if not admin:
        return False, "Invalid admin credentials.", None

    if not verify_password(password, admin.get('password_hash', '')):
        return False, "Invalid admin credentials.", None

    return True, "Admin login successful.", admin


def login_session(user_data: dict, role: str):
    session.clear()
    session['user_id'] = user_data.get('id')
    session['email'] = user_data.get('email')
    session['name'] = user_data.get('full_name') or user_data.get('name') or 'User'
    session['role'] = role
    session.permanent = True


def logout_session():
    session.clear()


def get_current_user():
    user_id = session.get('user_id')
    role = session.get('role')
    if not user_id or not role:
        return None

    if role == 'student':
        return users_db.find_by_id(user_id)
    elif role == 'admin':
        return admins_db.find_by_id(user_id)
    return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in with Google to continue.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash("Student access required.", "danger")
            return redirect(url_for('auth.login', next=request.url))

        user = get_current_user()
        if not user:
            return redirect(url_for('auth.login'))

        if user.get('enrollment_status') == 'Pending Onboarding' and request.endpoint != 'auth.onboarding':
            flash("Please complete your basic profile details first.", "info")
            return redirect(url_for('auth.onboarding'))

        if user.get('payment_status') == 'Unpaid' and request.endpoint not in ['auth.onboarding', 'auth.payment', 'auth.process_payment', 'auth.payment_success']:
            flash("Please complete your program enrollment payment to access student features.", "info")
            return redirect(url_for('auth.payment'))

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash("Admin access required. Please sign in with an administrator Google account.", "danger")
            return redirect(url_for('auth.admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
