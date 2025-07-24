from sms_engine import SMS_Engine
from unittest.mock import patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@patch("sms_engine.Client")
def test_send_sms(mock_client):
    sms = SMS_Engine()
    sms.send_sms("Hello", "+1000000000")
    mock_client.return_value.messages.create.assert_called()

def test_create_message_parent_approval():
    sms = SMS_Engine()
    msg = sms.create_message_parent_approval("Camp", "2024-08-01", "Timmy", "123", "tok")
    assert "Camp" in msg and "Timmy" in msg