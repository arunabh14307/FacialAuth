# RESTful API & OpenAPI Documentation

**FaceGuard Enterprise** provides a versioned REST API (`/api/v1`) for system health monitoring, analytics reporting, user management, and OpenAPI integration.

---

## Endpoints Summary

### 1. Health Check
- **Endpoint**: `GET /api/v1/health`
- **Description**: Returns system database connection and service health status.
- **Response**:
  ```json
  {
    "database_connected": true,
    "status": "healthy",
    "timestamp": 1774635600,
    "version": "2.0.0-enterprise"
  }
  ```

---

### 2. Facial Access Analytics
- **Endpoint**: `GET /api/v1/analytics`
- **Description**: Summary metrics of facial logins, success rates, and gesture statistics.
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "total_attempts": 150,
      "total_success": 142,
      "success_rate": 94.7,
      "total_face_users": 12
    }
  }
  ```

---

### 3. User Directory
- **Endpoint**: `GET /api/v1/users`
- **Parameters**: `search` (optional string), `limit` (int, max 100)
- **Description**: List registered users.
- **Response**:
  ```json
  {
    "success": true,
    "count": 1,
    "users": [
      {
        "user_id": 1,
        "name": "Jane Doe",
        "email": "jane@example.com",
        "created_at": "2026-07-27 12:00:00",
        "is_active": 1,
        "role": "user"
      }
    ]
  }
  ```

---

### 4. OpenAPI Specification
- **Endpoint**: `GET /api/v1/docs`
- **Description**: Returns full OpenAPI 3.0 JSON specification for Swagger UI integration.
