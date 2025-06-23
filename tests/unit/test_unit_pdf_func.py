import pytest
import os
from api.pdf_func import create_signed_pdf, generate_waiver_pdf

def test_create_signed_pdf(tmp_path):
    # Prepare sample data
    sample_data = {
        "activity_id": "test123",
        "allergies": "Peanuts",
        "restrictions": None,
        "special_diet": None,
        "prescriptions": None,
        "over_the_counter_drugs": None,
        "chronic_illness": None,
        "surgeries_12mo": None,
        "serious_illnesses": None,
        "comments": "No comments",
        "signature": None
    }

    ip = "127.0.0.1"
    user_agent = "pytest"

    # Override PDF_DIR temporarily if needed
    pdf_path = create_signed_pdf(sample_data, ip, user_agent)
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")

    # Clean up if needed
    os.remove(pdf_path)

def test_generate_pdf_creates_file(tmp_path):
    output_file = tmp_path / "test_waiver.pdf"
    generate_waiver_pdf(
        user_name="Test User",
        guardian_name="Guardian",
        activity_name="Campout",
        date_start="2025-07-01",
        date_end="2025-07-03",
        description="Overnight outdoor camp.",
        ip="123.45.67.89",
        user_agent="UnitTestAgent/1.0",
        output_path=str(output_file)
    )
    assert output_file.exists()
    assert output_file.stat().st_size > 100  # basic size check
