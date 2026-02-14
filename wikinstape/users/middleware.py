from django.http import JsonResponse
from users.models import User

class AdminDomainMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        forwarded_host = request.META.get("HTTP_X_FORWARDED_HOST")
        host = forwarded_host if forwarded_host else request.get_host()
        host = host.split(":")[0].lower()

        if host == "wikinapi.gssmart.in":
            return self.get_response(request)

        admin_user = User.objects.filter(
            role="admin",
            custom_domain__iexact=host
        ).first()

        if not admin_user:
            parts = host.split(".")
            if len(parts) > 2:
                subdomain = parts[0]
                admin_user = User.objects.filter(
                    role="admin",
                    subdomain__iexact=subdomain
                ).first()

        if not admin_user:
            return JsonResponse({"error": "Invalid domain"}, status=404)

        request.admin_user = admin_user

        return self.get_response(request)
