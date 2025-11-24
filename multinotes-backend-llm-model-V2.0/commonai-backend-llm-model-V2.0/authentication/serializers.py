from rest_framework import serializers
from .models import CustomUser, Role, Cluster, Referral, ReferralSetting
from planandsubscription.models import Subscription, Transaction
from ticketandcategory.models import MainCategory, Category
from rest_framework.exceptions import ValidationError
from .awsservice import getImageUrl
from django.db.models import Sum
from coreapp.views import format_number
from coreapp.models import PromptResponse, StorageUsage
from planandsubscription.serializers import (
           ModelPlanSerializer, UpdateSubscriptionSerializer
           )
from coreapp.serializers import GetCustomUserSerializer, StorageOutputSerializer
from backend.validators import (
    validate_password_strength,
    validate_email_format,
    validate_email_domain,
    validate_username,
    validate_phone_number,
    validate_country_code,
    sanitize_text,
    validate_referral_code,
)


class SocialLoginSerializer(serializers.Serializer):
    """Serializer for social login with input validation."""
    username = serializers.CharField(max_length=30)
    email = serializers.EmailField(max_length=255)
    socialId = serializers.CharField(max_length=255)
    socialType = serializers.IntegerField()
    role = serializers.CharField(max_length=50)
    password_generate = serializers.BooleanField()
    deviceToken = serializers.CharField(required=False, max_length=500, allow_blank=True)
    cluster_id = serializers.IntegerField(required=False)

    def validate_username(self, value):
        """Validate and sanitize username."""
        return validate_username(value)

    def validate_email(self, value):
        """Validate email format and domain."""
        value = validate_email_format(value)
        value = validate_email_domain(value)
        return value.lower()

    def validate_socialType(self, value):
        """Validate social type is valid."""
        valid_types = [1, 2, 3]  # 1=Google, 2=Apple, 3=Facebook
        if value not in valid_types:
            raise serializers.ValidationError("Invalid social login type.")
        return value

    def validate_role(self, value):
        """Validate role is valid."""
        valid_roles = ['user', 'admin', 'cluster_admin']
        if value.lower() not in valid_roles:
            raise serializers.ValidationError("Invalid role specified.")
        return value.lower()

    def create(self, validated_data):
        role = validated_data.pop('role')
        user = CustomUser.objects.create_user(**validated_data)
        role, _ = Role.objects.get_or_create(name=role)
        user.roles.add(role)
        return user


    # # role = serializers.CharField(required=True)
    # class Meta:
    #     model = CustomUser
    #     exclude = ["roles"]
    
    # def validate(self, attrs):
    #     email = attrs.get('email')
    #     username = attrs.get('username')

    #     if email and CustomUser.objects.filter(email=email, is_delete=False).exists():
    #         attrs.pop('email')  # Exclude email from validation if it already exists
    #     if username and CustomUser.objects.filter(username=username, is_delete=False).exists():
    #         attrs.pop('username')  # Exclude username from validation if it already exists
    #     return attrs
    
    # # Hash the password before saving
    # def create(self, validated_data):        
    #     user = CustomUser.objects.create_user(**validated_data)
    #     return user
    
    # def update(self, instance, validated_data):
    #     # validated_data.pop('email', None)
    #     validated_data.pop('password', None)

    #     instance = super().update(instance, validated_data)
    #     return instance
    
class UpdateSerializer(serializers.ModelSerializer):
    token_status = serializers.SerializerMethodField()
    storage_status = serializers.SerializerMethodField()
    credentials = serializers.CharField(write_only=True, allow_null=True)
    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'name', 
                  'phone_number', 'country_code', 'country', 'state', 
                  'zipcode', 'is_verified', 
                  'is_blocked', 'city', 'gender', 'token_status', 'storage_status', 'credentials', 'referral_code', 'stripeCustomerId']
    
    def get_token_status(self, instance):
        subs = Subscription.objects.filter(user=instance.id, is_delete=False).first()

        data = {
            "avialableTextToken": subs.balanceToken if subs else 0,
            "avialableFileToken": subs.fileToken if subs else 0,
        }
        return data
    
    def get_storage_status(self, instance):
        storage = StorageUsage.objects.filter(user=instance.id, is_delete=False).first()

        data = {
            "storageUsed": round(storage.total_storage_used/(1024*1024*1024), 2) if storage else 0,
            "storageLimit": round(storage.storage_limit/(1024*1024*1024), 2) if storage else 0,
        }
        return data

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration with comprehensive validation."""
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    password2 = serializers.CharField(write_only=True, min_length=8, max_length=128, required=False)
    role = serializers.CharField(max_length=50)
    referral_code = serializers.CharField(required=False, allow_blank=True, max_length=12)

    class Meta:
        model = CustomUser
        exclude = ["roles"]
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
        }

    def validate_email(self, value):
        """Validate email format, domain, and uniqueness."""
        value = validate_email_format(value)
        value = validate_email_domain(value)
        value = value.lower()

        # Check for existing user with this email
        if CustomUser.objects.filter(email=value, is_delete=False).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        """Validate username format and uniqueness."""
        value = validate_username(value)

        # Check for existing user with this username
        if CustomUser.objects.filter(username__iexact=value, is_delete=False).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_password(self, value):
        """Validate password strength."""
        return validate_password_strength(value)

    def validate_role(self, value):
        """Validate role is valid."""
        valid_roles = ['user', 'admin', 'cluster_admin']
        if value.lower() not in valid_roles:
            raise serializers.ValidationError("Invalid role specified.")
        return value.lower()

    def validate_referral_code(self, value):
        """Validate referral code if provided."""
        if value:
            value = validate_referral_code(value)
            # Check if referral code exists
            if not CustomUser.objects.filter(referral_code=value, is_delete=False).exists():
                raise serializers.ValidationError("Invalid referral code.")
        return value

    def validate_phone_number(self, value):
        """Validate phone number if provided."""
        if value:
            return validate_phone_number(value)
        return value

    def validate_country_code(self, value):
        """Validate country code if provided."""
        if value:
            return validate_country_code(value)
        return value

    def validate_name(self, value):
        """Sanitize name field."""
        if value:
            return sanitize_text(value)
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # Check password confirmation if provided
        password2 = attrs.pop('password2', None)
        if password2 and attrs.get('password') != password2:
            raise serializers.ValidationError({
                "password2": "Passwords do not match."
            })
        return attrs

    def create(self, validated_data):
        validated_data['is_verified'] = False
        validated_data['profile_image'] = None

        role = validated_data.pop('role')
        validated_data.pop('password2', None)  # Remove if present

        user = CustomUser.objects.create_user(**validated_data)

        role_obj, _ = Role.objects.get_or_create(name=role)
        user.roles.add(role_obj)

        user.save()
        return user
    
    # def update(self, instance, validated_data):
    #     validated_data.pop('password', None)
    #     validated_data.pop('profile_image', None)
    #     validated_data.pop('is_delete', None)

    #     instance = super().update(instance, validated_data)
    #     return instance
    

class ImageUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()

class ImageUrlSerializer(serializers.Serializer):
    url = serializers.URLField()



class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change with validation."""
    old_password = serializers.CharField(required=True, max_length=128)
    new_password = serializers.CharField(required=True, min_length=8, max_length=128)
    new_password2 = serializers.CharField(required=True, min_length=8, max_length=128)

    def validate_old_password(self, value):
        """Validate old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        """Validate new password strength."""
        return validate_password_strength(value)

    def validate(self, attrs):
        """Cross-field validation."""
        # Check passwords match
        if attrs.get('new_password') != attrs.get('new_password2'):
            raise serializers.ValidationError({
                "new_password2": "New passwords do not match."
            })

        # Check new password is different from old
        user = self.context['request'].user
        if user.check_password(attrs.get('new_password')):
            raise serializers.ValidationError({
                "new_password": "New password must be different from the old password."
            })

        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request."""
    email = serializers.EmailField(max_length=255)

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value).lower()


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset with token."""
    token = serializers.CharField(max_length=500)
    password = serializers.CharField(min_length=8, max_length=128)
    password2 = serializers.CharField(min_length=8, max_length=128)

    def validate_password(self, value):
        """Validate password strength."""
        return validate_password_strength(value)

    def validate(self, attrs):
        """Cross-field validation."""
        if attrs.get('password') != attrs.get('password2'):
            raise serializers.ValidationError({
                "password2": "Passwords do not match."
            })
        return attrs

    
class UserDetailSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    socialId = serializers.CharField()
    socialType = serializers.IntegerField()


class GetUserSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    token_status = serializers.SerializerMethodField()
    storage_status = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'name', 'email', 
                    'phone_number', 'country_code', 'profile_image',
                    'gender', 'country', 'city',  
                    'state', 'zipcode', 'is_verified', 
                    'is_delete', 'is_blocked', 'created_at', 
                    'user_type', 'password_generate', 'token_status',
                    'storage_status', 'roles', 'credentials', 'referral_code',
                    'email_otp'
                  ]
        
    def get_roles(self, obj):
        # Return the cluster name or None if there is no related cluster
        return [role.name for role in obj.roles.all()]
              
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if 'profileImage' in self.context and instance.profile_image:
            data['imageUrl'] = getImageUrl(instance.profile_image)
        return data
    
    def get_storage_status(self, instance):
        storage = StorageUsage.objects.filter(user=instance.id, is_delete=False).first()

        data = {
            "total_storage_used": round(storage.total_storage_used/(1024*1024*1024), 2) if storage else 0,
            "storage_limit": round(storage.storage_limit/(1024*1024*1024), 2) if storage else 0,
            "subscriptionExpiryDate": storage.subscriptionExpiryDate if storage else "N/A"
        }
        return data
    
    def get_token_status(self, instance):
        subs = Subscription.objects.filter(user=instance.id, is_delete=False).first()

        # text_ids = list(Category.objects.filter(alias_name__in=['category-1', 'category-3', 'category-4','category-7'], is_delete=False, status='active').values_list('id', flat=True))

        # file_ids = list(Category.objects.filter(alias_name__in=['category-2', 'category-5', 'category-6','category-7'], is_delete=False, status='active').values_list('id', flat=True))
        
        filtered_total_used_token = PromptResponse.objects.filter(
            user=instance.id, 
            is_delete=False, 
            response_type__in=[2, 3, 7, 8]).aggregate(total_used_token=Sum('tokenUsed'))
        totalUsedToken = filtered_total_used_token['total_used_token']

        
        filtered_total_buy_token = Transaction.objects.filter(
            user=instance.id, 
            payment_status= 'paid', 
            is_delete=False).aggregate(total_buy_token=Sum('tokenCount'))
        totalBuyToken = filtered_total_buy_token['total_buy_token']

        
        total_used_file_token = PromptResponse.objects.filter(
            user=instance.id, 
            is_delete=False, 
            response_type__in=[4, 5, 6]).aggregate(total_file_token=Sum('tokenUsed'))
        totalUsedFileToken = total_used_file_token['total_file_token']

        
        filtered_total_file_buy_token = Transaction.objects.filter(
            user=instance.id, 
            payment_status= 'paid', 
            is_delete=False).aggregate(total_buy_file_token=Sum('fileToken'))
        totalBuyFileToken = filtered_total_file_buy_token['total_buy_file_token']


        data = {
            "currentPlanAvialableToken": subs.balanceToken if subs else 0,
            # "currentPlanUsedToken": subs.usedToken if subs else 0,
            "totalUsedToken": totalUsedToken if totalUsedToken else 0,
            "totalBuyToken": totalBuyToken if totalBuyToken else 0,
            "totalExpireToken": subs.expireToken if subs else 0,

            "avialableFileToken": subs.fileToken if subs else 0,
            "totalUsedFileToken": totalUsedFileToken if totalUsedFileToken else 0,
            "totalBuyFileToken": totalBuyFileToken if totalBuyFileToken else 0,
            "totalExpireFileToken": subs.expireFileToken if subs else 0,
            "planExpireDate": subs.subscriptionExpiryDate if subs else "N/A"
        }
        return data
    
    def get_user_type(self, instance):
        subscription_status = Subscription.objects.filter(
                    user=instance.id, status__in=['active', 'expire']
                    ).values_list('status', flat=True)
        
        if 'active' in subscription_status:
            return 'paid'
        elif 'expire' in subscription_status:
            return 'expire'
        else:
            return 'free'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['name']       

class GetAllUserSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    token_status = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    # roles = RoleSerializer(many=True, read_only=True)
    # cluster = serializers.SerializerMethodField(source="cluster.cluster_name")
    cluster_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'name', 'email', 
                    'phone_number', 'country_code', 'profile_image',
                    'gender', 'country', 'city',  
                    'state', 'zipcode', 'is_verified', 
                    'is_delete', 'is_blocked', 'created_at', 
                    'user_type', 'token_status', 'password_generate', 
                    'cluster_name', 'cluster', 'is_cluster_owner', 'roles'
                  ]
        
    def get_roles(self, obj):
        # Return the cluster name or None if there is no related cluster
        return [role.name for role in obj.roles.all()]
        
    def get_cluster_name(self, obj):
        # Return the cluster name or None if there is no related cluster
        return obj.cluster.cluster_name if obj.cluster else None
              
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if 'profileImage' in self.context and instance.profile_image:
            data['imageUrl'] = getImageUrl(instance.profile_image)
        return data
    
    def get_token_status(self, instance):
        subs = Subscription.objects.filter(user=instance.id, is_delete=False).first()

        # text_ids = list(Category.objects.filter(alias_name__in=['category-1', 'category-3', 'category-4','category-7'], is_delete=False, status='active').values_list('id', flat=True))

        # file_ids = list(Category.objects.filter(alias_name__in=['category-2', 'category-5', 'category-6','category-7'], is_delete=False, status='active').values_list('id', flat=True))
        
        filtered_total_used_token = PromptResponse.objects.filter(
            user=instance.id, 
            is_delete=False, 
            response_type__in=[2, 3, 7, 8]).aggregate(total_used_token=Sum('tokenUsed'))
        totalUsedToken = filtered_total_used_token['total_used_token']

        
        filtered_total_buy_token = Transaction.objects.filter(
            user=instance.id, 
            payment_status= 'paid', 
            is_delete=False).aggregate(total_buy_token=Sum('tokenCount'))
        totalBuyToken = filtered_total_buy_token['total_buy_token']

        
        total_used_file_token = PromptResponse.objects.filter(
            user=instance.id, 
            is_delete=False, 
            response_type__in=[4, 5, 6]).aggregate(total_file_token=Sum('tokenUsed'))
        totalUsedFileToken = total_used_file_token['total_file_token']

        
        filtered_total_file_buy_token = Transaction.objects.filter(
            user=instance.id, 
            payment_status= 'paid', 
            is_delete=False).aggregate(total_buy_file_token=Sum('fileToken'))
        totalBuyFileToken = filtered_total_file_buy_token['total_buy_file_token']


        data = {
            "currentPlanAvialableToken": subs.balanceToken if subs else 0,
            # "currentPlanUsedToken": format_number(subs.usedToken) if subs else "0",
            "totalUsedToken": totalUsedToken if totalUsedToken else 0,
            "totalBuyToken": totalBuyToken if totalBuyToken else 0,
            "totalExpireToken": subs.expireToken if subs else 0,

            "avialableFileToken": subs.fileToken if subs else 0,
            "totalUsedFileToken": totalUsedFileToken if totalUsedFileToken else 0,
            "totalBuyFileToken": totalBuyFileToken if totalBuyFileToken else 0,
            "totalExpireFileToken": subs.expireFileToken if subs else 0,
            "planExpireDate": subs.subscriptionExpiryDate if subs else "NA"
        }
        return data
    
    def get_user_type(self, instance):
        subscription_status = Subscription.objects.filter(
                    user=instance.id, status__in=['active', 'expire']
                    ).values_list('status', flat=True)
        
        if 'active' in subscription_status:
            return 'paid'
        elif 'expire' in subscription_status:
            return 'expire'
        else:
            return 'free'


class DeleteUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['is_delete']


class GenerateCardTokenSerializer(serializers.Serializer):
    cardNumber = serializers.CharField(max_length=100)
    expYear = serializers.CharField(max_length=4)
    expMonth = serializers.CharField(max_length=2)
    cvc = serializers.CharField(max_length=4)

class UpdateCardSerializer(serializers.Serializer):
    customerId = serializers.CharField(max_length=100)
    cardId = serializers.CharField(max_length=100)
    # name = serializers.CharField(max_length=100, required=False)
    expYear = serializers.CharField(max_length=4)
    expMonth = serializers.CharField(max_length=2)

class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = '__all__'


class ClusterOutputSerializer(serializers.ModelSerializer):
    total_users = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    plan = ModelPlanSerializer()
    storage_plan = ModelPlanSerializer()
    subscription = UpdateSubscriptionSerializer()
    storage = StorageOutputSerializer()

    class Meta:
        model = Cluster
        fields = '__all__'

    def get_total_users(self, obj):
        users = CustomUser.objects.filter(cluster=obj.id, is_delete=False).count()
        return users

    def get_user(self, obj):
        user = CustomUser.objects.filter(cluster=obj.id, is_cluster_owner=True, is_delete=False).first()
        if user:
            data = {
                "userName": user.username,
                "phoneNumber": user.phone_number
            }
            return data
        else:
            return None

class ReferralSerializer(serializers.ModelSerializer):
    referr_to = GetCustomUserSerializer()
    class Meta:
        model = Referral
        fields = '__all__'

class ReferralPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = '__all__'

class ReferralInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralSetting
        fields = '__all__'

class ReferralOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralSetting
        fields = '__all__'



