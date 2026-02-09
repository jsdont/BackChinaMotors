import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def tawk_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 🔍 DEBUG: сначала просто логируем
    print("TAWK WEBHOOK:", json.dumps(payload, indent=2))

    # TODO: позже тут можно:
    # - сохранить лид в БД
    # - отправить в Telegram
    # - создать заявку

    return JsonResponse({"status": "ok"})
