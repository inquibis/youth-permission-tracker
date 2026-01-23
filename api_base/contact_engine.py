from typing import List, Dict
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()


class ContactEngine:
    base_site_url = os.getenv("BaseActivitySiteURL")
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')
    sms_sid = os.getenv("TWILLIO_MESSAGE_SID")

    def send_text(self, phone_number: List[str], message: str) -> Dict[str, bool]:
        # Implementation to send a text message
        pass

    def send_email(self, email_address: List[str], subject: str, body: str) -> Dict[str, bool]:
        # Implementation to send an email
        pass

    def send_sms(self, message:str, recipient:str)->None:
        client = Client(self.account_sid, self.auth_token)
        message = client.messages.create(
            messaging_service_sid=self.sms_sid,
            body=message,
            from_=recipient,
            to=recipient
        )
        print(f"Message sent to {recipient}: SID {message.sid}")
        return message.sid


    def send_whatsapp_message(self, recipient: str):
        client = Client(self.account_sid, self.auth_token)

        body = 'Click on this to approve: http://example.com'

        message = client.messages.create(
            body=body,
            from_=self.from_number,
            to=f'whatsapp:{recipient}'
        )
        print(f"WhatsApp message sent to {recipient}: SID {message.sid}")
        return message.sid


    def send_mms(self, recipient: str, media_url: str):
        client = Client(self.account_sid, self.auth_token)

        message_body = 'Click on this to approve: http://example.com'

        # Send the MMS
        message = client.messages.create(
            body=message_body,
            from_=self.from_number,
            to=recipient,
            media_url=[media_url]  # list of media URLs (e.g., images, GIFs)
        )
        print(f"MMS sent to {recipient}: SID {message.sid}")
        return message.sid