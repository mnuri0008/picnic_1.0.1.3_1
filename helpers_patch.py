# helpers_patch.py
from flask import request, url_for, g

def apply_helpers(app):
    @app.context_processor
    def _lang_url_util():
        def lang_url(lang_code):
            endpoint = (request.endpoint or "home")
            params = {}
            if request.view_args:
                params.update(request.view_args)
            if request.args:
                params.update(request.args.to_dict(flat=True))
            params["lang"] = lang_code
            try:
                return url_for(endpoint, **params)
            except Exception:
                return url_for("home", lang=lang_code)
        return dict(lang_url=lang_url)

    @app.before_request
    def _smtp_flag():
        smtp_cfg = app.config.get("SMTP", {})
        g.smtp_ready = bool(smtp_cfg.get("HOST") and smtp_cfg.get("USER") and smtp_cfg.get("PASS"))

    @app.route("/service-worker.js")
    def service_worker():
        return app.send_static_file("service-worker.js")
