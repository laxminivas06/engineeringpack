import sys
from app import app

client = app.test_client()

routes_to_test = [
    '/',
    '/about',
    '/journey',
    '/domains',
    '/projects',
    '/pricing',
    '/contact',
    '/login',
    '/admin/login'
]

print("--- 1. Testing Public & Auth Landing Pages ---")
all_passed = True
for route in routes_to_test:
    res = client.get(route)
    if res.status_code == 200:
        print(f"✅ {route} -> 200 OK")
    else:
        print(f"❌ {route} -> {res.status_code}")
        all_passed = False

print("\n--- 2. Testing Real Google OAuth Redirect URL Generation ---")
redirect_res = client.get('/auth/google/redirect', follow_redirects=False)
if redirect_res.status_code == 302 and 'accounts.google.com' in redirect_res.location:
    print(f"✅ Google OAuth Redirect URL generated correctly: {redirect_res.location[:65]}...")
else:
    print(f"❌ Google OAuth Redirect Failed: {redirect_res.status_code}")
    all_passed = False

print("\n--- 3. Testing Admin Account Recognition in Database ---")
from services.json_database import JSONDatabase
admins_db = JSONDatabase('admins')
admin_user = admins_db.find_one(email='laxminivasmorishetty143@gmail.com')

if admin_user and admin_user.get('role') == 'admin':
    print(f"✅ Admin Account found in database: {admin_user.get('name')} ({admin_user.get('email')})")
else:
    print("❌ Admin Account not found in admins.json!")
    all_passed = False

if all_passed:
    print("\n🎉 ALL TESTS PASSED! REAL GOOGLE OAUTH IS CONFIGURED CLEANLY!")
    sys.exit(0)
else:
    print("\n⚠️ SOME TESTS FAILED")
    sys.exit(1)
