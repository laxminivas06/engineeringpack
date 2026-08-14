from flask import Blueprint, render_template, request, flash, redirect, url_for
from services.json_database import JSONDatabase

public_bp = Blueprint('public', __name__)

curriculum_db = JSONDatabase('curriculum')
projects_db = JSONDatabase('projects')
mentors_db = JSONDatabase('mentors')
contacts_db = JSONDatabase('contacts')
settings_db = JSONDatabase('settings')


def get_site_settings():
    settings = settings_db.read_all()
    if isinstance(settings, dict):
        return settings
    elif isinstance(settings, list) and len(settings) > 0:
        return settings[0]
    return {
        "program_name": "ENGINEERING PACK",
        "tagline": "45 Days. One Engineering Journey.",
        "company": "AIVONTRAA Automation Pvt. Ltd.",
        "price": 3500,
        "currency_symbol": "₹",
        "duration_days": 45
    }


@public_bp.route('/')
def index():
    phases = curriculum_db.find_all()
    projects = projects_db.find_all()
    settings = get_site_settings()
    return render_template('public/index.html', phases=phases[:4], projects=projects[:3], settings=settings)


@public_bp.route('/about')
def about():
    mentors = mentors_db.find_all()
    settings = get_site_settings()
    return render_template('public/about.html', mentors=mentors, settings=settings)


@public_bp.route('/journey')
def journey():
    phases = curriculum_db.find_all()
    settings = get_site_settings()
    return render_template('public/journey.html', phases=phases, settings=settings)


@public_bp.route('/domains')
def domains():
    domains_list = [
        {
            "name": "Software Engineering",
            "icon": "code-slash",
            "description": "Master clean code, object-oriented design, design patterns, modular architecture, and unit testing."
        },
        {
            "name": "Linux",
            "icon": "terminal",
            "description": "Command-line fluent, shell scripting, file permissions, process management, and system administration."
        },
        {
            "name": "Networking",
            "icon": "diagram-3",
            "description": "TCP/IP stack, socket programming, DNS, HTTP/S protocols, subnets, and network diagnostic tools."
        },
        {
            "name": "Cybersecurity",
            "icon": "shield-lock",
            "description": "Ethical hacking, threat modeling, vulnerability scanning, cryptosystems, and secure software development."
        },
        {
            "name": "AI for Engineers",
            "icon": "robot",
            "description": "Practical ML integration, prompt engineering, LLM APIs, embeddings, vector search, and intelligent automation."
        },
        {
            "name": "Robotics",
            "icon": "cpu",
            "description": "Control systems, kinematics basics, actuator integration, hardware interfacing, and real-time sensory feedback."
        },
        {
            "name": "IoT",
            "icon": "wifi",
            "description": "Microcontrollers (ESP32/Arduino), MQTT telemetry protocols, sensor nodes, and real-time cloud data pipelines."
        },
        {
            "name": "System Design",
            "icon": "layers",
            "description": "Scalable cloud architecture, load balancing, caching, database indexing, and microservices decoupling."
        },
        {
            "name": "Git & GitHub",
            "icon": "git",
            "description": "Version control mastery, git rebase/merge, feature branching, pull request reviews, and GitHub Actions CI/CD."
        },
        {
            "name": "Career Engineering",
            "icon": "briefcase",
            "description": "Technical resume engineering, GitHub portfolio crafting, system design interviews, and career path positioning."
        },
        {
            "name": "Communication",
            "icon": "chat-square-text",
            "description": "Technical presentations, cross-team collaboration, clear requirements gathering, and professional pitch deck crafting."
        },
        {
            "name": "Documentation",
            "icon": "file-earmark-code",
            "description": "Writing API specs, architecture RFCs, system flow diagrams, clear READMEs, and technical blog writing."
        },
        {
            "name": "Personal & Soft Skills",
            "icon": "person-badge",
            "description": "Time allocation, first-principles problem solving, continuous self-learning, and high-performance mindset."
        }
    ]
    settings = get_site_settings()
    return render_template('public/domains.html', domains=domains_list, settings=settings)


@public_bp.route('/projects')
def projects():
    all_projects = projects_db.find_all()
    settings = get_site_settings()
    return render_template('public/projects.html', projects=all_projects, settings=settings)


@public_bp.route('/pricing')
def pricing():
    settings = get_site_settings()
    return render_template('public/pricing.html', settings=settings)


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
            "created_at": "2026-08-14T18:00:00Z",
            "status": "New"
        }
        contacts_db.create(contact_entry)
        flash("Thank you for reaching out! Our team will get back to you shortly.", "success")
        return redirect(url_for('public.contact'))

    return render_template('public/contact.html', settings=settings)
