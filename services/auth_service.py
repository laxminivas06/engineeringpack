import uuid
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from services.json_database import JSONDatabase
from services.product_service import get_default_product, get_product_by_id

users_db = JSONDatabase('users')
admins_db = JSONDatabase('admins')


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def get_or_create_google_user(google_info: dict, target_product_id: str = None):
    email = google_info.get('email', '').strip().lower()
    google_id = google_info.get('sub') or google_info.get('id') or ''
    name = google_info.get('name', '').strip() or 'User'
    picture = google_info.get('picture', '')

    if not email:
        return False, "Failed to retrieve email from Google profile.", None, 'student'

    # Check if this email belongs to an Admin account
    admin_user = admins_db.find_one(email=email)
    if admin_user:
        updates = {}
        if not admin_user.get('google_id') and google_id:
            updates['google_id'] = google_id
        if updates:
            admin_user = admins_db.update(admin_user['id'], updates)
        return True, "Admin Google authentication successful.", admin_user, 'admin'

    # Check if this email belongs to a Mentor account
    mentors_db = JSONDatabase('mentors')
    mentor_user = mentors_db.find_one(email=email)
    if mentor_user:
        updates = {}
        if not mentor_user.get('google_id') and google_id:
            updates['google_id'] = google_id
        if updates:
            mentor_user = mentors_db.update(mentor_user['id'], updates)
        return True, "Mentor authentication successful.", mentor_user, 'mentor'

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

    # Determine product
    product = get_product_by_id(target_product_id) if target_product_id else get_default_product()
    prod_id = product.get('id') if product else 'prod_engpack'
    prod_name = product.get('name') if product else 'Engineering Pack'

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
        'product_id': prod_id,
        'product_name': prod_name,
        'role': 'student',
        'status': 'Active',
        'student_status': 'Active',
        'registration_status': 'Registered',
        'enrollment_status': 'Unenrolled',
        'payment_status': 'Unpaid',
        'payment_amount': product.get('price', 3500) if product else 3500,
        'payment_method': 'Online / UPI',
        'payment_screenshot': '',
        'utr_number': '',
        'payment_date': '',
        'admin_remarks': '',
        'created_at': '2026-08-14T19:00:00Z',
        'current_phase': 'Phase 1',
        'current_day': 1,
        'progress_pct': 0,
        'completed_projects': 0
    }
    created = users_db.create(new_user)
    
    # Auto assign student to active cohort for chosen product
    from services.cohort_service import auto_assign_student_to_active_cohort, log_activity
    auto_assign_student_to_active_cohort(created['id'], prod_id)
    log_activity("student_registered", "New Student Registered", f"{created['full_name']} ({created['email']}) registered for {prod_name}.")

    return True, "Google registration successful.", created, 'student'


def complete_user_onboarding(user_id: str, data: dict):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    product_id = data.get('product_id') or user.get('product_id')
    product = get_product_by_id(product_id) or get_default_product()

    from services.cohort_service import auto_assign_student_to_active_cohort
    if not user.get('cohort_id') or user.get('product_id') != product.get('id'):
        auto_assign_student_to_active_cohort(user_id, product.get('id'))

    updates = {
        'full_name': data.get('full_name', '').strip(),
        'phone': data.get('phone', '').strip(),
        'user_type': data.get('user_type', '').strip(),
        'custom_user_type': data.get('custom_user_type', '').strip(),
        'branch': data.get('branch', '').strip(),
        'custom_branch': data.get('custom_branch', '').strip(),
        'academic_year': data.get('academic_year', '').strip(),
        'product_id': product.get('id'),
        'product_name': product.get('name'),
        'payment_amount': product.get('price', 3500),
        'registration_status': 'Payment Pending',
        'enrollment_status': 'Pending Payment'
    }

    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def submit_user_payment_proof(user_id: str, utr_number: str, screenshot_filename: str):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    import datetime
    updates = {
        'utr_number': utr_number,
        'payment_screenshot': screenshot_filename,
        'payment_status': 'Approved',
        'registration_status': 'Payment Verified',
        'enrollment_status': 'Enrolled',
        'student_status': 'Active',
        'payment_date': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    updated_user = users_db.update(user_id, updates)

    from services.cohort_service import log_activity
    log_activity("payment_submitted", "Payment Proof Submitted", f"Payment proof (UTR {utr_number}) submitted by {user.get('full_name')}.")

    return True, updated_user


def complete_user_payment(user_id: str):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    import datetime
    updates = {
        'payment_status': 'Approved',
        'registration_status': 'Payment Verified',
        'enrollment_status': 'Enrolled',
        'student_status': 'Active',
        'payment_date': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    updated_user = users_db.update(user_id, updates)
    return True, updated_user


def approve_student_payment(user_id: str, admin_remarks: str = ""):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    import datetime
    updates = {
        'payment_status': 'Approved',
        'registration_status': 'Payment Verified',
        'enrollment_status': 'Enrolled',
        'student_status': 'Active',
        'admin_remarks': admin_remarks,
        'payment_date': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    updated_user = users_db.update(user_id, updates)

    from services.cohort_service import log_activity
    log_activity("payment_approved", "Payment Approved", f"Payment for {user.get('full_name')} approved by admin.")
    return True, updated_user


def reject_student_payment(user_id: str, admin_remarks: str = ""):
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User account not found."

    updates = {
        'payment_status': 'Rejected',
        'registration_status': 'Payment Rejected',
        'enrollment_status': 'Payment Rejected',
        'admin_remarks': admin_remarks
    }
    updated_user = users_db.update(user_id, updates)

    from services.cohort_service import log_activity
    log_activity("payment_rejected", "Payment Rejected", f"Payment for {user.get('full_name')} rejected by admin.")
    return True, updated_user


def authenticate_admin(email: str, password: str):
    email = email.strip().lower()
    admin = admins_db.find_one(email=email)
    if not admin:
        return False, "Invalid admin credentials.", None

    if verify_password(password, admin.get('password_hash', '')):
        return True, "Authentication successful.", admin
    return False, "Invalid admin credentials.", None


def login_session(user: dict, role: str):
    session['user_id'] = user.get('id')
    session['email'] = user.get('email')
    session['role'] = role
    session['name'] = user.get('full_name') or user.get('name') or user.get('username') or 'User'
    session['show_welcome_banner'] = True


def logout_session():
    session.clear()


def get_current_user():
    user_id = session.get('user_id')
    role = session.get('role')
    if not user_id or not role:
        return None

    if role == 'admin':
        return admins_db.find_by_id(user_id)
    elif role == 'mentor':
        mentors_db = JSONDatabase('mentors')
        return mentors_db.find_by_id(user_id)
    elif role == 'student':
        return users_db.find_by_id(user_id)
    return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'admin':
            flash("Admin privilege required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def mentor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'mentor':
            flash("Mentor access required.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

