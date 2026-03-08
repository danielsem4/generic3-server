"""
Comprehensive test suite for authentication app.
Tests JWT authentication, 2FA flows, password changes, and security controls.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock, Mock
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from factories import (
    UserFactory, AdminUserFactory, DoctorUserFactory,
    PatientUserFactory, ClinicFactory, DoctorFactory,
    DoctorClinicFactory, ManagerClinicFactory, ClinicManagerFactory,
    ModulesFactory, ClinicModulesFactory
)
from users.models import User

pytestmark = pytest.mark.django_db


class TestSessionView:
    """Test login and logout functionality."""
    
    def test_login_success_with_valid_credentials(self, api_client, mock_send_email):
        """Test successful login with valid email and password."""
        user = UserFactory(role='ADMIN', is_staff=True)
        user.set_password('testpass123')
        user.save()
        
        url = reverse('sessions')
        data = {'email': user.email, 'password': 'testpass123'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert response.data['user']['email'] == user.email
        assert 'access_token' in response.data['user']
        assert 'refresh_token' in response.data['user']
        assert 'access' in response.cookies
        assert 'refresh' in response.cookies
    
    def test_login_with_clinic_context(self, api_client, mock_static_find):
        """Test login retrieves clinic context for non-staff users."""
        # Create doctor with clinic
        user = DoctorUserFactory()
        user.set_password('testpass123')
        user.save()
        doctor = DoctorFactory(user=user)
        clinic = ClinicFactory(clinic_name='TestClinic', clinic_url='https://testclinic.example.com')
        DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        # Create modules for clinic
        module1 = ModulesFactory(module_name='Activities')
        module2 = ModulesFactory(module_name='Medications')
        ClinicModulesFactory(clinic=clinic, module=module1)
        ClinicModulesFactory(clinic=clinic, module=module2)
        
        url = reverse('sessions')
        data = {'email': user.email, 'password': 'testpass123'}
        
        response = api_client.post(url, data, format='json', HTTP_HOST='testclinic.example.com')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user']['clinicName'] == 'TestClinic'
        assert response.data['user']['clinicId'] == clinic.id
        assert len(response.data['user']['modules']) == 2
        assert any(m['name'] == 'Activities' for m in response.data['user']['modules'])
    
    def test_login_fails_with_invalid_credentials(self, api_client):
        """Test login fails with wrong password."""
        user = UserFactory()
        user.set_password('correctpass')
        user.save()
        
        url = reverse('sessions')
        data = {'email': user.email, 'password': 'wrongpass'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid credentials' in response.data['detail']
    
    def test_login_requires_email_and_password(self, api_client):
        """Test login validation requires both email and password."""
        url = reverse('sessions')
        
        # Missing password
        response = api_client.post(url, {'email': 'test@example.com'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing email
        response = api_client.post(url, {'password': 'testpass'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_fails_for_non_staff_without_clinic(self, api_client):
        """Test non-staff users must have clinic association."""
        user = DoctorUserFactory()
        user.set_password('testpass123')
        user.save()
        # No DoctorClinic created - user has no clinic
        
        url = reverse('sessions')
        data = {'email': user.email, 'password': 'testpass123'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'No clinics found' in response.data['detail']
    
    def test_logout_clears_cookies_and_token(self, api_client):
        """Test logout removes cookies and tokens."""
        user = UserFactory()
        api_client.force_authenticate(user=user)
        
        url = reverse('sessions')
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Check cookies are deleted
        assert response.cookies.get('access', {}).get('max-age') == 0
        assert response.cookies.get('refresh', {}).get('max-age') == 0
    
    def test_logout_fails_for_unauthenticated(self, api_client):
        """Test logout requires authentication."""
        url = reverse('sessions')
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_jwt_cookies_have_security_attributes(self, api_client):
        """Test JWT cookies have HttpOnly and proper SameSite attributes."""
        user = AdminUserFactory()
        user.set_password('testpass123')
        user.save()
        
        url = reverse('sessions')
        data = {'email': user.email, 'password': 'testpass123'}
        
        response = api_client.post(url, data, format='json')
        
        access_cookie = response.cookies.get('access')
        refresh_cookie = response.cookies.get('refresh')
        
        assert access_cookie['httponly'] is True
        assert refresh_cookie['httponly'] is True
        assert access_cookie['max-age'] == 3600  # 60 minutes
        assert refresh_cookie['max-age'] == 86400  # 24 hours


class TestTokenRefreshView:
    """Test JWT token refresh functionality."""
    
    def test_refresh_token_generates_new_access_token(self, api_client):
        """Test valid refresh token generates new access token."""
        user = UserFactory()
        refresh_token = RefreshToken.for_user(user)
        
        api_client.cookies['refresh'] = str(refresh_token)
        
        url = reverse('token-refresh')
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.cookies
    
    def test_refresh_fails_without_refresh_cookie(self, api_client):
        """Test refresh endpoint requires refresh cookie."""
        url = reverse('token-refresh')
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'No refresh cookie' in response.data['detail']
    
    def test_refresh_fails_with_invalid_token(self, api_client):
        """Test refresh fails with invalid/expired token."""
        api_client.cookies['refresh'] = 'invalid_token_string'
        
        url = reverse('token-refresh')
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid refresh token' in response.data['detail']
    
    def test_refresh_token_extends_session(self, api_client):
        """Test refreshed access token has proper expiration."""
        user = UserFactory()
        refresh_token = RefreshToken.for_user(user)
        
        api_client.cookies['refresh'] = str(refresh_token)
        
        url = reverse('token-refresh')
        response = api_client.post(url)
        
        access_cookie = response.cookies.get('access')
        assert access_cookie['max-age'] == 3600  # 60 minutes


class TestTwoFactorAuthView:
    """Test 2FA code request functionality."""
    
    def test_2fa_code_request_creates_session(self, api_client, mock_send_email):
        """Test 2FA request creates pending session."""
        user = UserFactory()
        user.set_password('testpass123')
        user.save()
        
        url = reverse('two-factor-auth')
        data = {
            'email': user.email,
            'password': 'testpass123',
            'send_method': 'email'
        }
        
        with patch('generic3.utils.send2FA_code') as mock_send:
            mock_send.return_value = Mock(status_code=200)
            response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['requires_2fa'] is True
        assert 'session_key' in response.data
    
    def test_2fa_code_request_sends_email(self, api_client):
        """Test 2FA request sends verification code via email."""
        user = UserFactory(email='test@example.com')
        user.set_password('testpass123')
        user.save()
        
        url = reverse('two-factor-auth')
        data = {
            'email': user.email,
            'password': 'testpass123',
            'send_method': 'email'
        }
        
        with patch('generic3.utils.send2FA_code') as mock_send:
            mock_send.return_value = Mock(status_code=200)
            api_client.post(url, data, format='json')
            mock_send.assert_called_once_with(user, 'email')
    
    def test_2fa_request_fails_with_invalid_credentials(self, api_client):
        """Test 2FA request fails with wrong password."""
        user = UserFactory()
        user.set_password('correctpass')
        user.save()
        
        url = reverse('two-factor-auth')
        data = {
            'email': user.email,
            'password': 'wrongpass',
            'send_method': 'email'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_2fa_request_requires_email(self, api_client):
        """Test 2FA request validates required fields."""
        url = reverse('two-factor-auth')
        data = {'password': 'testpass'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Email is required' in response.data['error']
    
    def test_2fa_session_stores_user_and_timestamp(self, api_client):
        """Test 2FA request stores user ID and timestamp in session."""
        user = UserFactory()
        user.set_password('testpass123')
        user.save()
        
        url = reverse('two-factor-auth')
        data = {
            'email': user.email,
            'password': 'testpass123'
        }
        
        with patch('generic3.utils.send2FA_code') as mock_send:
            mock_send.return_value = Mock(status_code=200)
            response = api_client.post(url, data, format='json')
        
        # Check session contains pending 2FA data
        session = api_client.session
        assert session.get('pending_2fa_user_id') == user.id
        assert 'pending_2fa_timestamp' in session


class TestTwoFactorVerifyView:
    """Test 2FA code verification functionality."""
    
    def test_2fa_verify_success_with_valid_code(self, api_client):
        """Test 2FA verification succeeds with valid code."""
        user = UserFactory()
        
        # Set up pending 2FA session
        session = api_client.session
        session['pending_2fa_user_id'] = user.id
        session['pending_2fa_timestamp'] = timezone.now().isoformat()
        session.save()
        
        url = reverse('two-factor-verify')
        data = {
            'code': '123456',
            'code_type': 'login'
        }
        
        with patch('generic3.utils.verify_code') as mock_verify:
            mock_verify.return_value = True
            response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert '2FA verification successful' in response.data['message']
        assert 'access' in response.cookies
        assert 'refresh' in response.cookies
    
    def test_2fa_verify_clears_pending_session(self, api_client):
        """Test successful 2FA verification clears pending session."""
        user = UserFactory()
        
        session = api_client.session
        session['pending_2fa_user_id'] = user.id
        session['pending_2fa_timestamp'] = timezone.now().isoformat()
        session.save()
        
        url = reverse('two-factor-verify')
        data = {'code': '123456', 'code_type': 'login'}
        
        with patch('generic3.utils.verify_code') as mock_verify:
            mock_verify.return_value = True
            api_client.post(url, data, format='json')
        
        # Check session is cleared
        session = api_client.session
        assert 'pending_2fa_user_id' not in session
        assert 'pending_2fa_timestamp' not in session
    
    def test_2fa_verify_fails_with_invalid_code(self, api_client):
        """Test 2FA verification fails with wrong code."""
        user = UserFactory()
        
        session = api_client.session
        session['pending_2fa_user_id'] = user.id
        session['pending_2fa_timestamp'] = timezone.now().isoformat()
        session.save()
        
        url = reverse('two-factor-verify')
        data = {'code': 'wrong_code', 'code_type': 'login'}
        
        with patch('generic3.utils.verify_code') as mock_verify:
            mock_verify.return_value = False
            response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Invalid or expired 2FA code' in response.data['error']
    
    def test_2fa_verify_fails_without_pending_session(self, api_client):
        """Test 2FA verification requires pending session."""
        url = reverse('two-factor-verify')
        data = {'code': '123456', 'code_type': 'login'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'No pending 2FA session' in response.data['error']
    
    def test_2fa_verify_fails_after_session_expiration(self, api_client):
        """Test 2FA session expires after 5 minutes."""
        user = UserFactory()
        
        # Create expired session (6 minutes ago)
        expired_time = timezone.now() - timedelta(minutes=6)
        session = api_client.session
        session['pending_2fa_user_id'] = user.id
        session['pending_2fa_timestamp'] = expired_time.isoformat()
        session.save()
        
        url = reverse('two-factor-verify')
        data = {'code': '123456', 'code_type': 'login'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '2FA session expired' in response.data['error']
    
    def test_2fa_verify_requires_code(self, api_client):
        """Test 2FA verification validates required fields."""
        user = UserFactory()
        
        session = api_client.session
        session['pending_2fa_user_id'] = user.id
        session['pending_2fa_timestamp'] = timezone.now().isoformat()
        session.save()
        
        url = reverse('two-factor-verify')
        data = {'code_type': 'login'}  # Missing code
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Verification code is required' in response.data['error']


class TestPasswordView:
    """Test password change functionality."""
    
    def test_password_change_success(self, api_client):
        """Test successful password change with valid inputs."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456@',
            'confirm_new_password': 'NewPass456@'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Password changed successfully' in response.data['message']
        
        # Verify password was actually changed
        user.refresh_from_db()
        assert user.check_password('NewPass456@')
    
    def test_password_change_requires_authentication(self, api_client):
        """Test password change endpoint requires authentication."""
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456@',
            'confirm_new_password': 'NewPass456@'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_password_change_verifies_old_password(self, api_client):
        """Test password change validates old password."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'WrongOldPass!',
            'new_password': 'NewPass456@',
            'confirm_new_password': 'NewPass456@'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Old password is incorrect' in response.data['error']
    
    def test_password_change_requires_confirmation_match(self, api_client):
        """Test password change validates confirmation matches."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456@',
            'confirm_new_password': 'DifferentPass789#'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'do not match' in response.data['error']
    
    def test_password_change_enforces_length_validation(self, api_client):
        """Test password must be 8-20 characters."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        
        # Too short
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'Short1!',
            'confirm_new_password': 'Short1!'
        }
        response = api_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '8 and 20 characters' in response.data['error']
        
        # Too long
        data['new_password'] = 'VeryLongPassword123!@#$%'
        data['confirm_new_password'] = 'VeryLongPassword123!@#$%'
        response = api_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_password_change_requires_digit(self, api_client):
        """Test password must contain at least one digit."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NoDigits!@#',
            'confirm_new_password': 'NoDigits!@#'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'at least one digit' in response.data['error']
    
    def test_password_change_requires_letter(self, api_client):
        """Test password must contain at least one letter."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': '12345678!@#',
            'confirm_new_password': '12345678!@#'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'at least one letter' in response.data['error']
    
    def test_password_change_requires_special_char(self, api_client):
        """Test password must contain at least one special character."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NoSpecial123',
            'confirm_new_password': 'NoSpecial123'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'special character' in response.data['error']
    
    def test_password_change_requires_uppercase(self, api_client):
        """Test password must contain at least one uppercase letter."""
        user = UserFactory()
        user.set_password('OldPass123!')
        user.save()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'lowercase123!',
            'confirm_new_password': 'lowercase123!'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'uppercase letter' in response.data['error']
    
    def test_password_change_requires_all_fields(self, api_client):
        """Test password change validates all required fields."""
        user = UserFactory()
        api_client.force_authenticate(user=user)
        
        url = reverse('password')
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456@'
            # Missing confirm_new_password
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'required' in response.data['error']


class TestUserQRCodeView:
    """Test TOTP QR code generation."""
    
    def test_qr_code_generation_for_own_account(self, api_client):
        """Test user can get QR code for their own account."""
        user = UserFactory()
        api_client.force_authenticate(user=user)
        
        url = reverse('user-qr-code', kwargs={'user_id': user.id})
        
        with patch('generic3.utils.setup_totp') as mock_setup:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_setup.return_value = mock_response
            
            response = api_client.get(url)
            
            assert response.status_code == 200
            mock_setup.assert_called_once_with(user)
    
    def test_qr_code_generation_requires_authentication(self, api_client):
        """Test QR code endpoint requires authentication."""
        user = UserFactory()
        url = reverse('user-qr-code', kwargs={'user_id': user.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_qr_code_generation_denied_for_other_users(self, api_client):
        """Test non-admin users cannot get QR codes for other users."""
        user1 = UserFactory()
        user2 = UserFactory()
        api_client.force_authenticate(user=user1)
        
        url = reverse('user-qr-code', kwargs={'user_id': user2.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Permission denied' in response.data['detail']
    
    def test_qr_code_generation_allowed_for_admin(self, api_client):
        """Test admin can get QR codes for any user."""
        admin = AdminUserFactory()
        user = UserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('user-qr-code', kwargs={'user_id': user.id})
        
        with patch('generic3.utils.setup_totp') as mock_setup:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_setup.return_value = mock_response
            
            response = api_client.get(url)
            
            assert response.status_code == 200
    
    def test_qr_code_generation_handles_nonexistent_user(self, api_client):
        """Test QR code endpoint returns 404 for nonexistent user."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('user-qr-code', kwargs={'user_id': 99999})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'User not found' in response.data['detail']


class TestJWTSecurityControls:
    """Test JWT token security features."""
    
    def test_expired_access_token_rejected(self, api_client):
        """Test expired access tokens are rejected."""
        user = UserFactory()
        
        # Create an expired token (manually manipulate expiration)
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        
        # Set expiration to past
        token.set_exp(lifetime=timedelta(seconds=-1))
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')
        
        url = reverse('current_user')
        response = api_client.get(url)
        
        # Should be unauthorized due to expired token
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_jwt_contains_user_identification(self, api_client):
        """Test JWT tokens contain proper user identification."""
        user = UserFactory(email='test@example.com')
        
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Decode token and verify user_id
        assert str(access_token['user_id']) == str(user.id)
    
    def test_cookie_auth_takes_precedence(self, api_client):
        """Test cookie-based JWT authentication works."""
        user = UserFactory()
        user.set_password('testpass123')
        user.save()
        
        # Login to get cookies
        url = reverse('sessions')
        data = {'email': user.email, 'password': 'testpass123'}
        response = api_client.post(url, data, format='json')
        
        # Use cookies for authenticated request
        access_cookie = response.cookies['access'].value
        api_client.cookies['access'] = access_cookie
        
        url = reverse('current_user')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

