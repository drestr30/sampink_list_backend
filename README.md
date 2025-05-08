# Sampink Lists Backend API

This project provides a set of HTTP endpoints for managing background checks and user-related operations. The API is built using Azure Functions.

## Endpoints

### 1. `POST /backgroundCheck`
Launches a background check for a user.

#### Request Body
```json
{
  "checks": [
    {
      "typedoc": "CC",
      "doc": "123456789",
      "fechaE": "01/01/2020",
    }
  ]
}
```

#### Response
- **200 OK**
  ```json
  {
    "status": "success",
    "request_ids": [
      {
        "id": 1,
        "doc": "123456789",
        "status": "procesando",
        "response": "..."
      }
    ]
  }
  ```
- **400 Bad Request**
  ```json
  {
    "status": "failed",
    "message": "No requests processed due to insufficient credits"
  }
  ```
- **500 Internal Server Error**
  ```json
  {
    "error": "Internal server error ..."
  }
  ```

---

### 2. `GET /getUserChecks/{user_id}`
Retrieves all background checks for a specific user.

#### Path Parameters
- `user_id` (integer): The ID of the user.

#### Response
- **200 OK**
  ```json
  {
    "status": "success",
    "checks": [
      {
        "id": 1,
        "doc": "123456789",
        "status": "procesando",
        "timestamp": "2023-10-01 12:00:00"
      }
    ]
  }
  ```
- **404 Not Found**
  ```json
  {
    "status": "failed",
    "message": "No pending checks found"
  }
  ```
- **500 Internal Server Error**
  ```json
  {
    "error": "Internal server error ..."
  }
  ```

---

### 3. `GET /backgroundCheckSyncStatus/{user_id}`
Synchronizes the status of pending background checks for a user.

#### Path Parameters
- `user_id` (integer): The ID of the user.

#### Response
- **200 OK**
  ```json
  {
    "status": "success",
    "processing": true
  }
  ```
- **500 Internal Server Error**
  ```json
  {
    "error": "Internal server error ..."
  }
  ```

---

### 4. `GET /backgroundCheckResults/{check_id}`
Retrieves the results of a specific background check.

#### Path Parameters
- `check_id` (integer): The ID of the background check.

#### Response
- **200 OK**
  ```json
  {
    "dict_hallazgos": {
      "altos": [...],
      "medios": [...],
      "bajos": [...]
    },
    ...
  }
  ```
- **400 Bad Request**
  ```json
  {
    "error": "check_id is required"
  }
  ```
- **500 Internal Server Error**
  ```json
  {
    "error": "Internal server error ..."
  }
  ```

---

### 5. `POST /registerUser`
Registers a new user.

#### Request Body
```json
{
  "username": "user@example.com"
}
```

#### Response
- **200 OK**
  ```json
  {
    "status": "success",
    "user_id": 1
  }
  ```
- **400 Bad Request**
  ```json
  {
    "status": "User already exists."
  }
  ```
- **500 Internal Server Error**
  ```json
  {
    "error": "Internal server error ..."
  }
  ```

---

### 6. `POST /getUserId`
Retrieves the user ID for a given username.

#### Request Body
```json
{
  "username": "user@example.com"
}
```

#### Response
- **200 OK**
  ```json
  {
    "status": "success",
    "user_id": 1
  }
  ```
- **404 Not Found**
  ```json
  {
    "status": "failed",
    "message": "User not found"
  }
  ```
- **500 Internal Server Error**
  ```json
  {
    "error": "Internal server error ..."
  }
  ```

---

## Requirements
Install the dependencies listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## Running Locally
1. Set up the environment variables in a `.env` file.
2. Start the Azure Functions runtime:
   ```bash
   func start
   ```

---

## License
This project is licensed under the MIT License.