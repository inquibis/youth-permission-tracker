from sqlalchemy.orm import Session
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
from twilio.rest import Client
import secrets
from datetime import datetime, timedelta
from jinja2 import Template
from models import PermissionToken, ActivityPermission, User

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

       # self.email_guardians(invited, activity_name)
        self.sms_guardians(invited, activity_name)


    # def email_guardians(self, users: list, activity_name: str):
    #     smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    #     smtp_port = int(os.getenv("SMTP_PORT", "587"))
    #     smtp_user = os.getenv("SMTP_USER")
    #     smtp_pass = os.getenv("SMTP_PASS")

    #     for user in users:
    #         if not user.guardian_email:
    #             continue

    #         msg = EmailMessage()
    #         msg["Subject"] = f"New Activity: {activity_name}"
    #         msg["From"] = smtp_user
    #         msg["To"] = user.guardian_email
    #         msg.set_content(f"Hello {user.guardian_name},\n\n{user.first_name} has been invited to the activity: {activity_name}.\n\nThank you.")

    #         try:
    #             with smtplib.SMTP(smtp_host, smtp_port) as smtp:
    #                 smtp.starttls()
    #                 smtp.login(smtp_user, smtp_pass)
    #                 smtp.send_message(msg)
    #         except Exception as e:
    #             print(f"Failed to email {user.guardian_email}: {e}")


    # def email_guardians(self, users, activity, db):
    #     for user in users:
    #         # Generate secure token
    #         token = self.generate_token()
    #         expires = datetime.utcnow() + timedelta(days=7)

    #         # Save token in DB
    #         db_token = PermissionToken(
    #             token=token,
    #             user_id=user.id,
    #             activity_id=activity.id,
    #             expires_at=expires
    #         )
    #         db.add(db_token)

    #         # Construct email body using a template
    #         html_template = Template("""
    #         <p>Dear {{ guardian_name or "Parent" }},</p>
    #         <p>Please review and sign the permission waiver for the upcoming activity:</p>
    #         <ul>
    #         <li><strong>Name:</strong> {{ activity_name }}</li>
    #         <li><strong>Dates:</strong> {{ date_start }} to {{ date_end }}</li>
    #         <li><strong>Description:</strong> {{ description }}</li>
    #         </ul>
    #         <p>Click the button below to sign the waiver:</p>
    #         <p><a href="{{ link }}" style="padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">Sign Permission Waiver</a></p>
    #         <p>This link expires in 7 days.</p>
    #         """)

    #         html = html_template.render(
    #             guardian_name=user.guardian_name,
    #             activity_name=activity.activity_name,
    #             date_start=activity.date_start.strftime("%B %d, %Y"),
    #             date_end=activity.date_end.strftime("%B %d, %Y"),
    #             description=activity.description,
    #             link=f"https://yourdomain.com/parental-permission.html?token={token}"
    #         )

    #         self.send_email(to=user.guardian_email, subject="Permission Request for Activity", html=html)

    #     db.commit()

    def send_admin_confirmation(self, user_name, guardian_name, activity_name, pdf_path):
        msg = MIMEMultipart()
        msg['Subject'] = f"Signed Waiver: {user_name} - {activity_name}"
        msg['From'] = "noreply@notic.com"
        msg['To'] = "admin@notic.com"

        body = f"""
        Guardian {guardian_name} has signed the waiver for {user_name} to attend:
        
        {activity_name}

        The signed PDF waiver is attached.
        """
        msg.attach(MIMEText(body, 'plain'))

        # Attach the PDF
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(part)

        with smtplib.SMTP('smtp.yourserver.com') as server:
            server.login("your_username", "your_password")
            server.send_message(msg)


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


    # def create_parent_token(self):
    #     pass
#         Guardians receive an email with:

# Activity name, dates, description

# A secure, unique waiver link like:
# https://yourdomain.com/parental-permission.html?token=abc123

# That token:

# Is tied to a specific activity_id and user_id

# Expires after a set time (e.g. 7 days)

# Allows the guardian to open the form and submit permission