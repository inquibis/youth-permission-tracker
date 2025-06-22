import pytest
import os
from api.pdf_func import create_signed_pdf

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
