from django.urls import path
from authentication import views

urlpatterns = [
    # Authentication API endpoints
    path('api/v1/auth/sessions/', views.SessionView.as_view(), name='sessions'),
    path('api/v1/auth/tokens/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),
    path('api/v1/auth/2fa/', views.TwoFactorAuthView.as_view(), name='two-factor-auth'),
    path('api/v1/auth/2fa/verify/', views.TwoFactorVerifyView.as_view(), name='two-factor-verify'),
    path('api/v1/auth/password/', views.PasswordView.as_view(), name='password'),
    path('api/v1/auth/users/<int:user_id>/qr-code/', views.UserQRCodeView.as_view(), name='user-qr-code'),
]
