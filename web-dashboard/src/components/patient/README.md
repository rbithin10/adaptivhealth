# patient/ — Patient Health Display Panels

Panels and sections used on the Patient Detail page to display different aspects of a patient's health data.

## Files

| File | Purpose |
|------|---------|
| `VitalsPanel.tsx` | Shows live vital signs (heart rate, SpO2, blood pressure) as cards, plus a line chart of vitals history |
| `RiskAssessmentPanel.tsx` | Displays the AI-generated risk assessment — risk level, contributing factors, and health recommendations |
| `AlertsPanel.tsx` | Lists health alerts for a patient with Acknowledge and Resolve action buttons |
| `SessionHistoryPanel.tsx` | Shows a timeline of past exercise sessions with duration, type, heart rate, and recovery time |
| `AdvancedMLPanel.tsx` | A collapsible panel for AI anomaly detection results — header turns amber if anomalies are found |
| `PredictionExplainabilityPanel.tsx` | Explains WHY the AI made a risk prediction — shows which health factors contributed most with visual bars |
| `MedicalProfilePanel.tsx` | A collapsible panel showing the patient's medical conditions and medications with badge counts |
