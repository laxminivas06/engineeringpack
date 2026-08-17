import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from services.json_database import JSONDatabase

users_db = JSONDatabase('users')
curriculum_db = JSONDatabase('curriculum')


def build_responsive_email_html(
    title: str,
    preheader: str,
    badge_text: str,
    badge_bg: str,
    badge_color: str,
    student_name: str,
    main_message_html: str,
    details_list: list = None,
    cta_text: str = None,
    cta_url: str = None,
    footer_note: str = None
) -> str:
    """Builds a responsive, modern HTML email template for mobile and desktop."""
    
    details_html = ""
    if details_list:
        rows = ""
        for label, val in details_list:
            rows += f"""
            <tr>
              <td style="padding: 10px 14px; color: #94a3b8; font-weight: 500; border-bottom: 1px solid #1e293b; font-size: 14px;">{label}</td>
              <td style="padding: 10px 14px; color: #f8fafc; font-weight: 700; border-bottom: 1px solid #1e293b; font-size: 14px; text-align: right;">{val}</td>
            </tr>
            """
        details_html = f"""
        <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #0f172a; border-radius: 8px; margin: 20px 0; border: 1px solid #1e293b;">
          {rows}
        </table>
        """

    cta_html = ""
    if cta_text and cta_url:
        cta_html = f"""
        <div style="text-align: center; margin: 28px 0 16px;">
          <a href="{cta_url}" style="background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%); color: #ffffff; text-decoration: none; padding: 13px 26px; font-size: 15px; font-weight: 700; border-radius: 8px; display: inline-block; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.4);">
            {cta_text}
          </a>
        </div>
        """

    footer_note_html = ""
    if footer_note:
        footer_note_html = f"""
        <div style="background-color: #0b1324; border-left: 4px solid #38bdf8; padding: 14px; border-radius: 6px; font-size: 13px; color: #94a3b8; margin-top: 20px; line-height: 1.5;">
          {footer_note}
        </div>
        """

    badge_html = ""
    if badge_text:
        badge_html = f"""
        <div style="text-align: center; margin-bottom: 18px;">
          <span style="background-color: {badge_bg}; color: {badge_color}; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: inline-block; border: 1px solid {badge_color}40;">
            {badge_text}
          </span>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
  <div style="display: none; font-size: 1px; color: #0b0f19; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
    {preheader}
  </div>

  <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #0b0f19; padding: 30px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" style="width: 100%; max-width: 580px; border-collapse: collapse; background-color: #111827; border: 1px solid #1e293b; border-radius: 14px; overflow: hidden; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6);">
          
          <!-- BRAND HEADER -->
          <tr>
            <td style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 26px 24px; text-align: center; border-bottom: 1px solid #1e293b;">
              <h1 style="margin: 0; color: #38bdf8; font-size: 24px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px;">
                AIVONTRAA
              </h1>
              <div style="color: #94a3b8; font-size: 12px; font-weight: 600; margin-top: 4px; letter-spacing: 0.5px;">
                ENGINEERING PACK ACADEMY
              </div>
            </td>
          </tr>

          <!-- BODY CONTENT -->
          <tr>
            <td style="padding: 30px 26px;">
              
              {badge_html}

              <h2 style="margin: 0 0 16px 0; color: #f8fafc; font-size: 20px; font-weight: 700; line-height: 1.3; text-align: center;">
                {title}
              </h2>

              <p style="color: #cbd5e1; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
                Hello <strong>{student_name}</strong>,
              </p>

              <div style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 16px;">
                {main_message_html}
              </div>

              {details_html}

              {footer_note_html}

              {cta_html}

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color: #0b0f19; padding: 22px; text-align: center; border-top: 1px solid #1e293b; color: #64748b; font-size: 12px; line-height: 1.5;">
              <p style="margin: 0 0 6px 0; color: #94a3b8; font-weight: 600;">
                AIVONTRAA Engineering Programs
              </p>
              <p style="margin: 0 0 10px 0;">
                Questions? Contact support at <a href="mailto:support@aivontraa.com" style="color: #38bdf8; text-decoration: none;">support@aivontraa.com</a>
              </p>
              <p style="margin: 0; font-size: 11px; color: #475569;">
                © 2026 AIVONTRAA. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


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


def send_prelaunch_whatsapp_email(student: dict, cohort: dict, app=None) -> tuple[bool, str]:
    """Sends a responsive HTML email containing the official WhatsApp Group Link and Pre-Launch schedule."""
    student_name = student.get('full_name') or student.get('name') or 'Engineer'
    student_email = student.get('email')

    if not student_email:
        return False, "Student email missing."

    cohort_name = cohort.get('name', 'Cohort 1')
    whatsapp_link = cohort.get('whatsapp_link') or 'https://chat.whatsapp.com/sample-group-link'
    start_date = cohort.get('start_date', 'Coming Soon')
    duration_days = cohort.get('duration_days', 45)

    subject = f"🚀 Get Ready! Join Official WhatsApp Group & Pre-Launch Event: {cohort_name}"

    main_msg = f"""
    We are thrilled to welcome you to <strong>{cohort_name}</strong>! Your enrollment is fully confirmed.
    <br><br>
    Before <strong>Day 1</strong> begins, please join our official student community WhatsApp group below. All live session links, mentor announcements, and daily schedules will be posted here!
    <br><br>
    <strong>Pre-Launch Orientation Checklist:</strong>
    <ul style="padding-left: 20px; color: #cbd5e1; margin-top: 8px;">
      <li>👉 Join the Official WhatsApp Group using the button below</li>
      <li>📅 Mark your calendar for Day 1: <strong>{start_date}</strong></li>
      <li>💻 Setup your laptop workspace & GitHub profile</li>
    </ul>
    """

    details = [
        ("Assigned Cohort", cohort_name),
        ("Cohort Start Date", start_date),
        ("Bootcamp Duration", f"{duration_days} Days"),
        ("Official WhatsApp Group", "Access Granted")
    ]

    html_content = build_responsive_email_html(
        title=f"Welcome to {cohort_name} — Join WhatsApp Group",
        preheader=f"Join the Official WhatsApp Group for {cohort_name} & view your pre-launch schedule!",
        badge_text="🎉 Pre-Launch Orientation & Community Access",
        badge_bg="rgba(16, 185, 129, 0.15)",
        badge_color="#34d399",
        student_name=student_name,
        main_message_html=main_msg,
        details_list=details,
        cta_text="👉 JOIN OFFICIAL WHATSAPP GROUP NOW",
        cta_url=whatsapp_link,
        footer_note=f"Official WhatsApp Group Link: <a href='{whatsapp_link}' style='color: #38bdf8;'>{whatsapp_link}</a>"
    )

    return send_email(student_email, subject, html_content, app=app)


def send_daily_session_email(student: dict, day_number: int, cohort: dict = None, app=None) -> tuple[bool, str]:
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
    outcomes_list_html = "".join([f"<li style='margin-bottom: 8px;'>✨ {out}</li>" for out in outcomes])

    main_msg = f"""
    Welcome to <strong>Day {day_number}</strong> of your Engineering Journey! Today's session is packed with practical insights.
    <br><br>
    <strong>Key Outcomes for Today:</strong>
    <ul style="padding-left: 20px; color: #cbd5e1; margin-top: 8px;">
      {outcomes_list_html}
    </ul>
    """

    details = [
        ("Session Day", f"Day {day_number}"),
        ("Topic Title", session_topic),
        ("Engineering Domain", domain)
    ]

    whatsapp_link = (cohort.get('whatsapp_link') if cohort else None) or 'https://chat.whatsapp.com/sample-group-link'
    footer_note = f"Stay connected with your cohort: <a href='{whatsapp_link}' style='color: #25D366; font-weight: 700;'>Join Official Cohort WhatsApp Group &rarr;</a>"

    html_content = build_responsive_email_html(
        title=f"Day {day_number}: {session_topic}",
        preheader=f"Day {day_number} of your Engineering Journey is now active!",
        badge_text=f"Day {day_number} Curriculum Active",
        badge_bg="rgba(56, 189, 248, 0.15)",
        badge_color="#38bdf8",
        student_name=student_name,
        main_message_html=main_msg,
        details_list=details,
        cta_text="Access Today's Session →",
        cta_url="https://engineeringpack.aivontraa.com/student/dashboard",
        footer_note=footer_note
    )

    return send_email(student_email, subject, html_content, app=app)


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
