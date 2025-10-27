import os
from flask import Flask, render_template, request, jsonify, abort, send_from_directory
from datetime import datetime, timedelta
import threading, itertools

from server_patch import register_patch
register_patch(app)  # OTP+lang minimal patch
app = Flask(__name__, static_folder='static', template_folder='templates')

# In-memory “DB”
ROOMS = {}  # code -> {"owner": str, "date": str(ISO minutes), "items":[{...}]}
IDGEN = itertools.count(1)
LOCK = threading.Lock()

def mask(code: str) -> str:  # 28** gibi göstermelik
    code = str(code or "")
    return f"{code[:2]}**" if len(code) >= 2 else (code + "*")

def now_iso() -> str:
    # ISO benzeri, dakika hassasiyetinde (YYYY-MM-DDTHH:MM)
    return datetime.utcnow().isoformat(timespec="minutes")

def _as_dt(s: str):
    if not s:
        return None
    try:
        # RFC3339 'Z' son ekini tolere et
        return datetime.fromisoformat(s.replace('Z', '')).replace(second=0, microsecond=0)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except Exception:
            return None

# ---------- STATIC PWA ENDPOINTS (kökten servis) ----------
@app.route('/manifest.json')
def manifest():
    return send_from_directory(app.static_folder, 'manifest.json',
                               mimetype='application/manifest+json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(app.static_folder, 'service-worker.js',
                               mimetype='application/javascript')

# ---------- SAYFALAR ----------
@app.route("/")
def home():
    lang = request.args.get("lang", "tr")

    # 10 günü geçen (piknik tarihinden itibaren) odaları temizle
    now = datetime.utcnow()
    with LOCK:
        to_delete = []
        for code, r in list(ROOMS.items()):
            d = _as_dt(r.get("date") or "")
            if d and now > d + timedelta(days=10):
                to_delete.append(code)
        for c in to_delete:
            ROOMS.pop(c, None)

        # Liste için görüntü verisi
        rooms = []
        for code, r in ROOMS.items():
            d_str = r.get("date") or ""
            d_dt = _as_dt(d_str) or datetime.min
            rooms.append({
                "code": code,
                "date": d_str,
                "items": len(r.get("items", [])),
                "mask": mask(code),
                "_sort": d_dt
            })

    rooms.sort(key=lambda x: x["_sort"], reverse=True)
    for r in rooms:
        r.pop("_sort", None)

    return render_template("index.html", rooms=rooms, lang=lang)

@app.route("/room/<code>")
def room(code):
    username = request.args.get("username", "guest")
    lang = request.args.get("lang", "tr")
    # “Gör” linkinden gelindiyse sadece görüntüleme modu
    view = request.args.get("view") == "1"
    return render_template("room.html", code=code, username=username, lang=lang, view=view)

# ---------- API ----------
@app.post("/api/room")
def api_create_room():
    data = request.get_json(force=True) or {}
    code = str(data.get("code", "")).strip()
    if not code:
        abort(400, description="code required")
    owner = (data.get("owner") or "").strip()
    date  = (data.get("date") or now_iso())[:16]  # dakika hassasiyeti
    with LOCK:
        ROOMS.setdefault(code, {"owner": owner, "date": date, "items": []})
    return "", 201

@app.get("/api/rooms")
def api_rooms():
    with LOCK:
        out = []
        for c, r in ROOMS.items():
            out.append({
                "code": c,
                "mask": mask(c),
                "date": r.get("date"),
                "items": len(r.get("items", []))
            })
    return jsonify(out)

@app.get("/api/room/<code>")
def api_room(code):
    with LOCK:
        r = ROOMS.setdefault(str(code), {"owner": "", "date": now_iso(), "items": []})
        return jsonify(r)

@app.post("/api/room/<code>/items")
def api_add_item(code):
    data = request.get_json(force=True) or {}
    name   = (data.get("name") or "").strip()
    unit   = (data.get("unit") or "").strip()
    amount = data.get("amount", 0)
    try:
        amount = float(amount)
    except Exception:
        abort(400, description="amount must be a number")
    cat    = (data.get("cat") or "Diğer").strip()
    user   = (data.get("user") or "").strip()

    if not name or not unit or not user:
        abort(400, description="name, unit and user are required")

    with LOCK:
        r = ROOMS.setdefault(str(code), {"owner": "", "date": now_iso(), "items": []})
        item = {
            "id": next(IDGEN),
            "name": name,
            "unit": unit,
            "amount": amount,
            "cat": cat,
            "user": user,
            "state": "needed"
        }
        r["items"].append(item)
    return "", 201

@app.patch("/api/room/<code>/items/<int:item_id>")
def api_patch_item(code, item_id):
    data = request.get_json(force=True) or {}
    user  = data.get("user", "")
    state = data.get("state", "needed")
    with LOCK:
        r = ROOMS.get(str(code))
        if not r:
            abort(404)
        owner = r.get("owner", "")
        for it in r.get("items", []):
            if it["id"] == item_id:
                if user != it["user"] and user != owner:
                    abort(403)
                it["state"] = state
                return "", 204
    abort(404)

@app.delete("/api/room/<code>/items/<int:item_id>")
def api_del_item(code, item_id):
    user = request.args.get("user", "")
    with LOCK:
        r = ROOMS.get(str(code))
        if not r:
            abort(404)
        owner = r.get("owner", "")
        for it in list(r.get("items", [])):
            if it["id"] == item_id:
                if user != it["user"] and user != owner:
                    abort(403)
                r["items"].remove(it)
                return "", 204
    abort(404)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)