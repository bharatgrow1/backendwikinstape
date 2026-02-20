from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        token_session = validated_token.get("session_key")
        token_ip = validated_token.get("ip")
        token_agent = validated_token.get("agent")

        if not user.active_session_key:
            raise AuthenticationFailed("Session expired")

        if token_session != user.active_session_key:
            raise AuthenticationFailed("Session expired")

        if token_agent and user.last_user_agent and token_agent != user.last_user_agent:
            raise AuthenticationFailed("Device changed")

        return user