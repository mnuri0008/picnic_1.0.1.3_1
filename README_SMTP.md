# SMTP Setup (Gmail example)

Create a Google App Password (2FA required). Then set these Render Environment Variables:

SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = your@gmail.com
SMTP_PASS = <app password>
EMAIL_FROM = your@gmail.com

If SMTP is missing, the OTP code is written to server logs instead of sending.
