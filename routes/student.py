from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from services.auth_service import login_required, get_current_user
from services.json_database import JSONDatabase
from services.product_service import get_product_by_id

student_bp = Blueprint('student', __name__, url_prefix='/student')

curriculum_db = JSONDatabase('curriculum')
projects_db = JSONDatabase('projects')
announcements_db = JSONDatabase('announcements')
users_db = JSONDatabase('users')


def student_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'student':
            flash("Student access required.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_student_scoped_data(user: dict):
    from services.enrollment_service import get_student_enrollments
    from services.cohort_service import get_cohort_by_id

    enrollments = get_student_enrollments(user['id'])
    confirmed_enrollments = [e for e in enrollments if e.get('payment_status') in ['Confirmed', 'Paid', 'Approved']]

    active_prod_id = session.get('active_product_id')
    if not active_prod_id and confirmed_enrollments:
        active_prod_id = confirmed_enrollments[0].get('product_id')
    if not active_prod_id:
        active_prod_id = user.get('product_id', 'prod_engpack')

    matched_enr = next((e for e in confirmed_enrollments if e.get('product_id') == active_prod_id), None)
    cohort_id = matched_enr.get('cohort_id') if matched_enr and matched_enr.get('cohort_id') else user.get('cohort_id', '')

    cohort = get_cohort_by_id(cohort_id) if cohort_id else None

    # Filter curriculum phases
    phases = curriculum_db.find_all(lambda c: c.get('product_id') == active_prod_id)
    phases.sort(key=lambda x: int(x.get('phase_number', 0)))

    # Filter projects
    all_projects = projects_db.read_all()
    if cohort and cohort.get('assigned_project_ids'):
        assigned_pids = cohort.get('assigned_project_ids', [])
        projects = [p for p in all_projects if p.get('id') in assigned_pids]
    else:
        projects = [p for p in all_projects if p.get('product_id') == active_prod_id or not p.get('product_id')]

    # Filter mentors
    mentors_db = JSONDatabase('mentors')
    all_mentors = mentors_db.read_all()
    if cohort and cohort.get('assigned_mentor_ids'):
        assigned_mids = cohort.get('assigned_mentor_ids', [])
        mentors = [m for m in all_mentors if m.get('id') in assigned_mids]
    else:
        mentors = all_mentors

    all_anns = announcements_db.find_all()
    announcements = []
    for a in all_anns:
        if a.get('product_id') and a.get('product_id') != active_prod_id:
            continue
        c_ids = a.get('cohort_ids') or []
        if 'all' in c_ids or (cohort_id and cohort_id in c_ids) or not c_ids:
            announcements.append(a)

    product = get_product_by_id(active_prod_id)

    return {
        'phases': phases,
        'projects': projects,
        'mentors': mentors,
        'announcements': announcements,
        'product': product,
        'cohort': cohort,
        'active_product_id': active_prod_id,
        'enrollments': confirmed_enrollments,
        'matched_enrollment': matched_enr
    }


@student_bp.route('/switch-program/<product_id>')
@student_required
def switch_program(product_id):
    session['active_product_id'] = product_id
    flash("Switched active program view.", "info")
    return redirect(request.referrer or url_for('student.dashboard'))


@student_bp.route('/dashboard')
@student_required
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    from services.enrollment_service import has_confirmed_enrollment, get_student_enrollments
    if not has_confirmed_enrollment(user['id']):
        enrollments = get_student_enrollments(user['id'])
        if enrollments:
            pending = [e for e in enrollments if e.get('payment_status') in ['Proof Submitted', 'Pending']]
            rejected = [e for e in enrollments if e.get('payment_status') == 'Rejected']
            if pending:
                flash("Your payment proof is currently PENDING VERIFICATION by our admissions team. Your dashboard will open as soon as payment is confirmed by admin.", "warning")
                return redirect(url_for('auth.payment_success_page', enrollment_id=pending[0]['id']))
            elif rejected:
                flash("Your payment proof was rejected. Please resubmit your payment proof to enroll.", "danger")
                return redirect(url_for('auth.enroll_program', product_id=rejected[0]['product_id']))

        flash("Please enroll in a program and complete payment verification to access your dashboard.", "info")
        return redirect(url_for('public.programs_catalog'))

    data = get_student_scoped_data(user)
    cohort = data['cohort']
    timetable = cohort.get('timetable') if cohort and cohort.get('timetable') else []

    return render_template(
        'student/dashboard.html',
        user=user,
        phases=data['phases'],
        projects=data['projects'],
        announcements=data['announcements'],
        product=data['product'],
        enrollments=data['enrollments'],
        cohort=cohort,
        timetable=timetable,
        active_product_id=data['active_product_id']
    )


@student_bp.route('/calendar')
@student_required
def calendar():
    user = get_current_user()
    data = get_student_scoped_data(user)
    cohort = data['cohort']
    timetable = cohort.get('timetable') if cohort and cohort.get('timetable') else []
    return render_template(
        'student/calendar.html',
        user=user,
        cohort=cohort,
        timetable=timetable,
        product=data['product'],
        enrollments=data['enrollments'],
        active_product_id=data['active_product_id']
    )


@student_bp.route('/journey')
@student_required
def journey():
    user = get_current_user()
    data = get_student_scoped_data(user)
    cohort = data['cohort']
    timetable = cohort.get('timetable') if cohort and cohort.get('timetable') else []
    return render_template(
        'student/calendar.html',
        user=user,
        cohort=cohort,
        timetable=timetable,
        product=data['product'],
        enrollments=data['enrollments'],
        active_product_id=data['active_product_id']
    )


@student_bp.route('/projects')
@student_required
def projects():
    user = get_current_user()
    data = get_student_scoped_data(user)
    student_projects = data['projects']
    cohort = data['cohort']
    cohort_id = cohort.get('id') if cohort else ''

    from services.submission_service import get_student_submission_for_project
    for p in student_projects:
        sub = get_student_submission_for_project(user['id'], p['id'], cohort_id)
        p['submission'] = sub
        p['is_submitted'] = sub is not None
        p['submission_status'] = sub.get('status') if sub else None

    return render_template(
        'student/projects.html',
        user=user,
        projects=student_projects,
        product=data['product'],
        cohort=cohort,
        enrollments=data['enrollments'],
        active_product_id=data['active_product_id']
    )


@student_bp.route('/projects/<project_id>/submit', methods=['POST'])
@student_required
def submit_project(project_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    data = get_student_scoped_data(user)
    cohort = data['cohort']
    cohort_id = cohort.get('id') if cohort else ''
    product_id = data['active_product_id']

    target_project = next((p for p in data['projects'] if p['id'] == project_id), None)
    if not target_project:
        target_project = projects_db.find_by_id(project_id)

    if not target_project:
        flash("Project not found.", "danger")
        return redirect(url_for('student.projects'))

    # ACCESS CONTROL REQUIREMENT: Direct URL or API calls must NOT bypass project status
    p_status = target_project.get('status', 'Locked')
    if p_status != 'Open':
        flash("Access Denied: Project not yet opened by mentor.", "danger")
        return redirect(url_for('student.projects')), 403

    github_url = request.form.get('github_url', '').strip()
    from services.submission_service import submit_project_github_url
    success, msg, _ = submit_project_github_url(
        student_id=user['id'],
        product_id=product_id,
        cohort_id=cohort_id,
        project_id=project_id,
        github_url=github_url
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('student.projects'))


@student_bp.route('/certificates')
@student_required
def certificates():
    user = get_current_user()
    data = get_student_scoped_data(user)
    return render_template(
        'student/certificates.html',
        user=user,
        product=data['product'],
        cohort=data['cohort'],
        enrollments=data['enrollments'],
        active_product_id=data['active_product_id']
    )


@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    user = get_current_user()
    data = get_student_scoped_data(user)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        college = request.form.get('college', '').strip()
        user_type = request.form.get('user_type', '').strip()
        branch = request.form.get('branch', '').strip()
        academic_year = request.form.get('academic_year', '').strip() or request.form.get('year', '').strip()
        github_url = request.form.get('github_url', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        portfolio_url = request.form.get('portfolio_url', '').strip()

        updates = {
            'full_name': full_name or user.get('full_name'),
            'phone': phone or user.get('phone'),
            'college': college or user.get('college'),
            'user_type': user_type or user.get('user_type'),
            'branch': branch or user.get('branch'),
            'academic_year': academic_year or user.get('academic_year'),
            'year': academic_year or user.get('year'),
            'github_url': github_url,
            'linkedin_url': linkedin_url,
            'portfolio_url': portfolio_url
        }
        updated_user = users_db.update(user['id'], updates)
        if updated_user:
            session['name'] = updated_user.get('full_name')
            flash("Profile details & social links updated successfully!", "success")
            user = updated_user
        else:
            flash("Failed to update profile details.", "danger")

    return render_template(
        'student/profile.html',
        user=user,
        product=data['product'],
        cohort=data['cohort'],
        enrollments=data['enrollments'],
        active_product_id=data['active_product_id']
    )


@student_bp.route('/feedback', methods=['GET', 'POST'])
@student_required
def feedback():
    user = get_current_user()
    data = get_student_scoped_data(user)
    cohort = data['cohort']
    mentors = data['mentors']
    product = data['product']

    from services.review_service import create_review, get_reviews_for_student
    if request.method == 'POST':
        scope = request.form.get('scope', 'mentor').strip()
        mentor_id = request.form.get('mentor_id', '').strip()
        rating = int(request.form.get('rating', 5))
        category = request.form.get('category', 'General Feedback').strip()
        comment = request.form.get('comment', '').strip()
        is_anonymous = request.form.get('is_anonymous') == 'true' or request.form.get('is_anonymous') == 'on'

        mentor_name = ""
        if scope == 'mentor' and mentor_id:
            matched_mentor = next((m for m in mentors if m['id'] == mentor_id), None)
            if matched_mentor:
                mentor_name = matched_mentor.get('full_name') or matched_mentor.get('name', '')

        create_review(
            student_id=user['id'],
            student_name=user.get('full_name') or user.get('name', 'Student'),
            student_email=user.get('email', ''),
            program_id=product.get('id', '') if product else '',
            program_name=product.get('name', '') if product else '',
            cohort_id=cohort.get('id', '') if cohort else '',
            cohort_name=cohort.get('name', '') if cohort else '',
            scope=scope,
            mentor_id=mentor_id if scope == 'mentor' else '',
            mentor_name=mentor_name if scope == 'mentor' else '',
            rating=rating,
            category=category,
            comment=comment,
            is_anonymous=is_anonymous
        )
        flash("Thank you! Your feedback review has been submitted successfully.", "success")
        return redirect(url_for('student.feedback'))

    my_reviews = get_reviews_for_student(user['id'])
    return render_template(
        'student/feedback.html',
        user=user,
        mentors=mentors,
        cohort=cohort,
        product=product,
        my_reviews=my_reviews,
        enrollments=data['enrollments'],
        active_product_id=data['active_product_id']
    )
