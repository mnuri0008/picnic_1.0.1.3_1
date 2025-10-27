
# server_patch_fix.py
from datetime import datetime, timedelta
import os, random, smtplib, ssl
from email.mime.text import MIMEText

def _inject_lang_urls(app):
    @app.context_processor
    def _inject():
        try:
            from flask import request, url_for
            endpoint = request.endpoint or "home"
            args = {}
            if getattr(request, "view_args", None):
                args.update(request.view_args)
            if getattr(request, "args", None):
                args.update(request.args.to_dict(flat=True))
            args.pop("lang", None)
            tr = url_for(endpoint, **args, lang="tr")
            en = url_for(endpoint, **args, lang="en")
            return {"LANG_TR_URL": tr, "LANG_EN_URL": en}
        except Exception:
            return {"LANG_TR_URL": "#", "LANG_EN_URL": "#"}

def _maybe_add_sw_route(app):
    try:
        from flask import Response
        static_path = app.static_folder or "static"
        sw_fs = os.path.join(static_path, "service-worker.js")
        if not os.path.exists(sw_fs):
            @app.route("/service-worker.js")
            def _sw():
                return Response("// noop service worker", mimetype="application/javascript")
    except Exception:
        pass

_OTP_STORE = {}

def _send_email_smtp(app, to_email: str, subject: str, body_text: str) -> bool:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM", user or "no-reply@example.com")

    if not host or not user or not pwd:
        app.logger.warning("[SMTP not set] Would send mail to %s :: %s\n%s", to_email, subject, body_text)
        return False

    msg = MIMEText(body_text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(user, pwd)
        server.send_message(msg)
    return True

def _enable_otp_routes(app):
    from flask import request, jsonify

    @app.post("/auth/request-reset")
    def request_reset():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        if not email:
            return jsonify({"ok": False, "error": "email_required"}), 400

        from random import randint
        code = f"{randint(0, 9999):04d}"
        expiry = datetime.utcnow() + timedelta(minutes=10)
        _OTP_STORE[email] = {"code": code, "expiry": expiry}

        body = f"Şifre sıfırlama kodunuz: {code}\nKod 10 dakika boyunca geçerlidir."
        sent = _send_email_smtp(app, email, "Şifre Sıfırlama Kodu", body)
        return jsonify({"ok": True, "sent": bool(sent), "hint": "log" if not sent else ""})

    @app.post("/auth/verify-reset")
    def verify_reset():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        code  = (data.get("code") or "").strip()
        rec = _OTP_STORE.get(email)
        if not rec or rec["code"] != code:
            return jsonify({"ok": False, "error": "invalid_code"}), 400
        if datetime.utcnow() > rec["expiry"]:
            return jsonify({"ok": False, "error": "expired"}), 400
        return jsonify({"ok": True})

    @app.post("/auth/do-reset")
    def do_reset():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        code  = (data.get("code") or "").strip()
        newpw = (data.get("new_password") or "").strip()
        if not newpw:
            return jsonify({"ok": False, "error": "password_required"}), 400

        rec = _OTP_STORE.get(email)
        if not rec or rec["code"] != code:
            return jsonify({"ok": False, "error": "invalid_code"}), 400
        if datetime.utcnow() > rec["expiry"]:
            return jsonify({"ok": False, "error": "expired"}), 400

        cb = app.config.get("RESET_CALLBACK")
        if callable(cb):
            try:
                cb(email, newpw)
            except Exception as e:
                app.logger.exception("RESET_CALLBACK failed: %s", e)
                return jsonify({"ok": False, "error": "callback_failed"}), 500

        _OTP_STORE.pop(email, None)
        return jsonify({"ok": True})

def register_patch(app, *, enable_otp=True):
    if app is None:
        raise RuntimeError("register_patch(app): app is None")
    _inject_lang_urls(app)
    _maybe_add_sw_route(app)
    if enable_otp:
        _enable_otp_routes(app)
    app.logger.info("server_patch_fix registered (OTP=%s)", enable_otp)
