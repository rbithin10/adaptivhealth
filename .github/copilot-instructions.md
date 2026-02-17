# AI Agent Instructions for AdaptivHealth

## Project Overview
AdaptivHealth is a clinical-grade cardiovascular monitoring platform with three components:
- **Backend**: FastAPI (Python) - REST API with ML risk prediction
- **Mobile App**: Flutter (Dart) - Patient monitoring and workouts
- **Web Dashboard**: React (TypeScript) - Clinician patient management

**Key Context**: Healthcare application handling Protected Health Information (PHI). HIPAA compliance required.

---

## 1. CODE STYLE & CONVENTIONS

### Python Backend (FastAPI)

#### File Organization
- **Comprehensive file maps**: Every file has a navigation comment block at the top (lines 5-30)
- **Docstrings**: All functions/classes use triple-quoted docstrings with Args/Returns/Raises sections
- **Comment style**: Business context comments use `# WHY:` and `# DESIGN:` prefixes

**Example from `app/services/auth_service.py`:**
```python
"""
Authentication helpers.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 20
# PASSWORD HASHING CONFIG.............. Line 35
# 
# CLASS: AuthService
#   - hash_password().................. Line 68  (PBKDF2 hash)
```

#### Naming Conventions
- **Variables/functions**: `snake_case` (e.g., `get_current_user`, `check_vitals_for_alerts`)
- **Classes**: `PascalCase` (e.g., `AuthService`, `VitalSignRecord`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MODEL_PATH`, `BASE_DIR`)
- **Private methods**: Prefix with `_` (e.g., `_load_ml_model_inner`, `_handleDioError`)

#### Import Organization
Standard order (see `app/api/auth.py:35-55`):
```python
# 1. External libraries
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

# 2. Internal modules - database/config
from app.database import get_db
from app.config import settings

# 3. Internal modules - models/schemas/services
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
```

#### Type Hints
- **Always use type hints** for function parameters and returns
- **Use Optional[]** for nullable values: `Optional[str] = None`
- **Use List[], Dict[]** from typing module

**Example from `app/services/ml_prediction.py:88`:**
```python
def engineer_features(
    age: int,
    baseline_hr: int,
    max_safe_hr: int,
    avg_heart_rate: int,
    peak_heart_rate: int,
    min_heart_rate: int,
    avg_spo2: int,
    duration_minutes: int,
    recovery_time_minutes: int,
    activity_type: str = "walking"
) -> Dict[str, float]:
```

#### Logging Standards
```python
import logging
logger = logging.getLogger(__name__)

# Log levels:
logger.debug()    # Development details
logger.info()     # Normal operations (startup, config loaded)
logger.warning()  # Recoverable issues (model load failed, locked account)
logger.error()    # Serious problems (DB connection failed)
```

### Flutter Mobile App (Dart)

#### Naming Conventions
- **Files**: `snake_case.dart` (e.g., `api_client.dart`, `home_screen.dart`)
- **Classes**: `PascalCase` (e.g., `ApiClient`, `HomeScreen`, `AdaptivColors`)
- **Variables/methods**: `camelCase` (e.g., `apiClient`, `handleLoginSuccess`)
- **Private variables**: Prefix with `_` (e.g., `_authToken`, `_dio`)
- **Constants**: `camelCase` (e.g., `baseUrl`, unlike Python)

#### Comment Style (from `mobile-app/lib/services/api_client.dart:1-10`):
```dart
/*
This class talks to the backend server.

It also keeps the login token and sends it with each request.
All screens reuse this one client so everything stays consistent.
*/
```

#### Widget Organization
```dart
class MyScreen extends StatefulWidget {
  // 1. Constructor parameters
  final String title;
  
  const MyScreen({super.key, required this.title});
  
  // 2. State creation
  @override
  State<MyScreen> createState() => _MyScreenState();
}

class _MyScreenState extends State<MyScreen> {
  // 3. State variables
  bool _isLoading = false;
  
  // 4. Lifecycle methods (initState, dispose)
  @override
  void initState() {
    super.initState();
  }
  
  // 5. Event handlers
  void _handleSubmit() { }
  
  // 6. Build method
  @override
  Widget build(BuildContext context) {
    return Scaffold(...);
  }
}
```

### React Web Dashboard (TypeScript)

#### Naming Conventions
- **Files**: `PascalCase.tsx` for components (e.g., `LoginPage.tsx`, `StatusBadge.tsx`)
- **Files**: `camelCase.ts` for services/utils (e.g., `api.ts`, `colors.ts`)
- **Components**: `PascalCase` function components
- **Props interfaces**: `[ComponentName]Props` (e.g., `ProtectedRouteProps`)

#### Import Order (from `web-dashboard/src/App.tsx:1-16`):
```typescript
// 1. React/third-party
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// 2. Pages/components
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';

// 3. Styles
import './App.css';
```

#### Component Structure
```typescript
interface MyComponentProps {
  title: string;
  onSubmit: () => void;
}

const MyComponent: React.FC<MyComponentProps> = ({ title, onSubmit }) => {
  // 1. State hooks
  const [loading, setLoading] = React.useState(false);
  
  // 2. Effect hooks
  React.useEffect(() => {
    // Setup
  }, []);
  
  // 3. Event handlers
  const handleClick = () => { };
  
  // 4. Render
  return <div>{title}</div>;
};

export default MyComponent;
```

---

## 2. ARCHITECTURE PATTERNS

### Backend Structure (FastAPI)

#### Layered Architecture
```
app/
├── main.py              # FastAPI app initialization, middleware, lifespan
├── config.py            # Pydantic settings from environment variables
├── database.py          # SQLAlchemy engine, session factory, get_db()
├── api/                 # Route handlers (thin controllers)
│   ├── auth.py          # POST /login, /register, /refresh
│   ├── user.py          # GET /me, PUT /me
│   ├── vital_signs.py   # POST /vitals, GET /vitals/history
│   └── predict.py       # POST /predictions/risk
├── models/              # SQLAlchemy ORM models (database tables)
│   ├── user.py          # User(Base) - users table
│   ├── vital_signs.py   # VitalSignRecord(Base)
│   └── alert.py         # Alert(Base)
├── schemas/             # Pydantic models (API validation)
│   ├── user.py          # UserCreate, UserResponse
│   └── vital_signs.py   # VitalSignCreate, VitalSignResponse
└── services/            # Business logic (reusable across endpoints)
    ├── auth_service.py  # Password hashing, JWT creation
    ├── ml_prediction.py # Risk prediction logic
    └── encryption.py    # PHI encryption/decryption
```

#### Router Registration (from `app/main.py:100-120`):
```python
from app.api import auth, user, vital_signs, predict

# Routers included with prefix
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(user.router, prefix="/api/v1", tags=["users"])
app.include_router(vital_signs.router, prefix="/api/v1", tags=["vitals"])
```

#### Dependency Injection Pattern
Always use FastAPI's `Depends()` for:
- Database sessions
- Authentication
- Service instances

**Example from `app/api/vital_signs.py:239`:**
```python
@router.post("/vitals", response_model=VitalSignResponse)
def submit_vital_signs(
    vital_data: VitalSignCreate,              # Request body validation
    db: Session = Depends(get_db),            # DB session
    current_user: User = Depends(get_current_user),  # Auth
    background_tasks: BackgroundTasks = BackgroundTasks()  # Async tasks
):
```

#### Error Handling Pattern
```python
from fastapi import HTTPException, status

# Always use specific HTTP status codes
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password"
)

# Common status codes:
# 200 - OK
# 201 - Created
# 400 - Bad Request (client error)
# 401 - Unauthorized (auth failed)
# 403 - Forbidden (insufficient permissions)
# 404 - Not Found
# 422 - Validation Error (Pydantic)
# 423 - Locked (account locked)
# 500 - Internal Server Error
# 503 - Service Unavailable (ML model not loaded)
```

### Mobile App Structure (Flutter)

#### Directory Layout
```
lib/
├── main.dart               # App entry point, MaterialApp, routing
├── screens/                # Full-page views
│   ├── login_screen.dart
│   ├── home_screen.dart
│   └── workout_screen.dart
├── services/               # API clients, business logic
│   └── api_client.dart     # HTTP client with auth
├── theme/                  # Design system
│   ├── colors.dart         # AdaptivColors class
│   ├── typography.dart     # Text styles
│   └── theme.dart          # ThemeData builder
└── widgets/                # Reusable UI components
    └── heart_rate_ring.dart
```

#### API Client Pattern (from `mobile-app/lib/services/api_client.dart:10-50`):
```dart
class ApiClient {
  static const String baseUrl = 'http://localhost:8080/api/v1';
  final Dio _dio;
  static String? _authToken;  // Singleton token storage
  
  ApiClient() : _dio = _createDio() {
    _setupInterceptors();  // Auto-attach token to requests
  }
  
  void _setupInterceptors() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (_authToken != null) {
          options.headers['Authorization'] = 'Bearer $_authToken';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Auto-refresh token logic
        }
        return handler.next(error);
      },
    ));
  }
}
```

### Web Dashboard Structure (React)

#### Directory Layout
```
src/
├── App.tsx                 # Router setup, ProtectedRoute wrapper
├── index.tsx               # ReactDOM.render entry point
├── pages/                  # Route components
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── PatientsPage.tsx
│   └── PatientDetailPage.tsx
├── components/             # Reusable UI components
│   ├── common/
│   │   └── StatusBadge.tsx
│   └── cards/
│       └── StatCard.tsx
├── services/               # API client
│   └── api.ts
├── theme/                  # Design tokens
│   ├── colors.ts
│   └── typography.ts
└── types.ts               # TypeScript interfaces

```

#### API Service Pattern (from `web-dashboard/src/services/api.ts:10-95`):
```typescript
class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {'Content-Type': 'application/json'}
    });

    // Add token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle 401 errors (auto-logout)
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }
}
```

#### Protected Route Pattern (from `web-dashboard/src/App.tsx:24-32`):
```typescript
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};
```

---

## 3. BUILD AND TEST COMMANDS

### Backend (Python/FastAPI)

#### Install Dependencies
```bash
# Full dependencies
pip install -r requirements.txt

# Minimal dependencies (for quick testing)
pip install -r requirements-minimal.txt
```

**Key Dependencies** (from `requirements.txt`):
- `fastapi>=0.115` - Web framework
- `uvicorn[standard]>=0.30` - ASGI server
- `sqlalchemy>=2.0.30` - ORM
- `pydantic>=2.7` - Validation
- `python-jose[cryptography]>=3.3.0` - JWT
- `passlib[bcrypt]>=1.7.4` - Password hashing
- `scikit-learn==1.8.0` - ML model runtime (exact version required!)

#### Run Backend Server

**Method 1: Quick Start (Windows)**
```bash
start.bat
# This script:
# 1. Activates virtual environment
# 2. Installs dependencies if needed
# 3. Starts uvicorn on port 8080
```

**Method 2: Direct Python**
```bash
# From project root
python start_server.py
# Runs on http://0.0.0.0:8080

# Or with uvicorn directly
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Important**: Backend runs on **port 8080**, not 8000

#### Run Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_registration.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v
```

**Test Pattern** (from `tests/test_registration.py:15-25`):
```python
# Set environment before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars...")
os.environ.setdefault("DEBUG", "true")

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_register.db"
```

#### Run Migrations
```bash
# Run migration script
python run_migration.py

# The script uses raw SQL ALTER TABLE commands for SQLite
# For PostgreSQL, use Alembic:
alembic upgrade head
```

#### Database Setup

**SQLite (Development)** - Automatic, no setup needed:
```python
# .env file
DATABASE_URL=sqlite:///./adaptiv_health.db

# Database file created automatically on first run
```

**PostgreSQL (Production)**:
```bash
# .env file
DATABASE_URL=postgresql://user:password@host:5432/adaptiv_health

# Create database
createdb adaptiv_health

# Run migrations
alembic upgrade head
```

### Mobile App (Flutter)

#### Install Dependencies
```bash
cd mobile-app
flutter pub get
```

**Key Dependencies** (from `mobile-app/pubspec.yaml:14-35`):
- `google_fonts: ^6.1.0` - DM Sans typography
- `lucide_icons: ^0.257.0` - Icon system
- `go_router: ^14.0.0` - Navigation (not yet implemented)
- `provider: ^6.1.0` - State management (not yet implemented)
- `dio: ^5.4.0` - HTTP client
- `flutter_secure_storage: ^9.0.0` - Secure token storage
- `fl_chart: ^0.68.0` - Charts (not yet implemented)

#### Run App
```bash
# Run on connected device/emulator
flutter run

# Run specific platform
flutter run -d chrome          # Web
flutter run -d windows         # Windows desktop
flutter run -d <device-id>     # Physical device
```

#### Build for Release
```bash
# Android
flutter build apk --release
flutter build appbundle --release  # For Google Play

# iOS (requires Mac)
flutter build ios --release

# Web
flutter build web
```

#### Run Tests
```bash
flutter test
flutter test test/widget_test.dart  # Specific test
```

### Web Dashboard (React)

#### Install Dependencies
```bash
cd web-dashboard
npm install
# or
yarn install
```

**Key Dependencies** (from `web-dashboard/package.json:5-30`):
- `react: ^18.2.0`
- `react-router-dom: ^6.21.3` - Routing
- `axios: ^1.6.5` - HTTP client
- `@mui/material: ^5.15.6` - UI components
- `recharts: ^2.12.0` - Charts
- `typescript: ^4.9.5`

#### Run Development Server
```bash
npm start
# Runs on http://localhost:3000
```

#### Build for Production
```bash
npm run build
# Creates optimized build in build/ folder
# Deploy this folder to web hosting
```

#### Run Tests
```bash
npm test
npm test -- --coverage  # With coverage report
```

---

## 4. PROJECT CONVENTIONS

### API Endpoint Structure

#### Pattern: `/api/v1/{resource}/{action}`

All endpoints prefixed with `/api/v1` (from `app/main.py:115-125`):
```python
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(user.router, prefix="/api/v1", tags=["users"])
app.include_router(vital_signs.router, prefix="/api/v1", tags=["vitals"])
app.include_router(predict.router, prefix="/api/v1", tags=["predictions"])
```

#### Authentication Endpoints (from `app/api/auth.py:245-405`)
```python
# User Registration
POST /api/v1/register
Body: {"email": str, "password": str, "name": str, "age": int}
Response: UserResponse

# Login
POST /api/v1/login
Body: {"username": str, "password": str}  # OAuth2 format
Response: {"access_token": str, "refresh_token": str, "token_type": "bearer"}

# Token Refresh
POST /api/v1/refresh
Body: {"refresh_token": str}
Response: {"access_token": str, "refresh_token": str}

# Get Current User
GET /api/v1/me
Headers: Authorization: Bearer <token>
Response: UserProfileResponse
```

#### Vital Signs Endpoints (from `app/api/vital_signs.py`)
```python
# Submit vitals (patient only)
POST /api/v1/vitals
Body: VitalSignCreate (heart_rate, spo2, systolic_bp, diastolic_bp, timestamp)
Response: VitalSignResponse

# Get latest reading (patient only)
GET /api/v1/vitals/latest
Response: VitalSignResponse

# Get history (patient only)
GET /api/v1/vitals/history?days=7&limit=100
Response: VitalSignsHistoryResponse

# Get patient's vitals (clinician only)
GET /api/v1/vitals/user/{user_id}/latest
GET /api/v1/vitals/user/{user_id}/history?days=7
```

### Database Model Pattern (SQLAlchemy)

**Template** (from `app/models/vital_signs.py:35-100`):
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base

class MyModel(Base):
    """Docstring with table purpose."""
    
    __tablename__ = "table_name"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    
    # Data columns
    name = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="items")
    
    # Indexes
    __table_args__ = (
        Index('idx_my_composite', 'user_id', 'timestamp'),
        {'extend_existing': True}
    )
```

**Key Rules**:
1. Inherit from `Base`
2. Use timezone-aware DateTime: `DateTime(timezone=True)`
3. Add composite indexes for common queries
4. Foreign keys use `ondelete="CASCADE"` for data integrity
5. Add `extend_existing=True` to `__table_args__` for development flexibility

### Schema Validation Pattern (Pydantic)

**Template** (from `app/schemas/user.py:35-85`):
```python
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

class MyBase(BaseModel):
    """Base schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=120)
    
    @field_validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty')
        return v

class MyCreate(MyBase):
    """Schema for creation (includes password, etc.)."""
    password: str = Field(..., min_length=8)

class MyResponse(MyBase):
    """Schema for API response (excludes password)."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
```

**Key Rules**:
1. Separate schemas for Create, Update, Response
2. Use `Field()` for validation (min_length, ge, le)
3. Use `Optional[]` for nullable fields
4. Response schemas have `Config.from_attributes = True`
5. Never expose passwords in response schemas

### Service Layer Pattern

Services contain business logic reusable across endpoints (from `app/services/auth_service.py:68-150`):

```python
class AuthService:
    """Handles authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using PBKDF2-SHA256 with 200k rounds."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return pwd_context.verify(plain, hashed)
        except Exception:
            return False
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=30))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
```

**Key Rules**:
1. Services are stateless (use `@staticmethod` when possible)
2. One service per domain (auth, encryption, ML prediction)
3. Services never access FastAPI Request/Response - only pure data
4. Services can call other services

### ML Integration Pattern

**Model Loading** (from `app/services/ml_prediction.py:42-82`):
```python
# Global model state (loaded once at startup)
model = None
scaler = None
feature_columns = None

def load_ml_model(timeout: int = 15) -> bool:
    """Load model with timeout to prevent hanging startup."""
    global model, scaler, feature_columns
    
    # Use absolute paths from BASE_DIR
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    MODEL_PATH = BASE_DIR / "ml_models" / "risk_model.pkl"
    
    # Load with joblib
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    
    return True
```

**Feature Engineering** (from `app/services/ml_prediction.py:88-140`):
```python
def engineer_features(
    age: int,
    baseline_hr: int,
    # ... other vitals
) -> Dict[str, float]:
    """Calculate derived features from raw vitals."""
    hr_pct_of_max = peak_heart_rate / max_safe_hr
    hr_elevation = avg_heart_rate - baseline_hr
    # ... 17 total features
    
    return {
        'age': age,
        'hr_pct_of_max': hr_pct_of_max,
        'hr_elevation': hr_elevation,
        # ... all features
    }
```

**Prediction** (from `app/services/ml_prediction.py:145-200`):
```python
def predict_risk(...) -> Dict[str, Any]:
    """Predict risk score 0.0-1.0."""
    if not is_model_loaded():
        raise RuntimeError("ML model not loaded")
    
    # Engineer features
    features = engineer_features(...)
    
    # Convert to DataFrame with correct column order
    feature_df = pd.DataFrame([features])[feature_columns]
    
    # Scale and predict
    scaled = scaler.transform(feature_df)
    risk_score = float(model.predict_proba(scaled)[0][1])
    
    return {
        'risk_score': risk_score,
        'risk_level': _classify_risk(risk_score),
        'confidence': _calculate_confidence(...)
    }
```

### Authentication & Authorization Pattern

**JWT Authentication** (from `app/api/auth.py:120-175`):
```python
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extract user from JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
```

**Role-Based Access** (from `app/api/auth.py:175-195`):
```python
def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user has admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def get_current_doctor_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user has clinician role."""
    if current_user.role not in [UserRole.CLINICIAN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Clinician access required")
    return current_user
```

**Usage in Endpoints**:
```python
# Patient accessing own data
@router.get("/vitals/latest")
def get_vitals(current_user: User = Depends(get_current_user)):
    # current_user is automatically extracted from JWT

# Clinician accessing patient data
@router.get("/vitals/user/{user_id}/latest")
def get_patient_vitals(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user)
):
    # Only clinicians/admins can access this
```

### Healthcare Data Handling

**PHI Encryption** (from `app/services/encryption.py:30-90`):
```python
from app.services.encryption import encryption_service

# Encrypt before saving to database
encrypted_history = encryption_service.encrypt_text(user.medical_history)
user.medical_history_encrypted = encrypted_history

# Decrypt when reading
medical_history = encryption_service.decrypt_text(user.medical_history_encrypted)
```

**Alert Generation** (from `app/api/vital_signs.py:72-165`):
```python
def check_vitals_for_alerts(user_id: int, vital_data: VitalSignCreate):
    """Background task to create alerts for threshold violations."""
    
    # Check critical thresholds
    if vital_data.heart_rate > 180:
        Alert(
            user_id=user_id,
            alert_type=AlertType.HIGH_HEART_RATE.value,
            severity=SeverityLevel.CRITICAL.value,
            title="High Heart Rate Detected",
            message=f"Heart rate of {vital_data.heart_rate} BPM exceeds safe limit"
        )
    
    if vital_data.spo2 < 90:
        Alert(
            user_id=user_id,
            alert_type=AlertType.LOW_SPO2.value,
            severity=SeverityLevel.CRITICAL.value,
            title="Low Oxygen Level",
            message=f"SpO2 of {vital_data.spo2}% below safe level"
        )
```

---

## 5. INTEGRATION POINTS

### Database Configuration

**Database Type**: PostgreSQL (production) / SQLite (development)

**Configuration** (from `app/config.py:35-40` and `app/database.py:35-50`):
```python
# Settings
class Settings(BaseSettings):
    database_url: str = Field(
        default="sqlite:///./adaptiv_health.db",
        description="Database connection string"
    )

# Engine creation with conditional pooling
if "sqlite" in settings.database_url:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        connect_args={"options": "-c timezone=utc"}
    )
```

**Environment Variables** (from `.env`):
```bash
# SQLite (auto-created)
DATABASE_URL=sqlite:///./adaptiv_health.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@hostname:5432/adaptiv_health

# AWS RDS example
DATABASE_URL=postgresql://admin:pass@my-rds.region.rds.amazonaws.com:5432/adaptiv
```

### ML Model Integration

**Model Files** (from `app/services/ml_prediction.py:35-40`):
```
ml_models/
├── risk_model.pkl           # scikit-learn RandomForest (96.9% accuracy)
├── scaler.pkl               # StandardScaler for feature normalization
└── feature_columns.json     # List of 17 feature names in correct order
```

**Important**: Model requires **scikit-learn==1.8.0** (exact version!)

**Startup Integration** (from `app/main.py:40-68`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model on startup."""
    try:
        if load_ml_model():
            logger.info("ML model loaded successfully")
        else:
            logger.warning("ML model failed to load - predictions will return 503")
    except Exception as e:
        logger.warning(f"ML model loading skipped: {e}")
    
    yield
    
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
```

**Endpoint Integration** (from `app/api/predict.py:150-200`):
```python
@router.post("/predictions/risk")
def compute_risk_assessment(
    request: RiskPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compute ML risk prediction."""
    if not is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="ML model is not available"
        )
    
    prediction = predict_risk(
        age=current_user.age,
        baseline_hr=current_user.baseline_hr,
        # ... other features
    )
    
    return RiskAssessmentComputeResponse(**prediction)
```

### API Authentication Mechanism

**JWT Token Flow**:
```
1. User POSTs credentials to /api/v1/login
2. Backend validates, returns access_token + refresh_token
3. Client stores tokens (localStorage for web, secure storage for mobile)
4. Client adds Authorization: Bearer <access_token> to all requests
5. Backend validates token using get_current_user dependency
6. If token expires (401), client uses refresh_token to get new access_token
```

**Token Configuration** (from `.env`):
```bash
SECRET_KEY=<32+ character random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30      # Short-lived access token
REFRESH_TOKEN_EXPIRE_DAYS=7         # Long-lived refresh token
```

**Mobile Token Storage** (from `mobile-app/lib/services/api_client.dart:20-30`):
```dart
class ApiClient {
  static String? _authToken;       // In-memory (resets on app restart)
  static String? _refreshToken;
  
  // TODO: Use flutter_secure_storage for persistence
  // final storage = FlutterSecureStorage();
  // await storage.write(key: 'access_token', value: token);
}
```

**Web Token Storage** (from `web-dashboard/src/services/api.ts:55-65`):
```typescript
// Store tokens
localStorage.setItem('token', accessToken);
localStorage.setItem('refresh_token', refreshToken);

// Add to requests
this.client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Cross-Service Communication

**Backend ↔ Mobile App**:
- Protocol: HTTP REST
- Base URL: `http://localhost:8080/api/v1` (development)
- Auth: JWT Bearer token
- Format: JSON
- CORS: Enabled for `localhost:*` ports

**Backend ↔ Web Dashboard**:
- Protocol: HTTP REST
- Base URL: `http://localhost:8080/api/v1` (development)
- Auth: JWT Bearer token
- Format: JSON
- CORS: Enabled for `localhost:3000` (React dev server)

**CORS Configuration** (from `app/main.py:100-110`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 6. SECURITY PATTERNS

### Password Security

**Hashing Algorithm** (from `app/services/auth_service.py:35-50`):
- Algorithm: PBKDF2-SHA256
- Rounds: 200,000 (OWASP recommendation)
- Library: passlib

```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=200000
)
```

**Password Validation** (from `app/schemas/user.py:68-80`):
```python
@field_validator('password')
def validate_password_strength(cls, v):
    """Validate password meets security requirements."""
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters long')
    if not any(char.isdigit() for char in v):
        raise ValueError('Password must contain at least one digit')
    if not any(char.isalpha() for char in v):
        raise ValueError('Password must contain at least one letter')
    return v
```

### Account Security

**Failed Login Protection** (from `app/api/auth.py:100-140`):
```python
# Track failed attempts
auth_cred.failed_login_attempts += 1

# Lock account after 3 failed attempts
if auth_cred.failed_login_attempts >= 3:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

# Reset on successful login
auth_cred.failed_login_attempts = 0
auth_cred.locked_until = None
```

**Account Lockout Check**:
```python
def is_locked(self) -> bool:
    """Check if account is temporarily locked."""
    if self.locked_until is None:
        return False
    return datetime.now(timezone.utc) < self.locked_until
```

### Data Encryption

**PHI Encryption** (from `app/services/encryption.py:30-90`):
- Algorithm: AES-256-GCM (authenticated encryption)
- Key: 32-byte key from environment variable
- Nonce: Random 12-byte nonce per encryption
- Output: base64(nonce + ciphertext + tag)

```python
class EncryptionService:
    def __init__(self, key_b64: Optional[str] = None):
        key = base64.b64decode(key_b64)
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        self._aesgcm = AESGCM(key)
    
    def encrypt_text(self, plaintext: Optional[str]) -> Optional[str]:
        nonce = os.urandom(12)
        ct = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("utf-8")
```

**Environment Setup**:
```bash
# Generate key
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

# .env file
PHI_ENCRYPTION_KEY=DV6bGaOXYP29VZmLHeyaitlwzZpcMJ2x1OjwoTE0tLA=
```

### HIPAA Compliance Considerations

**Database Encryption**:
- At-rest: Use PostgreSQL with encryption enabled (AWS RDS encryption)
- In-transit: Use SSL/TLS for database connections
- Connection string example: `postgresql://...?sslmode=require`

**Audit Logging** (from `app/api/vital_signs.py:72-90`):
```python
logger.info(f"User {user_id} submitted vitals: HR={heart_rate}, SpO2={spo2}")
logger.warning(f"High heart rate alert for user {user_id}: {heart_rate} BPM")
```

**Access Control**:
- **Patients**: Can only access their own data
- **Clinicians**: Can access patient data with consent
- **Admins**: Full access (for system maintenance)

**Role Checks** (from `app/api/auth.py:175-225`):
```python
# Clinician-only endpoint
def get_current_doctor_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.CLINICIAN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Clinician access required")
    return current_user

# Consent check for PHI access
def check_clinician_phi_access(
    user_id: int,
    clinician: User,
    db: Session
):
    """Verify clinician has consent to access patient's PHI."""
    patient = db.query(User).filter(User.user_id == user_id).first()
    if patient.share_state != "SHARING_ON":
        raise HTTPException(status_code=403, detail="Patient has not granted access")
```

**Session Security** (from `app/config.py:75-85`):
```python
session_timeout_minutes: int = Field(default=30)
max_login_attempts: int = Field(default=3)
lockout_duration_minutes: int = Field(default=5)
```

---

## 7. DESIGN SYSTEM

### Color Palette (ISO 3864 Clinical Compliance)

**Backend Reference** (from `README.md:210-220`):
```
Primary Blue:   #2563EB (Actions, buttons, links)
Critical Red:   #EF4444 (High risk, danger alerts)
Warning Orange: #F59E0B (Moderate risk, caution)
Stable Green:   #22C55E (Low risk, safe, normal)
Neutral Gray:   #111827-#F9FAFB (Text, backgrounds)
```

**Flutter Colors** (from `mobile-app/lib/theme/colors.dart:20-70`):
```dart
class AdaptivColors {
  // Primary
  static const Color primary = Color(0xFF0066FF);
  static const Color primaryDark = Color(0xFF0052CC);
  
  // Clinical status
  static const Color critical = Color(0xFFFF3B30);
  static const Color warning = Color(0xFFFFB300);
  static const Color stable = Color(0xFF00C853);
  
  // Heart rate zones (for workout tracking)
  static const Color zoneResting = Color(0xFF4CAF50);     // 50-70 BPM
  static const Color zoneModerate = Color(0xFFFFC107);    // 100-140 BPM
  static const Color zoneMaximum = Color(0xFFF44336);     // 170+ BPM
  
  // Helper method
  static Color getRiskColor(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'high': return critical;
      case 'moderate': return warning;
      case 'low': return stable;
    }
  }
}
```

**React/TypeScript Colors** (from `web-dashboard/src/theme/colors.ts:5-50`):
```typescript
export const colors = {
  primary: {
    default: '#2563EB',
    dark: '#1E40AF',
    light: '#DBEAFE',
  },
  
  critical: {
    background: '#FEF2F2',
    border: '#FCA5A5',
    badge: '#EF4444',
    text: '#991B1B',
  },
  
  warning: {
    background: '#FFFBEB',
    badge: '#F59E0B',
    text: '#92400E',
  },
  
  stable: {
    background: '#F0FDF4',
    badge: '#22C55E',
    text: '#166534',
  },
};
```

### Typography (DM Sans Font Family)

**Backend Reference** (from `README.md:225-235`):
```
Screen Title:   24px, bold
Section Title:  18px, semibold
Card Title:     16px, semibold
Body:           14px, regular
Caption:        12px, regular
Hero Number:    56px, bold    (Heart rate display)
```

**Flutter Typography** (from `mobile-app/lib/theme/typography.dart` - inferred):
```dart
import 'package:google_fonts/google_fonts.dart';

TextStyle screenTitle = GoogleFonts.dmSans(
  fontSize: 24,
  fontWeight: FontWeight.w700,
);

TextStyle heroNumber = GoogleFonts.dmSans(
  fontSize: 56,
  fontWeight: FontWeight.w700,
  letterSpacing: -1.5,
);
```

**React Typography** (from `web-dashboard/src/theme/typography.ts` - inferred):
```typescript
export const typography = {
  screenTitle: {
    fontSize: '24px',
    fontWeight: 700,
    fontFamily: 'DM Sans, sans-serif',
  },
  
  body: {
    fontSize: '14px',
    fontWeight: 400,
    fontFamily: 'DM Sans, sans-serif',
  },
};
```

### Spacing System

**Base Unit: 8px** (from `README.md:240-245`)
```
4px, 8px, 12px, 16px, 20px, 24px, 32px, 40px, 48px, 64px
```

**Usage Examples**:
- Card padding: 16px or 24px
- Button padding: 12px horizontal, 8px vertical
- Section spacing: 32px or 48px
- Grid gap: 16px or 24px

---

## 8. COMMON TASKS

### Adding a New API Endpoint

1. **Define Schema** (`app/schemas/my_feature.py`):
```python
from pydantic import BaseModel

class MyFeatureCreate(BaseModel):
    name: str
    value: int

class MyFeatureResponse(BaseModel):
    id: int
    name: str
    value: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

2. **Define Model** (`app/models/my_feature.py`):
```python
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

class MyFeature(Base):
    __tablename__ = "my_features"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

3. **Create API Route** (`app/api/my_feature.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.my_feature import MyFeature
from app.schemas.my_feature import MyFeatureCreate, MyFeatureResponse

router = APIRouter()

@router.post("/my-feature", response_model=MyFeatureResponse)
def create_feature(
    feature: MyFeatureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new feature."""
    db_feature = MyFeature(
        name=feature.name,
        value=feature.value,
        user_id=current_user.user_id
    )
    db.add(db_feature)
    db.commit()
    db.refresh(db_feature)
    return db_feature

@router.get("/my-feature/{feature_id}", response_model=MyFeatureResponse)
def get_feature(
    feature_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a feature by ID."""
    feature = db.query(MyFeature).filter(MyFeature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature
```

4. **Register Router** (`app/main.py`):
```python
from app.api import my_feature

app.include_router(my_feature.router, prefix="/api/v1", tags=["features"])
```

5. **Run Migration** (create table):
```python
# For SQLite: run_migration.py
cursor.execute('''
    CREATE TABLE IF NOT EXISTS my_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        value INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    )
''')
```

### Adding a New Mobile Screen

1. **Create Screen File** (`mobile-app/lib/screens/my_screen.dart`):
```dart
import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../services/api_client.dart';

class MyScreen extends StatefulWidget {
  final ApiClient apiClient;
  
  const MyScreen({super.key, required this.apiClient});
  
  @override
  State<MyScreen> createState() => _MyScreenState();
}

class _MyScreenState extends State<MyScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  
  @override
  void initState() {
    super.initState();
    _loadData();
  }
  
  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      // Call API
      final data = await widget.apiClient.getMyFeatures();
      // Update state
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      setState(() => _isLoading = false);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Screen')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(child: Text(_errorMessage!))
              : _buildContent(),
    );
  }
  
  Widget _buildContent() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        // Your UI here
      ],
    );
  }
}
```

2. **Add API Method** (`mobile-app/lib/services/api_client.dart`):
```dart
Future<List<Map<String, dynamic>>> getMyFeatures() async {
  try {
    final response = await _dio.get('/my-feature');
    return List<Map<String, dynamic>>.from(response.data);
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}
```

3. **Add Navigation** (in `main.dart` or using go_router):
```dart
// In parent widget
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => MyScreen(apiClient: _apiClient),
  ),
);
```

### Adding a New React Page

1. **Create Page Component** (`web-dashboard/src/pages/MyPage.tsx`):
```typescript
import React from 'react';
import { useNavigate } from 'react-router-dom';
import apiService from '../services/api';

interface MyData {
  id: number;
  name: string;
  value: number;
}

const MyPage: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState<MyData[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const navigate = useNavigate();
  
  React.useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setLoading(true);
    try {
      const response = await apiService.getMyFeatures();
      setData(response);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  
  return (
    <div className="page-container">
      <h1>My Page</h1>
      <div className="data-grid">
        {data.map((item) => (
          <div key={item.id} className="card">
            <h3>{item.name}</h3>
            <p>{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MyPage;
```

2. **Add API Method** (`web-dashboard/src/services/api.ts`):
```typescript
async getMyFeatures(): Promise<MyData[]> {
  const response = await this.client.get('/my-feature');
  return response.data;
}
```

3. **Add Route** (`web-dashboard/src/App.tsx`):
```typescript
import MyPage from './pages/MyPage';

// In Routes component
<Route
  path="/my-page"
  element={
    <ProtectedRoute>
      <MyPage />
    </ProtectedRoute>
  }
/>
```

### Running the Full Stack

**Terminal 1 - Backend**:
```bash
# From project root
python start_server.py
# Runs on http://localhost:8080
```

**Terminal 2 - Web Dashboard**:
```bash
cd web-dashboard
npm start
# Runs on http://localhost:3000
```

**Terminal 3 - Mobile App**:
```bash
cd mobile-app
flutter run -d chrome  # For web
# or
flutter run  # For connected device
```

**Test Login**:
- Email: `test@example.com`
- Password: `password123`

---

## 9. DEBUGGING TIPS

### Backend Debugging

**Enable Debug Mode** (`.env`):
```bash
DEBUG=true
```

**View Logs** (`startup.log`):
```bash
# Logs written by start_server.py
type startup.log       # Windows
cat startup.log        # Linux/Mac
```

**Common Issues**:

1. **"ML model not available"** (503 error)
   - Check `ml_models/` folder has all 3 files
   - Verify scikit-learn version: `pip list | grep scikit-learn` (must be 1.8.0)
   - Check startup log for model loading errors

2. **"Database locked"** (SQLite)
   - Close any DB browser tools
   - Delete `.db-journal` file if exists
   - Restart server

3. **"JWT decode error"**
   - Check SECRET_KEY in `.env` matches between sessions
   - Token might be expired (30 min default)
   - Try login again

4. **CORS errors from frontend**
   - Verify backend CORS middleware is enabled
   - Check frontend URL matches allowed origins
   - Use browser DevTools Network tab to see actual error

### Mobile Debugging

**Flutter DevTools**:
```bash
flutter run --verbose
# Opens DevTools in browser
```

**API Connection Issues**:
```dart
// Check base URL matches backend
static const String baseUrl = 'http://localhost:8080/api/v1';

// For Android emulator, use:
static const String baseUrl = 'http://10.0.2.2:8080/api/v1';

// For physical device on same network:
static const String baseUrl = 'http://192.168.1.xxx:8080/api/v1';
```

**Hot Reload**: Press `r` in terminal running flutter

### Web Debugging

**Browser DevTools**:
- Network tab: See API requests/responses
- Console: See JavaScript errors
- Application > Local Storage: Check tokens

**Common Issues**:

1. **"Failed to fetch"**
   - Backend not running or wrong URL
   - Check `REACT_APP_API_URL` in `.env` (if set)
   - Default: `http://localhost:8080`

2. **Infinite redirect to /login**
   - Token missing or invalid
   - Clear localStorage: `localStorage.clear()`
   - Login again

3. **401 Unauthorized**
   - Token expired
   - Check localStorage for 'token'
   - Try refresh token or re-login

---

## 10. TESTING GUIDELINES

### Backend Testing

**Test File Structure** (`tests/test_*.py`):
```python
import os
import pytest
from fastapi.testclient import TestClient

# Set test environment
os.environ.setdefault("SECRET_KEY", "test-key-32chars-minimum-length!")
os.environ.setdefault("DEBUG", "true")

from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

class TestMyFeature:
    """Tests for my feature endpoints."""
    
    def test_create_success(self, client):
        """Test successful creation."""
        response = client.post("/api/v1/my-feature", json={
            "name": "test",
            "value": 42
        })
        assert response.status_code == 200
        assert response.json()["name"] == "test"
    
    def test_create_unauthorized(self, client):
        """Test creation without auth fails."""
        response = client.post("/api/v1/my-feature", json={})
        assert response.status_code == 401
```

**Run Tests**:
```bash
pytest                              # All tests
pytest tests/test_registration.py  # Specific file
pytest -v                           # Verbose
pytest --cov=app                    # With coverage
```

### Mobile Testing

**Widget Test** (`mobile-app/test/my_widget_test.dart`):
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:adaptiv_health/screens/my_screen.dart';

void main() {
  testWidgets('MyScreen shows loading indicator', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(home: MyScreen(apiClient: MockApiClient())),
    );
    
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
```

**Run Tests**:
```bash
flutter test
flutter test test/my_widget_test.dart
```

### Web Testing

**Component Test** (`web-dashboard/src/components/MyComponent.test.tsx`):
```typescript
import { render, screen } from '@testing-library/react';
import MyComponent from './MyComponent';

test('renders component with title', () => {
  render(<MyComponent title="Test Title" />);
  const titleElement = screen.getByText(/Test Title/i);
  expect(titleElement).toBeInTheDocument();
});
```

**Run Tests**:
```bash
npm test
npm test -- --coverage
```

---

## 11. ENVIRONMENT VARIABLES

### Required Variables

**Backend** (`.env` file in project root):
```bash
# Database
DATABASE_URL=sqlite:///./adaptiv_health.db  # or PostgreSQL URL

# Authentication (REQUIRED)
SECRET_KEY=<32+ character random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# PHI Encryption (REQUIRED if using encrypted fields)
PHI_ENCRYPTION_KEY=<base64-encoded 32-byte key>

# Application
ENVIRONMENT=development
DEBUG=true
APP_NAME=Adaptiv Health API
APP_VERSION=1.0.0

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Security
RATE_LIMIT_PER_MINUTE=60
MAX_LOGIN_ATTEMPTS=3
LOCKOUT_DURATION_MINUTES=5
```

**Generate Keys**:
```bash
# SECRET_KEY (JWT signing)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# PHI_ENCRYPTION_KEY (AES-256)
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

### Optional Variables

```bash
# AWS (for production deployments)
AWS_ACCESS_KEY_ID=<aws-access-key>
AWS_SECRET_ACCESS_KEY=<aws-secret-key>
AWS_REGION=us-east-1
S3_BUCKET_NAME=<bucket-name>
```

### Mobile App

No environment file needed. Configure in code:
```dart
// lib/services/api_client.dart
static const String baseUrl = 'http://localhost:8080/api/v1';
```

### Web Dashboard

Optional `.env` file in `web-dashboard/`:
```bash
REACT_APP_API_URL=http://localhost:8080
```

---

## 12. QUICK REFERENCE

### File Naming
- Python: `snake_case.py`
- Dart: `snake_case.dart`
- TypeScript: `PascalCase.tsx` (components), `camelCase.ts` (services)

### Function Naming
- Python: `snake_case()` - `get_current_user()`, `hash_password()`
- Dart: `camelCase()` - `handleLogin()`, `loadVitals()`
- TypeScript: `camelCase()` - `handleSubmit()`, `fetchData()`

### Async Patterns
- Python: `async def my_func()` with `await`
- Dart: `Future<void> myFunc() async` with `await`
- TypeScript: `async function myFunc()` with `await`

### Environment-Specific Behavior
```python
# Python
if settings.debug:
    logger.debug("Detailed debug info")
```

```dart
// Dart
if (kDebugMode) {
  print('Debug mode only');
}
```

### Common HTTP Status Codes
- `200` OK - Success
- `201` Created - Resource created
- `400` Bad Request - Client error
- `401` Unauthorized - Auth required
- `403` Forbidden - Insufficient permissions
- `404` Not Found - Resource doesn't exist
- `422` Validation Error - Invalid data
- `500` Internal Server Error - Backend error
- `503` Service Unavailable - ML model not loaded

### License & Compliance
- Project: Medical-grade healthcare application
- Data: Protected Health Information (PHI)
- Standards: HIPAA, ISO 3864 (clinical color coding)
- Security: NIST password standards, OWASP recommendations

---

## FINAL NOTES

1. **Always use type hints** in Python (improves IDE support and catches bugs)
2. **Always use try-catch** for API calls in Flutter/React (for error handling)
3. **Never commit `.env` file** to Git (contains secrets)
4. **Always test auth endpoints** with and without tokens
5. **Always validate user input** in schemas (Pydantic validators)
6. **Always use timezone-aware DateTime** (`timezone=True`)
7. **Always hash passwords** before storing (never store plain text)
8. **Always use HTTPS in production** (TLS/SSL certificates)
9. **Always log security events** (failed logins, lockouts, access violations)
10. **Always check role permissions** for sensitive endpoints

For questions or clarifications, refer to inline comments in the source files - they contain extensive documentation explaining WHY decisions were made, not just WHAT the code does.
