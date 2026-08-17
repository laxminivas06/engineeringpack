import datetime
import uuid
from typing import List, Dict, Any, Optional
from services.json_database import JSONDatabase
from services.product_service import get_product_by_id, get_default_product, get_all_products

cohorts_db = JSONDatabase('cohorts')
users_db = JSONDatabase('users')
activity_db = JSONDatabase('activity_logs')


def get_default_capacity(product_id: Optional[str] = None) -> int:
    """Fetches default cohort seat capacity for a given product or default (35)."""
    if product_id:
        product = get_product_by_id(product_id)
        if product and 'default_cohort_capacity' in product:
            return int(product['default_cohort_capacity'])
    return 35


def get_all_cohorts(product_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns list of all cohorts (filtered by product_id if provided), updating enrollment counts dynamically."""
    if product_id and product_id != 'all':
        cohorts = cohorts_db.find_all(lambda c: c.get('product_id') == product_id)
    else:
        cohorts = cohorts_db.find_all()

    users = users_db.find_all()
    products = {p['id']: p.get('name', 'Product') for p in get_all_products()}

    # Calculate real-time current enrollment per cohort
    for cohort in cohorts:
        cid = cohort.get('id')
        enrolled_count = len([u for u in users if u.get('cohort_id') == cid])
        cohort['current_enrollment'] = enrolled_count
        cohort['product_name'] = products.get(cohort.get('product_id'), 'Unassigned Product')
        if enrolled_count >= cohort.get('max_capacity', 35) and cohort.get('status') == 'Active':
            cohort['status'] = 'Full'

    return cohorts


def get_cohort_by_id(cohort_id: str) -> Optional[Dict[str, Any]]:
    """Finds a cohort by its ID."""
    all_cohorts = get_all_cohorts()
    for c in all_cohorts:
        if str(c.get('id')) == str(cohort_id):
            return c
    return None


def get_active_cohort(product_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns the currently active open cohort for a product."""
    if not product_id:
        default_prod = get_default_product()
        product_id = default_prod.get('id') if default_prod else None

    cohorts = get_all_cohorts(product_id)
    active = next((c for c in cohorts if c.get('status') == 'Active'), None)
    if active:
        return active

    upcoming = next((c for c in cohorts if c.get('status') == 'Upcoming'), None)
    if upcoming:
        cohorts_db.update(upcoming['id'], {'status': 'Active'})
        return get_cohort_by_id(upcoming['id'])

    return None


def create_cohort(
    product_id: str,
    name: str,
    start_date: str,
    end_date: str,
    max_capacity: Optional[int] = None,
    status: str = 'Upcoming',
    description: str = '',
    duration_days: Optional[int] = 45,
    whatsapp_link: str = '',
    assigned_project_ids: Optional[List[str]] = None,
    assigned_mentor_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Manually creates a new cohort record scoped to a Product/Program."""
    product = get_product_by_id(product_id) or get_default_product()
    prod_id = product.get('id')
    prod_name = product.get('name', 'Product')

    if not max_capacity or int(max_capacity) <= 0:
        max_capacity = get_default_capacity(prod_id)
    else:
        max_capacity = int(max_capacity)

    product_cohorts = cohorts_db.find_all(lambda c: c.get('product_id') == prod_id)
    cohort_num = len(product_cohorts) + 1
    cohort_id = f"cohort_{uuid.uuid4().hex[:8]}"
    days_count = int(duration_days) if duration_days else int(product.get('duration_days', 45))

    new_cohort = {
        "id": cohort_id,
        "product_id": prod_id,
        "name": name or f"Cohort {cohort_num}",
        "start_date": start_date or datetime.date.today().strftime('%Y-%m-%d'),
        "end_date": end_date or (datetime.date.today() + datetime.timedelta(days=days_count)).strftime('%Y-%m-%d'),
        "duration_days": days_count,
        "whatsapp_link": whatsapp_link or "https://chat.whatsapp.com/sample-group-link",
        "max_capacity": max_capacity,
        "current_enrollment": 0,
        "status": status,
        "description": description or f"Cohort for {prod_name} with {max_capacity} seat capacity.",
        "assigned_project_ids": assigned_project_ids or [],
        "assigned_mentor_ids": assigned_mentor_ids or []
    }

    cohorts_db.create(new_cohort)
    log_activity("cohort_created", f"{new_cohort['name']} ({prod_name}) Created", f"New cohort created under {prod_name} with capacity of {max_capacity}.")
    return new_cohort


def can_open_new_cohort(product_id: str, exclude_cohort_id: Optional[str] = None) -> tuple[bool, str]:
    """
    Checks if a new active cohort can be set for a specific product.
    Rule: Only one active cohort per product at a time.
    """
    cohorts = get_all_cohorts(product_id)
    for c in cohorts:
        if exclude_cohort_id and c.get('id') == exclude_cohort_id:
            continue
        if c.get('status') == 'Active':
            capacity = c.get('max_capacity', 35)
            enrollment = c.get('current_enrollment', 0)
            if enrollment < capacity:
                return False, f"Cannot activate another cohort until '{c.get('name')}' is FULL ({enrollment}/{capacity}) or marked as Completed."
    return True, "OK"


def set_active_cohort(cohort_id: str) -> tuple[bool, str]:
    """Activates specified cohort while deactivating other active ones in the same product."""
    target = get_cohort_by_id(cohort_id)
    if not target:
        return False, "Cohort not found."

    product_id = target.get('product_id')
    can_open, msg = can_open_new_cohort(product_id, exclude_cohort_id=cohort_id)
    if not can_open:
        return False, msg

    product_cohorts = cohorts_db.find_all(lambda c: c.get('product_id') == product_id)
    for c in product_cohorts:
        if c.get('id') == cohort_id:
            cohorts_db.update(c['id'], {'status': 'Active'})
            log_activity("cohort_activated", f"{c['name']} Activated", f"{c['name']} set as active cohort.")
        elif c.get('status') == 'Active':
            cohorts_db.update(c['id'], {'status': 'Upcoming'})

    return True, "Cohort activated successfully."


def complete_cohort(cohort_id: str) -> tuple[bool, str]:
    """Marks a cohort as Completed. Admin manually creates or activates the next cohort when ready."""
    target = get_cohort_by_id(cohort_id)
    if not target:
        return False, "Cohort not found."

    cohorts_db.update(cohort_id, {'status': 'Completed'})
    log_activity("cohort_completed", f"{target['name']} Completed", f"{target['name']} lifecycle completed.")
    return True, f"{target['name']} marked as Completed."


def generate_cohort_timetable(start_date_str: str, duration_days: int = 45) -> List[Dict[str, Any]]:
    """Generates a day-by-day calendar timetable for a cohort based on curriculum database."""
    curriculum_db = JSONDatabase('curriculum')
    curriculum_list = curriculum_db.read_all()
    curriculum_by_day = {item.get('day'): item for item in curriculum_list}

    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except Exception:
        start_date = datetime.date.today()

    timetable = []
    for day in range(1, duration_days + 1):
        curr_date = start_date + datetime.timedelta(days=day - 1)
        curr_item = curriculum_by_day.get(day, {})
        timetable.append({
            "day": day,
            "date": curr_date.strftime('%Y-%m-%d'),
            "formatted_date": curr_date.strftime('%b %d, %Y'),
            "title": curr_item.get('title', f"Day {day} Engineering Session"),
            "domain": curr_item.get('domain', 'General Engineering'),
            "outcomes": curr_item.get('outcomes', ["Practical application", "Hands-on skills"]),
            "status": "Scheduled"
        })
    return timetable


def launch_cohort(cohort_id: str) -> tuple[bool, str]:
    """
    Launches a cohort:
    1. Sets cohort status to 'Active'.
    2. Generates the calendar timetable schedule.
    3. Triggers Day 1 responsive HTML curriculum email & WhatsApp Group link email to all confirmed enrolled students.
    """
    cohort = cohorts_db.find_by_id(cohort_id)
    if not cohort:
        return False, "Cohort record not found."

    start_date_str = cohort.get('start_date') or datetime.date.today().strftime('%Y-%m-%d')
    product = get_product_by_id(cohort.get('product_id')) or get_default_product()
    duration_days = int(cohort.get('duration_days') or product.get('duration_days', 45))

    timetable = generate_cohort_timetable(start_date_str, duration_days=duration_days)
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"

    cohorts_db.update(cohort_id, {
        'status': 'Active',
        'launched_at': now_iso,
        'duration_days': duration_days,
        'timetable': timetable
    })

    # Fetch all confirmed enrolled students for this cohort
    enrollments_db = JSONDatabase('enrollments')
    enrolled_students = []

    # 1. From enrollments.json
    cohort_enrollments = enrollments_db.find_all(lambda e: e.get('cohort_id') == cohort_id and e.get('payment_status') in ['Confirmed', 'Paid', 'Approved'])
    student_ids = {e['student_id'] for e in cohort_enrollments}
    
    for sid in student_ids:
        u = users_db.find_by_id(sid)
        if u and u.get('email'):
            enrolled_students.append(u)

    # 2. From users.json fallback
    legacy_users = users_db.find_all(lambda u: u.get('cohort_id') == cohort_id and u.get('payment_status') in ['Confirmed', 'Paid', 'Approved', 'Enrolled'])
    for u in legacy_users:
        if u['id'] not in student_ids and u.get('email'):
            enrolled_students.append(u)

    # Send Pre-Launch WhatsApp email & Day 1 curriculum email to all enrolled members
    from services.email_service import send_daily_session_email, send_prelaunch_whatsapp_email
    sent_count = 0
    for student in enrolled_students:
        send_prelaunch_whatsapp_email(student, cohort)
        ok, _ = send_daily_session_email(student, day_number=1, cohort=cohort)
        if ok:
            sent_count += 1

    log_activity(
        "cohort_launched",
        f"{cohort.get('name')} Launched",
        f"Cohort launched with {len(enrolled_students)} enrolled students. Pre-launch WhatsApp email & Day 1 curriculum email dispatched to {sent_count} members."
    )

    return True, f"Cohort '{cohort.get('name')}' launched successfully! Timetable generated for {duration_days} days. WhatsApp link & Day 1 email sent to {sent_count} confirmed students."


def dispatch_cohort_scheduled_emails() -> tuple[bool, str]:
    """Checks active cohorts' timetables against today's date and dispatches the corresponding day's email."""
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    active_cohorts = cohorts_db.find_all(lambda c: c.get('status') == 'Active')
    
    from services.email_service import send_daily_session_email
    enrollments_db = JSONDatabase('enrollments')
    total_dispatched = 0

    for cohort in active_cohorts:
        timetable = cohort.get('timetable') or []
        today_entry = next((item for item in timetable if item.get('date') == today_str), None)
        if not today_entry:
            continue

        day_num = today_entry.get('day', 1)

        cohort_enrollments = enrollments_db.find_all(lambda e: e.get('cohort_id') == cohort['id'] and e.get('payment_status') in ['Confirmed', 'Paid', 'Approved'])
        student_ids = {e['student_id'] for e in cohort_enrollments}
        students = [users_db.find_by_id(sid) for sid in student_ids if users_db.find_by_id(sid)]

        legacy = users_db.find_all(lambda u: u.get('cohort_id') == cohort['id'] and u.get('payment_status') in ['Confirmed', 'Paid', 'Approved', 'Enrolled'])
        for u in legacy:
            if u['id'] not in student_ids:
                students.append(u)

        for s in students:
            if s and s.get('email'):
                ok, _ = send_daily_session_email(s, day_number=day_num)
                if ok:
                    total_dispatched += 1

    return True, f"Dispatched Day session emails to {total_dispatched} students across active cohorts for {today_str}."


def update_cohort_calendar_from_csv(cohort_id: str, file_stream) -> tuple[bool, str]:
    """Parses uploaded CSV/Excel timetable schedule and updates cohort's duration and timetable."""
    cohort = cohorts_db.find_by_id(cohort_id)
    if not cohort:
        return False, "Cohort not found."

    import csv
    import io

    try:
        raw_bytes = file_stream.read()
        content = raw_bytes.decode('utf-8', errors='ignore')
        reader = csv.DictReader(io.StringIO(content))
        
        parsed_timetable = []
        day_count = 1

        for row in reader:
            norm_row = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k}
            
            day_val = norm_row.get('day') or norm_row.get('day_number') or str(day_count)
            date_val = norm_row.get('date') or norm_row.get('calendar_date') or datetime.date.today().strftime('%Y-%m-%d')
            title_val = norm_row.get('title') or norm_row.get('topic') or norm_row.get('topic_title') or f"Day {day_count} Session"
            domain_val = norm_row.get('domain') or norm_row.get('category') or "General Engineering"
            outcomes_raw = norm_row.get('outcomes') or norm_row.get('outcome') or 'Practical application'
            outcomes_list = [o.strip() for o in outcomes_raw.split(';') if o.strip()]

            if isinstance(day_val, str) and day_val.lower().startswith('day'):
                try:
                    day_num = int(day_val.lower().replace('day', '').strip())
                except Exception:
                    day_num = day_count
            else:
                try:
                    day_num = int(day_val)
                except Exception:
                    day_num = day_count

            parsed_timetable.append({
                "day": day_num,
                "date": date_val,
                "formatted_date": date_val,
                "title": title_val,
                "domain": domain_val,
                "outcomes": outcomes_list or ["Practical application"],
                "status": "Scheduled"
            })
            day_count += 1

        if not parsed_timetable:
            return False, "No valid rows found in the uploaded file. Please ensure columns include Day, Date, and Title."

        cohorts_db.update(cohort_id, {
            "duration_days": len(parsed_timetable),
            "timetable": parsed_timetable
        })

        log_activity("cohort_calendar_updated", f"{cohort.get('name')} Calendar Uploaded", f"Uploaded timetable schedule containing {len(parsed_timetable)} days.")

        return True, f"Calendar timetable updated successfully! Uploaded {len(parsed_timetable)} days schedule for '{cohort.get('name')}'."
    except Exception as e:
        return False, f"Failed to parse calendar file: {str(e)}"


def auto_assign_student_to_active_cohort(user_id: str, product_id: Optional[str] = None) -> tuple[bool, str]:
    """Assigns student to current active cohort for chosen product."""
    user = users_db.find_by_id(user_id)
    if not user:
        return False, "User not found."

    if not product_id:
        product_id = user.get('product_id')
    if not product_id:
        default_p = get_default_product()
        product_id = default_p.get('id') if default_p else 'prod_engpack'

    product = get_product_by_id(product_id) or get_default_product()
    active_cohort = get_active_cohort(product.get('id'))

    # If no active cohort, check if there's any cohort or create Cohort 1 manually for student
    if not active_cohort:
        active_cohort = create_cohort(
            product_id=product.get('id'),
            name="Cohort 1",
            start_date=datetime.date.today().strftime('%Y-%m-%d'),
            end_date=(datetime.date.today() + datetime.timedelta(days=product.get('duration_days', 45))).strftime('%Y-%m-%d'),
            max_capacity=product.get('default_cohort_capacity', 35),
            status='Active',
            description=f"Initial active cohort for {product.get('name')}."
        )

    # Generate Registration ID
    all_users = users_db.find_all()
    reg_num = len(all_users) + 1
    prefix = product.get('name', 'PROD')[:3].upper()
    reg_id = user.get('registration_id') or f"{prefix}-2026-{reg_num:03d}"

    updates = {
        'product_id': product.get('id'),
        'product_name': product.get('name'),
        'cohort_id': active_cohort['id'],
        'cohort_name': active_cohort['name'],
        'registration_id': reg_id,
        'payment_amount': product.get('price', 3500)
    }
    users_db.update(user_id, updates)
    return True, f"Assigned to {product.get('name')} → {active_cohort['name']} ({reg_id})."


def get_dashboard_kpis(product_id: Optional[str] = None) -> Dict[str, Any]:
    """Calculates operational KPI metrics for the Admin Dashboard, filtered by product_id or global."""
    all_users = users_db.find_all()
    products = get_all_products()

    if product_id and product_id != 'all':
        selected_product = get_product_by_id(product_id)
        filtered_users = [u for u in all_users if u.get('product_id') == product_id]
        cohorts = get_all_cohorts(product_id)
        active_cohort = get_active_cohort(product_id)
    else:
        selected_product = None
        filtered_users = all_users
        cohorts = get_all_cohorts()
        active_cohort = cohorts[0] if cohorts else None

    total_registered = len(filtered_users)
    active_cohort_name = active_cohort.get('name', 'N/A') if active_cohort else 'N/A'
    current_capacity = active_cohort.get('max_capacity', 35) if active_cohort else 35

    active_cohort_id = active_cohort.get('id') if active_cohort else ''
    active_cohort_users = [u for u in filtered_users if u.get('cohort_id') == active_cohort_id]
    active_students_count = len([u for u in active_cohort_users if u.get('student_status', u.get('status')) in ['Active', 'Enrolled']])
    current_registered_count = len(active_cohort_users)

    available_seats = max(0, current_capacity - current_registered_count)
    is_full = current_registered_count >= current_capacity

    return {
        'product_id': product_id or 'all',
        'product_name': selected_product.get('name') if selected_product else 'All Programs',
        'total_registered': total_registered,
        'active_students_current_cohort': active_students_count,
        'current_cohort_name': active_cohort_name,
        'current_cohort_id': active_cohort_id,
        'current_cohort_status': active_cohort.get('status', 'Active') if active_cohort else 'N/A',
        'cohort_capacity': current_capacity,
        'current_registered': current_registered_count,
        'available_seats': available_seats,
        'is_full': is_full,
        'total_cohorts_count': len(cohorts),
        'total_products_count': len(products)
    }


def update_cohort(cohort_id: str, updates: dict) -> tuple[bool, Any]:
    """Updates fields of an existing cohort."""
    target = cohorts_db.find_by_id(cohort_id)
    if not target:
        return False, "Cohort not found."

    clean_updates = {}
    if 'name' in updates and updates['name'].strip():
        clean_updates['name'] = updates['name'].strip()
    if 'product_id' in updates and updates['product_id'].strip():
        clean_updates['product_id'] = updates['product_id'].strip()
    if 'start_date' in updates and updates['start_date'].strip():
        clean_updates['start_date'] = updates['start_date'].strip()
    if 'end_date' in updates and updates['end_date'].strip():
        clean_updates['end_date'] = updates['end_date'].strip()
    if 'max_capacity' in updates and str(updates['max_capacity']).isdigit():
        clean_updates['max_capacity'] = int(updates['max_capacity'])
    if 'status' in updates and updates['status'].strip():
        new_st = updates['status'].strip()
        clean_updates['status'] = new_st
        if new_st == 'Active':
            set_active_cohort(cohort_id)
    if 'description' in updates:
        clean_updates['description'] = updates['description'].strip()

    updated = cohorts_db.update(cohort_id, clean_updates)
    log_activity("cohort_updated", f"{updated.get('name')} Updated", "Cohort parameters updated by admin.")
    return True, updated


def delete_cohort(cohort_id: str) -> tuple[bool, str]:
    """Deletes a cohort if no enrolled students exist in it."""
    users = users_db.find_all()
    assigned = [u for u in users if u.get('cohort_id') == cohort_id]
    if assigned:
        return False, f"Cannot delete cohort with {len(assigned)} enrolled student(s)."

    cohorts_db.delete(cohort_id)
    log_activity("cohort_deleted", "Cohort Deleted", f"Cohort {cohort_id} deleted.")
    return True, "Cohort deleted successfully."


def log_activity(act_type: str, title: str, description: str):
    """Appends an event entry to activity_logs.json."""
    logs = activity_db.find_all()
    new_log = {
        "id": f"act_{uuid.uuid4().hex[:6]}",
        "type": act_type,
        "title": title,
        "description": description,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    activity_db.create(new_log)
