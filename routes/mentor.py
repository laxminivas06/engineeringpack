import os
import uuid
import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from werkzeug.utils import secure_filename
from services.auth_service import mentor_required, get_current_user
from services.mentor_service import (
    get_mentor_by_id, update_mentor_self_profile, get_cohorts_for_mentor,
    get_projects_for_mentor, process_mentor_links
)
from services.product_service import get_all_products, get_product_by_id
from services.cohort_service import get_cohort_by_id, log_activity
from services.submission_service import (
    get_submissions_for_project, get_submissions_for_cohort, review_submission
)
from services.json_database import JSONDatabase

mentor_bp = Blueprint('mentor', __name__, url_prefix='/mentor')

projects_db = JSONDatabase('projects')
announcements_db = JSONDatabase('announcements')
users_db = JSONDatabase('users')
cohorts_db = JSONDatabase('cohorts')


def allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}


@mentor_bp.route('/dashboard')
@mentor_required
def dashboard():
    mentor = get_current_user()
    if not mentor:
        return redirect(url_for('auth.login'))

    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    active_cohorts = [c for c in assigned_cohorts if c.get('status') == 'Active']
    upcoming_cohorts = [c for c in assigned_cohorts if c.get('status') == 'Upcoming']
    completed_cohorts = [c for c in assigned_cohorts if c.get('status') == 'Completed']

    # Get distinct assigned programs
    assigned_prod_ids = list({c.get('product_id') for c in assigned_cohorts if c.get('product_id')})
    all_products = get_all_products()
    assigned_programs = [p for p in all_products if p['id'] in assigned_prod_ids or mentor['id'] in p.get('assigned_mentor_ids', [])]

    # Get assigned projects
    assigned_projects = get_projects_for_mentor(mentor['id'])

    # Get all student submissions for assigned cohorts
    cohort_ids = {c['id'] for c in assigned_cohorts}
    submissions_db = JSONDatabase('submissions')
    all_submissions = submissions_db.find_all(lambda s: s.get('cohort_id') in cohort_ids)
    pending_submissions = [s for s in all_submissions if s.get('status') in ['Submitted', 'Under Review']]

    # Relevant Announcements
    all_anns = announcements_db.find_all()
    announcements = []
    for a in all_anns:
        c_ids = a.get('cohort_ids') or []
        if 'all' in c_ids or any(cid in cohort_ids for cid in c_ids) or a.get('product_id') in assigned_prod_ids:
            announcements.append(a)

    return render_template(
        'mentor/dashboard.html',
        mentor=mentor,
        assigned_programs=assigned_programs,
        assigned_cohorts=assigned_cohorts,
        active_cohorts=active_cohorts,
        upcoming_cohorts=upcoming_cohorts,
        completed_cohorts=completed_cohorts,
        assigned_projects=assigned_projects,
        all_submissions=all_submissions,
        pending_submissions=pending_submissions,
        announcements=announcements
    )


@mentor_bp.route('/cohorts')
@mentor_required
def cohorts():
    mentor = get_current_user()
    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    all_users = users_db.find_all()

    for c in assigned_cohorts:
        cid = c['id']
        c['students'] = [u for u in all_users if u.get('cohort_id') == cid]
        c['student_count'] = len(c['students'])

    return render_template(
        'mentor/cohorts.html',
        mentor=mentor,
        cohorts=assigned_cohorts
    )


@mentor_bp.route('/projects')
@mentor_required
def projects():
    mentor = get_current_user()
    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    assigned_projects = get_projects_for_mentor(mentor['id'])
    submissions_db = JSONDatabase('submissions')

    for p in assigned_projects:
        pid = p['id']
        p_submissions = submissions_db.find_all(lambda s: str(s.get('project_id')) == str(pid))
        p['submission_count'] = len(p_submissions)
        p['pending_count'] = len([s for s in p_submissions if s.get('status') in ['Submitted', 'Under Review']])

    return render_template(
        'mentor/projects.html',
        mentor=mentor,
        projects=assigned_projects,
        cohorts=assigned_cohorts
    )


@mentor_bp.route('/projects/<project_id>/toggle-status', methods=['POST'])
@mentor_required
def toggle_project_status(project_id):
    mentor = get_current_user()
    project = projects_db.find_by_id(project_id)
    if not project:
        flash("Project record not found.", "danger")
        return redirect(url_for('mentor.projects'))

    # Verify mentor permission for project's cohort or program
    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    mentor_cohort_ids = {c['id'] for c in assigned_cohorts}

    p_cohort_id = project.get('cohort_id')
    has_permission = False
    if p_cohort_id == 'all' or p_cohort_id in mentor_cohort_ids:
        has_permission = True
    else:
        for c in assigned_cohorts:
            if project['id'] in c.get('assigned_project_ids', []):
                has_permission = True
                break

    if not has_permission:
        flash("Permission denied: You can only control projects for cohorts assigned to you.", "danger")
        return redirect(url_for('mentor.projects'))

    target_status = request.form.get('status', '').strip()
    if target_status not in ['Open', 'Locked', 'Closed']:
        current_st = project.get('status', 'Locked')
        target_status = 'Open' if current_st != 'Open' else 'Closed'

    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    updates = {
        'status': target_status,
        'opened_by_mentor_id': mentor['id'],
        'opened_at': now_iso if target_status == 'Open' else project.get('opened_at', '')
    }

    projects_db.update(project_id, updates)
    log_activity(
        "project_status_toggled",
        f"Project '{project.get('name')}' marked as {target_status}",
        f"Mentor {mentor.get('full_name')} changed project access status to '{target_status}'."
    )

    flash(f"Project '{project.get('name')}' is now {target_status.upper()} for student access!", "success")
    return redirect(request.referrer or url_for('mentor.projects'))


@mentor_bp.route('/projects/<project_id>/submissions')
@mentor_required
def project_submissions(project_id):
    mentor = get_current_user()
    project = projects_db.find_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('mentor.projects'))

    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    cohort_ids = {c['id'] for c in assigned_cohorts}

    submissions_db = JSONDatabase('submissions')
    submissions = submissions_db.find_all(
        lambda s: str(s.get('project_id')) == str(project_id) and (s.get('cohort_id') in cohort_ids or not cohort_ids)
    )

    all_users = users_db.find_all()
    # Map student names/info
    user_map = {u['id']: u for u in all_users}
    for sub in submissions:
        sid = sub.get('student_id')
        if sid in user_map:
            sub['student_info'] = user_map[sid]

    return render_template(
        'mentor/project_submissions.html',
        mentor=mentor,
        project=project,
        submissions=submissions,
        cohorts=assigned_cohorts
    )


@mentor_bp.route('/submissions/<submission_id>/review', methods=['POST'])
@mentor_required
def review_submission_route(submission_id):
    mentor = get_current_user()
    status = request.form.get('status', 'Reviewed').strip()
    feedback = request.form.get('feedback', '').strip()

    success, msg, updated = review_submission(
        submission_id=submission_id,
        status=status,
        feedback=feedback,
        mentor_id=mentor['id']
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(request.referrer or url_for('mentor.projects'))


@mentor_bp.route('/profile', methods=['GET', 'POST'])
@mentor_required
def profile():
    mentor = get_current_user()
    if not mentor:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        updates = {
            'full_name': request.form.get('full_name', '').strip(),
            'professional_title': request.form.get('professional_title', '').strip(),
            'domain': request.form.get('domain', '').strip(),
            'short_bio': request.form.get('short_bio', '').strip(),
            'detailed_about': request.form.get('detailed_about', '').strip(),
            'experience': request.form.get('experience', '').strip(),
            'skills': request.form.get('skills', '').strip(),
            'education_certifications': request.form.get('education_certifications', '').strip(),
            'website': request.form.get('website', '').strip(),
            'github': request.form.get('github', '').strip(),
            'linkedin': request.form.get('linkedin', '').strip(),
            'twitter': request.form.get('twitter', '').strip(),
            'other_links': request.form.get('other_links', '').strip()
        }

        # Parse dynamic social links
        platforms = request.form.getlist('link_platform[]')
        urls = request.form.getlist('link_url[]')
        social_links = []
        for p, u in zip(platforms, urls):
            if u.strip():
                social_links.append({'platform': p.strip() or 'Link', 'url': u.strip()})
        if social_links:
            updates['social_links'] = social_links

        # Profile Photo upload
        photo_file = request.files.get('profile_photo')
        if photo_file and photo_file.filename and allowed_photo_file(photo_file.filename):
            ext = photo_file.filename.rsplit('.', 1)[1].lower()
            filename = f"mentor_{uuid.uuid4().hex[:6]}.{ext}"
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'mentors')
            os.makedirs(upload_dir, exist_ok=True)
            photo_file.save(os.path.join(upload_dir, filename))
            updates['profile_photo_url'] = f"/static/uploads/mentors/{filename}"

        success, res = update_mentor_self_profile(mentor['id'], updates)
        if success:
            flash("Your mentor profile details have been updated successfully!", "success")
            mentor = res
        else:
            flash(str(res), "danger")

    mentor['processed_links'] = process_mentor_links(mentor)
    return render_template('mentor/profile.html', mentor=mentor)


@mentor_bp.route('/announcements', methods=['GET', 'POST'])
@mentor_required
def announcements():
    mentor = get_current_user()
    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    cohort_ids = {c['id'] for c in assigned_cohorts}

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'Mentor Notice').strip()
        content = request.form.get('content', '').strip()
        selected_cohort_id = request.form.get('cohort_id', '').strip()

        if title and content:
            new_ann = {
                "id": f"ann_{uuid.uuid4().hex[:6]}",
                "product_id": assigned_cohorts[0].get('product_id') if assigned_cohorts else "",
                "cohort_ids": [selected_cohort_id] if selected_cohort_id else list(cohort_ids),
                "title": title,
                "date": datetime.date.today().strftime('%Y-%m-%d'),
                "category": category,
                "content": content,
                "posted_by_mentor": mentor.get('full_name')
            }
            announcements_db.create(new_ann)
            flash("Announcement posted to assigned cohort(s) successfully!", "success")
            return redirect(url_for('mentor.announcements'))
        else:
            flash("Title and Content are required.", "danger")

    all_anns = announcements_db.find_all()
    filtered_anns = []
    for a in all_anns:
        c_ids = a.get('cohort_ids') or []
        if 'all' in c_ids or any(cid in cohort_ids for cid in c_ids):
            filtered_anns.append(a)

    return render_template(
        'mentor/announcements.html',
        mentor=mentor,
        announcements=filtered_anns,
        cohorts=assigned_cohorts
    )


@mentor_bp.route('/feedback')
@mentor_required
def feedback():
    mentor = get_current_user()
    assigned_cohorts = get_cohorts_for_mentor(mentor['id'])
    cohort_ids = [c['id'] for c in assigned_cohorts]

    from services.review_service import get_reviews_for_mentor
    reviews = get_reviews_for_mentor(mentor['id'], cohort_ids=cohort_ids)

    return render_template(
        'mentor/feedback.html',
        mentor=mentor,
        reviews=reviews,
        cohorts=assigned_cohorts
    )
