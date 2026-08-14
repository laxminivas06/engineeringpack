import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'engineering-pack-secret-key-2026-aivontraa'
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    
    # Google OAuth (Set via environment variables or .env)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')

    # PhonePe / UPI Payment Details
    UPI_ID = os.environ.get('UPI_ID', 'aivontraa@ybl')
    UPI_NAME = os.environ.get('UPI_NAME', 'AIVONTRAA Automation Pvt. Ltd.')
    PAYMENT_AMOUNT = int(os.environ.get('PAYMENT_AMOUNT', 3500))

    # SMTP Email Settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'hello.aivontraa@gmail.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'hello.aivontraa@gmail.com')
    SENDER_NAME = os.environ.get('SENDER_NAME', 'Engineering Pack by AIVONTRAA')
    ENABLE_DAILY_EMAILS = True
