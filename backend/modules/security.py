"""
Security Engine — Input Sanitization, Password Policy, Security Headers, and Embedding Protection.
"""

import os
import re
import html
import hmac
import hashlib
import pickle


def get_encryption_key(key_override=None):
    """Derive a stable 32-byte key from SECRET_KEY or ENCRYPTION_KEY env var."""
    raw_key = key_override or os.environ.get('ENCRYPTION_KEY') or os.environ.get('SECRET_KEY', 'facial-recog-secret-key-change-in-production')
    return hashlib.sha256(raw_key.encode('utf-8')).digest()


def encrypt_embedding(face_encoding, key_override=None):
    """
    Serialize and encrypt a face encoding numpy array/vector.
    Returns encrypted binary blob with HMAC header.
    """
    data = pickle.dumps(face_encoding)
    key = get_encryption_key(key_override)
    
    # Generate random 16-byte IV/salt
    iv = os.urandom(16)
    
    # Generate keystream using HMAC-SHA256
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(data):
        h = hmac.new(key, iv + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        keystream.extend(h)
        counter += 1
        
    # XOR cipher
    encrypted_payload = bytes(a ^ b for a, b in zip(data, keystream[:len(data)]))
    
    # Signature to detect tampering
    signature = hmac.new(key, iv + encrypted_payload, hashlib.sha256).digest()
    
    # Format: MAC (32) + IV (16) + Encrypted Payload
    return b'ENC1' + signature + iv + encrypted_payload


def decrypt_embedding(blob, key_override=None):
    """
    Decrypt and deserialize a face encoding binary blob.
    Backward Compatible: If blob is unencrypted legacy pickle, loads it directly without error.
    """
    if not isinstance(blob, bytes):
        return None
        
    # Check for ENC1 header magic bytes
    if blob.startswith(b'ENC1'):
        try:
            key = get_encryption_key(key_override)
            signature = blob[4:36]
            iv = blob[36:52]
            encrypted_payload = blob[52:]
            
            # Verify signature
            expected_sig = hmac.new(key, iv + encrypted_payload, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected_sig):
                raise ValueError("Embedding tampering detected or invalid encryption key.")
                
            # Decrypt keystream
            keystream = bytearray()
            counter = 0
            while len(keystream) < len(encrypted_payload):
                h = hmac.new(key, iv + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
                keystream.extend(h)
                counter += 1
                
            decrypted_data = bytes(a ^ b for a, b in zip(encrypted_payload, keystream[:len(encrypted_payload)]))
            return pickle.loads(decrypted_data)
        except Exception:
            pass
            
    # Legacy fallback: Unencrypted pickle load
    try:
        return pickle.loads(blob)
    except Exception:
        return None


def validate_password_strength(password):
    """
    Enforce strong enterprise password policy.
    Requires: Min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character.
    Returns: (is_valid: bool, errors: list[str], score: int 0-100)
    """
    errors = []
    if not password:
        return False, ["Password cannot be empty."], 0

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one numerical digit (0-9).")
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]', password):
        errors.append("Password must contain at least one special character (e.g. !@#$%).")

    # Score calculation
    score = 0
    if len(password) >= 8: score += 20
    if len(password) >= 12: score += 20
    if re.search(r'[A-Z]', password): score += 15
    if re.search(r'[a-z]', password): score += 15
    if re.search(r'\d', password): score += 15
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]', password): score += 15

    is_valid = len(errors) == 0
    return is_valid, errors, score


def sanitize_input(value):
    """Sanitize string inputs to prevent XSS and injection attacks."""
    if not isinstance(value, str):
        return value
    # Strip dangerous HTML tags and escape HTML special characters
    clean = html.escape(value.strip())
    # Remove NULL bytes
    clean = clean.replace('\x00', '')
    return clean


def apply_security_headers(response):
    """Apply OWASP recommended security headers to HTTP response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self';"
    )
    return response
