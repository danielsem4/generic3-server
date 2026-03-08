from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    """
    Authenticate the user by reading the 'access' cookie directly.
    No 'Bearer' prefix, no header parsing.
    """
    def authenticate(self, request):
        raw_token = request.COOKIES.get("access")
        if raw_token is None:
            print("No access cookie found")
            return None            # no cookie -> let other authenticators run

        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception:           # invalid / expired token
            print("Invalid or expired access token")
            return None

        return self.get_user(validated_token), validated_token