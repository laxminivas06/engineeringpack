from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from services.auth_service import student_required, get_current_user
from services.json_database import JSONDatabase

student_bp = Blueprint('student', __name__, url_prefix='/student')

curriculum_db = JSONDatabase('curriculum')
projects_db = JSONDatabase('projects')
announcements_db = JSONDatabase('announcements')
users_db = JSONDatabase('users')


@student_bp.route('/dashboard')
@student_required
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    phases = curriculum_db.find_all()
    all_projects = projects_db.find_all()
    announcements = announcements_db.find_all()

    return render_template(
        'student/dashboard.html',
        user=user,
        phases=phases,
        projects=all_projects,
        announcements=announcements
    )


@student_bp.route('/journey')
@student_required
def journey():
    user = get_current_user()
    phases = curriculum_db.find_all()
    return render_template('student/journey.html', user=user, phases=phases)


@student_bp.route('/projects')
@student_required
def projects():
    user = get_current_user()
    all_projects = projects_db.find_all()
    return render_template('student/projects.html', user=user, projects=all_projects)


@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    user = get_current_user()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        user_type = request.form.get('user_type', '').strip()
        branch = request.form.get('branch', '').strip()
        academic_year = request.form.get('academic_year', '').strip()

        updates = {
            'full_name': full_name or user.get('full_name'),
            'phone': phone or user.get('phone'),
            'user_type': user_type or user.get('user_type'),
            'branch': branch or user.get('branch'),
            'academic_year': academic_year or user.get('academic_year')
        }
        updated_user = users_db.update(user['id'], updates)
        if updated_user:
            session['name'] = updated_user.get('full_name')
            flash("Profile details updated successfully!", "success")
            user = updated_user
        else:
            flash("Failed to update profile details.", "danger")

    return render_template('student/profile.html', user=user)
