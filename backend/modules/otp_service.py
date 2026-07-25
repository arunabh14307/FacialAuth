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
            sender_email = config.get('MAIL_FROM_ADDRESS') or config.get('SMTP_USERNAME') or 'arun12507086@gmail.com'
            if 'faceguard.local' in sender_email or not '@' in sender_email:
                sender_email = 'arun12507086@gmail.com'

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
            payload = {
                "from": config.get('MAIL_FROM_ADDRESS', 'onboarding@resend.dev'),
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

    # Check HTTPS API first
    api_success, api_fallback, api_msg = send_via_http_api(recipient_email, otp_code, subject, body, config)
    if api_success and not api_fallback:
        return True, False, api_msg

    if smtp_server:
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

        # Strategy 1: Direct SSL Port 465 (Bypasses STARTTLS firewall blocks)
        if port == 465 or 'gmail' in smtp_server.lower():
            try:
                server = smtplib.SMTP_SSL(smtp_server, 465, timeout=12)
                if username and password:
                    server.login(username, password)
                server.sendmail(mail_from, [recipient_email], msg.as_string())
                server.quit()
                print(f"[OTP SERVICE SUCCESS] Real email sent to {recipient_email} via SMTP_SSL (port 465)")
                return True, False, f"OTP email sent successfully to {recipient_email}"
            except Exception as e:
                print(f"[OTP SERVICE WARN] Port 465 SSL failed: {e}. Trying TLS port {port}...")

        # Strategy 2: TLS Port 587
        try:
            server = smtplib.SMTP(smtp_server, port, timeout=12)
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)

            server.sendmail(mail_from, [recipient_email], msg.as_string())
            server.quit()
            print(f"[OTP SERVICE SUCCESS] Real email sent to {recipient_email} via SMTP ({smtp_server}:{port})")
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

