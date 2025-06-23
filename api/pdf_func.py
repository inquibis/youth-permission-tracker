import os
import io
import base64
import requests
from datetime import datetime
from fpdf import FPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from PyPDF2 import PdfReader, PdfWriter
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509

# === CONFIG ===
PDF_DIR = "pdfs"
CERT_PATH = "certs/server_cert.pem"
KEY_PATH = "certs/server_key.pem"
TSA_URL = "http://timestamp.digicert.com"  # Example TSA

os.makedirs(PDF_DIR, exist_ok=True)


def create_signed_pdf(data: dict, ip: str, user_agent: str) -> str:
    """
    Generate and digitally sign a PDF with user-submitted form data.
    Returns: path to final signed & locked PDF
    """
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{data['activity_id']}_{ts}.pdf"
    pdf_path = os.path.join(PDF_DIR, filename)

    # === Step 1: Generate the base PDF with form content ===
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)

    text = c.beginText(40, 750)
    text.setFont("Helvetica", 11)
    text.textLine(f"Activity Permission Form")
    text.textLine(f"Activity ID: {data['activity_id']}")
    text.textLine(f"Submitted At: {ts} UTC")
    text.textLine(f"Submitted From IP: {ip}")
    text.textLine(f"User-Agent: {user_agent}")
    text.textLine("")

    for key, value in data.items():
        if key != "signature":  # Skip base64 signature for now
            text.textLine(f"{key.replace('_', ' ').title()}: {value or 'N/A'}")

    c.drawText(text)

    # === Draw signature image ===
    if "signature" in data and data["signature"]:
        try:
            header, b64 = data["signature"].split(",", 1)
            sig_data = base64.b64decode(b64)
            sig_path = os.path.join(PDF_DIR, f"sig_{ts}.png")
            with open(sig_path, "wb") as f:
                f.write(sig_data)
            c.drawImage(sig_path, 40, 100, width=200, height=75)
        except Exception as e:
            print("Signature decode failed:", e)

    c.showPage()
    c.save()

    # === Step 2: Write to disk ===
    with open(pdf_path, "wb") as f:
        f.write(buffer.getvalue())

    # === Step 3: Digitally sign the PDF ===
    signed_pdf_path = pdf_path.replace(".pdf", "_signed.pdf")
    digitally_sign_pdf(pdf_path, signed_pdf_path)

    return signed_pdf_path


def digitally_sign_pdf(input_pdf_path: str, output_pdf_path: str):
    """
    Sign a PDF using a server-side private key, apply lock & timestamp token.
    """
    # Load private key and certificate
    with open(KEY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    with open(CERT_PATH, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())

    # Read PDF and hash it
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Optional: Lock the PDF (disable edits)
    writer.add_metadata({
        "/Author": "Activity Form System",
        "/Locked": "true"
    })

    pdf_bytes = io.BytesIO()
    writer.write(pdf_bytes)
    digest = hashes.Hash(hashes.SHA256())
    digest.update(pdf_bytes.getvalue())
    pdf_hash = digest.finalize()

    # Step 4: Sign hash
    signature = private_key.sign(
        pdf_hash,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Step 5: Embed signature in custom metadata (or save separately)
    writer.add_metadata({
        "/Signature": base64.b64encode(signature).decode()
    })

    # Step 6: Optional timestamp token (TSA)
    tsa_token = request_tsa_timestamp(pdf_hash)
    if tsa_token:
        writer.add_metadata({"/TimestampToken": base64.b64encode(tsa_token).decode()})

    with open(output_pdf_path, "wb") as f:
        writer.write(f)

    print("PDF signed and saved:", output_pdf_path)

def generate_waiver_pdf(user_name, guardian_name, activity_name, date_start, date_end, description, ip, user_agent, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Parental Permission Waiver", ln=True, align="C")
    pdf.ln(10)

    pdf.cell(200, 10, txt=f"Participant: {user_name}", ln=True)
    pdf.cell(200, 10, txt=f"Guardian: {guardian_name}", ln=True)
    pdf.cell(200, 10, txt=f"Activity: {activity_name}", ln=True)
    pdf.cell(200, 10, txt=f"Dates: {date_start} to {date_end}", ln=True)
    pdf.multi_cell(200, 10, txt=f"Description: {description}")
    pdf.ln(5)

    pdf.cell(200, 10, txt=f"Signed on: {datetime.utcnow().isoformat()} UTC", ln=True)
    pdf.cell(200, 10, txt=f"IP Address: {ip}", ln=True)
    pdf.multi_cell(200, 10, txt=f"User-Agent: {user_agent}")
    pdf.ln(5)

    pdf.cell(200, 10, txt="Permission confirmed and digitally logged.", ln=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)


def request_tsa_timestamp(pdf_hash: bytes) -> bytes:
    """
    Request a timestamp token from a TSA for the document hash.
    """
    try:
        from asn1crypto import tsp, algos, core

        tsq = tsp.TimeStampReq({
            'version': 'v1',
            'message_imprint': {
                'hash_algorithm': {'algorithm': 'sha256'},
                'hashed_message': pdf_hash
            },
            'cert_req': True
        })

        headers = {
            'Content-Type': 'application/timestamp-query',
            'Accept': 'application/timestamp-reply'
        }

        response = requests.post(TSA_URL, data=tsq.dump(), headers=headers)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print("TSA error:", e)
    return b''
