# D-CAPTCHA Backend API

Simple FastAPI backend for AI-based Online Exam Proctoring System.

## 📁 Project Structure

```
backend/
├── main.py          # FastAPI app with endpoints
├── database.py      # SQLite database operations
├── monitoring.py    # ML monitoring control
└── requirements.txt # Backend dependencies
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install fastapi uvicorn
```

### 2. Run the Server

From the project root directory:

```bash
uvicorn backend.main:app --reload
```

The server will start at: `http://localhost:8000`

### 3. Access Swagger UI

Open your browser and navigate to:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📡 API Endpoints

### 1️⃣ Start Exam
**POST** `/exam/start`

Starts ML monitoring in a background thread.

**Response:**
```json
{
  "status": "Exam started"
}
```

### 2️⃣ Stop Exam
**POST** `/exam/stop`

Stops ML monitoring and releases camera.

**Response:**
```json
{
  "status": "Exam stopped"
}
```

### 3️⃣ Get Alerts
**GET** `/alerts`

Returns all logged violations.

**Response:**
```json
[
  {
    "violation": "Mobile Phone Detected",
    "timestamp": "2026-01-18 14:22:01"
  },
  {
    "violation": "Multiple Persons Detected",
    "timestamp": "2026-01-18 14:20:15"
  }
]
```

### 4️⃣ Get Monitoring Status
**GET** `/exam/status`

Returns current monitoring state and alert count.

**Response:**
```json
{
  "is_active": true,
  "alert_count": 5
}
```

### 5️⃣ Clear All Alerts
**DELETE** `/alerts`

Clears all alerts from database.

**Response:**
```json
{
  "status": "All alerts cleared"
}
```

## 💾 Database

- **Type**: SQLite (built-in)
- **File**: `alerts.db` (created automatically)
- **Table**: `alerts`
  - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
  - `violation`: TEXT
  - `timestamp`: DATETIME

## 🎯 How It Works

1. **Start Exam**: Backend launches ML monitoring in a background thread
2. **Monitoring**: YOLO model detects violations (multiple persons, phone)
3. **Logging**: Violations are logged to SQLite database
4. **Alerts**: Frontend can fetch alerts via API
5. **Stop Exam**: Backend stops monitoring and releases camera

## 🔧 Testing with cURL

### Start Exam
```bash
curl -X POST http://localhost:8000/exam/start
```

### Stop Exam
```bash
curl -X POST http://localhost:8000/exam/stop
```

### Get Alerts
```bash
curl http://localhost:8000/alerts
```

### Get Status
```bash
curl http://localhost:8000/exam/status
```

### Clear Alerts
```bash
curl -X DELETE http://localhost:8000/alerts
```

## 🛠️ Technical Details

- **Framework**: FastAPI
- **Database**: SQLite with thread-safe access
- **Monitoring**: Background thread with YOLO detection
- **CORS**: Enabled for frontend integration
- **Port**: 8000 (default)

## 📝 Notes

- Each violation is logged only once per occurrence
- Camera is automatically released when exam stops
- Database is created automatically on first run
- Thread-safe database operations
- Background monitoring doesn't block API requests

## 🎓 College-Level Implementation

This is a simple, functional backend suitable for college projects:
- ✅ No complex authentication
- ✅ No Docker/cloud services
- ✅ No Redis/Celery
- ✅ SQLite built-in database
- ✅ Simple threading for background tasks
- ✅ Clear, readable code with comments

## 🔗 Frontend Integration

Frontend can connect to this backend using:
- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **CORS**: Already configured

Example JavaScript fetch:
```javascript
// Start exam
fetch('http://localhost:8000/exam/start', { method: 'POST' })
  .then(res => res.json())
  .then(data => console.log(data));

// Get alerts
fetch('http://localhost:8000/alerts')
  .then(res => res.json())
  .then(alerts => console.log(alerts));
```

## 🐛 Troubleshooting

**Camera not opening?**
- Ensure no other app is using the camera
- Check camera permissions

**Import errors?**
- Make sure you're running from project root
- Check that all ML dependencies are installed

**Database errors?**
- The `alerts.db` file should be created automatically
- Check file permissions in the project directory
