from flask import Blueprint, render_template, request, flash, redirect, url_for
from services.auth_service import admin_required, get_current_user, approve_student_payment, reject_student_payment
from services.json_database import JSONDatabase

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

users_db = JSONDatabase('users')
curriculum_db = JSONDatabase('curriculum')
projects_db = JSONDatabase('projects')
announcements_db = JSONDatabase('announcements')
contacts_db = JSONDatabase('contacts')
mentors_db = JSONDatabase('mentors')
settings_db = JSONDatabase('settings')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    admin_user = get_current_user()
    students = users_db.find_all()
    active_students = [s for s in students if s.get('status') == 'Active']
    completed_students = [s for s in students if s.get('status') == 'Completed']
    projects = projects_db.find_all()
    enquiries = contacts_db.find_all()
    pending_payments = [s for s in students if s.get('payment_screenshot') or s.get('utr_number')]

    stats = {
        'total_students': len(students),
        'active_students': len(active_students),
        'completed_students': len(completed_students),
        'total_projects': len(projects),
        'pending_payments': len(pending_payments),
        'total_enquiries': len(enquiries)
    }

    return render_template(
        'admin/dashboard.html',
        admin=admin_user,
        stats=stats,
        recent_students=students[:5],
        pending_payments=pending_payments,
        recent_enquiries=enquiries[:5]
    )


@admin_bp.route('/payment/approve/<user_id>', methods=['POST'])
@admin_required
def approve_payment(user_id):
    success, res = approve_student_payment(user_id)
    if success:
        flash("Student payment approved and enrollment activated!", "success")
    else:
        flash(res, "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/payment/reject/<user_id>', methods=['POST'])
@admin_required
def reject_payment(user_id):
    success, res = reject_student_payment(user_id)
    if success:
        flash("Student payment marked as unpaid.", "info")
    else:
        flash(res, "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/students')
@admin_required
def students():
    admin_user = get_current_user()
    all_students = users_db.find_all()
    return render_template('admin/students.html', admin=admin_user, students=all_students)


@admin_bp.route('/curriculum')
@admin_required
def curriculum():
    admin_user = get_current_user()
    phases = curriculum_db.find_all()
    return render_template('admin/curriculum.html', admin=admin_user, phases=phases)


@admin_bp.route('/projects')
@admin_required
def projects():
    admin_user = get_current_user()
    all_projects = projects_db.find_all()
    return render_template('admin/projects.html', admin=admin_user, projects=all_projects)


@admin_bp.route('/announcements', methods=['GET', 'POST'])
@admin_required
def announcements():
    admin_user = get_current_user()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        content = request.form.get('content', '').strip()

        if title and content:
            ann_entry = {
                'title': title,
                'category': category or 'General',
                'content': content,
                'date': '2026-08-14'
            }
            announcements_db.create(ann_entry)
            flash("Announcement posted successfully!", "success")
            return redirect(url_for('admin.announcements'))

    all_announcements = announcements_db.find_all()
    return render_template('admin/announcements.html', admin=admin_user, announcements=all_announcements)


@admin_bp.route('/contacts')
@admin_required
def contacts():
    admin_user = get_current_user()
    all_contacts = contacts_db.find_all()
    return render_template('admin/contacts.html', admin=admin_user, contacts=all_contacts)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    admin_user = get_current_user()
    settings_records = settings_db.read_all()
    current_settings = settings_records[0] if isinstance(settings_records, list) and len(settings_records) > 0 else {}

    if request.method == 'POST':
        program_name = request.form.get('program_name', '').strip()
        tagline = request.form.get('tagline', '').strip()
        company = request.form.get('company', '').strip()
        price = request.form.get('price', '').strip()
        support_email = request.form.get('support_email', '').strip()
        support_phone = request.form.get('support_phone', '').strip()

        updated_settings = {
            'program_name': program_name or current_settings.get('program_name'),
            'tagline': tagline or current_settings.get('tagline'),
            'company': company or current_settings.get('company'),
            'price': int(price) if price.isdigit() else current_settings.get('price', 3500),
            'currency_symbol': '₹',
            'duration_days': 45,
            'support_email': support_email or current_settings.get('support_email'),
            'support_phone': support_phone or current_settings.get('support_phone')
        }

        settings_db.write_all([updated_settings])
        flash("Platform settings updated successfully!", "success")
        current_settings = updated_settings

    return render_template('admin/settings.html', admin=admin_user, settings=current_settings)
