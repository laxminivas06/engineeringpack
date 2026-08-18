import os

basedir = os.path.abspath(os.path.dirname(__file__))
env_file = os.path.join(basedir, '.env')

def load_env():
    """Directly reads and loads variables from .env file into os.environ."""
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key:
                        os.environ[key] = val

# Execute immediately on module import
load_env()



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'engineering-pack-secret-key-2026-aivontraa'
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    
    # Google OAuth (Set via environment variables or .env)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')

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
