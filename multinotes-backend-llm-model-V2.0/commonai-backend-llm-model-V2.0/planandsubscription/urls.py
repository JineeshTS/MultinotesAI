from django.urls import path
from .views import *


urlpatterns=[
    path('add-plan/', AddPlan.as_view()),
    path('get-plan/<int:pk>/', GetPlan.as_view()),
    path('get-plans/', GetPlan.as_view()),
    path('update-plan/<int:pk>/', UpdatePlan.as_view()),
    path('delete-plan/<int:pk>/', DeletePlan.as_view()),

    path('create-subscription/', CreateSubscription.as_view()),
    path('get-subscription/<int:pk>/', GetSubscription.as_view()),
    path('get-subscription/', GetSubscription.as_view()),
    path('update-subscription/<int:pk>/', UpdateSubscription.as_view()),
    path('delete-subscription/<int:pk>/', DeleteSubscription.as_view()),

    path('create-transaction/', CreateTransaction.as_view()),
    path('get-transaction/<int:pk>/', GetTransaction.as_view()),
    path('get-transaction/', GetTransaction.as_view()),
    path('update-transaction/<int:pk>/', UpdateTransaction.as_view()),
    path('delete-transaction/<int:pk>/', DeleteTransaction.as_view()),
    
]