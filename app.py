from flask import Flask
from config import Config
from routes.public import public_bp
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from services.auth_service import get_current_user
from services.json_database import JSONDatabase
from services.email_service import start_daily_email_scheduler

app = Flask(__name__)
app.config.from_object(Config)

# Register Blueprints
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)

# Start background SMTP email scheduler
start_daily_email_scheduler(app)

settings_db = JSONDatabase('settings')


@app.context_processor
def inject_global_context():
    user = get_current_user()
    settings_records = settings_db.read_all()
    site_settings = settings_records[0] if isinstance(settings_records, list) and len(settings_records) > 0 else {
        "program_name": "ENGINEERING PACK",
        "tagline": "45 Days. One Engineering Journey.",
        "company": "AIVONTRAA Automation Pvt. Ltd.",
        "price": 3500,
        "currency_symbol": "₹",
        "duration_days": 45
    }
    return {
        'current_user': user,
        'site_settings': site_settings
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)
