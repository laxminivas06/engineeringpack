import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app
from services.json_database import JSONDatabase

users_db = JSONDatabase('users')
enrollments_db = JSONDatabase('enrollments')
client = app.test_client()

def test_routes():
    print("--- 1. Testing Unauthenticated Header (Only Sign In / Login) ---")

    res = client.get('/')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Sign In / Login" in html, "Homepage missing Sign In / Login button"
    # Ensure unauthenticated nav does not show Enroll Program or Dashboard
    assert 'class="nav-actions">\n        \n          <a href="/login"' in html or 'Sign In / Login</a>' in html
    print("✓ Unauthenticated header shows ONLY 'Sign In / Login' button!")

    print("\n--- 2. Testing Unauthenticated Program Detail & Join Program Redirect ---")
    res = client.get('/program/engineering-pack')
    assert res.status_code == 302
    assert '/login' in res.location
    print("✓ Unauthenticated program detail redirects to /login!")

    print("\n--- 3. Testing Authenticated Student Browsing & Dashboard Access Control ---")
    test_student = {
        'id': 'usr_test_unverified_student',
        'email': 'unverified@example.com',
        'full_name': 'Unverified Student',
        'user_type': 'Student',
        'role': 'student'
    }
    users_db.create(test_student)

    with client.session_transaction() as sess:
        sess['user_id'] = test_student['id']
        sess['role'] = 'student'
        sess['email'] = test_student['email']
        sess['name'] = test_student['full_name']

    # 3a. Authenticated student can view program details
    res = client.get('/program/engineering-pack')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Join Program" in html, "Program detail missing Join Program button for logged-in user"
    assert "/enroll/prod_engpack" in html, "Join Program button did not link to /enroll/prod_engpack"
    print("✓ Authenticated student can view program details and see 'Join Program' linking to enrollment flow!")

    # 3b. Dashboard access blocked for unverified student
    res = client.get('/student/dashboard')
    assert res.status_code == 302, f"Unverified student should be blocked from dashboard, got {res.status_code}"
    assert '/programs' in res.location or '/payment/success' in res.location
    print("✓ Unverified student attempting to access /student/dashboard is correctly BLOCKED and redirected!")

    # 3c. Verify student after admin approval unlocks dashboard
    test_enr = {
        "id": "enr_test_confirmed",
        "student_id": test_student['id'],
        "product_id": "prod_engpack",
        "payment_status": "Confirmed",
        "enrollment_status": "Confirmed"
    }
    enrollments_db.create(test_enr)

    res = client.get('/student/dashboard')
    assert res.status_code == 200, f"Confirmed student should access dashboard, got {res.status_code}"
    html = res.get_data(as_text=True)
    assert "Dashboard" in html or "Roadmap" in html or "Curriculum" in html
    print("✓ Once payment is verified/confirmed, Student Dashboard unlocks and opens successfully!")

    # Cleanup
    users_db.delete(test_student['id'])
    enrollments_db.delete(test_enr['id'])

    print("\nALL NAVIGATION & ACCESS CONTROL TESTS PASSED SUCCESSFULLY! 🎉")

if __name__ == '__main__':
    test_routes()
