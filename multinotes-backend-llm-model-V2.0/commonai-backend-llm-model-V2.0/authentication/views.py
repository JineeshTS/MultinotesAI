from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (RegisterSerializer, ImageUploadSerializer, 
                          ChangePasswordSerializer, ForgotPasswordSerializer,
                          PasswordResetSerializer, SocialLoginSerializer, 
                          GetUserSerializer, DeleteUserSerializer,
                          UpdateSerializer, ImageUrlSerializer, GetAllUserSerializer,
                          ClusterSerializer, ClusterOutputSerializer, ReferralSerializer,
                          ReferralInputSerializer, ReferralOutputSerializer,
                          ReferralPostSerializer
                        )
from django.contrib.auth import authenticate
from .models import Role
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from rest_framework import status
from .tasks import send_verification_email, sendResetPasswordMail, otp_for_user_to_sub_admin
from rest_framework_simplejwt.authentication import JWTAuthentication   
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.hashers import make_password
from .utils import generateJWTToken
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import get_user_model
from django.core.serializers import serialize
from rest_framework.renderers import JSONRenderer
from .models import CustomUser, TokenBlacklist, Cluster, Referral, ReferralSetting
from .awsservice import getImageUrl, uploadImage
from rest_framework.pagination import PageNumberPagination
from .awsservice import getImageUrl
from .payments import createCustomerOnStripe
from planandsubscription.models import Subscription, UserPlan
from datetime import datetime, timedelta
from django.utils import timezone
from coreapp.models import StorageUsage
import random
import boto3
import time
import jwt
import os
import re
from django.db.models import Q


class SocialLogin(APIView):
    permission_classes = [AllowAny]

    # # permission_classes = [AllowAny]
    # def get_permissions(self):
    #     if self.request.method == 'POST':
    #         # Allow any user to access the POST method
    #         return [AllowAny()]
    #     else:
    #         # Use the default permissions for other HTTP methods
    #         return super().get_permissions()
    

    def post(self, request):
        data = request.data.copy()
        # data['password_generate'] = os.getenv('SOCIAL_LOGIN_PASSWORD')
        data['password_generate'] = False

        referr_by_code = request.data.get('referr_by_code', None) 

        email = data['email']
        domain = email.split("@")[1]
        cluster = Cluster.objects.filter(domain=domain, is_delete=False, is_enabled=True).first()

        if cluster:
            data['cluster_id'] = cluster.id
            data['role'] = "enterprise_user"

        serializer = SocialLoginSerializer(data=data)

        if serializer.is_valid():
            socialId = serializer.validated_data.get('socialId')
            socialType = serializer.validated_data.get('socialType')
            email = serializer.validated_data.get('email')
            username = serializer.validated_data.get('username')
            deviceToken = serializer.validated_data.get('deviceToken')

            # user = CustomUser.objects.filter(Q(socialId=socialId) | Q(username=username) | Q(email=email),  is_delete=False).first()

            user = CustomUser.objects.filter(Q(socialId=socialId) | Q(email=email),  is_delete=False).first()
            
            subs= None
            storage = None
            if user:
                if user and user.is_blocked:
                    return Response({'message': 'You are blocked.'}, status=status.HTTP_401_UNAUTHORIZED)
                
                # elif user and user.is_delete:
                #     return Response({'message': 'User Deleted'}, status=status.HTTP_400_BAD_REQUEST)

                user.socialId = socialId
                user.socialType = socialType

                # Create Customer Stripe Account if not exist
                if not user.stripeCustomerId and not cluster:
                    custId = createCustomerOnStripe(user.username, user.email)
                    if custId:
                        user.stripeCustomerId = custId
                user.save()

                # Check Subscription Status
                subs = Subscription.objects.filter(user=user.id, is_delete=False).first()
                storage = StorageUsage.objects.filter(user=user.id, is_delete=False).first()
                # subscription_status = Subscription.objects.filter(
                #         user=user.id, status__in=['active', 'expire', 'trial']
                #     ).values_list('id', 'status')

                # subscriptionId = None
                # userStatus = 'free'

                # for subscription in subscription_status:
                #     if 'active' in subscription:
                #         userStatus = 'paid'
                #         subscriptionId = subscription[0]  
                #         break  
                #     elif 'expire' in subscription:
                #         subscriptionId = subscription[0]
                #         userStatus = 'expire'
                #     else:
                #         subscriptionId = subscription[0]
                        
                message = "User Detail"

            else:
                user = serializer.save()

                if referr_by_code and not cluster:
                    referr_by_user = CustomUser.objects.filter(referral_code=referr_by_code).first()
                    refer_setting = ReferralSetting.objects.filter(isToken=True,is_delete=False).first()
                    if referr_by_user and refer_setting:
                        reffer_data = {
                            "referr_by": referr_by_user.id,
                            "referr_to": user.id,
                            "refer_to_token": refer_setting.refer_to_token,
                            "refer_by_token": refer_setting.refer_by_token,
                            "code": referr_by_code,
                        }
                    
                        serializer = ReferralPostSerializer(data=reffer_data, many=False)
                        if serializer.is_valid():
                            serializer.save()
                        else:
                            user.delete()
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                if not cluster:
                    custId = createCustomerOnStripe(user.username, user.email)
                    if custId:
                        user.stripeCustomerId = custId
                        user.save()

                    # subscriptionId = None
                    plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="token").first()

                    # Create Subscription for Trail Period Based on Trail Plan
                    if plan:
                        subs = Subscription.objects.create(
                            user_id = user.id, 
                            plan_id = plan.id,
                            subscriptionExpiryDate = timezone.now() + timedelta(days=plan.duration),
                            subscriptionEndDate = timezone.now() + timedelta(days=plan.duration + 7),
                            balanceToken = plan.totalToken,
                            fileToken = plan.fileToken,
                            description = "This is Free Plan For Trial Period", 
                            status = "trial", 
                            transactionId = "trial", 
                            payment_status = "trial", 
                            payment_mode = "online",
                            trialStartDate = timezone.now(), 
                            trialEndDate = timezone.now() + timedelta(days=plan.duration),

                            plan_name = plan.plan_name,
                            plan_for = plan.plan_for,
                            amount =  plan.amount,
                            duration = plan.duration,
                            totalToken = plan.totalToken,
                            totalFileToken = plan.fileToken,
                            feature = plan.feature,
                            discount = plan.discount

                        )

                    storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage").first()

                    # Create Free Storage Plan for New Register User
                    if storage_plan:
                        storage = StorageUsage.objects.create(
                            user_id = user.id, 
                            plan_id = storage_plan.id,
                            storage_limit = storage_plan.storage_size,
                            subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                            subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                            description = "This is Free Plan For Trial Period", 
                            status = "trial", 
                            transactionId = "trial", 
                            payment_status = "trial", 
                            payment_mode = "online",

                            plan_name = storage_plan.plan_name,
                            plan_for = storage_plan.plan_for,
                            amount =  storage_plan.amount,
                            duration = storage_plan.duration,
                            feature = storage_plan.feature,
                            discount = storage_plan.discount

                        )
                message = "User Created"
                    # subscriptionId = subscription.id
                # userStatus = 'free'


                # subscription_status = Subscription.objects.filter(
                #     user=user.id, status__in=['active', 'expire']
                # ).values_list('id', 'status')

                # subscriptionId = None
                # userStatus = 'free'  # Default status

                # for subscription in subscription_status:
                #     if 'active' in subscription:
                #         userStatus = 'paid'
                #         subscriptionId = subscription[0]  
                #         break  
                #     elif 'expire' in subscription:
                #         userStatus = 'expire'

            if deviceToken:
                user.deviceToken = deviceToken
                user.save()

            data = {
                "userName": user.username,
                "userId" : user.id,
                "is_cluster_owner": user.is_cluster_owner,
                "token": user.tokens(),
                "referral_code": user.referral_code,
                "image": user.profile_image,
                "role": [role.name for role in user.roles.all()],
                "customerId": user.stripeCustomerId,
                "status": 'free' if subs and subs.status == 'trial' else ('active' if subs and subs.status == 'active' else 'expire'),
                "subscriptionId": None if subs is None else subs.id,
                "credential": False if user.credentials is None else True,
                "storagePlanId": None if storage is None else storage.id,
                "clusterId": user.cluster.id if user.cluster else None,
                "message": message
            }

            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Create your views here.
class Register(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        self.authentication_classes = []
        data = request.data.copy()
        email = data['email']
        referr_by_code = request.data.get('referr_by_code', None)  

        refer_user = CustomUser.objects.filter(referral_code=referr_by_code).exists()
        
        if referr_by_code and not refer_user:
            return Response({"Message": "Please enter valid Referral code"}, status=status.HTTP_404_NOT_FOUND)

        domain = email.split("@")[1]
        cluster = Cluster.objects.filter(domain=domain, is_delete=False, is_enabled=True).first()

        if cluster:
            data['cluster'] = cluster.id
            data['role'] = 'enterprise_user'


        serializer = RegisterSerializer(data=data, many=False)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            username = serializer.validated_data['username']

            emailExist = CustomUser.objects.filter(email=email, is_delete=False).exists()
            nameExist = CustomUser.objects.filter(username=username, is_delete=False).exists()

            # is_exist = CustomUser.objects.filter(
            #     Q(email=email) | 
            #     Q(username=username), 
            #     is_delete=False
            # ).exists()

            if emailExist:
                return Response({"Message": "User with this email already exist"}, status=status.HTTP_400_BAD_REQUEST)

            if nameExist:
                return Response({"Message": "Username already exist. Please User Different Name"}, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()

            send_verification_email.delay(user.id)

            if referr_by_code and not cluster:
                referr_by_user = CustomUser.objects.filter(referral_code=referr_by_code).first()
                refer_setting = ReferralSetting.objects.filter(isToken=True,is_delete=False).first()
                if referr_by_user:
                    reffer_data = {
                        "referr_by": referr_by_user.id,
                        "referr_to": user.id,
                        "refer_to_token": refer_setting.refer_to_token,
                        "refer_by_token": refer_setting.refer_by_token,
                        "code": referr_by_code,
                    }
                
                    serializer = ReferralPostSerializer(data=reffer_data, many=False)
                    if serializer.is_valid():
                        serializer.save()
                    else:
                        user.delete()
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
            subs= None
            storage = None
            if not cluster:
                custId = createCustomerOnStripe(user.username, user.email)
                if custId:
                    user.stripeCustomerId = custId
                    user.save()
            

                plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="token").first()
                
                # Create Trial Subscription for New Regisrer User
                if plan:
                    subs = Subscription.objects.create(
                        user_id = user.id, 
                        plan_id = plan.id,
                        subscriptionExpiryDate = timezone.now() + timedelta(days=plan.duration),
                        subscriptionEndDate = timezone.now() + timedelta(days=plan.duration + 7),
                        balanceToken = plan.totalToken,
                        fileToken = plan.fileToken,
                        description = "This is Free Plan For Trial Period", 
                        status = "trial", 
                        transactionId = "trial", 
                        payment_status = "trial", 
                        payment_mode = "online",
                        trialStartDate = timezone.now(), 
                        trialEndDate = timezone.now() + timedelta(days=plan.duration),

                        plan_name = plan.plan_name,
                        plan_for = plan.plan_for,
                        amount =  plan.amount,
                        duration = plan.duration,
                        totalToken = plan.totalToken,
                        totalFileToken = plan.fileToken,
                        feature = plan.feature,
                        discount = plan.discount
                    )

                storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage").first()

                # Create Free Storage Plan for New Register User
                if storage_plan:
                    storage = StorageUsage.objects.create(
                        user_id = user.id, 
                        plan_id = storage_plan.id,
                        storage_limit = storage_plan.storage_size,
                        subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                        subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                        description = "This is Free Plan For Trial Period", 
                        status = "trial", 
                        transactionId = "trial", 
                        payment_status = "trial", 
                        payment_mode = "online",

                        plan_name = storage_plan.plan_name,
                        plan_for = storage_plan.plan_for,
                        amount =  storage_plan.amount,
                        duration = storage_plan.duration,
                        feature = storage_plan.feature,
                        discount = storage_plan.discount
                    )

            
            return Response({"userId": user.id, 
                             "referral_code": user.referral_code,
                             "subscriptionId": None if subs is None else subs.id,
                             "storagePlanId": None if storage is None else storage.id,
                             "credential": False if user.credentials is None else True,
                             "clusterId": user.cluster.id if user.cluster else None,
                             "status": "free" if not cluster else "Cluster Linked",
                             "Message": "User created and verification mail sent to user"}, 
                             status=status.HTTP_200_OK
                             )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Resend Verification Link.
class ResendVerification(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        # email = request.data.get('email')
        userId = request.data.get('userId')
        try:
            # validate_email(email)
            # user = CustomUser.objects.filter(email=email,is_delete=False).first()
            user = CustomUser.objects.get(id=userId)
            send_verification_email.delay(user.id)

            return Response({"Message": "Verification Email Resend"}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"Message": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        # except ValidationError:
        #     return Response({"Message": "Please Provide Valid Mail Id"}, status=status.HTTP_400_BAD_REQUEST)

        # if user:            
        #     send_verification_email.delay(user.id)
        #     return Response({"Message": "Email Resend"}, status=status.HTTP_200_OK)
        # else:
        #     return Response({"Message": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        

class LoginByEmailAndPassword(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        userNameOrEmail = request.data.get('userNameOrEmail')
        password = request.data.get('password')
        deviceToken = request.data.get('deviceToken')

        # Check if input is a valid email address
        try:
            validate_email(userNameOrEmail)
            user = CustomUser.objects.filter(email=userNameOrEmail, is_delete=False).first()
        except ValidationError:
            user = CustomUser.objects.filter(username=userNameOrEmail, is_delete=False).first()

        if user:
            # Authenticate user
            user = authenticate(request, id=user.id, password=password, is_delete=False)
            # user = authenticate(request, username=user.username, password=password, is_delete=False)
            # user = authenticate(request, username=user.username, password=password)

            subs= None
            storage = None
            if user is not None:

                if user and (user.is_superuser) and not (user.roles.filter(name='admin').exists()):
                    role, _ = Role.objects.get_or_create(name='admin')
                    user.roles.add(role)

                # if user and user.is_delete:
                #     return Response({'message': 'User Deleted'}, status=status.HTTP_400_BAD_REQUEST)
                
                elif user and user.is_blocked:
                    return Response({'message': 'You are blocked Please Contact to Admin'}, status=status.HTTP_401_UNAUTHORIZED)

                
                elif user and not user.is_verified:
                    send_verification_email.delay(user.id)
                    return Response({'message': 'You are not verified. Verification mail send'}, status=status.HTTP_406_NOT_ACCEPTABLE)


                else:
                    token = user.tokens()
                    roles = [role.name for role in user.roles.all()]

                    # Create Stripe Account if not exist
                    if not user.stripeCustomerId:
                        custId = createCustomerOnStripe(user.username, user.email)
                        if custId:
                            user.stripeCustomerId = custId
                            user.save()    

                    # subscription_status = Subscription.objects.filter(
                    #             user=user.id, status__in=['active', 'expire']
                    #             ).values_list('status', flat=True)
                    # print(subscription_status)
                    
                    # if 'active' in subscription_status:
                    #     userStatus = 'paid'
                    # elif 'expire' in subscription_status:
                    #     userStatus = 'expire'
                    # else:
                    #     userStatus = 'free'     

                    # Get user Subscription status(Paid, Expire or Free)
                    # subscription_status = Subscription.objects.filter(
                    #     user=user.id, status__in=['active', 'expire']
                    # ).values_list('id', 'status')

                    subs = Subscription.objects.filter(user=user.id, is_delete=False).first()
                    storage = StorageUsage.objects.filter(user=user.id, is_delete=False).first()
                    # userStatus = 'free'  # Default status

                    # for subscription in subscription_status:
                    #     if 'active' in subscription:
                    #         userStatus = 'paid'
                    #         subscriptionId = subscription[0]  # Assuming the subscription ID is the first element
                    #         break  # No need to continue checking once active subscription is found
                    #     elif 'expire' in subscription:
                    #         userStatus = 'expire'
                            
                    

                    if deviceToken:
                        user.deviceToken = deviceToken
                        user.save()
          

                    return Response({
                        'userName': user.username,
                        'userId': user.id,
                        "referral_code": user.referral_code,
                        "is_cluster_owner": user.is_cluster_owner,
                        'token': token,
                        'image': user.profile_image,
                        'roles': roles,
                        'customerId': user.stripeCustomerId,
                        "status": 'free' if subs and subs.status == 'trial' else ('active' if subs and subs.status == 'active' else 'expire'),
                        "subscriptionId": None if subs is None else subs.id,
                        "credential": False if user.credentials is None else True,
                        "storagePlanId": None if storage is None else storage.id,
                        "clusterId": user.cluster.id if user.cluster else None,
                        'message': 'Login successful'
                    }, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'error': 'Invalid username/email or password'}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            # User does not exist
            return JsonResponse({'error': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

# def convert_to_number(token):
#     if token.endswith('K'):
#         return float(token[:-1]) * 1000
#     elif token.endswith('M'):
#         return float(token[:-1]) * 1000000
#     elif token.endswith('B'):
#         return float(token[:-1]) * 1000000000
#     elif token.endswith('T'):
#         return float(token[:-1]) * 1000000000000
#     else:
#         return float(token)

# def count_token(textToken, fileToken):
#     textToken = convert_to_number(textToken)
#     fileToken = convert_to_number(fileToken)
#     return textToken, fileToken

    

# Update User.
class UpdateUser(APIView):
    
    def patch(self, request, pk=None):
        email = request.data.get('email')
        username = request.data.get('username')
        textToken = request.data.get('textToken')
        fileToken = request.data.get('fileToken')
        storageLimit = request.data.get('storageLimit')
        storageUsed = request.data.get('storageUsed')
        
        if email:
            user = CustomUser.objects.filter(email=email, is_delete=False).exclude(id=pk).exists()
            if user:
                return Response({"Message": "Email already exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        if username:
            user = CustomUser.objects.filter(username=username, is_delete=False).exclude(id=pk).exists()
            if user:
                return Response({"Message": "Username already exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            subs = Subscription.objects.filter(user=pk, is_delete=False).first()
            storage = StorageUsage.objects.filter(user=pk, is_delete=False).first()
            
            if subs and textToken and fileToken:
                # textTokens, fileTokens = count_token(textToken, fileToken)
                subs.balanceToken = textToken
                subs.fileToken = fileToken
                subs.save()

            if storage and storageLimit and storageUsed:
                storage.total_storage_used = int(storageUsed*1024*1024*1024)
                storage.storage_limit = int(storageLimit*1024*1024*1024)
                storage.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Sent OTP by email to superuser for change user to sub-admin.
class UserToSubAdminOTP(APIView):
    
    def get(self, request, pk=None):       
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        # if user.is_staff:
        #     return Response({"message": "User is Already Sub Admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        email_otp = random.randint(10000, 99999)

        user.email_otp = email_otp
        user.save()
        superuser = CustomUser.objects.filter(is_superuser=True, is_delete=False).first()

        otp_for_user_to_sub_admin.delay(superuser.id, email_otp)

        return Response({"message": "Otp sent at Superadmin email!"}, status=status.HTTP_200_OK)
    

# Change User status from user to sub-admin.
class UserToSubAdmin(APIView):
    
    def post(self, request, pk=None):   
        email_otp = request.data.get('emailOtp')    
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        
        if email_otp == user.email_otp:       
            role, _ = Role.objects.get_or_create(name='user')
            user.roles.remove((role))

            role, _ = Role.objects.get_or_create(name='sub_admin')
            user.roles.add(role)

            user.is_staff = True
            user.email_otp = random.randint(10000, 99999)
            user.save()
            return Response({"message": "Convert User to Sub Admin"}, status=status.HTTP_200_OK)
        return Response({"message": "Otp Mismatch"}, status=status.HTTP_400_BAD_REQUEST)
    

# Change User status from sub-admin to user.
class SubAdminToUserView(APIView):
    
    def post(self, request, pk=None):   
        email_otp = request.data.get('emailOtp')    
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        
        if email_otp == user.email_otp:       
            role, _ = Role.objects.get_or_create(name='sub_admin')
            user.roles.remove((role))

            role, _ = Role.objects.get_or_create(name='user')
            user.roles.add(role)

            user.is_staff = False
            user.email_otp = random.randint(10000, 99999)
            user.save()
            return Response({"message": "Convert Sub Admin To User"}, status=status.HTTP_200_OK)
        return Response({"message": "Otp Mismatch"}, status=status.HTTP_400_BAD_REQUEST)
    
# Sent OTP by email to superuser for change user to sub-admin.
class ClusterUserToAdminOTP(APIView):
    
    def get(self, request, pk=None):      
        clusterId = request.GET.get('clusterId') 
        try:
            cluster_user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "Cluster user Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            cluster_admin = CustomUser.objects.get(cluster=clusterId, is_cluster_owner=True, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "Cluster admin Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        # if user.is_staff:
        #     return Response({"message": "User is Already Sub Admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        email_otp = random.randint(10000, 99999)

        cluster_user.email_otp = email_otp
        cluster_user.save()

        # cluster_admin = CustomUser.objects.filter(cluster=clusterId, is_cluster_owner=True, is_delete=False).first()

        otp_for_user_to_sub_admin.delay(cluster_admin.id, email_otp)

        return Response({"message": "Otp sent at cluster admin email!"}, status=status.HTTP_200_OK)
    
# Change User status from cluster_user to cluster_admin.
class ClusterUserToAdminView(APIView):
    
    def post(self, request, pk=None):   
        email_otp = request.data.get('emailOtp')    
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        
        if str(email_otp) == user.email_otp:       
            role, _ = Role.objects.get_or_create(name='enterprise_user')
            user.roles.remove((role))

            role, _ = Role.objects.get_or_create(name='enterprise_sub_admin')
            user.roles.add(role)

            user.is_staff = False
            user.email_otp = random.randint(10000, 99999)
            user.save()
            return Response({"message": "Convert Cluster User To Cluster Sub-Admin"}, status=status.HTTP_200_OK)
        return Response({"message": "Otp Mismatch"}, status=status.HTTP_400_BAD_REQUEST)
    
# Change User status from cluster_admin to cluster_user.
class ClusterAdminToUserView(APIView):
    
    def post(self, request, pk=None):   
        email_otp = request.data.get('emailOtp')    
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response({"message": "User Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        
        if str(email_otp) == user.email_otp:       
            role, _ = Role.objects.get_or_create(name='enterprise_sub_admin')
            user.roles.remove((role))

            role, _ = Role.objects.get_or_create(name='enterprise_user')
            user.roles.add(role)

            user.is_staff = False
            user.email_otp = random.randint(10000, 99999)
            user.save()
            return Response({"message": "Convert Cluster Sub-Admin To Cluster User"}, status=status.HTTP_200_OK)
        return Response({"message": "Otp Mismatch"}, status=status.HTTP_400_BAD_REQUEST)
    

# Change User status from cluster_admin to cluster_user.
class ChangeUserRole(APIView):
    
    def get(self, request, pk=None):   
        users = CustomUser.objects.filter(is_delete=False, roles__name="enterprise")      

        
        for user in users:
            role = Role.objects.get(name='enterprise')
            user.roles.remove((role))

            role, _ = Role.objects.get_or_create(name='enterprise_admin')
            user.roles.add(role)

            user.save()

        users = CustomUser.objects.filter(is_delete=False, cluster__isnull=False, is_cluster_owner = False ) 

        for user in users:
            role = Role.objects.get(name='user')
            user.roles.remove((role))

            role, _ = Role.objects.get_or_create(name='enterprise_user')
            user.roles.add(role)

            user.save()

        return Response({"message": "Rolls Change Successfully"}, status=status.HTTP_200_OK)


    

class ImageUploadView(APIView):

    def post(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = request.FILES.get('file')

            objectKey = "multinote/user/" + str(int(time.time())) + '-' + file.name

            response = uploadImage(file, objectKey, file.content_type)

            if response is None:                          
                user = CustomUser.objects.get(pk=request.user.id)
                user.profile_image = objectKey
                user.save()
                return Response({
                    'message': 'Image uploaded',
                    'imageKey': objectKey,
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class getImageUrlView(APIView):

    def get(self, request, pk=None):
            
        objKey = request.GET.get('image')

        if objKey and objKey != 'null':
            url = getImageUrl(objKey)
        else:
            return Response({"message": "Please Provide image Url."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ImageUrlSerializer(data={'url': url})

        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        


class EmailVerificationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')

            user = CustomUser.objects.get(pk=user_id)
            user.is_verified = True
            user.is_active = True
            user.save()

            return Response({'message': 'Email verified'}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User Not Found'}, status=status.HTTP_404_NOT_FOUND)
    

class ChangePasswordView(APIView):

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            user.password = make_password(new_password)
            user.save()

            return Response({"message": "Password changed."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = CustomUser.objects.filter(email=serializer.validated_data['email'], is_delete=False).first()
            if user and user.is_blocked:
                return Response({"message": "User has blocked"}, status=status.HTTP_400_BAD_REQUEST)
            
            elif user and not user.is_verified:
                send_verification_email.delay(user.id)
                return Response({"message": "You are not verified. Verification mail sent."}, status=status.HTTP_400_BAD_REQUEST)
            
            elif user:
                sendResetPasswordMail.delay(user.id)

                return Response({"message": "Email Sent to User"}, status=status.HTTP_200_OK)
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):       
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')

            tokenStatus = TokenBlacklist.objects.filter(token=token, user=user_id).exists()
            if tokenStatus:
                return Response({'message': "Link has already been used."}, status=status.HTTP_208_ALREADY_REPORTED)

            user = CustomUser.objects.get(pk=user_id, is_delete=False)
            TokenBlacklist.objects.create(token=token, user_id=user.id)
            user.password = make_password(serializer.validated_data['password'])
            user.save()

            return Response({'message': 'Password Updated'}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    

class GeneratePassword(APIView):
    def post(self, request):       
        password = request.data.get('password')

        if not password:
            return Response({'message': 'Password Require'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user= CustomUser.objects.get(id=request.user.id)
            user.password = make_password(password)
            user.password_generate = True
            user.save()
            return Response({'message': 'Password Updated'}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        
# class GetUser(APIView):
#     pagination_class = PageNumberPagination

#     def get(self, request, pk=None):
#         paginator = self.pagination_class()
#         if pk is not None:
#             try:
#                 user = CustomUser.objects.get(pk=pk, is_delete=False)
#             except CustomUser.DoesNotExist:
#                 return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
            
#             serializer=GetUserSerializer(user, context={'profileImage': True})
#             return Response(serializer.data, status=status.HTTP_200_OK)

#         users = CustomUser.objects.filter(is_delete=False)
#         users = users.order_by('-created_at')
#         page = paginator.paginate_queryset(users, request)
#         serializer = GetUserSerializer(page, many=True, context={'profileImage': True})
#         total_pages = paginator.page.paginator.num_pages
#         response_data = {
#             'total_pages': total_pages,
#             'results': serializer.data
#         }

#         return paginator.get_paginated_response(response_data)
        
class GetUser(APIView):
    def get(self, request, pk=None):
        if pk is not None:
            try:
                user = CustomUser.objects.get(pk=pk, is_delete=False)
            except CustomUser.DoesNotExist:
                return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetUserSerializer(user, context={'profileImage': True})
            # serializer = GetAllUserSerializer(user, context={'profileImage': True})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"message": "Id Require"}, status=status.HTTP_400_BAD_REQUEST)
        
        
class GetAllUsers(APIView):
    pagination_class = PageNumberPagination

    def get(self, request):
        paginator = self.pagination_class()
        userType = request.GET.get('userType')
        searchBy = request.GET.get('searchBy')
        clusterId = request.GET.get('clusterId')
        user_role = request.GET.get('role')
        
        queryset = CustomUser.objects.filter(is_delete=False, is_superuser=False).exclude(
            id=request.user.id)

        if userType == 'free':
            filter_mapping = {
                # 'userName': 'username__icontains',
                # 'email': 'email__icontains',
                'status': 'is_blocked',
            }

            for param, lookup in filter_mapping.items():
                value = request.GET.get(param)
                if value != "null":
                    queryset = queryset.filter(Q(**{lookup: value}))

            if searchBy != "null":
                queryset = queryset.filter(Q(username__icontains=searchBy) | Q(email__icontains=searchBy)) 

            queryset = queryset.exclude(subscription__status__in=['active', 'expire'])

            if clusterId != "null":
                queryset = queryset.filter(cluster=clusterId, is_cluster_owner=False) 

            if user_role == "enterprise":
                queryset = queryset.filter(roles__name__in=['enterprise_admin', 'enterprise_sub_admin', 'enterprise_user']) 
            elif user_role != "null":
                queryset = queryset.filter(roles__name=user_role) 

            queryset = queryset.distinct()

        else:
            filter_mapping = {
                'userType': 'subscription__status',
                # 'userName': 'username__icontains',
                # 'email': 'email__icontains',
                'status': 'is_blocked',
            }

            for param, lookup in filter_mapping.items():
                value = request.GET.get(param)
                if value != "null":
                    queryset = queryset.filter(Q(**{lookup: value}))


            if searchBy != "null":
                queryset = queryset.filter(Q(username__icontains=searchBy) | Q(email__icontains=searchBy))        

            if userType == 'expire':
                queryset = queryset.exclude(subscription__status__in=['active'])
            queryset = queryset.distinct()

            if clusterId != "null":
                queryset = queryset.filter(cluster=clusterId, is_cluster_owner=False) 

            if user_role == "enterprise":
                queryset = queryset.filter(roles__name__in=['enterprise_admin', 'enterprise_sub_admin', 'enterprise_user']) 
            elif user_role != "null":
                queryset = queryset.filter(roles__name=user_role) 

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = GetAllUserSerializer(page, many=True, context={'profileImage': True})
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)


# Delete User.
class DeleteUser(APIView):
    
    def patch(self, request, pk=None):
        try:
            user = CustomUser.objects.get(pk=pk, is_delete=False)
        except CustomUser.DoesNotExist:
            return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = DeleteUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "User Deleted"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Cluster CRUD
class ClusterMngt(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        # userType = request.GET.get('userType')
        data = request.data.copy()
        # data['user'] = request.user.id

        domain = request.data.get("domain")

        if Cluster.objects.filter(domain=domain, is_delete=False).exists():
            return Response({"Message": "Domain with this name already exits."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ClusterSerializer(data=request.data, many=False)
        if serializer.is_valid():
            cluster = serializer.save()

            data['cluster'] = cluster.id
            data['is_cluster_owner'] = True
            data['role'] = "enterprise_admin"

            user_serializer = RegisterSerializer(data=data, many=False)
            if user_serializer.is_valid():
                email = user_serializer.validated_data['email']
                username = user_serializer.validated_data['username']

                emailExist = CustomUser.objects.filter(email=email, is_delete=False).exists()
                nameExist = CustomUser.objects.filter(username=username, is_delete=False).exists()

                if emailExist:
                    cluster.delete()
                    return Response({"Message": "User with this email already exist"}, status=status.HTTP_400_BAD_REQUEST)

                if nameExist:
                    cluster.delete()
                    return Response({"Message": "Username already exist. Please Use Different Name"}, status=status.HTTP_400_BAD_REQUEST)

                user = user_serializer.save()

                send_verification_email.delay(user.id)
                
                token_plan = UserPlan.objects.filter(id=int(data["plan"]), status='active', is_delete=False).first()
                
                # Get the current time in seconds since the epoch
                current_time_seconds = time.time()

                # Convert to an integer or a string if needed
                id_from_time = "TRN-" + str(int(current_time_seconds))
                # Create Trial Subscription for New Regisrer User

                if token_plan and token_plan.plan_for == "token":
                    subs = Subscription.objects.create(
                        user_id = user.id, 
                        plan_id = token_plan.id,
                        subscriptionExpiryDate = timezone.now() + timedelta(days=token_plan.duration),
                        subscriptionEndDate = timezone.now() + timedelta(days=token_plan.duration + 7),
                        balanceToken = token_plan.totalToken,
                        fileToken = token_plan.fileToken,
                        description = "This is Cluster Plan", 
                        status = "active", 
                        transactionId = id_from_time, 
                        payment_status = "paid", 
                        payment_mode = "mannual",

                        plan_name = token_plan.plan_name,
                        plan_for = token_plan.plan_for,
                        amount =  token_plan.amount,
                        duration = token_plan.duration,
                        totalToken = token_plan.totalToken,
                        totalFileToken = token_plan.fileToken,
                        feature = token_plan.feature,
                        discount = token_plan.discount

                        
                    )

                    cluster.subscription = subs
                    cluster.save()

                storage_plan = UserPlan.objects.filter(id=int(data["storage_plan"]), status='active', is_delete=False).first()

                if storage_plan and storage_plan.plan_for == "storage":
                    storage = StorageUsage.objects.create(
                        user_id = user.id, 
                        plan_id = storage_plan.id,
                        storage_limit = storage_plan.storage_size,
                        subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                        subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                        description = "This is Cluster Storage Plan", 
                        status = "active", 
                        transactionId = id_from_time, 
                        payment_status = "paid", 
                        payment_mode = "mannual",

                        plan_name = storage_plan.plan_name,
                        plan_for = storage_plan.plan_for,
                        amount =  storage_plan.amount,
                        duration = storage_plan.duration,
                        feature = storage_plan.feature,
                        discount = storage_plan.discount
                        )
                    
                    cluster.storage = storage
                    cluster.save()
                    
                return Response({"cluster": serializer.data, "userId": user.id, "userName": user.username, "message": "Cluster and User Created Successfully"}, status=status.HTTP_200_OK)
            cluster.delete()
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        cluster_status = request.GET.get('status')
        if pk is not None:
            try:
                cluster = Cluster.objects.get(pk=pk, is_delete=False)
            except Cluster.DoesNotExist:
                return Response({"message": "Cluster Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ClusterOutputSerializer(cluster)
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = Cluster.objects.filter(is_delete=False)

        if searchBy:
            queryset = queryset.filter(
                Q(cluster_name__icontains=searchBy) | 
                Q(email__icontains=searchBy) |
                Q(org_name__icontains=searchBy) |
                Q(domain__icontains=searchBy))
            
        if cluster_status:
            queryset = queryset.filter(is_enabled=cluster_status)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = ClusterOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        planId = request.data.get('plan', None)
        storagePlanId = request.data.get('storage_plan', None)
        is_active = request.data.get('is_enabled', None)

        if not is_active and CustomUser.objects.filter(cluster=pk, is_cluster_owner=False, is_delete=False).exists():
            return Response({"message": "Cluster user exits so you can't deactivate/delete cluster"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cluster = Cluster.objects.get(pk=pk, is_delete=False)
        except Cluster.DoesNotExist:
            return Response({"message": "Cluster Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        existingPlanId = cluster.plan.id
        existingStoragePlanId = cluster.storage_plan.id
        serializer = ClusterSerializer(cluster, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if existingPlanId != planId:
                plan = UserPlan.objects.filter(id=planId, status='active', is_delete=False).first()

                if plan and plan.plan_for == "token":
                    subs = Subscription.objects.filter(id=cluster.subscription.id).first()
                    if subs:
                        subs.plan = plan
                        subs.subscriptionExpiryDate = timezone.now() + timedelta(days=plan.duration)
                        subs.subscriptionEndDate = timezone.now() + timedelta(days=plan.duration + 7)
                        subs.balanceToken = plan.totalToken
                        subs.fileToken = plan.fileToken
                        subs.status = "active"
                        subs.payment_status = "paid"
                        subs.payment_mode = "mannual"

                        subs.plan_name = plan.plan_name
                        subs.plan_for = plan.plan_for
                        subs.amount =  plan.amount
                        subs.duration = plan.duration
                        subs.totalToken = plan.totalToken
                        subs.totalFileToken = plan.fileToken
                        subs.feature = plan.feature
                        subs.discount = plan.discount
                        

                        subs.save()

            if existingStoragePlanId != storagePlanId:
                storagePlan = UserPlan.objects.filter(id=storagePlanId, status='active', is_delete=False).first()
                if storagePlan and storagePlan.plan_for == "storage":
                    storage = StorageUsage.objects.filter(id=cluster.storage.id).first()
                    if storage:
                        storage.plan = storagePlan
                        storage.storage_limit = storagePlan.storage_size
                        storage.subscriptionExpiryDate = timezone.now() + timedelta(days=storagePlan.duration)
                        storage.subscriptionEndDate = timezone.now() + timedelta(days=storagePlan.duration + 7)
                        storage.status = "active"
                        storage.payment_status = "paid"
                        storage.payment_mode = "mannual"

                        storage.plan_name = storagePlan.plan_name
                        storage.plan_for = storagePlan.plan_for
                        storage.amount =  storagePlan.amount
                        storage.duration = storagePlan.duration
                        storage.feature = storagePlan.feature
                        storage.discount = storagePlan.discount
                        
                        storage.save()
                    

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "Cluster Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "Cluster Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Admin Referral Management
class ReferralMngt(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        # data = request.data.copy()
        # data['user'] = request.user.id

        is_token = request.data.get("isToken")
        is_storage = request.data.get("isStorage")
        is_first_payment = request.data.get("isFirstPayment")
        
        if is_token and ReferralSetting.objects.filter(isToken=is_token, is_delete=False).exists():
            return Response({"message": "Token Setting already available"}, status=status.HTTP_400_BAD_REQUEST)
        
        if is_storage and ReferralSetting.objects.filter(isStorage=is_storage, is_delete=False).exists():
            return Response({"message": "Storage Setting already available"}, status=status.HTTP_400_BAD_REQUEST)
        
        if is_first_payment and ReferralSetting.objects.filter(isFirstPayment=is_first_payment, is_delete=False).exists():
            return Response({"message": "Payment Setting already available"}, status=status.HTTP_400_BAD_REQUEST)
        

        serializer = ReferralInputSerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                referral = ReferralSetting.objects.get(pk=pk, is_delete=False)
            except ReferralSetting.DoesNotExist:
                return Response({"message": "Referral Setting Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ReferralOutputSerializer(referral)
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = ReferralSetting.objects.filter(is_delete=False)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = ReferralOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            referral = ReferralSetting.objects.get(pk=pk, is_delete=False)
        except ReferralSetting.DoesNotExist:
            return Response({"message": "Referral Setting Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ReferralInputSerializer(referral, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "Referral Setting Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "Referral Setting Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Admin Referral Management
class UserReferralView(APIView):
    pagination_class = PageNumberPagination

    def get(self, request):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')

        queryset = Referral.objects.filter(referr_by=request.user.id, is_delete=False)
        if searchBy:
            queryset = queryset.filter(Q(referr_to__username__icontains=searchBy)|
                            Q(referr_to__email__icontains=searchBy))

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = ReferralSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)