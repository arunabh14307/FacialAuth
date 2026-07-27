"""
OTP & Email Delivery Engine — Multi-protocol SMTP & HTTP API Mail Dispatcher.
Uses direct IPv4 socket creation (socket.AF_INET) attached to standard smtplib instances
without subclassing or monkey-patching, providing robust 220 banner reading and stage timing.
"""

import random
import string
import smtplib
import socket
import ssl
import time
import traceback
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.modules.logger import logger, log_security_event


def create_ipv4_smtp_client(smtp_server, port, timeout=60):
    """
    Create a standard smtplib.SMTP or smtplib.SMTP_SSL instance connected via
    an explicit IPv4 socket (socket.AF_INET) without subclassing smtplib or monkey-patching.
    Reads initial 220 server greeting banner reliably.
    """
    t_dns_start = time.time()
    dns_res = socket.getaddrinfo(smtp_server, port, socket.AF_INET, socket.SOCK_STREAM)
    dns_duration = time.time() - t_dns_start
    if not dns_res:
        raise socket.gaierror(f"Could not resolve IPv4 address for {smtp_server}:{port}")

    ipv4_ip = dns_res[0][4][0]
    sa = (ipv4_ip, port)

    print(f"[TIMING STAGE 1 - DNS RESOLUTION] Host: {smtp_server}:{port} -> IPv4 {ipv4_ip} (Elapsed: {dns_duration:.3f}s)")
    logger.info(f"[TIMING STAGE 1 - DNS RESOLUTION] Host: {smtp_server}:{port} -> IPv4 {ipv4_ip} (Elapsed: {dns_duration:.3f}s)")

    # TCP Connect
    t_tcp_start = time.time()
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.settimeout(timeout)
    raw_sock.connect(sa)
    tcp_duration = time.time() - t_tcp_start
    print(f"[TIMING STAGE 2 - TCP CONNECT] Connected to {ipv4_ip}:{port} (Elapsed: {tcp_duration:.3f}s)")
    logger.info(f"[TIMING STAGE 2 - TCP CONNECT] Connected to {ipv4_ip}:{port} (Elapsed: {tcp_duration:.3f}s)")

    if port == 465:
        # SSL Handshake for Port 465
        t_ssl_start = time.time()
        ctx = ssl.create_default_context()
        ssl_sock = ctx.wrap_socket(raw_sock, server_hostname=smtp_server)
        ssl_duration = time.time() - t_ssl_start
        print(f"[TIMING STAGE 3 - SSL HANDSHAKE] Completed SSL handshake with {smtp_server} (Elapsed: {ssl_duration:.3f}s)")
        logger.info(f"[TIMING STAGE 3 - SSL HANDSHAKE] Completed SSL handshake with {smtp_server} (Elapsed: {ssl_duration:.3f}s)")

        # Instantiate standard smtplib.SMTP_SSL
        t_banner_start = time.time()
        server = smtplib.SMTP_SSL(timeout=timeout)
        server._host = smtp_server
        server._port = port
        server.sock = ssl_sock
        server.file = None

        code, msg = server.getreply()
        banner_duration = time.time() - t_banner_start
        print(f"[TIMING STAGE 4 - BANNER 220 GREETING] Received banner '{code} {msg.decode() if isinstance(msg, bytes) else msg}' in {banner_duration:.3f}s")
        logger.info(f"[TIMING STAGE 4 - BANNER 220 GREETING] Received banner '{code}' in {banner_duration:.3f}s")

        if code != 220:
            server.close()
            raise smtplib.SMTPConnectError(code, msg)
        return server
    else:
        # Port 587 STARTTLS
        t_banner_start = time.time()
        server = smtplib.SMTP(timeout=timeout)
        server._host = smtp_server
        server._port = port
        server.sock = raw_sock
        server.file = None

        code, msg = server.getreply()
        banner_duration = time.time() - t_banner_start
        print(f"[TIMING STAGE 4 - BANNER 220 GREETING] Received banner '{code} {msg.decode() if isinstance(msg, bytes) else msg}' in {banner_duration:.3f}s")
        logger.info(f"[TIMING STAGE 4 - BANNER 220 GREETING] Received banner '{code}' in {banner_duration:.3f}s")

        if code != 220:
            server.close()
            raise smtplib.SMTPConnectError(code, msg)
        return server


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
    Send OTP code to recipient email address via HTTPS API or SMTP with full stage-by-stage timing.
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

    # Multi-port Strategy (Testing with 60-second timeout)
    ports_to_try = [smtp_port, 465, 587]
    ports_to_try = list(dict.fromkeys(ports_to_try))

    last_error_details = "Unknown connection error"

    for p in ports_to_try:
        conn_method = "SMTP_SSL" if p == 465 else "STARTTLS"
        print(f"\n========================================================")
        print(f"[SMTP TIMING DIAGNOSTIC] Initiating test on {smtp_server}:{p} ({conn_method}) | Timeout=60s")
        print(f"========================================================")

        current_stage = "INIT"
        stage_start = time.time()

        try:
            current_stage = "CREATE_IPV4_CLIENT_AND_READ_BANNER"
            stage_start = time.time()
            server = create_ipv4_smtp_client(smtp_server, p, timeout=60)

            if p != 465:
                # Stage 5: STARTTLS Handshake
                current_stage = "STARTTLS_HANDSHAKE"
                stage_start = time.time()
                print(f"[TIMING STAGE 5] Initiating STARTTLS handshake on {smtp_server}:{p}...")
                server.starttls()
                stage_duration = time.time() - stage_start
                starttls_log = f"[TIMING STAGE 5 SUCCESS] STARTTLS handshake completed in {stage_duration:.3f}s"
                print(starttls_log)
                logger.info(starttls_log)

            # Stage 6: SMTP Authentication (server.login)
            current_stage = "AUTHENTICATION_SERVER_LOGIN"
            stage_start = time.time()
            print(f"[TIMING STAGE 6] Authenticating user '{username}' via server.login()...")
            server.login(username, password)
            stage_duration = time.time() - stage_start
            auth_log = f"[TIMING STAGE 6 SUCCESS] Server login authenticated successfully in {stage_duration:.3f}s"
            print(auth_log)
            logger.info(auth_log)

            # Stage 7: Sendmail (server.sendmail)
            current_stage = "SENDMAIL"
            stage_start = time.time()
            print(f"[TIMING STAGE 7] Dispatching mail body from {mail_from} to {recipient_email}...")
            server.sendmail(mail_from, [recipient_email], msg.as_string())
            stage_duration = time.time() - stage_start
            send_log = f"[TIMING STAGE 7 SUCCESS] sendmail() completed in {stage_duration:.3f}s"
            print(send_log)
            logger.info(send_log)

            # Stage 8: Connection Quit
            current_stage = "QUIT"
            stage_start = time.time()
            server.quit()
            stage_duration = time.time() - stage_start
            quit_log = f"[TIMING STAGE 8 SUCCESS] server.quit() completed in {stage_duration:.3f}s"
            print(quit_log)
            logger.info(quit_log)

            success_msg = f"OTP email delivered successfully to {recipient_email} via SMTP ({smtp_server}:{p})"
            print(f"[SMTP SUCCESS] {success_msg}")
            logger.info(f"[SMTP SUCCESS] {success_msg}")
            log_security_event("OTP_EMAIL_SENT", f"Recipient: {recipient_email} via {smtp_server}:{p}")
            return True, success_msg

        except smtplib.SMTPAuthenticationError as e:
            stage_duration = time.time() - stage_start
            full_tb = traceback.format_exc()
            err_text = e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
            last_error_details = f"SMTP Authentication Error ({e.smtp_code}): {err_text}"
            diag_err = (
                f"[TIMING STAGE FAILED: {current_stage}] Authentication failed after {stage_duration:.3f}s on {smtp_server}:{p}\n"
                f"Full Traceback:\n{full_tb}"
            )
            print(diag_err)
            logger.error(diag_err)
            break

        except (socket.timeout, TimeoutError) as e:
            stage_duration = time.time() - stage_start
            full_tb = traceback.format_exc()
            last_error_details = f"TimeoutError at STAGE '{current_stage}' after {stage_duration:.3f}s: {e}"
            diag_err = (
                f"\n[TIMING TIMEOUT DETECTED]\n"
                f"  - Failed Stage: {current_stage}\n"
                f"  - Elapsed Time in Stage: {stage_duration:.3f}s\n"
                f"  - Host:Port: {smtp_server}:{p} ({conn_method})\n"
                f"Full Traceback:\n{full_tb}"
            )
            print(diag_err)
            logger.error(diag_err)

        except Exception as e:
            stage_duration = time.time() - stage_start
            full_tb = traceback.format_exc()
            last_error_details = f"{type(e).__name__} at STAGE '{current_stage}' after {stage_duration:.3f}s: {e}"
            diag_err = (
                f"\n[TIMING FAILURE DETECTED]\n"
                f"  - Failed Stage: {current_stage}\n"
                f"  - Elapsed Time in Stage: {stage_duration:.3f}s\n"
                f"  - Host:Port: {smtp_server}:{p} ({conn_method})\n"
                f"Full Traceback:\n{full_tb}"
            )
            print(diag_err)
            logger.error(diag_err)

    final_err = f"SMTP delivery failed: {last_error_details}"
    print(f"[SMTP ERROR] {final_err}")
    logger.error(f"[SMTP ERROR] {final_err}")
    log_security_event("OTP_EMAIL_FAILED", f"Recipient: {recipient_email} | Error: {last_error_details}")

    return False, final_err
