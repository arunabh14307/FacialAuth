"""
OTP & Email Delivery Engine — Multi-protocol SMTP & HTTP API Mail Dispatcher.
Uses dedicated IPv4-enforced SMTP transport subclasses (IPv4SMTP & IPv4SMTP_SSL)
to prevent container IPv6 network unreachable errors on cloud platforms like Render/AWS/GCP
without globally monkey-patching socket functions.
"""

import random
import string
import smtplib
import socket
import traceback
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.modules.logger import logger, log_security_event


class IPv4SMTP(smtplib.SMTP):
    """
    Subclass of smtplib.SMTP that forces IPv4 (socket.AF_INET) socket creation
    without modifying global socket behavior. This resolves container IPv6 unreachable
    errors on cloud platforms like Render/AWS/GCP where container interfaces lack IPv6 gateways.
    """
    def _get_socket(self, host, port, timeout):
        # Resolve IPv4 addresses specifically for this SMTP connection
        res = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if not res:
            raise socket.gaierror(f"Could not resolve IPv4 address for {host}:{port}")

        af, socktype, proto, canonname, sa = res[0]
        sock = socket.socket(af, socktype, proto)
        if timeout is not None and timeout != socket._GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(timeout)
        if self.source_address:
            sock.bind(self.source_address)
        sock.connect(sa)
        return sock


class IPv4SMTP_SSL(smtplib.SMTP_SSL):
    """
    Subclass of smtplib.SMTP_SSL that forces IPv4 (socket.AF_INET) socket creation
    without modifying global socket behavior, while preserving SNI TLS certificate verification.
    """
    def _get_socket(self, host, port, timeout):
        # Resolve IPv4 addresses specifically for this SMTP_SSL connection
        res = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if not res:
            raise socket.gaierror(f"Could not resolve IPv4 address for {host}:{port}")

        af, socktype, proto, canonname, sa = res[0]
        sock = socket.socket(af, socktype, proto)
        if timeout is not None and timeout != socket._GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(timeout)
        if self.source_address:
            sock.bind(self.source_address)
        sock.connect(sa)

        # Wrap socket with SSL context, maintaining SNI server_hostname verification
        server_hostname = self._host if self._host else host
        return self.context.wrap_socket(sock, server_hostname=server_hostname)


def generate_otp(length=6):
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


def send_via_http_api(recipient_email, otp_code, subject, body, config):
    """
    Dispatch email using HTTPS REST API (Brevo or Resend) on Port 443.
    """
    brevo_key = config.get('BREVO_API_KEY') or os.environ.get('BREVO_API_KEY', '')
    resend_key = config.get('RESEND_API_KEY') or os.environ.get('RESEND_API_KEY', '')

    if brevo_key:
        try:
            sender_email = config.get('MAIL_FROM_ADDRESS') or config.get('SMTP_USERNAME') or os.environ.get('MAIL_FROM_ADDRESS') or os.environ.get('SMTP_USERNAME') or ''
            if not '@' in sender_email:
                sender_email = 'no-reply@faceguard.local'

            print(f"[HTTP API CONNECTING] Dispatching via Brevo HTTPS API (Port 443)...")
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
                print(f"[HTTP API SUCCESS] Email delivered to {recipient_email} via Brevo API")
                logger.info(f"OTP email sent to {recipient_email} via Brevo HTTP API")
                return True, f"OTP email delivered via Brevo HTTP API to {recipient_email}"
            else:
                print(f"[HTTP API FAILURE] Brevo API status {res.status_code}: {res.text}")
                logger.warning(f"Brevo HTTP API failed ({res.status_code}): {res.text}")
        except Exception as e:
            full_tb = traceback.format_exc()
            print(f"[HTTP API ERROR] Brevo API exception:\n{full_tb}")
            logger.error(f"Brevo HTTP API exception:\n{full_tb}")

    if resend_key:
        try:
            print(f"[HTTP API CONNECTING] Dispatching via Resend HTTPS API (Port 443)...")
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
                print(f"[HTTP API SUCCESS] Email delivered to {recipient_email} via Resend API")
                logger.info(f"OTP email sent to {recipient_email} via Resend HTTP API")
                return True, f"OTP email delivered via Resend HTTP API to {recipient_email}"
            else:
                print(f"[HTTP API FAILURE] Resend API status {res.status_code}: {res.text}")
                logger.warning(f"Resend HTTP API failed ({res.status_code}): {res.text}")
        except Exception as e:
            full_tb = traceback.format_exc()
            print(f"[HTTP API ERROR] Resend API exception:\n{full_tb}")
            logger.error(f"Resend HTTP API exception:\n{full_tb}")

    return False, "No HTTP Email API configured or all HTTP APIs failed"


def send_otp_email(recipient_email, otp_code, config):
    """
    Send OTP code to recipient email address via HTTPS API or SMTP.
    Returns tuple: (success: bool, message: str)
    """
    recipient_email = (recipient_email or '').strip()
    if not recipient_email or '@' not in recipient_email:
        err_msg = f"Invalid recipient email address: '{recipient_email}'"
        print(f"[SMTP FAILURE] {err_msg}")
        logger.error(err_msg)
        return False, err_msg

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

    # Check HTTPS REST API first if configured
    api_success, api_msg = send_via_http_api(recipient_email, otp_code, subject, body, config)
    if api_success:
        return True, api_msg

    # Load SMTP settings from config, environment variables, or database fallbacks
    smtp_server = (config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER') or 'smtp.gmail.com').strip()
    if '@' in smtp_server and 'brevo.com' not in smtp_server:
        smtp_server = smtp_server.split('@')[-1]
    if smtp_server.lower() in ['gmail.com', 'outlook.com', 'office365.com', 'yahoo.com']:
        smtp_server = 'smtp.' + smtp_server.lower()

    smtp_port = int(config.get('SMTP_PORT') or os.environ.get('SMTP_PORT') or 465)
    username = (config.get('SMTP_USERNAME') or os.environ.get('SMTP_USERNAME') or 'arun12507086@gmail.com').strip()
    password = (config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD') or 'rmvephrzvgeuetkj').replace(' ', '').strip()
    mail_from = (config.get('MAIL_FROM_ADDRESS') or os.environ.get('MAIL_FROM_ADDRESS') or username or 'arun12507086@gmail.com').strip()

    if not username or not password:
        err_msg = "SMTP Username or Password missing in system configuration."
        print(f"[SMTP FAILURE] {err_msg}")
        logger.error(f"[SMTP FAILURE] {err_msg}")
        return False, err_msg

    # Prepare MIME Message
    msg = MIMEMultipart()
    msg['From'] = f"FaceGuard Security <{mail_from}>" if '<' not in mail_from else mail_from
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Single or Multi-port Connection Strategy
    # Port 465 MUST use SSL (IPv4SMTP_SSL). Port 587 MUST use STARTTLS (IPv4SMTP).
    ports_to_try = [smtp_port, 465, 587]
    ports_to_try = list(dict.fromkeys(ports_to_try))

    last_error_details = "Unknown connection error"

    for p in ports_to_try:
        conn_method = "SMTP_SSL" if p == 465 else "STARTTLS"

        # DNS Resolution Diagnostic for IPv4
        ipv4_addrs = []
        try:
            dns_info = socket.getaddrinfo(smtp_server, p, socket.AF_INET, socket.SOCK_STREAM)
            for res in dns_info:
                ip = res[4][0]
                if ip not in ipv4_addrs:
                    ipv4_addrs.append(ip)
        except Exception as dns_e:
            logger.warning(f"[SMTP DNS DIAGNOSTIC WARNING] Resolution failed for {smtp_server}:{p} — {dns_e}")

        diag_header = (
            f"[SMTP DIAGNOSTIC]\n"
            f"  - Server: {smtp_server}\n"
            f"  - Port: {p}\n"
            f"  - Connection Method: {conn_method}\n"
            f"  - Enforced Transport: IPv4 Subclass (AF_INET)\n"
            f"  - Resolved IPv4 Addresses: {ipv4_addrs if ipv4_addrs else 'None'}"
        )
        print(diag_header)
        logger.info(diag_header)

        try:
            print(f"[SMTP CONNECTING] Connecting to {smtp_server}:{p} ({conn_method}) via IPv4 transport...")
            logger.info(f"[SMTP CONNECTING] Connecting to {smtp_server}:{p} ({conn_method}) via IPv4 transport")

            if p == 465:
                # SSL Connection for Port 465 using IPv4-enforced SMTP_SSL transport subclass
                server = IPv4SMTP_SSL(smtp_server, 465, timeout=15)
            else:
                # Standard Connection for Port 587 using IPv4-enforced SMTP transport subclass + STARTTLS
                server = IPv4SMTP(smtp_server, p, timeout=15)
                print(f"[SMTP STARTTLS] Initiating STARTTLS handshake on {smtp_server}:{p}...")
                logger.info(f"[SMTP STARTTLS] Initiating STARTTLS on {smtp_server}:{p}")
                server.starttls()

            print(f"[SMTP AUTHENTICATING] Authenticating user '{username}' on {smtp_server}:{p}...")
            logger.info(f"[SMTP AUTHENTICATING] Authenticating {username} on port {p}")
            server.login(username, password)

            print(f"[SMTP SENDING] Dispatching mail from {mail_from} to {recipient_email}...")
            logger.info(f"[SMTP SENDING] Sending from {mail_from} to {recipient_email}")
            server.sendmail(mail_from, [recipient_email], msg.as_string())
            server.quit()

            success_msg = f"OTP email delivered successfully to {recipient_email} via SMTP ({smtp_server}:{p})"
            print(f"[SMTP SUCCESS] {success_msg}")
            logger.info(f"[SMTP SUCCESS] {success_msg}")
            log_security_event("OTP_EMAIL_SENT", f"Recipient: {recipient_email} via {smtp_server}:{p}")
            return True, success_msg

        except smtplib.SMTPAuthenticationError as e:
            full_tb = traceback.format_exc()
            err_text = e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
            last_error_details = f"SMTP Authentication Error ({e.smtp_code}): {err_text}"
            diag_err = (
                f"[SMTP FAILURE DIAGNOSTIC] Authentication failed on {smtp_server}:{p}\n"
                f"Full Traceback:\n{full_tb}"
            )
            print(diag_err)
            logger.error(diag_err)
            break

        except Exception as e:
            full_tb = traceback.format_exc()
            last_error_details = f"{type(e).__name__}: {str(e)}"
            diag_err = (
                f"[SMTP FAILURE DIAGNOSTIC] Port {p} ({conn_method}) failed on {smtp_server}:\n"
                f"Full Traceback:\n{full_tb}"
            )
            print(diag_err)
            logger.error(diag_err)

    final_err = f"SMTP delivery failed: {last_error_details}"
    print(f"[SMTP ERROR] {final_err}")
    logger.error(f"[SMTP ERROR] {final_err}")
    log_security_event("OTP_EMAIL_FAILED", f"Recipient: {recipient_email} | Error: {last_error_details}")

    return False, final_err
