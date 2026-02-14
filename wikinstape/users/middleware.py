from users.models import User

class AdminDomainMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        host = request.get_host().split(":")[0].lower()

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

        request.admin_user = admin_user

        return self.get_response(request)
