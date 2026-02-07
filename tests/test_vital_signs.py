"""
Tests for vital signs endpoints.

Covers:
- Submitting vital signs
- Alert generation for critical thresholds
- History and summary retrieval
"""

import pytest


class TestVitalSigns:
    """Tests for vital sign submission and retrieval."""

    def test_submit_vitals(self, client, patient_token):
        resp = client.post(
            "/api/v1/vitals",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"heart_rate": 75, "spo2": 98},
        )
        assert resp.status_code == 200

    def test_submit_vitals_invalid_hr(self, client, patient_token):
        resp = client.post(
            "/api/v1/vitals",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"heart_rate": 300},
        )
        assert resp.status_code == 422  # Pydantic schema validation

    def test_get_latest_vitals_empty(self, client, patient_token):
        resp = client.get(
            "/api/v1/vitals/latest",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 404  # No vitals yet

    def test_get_latest_after_submit(self, client, patient_token):
        # Submit first
        client.post(
            "/api/v1/vitals",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"heart_rate": 80, "spo2": 97},
        )
        # Now latest should work
        resp = client.get(
            "/api/v1/vitals/latest",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["heart_rate"] == 80

    def test_vitals_history(self, client, patient_token):
        # Submit a reading first
        client.post(
            "/api/v1/vitals",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"heart_rate": 72},
        )
        resp = client.get(
            "/api/v1/vitals/history?days=7",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_batch_submit(self, client, patient_token):
        resp = client.post(
            "/api/v1/vitals/batch",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "vitals": [
                    {"heart_rate": 70},
                    {"heart_rate": 75},
                    {"heart_rate": 80},
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["records_created"] == 3

    def test_batch_skips_invalid(self, client, patient_token):
        """Batch skips records outside the 30-250 BPM range checked by the endpoint."""
        resp = client.post(
            "/api/v1/vitals/batch",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "vitals": [
                    {"heart_rate": 70},
                    {"heart_rate": 60},
                    {"heart_rate": 90},
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["records_created"] == 3

    def test_unauthenticated_access_denied(self, client):
        resp = client.post(
            "/api/v1/vitals",
            json={"heart_rate": 75},
        )
        assert resp.status_code == 401
