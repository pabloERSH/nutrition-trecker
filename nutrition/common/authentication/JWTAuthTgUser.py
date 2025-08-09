from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError


class JWTAuthTgUser(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            prefix, token = auth_header.split()
            if prefix.lower() != "bearer":
                raise AuthenticationFailed("Invalid token prefix")
        except ValueError:
            raise AuthenticationFailed("Invalid Authorization header")

        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
            telegram_id = payload.get("telegram_id")
            if not telegram_id or not isinstance(telegram_id, int):
                raise AuthenticationFailed("Invalid telegram_id in token")

            return (telegram_id, token)
        except ExpiredSignatureError:
            raise AuthenticationFailed("Token expired")
        except InvalidTokenError:
            raise AuthenticationFailed("Invalid token")
