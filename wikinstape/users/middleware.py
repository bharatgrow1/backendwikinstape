from django.shortcuts import render
from users.models import User


class AdminDomainMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        host = request.get_host().split(":")[0].lower()

        # 🔹 Allow local development
        if host in ["127.0.0.1", "localhost"]:
            request.admin_user = User.objects.filter(role="superadmin").first()
            return self.get_response(request)

        # 🔹 Allow main API domain
        if host == "wikinapi.gssmart.in":
            request.admin_user = User.objects.filter(role="superadmin").first()
            return self.get_response(request)

        admin_user = None

        # 🔹 Check custom domain
        admin_user = User.objects.filter(
            role="admin",
            custom_domain__iexact=host
        ).first()

        # 🔹 Check subdomain
        if not admin_user:
            parts = host.split(".")
            if len(parts) > 2:
                subdomain = parts[0]
                admin_user = User.objects.filter(
                    role="admin",
                    subdomain__iexact=subdomain
                ).first()

        # 🔴 BLOCK if not found in DB
        if not admin_user:
            return render(
                request,
                "invalid_domain.html",
                status=404
            )

        request.admin_user = admin_user
        return self.get_response(request)
