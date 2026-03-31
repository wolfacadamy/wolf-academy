"""
Email service for Wolf Academy LMS.
Sends course invite emails to employees via SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config


def send_invite_email(to_email, employee_name, course_title, course_url):
    """
    Send a styled HTML invite email to an employee.

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    if not Config.SMTP_SENDER or not Config.SMTP_PASSWORD:
        return False, "SMTP not configured. Set SMTP_SENDER and SMTP_PASSWORD in .env"

    sender = Config.SMTP_SENDER
    subject = f"You're Invited: {course_title} — Wolf Academy"

    # Build HTML email
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0; padding: 0;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #0a0a0f; color: #f0ece4;
            }}
            .container {{
                max-width: 560px; margin: 0 auto;
                padding: 40px 30px;
            }}
            .header {{
                text-align: center;
                padding-bottom: 30px;
                border-bottom: 1px solid #2a2a3a;
            }}
            .header h1 {{
                font-size: 28px;
                color: #d4a843;
                margin: 10px 0 5px;
            }}
            .header .subtitle {{
                color: #9a9aaa;
                font-size: 14px;
            }}
            .body {{
                padding: 30px 0;
            }}
            .body p {{
                font-size: 16px;
                line-height: 1.7;
                color: #ccc;
                margin-bottom: 15px;
            }}
            .course-card {{
                background: #1a1a26;
                border: 1px solid #2a2a3a;
                border-radius: 12px;
                padding: 24px;
                margin: 24px 0;
                text-align: center;
            }}
            .course-card h2 {{
                font-size: 22px;
                color: #f0ece4;
                margin: 0 0 8px;
            }}
            .course-card .meta {{
                color: #9a9aaa;
                font-size: 13px;
            }}
            .btn {{
                display: inline-block;
                padding: 14px 36px;
                background: #d4a843;
                color: #0a0a0f !important;
                font-size: 16px;
                font-weight: 700;
                text-decoration: none;
                border-radius: 8px;
                margin-top: 10px;
            }}
            .footer {{
                border-top: 1px solid #2a2a3a;
                padding-top: 20px;
                text-align: center;
                color: #6a6a7a;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div style="font-size:36px;">&#128058;</div>
                <h1>Wolf Academy</h1>
                <div class="subtitle">Staff Learning Portal</div>
            </div>
            <div class="body">
                <p>Hi <strong>{employee_name}</strong>,</p>
                <p>You have been enrolled in a new course. Click the button below to start learning!</p>

                <div class="course-card">
                    <h2>{course_title}</h2>
                    <div class="meta">Assigned by your administrator</div>
                    <br>
                    <a href="{course_url}" class="btn">Start Course &rarr;</a>
                </div>

                <p style="font-size:14px; color:#9a9aaa;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{course_url}" style="color:#d4a843;">{course_url}</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; Wolf Academy &middot; Staff Training Platform</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain-text fallback
    text_body = (
        f"Hi {employee_name},\\n\\n"
        f"You've been enrolled in: {course_title}\\n\\n"
        f"Start the course here: {course_url}\\n\\n"
        f"— Wolf Academy"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Wolf Academy <{sender}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, Config.SMTP_PASSWORD)
        server.sendmail(sender, to_email, msg.as_string())
        server.quit()
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check your email/password in .env"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Email error: {str(e)}"
