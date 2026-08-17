import uuid
import datetime
from typing import List, Dict, Any, Optional
from services.json_database import JSONDatabase

reviews_db = JSONDatabase('reviews')

def create_review(
    student_id: str,
    student_name: str,
    student_email: str,
    program_id: str,
    program_name: str,
    cohort_id: str,
    cohort_name: str,
    scope: str, # 'mentor' or 'cohort'
    mentor_id: str = "",
    mentor_name: str = "",
    rating: int = 5,
    category: str = "General Feedback",
    comment: str = "",
    is_anonymous: bool = False
) -> Dict[str, Any]:
    """Creates a new student review for a mentor or overall cohort."""
    review_id = f"rev_{uuid.uuid4().hex[:8]}"
    
    review_entry = {
        "id": review_id,
        "student_id": student_id,
        "student_name": "Anonymous Student" if is_anonymous else student_name,
        "student_email": "" if is_anonymous else student_email,
        "program_id": program_id,
        "program_name": program_name,
        "cohort_id": cohort_id,
        "cohort_name": cohort_name,
        "scope": scope if scope in ['mentor', 'cohort'] else 'cohort',
        "mentor_id": mentor_id if scope == 'mentor' else "",
        "mentor_name": mentor_name if scope == 'mentor' else "",
        "rating": max(1, min(5, int(rating))),
        "category": category.strip() or "General Feedback",
        "comment": comment.strip(),
        "is_anonymous": is_anonymous,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

    reviews_db.create(review_entry)
    return review_entry


def get_all_reviews() -> List[Dict[str, Any]]:
    """Returns all reviews sorted by newest first."""
    reviews = reviews_db.read_all()
    return sorted(reviews, key=lambda x: x.get('created_at', ''), reverse=True)


def get_reviews_for_student(student_id: str) -> List[Dict[str, Any]]:
    """Returns all reviews submitted by a specific student."""
    reviews = reviews_db.find_all(lambda r: r.get('student_id') == student_id)
    return sorted(reviews, key=lambda x: x.get('created_at', ''), reverse=True)


def get_reviews_for_mentor(mentor_id: str, cohort_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Returns reviews explicitly mentioning the mentor or for assigned cohorts."""
    all_reviews = reviews_db.read_all()
    matched = []
    cohort_ids_set = set(cohort_ids) if cohort_ids else set()

    for rev in all_reviews:
        if rev.get('mentor_id') == mentor_id or (rev.get('scope') == 'cohort' and rev.get('cohort_id') in cohort_ids_set):
            matched.append(rev)
            
    return sorted(matched, key=lambda x: x.get('created_at', ''), reverse=True)


def get_reviews_for_cohort(cohort_id: str) -> List[Dict[str, Any]]:
    """Returns reviews attached to a specific cohort."""
    reviews = reviews_db.find_all(lambda r: r.get('cohort_id') == cohort_id)
    return sorted(reviews, key=lambda x: x.get('created_at', ''), reverse=True)
