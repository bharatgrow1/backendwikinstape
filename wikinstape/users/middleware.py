from django.http import JsonResponse
from users.models import User

class AdminDomainMiddleware:

    ALLOWED_SYSTEM_DOMAINS = [
        "wikinapi.gssmart.in",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        host = request.get_host().split(":")[0].lower()

        if host in self.ALLOWED_SYSTEM_DOMAINS:
            return self.get_response(request)

        admin_user = None

        admin_user = User.objects.filter(
            role="admin",
            custom_domain__iexact=host
        ).first()

        if not admin_user:
            parts = host.split(".")
            if len(parts) == 3:
                subdomain = parts[0]

                admin_user = User.objects.filter(
                    role="admin",
                    subdomain=subdomain
                ).first()

        if not admin_user:
            return JsonResponse(
                {"error": "Invalid domain"},
                status=404
            )

        request.admin_user = admin_user

        return self.get_response(request)
