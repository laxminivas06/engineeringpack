import re
import datetime
import uuid
from typing import List, Dict, Any, Optional
from services.json_database import JSONDatabase
from services.product_service import get_product_by_id

submissions_db = JSONDatabase('submissions')
projects_db = JSONDatabase('projects')
users_db = JSONDatabase('users')
cohorts_db = JSONDatabase('cohorts')


def validate_github_url(url: str) -> bool:
    """Validates if string is a valid GitHub repository URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    pattern = r'^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\/)?$'
    return bool(re.match(pattern, url))


def get_student_submissions(student_id: str) -> List[Dict[str, Any]]:
    """Returns all project submissions submitted by a specific student."""
    return submissions_db.find_all(lambda s: str(s.get('student_id')) == str(student_id))


def get_student_submission_for_project(student_id: str, project_id: str, cohort_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches a student's submission for a specific project and cohort."""
    submissions = submissions_db.find_all(
        lambda s: str(s.get('student_id')) == str(student_id) and str(s.get('project_id')) == str(project_id)
    )
    if cohort_id:
        cohort_matches = [s for s in submissions if str(s.get('cohort_id')) == str(cohort_id)]
        if cohort_matches:
            return cohort_matches[0]
    return submissions[0] if submissions else None


def get_submissions_for_project(project_id: str, cohort_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all student submissions for a project (optionally filtered by cohort)."""
    if cohort_id and cohort_id != 'all':
        return submissions_db.find_all(lambda s: str(s.get('project_id')) == str(project_id) and str(s.get('cohort_id')) == str(cohort_id))
    return submissions_db.find_all(lambda s: str(s.get('project_id')) == str(project_id))


def get_submissions_for_cohort(cohort_id: str) -> List[Dict[str, Any]]:
    """Returns all submissions for a cohort."""
    return submissions_db.find_all(lambda s: str(s.get('cohort_id')) == str(cohort_id))


def submit_project_github_url(
    student_id: str,
    product_id: str,
    cohort_id: str,
    project_id: str,
    github_url: str
) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Submits or updates a student's GitHub repository submission for a project."""
    github_url = github_url.strip()
    if not validate_github_url(github_url):
        return False, "Please enter a valid GitHub repository URL (e.g. https://github.com/username/repository).", None

    user = users_db.find_by_id(student_id)
    if not user:
        return False, "Student record not found.", None

    project = projects_db.find_by_id(project_id)
    if not project:
        return False, "Project record not found.", None

    # Check project status for cohort
    p_status = project.get('status', 'Locked')
    if p_status != 'Open':
        return False, "This project has not been opened by your mentor yet.", None

    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    existing = get_student_submission_for_project(student_id, project_id, cohort_id)

    if existing:
        updates = {
            'github_url': github_url,
            'updated_at': now_iso,
            'status': 'Submitted' if existing.get('status') in ['Submitted', 'Changes Requested'] else existing.get('status')
        }
        updated = submissions_db.update(existing['id'], updates)
        return True, "Project GitHub repository link updated successfully!", updated
    else:
        new_submission = {
            'id': f"sub_{uuid.uuid4().hex[:8]}",
            'student_id': student_id,
            'student_name': user.get('full_name') or user.get('name') or 'Student',
            'student_email': user.get('email', ''),
            'product_id': product_id,
            'cohort_id': cohort_id,
            'project_id': project_id,
            'project_name': project.get('name', 'Project'),
            'github_url': github_url,
            'submitted_at': now_iso,
            'updated_at': now_iso,
            'status': 'Submitted',
            'mentor_feedback': '',
            'reviewed_by_mentor_id': '',
            'reviewed_at': ''
        }
        created = submissions_db.create(new_submission)
        return True, "Project GitHub repository submitted successfully!", created


def review_submission(
    submission_id: str,
    status: str,
    feedback: str = "",
    mentor_id: str = ""
) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Updates review status and feedback for a student submission."""
    submission = submissions_db.find_by_id(submission_id)
    if not submission:
        return False, "Submission record not found.", None

    valid_statuses = ['Submitted', 'Under Review', 'Reviewed', 'Changes Requested']
    if status not in valid_statuses:
        return False, f"Invalid status. Choose from: {', '.join(valid_statuses)}", None

    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    updates = {
        'status': status,
        'mentor_feedback': feedback.strip(),
        'reviewed_by_mentor_id': mentor_id,
        'reviewed_at': now_iso
    }

    updated = submissions_db.update(submission_id, updates)
    return True, f"Submission status updated to '{status}'.", updated
