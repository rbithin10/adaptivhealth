"""
Document extraction service using Google Gemini.

Extracts structured medical conditions and medications from
uploaded clinical documents (PDF, TXT) using Gemini 2.0 Flash.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 20
# CONSTANTS........................... Line 30
#
# FUNCTIONS
#   - extract_text_from_pdf()......... Line 40  (PDF → plain text)
#   - extract_text_from_file()........ Line 65  (Route by file type)
#   - build_extraction_prompt()....... Line 85  (Gemini prompt template)
#   - extract_medical_data().......... Line 130 (Call Gemini, parse JSON)
#
# BUSINESS CONTEXT:
# - Clinician uploads a clinical document (discharge summary, referral, etc.)
# - Service extracts text, sends to Gemini for structured extraction
# - Returns JSON with conditions + medications for clinician review
# - Uses Gemini 2.0 Flash free tier (15 RPM, 1M tokens/day)
# =============================================================================
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Max text length to send to Gemini (avoid token limits)
MAX_TEXT_LENGTH = 30000


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using PyPDF2.

    Args:
        file_path: Path to the PDF file on disk.

    Returns:
        Concatenated text from all pages.
    """
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        full_text = "\n\n".join(pages_text)
        logger.info(f"Extracted {len(full_text)} chars from PDF ({len(reader.pages)} pages)")
        return full_text
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}")


def extract_text_from_file(file_path: str, file_type: str) -> str:
    """
    Extract text from a file based on its type.

    Args:
        file_path: Path to the file on disk.
        file_type: File extension ('pdf' or 'txt').

    Returns:
        Extracted plain text.
    """
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        logger.info(f"Read {len(text)} chars from TXT file")
        return text
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _build_extraction_prompt(document_text: str) -> str:
    """
    Build the Gemini prompt for medical data extraction.

    Uses our exact condition_type and drug_class enums so the LLM
    output maps directly to our database schema.
    """
    # Truncate if too long
    if len(document_text) > MAX_TEXT_LENGTH:
        document_text = document_text[:MAX_TEXT_LENGTH] + "\n\n[... document truncated ...]"

    return f"""You are a clinical data extraction assistant for a cardiac rehabilitation system.
Extract structured medical data from this clinical document.

Return ONLY valid JSON with this exact structure:
{{
  "conditions": [
    {{
      "condition_type": "<one of: prior_mi, cabg, pci_stent, heart_failure, valve_disease, atrial_fibrillation, other_arrhythmia, hypertension, diabetes_type1, diabetes_type2, dyslipidemia, ckd, copd, pad, stroke_tia, smoking, family_cvd, obesity, other>",
      "condition_detail": "<brief detail, e.g. 'NYHA Class II', 'LAD stent 2023'>",
      "status": "<one of: active, resolved, managed>"
    }}
  ],
  "medications": [
    {{
      "drug_class": "<one of: beta_blocker, ace_inhibitor, arb, antiplatelet, anticoagulant, statin, diuretic, ccb, nitrate, antiarrhythmic, insulin, metformin, sglt2_inhibitor, other>",
      "drug_name": "<medication name, e.g. 'Metoprolol 50mg'>",
      "dose": "<dosage, e.g. '50mg'>",
      "frequency": "<one of: daily, twice_daily, three_times_daily, as_needed, weekly>"
    }}
  ]
}}

Rules:
- Only extract conditions and medications that are clearly stated in the document.
- If something is unclear or ambiguous, omit it rather than guessing.
- Use the exact enum values listed above for condition_type, drug_class, status, and frequency.
- For condition_detail, include specific clinical details (NYHA class, vessel involved, year, etc.)
- If no conditions or medications are found, return empty arrays.

Document text:
---
{document_text}
---"""


async def extract_medical_data(
    file_path: str,
    file_type: str,
    gemini_api_key: Optional[str] = None,
) -> dict:
    """
    Extract structured medical data from a clinical document using Gemini.

    Flow:
    1. Extract raw text from file (PDF or TXT)
    2. Build extraction prompt with our schema enums
    3. Call Gemini 2.0 Flash API
    4. Parse JSON response

    Args:
        file_path: Path to the uploaded file.
        file_type: File extension ('pdf' or 'txt').
        gemini_api_key: Google Gemini API key.

    Returns:
        Dict with 'conditions' and 'medications' lists, or error info.
    """
    # Step 1: Extract text
    try:
        document_text = extract_text_from_file(file_path, file_type)
    except ValueError as e:
        return {"conditions": [], "medications": [], "error": str(e)}

    if not document_text.strip():
        return {
            "conditions": [],
            "medications": [],
            "error": "No text could be extracted from the document."
        }

    # Step 2: Check API key
    if not gemini_api_key:
        logger.warning("No Gemini API key configured — returning empty extraction")
        return {
            "conditions": [],
            "medications": [],
            "error": "Gemini API key not configured. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env and restart backend."
        }

    # Step 3: Call Gemini
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_api_key)

        prompt = _build_extraction_prompt(document_text)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,  # Low temperature for factual extraction
            ),
        )

        # Step 4: Parse response
        response_text = response.text.strip()
        logger.info(f"Gemini response length: {len(response_text)} chars")

        extracted = json.loads(response_text)

        # Validate structure
        conditions = extracted.get("conditions", [])
        medications = extracted.get("medications", [])

        logger.info(
            f"Extraction complete: {len(conditions)} conditions, "
            f"{len(medications)} medications"
        )

        return {
            "conditions": conditions,
            "medications": medications,
            "error": None
        }

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        return {
            "conditions": [],
            "medications": [],
            "error": "AI returned invalid JSON. Please try again or enter data manually."
        }
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        return {
            "conditions": [],
            "medications": [],
            "error": f"AI extraction failed: {str(e)}. Please enter data manually."
        }
