import os
import csv
import io
import uuid
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, current_app, session
from werkzeug.utils import secure_filename
from services.auth_service import admin_required, get_current_user, approve_student_payment, reject_student_payment
from services.product_service import (
    get_all_products, get_product_by_id, create_product, update_product, delete_product, get_default_product
)
from services.cohort_service import (
    get_all_cohorts, get_cohort_by_id, get_active_cohort, create_cohort,
    set_active_cohort, complete_cohort, get_dashboard_kpis, can_open_new_cohort,
    update_cohort, delete_cohort
)
from services.mentor_service import (
    get_all_mentors, get_mentor_by_id, create_mentor, update_mentor, delete_mentor,
    get_mentors_for_program, assign_mentor_to_program, remove_mentor_from_program
)
from services.json_database import JSONDatabase

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

users_db = JSONDatabase('users')
curriculum_db = JSONDatabase('curriculum')
projects_db = JSONDatabase('projects')
announcements_db = JSONDatabase('announcements')
contacts_db = JSONDatabase('contacts')
mentors_db = JSONDatabase('mentors')
settings_db = JSONDatabase('settings')
activity_db = JSONDatabase('activity_logs')

ALLOWED_QR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_qr_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_QR_EXTENSIONS


def get_selected_product_id():
    """Retrieves selected active product ID from URL query string or session."""
    query_prod = request.args.get('product_id')
    if query_prod:
        session['admin_product_id'] = query_prod
        return query_prod
    return session.get('admin_product_id', 'all')


# ----------------------------------------------------
# 0. PRODUCT CONTEXT SWITCHER ROUTE
# ----------------------------------------------------
@admin_bp.route('/select-product/<product_id>')
@admin_required
def select_product(product_id):
    session['admin_product_id'] = product_id
    referrer = request.referrer
    if referrer and '/admin/' in referrer:
        return redirect(referrer)
    return redirect(url_for('admin.dashboard'))


# ----------------------------------------------------
# 1. PRODUCTS & PROGRAM MANAGEMENT (Top-Level Entity)
# ----------------------------------------------------
@admin_bp.route('/products')
@admin_required
def products():
    admin_user = get_current_user()
    all_prods = get_all_products()
    cohorts = get_all_cohorts()

    # Calculate statistics per product
    for p in all_prods:
        prod_cohorts = [c for c in cohorts if c.get('product_id') == p.get('id')]
        p['cohort_count'] = len(prod_cohorts)
        p['student_count'] = len(users_db.find_all(lambda u: u.get('product_id') == p.get('id')))

    return render_template('admin/products.html', admin=admin_user, products=all_prods)


@admin_bp.route('/products/add', methods=['POST'])
@admin_required
def add_product():
    name = request.form.get('name', '').strip()
    tagline = request.form.get('tagline', '').strip()
    description = request.form.get('description', '').strip()
    duration_days = request.form.get('duration_days', '45').strip()
    price = request.form.get('price', '3500').strip()
    default_cohort_capacity = request.form.get('default_cohort_capacity', '35').strip()
    status = request.form.get('status', 'Active').strip()

    overview = request.form.get('overview', '').strip()
    curriculum_summary = request.form.get('curriculum_summary', '').strip()
    courses_modules = request.form.get('courses_modules', '').strip()
    phases_duration = request.form.get('phases_duration', '').strip()
    projects_summary = request.form.get('projects_summary', '').strip()
    learning_outcomes = request.form.get('learning_outcomes', '').strip()
    eligibility = request.form.get('eligibility', '').strip()
    program_specific_content = request.form.get('program_specific_content', '').strip()

    if not name:
        flash("Product Name is required.", "danger")
        return redirect(url_for('admin.products'))

    # Handle QR upload if provided
    qr_file = request.files.get('payment_qr')
    qr_url = "/static/images/qr-code.png"
    if qr_file and qr_file.filename and allowed_qr_file(qr_file.filename):
        ext = qr_file.filename.rsplit('.', 1)[1].lower()
        filename = f"qr_{uuid.uuid4().hex[:6]}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'qr')
        os.makedirs(upload_dir, exist_ok=True)
        qr_file.save(os.path.join(upload_dir, filename))
        qr_url = f"/static/uploads/qr/{filename}"

    # Handle Program Banner / Image upload
    banner_file = request.files.get('banner_image')
    banner_url = ""
    if banner_file and banner_file.filename and allowed_qr_file(banner_file.filename):
        ext = banner_file.filename.rsplit('.', 1)[1].lower()
        b_filename = f"banner_{uuid.uuid4().hex[:6]}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'programs')
        os.makedirs(upload_dir, exist_ok=True)
        banner_file.save(os.path.join(upload_dir, b_filename))
        banner_url = f"/static/uploads/programs/{b_filename}"

    new_prod = create_product(
        name=name,
        tagline=tagline,
        description=description,
        duration_days=int(duration_days) if duration_days.isdigit() else 45,
        price=float(price) if price.replace('.', '', 1).isdigit() else 3500,
        payment_qr_url=qr_url,
        banner_image_url=banner_url,
        overview=overview,
        curriculum_summary=curriculum_summary,
        courses_modules=courses_modules,
        phases_duration=phases_duration,
        projects_summary=projects_summary,
        learning_outcomes=learning_outcomes,
        eligibility=eligibility,
        program_specific_content=program_specific_content,
        default_cohort_capacity=int(default_cohort_capacity) if default_cohort_capacity.isdigit() else 35,
        status=status
    )

    # Automatically create initial Cohort 1 for this new product
    create_cohort(
        product_id=new_prod['id'],
        name="Cohort 1",
        start_date="",
        end_date="",
        max_capacity=new_prod['default_cohort_capacity'],
        status="Active",
        description=f"Initial active cohort for {new_prod['name']}."
    )

    flash(f"Product '{new_prod['name']}' created successfully with Cohort 1 initialized!", "success")
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/edit/<product_id>', methods=['POST'])
@admin_required
def edit_product(product_id):
    name = request.form.get('name', '').strip()
    tagline = request.form.get('tagline', '').strip()
    description = request.form.get('description', '').strip()
    duration_days = request.form.get('duration_days', '').strip()
    price = request.form.get('price', '').strip()
    default_cohort_capacity = request.form.get('default_cohort_capacity', '').strip()
    status = request.form.get('status', '').strip()

    overview = request.form.get('overview', '').strip()
    curriculum_summary = request.form.get('curriculum_summary', '').strip()
    courses_modules = request.form.get('courses_modules', '').strip()
    phases_duration = request.form.get('phases_duration', '').strip()
    projects_summary = request.form.get('projects_summary', '').strip()
    learning_outcomes = request.form.get('learning_outcomes', '').strip()
    eligibility = request.form.get('eligibility', '').strip()
    program_specific_content = request.form.get('program_specific_content', '').strip()

    updates = {
        'name': name,
        'tagline': tagline,
        'description': description,
        'status': status,
        'overview': overview,
        'curriculum_summary': curriculum_summary,
        'courses_modules': courses_modules,
        'phases_duration': phases_duration,
        'projects_summary': projects_summary,
        'learning_outcomes': learning_outcomes,
        'eligibility': eligibility,
        'program_specific_content': program_specific_content
    }
    if duration_days.isdigit():
        updates['duration_days'] = int(duration_days)
    if price.replace('.', '', 1).isdigit():
        updates['price'] = float(price)
    if default_cohort_capacity.isdigit():
        updates['default_cohort_capacity'] = int(default_cohort_capacity)

    # Handle QR Upload
    qr_file = request.files.get('payment_qr')
    if qr_file and qr_file.filename and allowed_qr_file(qr_file.filename):
        ext = qr_file.filename.rsplit('.', 1)[1].lower()
        filename = f"qr_{uuid.uuid4().hex[:6]}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'qr')
        os.makedirs(upload_dir, exist_ok=True)
        qr_file.save(os.path.join(upload_dir, filename))
        updates['payment_qr_url'] = f"/static/uploads/qr/{filename}"

    # Handle Program Banner / Image upload
    banner_file = request.files.get('banner_image')
    if banner_file and banner_file.filename and allowed_qr_file(banner_file.filename):
        ext = banner_file.filename.rsplit('.', 1)[1].lower()
        b_filename = f"banner_{uuid.uuid4().hex[:6]}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'programs')
        os.makedirs(upload_dir, exist_ok=True)
        banner_file.save(os.path.join(upload_dir, b_filename))
        updates['banner_image_url'] = f"/static/uploads/programs/{b_filename}"

    success, res = update_product(product_id, updates)
    if success:
        flash(f"Product '{name}' updated successfully!", "success")
    else:
        flash(res, "danger")

    return redirect(request.referrer or url_for('admin.products'))


@admin_bp.route('/products/delete/<product_id>', methods=['POST'])
@admin_required
def delete_existing_product(product_id):
    success, res = delete_product(product_id)
    if success:
        flash(res, "success")
    else:
        flash(res, "warning")
    return redirect(url_for('admin.products'))


# ----------------------------------------------------
# 2. ADMIN PRODUCT DASHBOARD (Operational Overview)
# ----------------------------------------------------
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    admin_user = get_current_user()
    selected_prod_id = get_selected_product_id()
    kpis = get_dashboard_kpis(selected_prod_id)
    
    # Fetch recent activity timeline (last 6 entries)
    activities = activity_db.find_all()
    recent_activities = sorted(activities, key=lambda x: x.get('timestamp', ''), reverse=True)[:6]

    # Fetch student reviews for feedback widget
    from services.review_service import get_all_reviews
    all_reviews = get_all_reviews()
    mentor_reviews = [r for r in all_reviews if r.get('scope') == 'mentor']
    cohort_reviews = [r for r in all_reviews if r.get('scope') == 'cohort']

    return render_template(
        'admin/dashboard.html',
        admin=admin_user,
        kpis=kpis,
        recent_activities=recent_activities,
        selected_prod_id=selected_prod_id,
        reviews=all_reviews[:6],
        mentor_reviews=mentor_reviews[:6],
        cohort_reviews=cohort_reviews[:6],
        total_reviews_count=len(all_reviews),
        mentor_reviews_count=len(mentor_reviews),
        cohort_reviews_count=len(cohort_reviews)
    )


# ----------------------------------------------------
# 3. PRODUCT SETTINGS PAGE (Price, QR, Capacity, etc.)
# ----------------------------------------------------
@admin_bp.route('/product-settings', defaults={'product_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/product-settings/<product_id>', methods=['GET', 'POST'])
@admin_required
def product_settings(product_id):
    admin_user = get_current_user()
    if not product_id:
        product_id = get_selected_product_id()
        if product_id == 'all':
            default_p = get_default_product()
            product_id = default_p.get('id') if default_p else 'prod_engpack'

    product = get_product_by_id(product_id) or get_default_product()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        tagline = request.form.get('tagline', '').strip()
        description = request.form.get('description', '').strip()
        duration_days = request.form.get('duration_days', '').strip()
        price = request.form.get('price', '').strip()
        default_cohort_capacity = request.form.get('default_cohort_capacity', '').strip()

        overview = request.form.get('overview', '').strip()
        curriculum_summary = request.form.get('curriculum_summary', '').strip()
        courses_modules = request.form.get('courses_modules', '').strip()
        phases_duration = request.form.get('phases_duration', '').strip()
        projects_summary = request.form.get('projects_summary', '').strip()
        learning_outcomes = request.form.get('learning_outcomes', '').strip()
        eligibility = request.form.get('eligibility', '').strip()
        program_specific_content = request.form.get('program_specific_content', '').strip()

        updates = {
            'name': name or product.get('name'),
            'tagline': tagline,
            'description': description,
            'overview': overview,
            'curriculum_summary': curriculum_summary,
            'courses_modules': courses_modules,
            'phases_duration': phases_duration,
            'projects_summary': projects_summary,
            'learning_outcomes': learning_outcomes,
            'eligibility': eligibility,
            'program_specific_content': program_specific_content
        }
        if duration_days.isdigit():
            updates['duration_days'] = int(duration_days)
        if price.replace('.', '', 1).isdigit():
            updates['price'] = float(price)
        if default_cohort_capacity.isdigit():
            updates['default_cohort_capacity'] = int(default_cohort_capacity)

        # Handle Payment QR Image Upload
        qr_file = request.files.get('payment_qr')
        if qr_file and qr_file.filename and allowed_qr_file(qr_file.filename):
            ext = qr_file.filename.rsplit('.', 1)[1].lower()
            filename = f"payment_qr_{product['id']}_{uuid.uuid4().hex[:6]}.{ext}"
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'qr')
            os.makedirs(upload_dir, exist_ok=True)
            qr_file.save(os.path.join(upload_dir, filename))
            updates['payment_qr_url'] = f"/static/uploads/qr/{filename}"
            flash("Product Payment QR Code uploaded successfully!", "success")

        # Handle Program Banner Image Upload
        banner_file = request.files.get('banner_image')
        if banner_file and banner_file.filename and allowed_qr_file(banner_file.filename):
            ext = banner_file.filename.rsplit('.', 1)[1].lower()
            b_filename = f"banner_{product['id']}_{uuid.uuid4().hex[:6]}.{ext}"
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'programs')
            os.makedirs(upload_dir, exist_ok=True)
            banner_file.save(os.path.join(upload_dir, b_filename))
            updates['banner_image_url'] = f"/static/uploads/programs/{b_filename}"
            flash("Program Banner Image uploaded successfully!", "success")

        success, res = update_product(product['id'], updates)
        if success:
            flash(f"Product settings updated for '{product.get('name')}'!", "success")
            product = get_product_by_id(product['id'])
        else:
            flash(res, "danger")

    assigned_mentors = get_mentors_for_program(product['id'], public_only=False)
    all_central_mentors = get_all_mentors()
    assigned_ids = [m['id'] for m in assigned_mentors]
    available_mentors = [m for m in all_central_mentors if m['id'] not in assigned_ids]

    return render_template(
        'admin/product_settings.html',
        admin=admin_user,
        product=product,
        assigned_mentors=assigned_mentors,
        available_mentors=available_mentors
    )


# ----------------------------------------------------
# 3.5 CENTRAL MENTOR MANAGEMENT SYSTEM (Admin -> Mentors)
# ----------------------------------------------------
@admin_bp.route('/mentors')
@admin_required
def mentors_page():
    admin_user = get_current_user()
    mentors_list = get_all_mentors()
    products_list = get_all_products()

    # Calculate assigned programs per mentor
    for m in mentors_list:
        assigned_prods = [p for p in products_list if m['id'] in p.get('assigned_mentor_ids', [])]
        m['assigned_program_count'] = len(assigned_prods)
        m['assigned_programs'] = [p.get('name') for p in assigned_prods]

    return render_template('admin/mentors.html', admin=admin_user, mentors=mentors_list, products=products_list)


@admin_bp.route('/mentors/add', methods=['POST'])
@admin_required
def add_mentor_route():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    professional_title = request.form.get('professional_title', '').strip()
    internal_phone = request.form.get('internal_phone', '').strip()
    status = request.form.get('status', 'Active').strip()

    if not full_name:
        flash("Mentor Full Name is required.", "danger")
        return redirect(url_for('admin.mentors_page'))

    # Handle Profile Photo Upload
    photo_file = request.files.get('profile_photo')
    photo_url = "/static/images/default-avatar.png"
    if photo_file and photo_file.filename and allowed_qr_file(photo_file.filename):
        ext = photo_file.filename.rsplit('.', 1)[1].lower()
        filename = f"mentor_{uuid.uuid4().hex[:6]}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'mentors')
        os.makedirs(upload_dir, exist_ok=True)
        photo_file.save(os.path.join(upload_dir, filename))
        photo_url = f"/static/uploads/mentors/{filename}"

    new_m = create_mentor(
        full_name=full_name,
        email=email,
        professional_title=professional_title,
        internal_phone=internal_phone,
        profile_photo_url=photo_url,
        status=status
    )

    # Assign immediately to selected programs if submitted
    selected_program_ids = request.form.getlist('assigned_program_ids')
    for pid in selected_program_ids:
        assign_mentor_to_program(pid, new_m['id'])

    flash(f"Mentor '{new_m['full_name']}' created successfully in central database!", "success")
    return redirect(url_for('admin.mentors_page'))


@admin_bp.route('/mentors/edit/<mentor_id>', methods=['POST'])
@admin_required
def edit_mentor_route(mentor_id):
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    professional_title = request.form.get('professional_title', '').strip()
    internal_phone = request.form.get('internal_phone', '').strip()
    status = request.form.get('status', 'Active').strip()

    updates = {
        'full_name': full_name,
        'email': email,
        'professional_title': professional_title,
        'internal_phone': internal_phone,
        'status': status
    }

    # Handle Photo Upload if a new file is uploaded
    photo_file = request.files.get('profile_photo')
    if photo_file and photo_file.filename and allowed_qr_file(photo_file.filename):
        ext = photo_file.filename.rsplit('.', 1)[1].lower()
        filename = f"mentor_{uuid.uuid4().hex[:6]}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'mentors')
        os.makedirs(upload_dir, exist_ok=True)
        photo_file.save(os.path.join(upload_dir, filename))
        updates['profile_photo_url'] = f"/static/uploads/mentors/{filename}"

    success, res = update_mentor(mentor_id, updates)
    if success:
        flash(f"Mentor '{full_name}' updated successfully!", "success")
    else:
        flash(res, "danger")

    return redirect(request.referrer or url_for('admin.mentors_page'))


@admin_bp.route('/mentors/delete/<mentor_id>', methods=['POST'])
@admin_required
def delete_mentor_route(mentor_id):
    success, msg = delete_mentor(mentor_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "warning")
    return redirect(url_for('admin.mentors_page'))


@admin_bp.route('/product-mentors/<product_id>/assign', methods=['POST'])
@admin_required
def assign_product_mentor(product_id):
    mentor_id = request.form.get('mentor_id', '').strip()
    if not mentor_id:
        flash("Please select a mentor to assign.", "danger")
        return redirect(request.referrer or url_for('admin.product_settings', product_id=product_id))

    success, msg = assign_mentor_to_program(product_id, mentor_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "warning")
    return redirect(request.referrer or url_for('admin.product_settings', product_id=product_id))


@admin_bp.route('/product-mentors/<product_id>/remove/<mentor_id>', methods=['POST'])
@admin_required
def remove_product_mentor(product_id, mentor_id):
    success, msg = remove_mentor_from_program(product_id, mentor_id)
    if success:
        flash(msg, "info")
    else:
        flash(msg, "danger")
    return redirect(request.referrer or url_for('admin.product_settings', product_id=product_id))


# ----------------------------------------------------
# 4. COHORT MANAGEMENT SYSTEM (Scoped to Product)
# ----------------------------------------------------
@admin_bp.route('/cohorts')
@admin_required
def cohorts():
    admin_user = get_current_user()
    selected_prod_id = get_selected_product_id()
    all_cohorts = get_all_cohorts(selected_prod_id)
    active_cohort = get_active_cohort(selected_prod_id if selected_prod_id != 'all' else None)

    projects_db = JSONDatabase('projects')
    mentors_db = JSONDatabase('mentors')
    all_projects = projects_db.read_all()
    all_mentors = mentors_db.read_all()

    return render_template(
        'admin/cohorts.html',
        admin=admin_user,
        cohorts=all_cohorts,
        active_cohort=active_cohort,
        selected_prod_id=selected_prod_id,
        all_projects=all_projects,
        all_mentors=all_mentors
    )


@admin_bp.route('/cohorts/create', methods=['POST'])
@admin_required
def create_new_cohort():
    product_id = request.form.get('product_id', '').strip()
    name = request.form.get('name', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    max_capacity = request.form.get('max_capacity', '').strip()
    status = request.form.get('status', 'Upcoming').strip()
    description = request.form.get('description', '').strip()

    if not product_id:
        product_id = get_selected_product_id()
        if product_id == 'all':
            default_p = get_default_product()
            product_id = default_p.get('id') if default_p else 'prod_engpack'

    if not name:
        flash("Cohort Name is required.", "danger")
        return redirect(url_for('admin.cohorts'))

    if status == 'Active':
        can_open, msg = can_open_new_cohort(product_id)
        if not can_open:
            flash(msg, "warning")
            return redirect(url_for('admin.cohorts'))

    duration_days = request.form.get('duration_days', '').strip()
    whatsapp_link = request.form.get('whatsapp_link', '').strip()
    assigned_project_ids = request.form.getlist('assigned_project_ids')
    assigned_mentor_ids = request.form.getlist('assigned_mentor_ids')

    cap_val = int(max_capacity) if max_capacity.isdigit() else get_dashboard_kpis(product_id).get('cohort_capacity', 35)
    new_c = create_cohort(
        product_id=product_id,
        name=name,
        start_date=start_date,
        end_date=end_date,
        max_capacity=cap_val,
        status=status,
        description=description,
        duration_days=int(duration_days) if duration_days.isdigit() else 45,
        whatsapp_link=whatsapp_link,
        assigned_project_ids=assigned_project_ids,
        assigned_mentor_ids=assigned_mentor_ids
    )

    if status == 'Active':
        set_active_cohort(new_c['id'])

    flash(f"Successfully created '{new_c['name']}' with seat capacity of {cap_val}.", "success")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/activate/<cohort_id>', methods=['POST'])
@admin_required
def activate_existing_cohort(cohort_id):
    success, msg = set_active_cohort(cohort_id)
    if success:
        flash("Selected cohort is now active for new enrollments.", "success")
    else:
        flash(msg, "warning")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/edit/<cohort_id>', methods=['POST'])
@admin_required
def edit_cohort_route(cohort_id):
    product_id = request.form.get('product_id', '').strip()
    name = request.form.get('name', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    max_capacity = request.form.get('max_capacity', '').strip()
    status = request.form.get('status', '').strip()
    description = request.form.get('description', '').strip()
    duration_days = request.form.get('duration_days', '').strip()
    whatsapp_link = request.form.get('whatsapp_link', '').strip()
    assigned_project_ids = request.form.getlist('assigned_project_ids')
    assigned_mentor_ids = request.form.getlist('assigned_mentor_ids')

    updates = {
        'name': name,
        'start_date': start_date,
        'end_date': end_date,
        'max_capacity': max_capacity,
        'status': status,
        'description': description,
        'whatsapp_link': whatsapp_link,
        'assigned_project_ids': assigned_project_ids,
        'assigned_mentor_ids': assigned_mentor_ids
    }
    if duration_days.isdigit():
        updates['duration_days'] = int(duration_days)
    if product_id:
        updates['product_id'] = product_id

    success, res = update_cohort(cohort_id, updates)
    if product_id:
        updates['product_id'] = product_id

    success, res = update_cohort(cohort_id, updates)
    if success:
        flash(f"Cohort '{name}' details updated successfully!", "success")
    else:
        flash(res, "danger")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/delete/<cohort_id>', methods=['POST'])
@admin_required
def delete_existing_cohort(cohort_id):
    success, res = delete_cohort(cohort_id)
    if success:
        flash(res, "success")
    else:
        flash(res, "warning")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/complete/<cohort_id>', methods=['POST'])
@admin_required
def complete_existing_cohort(cohort_id):
    success, msg = complete_cohort(cohort_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/launch/<cohort_id>', methods=['POST'])
@admin_required
def launch_cohort_route(cohort_id):
    from services.cohort_service import launch_cohort
    success, msg = launch_cohort(cohort_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/upload-calendar/<cohort_id>', methods=['POST'])
@admin_required
def upload_cohort_calendar(cohort_id):
    if 'calendar_file' not in request.files:
        flash("No calendar file uploaded.", "warning")
        return redirect(url_for('admin.cohorts'))

    file = request.files['calendar_file']
    if not file or file.filename == '':
        flash("No file selected.", "warning")
        return redirect(url_for('admin.cohorts'))

    from services.cohort_service import update_cohort_calendar_from_csv
    success, msg = update_cohort_calendar_from_csv(cohort_id, file.stream)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('admin.cohorts'))


@admin_bp.route('/cohorts/sample-calendar-csv')
@admin_required
def download_sample_calendar_csv():
    from flask import Response

    sample_csv = """Day,Date,Title,Domain,Outcomes
Day 1,2026-08-20,Introduction to Engineering & Robotics,Embedded Systems,Practical application;Technical mindset
Day 2,2026-08-21,Microcontroller Programming & Sensors,Electronics,Hardware interfacing;Sensor calibration
Day 3,2026-08-22,CAD Modeling & Rapid Prototyping,Mechanical,3D Design;Prototyping basics
Day 4,2026-08-23,IoT Gateways & Cloud Connectivity,IoT & Cloud,Telemetry ingestion;Dashboard setup
Day 5,2026-08-24,AI/ML Model Training for Edge Devices,Artificial Intelligence,Edge Deployment;Model optimization
"""
    return Response(
        sample_csv,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=sample_cohort_calendar.csv"}
    )


# ----------------------------------------------------
# 5. REGISTERED STUDENTS PAGE (Product + Cohort Filters)
# ----------------------------------------------------
@admin_bp.route('/students')
@admin_required
def students():
    admin_user = get_current_user()
    all_students = users_db.find_all()
    selected_prod_id = get_selected_product_id()

    all_products = get_all_products()
    cohorts = get_all_cohorts(selected_prod_id if selected_prod_id != 'all' else None)

    # Filters
    search_query = request.args.get('q', '').strip().lower()
    filter_product = request.args.get('product', selected_prod_id).strip()
    selected_cohort = request.args.get('cohort', 'all').strip()
    selected_payment = request.args.get('payment', 'all').strip()
    selected_status = request.args.get('status', 'all').strip()
    page = int(request.args.get('page', 1))
    per_page = 12

    filtered = []
    for s in all_students:
        # Product filter
        if filter_product != 'all' and s.get('product_id') != filter_product:
            continue

        # Cohort filter
        if selected_cohort != 'all' and s.get('cohort_id') != selected_cohort:
            continue

        # Payment status filter
        if selected_payment != 'all' and (s.get('payment_status') or 'Pending').lower() != selected_payment.lower():
            continue

        # Student status filter
        st_status = s.get('student_status') or s.get('status') or 'Active'
        if selected_status != 'all' and st_status.lower() != selected_status.lower():
            continue

        # Search query filter
        if search_query:
            match_name = search_query in (s.get('full_name') or s.get('name') or '').lower()
            match_email = search_query in (s.get('email') or '').lower()
            match_reg = search_query in (s.get('registration_id') or '').lower()
            match_phone = search_query in (s.get('phone') or '').lower()
            if not (match_name or match_email or match_reg or match_phone):
                continue

        filtered.append(s)

    # Pagination
    total_count = len(filtered)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    start_idx = (page - 1) * per_page
    paginated_students = filtered[start_idx:start_idx + per_page]

    return render_template(
        'admin/students.html',
        admin=admin_user,
        students=paginated_students,
        products=all_products,
        cohorts=cohorts,
        search_query=search_query,
        filter_product=filter_product,
        selected_cohort=selected_cohort,
        selected_payment=selected_payment,
        selected_status=selected_status,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@admin_bp.route('/students/update-status/<user_id>', methods=['POST'])
@admin_required
def update_student_status(user_id):
    new_status = request.form.get('student_status', 'Active').strip()
    user = users_db.find_by_id(user_id)
    if user:
        users_db.update(user_id, {'student_status': new_status, 'status': new_status})
        flash(f"Student status updated to '{new_status}' for {user.get('full_name')}.", "success")
    else:
        flash("Student record not found.", "danger")
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/export')
@admin_required
def export_students_csv():
    students_list = users_db.find_all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Student ID', 'Registration ID', 'Full Name', 'Email', 'Phone',
        'Program Name', 'Cohort Name', 'Registration Status',
        'Payment Status', 'Enrollment Status', 'Student Status', 'Created At'
    ])
    
    for s in students_list:
        writer.writerow([
            s.get('id', ''),
            s.get('registration_id', 'N/A'),
            s.get('full_name') or s.get('name', ''),
            s.get('email', ''),
            s.get('phone', ''),
            s.get('product_name', 'Engineering Pack'),
            s.get('cohort_name', 'Cohort 1'),
            s.get('registration_status', 'Registered'),
            s.get('payment_status', 'Pending'),
            s.get('enrollment_status', 'Pending Onboarding'),
            s.get('student_status', 'Active'),
            s.get('created_at', '')
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=registered_students_report.csv'
    return response


# ----------------------------------------------------
# 6. DEDICATED PAYMENT APPROVALS PAGE
# ----------------------------------------------------
@admin_bp.route('/payments')
@admin_required
def payments():
    admin_user = get_current_user()
    selected_prod_id = get_selected_product_id()

    selected_status = request.args.get('status', 'all').strip().lower()
    search_query = request.args.get('q', '').strip().lower()
    page = int(request.args.get('page', 1))
    per_page = 10

    all_payments = []

    # 1. Fetch from enrollments.json (Multi-program enrollments)
    from services.enrollment_service import get_enrollment_by_id
    from services.json_database import JSONDatabase
    enrollments_db = JSONDatabase('enrollments')
    enrollments = enrollments_db.find_all()

    for enr in enrollments:
        full_enr = get_enrollment_by_id(enr['id'])
        if not full_enr:
            continue
        student = full_enr.get('student') or {}
        product = full_enr.get('product') or {}
        
        utr = full_enr.get('utr_number', '').strip()
        screenshot = full_enr.get('payment_screenshot', '').strip()
        raw_status = full_enr.get('payment_status', '').strip()

        # Only display students who have submitted payment proof (screenshot or UTR) or have an explicit status
        if not (utr or screenshot or raw_status in ['Proof Submitted', 'Confirmed', 'Paid', 'Approved', 'Rejected']):
            continue

        pay_status = raw_status if raw_status != 'Proof Submitted' else 'Pending'

        rec = {
            'id': full_enr['id'],
            'is_enrollment_record': True,
            'full_name': student.get('full_name') or student.get('name') or 'Student',
            'email': student.get('email', ''),
            'registration_id': full_enr.get('reference_id') or full_enr['id'],
            'product_id': full_enr.get('product_id', ''),
            'product_name': product.get('name', 'Engineering Pack'),
            'cohort_name': full_enr.get('cohort', {}).get('name', 'Active Cohort') if full_enr.get('cohort') else 'Default Cohort',
            'utr_number': utr,
            'payment_screenshot': screenshot,
            'payment_amount': product.get('price', 3500),
            'payment_status': pay_status,
            'created_at': full_enr.get('created_at', '')
        }
        all_payments.append(rec)

    # 2. Fetch legacy users_db records if not already in enrollments
    all_students = users_db.find_all()
    for s in all_students:
        if any(p['email'] == s.get('email') and p['product_id'] == s.get('product_id') for p in all_payments):
            continue

        utr = s.get('utr_number', '').strip()
        screenshot = s.get('payment_screenshot', '').strip()
        raw_status = s.get('payment_status', '').strip()

        # Filter out raw signed-in users who haven't submitted payment details
        if not (utr or screenshot or raw_status in ['Proof Submitted', 'Confirmed', 'Paid', 'Approved', 'Rejected']):
            continue

        rec = {
            'id': s['id'],
            'is_enrollment_record': False,
            'full_name': s.get('full_name') or s.get('name') or 'Student',
            'email': s.get('email', ''),
            'registration_id': s.get('registration_id') or s['id'],
            'product_id': s.get('product_id', ''),
            'product_name': s.get('product_name', 'Engineering Pack'),
            'cohort_name': 'Cohort 1',
            'utr_number': utr,
            'payment_screenshot': screenshot,
            'payment_amount': s.get('payment_amount', 3500),
            'payment_status': raw_status if raw_status != 'Proof Submitted' else 'Pending',
            'created_at': s.get('created_at', '')
        }
        all_payments.append(rec)

    filtered = []
    for p in all_payments:
        if selected_prod_id != 'all' and p.get('product_id') != selected_prod_id:
            continue

        p_status = p.get('payment_status', 'Pending')
        if selected_status != 'all':
            if selected_status == 'pending' and p_status not in ['Pending', 'Proof Submitted']:
                continue
            elif selected_status == 'approved' and p_status not in ['Approved', 'Paid', 'Confirmed']:
                continue
            elif selected_status == 'rejected' and p_status != 'Rejected':
                continue

        if search_query:
            match_name = search_query in (p.get('full_name') or '').lower()
            match_email = search_query in (p.get('email') or '').lower()
            match_reg = search_query in (p.get('registration_id') or '').lower()
            match_utr = search_query in (p.get('utr_number') or '').lower()
            if not (match_name or match_email or match_reg or match_utr):
                continue
                
        filtered.append(p)

    filtered.sort(key=lambda x: (0 if x.get('payment_status') in ['Pending', 'Proof Submitted'] else 1, x.get('created_at', '')))

    total_count = len(filtered)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    start_idx = (page - 1) * per_page
    paginated_payments = filtered[start_idx:start_idx + per_page]

    status_counts = {
        'all': len(all_payments),
        'pending': len([p for p in all_payments if p.get('payment_status') in ['Pending', 'Proof Submitted']]),
        'approved': len([p for p in all_payments if p.get('payment_status') in ['Approved', 'Paid', 'Confirmed']]),
        'rejected': len([p for p in all_payments if p.get('payment_status') == 'Rejected'])
    }

    return render_template(
        'admin/payments.html',
        admin=admin_user,
        payments=paginated_payments,
        status_counts=status_counts,
        selected_status=selected_status,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@admin_bp.route('/payment/approve/<user_id>', methods=['POST'])
@admin_required
def approve_payment(user_id):
    admin_user = get_current_user()
    admin_remarks = request.form.get('admin_remarks', '').strip()

    if user_id.startswith('enr_'):
        from services.enrollment_service import verify_enrollment_payment_admin
        success, res = verify_enrollment_payment_admin(user_id, admin_id=admin_user['id'], action='approve')
    else:
        success, res = approve_student_payment(user_id, admin_remarks=admin_remarks)

    if success:
        flash(f"Payment approved! {res}", "success")
    else:
        flash(res, "danger")
    return redirect(url_for('admin.payments'))


@admin_bp.route('/payment/reject/<user_id>', methods=['POST'])
@admin_required
def reject_payment(user_id):
    admin_user = get_current_user()
    admin_remarks = request.form.get('admin_remarks', '').strip()

    if user_id.startswith('enr_'):
        from services.enrollment_service import verify_enrollment_payment_admin
        success, res = verify_enrollment_payment_admin(user_id, admin_id=admin_user['id'], action='reject')
    else:
        success, res = reject_student_payment(user_id, admin_remarks=admin_remarks)

    if success:
        flash("Payment rejected.", "info")
    else:
        flash(res, "danger")
    return redirect(url_for('admin.payments'))


# ----------------------------------------------------
# 7. PRODUCT-SPECIFIC CURRICULUM MANAGEMENT
# ----------------------------------------------------
@admin_bp.route('/curriculum', methods=['GET'])
@admin_required
def curriculum():
    admin_user = get_current_user()
    selected_prod_id = get_selected_product_id()

    if selected_prod_id != 'all':
        phases = curriculum_db.find_all(lambda c: c.get('product_id') == selected_prod_id)
    else:
        phases = curriculum_db.find_all()

    phases.sort(key=lambda x: int(x.get('phase_number', 0)))
    all_prods = get_all_products()

    return render_template(
        'admin/curriculum.html',
        admin=admin_user,
        phases=phases,
        products=all_prods,
        selected_prod_id=selected_prod_id
    )


@admin_bp.route('/curriculum/add', methods=['POST'])
@admin_required
def add_curriculum_phase():
    product_id = request.form.get('product_id', '').strip()
    phase_num = request.form.get('phase_number', '').strip()
    title = request.form.get('title', '').strip()
    day_range = request.form.get('day_range', '').strip()
    domain = request.form.get('domain', '').strip()
    icon = request.form.get('icon', 'layers').strip()
    description = request.form.get('description', '').strip()

    if not product_id or product_id == 'all':
        default_p = get_default_product()
        product_id = default_p.get('id') if default_p else 'prod_engpack'

    if title and phase_num.isdigit():
        new_phase = {
            "id": f"phase_{uuid.uuid4().hex[:6]}",
            "product_id": product_id,
            "phase_number": int(phase_num),
            "title": title,
            "day_range": day_range or f"Phase {phase_num}",
            "domain": domain or "Domain",
            "icon": icon or "layers",
            "description": description
        }
        curriculum_db.create(new_phase)
        flash(f"Phase {phase_num}: '{title}' added to curriculum successfully!", "success")
    else:
        flash("Phase Number and Title are required.", "danger")
    return redirect(url_for('admin.curriculum'))


@admin_bp.route('/curriculum/edit/<phase_id>', methods=['POST'])
@admin_required
def edit_curriculum_phase(phase_id):
    product_id = request.form.get('product_id', '').strip()
    phase_num = request.form.get('phase_number', '').strip()
    title = request.form.get('title', '').strip()
    day_range = request.form.get('day_range', '').strip()
    domain = request.form.get('domain', '').strip()
    icon = request.form.get('icon', 'layers').strip()
    description = request.form.get('description', '').strip()

    updates = {
        "title": title,
        "day_range": day_range,
        "domain": domain,
        "icon": icon,
        "description": description
    }
    if product_id:
        updates["product_id"] = product_id
    if phase_num.isdigit():
        updates["phase_number"] = int(phase_num)

    curriculum_db.update(phase_id, updates)
    flash(f"Curriculum phase '{title}' updated successfully!", "success")
    return redirect(url_for('admin.curriculum'))


@admin_bp.route('/curriculum/delete/<phase_id>', methods=['POST'])
@admin_required
def delete_curriculum_phase(phase_id):
    curriculum_db.delete(phase_id)
    flash("Curriculum phase deleted.", "info")
    return redirect(url_for('admin.curriculum'))


# ----------------------------------------------------
# 8. PRODUCT & COHORT PROJECTS MANAGEMENT
# ----------------------------------------------------
@admin_bp.route('/projects', methods=['GET'])
@admin_required
def projects():
    admin_user = get_current_user()
    selected_prod_id = get_selected_product_id()

    if selected_prod_id != 'all':
        all_projects = projects_db.find_all(lambda p: p.get('product_id') == selected_prod_id)
    else:
        all_projects = projects_db.find_all()

    all_prods = get_all_products()
    cohorts = get_all_cohorts(selected_prod_id if selected_prod_id != 'all' else None)

    return render_template(
        'admin/projects.html',
        admin=admin_user,
        projects=all_projects,
        products=all_prods,
        cohorts=cohorts,
        selected_prod_id=selected_prod_id
    )


@admin_bp.route('/projects/add', methods=['POST'])
@admin_required
def add_project():
    product_id = request.form.get('product_id', '').strip()
    cohort_id = request.form.get('cohort_id', 'all').strip()
    name = request.form.get('name', '').strip()
    domain = request.form.get('domain', '').strip()
    icon = request.form.get('icon', 'layers').strip()
    description = request.form.get('description', '').strip()
    outcome = request.form.get('outcome', '').strip()

    if not product_id or product_id == 'all':
        default_p = get_default_product()
        product_id = default_p.get('id') if default_p else 'prod_engpack'

    if name:
        new_proj = {
            "id": f"proj_{uuid.uuid4().hex[:6]}",
            "product_id": product_id,
            "cohort_id": cohort_id or "all",
            "assigned_student_ids": [],
            "name": name,
            "domain": domain or "Engineering",
            "icon": icon or "layers",
            "description": description,
            "outcome": outcome
        }
        projects_db.create(new_proj)
        flash(f"Project '{name}' added successfully!", "success")
    else:
        flash("Project Name is required.", "danger")
    return redirect(url_for('admin.projects'))


@admin_bp.route('/projects/edit/<project_id>', methods=['POST'])
@admin_required
def edit_project(project_id):
    product_id = request.form.get('product_id', '').strip()
    cohort_id = request.form.get('cohort_id', 'all').strip()
    name = request.form.get('name', '').strip()
    domain = request.form.get('domain', '').strip()
    icon = request.form.get('icon', 'layers').strip()
    description = request.form.get('description', '').strip()
    outcome = request.form.get('outcome', '').strip()

    updates = {
        "name": name,
        "domain": domain,
        "icon": icon,
        "description": description,
        "outcome": outcome
    }
    if product_id:
        updates["product_id"] = product_id
    if cohort_id:
        updates["cohort_id"] = cohort_id

    projects_db.update(project_id, updates)
    flash(f"Project '{name}' updated successfully!", "success")
    return redirect(url_for('admin.projects'))


@admin_bp.route('/projects/delete/<project_id>', methods=['POST'])
@admin_required
def delete_project(project_id):
    projects_db.delete(project_id)
    flash("Project deleted.", "info")
    return redirect(url_for('admin.projects'))


# ----------------------------------------------------
# 9. PRODUCT-SPECIFIC ANNOUNCEMENTS
# ----------------------------------------------------
@admin_bp.route('/announcements', methods=['GET', 'POST'])
@admin_required
def announcements():
    admin_user = get_current_user()
    selected_prod_id = get_selected_product_id()

    if request.method == 'POST':
        product_id = request.form.get('product_id', '').strip()
        selected_cohorts = request.form.getlist('cohort_ids')
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        content = request.form.get('content', '').strip()

        if not product_id or product_id == 'all':
            default_p = get_default_product()
            product_id = default_p.get('id') if default_p else 'prod_engpack'

        if title and content:
            ann_entry = {
                'id': f"ann_{uuid.uuid4().hex[:6]}",
                'product_id': product_id,
                'cohort_ids': selected_cohorts if selected_cohorts else ['all'],
                'title': title,
                'category': category or 'General',
                'content': content,
                'date': '2026-08-17'
            }
            announcements_db.create(ann_entry)
            flash("Product Announcement posted successfully!", "success")
            return redirect(url_for('admin.announcements'))

    if selected_prod_id != 'all':
        all_announcements = announcements_db.find_all(lambda a: a.get('product_id') == selected_prod_id)
    else:
        all_announcements = announcements_db.find_all()

    all_prods = get_all_products()
    cohorts = get_all_cohorts(selected_prod_id if selected_prod_id != 'all' else None)

    return render_template(
        'admin/announcements.html',
        admin=admin_user,
        announcements=all_announcements,
        products=all_prods,
        cohorts=cohorts,
        selected_prod_id=selected_prod_id
    )


@admin_bp.route('/contacts')
@admin_required
def contacts():
    admin_user = get_current_user()
    all_contacts = contacts_db.find_all()
    return render_template('admin/contacts.html', admin=admin_user, contacts=all_contacts)


# ----------------------------------------------------
# 10. GLOBAL SYSTEM SETTINGS (Company & Support Info)
# ----------------------------------------------------
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    admin_user = get_current_user()
    settings_records = settings_db.read_all()
    current_settings = settings_records[0] if isinstance(settings_records, list) and len(settings_records) > 0 else {}

    if request.method == 'POST':
        company = request.form.get('company', '').strip()
        support_email = request.form.get('support_email', '').strip()
        support_phone = request.form.get('support_phone', '').strip()
        currency_symbol = request.form.get('currency_symbol', '₹').strip()

        updated_settings = {
            'company': company or current_settings.get('company', 'AIVONTRAA Automation Pvt. Ltd.'),
            'currency_symbol': currency_symbol or '₹',
            'support_email': support_email or current_settings.get('support_email', 'hello.aivontraa@gmail.com'),
            'support_phone': support_phone or current_settings.get('support_phone', '+91 9876543210')
        }

        settings_db.write_all([updated_settings])
        flash("Global platform settings updated successfully!", "success")
        current_settings = updated_settings

    return render_template('admin/settings.html', admin=admin_user, settings=current_settings)


@admin_bp.route('/feedback')
@admin_required
def feedback():
    admin_user = get_current_user()
    from services.review_service import get_all_reviews
    reviews = get_all_reviews()
    return render_template('admin/feedback.html', admin=admin_user, reviews=reviews)
