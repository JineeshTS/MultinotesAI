from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from planandsubscription.models import Subscription
from rest_framework.permissions import BasePermission
from django.utils import timezone
from datetime import date
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from authentication.models import CustomUser


def decode_jwt_token(token):
    try:
        # Decode the JWT token
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        # print(decoded_token)
        user_id = decoded_token.get('user_id')

        # Return the decoded token (user information)
        return user_id
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token')

class TextSubscriptionAuth(BasePermission):
    message = "You do not have an active subscription or your token has finished."
    
    def has_permission(self, request, view):
        # Extract JWT token from the request
        token = request.headers.get('Authorization').split()[1]
        
        # Implement your JWT decoding logic here
        userId = decode_jwt_token(token)  # Replace with your JWT decoding logic

        user = CustomUser.objects.get(id=userId)

        cluster = user.cluster
        if cluster:
            cluster_user_id = cluster.subscription.user.id
            subscription = Subscription.objects.filter(user=cluster_user_id, status__in=['active', 'trial'], subscriptionExpiryDate__gte=timezone.now(), balanceToken__gt=100).exists()
        else:
            subscription = Subscription.objects.filter(user=userId, status__in=['active', 'trial'], subscriptionExpiryDate__gte=timezone.now(), balanceToken__gt=100).exists()

        if not subscription:
                raise PermissionDenied(self.message)

        return True

        # if subscription:
        #     return True
        # else:
        #     return False #raise AuthenticationFailed('No subscription found')
    

class FileSubscriptionAuth(BasePermission):
    message = "You do not have an active subscription or your token has finished."

    def has_permission(self, request, view):
        # Extract JWT token from the request
        token = request.headers.get('Authorization').split()[1]
        
        # Implement your JWT decoding logic here
        userId = decode_jwt_token(token)  # Replace with your JWT decoding logic

        user = CustomUser.objects.get(id=userId)

        cluster = user.cluster
        if cluster:
            cluster_user_id = cluster.subscription.user.id
            subscription = Subscription.objects.filter(user=cluster_user_id, status__in=['active', 'trial'], subscriptionExpiryDate__gte=timezone.now(), balanceToken__gt=100).exists()
        else:
            subscription = Subscription.objects.filter(user=userId, status__in=['active', 'trial'], subscriptionExpiryDate__gte=timezone.now(), fileToken__gt=1).exists()

        if not subscription:
                raise PermissionDenied(self.message)

        return True

