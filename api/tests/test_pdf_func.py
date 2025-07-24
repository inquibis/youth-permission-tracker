from pdf_func import generate_waiver_pdf
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_generate_waiver_pdf_creates_file():
    out_path = "/mnt/data/test_waiver.pdf"
    generate_waiver_pdf(
        user_name="John Doe",
        guardian_name="Jane Doe",
        activity_name="Test Event",
        date_start="2024-01-01",
        date_end="2024-01-02",
        description="A test description.",
        ip="127.0.0.1",
        user_agent="pytest",
        output_path=out_path
    )
    assert os.path.exists(out_path)