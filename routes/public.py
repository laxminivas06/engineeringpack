from flask import Blueprint, render_template, request, flash, redirect, url_for
from services.json_database import JSONDatabase
from services.product_service import get_all_products, get_product_by_id, get_default_product
from services.mentor_service import get_mentors_for_program, get_all_mentors, sanitize_public_mentor
from services.auth_service import get_current_user

public_bp = Blueprint('public', __name__)

curriculum_db = JSONDatabase('curriculum')
projects_db = JSONDatabase('projects')
mentors_db = JSONDatabase('mentors')
contacts_db = JSONDatabase('contacts')
settings_db = JSONDatabase('settings')
users_db = JSONDatabase('users')
cohorts_db = JSONDatabase('cohorts')


def get_site_settings():
    settings = settings_db.read_all()
    if isinstance(settings, list) and len(settings) > 0:
        return settings[0]
    return {
        "company": "AIVONTRAA Automation Pvt. Ltd.",
        "currency_symbol": "₹",
        "support_email": "hello.aivontraa@gmail.com",
        "support_phone": "+91 9876543210"
    }


def get_public_stats():
    """
    Computes safe aggregated organization-level statistics.
    Crucial: Strictly returns count totals, NEVER individual student data or rosters.
    """
    all_users = users_db.read_all()
    all_products = get_all_products()
    all_cohorts = cohorts_db.read_all()

    active_prods = [p for p in all_products if p.get('status') == 'Active']
    completed_cohorts = [c for c in all_cohorts if c.get('status') == 'Completed']

    return {
        "total_registered": len(all_users),
        "active_programs": len(active_prods),
        "completed_cohorts": len(completed_cohorts),
        "total_projects": len(projects_db.read_all())
    }


def get_core_pillars():
    """Organization approach pillars for student growth and career readiness."""
    return [
        {
            "id": "pillar_learning",
            "title": "Learning & Skill Development",
            "icon": "journal-code",
            "description": "Structured curriculum grounded in first principles, systems architecture, clean code, and cross-functional engineering."
        },
        {
            "id": "pillar_practical",
            "title": "Practical & Project-Based Exposure",
            "icon": "tools",
            "description": "Terminal-first hands-on labs, real toolchains, live packet analysis, code auditing, and end-to-end portfolio building."
        },
        {
            "id": "pillar_internships",
            "title": "Internships & Industry Experience",
            "icon": "briefcase-fill",
            "description": "Direct bridge to industry partner opportunities, real team workflows, pull request reviews, and agile sprints."
        },
        {
            "id": "pillar_innovation",
            "title": "Innovation & Entrepreneurship",
            "icon": "lightbulb-fill",
            "description": "Fostering creative technical problem solving, product prototyping, and hacker-mindset product building."
        },
        {
            "id": "pillar_startup",
            "title": "Startup Ecosystem",
            "icon": "rocket-takeoff-fill",
            "description": "Mentorship from founders, system architects, and tech directors to turn student projects into viable startup products."
        },
        {
            "id": "pillar_readiness",
            "title": "Career & Industry Readiness",
            "icon": "award-fill",
            "description": "Technical interview preparation, system design drills, portfolio verification, and professional communication mastery."
        }
    ]


@public_bp.route('/')
def index():
    products = [p for p in get_all_products() if p.get('status') == 'Active']
    stats = get_public_stats()
    pillars = get_core_pillars()
    settings = get_site_settings()
    phases = curriculum_db.find_all()
    projects = projects_db.find_all()

    return render_template(
        'public/index.html',
        products=products,
        stats=stats,
        pillars=pillars,
        phases=phases[:4],
        projects=projects[:3],
        settings=settings
    )


@public_bp.route('/programs')
def programs_catalog():
    products = [p for p in get_all_products() if p.get('status') == 'Active']
    settings = get_site_settings()
    stats = get_public_stats()
    return render_template('public/programs.html', products=products, settings=settings, stats=stats)


@public_bp.route('/program/<product_id_or_slug>')
def program_detail(product_id_or_slug):
    user = get_current_user()
    if not user:
        flash("Please sign in with Google to view program details and access enrollment.", "info")
        return redirect(url_for('auth.login'))

    product = get_product_by_id(product_id_or_slug)
    if not product:
        flash("Program not found.", "warning")
        return redirect(url_for('public.programs_catalog'))

    settings = get_site_settings()
    
    # Get public phases and projects associated with this product
    phases = curriculum_db.find_all(lambda c: c.get('product_id') == product.get('id'))
    if not phases and product.get('id') == 'prod_engpack':
        phases = curriculum_db.find_all()

    projects = projects_db.find_all(lambda p: p.get('product_id') == product.get('id'))
    if not projects and product.get('id') == 'prod_engpack':
        projects = projects_db.find_all()

    stats = get_public_stats()
    mentors = get_mentors_for_program(product['id'], public_only=True)

    return render_template(
        'public/program_detail.html',
        product=product,
        phases=phases,
        projects=projects,
        settings=settings,
        stats=stats,
        mentors=mentors
    )


@public_bp.route('/about')
def about():
    raw_mentors = get_all_mentors(status_filter='Active')
    mentors = [sanitize_public_mentor(m) for m in raw_mentors]
    settings = get_site_settings()
    pillars = get_core_pillars()
    stats = get_public_stats()

    lifecycle_steps = [
        {"num": 1, "title": "Nurture", "desc": "Identify student passion and establish foundational engineering mindset.", "icon": "flower1"},
        {"num": 2, "title": "Learn", "desc": "Rigorous first-principles curriculum across core domains.", "icon": "journal-text"},
        {"num": 3, "title": "Build", "desc": "Hands-on coding, terminal labs, and hardware-software integration.", "icon": "hammer"},
        {"num": 4, "title": "Practical Exposure", "desc": "Real-world project scenarios, security audits, and cloud deployment.", "icon": "terminal"},
        {"num": 5, "title": "Internships", "desc": "Industry partner connections and real-world team experience.", "icon": "briefcase"},
        {"num": 6, "title": "Entrepreneurship", "desc": "Ideation, prototype design, and product thinking.", "icon": "lightbulb"},
        {"num": 7, "title": "Startup Ecosystem", "desc": "Founder mentorship, pitch prep, and incubation opportunities.", "icon": "rocket-takeoff"},
        {"num": 8, "title": "Career Readiness", "desc": "Verified engineering portfolio, resume, and technical interview confidence.", "icon": "check-circle-fill"}
    ]

    return render_template(
        'public/about.html',
        settings=settings,
        pillars=pillars,
        stats=stats,
        lifecycle_steps=lifecycle_steps
    )


@public_bp.route('/mentors')
def mentors():
    raw_mentors = get_all_mentors(status_filter='Active')
    mentors = [sanitize_public_mentor(m) for m in raw_mentors]
    settings = get_site_settings()
    stats = get_public_stats()

    return render_template(
        'public/mentors.html',
        mentors=mentors,
        settings=settings,
        stats=stats
    )


@public_bp.route('/journey')
def journey():
    selected_prod = request.args.get('product_id')
    if selected_prod:
        phases = curriculum_db.find_all(lambda c: c.get('product_id') == selected_prod)
    else:
        phases = curriculum_db.find_all()
    products = [p for p in get_all_products() if p.get('status') == 'Active']
    settings = get_site_settings()
    return render_template('public/journey.html', phases=phases, products=products, settings=settings)


@public_bp.route('/domains')
def domains():
    domains_list = [
        {"name": "Software Engineering", "icon": "code-slash", "description": "Master clean code, object-oriented design, design patterns, modular architecture, and unit testing."},
        {"name": "Linux Systems", "icon": "terminal", "description": "Command-line fluent, shell scripting, file permissions, process management, and system administration."},
        {"name": "Networking Protocols", "icon": "diagram-3", "description": "TCP/IP stack, socket programming, DNS, HTTP/S protocols, subnets, and network diagnostic tools."},
        {"name": "Cybersecurity", "icon": "shield-lock", "description": "Ethical hacking, threat modeling, vulnerability scanning, cryptosystems, and secure software development."},
        {"name": "Robotics & Telemetry", "icon": "cpu", "description": "Control systems, actuator integration, microcontrollers (ESP32/Arduino), and real-time sensory feedback."},
        {"name": "AI Automation", "icon": "robot", "description": "Practical ML integration, prompt engineering, LLM APIs, embeddings, vector search, and intelligent automation."}
    ]
    settings = get_site_settings()
    return render_template('public/domains.html', domains=domains_list, settings=settings)


@public_bp.route('/projects')
def projects():
    all_projects = projects_db.find_all()
    products = [p for p in get_all_products() if p.get('status') == 'Active']
    settings = get_site_settings()
    return render_template('public/projects.html', projects=all_projects, products=products, settings=settings)


@public_bp.route('/pricing')
def pricing():
    products = [p for p in get_all_products() if p.get('status') == 'Active']
    settings = get_site_settings()
    return render_template('public/pricing.html', products=products, settings=settings)


@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    settings = get_site_settings()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash("Please fill in all required fields (Name, Email, Message).", "danger")
            return redirect(url_for('public.contact'))

        contact_entry = {
            "name": name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "message": message,
            "created_at": "2026-08-17T18:00:00Z",
            "status": "New"
        }
        contacts_db.create(contact_entry)
        flash("Thank you for reaching out! Our team will get back to you shortly.", "success")
        return redirect(url_for('public.contact'))

    return render_template('public/contact.html', settings=settings)
