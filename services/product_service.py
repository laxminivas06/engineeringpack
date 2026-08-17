import datetime
import uuid
from typing import List, Dict, Any, Optional
from services.json_database import JSONDatabase

products_db = JSONDatabase('products')


def get_all_products() -> List[Dict[str, Any]]:
    """Returns a list of all products/programs."""
    return products_db.find_all()


def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Finds a product by its ID or slug."""
    if not product_id:
        return None
    products = get_all_products()
    for p in products:
        if str(p.get('id')) == str(product_id) or str(p.get('slug')) == str(product_id):
            return p
    return None


def get_default_product() -> Dict[str, Any]:
    """Returns the default active product (Engineering Pack or first available)."""
    products = get_all_products()
    for p in products:
        if p.get('id') == 'prod_engpack':
            return p
    if products:
        return products[0]
    
    # Fallback if DB empty
    return create_product(
        name="Engineering Pack",
        tagline="45 Days. One Engineering Journey.",
        description="Comprehensive engineering program.",
        duration_days=45,
        price=3500,
        currency_symbol="₹"
    )


def create_product(
    name: str,
    tagline: str = "",
    description: str = "",
    duration_days: int = 45,
    price: float = 3500,
    currency_symbol: str = "₹",
    payment_qr_url: str = "/static/images/qr-code.png",
    banner_image_url: str = "",
    overview: str = "",
    curriculum_summary: str = "",
    courses_modules: str = "",
    phases_duration: str = "",
    projects_summary: str = "",
    learning_outcomes: str = "",
    eligibility: str = "",
    program_specific_content: str = "",
    default_cohort_capacity: int = 35,
    status: str = "Active"
) -> Dict[str, Any]:
    """Creates a new product/program entity with rich curriculum, project, and outcome details."""
    slug = name.lower().strip().replace(' ', '-').replace('/', '-')
    prod_id = f"prod_{uuid.uuid4().hex[:8]}"

    new_product = {
        "id": prod_id,
        "name": name.strip(),
        "slug": slug,
        "tagline": tagline.strip(),
        "description": description.strip(),
        "duration_days": int(duration_days) if str(duration_days).isdigit() else 45,
        "price": float(price) if str(price).replace('.', '', 1).isdigit() else 3500.0,
        "currency_symbol": currency_symbol or "₹",
        "payment_qr_url": payment_qr_url or "/static/images/qr-code.png",
        "banner_image_url": banner_image_url.strip(),
        "overview": overview.strip(),
        "curriculum_summary": curriculum_summary.strip(),
        "courses_modules": courses_modules.strip(),
        "phases_duration": phases_duration.strip(),
        "projects_summary": projects_summary.strip(),
        "learning_outcomes": learning_outcomes.strip(),
        "eligibility": eligibility.strip(),
        "program_specific_content": program_specific_content.strip(),
        "default_cohort_capacity": int(default_cohort_capacity) if str(default_cohort_capacity).isdigit() else 35,
        "status": status.strip() or "Active",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

    products_db.create(new_product)
    return new_product


def update_product(product_id: str, updates: dict) -> tuple[bool, Any]:
    """Updates product settings/data."""
    product = get_product_by_id(product_id)
    if not product:
        return False, "Product not found."

    clean_updates = {}
    if 'name' in updates and updates['name'].strip():
        clean_updates['name'] = updates['name'].strip()
        clean_updates['slug'] = updates['name'].lower().strip().replace(' ', '-').replace('/', '-')
    if 'tagline' in updates:
        clean_updates['tagline'] = updates['tagline'].strip()
    if 'description' in updates:
        clean_updates['description'] = updates['description'].strip()
    if 'duration_days' in updates and str(updates['duration_days']).isdigit():
        clean_updates['duration_days'] = int(updates['duration_days'])
    if 'price' in updates and str(updates['price']).replace('.', '', 1).isdigit():
        clean_updates['price'] = float(updates['price'])
    if 'currency_symbol' in updates and updates['currency_symbol'].strip():
        clean_updates['currency_symbol'] = updates['currency_symbol'].strip()
    if 'payment_qr_url' in updates:
        clean_updates['payment_qr_url'] = updates['payment_qr_url']
    if 'banner_image_url' in updates:
        clean_updates['banner_image_url'] = updates['banner_image_url']
    if 'overview' in updates:
        clean_updates['overview'] = updates['overview'].strip()
    if 'curriculum_summary' in updates:
        clean_updates['curriculum_summary'] = updates['curriculum_summary'].strip()
    if 'courses_modules' in updates:
        clean_updates['courses_modules'] = updates['courses_modules'].strip()
    if 'phases_duration' in updates:
        clean_updates['phases_duration'] = updates['phases_duration'].strip()
    if 'projects_summary' in updates:
        clean_updates['projects_summary'] = updates['projects_summary'].strip()
    if 'learning_outcomes' in updates:
        clean_updates['learning_outcomes'] = updates['learning_outcomes'].strip()
    if 'eligibility' in updates:
        clean_updates['eligibility'] = updates['eligibility'].strip()
    if 'program_specific_content' in updates:
        clean_updates['program_specific_content'] = updates['program_specific_content'].strip()
    if 'default_cohort_capacity' in updates and str(updates['default_cohort_capacity']).isdigit():
        clean_updates['default_cohort_capacity'] = int(updates['default_cohort_capacity'])
    if 'status' in updates and updates['status'].strip():
        clean_updates['status'] = updates['status'].strip()

    updated = products_db.update(product['id'], clean_updates)
    return True, updated


def delete_product(product_id: str) -> tuple[bool, str]:
    """Deletes a product if no cohorts or enrolled users are attached to it."""
    from services.json_database import JSONDatabase
    cohorts_db = JSONDatabase('cohorts')
    users_db = JSONDatabase('users')

    cohorts = cohorts_db.find_all(lambda c: c.get('product_id') == product_id)
    if cohorts:
        return False, f"Cannot delete product with {len(cohorts)} associated cohort(s). Delete or reassign cohorts first."

    users = users_db.find_all(lambda u: u.get('product_id') == product_id)
    if users:
        return False, f"Cannot delete product with {len(users)} enrolled student(s)."

    products_db.delete(product_id)
    return True, "Product deleted successfully."
