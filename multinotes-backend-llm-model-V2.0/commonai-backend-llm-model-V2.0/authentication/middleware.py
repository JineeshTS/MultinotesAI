import os
from rest_framework.exceptions import AuthenticationFailed
# from rest_framework.authentication import BaseAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework_simplejwt.authentication import JWTAuthentication
import base64
from django.http import JsonResponse
from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from .models import CustomUser
from django.conf import settings
from django.db.models import Q
import jwt


class CustomMiddleware():
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request):
        # Check if the request URL matches the API for which you want to apply middleware
        if 'v1' in request.path:
            # Get the basic token from the Authorization header
            auth = request.headers.get('Authorization')

            if not auth:
                return JsonResponse({'message': 'Authorization header is Missing'}, status=status.HTTP_400_BAD_REQUEST) 
                    
            try:
                # Extract the token from the Authorization header
                _, token = auth.split()

                decoded_bytes = base64.b64decode(token)
                decoded_string = decoded_bytes.decode('utf-8')
                username, password = decoded_string.split(':')

                if username == os.getenv('BASIC_AUTH_USERNAME') and password == os.getenv('BASIC_AUTH_PASSWORD'):
                    pass
                else:
                    return JsonResponse({'message': 'Invalid basic token'}, status=status.HTTP_400_BAD_REQUEST) 

            except ValueError:
                return JsonResponse({'message':'Invalid authorization header format'}, status=status.HTTP_400_BAD_REQUEST)
            

        # Pass the request to the next middleware or view
        response = await self.get_response(request)

        return response


class CheckUserStatus():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the basic token from the Authorization header
        auth = request.headers.get('Authorization')

        if auth:     
            try:          
                # Extract the token from the Authorization header
                _, token = auth.split()

                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                userId = payload.get('user_id')


                # blck_user = CustomUser.objects.filter(Q(id=userId) & (Q(is_blocked=True) | Q(is_delete=True))).exists()
                
                if CustomUser.objects.filter(id=userId, is_blocked=True).exists():
                    return JsonResponse({'message': 'Your account has blocked by Admin, please contact at test@gmail.com for support'}, status=status.HTTP_401_UNAUTHORIZED)
                
                if CustomUser.objects.filter(id=userId, is_delete=True).exists():
                    return JsonResponse({'message': 'Account Deleted!'}, status=status.HTTP_401_UNAUTHORIZED)

                # if user:
                #     return JsonResponse({'message': 'Your account has blocked by Admin, please contact at test@gmail.com for support'}, status=status.HTTP_400_BAD_REQUEST)
            except jwt.ExpiredSignatureError:
                return JsonResponse({'message': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)
            except jwt.InvalidSignatureError:
                return JsonResponse({'message': 'Token Signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)
            except jwt.InvalidTokenError:
                return JsonResponse({'message': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        # Pass the request to the next middleware or view
        response = self.get_response(request)

        return response
    




