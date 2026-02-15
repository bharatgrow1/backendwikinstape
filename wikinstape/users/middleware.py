from django.http import JsonResponse
from users.models import User

class AdminDomainMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        host = request.get_host().split(":")[0].lower()

        if host in ["127.0.0.1", "localhost"]:
            superadmin = User.objects.filter(role="superadmin").first()
            request.admin_user = superadmin
            return self.get_response(request)

        admin_user = None

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
                    subdomain=subdomain
                ).first()

        if host == "wikinapi.gssmart.in":
            superadmin = User.objects.filter(role="superadmin").first()
            request.admin_user = superadmin
            return self.get_response(request)


        if not admin_user:
            return JsonResponse(
                {"error": "Invalid domain"},
                status=404
            )

        request.admin_user = admin_user

        return self.get_response(request)
