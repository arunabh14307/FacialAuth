"""
Application & Integration Tests using standard unittest framework.
"""

import unittest
from app import app


class AuthIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health_api(self):
        """Verify REST API health check endpoint."""
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'healthy')

    def test_security_headers(self):
        """Verify OWASP security headers on response."""
        response = self.client.get('/')
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')

    def test_admin_login_page(self):
        """Verify admin login page loads."""
        response = self.client.get('/admin/login')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
