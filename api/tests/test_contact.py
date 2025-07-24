from contact import Contact
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_contact_users_filters_correctly():
    db = MagicMock()
    db.query().all.return_value = [
        MagicMock(groups='["Group1"]', first_name="Alice"),
        MagicMock(groups='["OtherGroup"]', first_name="Bob")
    ]
    c = Contact()
    c.sms_guardians = MagicMock()
    c.contact_users(["Group1"], db, "Test Activity")
    c.sms_guardians.assert_called_once()

@patch("smtplib.SMTP")
def test_send_admin_confirmation(mock_smtp):
    c = Contact()
    c.send_admin_confirmation("John", "Doe", "Camp", "/mnt/data/fake.pdf")
    mock_smtp.return_value.send_message.assert_called()