import os
import json
from werkzeug.security import generate_password_hash

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Admins
admins = [
    {
        "id": "adm_001",
        "name": "System Administrator",
        "email": "admin@engineeringpack.com",
        "password_hash": generate_password_hash("Admin@123456"),
        "role": "admin",
        "created_at": "2026-08-14T18:00:00Z"
    }
]

# Users (Students)
users = [
    {
        "id": "std_001",
        "full_name": "Alexander Vance",
        "email": "student@engineeringpack.com",
        "phone": "+91 98765 43210",
        "college": "Indian Institute of Technology",
        "branch": "Computer Science & Engineering",
        "year": "3rd Year",
        "password_hash": generate_password_hash("Student@123456"),
        "role": "student",
        "status": "Active",
        "current_phase": "Phase 2: Software Engineering",
        "current_day": 7,
        "progress_pct": 16,
        "completed_projects": 1,
        "certificates_count": 0,
        "created_at": "2026-08-14T18:00:00Z"
    },
    {
        "id": "std_002",
        "full_name": "Ananya Sharma",
        "email": "ananya.s@example.com",
        "phone": "+91 91234 56789",
        "college": "National Institute of Technology",
        "branch": "Electronics & Communication",
        "year": "4th Year",
        "password_hash": generate_password_hash("Student@123456"),
        "role": "student",
        "status": "Active",
        "current_phase": "Phase 4: Cybersecurity",
        "current_day": 18,
        "progress_pct": 40,
        "completed_projects": 2,
        "certificates_count": 0,
        "created_at": "2026-08-14T18:00:00Z"
    }
]

# Curriculum
curriculum = [
    {
        "phase_number": 1,
        "title": "Engineer Mindset",
        "day_range": "Days 1 - 4",
        "domain": "System Thinking & Engineering Fundamentals",
        "icon": "brain",
        "description": "Transitioning from passive academic learning to active first-principles engineering, problem breakdown, and computational thinking."
    },
    {
        "phase_number": 2,
        "title": "Software Engineering",
        "day_range": "Days 5 - 9",
        "domain": "Software Engineering",
        "icon": "code-slash",
        "description": "Clean code architecture, modular design patterns, API design, debugging strategies, and production code quality."
    },
    {
        "phase_number": 3,
        "title": "Linux & Networking",
        "day_range": "Days 10 - 14",
        "domain": "Linux & Networking",
        "icon": "terminal",
        "description": "Command-line mastery, shell scripting, TCP/IP protocol suite, DNS, HTTP/S fundamentals, and network analysis."
    },
    {
        "phase_number": 4,
        "title": "Cybersecurity",
        "day_range": "Days 15 - 19",
        "domain": "Cybersecurity",
        "icon": "shield-check",
        "description": "Ethical hacking concepts, vulnerability assessments, secure coding, encryption standards, and threat analysis."
    },
    {
        "phase_number": 5,
        "title": "Robotics & IoT",
        "day_range": "Days 20 - 24",
        "domain": "Robotics & IoT",
        "icon": "cpu",
        "description": "Microcontrollers, embedded systems, sensor integration, actuator control, MQTT protocols, and hardware-software bridging."
    },
    {
        "phase_number": 6,
        "title": "Design & System Thinking",
        "day_range": "Days 25 - 28",
        "domain": "System Design",
        "icon": "diagram-3",
        "description": "Scalable systems design, database selection, load balancing, caching strategies, and resilient architecture."
    },
    {
        "phase_number": 7,
        "title": "Git & GitHub",
        "day_range": "Days 29 - 32",
        "domain": "Git & GitHub",
        "icon": "git",
        "description": "Professional version control, branching strategies, collaborative workflows, CI/CD pipelines, and pull request reviews."
    },
    {
        "phase_number": 8,
        "title": "AI for Engineers",
        "day_range": "Days 33 - 36",
        "domain": "AI for Engineers",
        "icon": "robot",
        "description": "Applied Machine Learning, LLM prompt engineering, AI service integration, vector databases, and intelligent automation."
    },
    {
        "phase_number": 9,
        "title": "Career Engineering",
        "day_range": "Days 37 - 40",
        "domain": "Career Engineering",
        "icon": "briefcase",
        "description": "Resume engineering, tech portfolio building, technical interview prep, system design rounds, and industry networking."
    },
    {
        "phase_number": 10,
        "title": "Communication & Documentation",
        "day_range": "Days 41 - 43",
        "domain": "Communication & Documentation",
        "icon": "file-earmark-text",
        "description": "Writing technical documentation, architecture specs, effective code comments, and delivering technical presentations."
    },
    {
        "phase_number": 11,
        "title": "Engineering Showcase",
        "day_range": "Days 44 - 45",
        "domain": "Capstone Project",
        "icon": "trophy",
        "description": "Final capstone project presentation, peer review, expert feedback, and graduation credentials."
    }
]

# Projects
projects = [
    {
        "id": "proj_01",
        "name": "Full-Stack Web Platform",
        "domain": "Software Engineering",
        "icon": "layers",
        "description": "Build a modular web platform with clean frontend-backend separation, session security, and structured data handling.",
        "outcome": "Deployable full-stack application with production-ready structure and responsive UI."
    },
    {
        "id": "proj_02",
        "name": "Network Protocol Analyzer",
        "domain": "Networking & Linux",
        "icon": "diagram-2",
        "description": "Create a command-line tool to inspect network packets, parse HTTP/DNS requests, and output diagnostic reports.",
        "outcome": "Deep understanding of TCP/IP stack and Linux networking socket operations."
    },
    {
        "id": "proj_03",
        "name": "Security Audit & Vulnerability Scanner",
        "domain": "Cybersecurity",
        "icon": "shield-lock",
        "description": "Implement automated security checks for web application headers, weak configurations, and input sanitization.",
        "outcome": "Practical exposure to OWASP Top 10 vulnerabilities and defensive engineering."
    },
    {
        "id": "proj_04",
        "name": "IoT Real-Time Dashboard",
        "domain": "Robotics & IoT",
        "icon": "broadcast",
        "description": "Develop a lightweight telemetry dashboard that ingests sensor data via MQTT/WebSockets and renders live telemetry.",
        "outcome": "End-to-end telemetry pipeline connecting physical hardware sensors to cloud dashboard."
    },
    {
        "id": "proj_05",
        "name": "Engineering Showcase Capstone",
        "domain": "Capstone Project",
        "icon": "star",
        "description": "Synthesize software, networking, security, and AI concepts into an end-to-end engineering solution.",
        "outcome": "Portfolio-grade capstone project ready for technical recruiters and industry showcase."
    }
]

# Announcements
announcements = [
    {
        "id": "ann_01",
        "title": "Welcome to Engineering Pack Cohort 2026!",
        "date": "2026-08-14",
        "category": "Platform",
        "content": "Welcome to your 45-day engineering journey! Dive into Phase 1 to begin building first-principles engineering habits."
    },
    {
        "id": "ann_02",
        "title": "Upcoming Live Q&A Session: Linux & Networking",
        "date": "2026-08-18",
        "category": "Live Session",
        "content": "Join our industry mentors this Friday for an interactive Linux terminal deep-dive and networking troubleshooting."
    }
]

# Mentors
mentors = [
    {
        "id": "mnt_01",
        "name": "Dr. Vikram Seth",
        "role": "Principal Systems Architect",
        "domain": "Software & Systems Architecture",
        "company": "Ex-Google / AIVONTRAA",
        "bio": "15+ years in distributed systems, kernel engineering, and high-throughput backend infrastructure."
    },
    {
        "id": "mnt_02",
        "name": "Sarah Lin",
        "role": "Cybersecurity Director",
        "domain": "Network Security & Ethical Hacking",
        "company": "CyberShield Labs",
        "bio": "Offensive security specialist, bug bounty hunter, and cloud security architecture expert."
    }
]

# Certificates (Empty)
certificates = []

# Contacts (Empty)
contacts = []

# Settings
settings = {
    "program_name": "ENGINEERING PACK",
    "tagline": "45 Days. One Engineering Journey.",
    "company": "AIVONTRAA Automation Pvt. Ltd.",
    "price": 3500,
    "currency": "INR",
    "currency_symbol": "₹",
    "duration_days": 45,
    "support_email": "support@engineeringpack.com",
    "support_phone": "+91 98765 43210",
    "address": "AIVONTRAA Tech Park, Innovation Hub, Tech City, India"
}

# Save files
files = {
    'admins.json': admins,
    'users.json': users,
    'curriculum.json': curriculum,
    'projects.json': projects,
    'announcements.json': announcements,
    'mentors.json': mentors,
    'certificates.json': certificates,
    'contacts.json': contacts,
    'settings.json': settings,
    'progress.json': []
}

for filename, content in files.items():
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(content, f, indent=2)
    print(f"Generated {filename}")
