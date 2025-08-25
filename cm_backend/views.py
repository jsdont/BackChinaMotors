import os, json, requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from requests.exceptions import RequestException, Timeout

@csrf_exempt
@require_POST
def telegram_hook(request):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return JsonResponse({"ok": False, "where": "env", "error": "Missing env TELEGRAM_TOKEN or TELEGRAM_CHAT_ID"}, status=200)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except Exception as e:
        return JsonResponse({"ok": False, "where": "json", "error": str(e)}, status=200)

    text = (payload.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "where": "payload", "error": "Empty text"}, status=200)

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        ct = r.headers.get("content-type", "")
        data = r.json() if "application/json" in ct else {"raw": r.text}
        return JsonResponse({"http": r.status_code, **data}, status=200)
    except Timeout as e:
        return JsonResponse({"ok": False, "where": "network", "error": "Telegram timeout", "detail": str(e)}, status=200)
    except RequestException as e:
        return JsonResponse({"ok": False, "where": "network", "error": str(e)}, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "where": "server", "error": str(e)}, status=200)
