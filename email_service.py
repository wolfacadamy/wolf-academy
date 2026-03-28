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
    Send a styled HTML invite email to an employee (bilingual Arabic/English).

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    if not Config.SMTP_SENDER or not Config.SMTP_PASSWORD:
        return False, "SMTP not configured. Set SMTP_SENDER and SMTP_PASSWORD in .env"

    sender = Config.SMTP_SENDER
    logo_url = f"{Config.BASE_URL}/static/logo.png"
    subject = f"دعوة للدورة: {course_title} — Wolf Academy"

    # Build bilingual HTML email
    html_body = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0; padding: 0;
                font-family: 'Segoe UI', 'Arial', 'Tahoma', sans-serif;
                background: #0a0a0f; color: #f0ece4;
            }}
            .wrapper {{
                max-width: 600px; margin: 0 auto;
                background: #0a0a0f;
            }}
            .header {{
                text-align: center;
                padding: 40px 30px 30px;
                background: linear-gradient(180deg, #0f1a15 0%, #0a0a0f 100%);
                border-bottom: 2px solid #073120;
            }}
            .header img {{
                max-width: 200px;
                height: auto;
            }}
            .header .subtitle {{
                color: #9a9aaa;
                font-size: 13px;
                margin-top: 8px;
                letter-spacing: 0.5px;
            }}
            .content {{
                padding: 35px 30px;
            }}
            .greeting {{
                font-size: 18px;
                color: #f0ece4;
                margin-bottom: 8px;
                font-weight: 600;
            }}
            .message {{
                font-size: 15px;
                line-height: 1.8;
                color: #b0b0ba;
                margin-bottom: 5px;
            }}
            .divider {{
                border: none;
                border-top: 1px solid #1a2a22;
                margin: 25px 0;
            }}
            .course-card {{
                background: linear-gradient(145deg, #111a16, #0d1210);
                border: 1px solid #1a3a2a;
                border-radius: 16px;
                padding: 28px;
                margin: 25px 0;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .course-card::before {{
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 3px;
                background: linear-gradient(90deg, transparent, #0d7a4f, transparent);
            }}
            .course-card h2 {{
                font-size: 22px;
                color: #f0ece4;
                margin: 0 0 6px;
                font-weight: 700;
            }}
            .course-card .meta {{
                color: #7a8a80;
                font-size: 13px;
            }}
            .btn {{
                display: inline-block;
                padding: 14px 40px;
                background: linear-gradient(135deg, #0d7a4f, #0a5236);
                color: #ffffff !important;
                font-size: 16px;
                font-weight: 700;
                text-decoration: none;
                border-radius: 10px;
                margin-top: 18px;
                letter-spacing: 0.3px;
            }}
            .link-fallback {{
                font-size: 13px;
                color: #6a7a70;
                margin-top: 20px;
                direction: ltr;
                text-align: center;
            }}
            .link-fallback a {{
                color: #0d7a4f;
                word-break: break-all;
            }}
            .footer {{
                border-top: 1px solid #1a2a22;
                padding: 25px 30px;
                text-align: center;
                color: #4a5a50;
                font-size: 12px;
                background: #080a09;
            }}
            .footer .brand {{
                color: #0d7a4f;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <!-- Header with Logo -->
            <div class="header">
                <img src="{logo_url}" alt="Wolf Academy">
                <div class="subtitle">بوابة التدريب للموظفين &bull; Staff Training Portal</div>
            </div>

            <!-- Content -->
            <div class="content">
                <!-- Arabic Section -->
                <div dir="rtl" style="text-align:right;">
                    <div class="greeting">مرحباً {employee_name} 👋</div>
                    <p class="message">
                        تم تسجيلك في دورة تدريبية جديدة. اضغط على الزر أدناه للبدء في التعلم!
                    </p>
                </div>

                <hr class="divider">

                <!-- English Section -->
                <div dir="ltr" style="text-align:left;">
                    <div class="greeting">Hi {employee_name} 👋</div>
                    <p class="message">
                        You have been enrolled in a new course. Click the button below to start learning!
                    </p>
                </div>

                <!-- Course Card -->
                <div class="course-card">
                    <h2>{course_title}</h2>
                    <div class="meta">تم التعيين من قبل المسؤول &bull; Assigned by your administrator</div>
                    <br>
                    <a href="{course_url}" class="btn">ابدأ الدورة &larr; Start Course &rarr;</a>
                </div>

                <!-- Link Fallback -->
                <div class="link-fallback">
                    إذا لم يعمل الزر، انسخ هذا الرابط في متصفحك:<br>
                    If the button doesn't work, copy this link:<br>
                    <a href="{course_url}">{course_url}</a>
                </div>
            </div>

            <!-- Footer -->
            <div class="footer">
                <p>&copy; <span class="brand">Wolf Academy</span> &middot; منصة تدريب الموظفين &middot; Staff Training Platform</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain-text fallback (bilingual)
    text_body = (
        f"مرحباً {employee_name},\n\n"
        f"تم تسجيلك في دورة: {course_title}\n"
        f"ابدأ الدورة من هنا: {course_url}\n\n"
        f"---\n\n"
        f"Hi {employee_name},\n\n"
        f"You've been enrolled in: {course_title}\n"
        f"Start the course here: {course_url}\n\n"
        f"— Wolf Academy"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Wolf Academy <{sender}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

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
