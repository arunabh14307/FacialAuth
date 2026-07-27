import random
import string
import smtplib
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def generate_otp(length=6):
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


def send_via_http_api(recipient_email, otp_code, subject, body, config):
    """
    Dispatch email using HTTPS REST API (Brevo or Resend) on Port 443.
    Bypasses raw TCP SMTP port restrictions and datacenter IP blocks.
    """
    brevo_key = config.get('BREVO_API_KEY') or os.environ.get('BREVO_API_KEY', '')
    resend_key = config.get('RESEND_API_KEY') or os.environ.get('RESEND_API_KEY', '')

    # Strategy A: Brevo HTTP API
    if brevo_key:
        try:
            sender_email = config.get('MAIL_FROM_ADDRESS') or config.get('SMTP_USERNAME') or ''
            if not '@' in sender_email:
                sender_email = 'no-reply@faceguard.local'

            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": brevo_key.strip(),
                "content-type": "application/json"
            }
            payload = {
                "sender": {"name": "FaceGuard Security", "email": sender_email},
                "to": [{"email": recipient_email}],
                "subject": subject,
                "textContent": body
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code in [200, 201, 202]:
                print(f"[OTP SERVICE SUCCESS] Email delivered to {recipient_email} via Brevo HTTPS API")
                return True, False, f"OTP email delivered via Brevo HTTP API to {recipient_email}"
            else:
                print(f"[OTP SERVICE WARN] Brevo API status {res.status_code}: {res.text}")
                return False, True, f"Brevo API error ({res.status_code}): {res.text}"
        except Exception as e:
            print(f"[OTP SERVICE WARN] Brevo API failed: {e}")

    # Strategy B: Resend HTTP API
    if resend_key:
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_key.strip()}",
                "Content-Type": "application/json"
            }
            sender = config.get('MAIL_FROM_ADDRESS') or 'onboarding@resend.dev'
            if 'gmail.com' in sender or 'faceguard.local' in sender or not '@' in sender:
                sender = 'onboarding@resend.dev'

            payload = {
                "from": f"FaceGuard Security <{sender}>" if '<' not in sender else sender,
                "to": [recipient_email],
                "subject": subject,
                "text": body
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code in [200, 201, 202]:
                print(f"[OTP SERVICE SUCCESS] Email delivered to {recipient_email} via Resend HTTPS API")
                return True, False, f"OTP email delivered via Resend HTTP API to {recipient_email}"
            else:
                print(f"[OTP SERVICE WARN] Resend API status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[OTP SERVICE WARN] Resend API failed: {e}")

    return False, True, "No HTTP Email API configured"


def send_otp_email(recipient_email, otp_code, config):
    """
    Send OTP code to the recipient email address via HTTPS API or SMTP.
    Returns tuple: (success: bool, is_fallback: bool, message: str)
    """
    smtp_server = (config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER') or 'smtp.gmail.com').strip()
    if '@' in smtp_server and 'brevo.com' not in smtp_server:
        smtp_server = smtp_server.split('@')[-1]

    if smtp_server.lower() in ['gmail.com', 'outlook.com', 'office365.com', 'yahoo.com']:
        smtp_server = 'smtp.' + smtp_server.lower()

    username = (config.get('SMTP_USERNAME') or os.environ.get('SMTP_USERNAME') or '').strip()
    password = (config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD') or '').replace(' ', '').strip()
    mail_from = config.get('MAIL_FROM_ADDRESS') or os.environ.get('MAIL_FROM_ADDRESS') or username

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

    # Check HTTPS API first
    api_success, api_fallback, api_msg = send_via_http_api(recipient_email, otp_code, subject, body, config)
    if api_success and not api_fallback:
        return True, False, api_msg

    if smtp_server:
        port = int(config.get('SMTP_PORT', 587))
        use_tls = config.get('SMTP_USE_TLS', True)
        if isinstance(use_tls, str):
            use_tls = use_tls.lower() == 'true'

        msg = MIMEMultipart()
        msg['From'] = mail_from
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Multi-port strategy: Try user port, 2525, 587, 465 automatically
        ports_to_try = [port, 2525, 587, 465] if 'brevo' in smtp_server.lower() else [port, 465, 587, 2525]
        ports_to_try = list(dict.fromkeys(ports_to_try))

        last_error = "Unknown error"
        for p in ports_to_try:
            try:
                if p == 465:
                    server = smtplib.SMTP_SSL(smtp_server, 465, timeout=10)
                else:
                    server = smtplib.SMTP(smtp_server, p, timeout=10)
                    if use_tls or p in [587, 2525]:
                        server.starttls()

                if username and password:
                    server.login(username, password)

                server.sendmail(mail_from, [recipient_email], msg.as_string())
                server.quit()
                print(f"[OTP SERVICE SUCCESS] Real email sent to {recipient_email} via SMTP ({smtp_server}:{p})")
                return True, False, f"OTP email sent successfully to {recipient_email}"
            except Exception as e:
                last_error = str(e)
                print(f"[OTP SERVICE WARN] Port {p} failed on {smtp_server}: {last_error}")

        print(f"[OTP SERVICE FALLBACK] All ports failed for {recipient_email}: [{otp_code}]")
        return True, True, f"SMTP delivery failed ({last_error}). Dev OTP code generated."
    else:
        # Dev / Offline fallback mode
        print("\n" + "=" * 50)
        print(f"[OTP SERVICE - DEV FALLBACK]")
        print(f"Target Admin Email: {recipient_email}")
        print(f"Generated OTP Code: {otp_code}")
        print("Note: SMTP server host is not configured in Admin Settings.")
        print("=" * 50 + "\n")
        return True, True, f"SMTP Server not configured. Dev OTP code generated."

