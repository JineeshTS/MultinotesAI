from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from planandsubscription.models import UserPlan, Subscription, Transaction
import stripe
import os
import datetime
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.permissions import BasePermission
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from rest_framework import status
from django.db.models import Q
from .serializers import (GenerateCardTokenSerializer, UpdateCardSerializer
                        )

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def createCustomerOnStripe(userName, email):
    cardDetail = stripe.Customer.create(
        name = userName,
        email = email
    )
    return cardDetail.id

class CreatePaymentIntent(APIView):
    def post(self, request):
        amount = request.data.get('amount')
        userName = request.data.get('userName')
        planId = request.data.get('planId')
        line1 = request.data.get('line1', "")
        line2 = request.data.get('line2', "")
        postalCode = request.data.get('postalCode', "")
        city = request.data.get('city', "")
        state = request.data.get('state', "")
        country = request.data.get('country')
        amount_in_cent = int(amount * 100)
        # customerId = request.data.get('customerId') 
        if not amount or not userName or not country or not planId:
            return Response({'message': 'Amount, Username, County And PlanId Require.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            intent = stripe.PaymentIntent.create(
                receipt_email = request.user.email,
                amount = amount_in_cent,
                currency = 'usd',
                customer = request.user.stripeCustomerId,
                description = "Plan Subscription Payment",
                # automatic_payment_methods= {"enabled": True, "allow_redirects": "never"}
                automatic_payment_methods = {"enabled": True},
                # payment_method_types = ['card']
                shipping = {
                    "name": userName ,
                    "address": {
                        "line1": line1,
                        "line2": line2,
                        "postal_code": postalCode,
                        "city": city,
                        "state": state,
                        "country": country,
                    },
                },
            )

            plan = UserPlan.objects.get(id=planId)
            Transaction.objects.create(
                user_id=request.user.id, 
                transactionId= intent.id, 
                amount= intent.amount/100,
                plan_name= plan.plan_name,
                duration = plan.duration,
                tokenCount = plan.totalToken,
                fileToken = plan.fileToken,
                payment_method=intent.payment_method_types[0]
            )
            return Response({'client_secret': intent.client_secret})
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
# class AddCustomer(APIView):
#     # permission_classes = [AllowAny]
#     def post(self, request):
#         userName = request.data.get('name') 
#         userEmail = request.data.get('email') 

#         try:
#             intent = stripe.Customer.create(
#                 name = userName,
#                 email = userEmail,
#             )
#             return Response(intent)
#         except Exception as e:
#             return Response({'error': str(e)}, status=500)
        
        
class AddCard(APIView):
    def post(self, request):
        custId = request.data.get('customerId') 
        token = request.data.get('token') 

        if not custId or not token:
            return Response({'message': 'CustomerId And Token Require.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cardDetail = stripe.Customer.create_source(
                custId,
                source = token,
                # source = "tok_visa",
                )
            return Response(cardDetail, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
class GetCards(APIView):
    def get(self, request):
        custId = request.GET.get('customerId') 
        if not custId:
            return Response({'message': 'CustomerId Require.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cardDetails = stripe.Customer.list_sources(
                custId,
                object = "card",
                limit = 20
                )
            return Response(cardDetails, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
        
class UpdateCard(APIView):
    def patch(self, request):

        serializer = UpdateCardSerializer(data=request.data)

        if serializer.is_valid():
            custId = serializer.validated_data.get('customerId')
            cardId = serializer.validated_data.get('cardId')
            # name = serializer.validated_data.get('name')
            expYear = serializer.validated_data.get('expYear')
            expMonth = serializer.validated_data.get('expMonth')

        try:
            cardDetail = stripe.Customer.modify_source(
                custId,
                cardId,
                # name = name,
                exp_year = expYear,
                exp_month = expMonth
            )
            return Response(cardDetail, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
        
class DeleteCard(APIView):
    def delete(self, request):
        custId = request.data.get('customerId') 
        cardId = request.data.get('cardId') 

        if not custId or not cardId:
            return Response({'message': 'CustomerId And CardId Require.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cardDetail = stripe.Customer.delete_source(
                custId,
                cardId,
            )
            return Response(cardDetail, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
        
class GetCustomerDetails(APIView):
    def get(self, request, custId):

        try:
            cardDetail = stripe.Customer.retrieve(custId)
            return Response(cardDetail, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
        
class MarkCardDefault(APIView):
    def patch(self, request):
        custId = request.data.get('customerId') 
        cardId = request.data.get('cardId') 

        try:
            cardDetail = stripe.Customer.modify(
                custId,
                default_source = cardId
            )
            return Response(cardDetail, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
## We generate card Token by direct hit stripe api in browser. Not save card detail in own database.       
class GenerateCardToken(APIView):
    def post(self, request):
        serializer = GenerateCardTokenSerializer(data=request.data)

        if serializer.is_valid():
            cardNumber = serializer.validated_data.get('cardNumber')
            expYear = serializer.validated_data.get('expYear')
            expMonth = serializer.validated_data.get('expMonth')
            cvc = serializer.validated_data.get('cvc')
            try:
                token = stripe.Token.create(
                        card={
                            # "name": cardName,
                            "number": cardNumber,
                            "exp_month": expMonth,
                            "exp_year": expYear,
                            "cvc": cvc,
                        },
                    )
                return Response(token, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class MakePayment(APIView):
    def post(self, request):
        custId = request.data.get('customerId') 
        cardId = request.data.get('cardId') 
        amount = request.data.get('amount') 

        try:
            intent = stripe.Charge.create(
                # receipt_email = "anils.rana97@gmail.com",
                amount = amount,
                currency = "usd",
                customer = custId,
                description = 'Monthly Subscription Payment',
                # card = cardId
                # source = cardId,
                )
            return Response(intent)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


def createChargesOnStripe(data):
    intent = stripe.Charge.create(
        amount = data["amount"],
        currency = data["currency"],
        customer = data["customer"],
        description = data["description"]
    )
    return intent
        
def subscriptions():
# def subscriptions(request):
    subscriptions = Subscription.objects.filter(is_delete=0, isSubscribe=True)
    # subscriptions = subscriptions.filter(Q(subscriptionExpiryDate__lte=timezone.now()) | Q(balanceToken__lte=100))

    for subscrip in subscriptions:
        if subscrip.subscriptionExpiryDate <= timezone.now() or subscrip.balanceToken <= 100:
            chargesObj = {
                "amount": int((subscrip.plan.amount) * 100),
                "currency": "usd",
                "customer": subscrip.user.stripeCustomerId,
                "description": 'Monthly Subscription Payment'
            }
            paymentResponse = createChargesOnStripe(chargesObj)
            if paymentResponse and paymentResponse.id:
                nextSubsDate = subscrip.subscriptionExpiryDate + timedelta(days=subscrip.plan.duration)
                planEndDate = subscrip.subscriptionExpiryDate + timedelta(days=subscrip.plan.duration + 7)
                subscrip.subscriptionExpiryDate = nextSubsDate
                subscrip.subscriptionEndDate = planEndDate
                subscrip.balanceToken += subscrip.plan.totalToken
                subscrip.fileToken += subscrip.plan.fileToken
                subscrip.save()
                # return HttpResponse(paymentResponse.id, status=200)
    # return HttpResponse("No Subscription Found", status=200)
    print(f"** Crone Job Run at {timezone.now()}")
        







