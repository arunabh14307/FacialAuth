"""
OTP Service — Generates 6-digit one-time passwords and dispatches them via SMTP or dev fallback.
"""

import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def generate_otp(length=6):
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(recipient_email, otp_code, config):
    """
    Send OTP code to the recipient email address via SMTP.
    If SMTP server is configured, sends via network SMTP.
    Otherwise, logs to console and returns fallback status.
    Returns tuple: (success: bool, is_fallback: bool, message: str)
    """
    smtp_server = config.get('SMTP_SERVER', '').strip()
    if '@' in smtp_server:
        smtp_server = smtp_server.split('@')[-1]

    mail_from = config.get('MAIL_FROM_ADDRESS') or config.get('SMTP_USERNAME') or 'noreply@faceguard.local'

    subject = "FaceGuard Admin Access — One-Time Verification Password (OTP)"
    body = f"""Hello Admin,

Your One-Time Password (OTP) for accessing the FaceGuard Admin Portal is:

    ======================
            {otp_code}
    ======================

This OTP is valid for 5 minutes. If you did not request this access, please secure your credentials immediately.

Regards,
FaceGuard Security Team
"""

    if smtp_server:
        try:
            port = int(config.get('SMTP_PORT', 587))
            username = config.get('SMTP_USERNAME', '').strip()
            password = config.get('SMTP_PASSWORD', '').replace(' ', '').strip()
            use_tls = config.get('SMTP_USE_TLS', True)
            if isinstance(use_tls, str):
                use_tls = use_tls.lower() == 'true'

            msg = MIMEMultipart()
            msg['From'] = mail_from
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, port, timeout=12)
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)

            server.sendmail(mail_from, [recipient_email], msg.as_string())
            server.quit()
            print(f"[OTP SERVICE SUCCESS] Real email sent to {recipient_email} via SMTP ({smtp_server})")
            return True, False, f"OTP email sent successfully to {recipient_email}"
        except Exception as e:
            error_msg = str(e)
            print(f"[OTP SERVICE ERROR] Failed to send email via SMTP ({smtp_server}): {error_msg}")
            print(f"[OTP SERVICE FALLBACK] Code for {recipient_email}: [{otp_code}]")
            return True, True, f"SMTP delivery failed ({error_msg}). Dev OTP code generated."
    else:
        # Dev / Offline fallback mode
        print("\n" + "=" * 50)
        print(f"[OTP SERVICE - DEV FALLBACK]")
        print(f"Target Admin Email: {recipient_email}")
        print(f"Generated OTP Code: {otp_code}")
        print("Note: SMTP server host is not configured in Admin Settings.")
        print("=" * 50 + "\n")
        return True, True, f"SMTP Server not configured. Dev OTP code generated."

