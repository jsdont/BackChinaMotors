import os, json, requests, xml.etree.ElementTree as ET
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from requests.exceptions import RequestException, Timeout

# ---------- Telegram ----------
@csrf_exempt
@require_POST
def telegram_hook(request):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return JsonResponse({"ok": False, "where": "env", "error": "Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID"}, status=200)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
        text = (payload.get("text") or "").strip()
        if not text:
            return JsonResponse({"ok": False, "where": "payload", "error": "Empty text"}, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "where": "json", "error": str(e)}, status=200)

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        ct = r.headers.get("content-type", "")
        data = r.json() if "application/json" in ct else {"raw": r.text}
        ok = bool(data.get("ok", r.ok))
        desc = data.get("description") or ("" if ok else r.text)
        return JsonResponse({"ok": ok, "http": r.status_code, "description": desc}, status=200)
    except Timeout as e:
        return JsonResponse({"ok": False, "where": "network", "error": "Telegram timeout", "detail": str(e)}, status=200)
    except RequestException as e:
        return JsonResponse({"ok": False, "where": "network", "error": str(e)}, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "where": "server", "error": str(e)}, status=200)

# ---------- USD rate (server-side fetch to bypass CORS) ----------
def usd_rate(request):
    """
    Возвращает актуальный курс USD→KZT с сайта Нацбанка РК (RSS).
    Формат ответа: {"ok": true, "rate": 477.65}
    """
    try:
        resp = requests.get("https://nationalbank.kz/rss/rates_all.xml", timeout=10)
        resp.raise_for_status()
        # RSS XML -> ищем item с title=USD, значение в <description>
        root = ET.fromstring(resp.text)
        usd = None
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            if title.strip().upper() == "USD":
                desc = (item.findtext("description") or "").strip().replace(",", ".")
                # описание содержит число, например "477.65"
                try:
                    usd = float(desc)
                except ValueError:
                    usd = None
                break
        if usd:
            return JsonResponse({"ok": True, "rate": usd}, status=200)
        return JsonResponse({"ok": False, "error": "USD not found in feed"}, status=502)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)
