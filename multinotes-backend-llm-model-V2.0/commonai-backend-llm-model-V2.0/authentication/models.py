from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin, AbstractBaseUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import random
import string
# from coreapp.models import StorageUsage



# Create your models here.
class Role(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    

# @receiver(post_save, sender=Role)
# def create_default_row(sender, instance, created, **kwargs):
#     if created and Role.objects.count() == 1: 
#         # Create the default row
#         Role.objects.create(name='admin')

    
def validate_symbol(value):
    if '@' in value:
        raise ValidationError('The value should not contain the @ symbol.')
    
class Cluster(models.Model):
    plan = models.ForeignKey('planandsubscription.UserPlan', on_delete=models.CASCADE)

    storage_plan = models.ForeignKey('planandsubscription.UserPlan', on_delete=models.CASCADE, related_name='storage_plan')

    subscription = models.ForeignKey('planandsubscription.Subscription', on_delete=models.CASCADE, null=True, blank=True)
    
    storage = models.ForeignKey('coreapp.StorageUsage', on_delete=models.CASCADE, null=True, blank=True)
    
    cluster_name = models.CharField(max_length=255)
    org_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=250)
    domain = models.CharField(max_length=255, validators=[validate_symbol])
    is_enabled = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.cluster_name}"

class CustomUser(AbstractUser, PermissionsMixin):
    class Meta:
        db_table='customuser'

    social_type = ((2, 'google'),(3, 'facebook'))
    # status_type = (('free', 'free'),('paid', 'paid'), ('expire', 'expire'))
    gender_type = (('male','male'),('female','female'))

    username = models.CharField(max_length=250)
    name = models.CharField(default="guest", max_length=250) # first + lastName
    email = models.EmailField(max_length=250)
    phone_number = models.CharField(unique=True, max_length=100, null=True)
    country_code = models.CharField(max_length=100, null=True, blank=True)
    first_name = None # Not Required
    last_name = None
    profile_image = models.CharField(max_length=250, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=gender_type, null=True, blank=True)
    # status = models.CharField(choices=status_type, max_length=100, default='free')
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, null=True, blank=True)
    is_cluster_owner = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=14, unique=True, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=100, null=True, blank=True)
    mobile_otp = models.CharField(max_length=50, null=True, blank=True)
    email_otp = models.CharField(max_length=50, null=True, blank=True)
    socialId = models.CharField(max_length=250, null=True, blank=True)
    deviceToken = models.CharField(max_length=250, null=True, blank=True)
    credentials = models.TextField(null=True, blank=True)
    groupName = models.CharField(max_length=250, null=True, blank=True)
    stripeCustomerId = models.CharField(max_length=250, null=True, blank=True)
    socialType = models.IntegerField(choices=social_type, null=True, blank=True)
    is_verified = models.BooleanField(default=True)
    password_generate = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # different user roles
    roles = models.ManyToManyField(Role)
   
    USERNAME_FIELD = 'id'
    # REQUIRED_FIELDS = ['username']
    
    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    
    def save(self, *args, **kwargs):
        if self.is_superuser:
            super().save(*args, **kwargs)
            # Add default role
            role, _ = Role.objects.get_or_create(name='admin')
            self.roles.add(role)
        else:
            super().save(*args, **kwargs)

    def __str__(self):  
        return f'{self.username}'
    
    
def generate_unique_referral_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        if not CustomUser.objects.filter(referral_code=code).exists():
            return code  
        
@receiver(post_save, sender=CustomUser)
def set_referral_code(sender, instance, created, **kwargs):
    if created and not instance.referral_code and not instance.cluster:
        instance.referral_code = generate_unique_referral_code()
        instance.save()

# class UserToken(models.Model):
#     # class Meta:
#     #     db_table='usertoken'

#     TOKEN_TYPES = (
#         ('refresh', 'refresh'),
#         ('reset password', 'reset password')
#     )

#     token = models.CharField(max_length=255, unique=True)
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     type = models.CharField(max_length=55, choices=TOKEN_TYPES)
#     expires = models.DateTimeField()
#     blacklisted = models.BooleanField(default=False)
#     is_delete = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user}"

#     def is_expired(self):
#         return timezone.now() > self.expires
    

# class VerificationToken(models.Model):
#     # class Meta:
#     #     db_table='verificationtoken'

#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     token = models.CharField(max_length=255, unique=True)
#     is_delete = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user}"
    

class TokenBlacklist(models.Model):
    token = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    isTokenUsed = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Referral(models.Model):
    referr_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referrals_by')

    referr_to = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='referrals_to', null=True, blank=True)
    refer_to_token = models.IntegerField(default=0)
    refer_by_token = models.IntegerField(default=0)
    code = models.CharField(max_length=50)
    reward_given = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f"{self.referr_by.username} referr_to {self.referr_to.username if self.referr_to else 'None'}"


class ReferralSetting(models.Model):
    refer_to_token = models.IntegerField(default=0)
    refer_by_token = models.IntegerField(default=0)
    storage = models.FloatField(default=0)
    isToken = models.BooleanField(default=False)
    isStorage = models.BooleanField(default=False)
    isFirstPayment = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return self.token
    




