# Render Fix + OTP Email Patch

This patch does **not** change your UI or categories. It only:
- adds `requirements.txt` so Render can build,
- exposes safe language URLs (`LANG_TR_URL`, `LANG_EN_URL`) to avoid Jinja `**kwargs` unpack error,
- adds email-based OTP reset endpoints.

## Apply
1) Copy all files to your repo.
2) In `server.py` right after `app = Flask(__name__)` add:

   from server_patch import register_patch
   register_patch(app)

3) Open `templates/base.html`, replace your two language anchors with the contents of `templates/base_lang_snippet.html`.
4) Commit & push. Ensure Render build command is `pip install -r requirements.txt`.

## Test
- POST /auth/request-reset  {"email":"you@example.com"}
- If SMTP not set, code is logged.
- POST /auth/verify-reset   {"email":"...","code":"1234"}
- POST /auth/do-reset       {"email":"...","code":"1234","new_password":"xxxxxx"}
