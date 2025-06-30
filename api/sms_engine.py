from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

class SMS_Engine:
    base_site_url = os.getenv("BaseActivitySiteURL")
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')


    def send_sms(self, message:str, recipient:str)->None:
        client = Client(self.account_sid, self.auth_token)
        message = client.messages.create(
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


    def create_message_parent_approval(self, activity_name:str, activity_date:str, child_name:str, activity_id:str, parent_token:str)->str:
        msg = f"""This is to request permission for {child_name} to attend an activity ({activity_name}) for <groups>.  This activity <description> will be held on {activity_date}.

        Give permission
        Deny permission
        If you want to give permission but do not need to update your child’s medical/health information since last time you can simply click here Giver Permission and skip the medical form.
        """
        return msg
    
    def create_message_supervisor_approval(self, activity_name:str, activity_date:str, activity_id:str, super_token:str, activity_desc:str, unit_name:str="Brookhurst Ward")->str:
        msg = f"""This is a request from {unit_name} for you to approve their activity, {activity_name}, set for {activity_date}.  {activity_desc}.

        Give permission
        Deny permission
        More information http://{self.base_site_url}/activity-info.html?id={activity_id}
        """
        return msg