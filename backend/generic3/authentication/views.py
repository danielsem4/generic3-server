from datetime import timedelta
import logging

from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils import timezone
from django.contrib.auth import authenticate

from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from modules.models import ClinicModules, Modules
from clinics.models import Clinic
from generic3.utils import get_clinic_id_for_user, send2FA_code, setup_totp, verify_code
from users.models import User
from users.serializers import UserSerializer

logger = logging.getLogger(__name__)

# RESTful Authentication API Views

class SessionView(APIView):
    """
    POST: Create a new session (login)
    DELETE: Destroy session (logout)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Login - Create session"""
        default_url = "https://generic2dev.hitheal.org.il"
        site = f"http://{request.get_host()}"

        email = request.data.get('email')
        password = request.data.get('password')
        logger.info(f"Login attempt for email: {email} at site: {site}")
        
        if not email or not password:
            return Response(
                {"detail": "Email and password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use Django's built-in authentication
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"detail": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # create JWT pair
        tokens = RefreshToken.for_user(user)

        # Get user data
        serializer = UserSerializer(instance=user)
        clinic_id = get_clinic_id_for_user(user , site=site)
        clinic_data = None
        clinic_image = f'{site}/static/images/default.png'
        modules = []

        logger.info(f"User {user.email} login attempt - Clinic: {clinic_id}")
        
        if not clinic_id and not user.is_staff:
            return Response(
                {"detail": "No clinics found for this user"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user.is_staff:
            # Get clinic data more efficiently
            try:
                clinic = Clinic.objects.get(id=clinic_id)
                clinic_data = {
                    'id': clinic.id,
                    'url': clinic.clinic_url,
                    'name': clinic.clinic_name
                }
            except Clinic.DoesNotExist:
                return Response(
                    {"detail": f"Clinic not found with id {clinic_id} and site: {site}"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get modules for the clinic
            clinic_modules = ClinicModules.objects.filter(
                clinic_id=clinic_id
            ).values_list('module_id', flat=True)
            
            if clinic_modules:
                modules = list(Modules.objects.filter(
                    id__in=clinic_modules
                ).values_list('module_name', 'id'))
                
            clinic_name = clinic_data['name']
            try:
                # Check if static file exists
                static_file_path = f'images/{clinic_name}.png'
                file_exists = finders.find(static_file_path) is not None
            except Exception as e:
                logger.error(f"Error checking file existence: {e}")
                file_exists = False
            
            if file_exists:
                clinic_image = f'{site}/static/images/{clinic_name}.png'

        data = serializer.data
        user_data = {
            'clinicId': clinic_id if clinic_id else 0,
            'clinicName': clinic_data['name'] if clinic_data else "GenericWeb",
            'clinic_image': clinic_image,
            'modules': [{'name': module[0], 'id': module[1]} for module in modules] if modules else [],
            'status': 'Success',
            'server_url': clinic_data['url'] if clinic_data else default_url,
        }
        data.update(user_data)
        data.update({
            'access_token': str(tokens.access_token),
            'refresh_token': str(tokens)
        })

        logger.info(f"User {user.email} logged in successfully with clinic {user_data['clinicName']}")
        
        response = Response({"user": data}, status=status.HTTP_201_CREATED)
        
        # -- set cookies --
        is_secure = not settings.DEBUG  # Only use secure cookies in production
        response.set_cookie(
            "access",
            str(tokens.access_token),
            max_age=60 * 60,          # 60 min
            httponly=True,
            secure=is_secure,
            samesite="Lax" if settings.DEBUG else "None",
            path="/",
        )
        response.set_cookie(
            "refresh",
            str(tokens),
            max_age=24 * 60 * 60,     # 1 day
            httponly=True,
            secure=is_secure,
            samesite="Lax" if settings.DEBUG else "None",
            path="/auth/refresh/",    # only sent to the refresh endpoint
        )
        return response
    
    def delete(self, request):
        """Logout - Destroy session"""
        if request.user.is_authenticated:
            logger.info(f"User {request.user.email} logging out")
            # Delete the user's token to log them out
            try:
                token = Token.objects.get(user=request.user)
                token.delete()
            except Token.DoesNotExist:
                pass
            
            response = Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            # Clear cookies
            response.delete_cookie('access')
            response.delete_cookie('refresh')
            return response
        else:
            return Response(
                {'message': 'User was not logged in'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class TokenRefreshView(APIView):
    """
    POST: Refresh access token
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Refresh access token"""
        refresh = request.COOKIES.get("refresh")
        if refresh is None:
            return Response(
                {"detail": "No refresh cookie"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            token = RefreshToken(refresh)
            new_access = token.access_token
        except Exception:
            return Response(
                {"detail": "Invalid refresh token"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        response = Response({"detail": "Token refreshed"})
        response.set_cookie(
            "access",      
            str(new_access),
            max_age=60 * 60,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax" if settings.DEBUG else "None",
            path="/",
        ) 
        return response


class TwoFactorAuthView(APIView):
    """
    POST: Request 2FA code
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Request 2FA code"""
        email = request.data.get('email')
        password = request.data.get('password')
        send_method = request.data.get('send_method', 'email').lower()

        if not email:
            return Response(
                {'error': 'Email is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email , password=password)
        if user is None:
            return Response(
                {'error': 'Invalid email'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Store user session temporarily for 2FA verification
        request.session['pending_2fa_user_id'] = user.id
        request.session['pending_2fa_timestamp'] = timezone.now().isoformat()
        request.session.save()  # Explicitly save the session
        
        logger.info(f"2FA session created for user {user.id} - Session key: {request.session.session_key}")

        response = send2FA_code(user, send_method)
        if response.status_code != 200:
            return response

        return Response({
            'message': 'Credentials verified. Please enter 2FA code.',
            'requires_2fa': True,
            'session_key': request.session.session_key  # Return session key for debugging
        }, status=status.HTTP_200_OK)


class TwoFactorVerifyView(APIView):
    """
    POST: Verify 2FA code
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Verify 2FA code and complete login"""
        code = request.data.get('code')
        code_type = request.data.get('code_type')
        user_id = request.session.get('pending_2fa_user_id')
        
        logger.info(f"2FA verify attempt - Session key: {request.session.session_key}, user_id from session: {user_id}, code: {code}, code_type: {code_type}")
        
        if not code or not user_id:
            error_msg = 'Invalid request'
            if not user_id:
                error_msg = 'No pending 2FA session found. Please request a 2FA code first.'
            elif not code:
                error_msg = 'Verification code is required'
            
            return Response(
                {'error': error_msg}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if session hasn't expired (5 minutes)
        timestamp_str = request.session.get('pending_2fa_timestamp')
        if timestamp_str:
            from datetime import datetime
            timestamp = datetime.fromisoformat(timestamp_str)
            if timezone.now() - timestamp > timedelta(minutes=5):
                request.session.pop('pending_2fa_user_id', None)
                request.session.pop('pending_2fa_timestamp', None)
                return Response(
                    {'error': '2FA session expired'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            user = User.objects.get(id=user_id)

            if verify_code(user, code, code_type):
                # Clear pending session
                request.session.pop('pending_2fa_user_id', None)
                request.session.pop('pending_2fa_timestamp', None)
                
                response = Response({
                    'message': '2FA verification successful',
                    'user': {'id': user.id, 'email': user.email}
                })

                if code_type == "login":
                    # Generate JWT tokens
                    tokens = RefreshToken.for_user(user)

                    # Set cookies
                    response.set_cookie(
                        "access",
                        str(tokens.access_token),
                        max_age=60 * 60,
                        httponly=True,
                        secure=not settings.DEBUG,
                        samesite="Lax" if settings.DEBUG else "None",
                        path="/",
                    )
                    response.set_cookie(
                        "refresh",
                        str(tokens),
                        max_age=24 * 60 * 60,
                        httponly=True,
                        secure=not settings.DEBUG,
                        samesite="Lax" if settings.DEBUG else "None",
                        path="/auth/refresh/",
                    )
                
                return response
            else:
                return Response(
                    {'error': 'Invalid or expired 2FA code'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid request'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordView(APIView):
    """
    PUT: Change password for authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        """Change authenticated user's password"""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_new_password = request.data.get('confirm_new_password')

        if not old_password or not new_password or not confirm_new_password:
            return Response(
                {'error': 'Old password, new password, and confirm new password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_new_password:
            return Response(
                {'error': 'New password and confirm new password do not match'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify old password
        user = request.user
        if not user.check_password(old_password):
            return Response(
                {'error': 'Old password is incorrect'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Password validation
        if not (8 <= len(new_password) <= 20):
            return Response(
                {'error': 'Password must be between 8 and 20 characters'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not any(char.isdigit() for char in new_password):
            return Response(
                {'error': 'Password must contain at least one digit'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not any(char.isalpha() for char in new_password):
            return Response(
                {'error': 'Password must contain at least one letter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in new_password):
            return Response(
                {'error': 'Password must contain at least one special character'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not any(char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for char in new_password):
            return Response(
                {'error': 'Password must contain at least one uppercase letter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {'message': 'Password changed successfully'}, 
            status=status.HTTP_200_OK
        )


class UserQRCodeView(APIView):
    """
    GET: Get QR code for TOTP setup
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get QR code image for TOTP setup"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only allow users to get their own QR code or admins to get any
        if request.user.id != user_id and not request.user.is_staff:
            return Response(
                {"detail": "Permission denied"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        return setup_totp(user)
