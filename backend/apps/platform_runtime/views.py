from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .webhooks import receive_webhook


@csrf_exempt
@require_POST
def inbound_webhook(request, provider: str):
    try:
        event, duplicate = receive_webhook(
            provider=provider,
            body=request.body,
            signature=request.headers.get("X-Webhook-Signature", ""),
            headers=request.headers,
        )
    except LookupError:
        return JsonResponse({"detail": "unknown webhook provider"}, status=404)
    except PermissionError:
        return JsonResponse({"detail": "invalid webhook signature"}, status=401)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    return JsonResponse({"accepted": True, "duplicate": duplicate, "event_id": str(event.id)}, status=202)
