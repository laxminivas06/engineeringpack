import json
from flask import Flask, session, request
from config import Config
from routes.public import public_bp
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.mentor import mentor_bp
from services.auth_service import get_current_user
from services.product_service import get_all_products, get_product_by_id, get_default_product
from services.json_database import JSONDatabase
from services.email_service import start_daily_email_scheduler

app = Flask(__name__)
app.config.from_object(Config)

# Register Custom Jinja Filters
@app.template_filter('escapejs')
def escapejs_filter(val):
    if val is None:
        return ''
    # Convert string to JS escaped representation without outer quotes
    return json.dumps(str(val))[1:-1].replace("'", "\\'").replace('"', '\\"')

# Register Blueprints
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(mentor_bp)

# Start background SMTP email scheduler
start_daily_email_scheduler(app)

settings_db = JSONDatabase('settings')


@app.context_processor
def inject_global_context():
    user = get_current_user()
    settings_records = settings_db.read_all()
    site_settings = settings_records[0] if isinstance(settings_records, list) and len(settings_records) > 0 else {
        "company": "AIVONTRAA Automation Pvt. Ltd.",
        "currency_symbol": "₹",
        "support_email": "hello.aivontraa@gmail.com",
        "support_phone": "+91 9876543210"
    }

    products = get_all_products()
    selected_prod_id = request.args.get('product_id') or session.get('admin_product_id') or 'all'
    
    if selected_prod_id != 'all':
        current_product = get_product_by_id(selected_prod_id) or get_default_product()
    else:
        current_product = None

    from services.enrollment_service import is_student_enrolled
    has_confirmed = is_student_enrolled(user['id']) if user else False

    return {
        'current_user': user,
        'has_confirmed_enrollment': has_confirmed,
        'site_settings': site_settings,
        'all_products': products,
        'admin_product_id': selected_prod_id,
        'current_product': current_product
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)
