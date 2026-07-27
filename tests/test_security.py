"""
Security & Encryption Unit Tests using standard unittest framework.
"""

import unittest
import numpy as np
from backend.modules.security import (
    encrypt_embedding,
    decrypt_embedding,
    validate_password_strength,
    sanitize_input
)


class SecurityTestCase(unittest.TestCase):
    def test_face_embedding_encryption_decryption(self):
        """Verify AES-256 Fernet embedding encryption and decryption."""
        original_vector = np.random.rand(128).astype(np.float32)
        encrypted_blob = encrypt_embedding(original_vector)

        self.assertIsInstance(encrypted_blob, bytes)
        self.assertTrue(encrypted_blob.startswith(b'ENC1'))

        decrypted_vector = decrypt_embedding(encrypted_blob)
        self.assertIsNotNone(decrypted_vector)
        self.assertTrue(np.allclose(original_vector, decrypted_vector))

    def test_password_strength_validator(self):
        """Verify password policy enforcement."""
        is_valid, errors, score = validate_password_strength("weak")
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

        is_valid, errors, score = validate_password_strength("SuperSecret@2026")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertGreaterEqual(score, 80)

    def test_input_sanitizer(self):
        """Verify XSS and injection sanitization."""
        dirty = "<script>alert('xss')</script> John Doe"
        clean = sanitize_input(dirty)
        self.assertNotIn("<script>", clean)
        self.assertIn("John Doe", clean)

    def test_ipv4_smtp_client_creator(self):
        """Verify create_ipv4_smtp_client helper function exists and is callable."""
        from backend.modules.otp_service import create_ipv4_smtp_client
        self.assertTrue(callable(create_ipv4_smtp_client))


if __name__ == '__main__':
    unittest.main()
