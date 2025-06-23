from unittest.mock import patch, MagicMock
from api.email import send_admin_confirmation

@patch("api.email.smtplib.SMTP")
def test_send_admin_confirmation(mock_smtp):
    instance = mock_smtp.return_value.__enter__.return_value
    instance.send_message = MagicMock()

    # Call function
    send_admin_confirmation(
        user_name="Test User",
        guardian_name="Guardian",
        activity_name="Campout",
        pdf_path="tests/assets/sample.pdf"
    )

    instance.send_message.assert_called_once()
