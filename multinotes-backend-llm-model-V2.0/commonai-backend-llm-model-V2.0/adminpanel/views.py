from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from authentication.models import CustomUser
from rest_framework.permissions import IsAdminUser
from .serilizers import UserListSerializer, SingleUserSerializer
from rest_framework.response import Response
from django.conf import settings
import datetime
# Create your views here.

class UserListView(ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = CustomUser.objects.filter(roles__name__contains='user')
    serializer_class = UserListSerializer

    def get(self,request):
        try:
          id = request.GET.get('id')
          if id is not None:
               user = CustomUser.objects.get(pk=id)
               serializer = SingleUserSerializer(user) 
               return Response({'payload':serializer.data,'message':'success','status':200 })
          else:
                 return super().list(request)
        except CustomUser.DoesNotExist:
            return Response({'error':'User not found','status':404})
        except Exception as e:
            return Response({'error':str(e),'status':400})
        
    
    def patch(self,request):
        try:
            user_id = request.data.get('id')
            if user_id is None:
                return Response({
                'status':400,
                'message':"user id is needed"
            })
            user = CustomUser.objects.get(pk=user_id)
            user.is_blocked = not user.is_blocked  
            user.save()

            return Response({
                'status': 200,
                'message': f'Successfully {"unblocked" if user.is_blocked else "blocked"} the user'
            })            
        except CustomUser.DoesNotExist:
            return Response({
                'status':404,
                'error':'User not found'
            })
        except Exception as e:
            return Response({
                'status':400,
                'error': str(e)
            })



