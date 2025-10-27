# server_patch.py
from datetime import datetime, timedelta
import os, smtplib, ssl, random, string
from email.message import EmailMessage
from flask import request, current_app as app, jsonify, url_for

_OTPS = {}

def _gen_code(n=4):
    import secrets, string as _s
    return "".join(secrets.choice(_s.digits) for _ in range(n))

def _smtp_ready():
    need = ["SMTP_HOST","SMTP_PORT","SMTP_USER","SMTP_PASS","EMAIL_FROM"]
    return all(app.config.get(k) or os.getenv(k) for k in need)

def _smtp_get(k, default=None):
    return app.config.get(k) or os.getenv(k, default)

def _send_email(to_email, subject, body):
    if not _smtp_ready():
        app.logger.warning("[OTP] SMTP not configured; would send to %s: %s", to_email, body)
        return False
    host = _smtp_get("SMTP_HOST")
    port = int(_smtp_get("SMTP_PORT","587"))
    user = _smtp_get("SMTP_USER")
    pwd  = _smtp_get("SMTP_PASS")
    from_addr = _smtp_get("EMAIL_FROM", user)
    context = ssl.create_default_context()
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=20) as s:
        s.starttls(context=context)
        s.login(user, pwd)
        s.send_message(msg)
    return True

def _build_lang_url(lang_value:str):
    view_params = request.view_args or {}
    q = request.args.to_dict(flat=True)
    q.pop("lang", None)
    q["lang"] = lang_value
    return url_for(request.endpoint, **view_params, **q)

def register_patch(flask_app):
    @flask_app.context_processor
    def _inject_lang_urls():
        try:
            return dict(
                LANG_TR_URL=_build_lang_url("tr"),
                LANG_EN_URL=_build_lang_url("en"),
            )
        except Exception:
            return dict(LANG_TR_URL="#", LANG_EN_URL="#")

    @flask_app.post("/auth/request-reset")
    def request_reset():
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip()
        if not email:
            return jsonify(ok=False, error="email_required"), 400
        code = _gen_code(4)
        _OTPS[email] = {"code": code, "exp": datetime.utcnow() + timedelta(minutes=10)}
        sent = _send_email(email, "Piknik Vakti — Şifre Sıfırlama Kodu", f"Kodunuz: {code} (10 dk geçerli)")
        return jsonify(ok=True, delivered=bool(sent))

    @flask_app.post("/auth/verify-reset")
    def verify_reset():
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip()
        code  = (data.get("code") or "").strip()
        rec = _OTPS.get(email)
        if not rec:
            return jsonify(ok=False, error="no_request"), 404
        if datetime.utcnow() > rec["exp"]:
            return jsonify(ok=False, error="expired"), 410
        if code != rec["code"]:
            return jsonify(ok=False, error="invalid_code"), 400
        return jsonify(ok=True)

    @flask_app.post("/auth/do-reset")
    def do_reset():
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip()
        code  = (data.get("code") or "").strip()
        newpw = (data.get("new_password") or "").strip()
        rec = _OTPS.get(email)
        if not rec:
            return jsonify(ok=False, error="no_request"), 404
        if datetime.utcnow() > rec["exp"]:
            return jsonify(ok=False, error="expired"), 410
        if code != rec["code"]:
            return jsonify(ok=False, error="invalid_code"), 400
        if len(newpw) < 6:
            return jsonify(ok=False, error="weak_password"), 400

        cb = flask_app.config.get("RESET_CALLBACK")
        if callable(cb):
            try:
                cb(email, newpw)
            except Exception as e:
                return jsonify(ok=False, error="callback_failed", detail=str(e)), 500

        _OTPS.pop(email, None)
        return jsonify(ok=True)
