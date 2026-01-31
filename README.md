# Face Authentication Attendance System

A Flask-based attendance management system with face recognition, admin authorization, and comprehensive anti-spoofing measures.

## 🌟 Features

### Core Functionality
- **Face Registration**: Register employee faces with multiple image capture
- **Face Recognition**: Identify employees using face recognition
- **Attendance Tracking**: Punch-in and punch-out with timestamps
- **Admin Authorization**: Admin face verification required before registering new users

### Security Features
- **Anti-Spoofing Detection**: 
  - Texture analysis (Laplacian/Sobel variance)
  - Motion detection across frames
  - Frequency analysis (FFT)
  - Blink detection support
- **Lighting Normalization**: CLAHE and gamma correction for varying conditions
- **Session Management**: Time-limited admin sessions with auto-expiry

### Admin Features
- Separate admin database connection
- Admin activity logging
- User management dashboard
- Attendance reports generation

## 📁 Project Structure

```
Face Detection/
├── app.py                    # Flask application entry point
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration classes
├── models/
│   ├── __init__.py
│   ├── database.py           # Database connections
│   ├── user.py               # User model
│   ├── admin.py              # Admin model
│   └── attendance.py         # Attendance model
├── services/
│   ├── __init__.py
│   ├── face_recognition.py   # Face detection & encoding
│   ├── anti_spoofing.py      # Spoof prevention
│   ├── image_processor.py    # Image preprocessing
│   └── admin_auth.py         # Admin authentication
├── routes/
│   ├── __init__.py
│   ├── main.py               # Main pages
│   ├── admin.py              # Admin endpoints
│   ├── users.py              # User endpoints
│   └── attendance.py         # Attendance endpoints
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Utility functions
├── templates/
│   ├── index.html
│   ├── admin_setup.html
│   ├── admin.html
│   ├── register.html
│   ├── attendance.html
│   └── dashboard.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── camera.js
│       ├── admin.js
│       ├── admin_setup.js
│       ├── register.js
│       ├── attendance.js
│       └── dashboard.js
├── data/                     # Auto-created directories
│   ├── face_encodings/       # User face encodings
│   └── admin_encodings/      # Admin face encodings
└── README.md
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- CMake (for dlib)
- Visual Studio Build Tools (Windows) or GCC (Linux/Mac)

### Step 1: Clone/Setup Project

```bash
cd "Face Detection"
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

### Step 3: Install Dependencies

**Windows (using pre-built dlib wheel):**
```bash
# Install dlib from pre-built wheel (recommended for Windows)
pip install dlib-19.22.99-cp310-cp310-win_amd64.whl

# Install all other requirements
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
# Install cmake first
pip install cmake

# Install dlib (may take several minutes)
pip install dlib

# Install all requirements
pip install -r requirements.txt
```

### Step 4: Setup Supabase

1. Create two Supabase projects:
   - **Main Database**: For users and attendance
   - **Admin Database**: For admins and activity logs

2. Run the following SQL in each database:

**Main Database:**
```sql
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    employee_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    department TEXT,
    registered_by TEXT,
    is_registered BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE attendance (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    employee_id TEXT NOT NULL,
    punch_in TIMESTAMP NOT NULL,
    punch_out TIMESTAMP,
    date DATE NOT NULL,
    hours_worked FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Admin Database:**
```sql
CREATE TABLE admins (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    is_active BOOLEAN DEFAULT true,
    is_registered BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE TABLE admin_activity_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_employee_id TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Main Database (Users & Attendance)
SUPABASE_URL=https://your-main-project.supabase.co
SUPABASE_KEY=your-main-anon-key

# Admin Database (Admins & Activity Log)
ADMIN_SUPABASE_URL=https://your-admin-project.supabase.co
ADMIN_SUPABASE_KEY=your-admin-anon-key

# Flask
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=true
```

### Step 6: Run the Application

```bash
python app.py
```

Access the application at: `http://localhost:5000`

## 📱 Usage Guide

### First Time Setup
1. Navigate to `/admin/setup`
2. Fill in admin details (ID, Name, Email)
3. Capture your face for registration
4. You are now the first admin

### Registering New Users
1. Go to `/register`
2. **Step 1**: Admin scans their face for authorization
3. **Step 2**: Fill in user details (Employee ID, Name, Email, Department)
4. **Step 3**: Capture user's face (5 images captured automatically)

### Marking Attendance
1. Go to `/attendance`
2. Select mode: Punch In or Punch Out
3. Start camera and scan your face
4. System identifies you and records attendance

### Admin Panel
1. Go to `/admin`
2. Authenticate with your admin face
3. View/manage users, admins, and activity logs

### Dashboard
1. Go to `/dashboard`
2. View attendance statistics
3. Generate reports for specific date ranges

## 🔧 Technical Details

### Face Recognition Model
- **Library**: `face_recognition` (based on dlib)
- **Detection Method**: HOG (Histogram of Oriented Gradients)
- **Encoding**: 128-dimensional face encoding
- **Recognition Tolerance**: 
  - Users: 0.6 (standard)
  - Admins: 0.5 (stricter for security)

### Anti-Spoofing Techniques

| Technique | Description | Threshold |
|-----------|-------------|-----------|
| Texture Analysis | Laplacian variance to detect flat images | > 100 |
| Edge Detection | Sobel operator for edge density | > 50 |
| Motion Detection | Frame-to-frame pixel differences | > 0.5 |
| Frequency Analysis | FFT to detect screen patterns | Varies |

### Accuracy & Limitations

**Expected Accuracy:**
- Face Detection: ~95% in good lighting
- Face Recognition: ~90% with proper enrollment
- Anti-Spoofing: ~70-80% (basic implementation)

**Limitations:**
- Performance degrades in poor lighting (< 100 lux)
- Glasses/masks may reduce accuracy
- Twins/similar faces may cause false matches
- Not recommended for high-security applications without additional measures

**Recommendations for Better Accuracy:**
1. Ensure good, even lighting during registration
2. Capture faces from multiple angles
3. Update face encodings periodically
4. Combine with other authentication factors for high security

## 🔌 API Endpoints

### Admin Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/check-first` | Check if first admin exists |
| POST | `/api/admin/register-first` | Register first admin |
| POST | `/api/admin/authenticate` | Authenticate admin face |
| POST | `/api/admin/verify-session` | Verify session token |
| GET | `/api/admin/list` | List all admins |
| GET | `/api/admin/activity-log` | Get activity logs |

### User Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register` | Register new user (requires admin token) |
| GET | `/api/users/list` | List all users |
| DELETE | `/api/users/{id}` | Delete user |

### Attendance Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/attendance/mark` | Record punch-in/out (auto-detect) |
| GET | `/api/attendance/today` | Get today's attendance |
| GET | `/api/attendance/statistics` | Get statistics |
| POST | `/api/attendance/report` | Generate report |

## 🚀 Deployment

### Deploy to Railway (Recommended)

1. **Create Railway Account**: Go to [railway.app](https://railway.app)

2. **Connect GitHub**: Link your GitHub repository

3. **Add Environment Variables**: In Railway dashboard, add:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SECRET_KEY=your-super-secret-key
   FLASK_DEBUG=False
   FLASK_ENV=production
   FACE_DETECTION_MODEL=hog
   SPOOF_DETECTION_ENABLED=True
   ```

4. **Deploy**: Railway will auto-detect the Procfile and deploy

### Deploy to Render

1. **Create render.yaml**:
   ```yaml
   services:
     - type: web
       name: face-attendance
       env: python
       buildCommand: pip install -r requirements-deploy.txt
       startCommand: gunicorn app:app
   ```

2. Connect your GitHub repo and deploy

### Deploy to Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set SUPABASE_URL=https://your-project.supabase.co
heroku config:set SUPABASE_KEY=your-key
heroku config:set SECRET_KEY=your-secret-key
heroku config:set FACE_DETECTION_MODEL=hog

# Deploy
git push heroku main
```

### Important Deployment Notes

⚠️ **Use `requirements-deploy.txt`** for cloud deployment (Linux servers)
- Uses `opencv-python-headless` instead of `opencv-python`
- Builds `dlib` from source (takes ~10 min on first deploy)

⚠️ **Set `FACE_DETECTION_MODEL=hog`** for cloud deployment
- YOLO requires more memory
- HOG works well on limited resources

## 🐛 Troubleshooting

### Common Issues

**1. dlib installation fails**
```bash
# Windows: Install Visual Studio Build Tools
# Mac: brew install cmake
# Linux: sudo apt-get install cmake libboost-all-dev
```

**2. Camera not accessible**
- Check browser permissions
- Ensure no other app is using the camera
- Try using Chrome or Firefox

**3. Face not detected**
- Improve lighting conditions
- Ensure face is fully visible
- Remove obstructions (heavy glasses, masks)

**4. Database connection issues**
- Verify Supabase URLs and keys in `.env`
- Check if tables are created properly
- Ensure network connectivity

## 📝 License

MIT License - Feel free to modify and use for your projects.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

**Note**: This is a demonstration project. For production use, consider:
- Additional security measures (HTTPS, rate limiting)
- More sophisticated anti-spoofing (3D depth, liveness)
- Scalable face encoding storage
- Comprehensive logging and monitoring
