from borb.pdf import Document, Page, SingleColumnLayout, Paragraph
from borb.pdf import PDF, SignatureWidget, Rectangle
from pathlib import Path

from pdfrw import PdfReader, PdfWriter, PageMerge, PdfDict

import dropbox

class YouthPermissionRequestor:
  TEMPLATE_PATH = '2017_parental_or_guardian_permission_medical_release.pdf'
  OUTPUT_PATH = 'filled_permission_form.pdf'

  ANNOT_KEY = '/Annots'
  ANNOT_FIELD_KEY = '/T'
  ANNOT_VAL_KEY = '/V'

  data = {
    "Participant": input("Participant full name: "),
    "Date of birth": input("Date of birth (MM/DD/YYYY): "),
    "Age": input("Age: "),
    "Event": input("Event name: "),
    "Dates of event": input("Event dates: "),
    "Ward": input("Ward: "),
    "Stake": input("Stake: "),
    "Event or activity leader": input("Leader name: "),
    # continue for all fields…
}
  
  def create_request(self)->None:
    pass

  def fill_pdf(self, template_path:str, output_path:str, data:dict):
    pdf = PdfReader(template_path)
    for page in pdf.pages:
        annotations = page[ANNOT_KEY]
        if annotations:
            for annotation in annotations:
                key = annotation.get(ANNOT_FIELD_KEY)
                if key:
                    field_name = key[1:-1]  # remove parentheses
                    if field_name in data:
                        annotation.update(PdfDict(V='{}'.format(data[field_name])))
    PdfWriter(output_path, trailer=pdf).write()


  def upload_to_dropbox(self, local_path:str, dropbox_path:str, token):
    dbx = dropbox.Dropbox(token)
    with open(local_path, 'rb') as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
      
  def add_signature_field(self, input_pdf_path: str, output_pdf_path: str):
    # Read existing PDF
    with open(input_pdf_path, "rb") as pdf_file_handle:
        doc = PDF.loads(pdf_file_handle)

    page = doc.get_page(0)  # Signature on the first page
    # Add signature widget at a defined location
    signature_widget = SignatureWidget(
        Rectangle(x=400, y=100, width=150, height=50),  # Adjust position as needed
        field_name="Signature"
    )
    page.add_widget(signature_widget)

    # Save the updated PDF
    with open(output_pdf_path, "wb") as output_file_handle:
        PDF.dumps(output_file_handle, doc)
