import datetime
import uuid
import os
from typing import List, Dict, Any, Optional, Tuple
from services.json_database import JSONDatabase
from services.product_service import get_product_by_id
from services.email_service import send_email, build_responsive_email_html

enrollments_db = JSONDatabase('enrollments')
users_db = JSONDatabase('users')
cohorts_db = JSONDatabase('cohorts')


def get_student_enrollments(student_id: str) -> List[Dict[str, Any]]:
    """Returns all multi-program enrollments for a specific student."""
    if not student_id:
        return []
    enrollments = enrollments_db.find_all(lambda e: e.get('student_id') == student_id)
    for enr in enrollments:
        enr['product'] = get_product_by_id(enr.get('product_id'))
        if enr.get('cohort_id'):
            enr['cohort'] = cohorts_db.find_by_id(enr['cohort_id'])
    return enrollments


def get_enrollment_by_id(enrollment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an enrollment record with populated product & student details."""
    enr = enrollments_db.find_by_id(enrollment_id)
    if enr:
        enr['product'] = get_product_by_id(enr.get('product_id'))
        enr['student'] = users_db.find_by_id(enr.get('student_id'))
        if enr.get('cohort_id'):
            enr['cohort'] = cohorts_db.find_by_id(enr['cohort_id'])
    return enr


def get_or_create_enrollment(student_id: str, product_id: str) -> Dict[str, Any]:
    """Gets an existing enrollment for a student in a program or creates a new draft."""
    existing = enrollments_db.find_all(
        lambda e: e.get('student_id') == student_id and e.get('product_id') == product_id
    )
    if existing:
        enr = existing[0]
        enr['product'] = get_product_by_id(product_id)
        return enr

    # Create new enrollment draft
    enrollment_id = f"enr_{uuid.uuid4().hex[:8]}"
    ref_id = f"ENR-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    new_enr = {
        "id": enrollment_id,
        "reference_id": ref_id,
        "student_id": student_id,
        "product_id": product_id,
        "cohort_id": "",
        "program_answers": {},
        "enrollment_status": "Pending Payment",
        "payment_status": "Unpaid",
        "utr_number": "",
        "payment_screenshot": "",
        "submitted_at": "",
        "verified_at": "",
        "verified_by": "",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

    enrollments_db.create(new_enr)
    new_enr['product'] = get_product_by_id(product_id)
    return new_enr


def update_master_student_profile(student_id: str, profile_data: Dict[str, Any]) -> Tuple[bool, Any]:
    """Updates the single reusable master student profile in users.json."""
    user = users_db.find_by_id(student_id)
    if not user:
        return False, "Student account not found."

    clean_data = {}
    if 'full_name' in profile_data and profile_data['full_name'].strip():
        clean_data['full_name'] = profile_data['full_name'].strip()
        clean_data['name'] = profile_data['full_name'].strip()

    if 'phone' in profile_data:
        clean_data['phone'] = profile_data['phone'].strip()
    if 'gender' in profile_data:
        clean_data['gender'] = profile_data['gender'].strip()
    if 'dob' in profile_data:
        clean_data['dob'] = profile_data['dob'].strip()
    if 'address' in profile_data:
        clean_data['address'] = profile_data['address'].strip()
    if 'branch' in profile_data:
        clean_data['branch'] = profile_data['branch'].strip()
    if 'custom_branch' in profile_data:
        clean_data['custom_branch'] = profile_data['custom_branch'].strip()

    # Academic Year handling (1st Year, 2nd Year, 3rd Year, 4th Year, Postgraduate, N/A, Others)
    academic_year = profile_data.get('academic_year', '').strip()
    custom_year = profile_data.get('custom_academic_year', '').strip()

    if academic_year == 'Others' and custom_year:
        clean_data['academic_year'] = f"Other ({custom_year})"
        clean_data['custom_academic_year'] = custom_year
    else:
        clean_data['academic_year'] = academic_year

    clean_data['master_profile_complete'] = True

    updated_user = users_db.update(student_id, clean_data)
    return True, updated_user


def submit_enrollment_payment_proof(
    enrollment_id: str,
    utr_number: str,
    screenshot_file: Any,
    app_root_path: str
) -> Tuple[bool, str]:
    """
    Submits UTR and payment screenshot proof for an enrollment.
    Enforces STRICT 100 KB max screenshot file size and non-empty UTR validation.
    """
    enr = get_enrollment_by_id(enrollment_id)
    if not enr:
        return False, "Enrollment record not found."

    # 1. Flexible UTR Validation (min 6 chars, non-empty, not forced to 12 digits)
    clean_utr = utr_number.strip()
    if not clean_utr or len(clean_utr) < 6:
        return False, "Please enter a valid payment reference / UTR transaction number (minimum 6 characters)."

    # 2. Screenshot File Validation
    if not screenshot_file or not screenshot_file.filename:
        return False, "Please upload your payment screenshot."

    # Validate file extension
    ext = screenshot_file.filename.rsplit('.', 1)[-1].lower()
    if ext not in {'png', 'jpg', 'jpeg', 'webp'}:
        return False, "Unsupported file format. Please upload PNG, JPG, JPEG, or WEBP image."

    # Read and validate file size (< 100 KB)
    screenshot_file.seek(0, os.SEEK_END)
    file_size_bytes = screenshot_file.tell()
    screenshot_file.seek(0)

    MAX_SIZE_BYTES = 100 * 1024  # 100 KB
    if file_size_bytes > MAX_SIZE_BYTES:
        size_kb = round(file_size_bytes / 1024, 1)
        return False, f"File size ({size_kb} KB) exceeds the maximum limit of 100 KB. Please compress or resize your screenshot image before uploading."

    # Save payment screenshot file securely
    filename = f"pay_{enr['student_id']}_{uuid.uuid4().hex[:6]}.{ext}"
    upload_dir = os.path.join(app_root_path, 'static', 'uploads', 'payments')
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, filename)
    screenshot_file.save(save_path)

    # 3. Update Enrollment Record to Proof Submitted / Pending Verification
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    updates = {
        "utr_number": clean_utr,
        "payment_screenshot": f"/static/uploads/payments/{filename}",
        "payment_status": "Proof Submitted",
        "enrollment_status": "Proof Submitted",
        "submitted_at": now_iso
    }

    enrollments_db.update(enrollment_id, updates)

    # Also update master student status
    users_db.update(enr['student_id'], {
        "payment_status": "Proof Submitted",
        "enrollment_status": "Proof Submitted"
    })

    # Trigger Payment Proof Received & Verification In Progress email
    updated_enr = get_enrollment_by_id(enrollment_id)
    if updated_enr:
        send_payment_proof_submitted_email(updated_enr)

    return True, "Payment proof submitted successfully! Pending admin verification."


def verify_enrollment_payment_admin(
    enrollment_id: str,
    admin_id: str,
    action: str = "approve"
) -> Tuple[bool, str]:
    """Admin verifies or rejects a student's enrollment payment proof."""
    enr = get_enrollment_by_id(enrollment_id)
    if not enr:
        return False, "Enrollment record not found."

    now_iso = datetime.datetime.utcnow().isoformat() + "Z"

    if action == "approve":
        updates = {
            "payment_status": "Confirmed",
            "enrollment_status": "Confirmed",
            "verified_at": now_iso,
            "verified_by": admin_id
        }
        enrollments_db.update(enrollment_id, updates)

        # Update user record
        users_db.update(enr['student_id'], {
            "payment_status": "Paid",
            "enrollment_status": "Enrolled"
        })

        # Send Automated Confirmation Email
        send_enrollment_confirmation_email(enr)
        return True, f"Payment proof approved and enrollment confirmed for '{enr['student'].get('full_name')}'!"

    elif action == "reject":
        updates = {
            "payment_status": "Rejected",
            "enrollment_status": "Payment Rejected",
            "verified_at": now_iso,
            "verified_by": admin_id
        }
        enrollments_db.update(enrollment_id, updates)
        send_payment_rejection_email(enr)
        return True, "Payment proof rejected."

    return False, "Invalid verification action."


def send_payment_proof_submitted_email(enrollment: Dict[str, Any]):
    """Sends automated responsive HTML email notification when student submits payment proof."""
    student = enrollment.get('student') or users_db.find_by_id(enrollment.get('student_id')) or {}
    product = enrollment.get('product') or get_product_by_id(enrollment.get('product_id')) or {}
    recipient = student.get('email')

    if not recipient:
        return

    student_name = student.get('full_name') or student.get('name') or "Student"
    ref_id = enrollment.get('reference_id', 'ENR-PENDING')
    prog_name = product.get('name', 'Engineering Program')
    utr_num = enrollment.get('utr_number', 'N/A')
    subject = f"Registration Received & Payment Verification In Progress: {prog_name} — AIVONTRAA"

    msg_html = f"""
    Thank you for registering for <strong>{prog_name}</strong>!
    <br><br>
    Your payment proof screenshot and transaction reference (<strong>{utr_num}</strong>) have been received successfully and are currently undergoing verification by our finance and admissions team.
    """

    details = [
        ("Student Name", student_name),
        ("Program Name", prog_name),
        ("Reference ID", ref_id),
        ("UTR / Reference No.", utr_num),
        ("Payment Status", "Verification In Progress")
    ]

    footer_note = "<strong>What happens next?</strong> Our admissions team is reviewing your transaction screenshot. Once verified, your enrollment will be confirmed and your Student Dashboard will automatically unlock."

    html_content = build_responsive_email_html(
        title="Payment Proof Received — Verification In Progress",
        preheader=f"Your registration for {prog_name} is under review.",
        badge_text="Verification In Progress",
        badge_bg="rgba(245, 158, 11, 0.15)",
        badge_color="#f59e0b",
        student_name=student_name,
        main_message_html=msg_html,
        details_list=details,
        footer_note=footer_note
    )

    send_email(recipient, subject, html_content)


def send_enrollment_confirmation_email(enrollment: Dict[str, Any]):
    """Sends automated responsive HTML email notification when payment is confirmed by admin."""
    student = enrollment.get('student') or users_db.find_by_id(enrollment.get('student_id')) or {}
    product = enrollment.get('product') or get_product_by_id(enrollment.get('product_id')) or {}
    recipient = student.get('email')

    if not recipient:
        return

    student_name = student.get('full_name') or student.get('name') or "Student"
    ref_id = enrollment.get('reference_id', 'ENR-CONFIRMED')
    prog_name = product.get('name', 'Engineering Program')
    subject = f"🎉 Enrollment Confirmed: {prog_name} — AIVONTRAA"

    msg_html = f"""
    🎉 <strong>Congratulations!</strong> Your payment proof and enrollment for <strong>{prog_name}</strong> have been verified and <strong>CONFIRMED</strong>!
    <br><br>
    Your Student Dashboard is now fully unlocked and active. You can access your curriculum roadmap, live projects, and cohort schedules anytime.
    """

    details = [
        ("Student Name", student_name),
        ("Enrolled Program", prog_name),
        ("Reference Enrollment ID", ref_id),
        ("Payment Status", "<span style='color: #34d399;'>Verified & Confirmed</span>"),
        ("Enrollment Status", "<span style='color: #34d399;'>Enrolled</span>")
    ]

    footer_note = "<strong>Welcome to AIVONTRAA!</strong> You will receive cohort start schedules prior to your cohort launch date."

    html_content = build_responsive_email_html(
        title=f"Welcome to {prog_name}!",
        preheader=f"Your enrollment for {prog_name} is confirmed! Enter your dashboard now.",
        badge_text="Enrollment Confirmed & Verified",
        badge_bg="rgba(16, 185, 129, 0.15)",
        badge_color="#34d399",
        student_name=student_name,
        main_message_html=msg_html,
        details_list=details,
        cta_text="Enter Student Dashboard →",
        cta_url="https://engineeringpack.aivontraa.com/student/dashboard",
        footer_note=footer_note
    )

    send_email(recipient, subject, html_content)


def send_payment_rejection_email(enrollment: Dict[str, Any], admin_remarks: str = ""):
    """Sends automated responsive HTML email notification when payment proof is rejected by admin."""
    student = enrollment.get('student') or users_db.find_by_id(enrollment.get('student_id')) or {}
    product = enrollment.get('product') or get_product_by_id(enrollment.get('product_id')) or {}
    recipient = student.get('email')

    if not recipient:
        return

    student_name = student.get('full_name') or student.get('name') or "Student"
    ref_id = enrollment.get('reference_id', 'ENR-REJECTED')
    prog_name = product.get('name', 'Engineering Program')
    subject = f"Payment Proof Action Required: {prog_name} — AIVONTRAA"

    msg_html = f"""
    We reviewed your submitted payment proof for <strong>{prog_name}</strong>. Unfortunately, we were unable to verify your payment transaction at this time.
    <br><br>
    <strong>Admin Remarks / Reason:</strong> {admin_remarks or 'Invalid transaction reference or unreadable screenshot uploaded.'}
    <br><br>
    Don't worry! You can easily re-submit a valid payment screenshot and UTR transaction reference to complete your enrollment.
    """

    details = [
        ("Student Name", student_name),
        ("Program Name", prog_name),
        ("Reference ID", ref_id),
        ("Status", "<span style='color: #ef4444;'>Action Required / Payment Rejected</span>")
    ]

    footer_note = "Please sign in to your account and re-submit a clear payment screenshot & correct UTR number to complete your program enrollment."

    html_content = build_responsive_email_html(
        title="Payment Proof Resubmission Required",
        preheader=f"Action required for your enrollment in {prog_name}.",
        badge_text="Action Required",
        badge_bg="rgba(239, 68, 68, 0.15)",
        badge_color="#ef4444",
        student_name=student_name,
        main_message_html=msg_html,
        details_list=details,
        cta_text="Resubmit Payment Proof →",
        cta_url=f"https://engineeringpack.aivontraa.com/enroll/{product.get('id', 'prod_engpack')}",
        footer_note=footer_note
    )

    send_email(recipient, subject, html_content)


def has_confirmed_enrollment(student_id: str) -> bool:
    """Checks whether a student has a verified and confirmed payment enrollment."""
    if not student_id:
        return False
    enrollments = enrollments_db.find_all(lambda e: e.get('student_id') == student_id)
    for enr in enrollments:
        if enr.get('payment_status') in ['Confirmed', 'Paid', 'Approved'] or enr.get('enrollment_status') in ['Confirmed', 'Enrolled']:
            return True

    user = users_db.find_by_id(student_id)
    if user and (user.get('payment_status') in ['Paid', 'Approved', 'Confirmed'] or user.get('enrollment_status') in ['Enrolled', 'Confirmed']):
        return True

    return False


def is_student_enrolled(student_id: str) -> bool:
    """Checks whether a student has an active confirmed enrollment."""
    return has_confirmed_enrollment(student_id)
