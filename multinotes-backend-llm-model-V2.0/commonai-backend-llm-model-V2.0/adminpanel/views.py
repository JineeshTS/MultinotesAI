from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from authentication.models import CustomUser
from rest_framework.permissions import IsAdminUser
from .serializers import UserListSerializer, SingleUserSerializer
from rest_framework.response import Response
from django.conf import settings
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import datetime


class DashboardStatsView(APIView):
    """Admin dashboard statistics endpoint."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            from planandsubscription.models import Subscription, Transaction
            from coreapp.models import Prompt, PromptResponse

            now = timezone.now()
            today = now.date()
            thirty_days_ago = today - timedelta(days=30)
            seven_days_ago = today - timedelta(days=7)

            # User stats
            total_users = CustomUser.objects.filter(is_active=True).count()
            new_users_30d = CustomUser.objects.filter(
                date_joined__gte=thirty_days_ago
            ).count()
            new_users_7d = CustomUser.objects.filter(
                date_joined__gte=seven_days_ago
            ).count()

            # Subscription stats
            active_subscriptions = Subscription.objects.filter(
                status='active',
                is_delete=False
            ).count()

            # Revenue stats
            revenue_30d = Transaction.objects.filter(
                payment_status='paid',
                created_at__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Usage stats
            prompts_30d = Prompt.objects.filter(
                created_at__gte=thirty_days_ago,
                is_delete=False
            ).count()

            responses_30d = PromptResponse.objects.filter(
                created_at__gte=thirty_days_ago,
                is_delete=False
            ).count()

            tokens_used_30d = PromptResponse.objects.filter(
                created_at__gte=thirty_days_ago,
                is_delete=False
            ).aggregate(total=Sum('tokenUsed'))['total'] or 0

            # Daily signups for chart
            daily_signups = CustomUser.objects.filter(
                date_joined__gte=thirty_days_ago
            ).annotate(
                date=TruncDate('date_joined')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')

            # Daily revenue for chart
            daily_revenue = Transaction.objects.filter(
                payment_status='paid',
                created_at__gte=thirty_days_ago
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                total=Sum('amount')
            ).order_by('date')

            return Response({
                'status': 200,
                'data': {
                    'users': {
                        'total': total_users,
                        'new_30d': new_users_30d,
                        'new_7d': new_users_7d,
                    },
                    'subscriptions': {
                        'active': active_subscriptions,
                    },
                    'revenue': {
                        'total_30d': float(revenue_30d),
                    },
                    'usage': {
                        'prompts_30d': prompts_30d,
                        'responses_30d': responses_30d,
                        'tokens_30d': tokens_used_30d,
                    },
                    'charts': {
                        'daily_signups': list(daily_signups),
                        'daily_revenue': list(daily_revenue),
                    }
                }
            })
        except Exception as e:
            return Response({
                'status': 500,
                'error': str(e)
            })


class SystemHealthView(APIView):
    """System health monitoring endpoint."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        import redis
        from django.db import connection

        health = {
            'status': 'healthy',
            'components': {}
        }

        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health['components']['database'] = 'healthy'
        except Exception as e:
            health['components']['database'] = f'unhealthy: {str(e)}'
            health['status'] = 'degraded'

        # Redis check
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            health['components']['redis'] = 'healthy'
        except Exception as e:
            health['components']['redis'] = f'unhealthy: {str(e)}'
            health['status'] = 'degraded'

        # Celery check (basic)
        try:
            from backend.celery import app
            health['components']['celery'] = 'configured'
        except Exception as e:
            health['components']['celery'] = f'error: {str(e)}'

        return Response(health)

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



