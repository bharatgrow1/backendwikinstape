from django.shortcuts import render
from users.models import User

class AdminDomainMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # 🔥 IMPORTANT CHANGE
        client_domain = request.headers.get("X-Client-Domain", "").lower().strip()

        if client_domain:
            host = client_domain
        else:
            host = request.get_host().split(":")[0].lower()

        # Localhost allow
        if host in ["127.0.0.1", "localhost"]:
            request.admin_user = User.objects.filter(role="superadmin").first()
            return self.get_response(request)

        # Main backend domain
        if host == "wikinapi.gssmart.in":
            request.admin_user = User.objects.filter(role="superadmin").first()
            return self.get_response(request)

        admin_user = None

        # 🔥 Custom domain match
        admin_user = User.objects.filter(
            role="admin",
            custom_domain__iexact=host
        ).first()

        # 🔥 Subdomain match
        if not admin_user:
            parts = host.split(".")
            if len(parts) > 2:
                subdomain = parts[0]
                admin_user = User.objects.filter(
                    role="admin",
                    subdomain__iexact=subdomain
                ).first()

        if not admin_user:
            return render(
                request,
                "invalid_domain.html",
                status=404
            )

        request.admin_user = admin_user
        return self.get_response(request)
