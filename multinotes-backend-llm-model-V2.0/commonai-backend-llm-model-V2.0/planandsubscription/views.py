from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (AddPlanSerializer, GetPlanSerializer,
                          UpdatePlanSerializer, GetSubscriptionSerializer,
                          CreateSubscriptionSerializer, UpdateSubscriptionSerializer,
                          CreateTransactionSerializer, GetTransactionSerializer, 
                          UpdateTransactionSerializer, GetUserPlanSerializer
                          )
from coreapp.serializers import LatestTransactionSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from rest_framework.renderers import JSONRenderer
from authentication.models import CustomUser, Referral, ReferralSetting
from .models import UserPlan, Subscription, Transaction
from rest_framework.pagination import PageNumberPagination
from authentication.awsservice import uploadImage
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
import boto3
import time
import jwt
import os


# Perform the search query using the __contains lookup
# results = YourModel.objects.filter(name__contains=search_query)

# Create Plan.
class AddPlan(APIView):
    def post(self, request):
        data = request.data.copy()
        storageSize = request.data.get('storage_size', None)
        plan_name = request.data.get('plan_name')
        is_free = request.data.get('is_free')
        plan_for = request.data.get('plan_for')

        if is_free and plan_for=='token':
            if UserPlan.objects.filter(is_free=is_free, is_delete=False, plan_for='token').exists():
                return Response({"message": "Free token plan already exist"}, status=status.HTTP_400_BAD_REQUEST)
            
        if is_free and plan_for=='storage':
            if UserPlan.objects.filter(is_free=is_free, is_delete=False, plan_for='storage').exists():
                return Response({"message": "Free storage plan already exist"}, status=status.HTTP_400_BAD_REQUEST)

        plan = UserPlan.objects.filter(plan_name=plan_name, is_delete=False).exists()
        if plan:
            return Response({"message": "Plan already exist"}, status=status.HTTP_400_BAD_REQUEST)
        

        if storageSize:
            data['storage_size'] = int(storageSize)*1024*1024*1024  # Convert GB into Byte
            
        serializer = AddPlanSerializer(data=data)

        if serializer.is_valid():
            serializer.save()


            detail = serializer.data
            new_detail = detail.copy()

            new_detail['storage_size'] = detail['storage_size']/(1024*1024*1024)
            
            
            return Response(new_detail, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get Plan
class GetPlan(APIView):
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()

        statusType = request.GET.get('status')
        searchBy = request.GET.get('searchBy')
        planType = request.GET.get('planType')
        userType = request.GET.get('userType')
        admin = request.GET.get('admin', 'true')

        admin_bool = admin.lower() == "true"

        # print(admin_bool, type(admin_bool))

        if pk is not None:
            try:
                plan = UserPlan.objects.get(pk=pk, is_delete=False)
            except UserPlan.DoesNotExist:
                return Response("Plan Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetPlanSerializer(plan)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
        # print(request.token)
        # try:
            # roles = [role.name for role in request.user.roles.all()]
        plans = UserPlan.objects.filter(is_delete=False)
        # except AttributeError:
            # plans = UserPlan.objects.filter(is_delete=False,  status='active')

        # plans = UserPlan.objects.filter(is_delete=False, description__contains='image') # contains mean case Senstive
        # plans = UserPlan.objects.filter(is_delete=False, description__icontains='image')  # icontains mean case Insenstive
            
        if searchBy != 'null':
            plans = plans.filter(plan_name__icontains=searchBy)

        if statusType != 'null':
            plans = plans.filter(status=statusType)

        
        # if userType == 'user' and admin=='false':
        #     plans = plans.filter(is_for_cluster= False, status='active')
        #     # if planType == 'user':
        #     #     plans = plans.filter(status='active')
        
        if userType == 'user':
            plans = plans.filter(is_for_cluster= False)


        elif userType == 'cluster':
            plans = plans.filter(is_for_cluster= True)


        if planType != 'null':
            plans = plans.filter(plan_for= planType)

        plans = plans.order_by('-created_at')
        
        if userType == 'user' and not admin_bool:
            # plans = plans.filter(is_free=False)
            serializer = GetUserPlanSerializer(plans, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            page = paginator.paginate_queryset(plans, request)
            serializer = GetPlanSerializer(page, many=True)
            total_pages = paginator.page.paginator.num_pages
            response_data = {
                'total_pages': total_pages,
                'results': serializer.data
            }

            return paginator.get_paginated_response(response_data)
        

# Update Plan.
class UpdatePlan(APIView):
    
    def patch(self, request, pk=None):
        data = request.data.copy()
        plan_name = request.data.get('plan_name')
        storageSize = request.data.get('storage_size')

        if plan_name:
            plan = UserPlan.objects.filter(plan_name=plan_name, is_delete=False).exclude(id=pk).exists()
            if plan:
                return Response({"Message": "Plan already exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = UserPlan.objects.get(pk=pk, is_delete=False)
        except UserPlan.DoesNotExist:
            return Response("Plan Not Found", status=status.HTTP_404_NOT_FOUND)
        
        if storageSize:
            data['storage_size'] = int(storageSize)*1024*1024*1024  # Convert GB into Byte
        
        serializer = UpdatePlanSerializer(plan, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Plan.
class DeletePlan(APIView):
    
    def patch(self, request, pk=None):
        try:
            plan = UserPlan.objects.get(pk=pk, is_delete=False)
        except UserPlan.DoesNotExist:
            return Response("Plan Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdatePlanSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Plan Delete"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Create Subscription
class CreateSubscription(APIView):

    def post(self, request):

        transactionId = request.data.get('transactionId')
        payment_status = request.data.get('payment_status')
        planId = request.data.get('plan')
        coupon_code = request.data.get('couponCode', None)
        coupon_type = request.data.get('couponType', None)
        discount_value = request.data.get('discountValue', None)
        bonus_token = request.data.get('bonusToken', 0)
        
        try:
            transaction = Transaction.objects.get(transactionId=transactionId)
            # print(transaction.id)
        except Transaction.DoesNotExist:
            return Response("No Such Payment Exist", status=status.HTTP_404_NOT_FOUND)
        
        plan = UserPlan.objects.filter(id=planId, is_delete=False, status='active').first()

        if not plan:
            return Response("No Such Plan Exist", status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        subscriptionExpiryDate = timezone.now() + timedelta(days=plan.duration)
        subscriptionEndDate = timezone.now() + timedelta(days=plan.duration + 7)

        # user = CustomUser.objects.get(id=request.user.id)

        subs = Subscription.objects.filter(user=request.user.id, is_delete=False).first()
        if subs:
            # balanceToken = subs.balanceToken + plan.totalToken
            if subs.subscriptionEndDate < timezone.now():
                expireToken = subs.expireToken + subs.balanceToken if subs.balanceToken > 0 else subs.expireToken

                expireFileToken = subs.expireFileToken + subs.fileToken

                balanceToken = plan.totalToken if subs.balanceToken > 0 else plan.totalToken + subs.balanceToken

                fileToken = plan.fileToken

            elif subs.plan.is_free:
                expireToken = subs.expireToken + subs.balanceToken if subs.balanceToken > 0 else subs.expireToken

                expireFileToken = subs.expireFileToken + subs.fileToken

                balanceToken = plan.totalToken if subs.balanceToken > 0 else plan.totalToken + subs.balanceToken

                fileToken = plan.fileToken

            else:
                expireToken = subs.expireToken
                balanceToken = subs.balanceToken + plan.totalToken
                fileToken = subs.fileToken + plan.fileToken
                expireFileToken = subs.expireFileToken
                
            new_data = {
                "subscriptionExpiryDate": subscriptionExpiryDate,
                "subscriptionEndDate": subscriptionEndDate,
                "status": 'active',
                "transactionId": transactionId,
                "balanceToken": balanceToken + int(bonus_token),
                "expireToken": expireToken,
                "fileToken": fileToken,
                "payment_status": payment_status,
                "expireFileToken": expireFileToken,
                "plan": plan.id,
                # "usedToken": 0,
                # "usedFileToken": 0,

                "plan_name": plan.plan_name,
                "plan_for": plan.plan_for,
                "amount": plan.amount,
                "duration": plan.duration,
                "totalToken": plan.totalToken,
                "totalFileToken": plan.fileToken,
                "feature": plan.feature,
                "discount": plan.discount,

                "coupon_code": coupon_code,
                "coupon_type": coupon_type,
                "discount_value":discount_value,
                "bonus_token": bonus_token
            }

            serializer = CreateSubscriptionSerializer(subs, data=new_data, partial=True)
            
            if serializer.is_valid():
                updated_subs = serializer.save()

                # Fetch the first referral matching the criteria, if any
                referral = Referral.objects.filter(
                    referr_to= request.user.id, 
                    reward_given= False,
                    is_delete= False
                ).first()

                if referral:
                    # Fetch the first token detail if any
                    # token_detail = ReferralSetting.objects.filter(
                    #     isToken=True, 
                    #     is_delete=False
                    # ).first()

                    # if token_detail:
                        # Check if there are any active subscriptions for the referrer
                    
                    final_token = updated_subs.balanceToken + referral.refer_to_token
                    updated_subs.balanceToken = final_token
                    # updated_subs.balanceToken += referral.refer_to_token
                    updated_subs.save()

                    refer_subs = Subscription.objects.filter(
                        user=referral.referr_by.id,
                        status__in= ["active", "trial"],
                        is_delete= False
                    ).first()


                    if refer_subs:
                        refer_subs.balanceToken += referral.refer_by_token
                        refer_subs.save()
                        
                        referral.reward_given = True
                        referral.save()



                trans_data = {
                    "payment_status": payment_status,
                    "subscription_id": subs.id
                }
                trans_serializer = UpdateTransactionSerializer(transaction, data=trans_data, partial=True)

                if trans_serializer.is_valid():
                    trans_serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # transaction.payment_status = payment_status
                # transaction.subscription_id = subs.id
                # transaction.save()

                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            data['user'] = request.user.id
            data['subscriptionExpiryDate'] = subscriptionExpiryDate
            data['subscriptionEndDate'] = subscriptionEndDate
            data['balanceToken'] = plan.totalToken + int(bonus_token)
            data['fileToken'] = plan.fileToken
            data['payment_mode'] = 'online'

            data["plan_name"] = plan.plan_name
            data["plan_for"] = plan.plan_for
            data["amount"] = plan.amount
            data["duration"] = plan.duration
            data["totalToken"] = plan.totalToken
            data["totalFileToken"] = plan.fileToken
            data["feature"] = plan.feature
            data["discount"] = plan.discount

            data["coupon_code"] = coupon_code
            data["coupon_type"] = coupon_type
            data["discount_value"] = discount_value
            data["bonus_token"] = bonus_token

            serializer = CreateSubscriptionSerializer(data=data, many=False)

            if serializer.is_valid():
                payment_status = serializer.validated_data.get('payment_status')
                user_subscript = serializer.save()

                # Fetch the first referral matching the criteria, if any
                referral = Referral.objects.filter(
                    referr_to= request.user.id, 
                    reward_given= False,
                    is_delete= False
                ).first()

                if referral:
                    # Fetch the first token detail if any
                    token_detail = ReferralSetting.objects.filter(isToken=True, is_delete=False).first()

                    if token_detail:
                        # Check if there are any active subscriptions for the referrer
                        user_subscript.balanceToken += token_detail.refer_to_token

                        refer_subs = Subscription.objects.filter(
                            user=referral.referr_by.id,
                            status__in= ["active", "trial"],
                            is_delete= False
                        )

                        if refer_subs:
                            refer_subs.balanceToken += token_detail.refer_by_token
                            refer_subs.save()
                            
                            referral.reward_given = True
                            referral.save()
                            

                trans_data = {
                    "payment_status": payment_status,
                    "subscription_id": user_subscript.id
                }
                trans_serializer = UpdateTransactionSerializer(transaction, data=trans_data, partial=True)

                if trans_serializer.is_valid():
                    trans_serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # transaction.payment_status = payment_status
                # transaction.subscription_id = user_subscript.id
                # transaction.save()
            
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get Subscription
class GetSubscription(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        if pk is not None:
            try:
                subscription = Subscription.objects.get(pk=pk, is_delete=False)
            except Subscription.DoesNotExist:
                return Response("Subscription Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetSubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
        subscription = Subscription.objects.filter(is_delete=False)
        subscription = subscription.order_by('-created_at')
        page = paginator.paginate_queryset(subscription, request)
        serializer = GetSubscriptionSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)


# Update Subscription
class UpdateSubscription(APIView):
    
    def patch(self, request, pk=None):
        try:
            subscription = Subscription.objects.get(pk=pk, is_delete=False)
        except Subscription.DoesNotExist:
            return Response("Subbcription Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateSubscriptionSerializer(subscription, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Subscription
class DeleteSubscription(APIView):
    
    def patch(self, request, pk=None):
        try:
            subscription = Subscription.objects.get(pk=pk, is_delete=False)
        except Subscription.DoesNotExist:
            return Response("Subscription Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateSubscriptionSerializer(subscription, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Subscription Delete"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Create Transaction
class CreateTransaction(APIView):

    def post(self, request):

        # planId = request.data.get('plan')
        # try:
        #     Transaction = Transaction.objects.get(id=planId)
        # except Transaction.DoesNotExist:
        #     return Response("No Such Plan Exist", status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        # data['end_time'] = timezone.now() + timedelta(days=plan.duration)
        data['user'] = request.user.id

        serializer = CreateTransactionSerializer(data=data, many=False)

        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get Transaction
class GetTransaction(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        if pk is not None:
            try:
                transaction = Transaction.objects.get(pk=pk, is_delete=False)
                
            except Transaction.DoesNotExist:
                return Response("Transaction Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetTransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
        transaction = Transaction.objects.filter(is_delete=False)

        if searchBy != "null":
            transaction = transaction.filter(
                Q(user__username__icontains=searchBy) | 
                Q(user__email__icontains=searchBy) |
                Q(plan_name__icontains=searchBy)
            ) 

        # if searchBy != 'null':
        #     transaction = transaction.filter(transactionId__icontains=searchBy)

        transaction = transaction.order_by('-created_at')
        page = paginator.paginate_queryset(transaction, request)
        serializer = LatestTransactionSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)


# Update Transaction
class UpdateTransaction(APIView):
    
    def patch(self, request, pk=None):
        try:
            transaction = Transaction.objects.get(pk=pk, is_delete=False)
        except Transaction.DoesNotExist:
            return Response("Transaction Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateTransactionSerializer(transaction, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Transaction
class DeleteTransaction(APIView):
    
    def patch(self, request, pk=None):
        try:
            transaction = Transaction.objects.get(pk=pk, is_delete=False)
        except Transaction.DoesNotExist:
            return Response("Transaction Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateTransactionSerializer(transaction, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Transaction Delete"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


