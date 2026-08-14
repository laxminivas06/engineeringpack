import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from services.json_database import JSONDatabase

users_db = JSONDatabase('users')
curriculum_db = JSONDatabase('curriculum')


def send_email(to_email: str, subject: str, body_html: str, app=None) -> tuple[bool, str]:
    """Sends an email using configured SMTP credentials with fallback logging mode."""
    if app:
        smtp_server = app.config.get('SMTP_SERVER')
        smtp_port = app.config.get('SMTP_PORT')
        smtp_username = app.config.get('SMTP_USERNAME')
        smtp_password = app.config.get('SMTP_PASSWORD')
        sender_email = app.config.get('SENDER_EMAIL')
        sender_name = app.config.get('SENDER_NAME')
    else:
        try:
            smtp_server = current_app.config.get('SMTP_SERVER')
            smtp_port = current_app.config.get('SMTP_PORT')
            smtp_username = current_app.config.get('SMTP_USERNAME')
            smtp_password = current_app.config.get('SMTP_PASSWORD')
            sender_email = current_app.config.get('SENDER_EMAIL')
            sender_name = current_app.config.get('SENDER_NAME')
        except Exception:
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
            smtp_username = 'support@aivontraa.com'
            smtp_password = ''
            sender_email = 'support@aivontraa.com'
            sender_name = 'Engineering Pack'

    if not smtp_password:
        print(f"📧 [SMTP SIMULATION / DRY RUN] To: {to_email} | Subject: '{subject}'")
        return True, "Email simulated successfully (SMTP password not set)."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email

        part_html = MIMEText(body_html, 'html')
        msg.attach(part_html)

        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, [to_email], msg.as_string())

        print(f"✅ [SMTP SENT] Successfully sent email to {to_email}")
        return True, "Email sent successfully via SMTP."
    except Exception as e:
        print(f"❌ [SMTP ERROR] Failed to send email to {to_email}: {e}")
        return False, str(e)


def send_daily_session_email(student: dict, day_number: int, app=None) -> tuple[bool, str]:
    """Builds and delivers a personalized daily session email for an enrolled student."""
    curriculum = curriculum_db.read_all()
    session_topic = "Engineering Fundamentals & Hands-on Session"
    domain = "General Engineering"
    outcomes = ["Practical application", "Technical mindset"]

    for item in curriculum:
        if item.get('day') == day_number:
            session_topic = item.get('title', session_topic)
            domain = item.get('domain', domain)
            outcomes = item.get('outcomes', outcomes)
            break

    student_name = student.get('full_name') or student.get('name') or 'Engineer'
    student_email = student.get('email')

    if not student_email:
        return False, "Student has no email address."

    subject = f"Day {day_number} Session: {session_topic} — Engineering Pack"
    
    outcomes_html = "".join([f"<li style='margin-bottom:6px;'>✨ {out}</li>" for out in outcomes])

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{subject}</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0f19; color: #e2e8f0; margin: 0; padding: 20px;">
      <div style="max-width: 600px; margin: 0 auto; background-color: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        
        <div style="text-align: center; border-bottom: 1px solid #1e293b; padding-bottom: 20px; margin-bottom: 25px;">
          <h2 style="color: #06b6d4; margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 1px;">ENGINEERING PACK</h2>
          <p style="color: #94a3b8; font-size: 13px; margin-top: 5px;">45 Days. One Engineering Journey. Powered by AIVONTRAA</p>
        </div>

        <p style="font-size: 16px; color: #f8fafc;">Hello <strong>{student_name}</strong>,</p>

        <p style="font-size: 15px; color: #cbd5e1; line-height: 1.6;">
          Welcome to <strong>Day {day_number}</strong> of your 45-Day Engineering Journey! Today's session is packed with practical insights.
        </p>

        <div style="background: linear-gradient(135deg, rgba(6,182,212,0.1), rgba(59,130,246,0.1)); border: 1px solid #06b6d4; border-radius: 8px; padding: 20px; margin: 25px 0;">
          <div style="font-size: 12px; color: #06b6d4; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Day {day_number} Focus Domain</div>
          <div style="font-size: 20px; font-weight: bold; color: #ffffff; margin: 8px 0;">{session_topic}</div>
          <div style="font-size: 13px; color: #a5f3fc;"><span style="background: #0891b2; color: #fff; padding: 3px 8px; border-radius: 4px;">{domain}</span></div>
        </div>

        <h3 style="color: #38bdf8; font-size: 16px; margin-top: 20px;">Key Outcomes For Today:</h3>
        <ul style="color: #cbd5e1; font-size: 14px; padding-left: 20px; line-height: 1.6;">
          {outcomes_html}
        </ul>

        <div style="margin-top: 30px; text-align: center;">
          <a href="http://localhost:5009/student/dashboard" style="background: linear-gradient(135deg, #06b6d4, #3b82f6); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: bold; font-size: 15px; display: inline-block;">Open Student Dashboard</a>
        </div>

        <div style="border-top: 1px solid #1e293b; margin-top: 35px; padding-top: 20px; text-align: center; font-size: 12px; color: #64748b;">
          <p>Need support? Contact us at support@aivontraa.com | Powered by AIVONTRAA Automation Pvt. Ltd.</p>
        </div>
      </div>
    </body>
    </html>
    """

    return send_email(student_email, subject, body_html, app=app)


def run_daily_email_trigger(app=None):
    """Iterates through active enrolled students and sends their current day's session email."""
    all_users = users_db.read_all()
    sent_count = 0
    for u in all_users:
        if u.get('enrollment_status') == 'Enrolled' and u.get('payment_status') == 'Paid':
            current_day = u.get('current_day', 1)
            success, _ = send_daily_session_email(u, current_day, app=app)
            if success:
                sent_count += 1
    print(f"📧 [DAILY SCHEDULER] Triggered session emails for {sent_count} enrolled students.")


def start_daily_email_scheduler(app):
    """Launches a background daemon thread that runs daily session email triggers."""
    def scheduler_loop():
        # Wait 10 seconds after server startup
        time.sleep(10)
        while True:
            try:
                with app.app_context():
                    run_daily_email_trigger(app=app)
            except Exception as e:
                print(f"Scheduler error: {e}")
            # Run every 24 hours (86400 seconds)
            time.sleep(86400)

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print("🚀 [BACKGROUND SCHEDULER] Daily SMTP email service started!")
