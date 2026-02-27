"""
tests/test_predict_807.py

Covers predict.py line 807:
    raise HTTPException(status_code=404, detail="No recommendations found")

Calls the async function DIRECTLY - no HTTP, no auth, no middleware.
"""
import asyncio
import uuid
import pytest
from fastapi import HTTPException
from tests.helpers import make_user


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_predict_807_no_recommendations(db_session):
    """
    Call get_patient_latest_recommendation directly with a patient
    who has zero ExerciseRecommendation rows → hits line 807.
    """
    from app.api.predict import get_patient_latest_recommendation

    clinician = make_user(
        db_session,
        f"doc807_{uuid.uuid4().hex[:8]}@test.com",
        "Doc 807",
        "clinician",
    )
    patient = make_user(
        db_session,
        f"pat807_{uuid.uuid4().hex[:8]}@test.com",
        "Pat 807",
        "patient",
    )
    # Ensure share_state allows access
    patient.share_state = "SHARING_ON"
    db_session.commit()

    # Call the async function directly — no FastAPI, no JWT, no middleware
    with pytest.raises(HTTPException) as exc_info:
        _run(
            get_patient_latest_recommendation(
                user_id=patient.user_id,
                current_user=clinician,
                db=db_session,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No recommendations found"
