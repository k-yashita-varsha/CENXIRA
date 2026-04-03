import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.config import AppConfig

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.config = AppConfig()
        self.smtp_host = self.config.smtp_host
        self.smtp_port = self.config.smtp_port
        self.smtp_user = self.config.smtp_user
        self.smtp_pass = self.config.smtp_pass

    def send_approval_email(self, email_to: str, ohrid: str, temp_password: str):
        """Send an approval credential email to the newly approved user."""
        
        if not self.smtp_user or not self.smtp_pass:
            logger.warning("SMTP not properly configured. Cannot send email.")
            return

        subject = "Welcome to CENRIXA - Your Account is Activated!"

        html_content = f"""
        <html>
            <body>
                <h2 style='color:#2c3e50;'>Welcome to CENRIXA Training Portal</h2>
                <p>Hello,</p>
                <p>Your portal registration has been approved by the administrator!</p>
                <p>Here are your unique credentials to login:</p>
                <ul>
                    <li><b>OHRID / Username:</b> {ohrid}</li>
                    <li><b>Temporary Password:</b> {temp_password}</li>
                </ul>
                <p>Upon your first login via Keycloak, you will be strictly required to change your temporary password.</p>
                <p>Best Regards,<br>CENRIXA Training Team</p>
            </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = self.smtp_user
        msg['To'] = email_to

        mime_text = MIMEText(html_content, "html")
        msg.attach(mime_text)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, email_to, msg.as_string())
            logger.info(f"Approval email successfully sent to {email_to}")
        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {str(e)}")
            raise e
