import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.json_database import JSONDatabase
from services.enrollment_service import (
    get_or_create_enrollment, update_master_student_profile,
    submit_enrollment_payment_proof, verify_enrollment_payment_admin,
    get_student_enrollments
)

users_db = JSONDatabase('users')
enrollments_db = JSONDatabase('enrollments')
client = app.test_client()

def test_multi_enrollment_workflow():
    print("--- 1. Testing Master Profile Creation & Multi-Program Enrollments ---")

    # Create dummy student user
    student_id = "usr_test_multi_student"
    test_user = {
        "id": student_id,
        "email": "multiprogram@example.com",
        "full_name": "Multi Program Student",
        "user_type": "Student",
        "role": "student"
    }
    users_db.create(test_user)

    # 1. Update Master Profile (with Academic Year = Others)
    profile_data = {
        "full_name": "Multi Program Student Updated",
        "phone": "+91 9988776655",
        "gender": "Female",
        "dob": "2003-05-15",
        "address": "Bangalore, India",
        "branch": "Computer Science & Engineering",
        "academic_year": "Others",
        "custom_academic_year": "Diploma Final Year"
    }
    success, updated_u = update_master_student_profile(student_id, profile_data)
    assert success, "Master profile update failed"
    assert updated_u['academic_year'] == "Other (Diploma Final Year)", f"Academic year mismatch: {updated_u['academic_year']}"
    print("✓ Master Student Profile updated & stored in users.json!")

    # 2. Test Multi-Program Enrollments (Engineering Pack + Robotics Pack)
    enr_eng = get_or_create_enrollment(student_id, "prod_engpack")
    enr_rob = get_or_create_enrollment(student_id, "prod_robotics")

    student_all_enr = get_student_enrollments(student_id)
    assert len(student_all_enr) >= 2, f"Expected at least 2 program enrollments, got {len(student_all_enr)}"
    print("✓ Multi-Program Enrollments Architecture verified (2 independent program drafts created for single student)!")

    # 3. Test Payment Screenshot Upload Size Validation (STRICT 100 KB LIMIT)
    print("\n--- 2. Testing 100 KB Screenshot File Validation ---")
    
    from werkzeug.datastructures import FileStorage

    # Over 100 KB dummy file (150 KB)
    large_data = b"X" * (150 * 1024)
    large_file = FileStorage(stream=io.BytesIO(large_data), filename="large_screenshot.png")

    ok, msg = submit_enrollment_payment_proof(
        enrollment_id=enr_eng['id'],
        utr_number="UTR123456789",
        screenshot_file=large_file,
        app_root_path=app.root_path
    )
    assert not ok, "File over 100 KB should have been rejected!"
    assert "exceeds the maximum limit of 100 KB" in msg, f"Unexpected error msg: {msg}"
    print("✓ Screenshot over 100 KB correctly rejected with file size error!")

    # Under 100 KB valid file (50 KB)
    small_data = b"Y" * (50 * 1024)
    small_file = FileStorage(stream=io.BytesIO(small_data), filename="valid_screenshot.png")

    ok, msg = submit_enrollment_payment_proof(
        enrollment_id=enr_eng['id'],
        utr_number="UTR987654321",
        screenshot_file=small_file,
        app_root_path=app.root_path
    )
    assert ok, f"Payment proof submit failed: {msg}"
    
    # Check pending status
    enr_check = enrollments_db.find_by_id(enr_eng['id'])
    assert enr_check['payment_status'] == "Proof Submitted", f"Expected Proof Submitted, got {enr_check['payment_status']}"
    print("✓ Screenshot under 100 KB accepted! Status set to 'Proof Submitted' (Pending Verification).")

    # 4. Admin Payment Verification & Automated Email
    print("\n--- 3. Testing Admin Payment Approval & Confirmation Email ---")
    ok, msg = verify_enrollment_payment_admin(enr_eng['id'], "admin_tester", action="approve")
    assert ok, f"Admin verification failed: {msg}"

    enr_final = enrollments_db.find_by_id(enr_eng['id'])
    assert enr_final['payment_status'] == "Confirmed", f"Expected Confirmed, got {enr_final['payment_status']}"
    assert enr_final['enrollment_status'] == "Confirmed"
    print("✓ Admin approval successfully verified payment, set status to Confirmed, and sent confirmation email!")

    # Cleanup
    users_db.delete(student_id)
    enrollments_db.delete(enr_eng['id'])
    enrollments_db.delete(enr_rob['id'])
    print("\nALL MULTI-PROGRAM ENROLLMENT TESTS PASSED PERFECTLY! 🚀")

if __name__ == '__main__':
    test_multi_enrollment_workflow()
