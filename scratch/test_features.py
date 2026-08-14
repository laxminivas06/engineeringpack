import sys
import io
from app import app
from services.email_service import send_daily_session_email
from services.json_database import JSONDatabase

client = app.test_client()
users_db = JSONDatabase('users')

print("--- 1. Testing PhonePe Payment Page Render ---")
# Setup a student in pending payment state
test_user = users_db.read_all()[0]
users_db.update(test_user['id'], {'payment_status': 'Unpaid', 'enrollment_status': 'Pending Payment'})

with client.session_transaction() as sess:
    sess['user_id'] = test_user['id']
    sess['role'] = 'student'
    sess['email'] = test_user['email']
    sess['name'] = test_user['full_name']

res = client.get('/payment')
if res.status_code == 200 and b'PhonePe / UPI Scan & Pay' in res.data and b'aivontraa@ybl' in res.data:
    print("✅ PhonePe payment page rendered successfully with QR code & UPI ID (aivontraa@ybl)!")
else:
    print(f"❌ Payment page failed to render cleanly: {res.status_code}")
    sys.exit(1)

print("\n--- 2. Testing Payment Screenshot & UTR Upload Submission ---")
data = {
    'utr_number': '123456789012',
    'payment_screenshot': (io.BytesIO(b"fake image content"), 'test_receipt.png')
}
res_upload = client.post('/payment/process', data=data, content_type='multipart/form-data', follow_redirects=True)
if res_upload.status_code == 200:
    print("✅ Payment screenshot upload & UTR reference submitted successfully!")
else:
    print(f"❌ Payment screenshot upload failed: {res_upload.status_code}")
    sys.exit(1)

print("\n--- 3. Testing Live SMTP Daily Session Email Dispatch ---")
with app.app_context():
    student = users_db.read_all()[0]
    success, msg = send_daily_session_email(student, day_number=1)
    if success:
        print(f"✅ Live SMTP Email delivered via hello.aivontraa@gmail.com: {msg}")
    else:
        print(f"❌ Email engine failed: {msg}")
        sys.exit(1)

print("\n🎉 ALL FEATURE TESTS PASSED SUCCESSFULLY!")
