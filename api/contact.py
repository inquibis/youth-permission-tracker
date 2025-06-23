from sqlalchemy.orm import Session
from api.models import User
import smtplib
from email.message import EmailMessage
import os
from twilio.rest import Client

class Contact:

    # def contact_users(groups: list[str], db: Session):
    #     # Get users who are in at least one of the groups
    #     users = db.query(User).filter(
    #         User.groups.op('JSON_OVERLAPS')(groups)
    #     ).all()

    #     for user in users:
    #         print(f"Hello {user.first_name}!")

    def contact_users(self, groups: list[str], db: Session, activity_name: str):
        users = db.query(User).all()
        invited = [u for u in users if any(g in u.groups for g in groups)]

        for u in invited:
            print(f"Hello {u.first_name}!")

        self.email_guardians(invited, activity_name)
        self.sms_guardians(invited, activity_name)


    def email_guardians(self, users: list, activity_name: str):
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        for user in users:
            if not user.guardian_email:
                continue

            msg = EmailMessage()
            msg["Subject"] = f"New Activity: {activity_name}"
            msg["From"] = smtp_user
            msg["To"] = user.guardian_email
            msg.set_content(f"Hello {user.guardian_name},\n\n{user.first_name} has been invited to the activity: {activity_name}.\n\nThank you.")

            try:
                with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_user, smtp_pass)
                    smtp.send_message(msg)
            except Exception as e:
                print(f"Failed to email {user.guardian_email}: {e}")

    def sms_guardians(self, users: list, activity_name: str):
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_from = os.getenv("TWILIO_FROM")

        client = Client(twilio_sid, twilio_token)

        for user in users:
            if not user.guardian_cell:
                continue
            try:
                client.messages.create(
                    body=f"{user.first_name} is invited to: {activity_name}",
                    from_=twilio_from,
                    to=user.guardian_cell
                )
            except Exception as e:
                print(f"Failed to SMS {user.guardian_cell}: {e}")