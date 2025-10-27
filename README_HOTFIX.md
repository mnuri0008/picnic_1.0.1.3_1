
# Render Hotfix: app is not defined & Jinja **kwargs

This patch fixes two issues without touching your original UI/categories:

1) server:app boot crash — register_patch(app) was called before app existed.
2) Jinja invalid syntax — url_for(..., **kwargs) is not valid in Jinja templates.

## Apply (minimal)

1. Ensure your server.py creates the Flask app first:

    from flask import Flask
    app = Flask(__name__)

2. After the app is created (e.g., bottom of server.py):

    try:
        from server_patch_fix import register_patch
        register_patch(app)  # registers LANG_* URLs, /service-worker.js, and OTP endpoints
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Patch load failed: %s", e)

3. In templates/base.html replace language links with:

    {% include 'base_lang_snippet.html' %}

4. Commit the requirements.txt at repo root.

## SMTP (for real emails)

Set env vars in Render (or .env locally):

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=<app-password>
EMAIL_FROM=your@gmail.com

If SMTP is not set, OTP codes will be logged (test mode).

## OTP Endpoints

POST /auth/request-reset   body: {"email":"user@example.com"}
POST /auth/verify-reset    body: {"email":"...", "code":"1234"}
POST /auth/do-reset        body: {"email":"...", "code":"1234", "new_password":"..."}

Hook into your user DB with:

def my_reset(email, new_password):
    pass  # update DB here
app.config["RESET_CALLBACK"] = my_reset
