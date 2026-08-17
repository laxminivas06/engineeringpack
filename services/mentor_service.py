import datetime
import uuid
from typing import List, Dict, Any, Optional
from services.json_database import JSONDatabase
from services.product_service import get_product_by_id, get_all_products, update_product

mentors_db = JSONDatabase('mentors')
products_db = JSONDatabase('products')


def get_icon_for_link(platform: str, url: str = "") -> str:
    """Returns the matching Bootstrap icon class based on platform or URL string."""
    text = (platform + " " + url).lower()
    if 'linkedin' in text:
        return 'bi-linkedin'
    elif 'github' in text:
        return 'bi-github'
    elif 'twitter' in text or 'x.com' in text:
        return 'bi-twitter-x'
    elif 'instagram' in text:
        return 'bi-instagram'
    elif 'youtube' in text:
        return 'bi-youtube'
    elif 'website' in text or 'globe' in text:
        return 'bi-globe'
    elif 'facebook' in text:
        return 'bi-facebook'
    elif 'medium' in text:
        return 'bi-medium'
    return 'bi-link-45deg'


def get_all_mentors(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns list of central mentor records with processed icon fields for rendering."""
    all_mentors = mentors_db.find_all()
    if status_filter:
        all_mentors = [m for m in all_mentors if m.get('status', 'Active').lower() == status_filter.lower()]

    for m in all_mentors:
        m['processed_links'] = process_mentor_links(m)

    return all_mentors


def get_mentor_by_id(mentor_id: str) -> Optional[Dict[str, Any]]:
    """Finds a mentor by ID and includes processed_links."""
    if not mentor_id:
        return None
    mentor = mentors_db.find_by_id(mentor_id)
    if mentor:
        mentor['processed_links'] = process_mentor_links(mentor)
    return mentor


def get_mentor_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Finds a mentor by email address."""
    if not email:
        return None
    clean_email = email.strip().lower()
    mentor = mentors_db.find_one(email=clean_email)
    if mentor:
        mentor['processed_links'] = process_mentor_links(mentor)
    return mentor


def process_mentor_links(mentor: Dict[str, Any]) -> List[Dict[str, str]]:
    """Normalizes legacy and dynamic social links into a unified list of link dicts."""
    links = []
    # Dynamic social links list if present
    if mentor.get('social_links') and isinstance(mentor['social_links'], list):
        for item in mentor['social_links']:
            if isinstance(item, dict) and item.get('url'):
                platform = item.get('platform', 'Link').strip()
                url = item.get('url', '').strip()
                links.append({
                    'platform': platform,
                    'url': url,
                    'icon': get_icon_for_link(platform, url)
                })

    # Backward-compatibility for individual fields if not in dynamic list
    existing_urls = {l['url'] for l in links}
    legacy_map = [
        ('Website', mentor.get('website')),
        ('GitHub', mentor.get('github')),
        ('LinkedIn', mentor.get('linkedin')),
        ('Twitter/X', mentor.get('twitter')),
        ('Custom Link', mentor.get('other_links'))
    ]
    for platform, url in legacy_map:
        if url and url.strip() and url.strip() not in existing_urls:
            links.append({
                'platform': platform,
                'url': url.strip(),
                'icon': get_icon_for_link(platform, url.strip())
            })
            existing_urls.add(url.strip())

    return links


def create_mentor(
    full_name: str,
    email: str = "",
    professional_title: str = "",
    domain: str = "",
    short_bio: str = "",
    detailed_about: str = "",
    experience: str = "",
    skills: str = "",
    education_certifications: str = "",
    website: str = "",
    github: str = "",
    linkedin: str = "",
    twitter: str = "",
    other_links: str = "",
    internal_phone: str = "",
    profile_photo_url: str = "",
    status: str = "Active",
    social_links: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Creates a new mentor entry in the central Mentor database."""
    mentor_id = f"mnt_{uuid.uuid4().hex[:8]}"

    new_mentor = {
        "id": mentor_id,
        "full_name": full_name.strip(),
        "name": full_name.strip(),
        "email": email.strip().lower(),
        "role": "mentor",
        "professional_title": professional_title.strip(),
        "domain": domain.strip(),
        "short_bio": short_bio.strip(),
        "bio": short_bio.strip(),
        "detailed_about": detailed_about.strip(),
        "experience": experience.strip(),
        "skills": skills.strip(),
        "education_certifications": education_certifications.strip(),
        "website": website.strip(),
        "github": github.strip(),
        "linkedin": linkedin.strip(),
        "twitter": twitter.strip(),
        "other_links": other_links.strip(),
        "social_links": social_links if social_links is not None else [],
        "internal_phone": internal_phone.strip(),
        "profile_photo_url": profile_photo_url.strip() or "/static/images/default-avatar.png",
        "status": status.strip() or "Active",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

    mentors_db.create(new_mentor)
    new_mentor['processed_links'] = process_mentor_links(new_mentor)
    return new_mentor


def update_mentor(mentor_id: str, updates: dict) -> tuple[bool, Any]:
    """Updates a mentor's profile details."""
    mentor = get_mentor_by_id(mentor_id)
    if not mentor:
        return False, "Mentor record not found."

    clean_updates = {}
    if 'full_name' in updates and updates['full_name'].strip():
        clean_updates['full_name'] = updates['full_name'].strip()
        clean_updates['name'] = updates['full_name'].strip()
    if 'email' in updates and updates['email'].strip():
        clean_updates['email'] = updates['email'].strip().lower()
    if 'professional_title' in updates:
        clean_updates['professional_title'] = updates['professional_title'].strip()
    if 'domain' in updates:
        clean_updates['domain'] = updates['domain'].strip()
    if 'short_bio' in updates:
        clean_updates['short_bio'] = updates['short_bio'].strip()
        clean_updates['bio'] = updates['short_bio'].strip()
    if 'detailed_about' in updates:
        clean_updates['detailed_about'] = updates['detailed_about'].strip()
    if 'experience' in updates:
        clean_updates['experience'] = updates['experience'].strip()
    if 'skills' in updates:
        clean_updates['skills'] = updates['skills'].strip()
    if 'education_certifications' in updates:
        clean_updates['education_certifications'] = updates['education_certifications'].strip()
    if 'website' in updates:
        clean_updates['website'] = updates['website'].strip()
    if 'github' in updates:
        clean_updates['github'] = updates['github'].strip()
    if 'linkedin' in updates:
        clean_updates['linkedin'] = updates['linkedin'].strip()
    if 'twitter' in updates:
        clean_updates['twitter'] = updates['twitter'].strip()
    if 'other_links' in updates:
        clean_updates['other_links'] = updates['other_links'].strip()
    if 'social_links' in updates:
        clean_updates['social_links'] = updates['social_links']
    if 'internal_phone' in updates:
        clean_updates['internal_phone'] = updates['internal_phone'].strip()
    if 'profile_photo_url' in updates and updates['profile_photo_url'].strip():
        clean_updates['profile_photo_url'] = updates['profile_photo_url'].strip()
    if 'status' in updates and updates['status'].strip():
        clean_updates['status'] = updates['status'].strip()

    updated = mentors_db.update(mentor_id, clean_updates)
    if updated:
        updated['processed_links'] = process_mentor_links(updated)
    return True, updated


def update_mentor_self_profile(mentor_id: str, updates: dict) -> tuple[bool, Any]:
    """Allows mentors to update allowed public fields while protecting sensitive administrative fields."""
    allowed_fields = [
        'full_name', 'professional_title', 'domain', 'short_bio', 'detailed_about',
        'experience', 'skills', 'education_certifications', 'website', 'github',
        'linkedin', 'twitter', 'other_links', 'social_links', 'profile_photo_url'
    ]
    safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    return update_mentor(mentor_id, safe_updates)


def delete_mentor(mentor_id: str) -> tuple[bool, str]:
    """Deletes a mentor from central DB and removes them from all program assignments."""
    mentor = get_mentor_by_id(mentor_id)
    if not mentor:
        return False, "Mentor record not found."

    products = get_all_products()
    for p in products:
        assigned = p.get('assigned_mentor_ids', [])
        if mentor_id in assigned:
            new_assigned = [mid for mid in assigned if mid != mentor_id]
            products_db.update(p['id'], {'assigned_mentor_ids': new_assigned})

    mentors_db.delete(mentor_id)
    return True, f"Mentor '{mentor.get('full_name')}' deleted successfully."


def get_mentors_for_program(product_id: str, public_only: bool = True) -> List[Dict[str, Any]]:
    """Returns list of mentor objects assigned to a specific program."""
    product = get_product_by_id(product_id)
    if not product:
        return []

    assigned_ids = product.get('assigned_mentor_ids', [])
    mentors = []
    for mid in assigned_ids:
        m = get_mentor_by_id(mid)
        if m:
            if public_only:
                if m.get('status', 'Active') == 'Active':
                    mentors.append(sanitize_public_mentor(m))
            else:
                mentors.append(m)
    return mentors


def get_cohorts_for_mentor(mentor_id: str) -> List[Dict[str, Any]]:
    """Fetches all cohorts assigned to a specific mentor across all programs."""
    cohorts_db = JSONDatabase('cohorts')
    all_cohorts = cohorts_db.read_all()
    products = {p['id']: p for p in get_all_products()}

    assigned_cohorts = []
    for c in all_cohorts:
        assigned_mids = c.get('assigned_mentor_ids', [])
        if mentor_id in assigned_mids:
            prod = products.get(c.get('product_id'), {})
            c['product_name'] = prod.get('name', 'Program')
            c['product_slug'] = prod.get('slug', '')
            assigned_cohorts.append(c)

    return assigned_cohorts


def get_projects_for_mentor(mentor_id: str) -> List[Dict[str, Any]]:
    """Fetches all projects associated with cohorts assigned to a specific mentor."""
    assigned_cohorts = get_cohorts_for_mentor(mentor_id)
    cohort_ids = {c['id'] for c in assigned_cohorts}

    projects_db = JSONDatabase('projects')
    all_projects = projects_db.read_all()

    mentor_projects = []
    for p in all_projects:
        # Check if project cohort is assigned to mentor, or if project is assigned via cohort's assigned_project_ids
        p_cohort_id = p.get('cohort_id')
        if p_cohort_id in cohort_ids or p_cohort_id == 'all':
            mentor_projects.append(p)
        else:
            for c in assigned_cohorts:
                if p['id'] in c.get('assigned_project_ids', []):
                    mentor_projects.append(p)
                    break

    return mentor_projects


def assign_mentor_to_program(product_id: str, mentor_id: str) -> tuple[bool, str]:
    """Assigns an existing central mentor to a program."""
    product = get_product_by_id(product_id)
    if not product:
        return False, "Program not found."

    mentor = get_mentor_by_id(mentor_id)
    if not mentor:
        return False, "Mentor not found in central database."

    assigned_ids = product.get('assigned_mentor_ids', [])
    if mentor_id in assigned_ids:
        return False, f"Mentor '{mentor.get('full_name')}' is already assigned to this program."

    assigned_ids.append(mentor_id)
    products_db.update(product['id'], {'assigned_mentor_ids': assigned_ids})
    return True, f"Mentor '{mentor.get('full_name')}' assigned to '{product.get('name')}' successfully."


def remove_mentor_from_program(product_id: str, mentor_id: str) -> tuple[bool, str]:
    """Removes a mentor assignment from a program without deleting their central profile."""
    product = get_product_by_id(product_id)
    if not product:
        return False, "Program not found."

    assigned_ids = product.get('assigned_mentor_ids', [])
    if mentor_id not in assigned_ids:
        return False, "Mentor is not assigned to this program."

    new_ids = [mid for mid in assigned_ids if mid != mentor_id]
    products_db.update(product['id'], {'assigned_mentor_ids': new_ids})
    return True, "Mentor removed from program successfully."


def sanitize_public_mentor(mentor: Dict[str, Any]) -> Dict[str, Any]:
    """CONFIDENTIALITY SAFEGUARD: Strips internal phone numbers and private fields for safe public rendering."""
    safe_mentor = dict(mentor)
    safe_mentor.pop('internal_phone', None)
    return safe_mentor

