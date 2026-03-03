# Adaptiv Health - Development Roadmap

> **Last updated**: March 2026

---

## Remaining Work

### Web Dashboard QA
- [ ] Admin Page CRUD end-to-end manual testing (P0 blocker)
- [ ] Clinician patient filtering verification

### Mobile App
- [ ] Edge AI runtime stabilization (offline sync false states)
- [ ] Heart rate ring — replace placeholder with real rendering / animation

### Documentation
- [ ] Update architecture diagrams for 5-tab UX
- [x] ~~Create deployment checklist + production walkthrough~~ (see `docs/DEPLOYMENT_CHECKLIST.md`)

### Testing
- [ ] Close final ~2 % backend test coverage gap

---

## Future Enhancements

### Push Notifications
- Integration with a push notification provider
- Real-time alerts to users when vital thresholds are exceeded
- Caregiver and clinician notifications for high-risk patients

### Email System
- SMTP server configuration (SendGrid / AWS SES)
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

### BLE Integration
- [x] Phase 1: Heart Rate BLE (HRS 0x180D scan, connect, stream)
- [x] Phase 2: HealthKit / Google Fit via `health` package
- [x] Phase 3: `VitalsProvider` abstraction (BLE → Health → Mock fallback)
- [ ] Phase 4: Background BLE + auto-reconnect

---

## Notes

- Email sending requires SMTP configuration; reset tokens are currently logged for dev/testing
- Alert thresholds are hardcoded but designed for easy per-user customization
- All completed features (alerts, password reset, caregiver access, sparkline charts, notification bell) have been validated
