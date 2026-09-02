import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        resend.api_key = getattr(settings, 'RESEND_API_KEY', '')

    def send_messages(self, email_messages):
        sent = 0
        for msg in email_messages:
            try:
                resend.Emails.send({
                    "from": msg.from_email,
                    "to": msg.to,
                    "subject": msg.subject,
                    "html": msg.body if '<' in msg.body else None,
                    "text": msg.body if '<' not in msg.body else None,
                })
                sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise e
        return sent
