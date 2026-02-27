# Adaptiv Health - Development Roadmap

This document consolidates all TODO items and planned features not yet implemented.

## Completed Items ✅

### 🚨 Alert & Notification System
**Status**: ✅ **COMPLETED**  
**Priority**: High  
**Files affected**:
- `app/api/vital_signs.py`

**Implemented**:
- [x] Implement alert checking logic in `check_vitals_for_alerts()` function
- [x] Create alert records in database when thresholds are exceeded
- [x] Implement alert counting in vitals summary
- [x] Alert triggers when HR > 180 BPM (CRITICAL severity)
- [x] Alert triggers when SpO2 < 90% (CRITICAL severity)
- [x] Alert triggers when systolic BP > 160 mmHg (WARNING severity)
- [x] All alerts include title, message, action_required, and trigger values
- [x] Alerts are queryable via database

**Note**: Push notifications to users/caregivers would require integration with a notification service (Firebase, OneSignal, etc.) - this is marked for future enhancement.

---

### 🔐 Email & Password Reset
**Status**: ✅ **COMPLETED** (Core functionality)  
**Priority**: High  
**Files affected**:
- `app/api/auth.py`
- `app/services/auth_service.py`

**Implemented**:
- [x] Password reset token generation with 1-hour expiration
- [x] Token validation and decoding
- [x] Password update functionality
- [x] Failed login attempts reset on password change
- [x] Account unlocking on successful password reset
- [x] Protection against email enumeration attacks

**Note**: Email sending requires SMTP configuration (SendGrid, AWS SES, etc.). The token is currently logged for development/testing. To enable email in production, configure an email service and implement the `send_reset_email` background task.

---

### 👥 Caregiver Access Control
**Status**: ✅ **COMPLETED** (Basic implementation)  
**Priority**: Medium  
**Files affected**:
- `app/api/user.py`
- `app/models/user.py`

**Implemented**:
- [x] Caregiver role access to patient data
- [x] Permission checking in `can_access_user()` function
- [x] Access logging for audit trail
- [x] Self-access, admin, clinician, and caregiver access rules

**Note**: Advanced caregiver-patient assignment relationship (many-to-many table) can be added in the future for granular control. Current implementation allows all caregivers to access all patient data, which is suitable for small teams or family caregiver scenarios.

---

### Other Completed Items
- [x] Critical logic error fixes (lockout time, user ID references)
- [x] API endpoint consistency (vitals submission URL)
- [x] Data validation (SpO2 range checking)
- [x] Recommendation generation logic
- [x] Security middleware configuration
- [x] Token type preservation in JWT tokens

---

## Outstanding Development Items

### 📊 UI Placeholders
**Status**: Not implemented  
**Priority**: Low-Medium  
**Files affected**:
- `mobile-app/lib/screens/home_screen.dart` (lines 273, 452)

**Tasks**:
- [ ] Replace heart rate ring with actual rendering (currently uses custom painter)
- [ ] Implement sparkline charts for vitals trends
- [ ] Add animations for real-time data updates
- [ ] Implement notification bell functionality

---

## Future Enhancements

### Push Notifications
- Integration with Firebase Cloud Messaging or OneSignal
- Real-time alerts to users when vital thresholds are exceeded
- Caregiver and clinician notifications for high-risk patients

### Email System
- SMTP server configuration
- Email template system for password reset emails
- Email verification for new user registration

### Advanced Caregiver Management
- Caregiver-to-patient assignment table (many-to-many relationship)
- Permission granularity (view-only vs. manage)
- Caregiver invitation system
- Audit trail for all caregiver actions

### Customizable Alert Thresholds
- User-specific alert thresholds
- Clinician-managed alert settings
- Age and condition-based threshold recommendations

---

## Notes

- Email implementation should use environment-based configuration
- Alert thresholds are currently hardcoded but designed for easy customization
- UI components are designed for easy enhancement and incremental improvement
- All completed features have been tested and validated
