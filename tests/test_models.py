"""
Tests for model methods.

Covers model methods at 0%:
- User: calculate_max_heart_rate, get_heart_rate_zones, is_account_locked, properties, __repr__
- VitalSignRecord: is_heart_rate_abnormal, is_spo2_low, get_risk_indicators, to_dict, __repr__, properties
- Alert: acknowledge, resolve, get_severity_color, to_dict, __repr__, properties
- AuthCredential: is_locked, to_dict, __repr__
- ActivitySession: id, to_dict, __repr__
- ExerciseRecommendation: id, __repr__
- RiskAssessment: id, __repr__

Run with:
    pytest tests/test_models.py -v
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.models.user import User
from app.models.vital_signs import VitalSignRecord
from app.models.alert import Alert
from app.models.auth_credential import AuthCredential
from app.models.activity import ActivitySession
from app.models.recommendation import ExerciseRecommendation
from app.models.risk_assessment import RiskAssessment


# =============================================================================
# User Model Tests
# =============================================================================

class TestUserModel:
    """Test User model methods from app/models/user.py."""

    def test_calculate_max_heart_rate_young(self, db_session):
        """Test max heart rate calculation for young person."""
        user = User(
            email="young@example.com",
            full_name="Young Person",
            age=30,
            role="patient"
        )
        
        max_hr = user.calculate_max_heart_rate()
        assert max_hr == 190  # 220 - 30

    def test_calculate_max_heart_rate_old(self, db_session):
        """Test max heart rate calculation for older person."""
        user = User(
            email="old@example.com",
            full_name="Senior Person",
            age=55,
            role="patient"
        )
        
        max_hr = user.calculate_max_heart_rate()
        assert max_hr == 165  # 220 - 55

    def test_get_heart_rate_zones(self, db_session):
        """Test heart rate zone calculation."""
        user = User(
            email="athlete@example.com",
            full_name="Athlete",
            age=40,
            role="patient"
        )
        
        zones = user.get_heart_rate_zones()
        
        assert isinstance(zones, dict)
        assert "light" in zones
        assert "moderate" in zones
        assert "vigorous" in zones
        assert "high" in zones
        assert "maximum" in zones
        
        # Zones should be tuples with (min, max)
        assert isinstance(zones["light"], tuple)
        assert len(zones["light"]) == 2
        # Zones should be in ascending order
        assert zones["light"][1] <= zones["moderate"][0]
        assert zones["moderate"][1] <= zones["vigorous"][0]

    def test_is_account_locked_not_locked(self, db_session):
        """Test account not locked."""
        user = User(
            email="free@example.com",
            full_name="Free User",
            age=30,
            role="patient"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create auth credential with no lock
        cred = AuthCredential(
            user_id=user.user_id,
            hashed_password="fakehash",
            failed_login_attempts=0,
            locked_until=None
        )
        db_session.add(cred)
        db_session.commit()
        
        assert user.is_account_locked() is False

    def test_is_account_locked_when_locked(self, db_session):
        """Test account locked."""
        user = User(
            email="locked@example.com",
            full_name="Locked User",
            age=30,
            role="patient"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create auth credential with future lock
        future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        cred = AuthCredential(
            user_id=user.user_id,
            hashed_password="fakehash",
            failed_login_attempts=3,
            locked_until=future_time
        )
        db_session.add(cred)
        db_session.commit()
        
        assert user.is_account_locked() is True

    def test_baseline_heart_rate_property(self, db_session):
        """Test baseline_heart_rate property returns baseline_hr."""
        user = User(
            email="baseline@example.com",
            full_name="Baseline User",
            age=30,
            role="patient",
            baseline_hr=65
        )
        
        assert user.baseline_heart_rate == 65

    def test_max_heart_rate_property(self, db_session):
        """Test max_heart_rate property returns max_safe_hr."""
        user = User(
            email="maxhr@example.com",
            full_name="Max HR User",
            age=30,
            role="patient",
            max_safe_hr=180
        )
        
        assert user.max_heart_rate == 180

    def test_user_repr(self, db_session):
        """Test __repr__ returns string with user info."""
        user = User(
            user_id=123,
            email="repr@example.com",
            full_name="Repr User",
            age=30,
            role="patient"
        )
        
        repr_str = repr(user)
        assert isinstance(repr_str, str)
        assert "User" in repr_str
        assert "123" in repr_str or "repr@example.com" in repr_str


# =============================================================================
# VitalSignRecord Model Tests
# =============================================================================

class TestVitalSignRecordModel:
    """Test VitalSignRecord model methods from app/models/vital_signs.py."""

    def test_is_heart_rate_abnormal_high(self, db_session):
        """Test detects abnormally high heart rate."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=200,
            spo2=98,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert vital.is_heart_rate_abnormal() is True

    def test_is_heart_rate_abnormal_low(self, db_session):
        """Test detects abnormally low heart rate."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=35,
            spo2=98,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert vital.is_heart_rate_abnormal() is True

    def test_is_heart_rate_normal(self, db_session):
        """Test normal heart rate not flagged."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=75,
            spo2=98,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert vital.is_heart_rate_abnormal() is False

    def test_is_spo2_low_true(self, db_session):
        """Test detects low SpO2."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=75,
            spo2=85,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert vital.is_spo2_low() is True

    def test_is_spo2_normal(self, db_session):
        """Test normal SpO2 not flagged."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=75,
            spo2=98,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert vital.is_spo2_low() is False

    def test_get_risk_indicators(self, db_session):
        """Test risk indicators returns list."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=195,
            spo2=87,
            timestamp=datetime.now(timezone.utc)
        )
        
        indicators = vital.get_risk_indicators()
        
        assert isinstance(indicators, list)
        assert len(indicators) > 0
        # Should flag both tachycardia and hypoxemia
        assert "tachycardia" in indicators
        assert "hypoxemia" in indicators

    def test_to_dict(self, db_session):
        """Test to_dict returns dict with all fields."""
        vital = VitalSignRecord(
            reading_id=uuid4(),
            user_id=1,
            heart_rate=75,
            spo2=98,
            systolic_bp=120,
            diastolic_bp=80,
            timestamp=datetime.now(timezone.utc)
        )
        
        data = vital.to_dict()
        
        assert isinstance(data, dict)
        assert "reading_id" in data or "id" in data
        assert "user_id" in data
        assert "heart_rate" in data
        assert "spo2" in data
        assert data["heart_rate"] == 75

    def test_blood_pressure_properties(self, db_session):
        """Test blood pressure properties."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=75,
            spo2=98,
            systolic_bp=120,
            diastolic_bp=80,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert vital.blood_pressure_systolic == 120
        assert vital.blood_pressure_diastolic == 80

    def test_vital_repr(self, db_session):
        """Test __repr__ returns string with vital info."""
        vital = VitalSignRecord(
            reading_id=uuid4(),
            user_id=1,
            heart_rate=75,
            spo2=98,
            timestamp=datetime.now(timezone.utc)
        )
        
        repr_str = repr(vital)
        assert isinstance(repr_str, str)
        assert "Vital" in repr_str or "75" in repr_str


# =============================================================================
# Alert Model Tests
# =============================================================================

class TestAlertModel:
    """Test Alert model methods from app/models/alert.py."""

    def test_acknowledge(self, db_session):
        """Test acknowledge sets acknowledged to True."""
        alert = Alert(
            user_id=1,
            alert_type="HIGH_HEART_RATE",
            severity="critical",
            title="High HR",
            message="HR above safe limit",
            acknowledged=False
        )
        db_session.add(alert)
        db_session.commit()
        
        alert.acknowledge(by="user")
        
        assert alert.acknowledged is True

    def test_resolve(self, db_session):
        """Test resolve sets resolved fields."""
        alert = Alert(
            user_id=1,
            alert_type="HIGH_HEART_RATE",
            severity="warning",
            title="High HR",
            message="HR elevated",
            is_resolved=False
        )
        db_session.add(alert)
        db_session.commit()
        
        alert.resolve(resolved_by="clinician", notes="Patient rested, HR normalized")
        
        assert alert.is_resolved is True
        assert alert.resolved_by == "clinician"
        assert alert.resolved_at is not None
        assert alert.resolution_notes == "Patient rested, HR normalized"

    def test_get_severity_color_critical(self, db_session):
        """Test severity color for critical alert."""
        alert = Alert(
            user_id=1,
            alert_type="HIGH_HEART_RATE",
            severity="critical",
            title="Critical HR",
            message="HR dangerously high"
        )
        
        color = alert.get_severity_color()
        assert color == "#EF4444"  # Critical red

    def test_get_severity_color_warning(self, db_session):
        """Test severity color for warning alert."""
        alert = Alert(
            user_id=1,
            alert_type="ELEVATED_HR",
            severity="warning",
            title="Warning",
            message="HR elevated"
        )
        
        color = alert.get_severity_color()
        assert color == "#F59E0B"  # Warning orange

    def test_get_severity_color_info(self, db_session):
        """Test severity color for info alert."""
        alert = Alert(
            user_id=1,
            alert_type="REMINDER",
            severity="info",
            title="Info",
            message="Time for workout"
        )
        
        color = alert.get_severity_color()
        assert color == "#6B7280"  # Info/default gray

    def test_alert_properties(self, db_session):
        """Test alert properties."""
        alert_id = uuid4()
        created_time = datetime.now(timezone.utc)
        
        alert = Alert(
            alert_id=alert_id,
            user_id=1,
            alert_type="HIGH_HEART_RATE",
            severity="critical",
            title="High HR",
            message="HR high",
            created_at=created_time,
            acknowledged=False
        )
        
        assert alert.id == alert_id
        assert alert.severity_level == "critical"
        assert alert.alert_time == created_time
        assert alert.is_acknowledged is False

    def test_alert_to_dict(self, db_session):
        """Test to_dict returns dict with all fields."""
        alert = Alert(
            alert_id=uuid4(),
            user_id=1,
            alert_type="HIGH_HEART_RATE",
            severity="critical",
            title="High HR",
            message="HR high"
        )
        
        data = alert.to_dict()
        
        assert isinstance(data, dict)
        assert "alert_id" in data or "id" in data
        assert "alert_type" in data
        assert "severity" in data

    def test_alert_repr(self, db_session):
        """Test __repr__ returns string with alert info."""
        alert = Alert(
            alert_id=uuid4(),
            user_id=1,
            alert_type="HIGH_HEART_RATE",
            severity="critical",
            title="High HR",
            message="HR high"
        )
        
        repr_str = repr(alert)
        assert isinstance(repr_str, str)
        assert "Alert" in repr_str


# =============================================================================
# AuthCredential Model Tests
# =============================================================================

class TestAuthCredentialModel:
    """Test AuthCredential model methods from app/models/auth_credential.py."""

    def test_is_locked_true(self, db_session):
        """Test is_locked returns True when locked."""
        future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        cred = AuthCredential(
            user_id=1,
            hashed_password="fakehash",
            failed_login_attempts=3,
            locked_until=future_time
        )
        
        assert cred.is_locked() is True

    def test_is_locked_false_no_lock(self, db_session):
        """Test is_locked returns False when no lock."""
        cred = AuthCredential(
            user_id=1,
            hashed_password="fakehash",
            failed_login_attempts=0,
            locked_until=None
        )
        
        assert cred.is_locked() is False

    def test_is_locked_false_expired(self, db_session):
        """Test is_locked returns False when lock expired."""
        past_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        cred = AuthCredential(
            user_id=1,
            hashed_password="fakehash",
            failed_login_attempts=3,
            locked_until=past_time
        )
        
        assert cred.is_locked() is False

    def test_auth_credential_to_dict(self, db_session):
        """Test to_dict returns dict."""
        cred = AuthCredential(
            credential_id=uuid4(),
            user_id=1,
            hashed_password="fakehash",
            failed_login_attempts=0,
            locked_until=None
        )
        
        data = cred.to_dict()
        
        assert isinstance(data, dict)
        assert "credential_id" in data or "user_id" in data
        assert "failed_login_attempts" in data

    def test_auth_credential_repr(self, db_session):
        """Test __repr__ returns string."""
        cred = AuthCredential(
            user_id=1,
            hashed_password="fakehash",
            failed_login_attempts=0,
            locked_until=None
        )
        
        repr_str = repr(cred)
        assert isinstance(repr_str, str)
        assert "AuthCredential" in repr_str or "Credential" in repr_str


# =============================================================================
# ActivitySession Model Tests
# =============================================================================

class TestActivitySessionModel:
    """Test ActivitySession model methods from app/models/activity.py."""

    def test_activity_id_property(self, db_session):
        """Test id property returns session_id."""
        session = ActivitySession(
            session_id=uuid4(),
            user_id=1,
            activity_type="WALKING",
            duration_minutes=20,
            start_time=datetime.now(timezone.utc)
        )
        
        assert session.id == session.session_id

    def test_activity_to_dict(self, db_session):
        """Test to_dict returns dict."""
        session = ActivitySession(
            session_id=uuid4(),
            user_id=1,
            activity_type="WALKING",
            duration_minutes=20,
            start_time=datetime.now(timezone.utc)
        )
        
        data = session.to_dict()
        
        assert isinstance(data, dict)
        assert "session_id" in data or "user_id" in data
        assert "activity_type" in data or "duration_minutes" in data

    def test_activity_repr(self, db_session):
        """Test __repr__ returns string."""
        session = ActivitySession(
            session_id=uuid4(),
            user_id=1,
            activity_type="WALKING",
            duration_minutes=20,
            start_time=datetime.now(timezone.utc)
        )
        
        repr_str = repr(session)
        assert isinstance(repr_str, str)
        assert "Activity" in repr_str or "Session" in repr_str


# =============================================================================
# ExerciseRecommendation Model Tests
# =============================================================================

class TestExerciseRecommendationModel:
    """Test ExerciseRecommendation model methods from app/models/recommendation.py."""

    def test_recommendation_id_property(self, db_session):
        """Test id property returns recommendation_id."""
        rec = ExerciseRecommendation(
            recommendation_id=uuid4(),
            user_id=1,
            suggested_activity="WALKING",
            duration_minutes=20,
            intensity_level="LIGHT"
        )
        
        assert rec.id == rec.recommendation_id

    def test_recommendation_repr(self, db_session):
        """Test __repr__ returns string."""
        rec = ExerciseRecommendation(
            recommendation_id=uuid4(),
            user_id=1,
            suggested_activity="WALKING",
            duration_minutes=20,
            intensity_level="LIGHT"
        )
        
        repr_str = repr(rec)
        assert isinstance(repr_str, str)
        assert "Recommendation" in repr_str or "WALKING" in repr_str


# =============================================================================
# RiskAssessment Model Tests
# =============================================================================

class TestRiskAssessmentModel:
    """Test RiskAssessment model methods from app/models/risk_assessment.py."""

    def test_risk_assessment_id_property(self, db_session):
        """Test id property returns assessment_id."""
        assessment = RiskAssessment(
            assessment_id=uuid4(),
            user_id=1,
            risk_score=0.35,
            risk_level="LOW"
        )
        
        assert assessment.id == assessment.assessment_id

    def test_risk_assessment_repr(self, db_session):
        """Test __repr__ returns string."""
        assessment = RiskAssessment(
            assessment_id=uuid4(),
            user_id=1,
            risk_score=0.35,
            risk_level="LOW"
        )
        
        repr_str = repr(assessment)
        assert isinstance(repr_str, str)
        assert "Risk" in repr_str or "Assessment" in repr_str or "0.35" in repr_str


# =============================================================================
# Additional Model Branch Coverage
# =============================================================================

class TestModelBranchCoverage:
    """Additional branch coverage for model methods."""

    def test_calculate_max_heart_rate_age_none_returns_default(self, db_session):
        """Test max heart rate calculation when age is None."""
        user = User(
            email="no_age@example.com",
            full_name="No Age",
            age=None,
            role="patient"
        )
        
        max_hr = user.calculate_max_heart_rate()
        # Should return default (typically 180 or 220)
        assert isinstance(max_hr, int)
        assert max_hr > 0

    def test_is_account_locked_empty_auth_credentials(self, db_session):
        """Test is_account_locked when auth_credentials list is empty."""
        user = User(
            email="empty_cred@example.com",
            full_name="Empty Cred",
            role="patient"
        )
        # No auth_credential relationship set
        
        is_locked = user.is_account_locked()
        assert isinstance(is_locked, bool)

    def test_vital_sign_blood_pressure_both_none_returns_none(self, db_session):
        """Test blood_pressure property when both systolic and diastolic are None."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=75,
            spo2=98,
            systolic_bp=None,
            diastolic_bp=None,
            timestamp=datetime.now(timezone.utc)
        )
        
        bp = vital.blood_pressure
        assert bp is None or bp == {"systolic": None, "diastolic": None}

    def test_is_spo2_low_spo2_none_returns_false(self, db_session):
        """Test is_spo2_low when spo2 is None."""
        vital = VitalSignRecord(
            user_id=1,
            heart_rate=75,
            spo2=None,
            systolic_bp=120,
            diastolic_bp=80,
            timestamp=datetime.now(timezone.utc)
        )
        
        is_low = vital.is_spo2_low()
        assert isinstance(is_low, bool)
        assert is_low is False
