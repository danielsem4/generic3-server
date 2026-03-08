from rest_framework import serializers
from users.models import User, Doctor, Patient, ClinicManager


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with basic fields"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'role']
        read_only_fields = ['id', 'role']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer including patient modules if applicable"""
    patient_modules = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'patient_modules']
        read_only_fields = ['id', 'role']
    
    def get_patient_modules(self, obj):
        """Get patient modules if user is a patient"""
        if obj.role in ['PATIENT', 'RESEARCH_PATIENT']:
            from modules.models import PatientModules
            clinic_id = self.context.get('clinic_id')
            if clinic_id:
                patient_modules = PatientModules.objects.filter(
                    patient__user=obj,
                    clinic__id=clinic_id
                ).select_related('module').values(
                    'module__id',
                    'module__module_name',
                    'module__module_description',
                    'is_active'
                )
                return [{
                    'id': module['module__id'],
                    'name': module['module__module_name'],
                    'description': module['module__module_description'],
                    'active': module['is_active']
                } for module in patient_modules]
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'password', 'confirm_password']
    
    def validate(self, data):
        """Validate password confirmation if provided"""
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        return data

