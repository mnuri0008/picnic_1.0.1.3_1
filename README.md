# Picnic Vakti — LANG + SMTP Patch (Drop‑in)
1) `helpers_patch.apply_helpers(app)`'i `app = Flask(__name__)` oluştuktan sonra çağırın.
2) Bu paketteki `templates/base.html` dil linklerini güvenli hale getirir. İsterseniz sadece:
   `<a href="{{ lang_url('tr') }}">TR</a>  <a href="{{ lang_url('en') }}">EN</a>` kullanın.
3) `static/service-worker.js` 404'ü giderir.
4) Render ortam değişkenlerini `.env.example`'a göre ekleyin.

**ÖNEMLİ:** `register_patch(app)` gibi çağrıları `app` oluşturulmadan önce kullanmayın.
