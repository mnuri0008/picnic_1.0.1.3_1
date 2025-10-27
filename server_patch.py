
import os, random, time
from flask import request

def register_patch(app):
    @app.context_processor
    def inject_lang_links():
        try:
            ep = request.endpoint or 'home'
            view_args = dict(request.view_args or {})
            q = dict(request.args.to_dict(flat=True)); q.pop('lang', None)
            from flask import url_for
            def _u(lang):
                params = dict(view_args); params.update(q); params['lang'] = lang
                try:
                    return url_for(ep, **params)
                except Exception:
                    return url_for('home', lang=lang)
            return dict(LANG_TR_URL=_u('tr'), LANG_EN_URL=_u('en'))
        except Exception:
            return dict(LANG_TR_URL="#", LANG_EN_URL="#")

    OTP = {}
    def _send(to, sub, body):
        host=os.getenv("SMTP_HOST"); user=os.getenv("SMTP_USER"); pwd=os.getenv("SMTP_PASS")
        port=int(os.getenv("SMTP_PORT","587")); from_addr=os.getenv("EMAIL_FROM", user or "no-reply@example.com")
        if not (host and user and pwd):
            app.logger.warning("[SMTP DISABLED] to=%s subject=%s body=%s", to, sub, body); return False
        import smtplib
        from email.mime.text import MIMEText
        msg=MIMEText(body, _charset="utf-8"); msg["Subject"]=sub; msg["From"]=from_addr; msg["To"]=to
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(); s.login(user, pwd); s.sendmail(from_addr, [to], msg.as_string())
        return True

    from flask import jsonify

    @app.post("/auth/request-reset")
    def request_reset():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        if not email: return jsonify(ok=False, error="email_required"), 400
        code = f"{random.randint(0,9999):04d}"
        OTP[email] = dict(code=code, exp=time.time()+600)
        sent = _send(email, "Piknik Vakti Şifre Sıfırlama", f"Kodunuz: {code} (10 dk)")
        return jsonify(ok=True, sent=bool(sent))

    @app.post("/auth/verify-reset")
    def verify_reset():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip(); code=(data.get("code") or "").strip()
        rec = OTP.get(email)
        if not rec: return jsonify(ok=False, error="not_requested"), 400
        if time.time()>rec["exp"]: return jsonify(ok=False, error="expired"), 400
        if code!=rec["code"]: return jsonify(ok=False, error="invalid_code"), 400
        return jsonify(ok=True)

    @app.post("/auth/do-reset")
    def do_reset():
        data = request.get_json(silent=True) or {}
        email=(data.get("email") or "").strip(); code=(data.get("code") or "").strip()
        if not (OTP.get(email) and OTP[email]["code"]==code and time.time()<OTP[email]["exp"]):
            return jsonify(ok=False, error="verify_first"), 400
        # Integrate with your user store if available:
        try:
            updated = True
            if hasattr(app, "reset_password"):
                updated = bool(app.reset_password(email, data.get("new_password")))
        except Exception:
            app.logger.exception("Password update failed"); return jsonify(ok=False, error="update_failed"), 500
        OTP.pop(email, None)
        return jsonify(ok=updated)
