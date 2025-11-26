from django.urls import path
from .views import (
    AddPlan, GetPlan, UpdatePlan, DeletePlan,
    CreateSubscription, GetSubscription, UpdateSubscription, DeleteSubscription,
    CreateTransaction, GetTransaction, UpdateTransaction, DeleteTransaction,
)
from .razorpay_service import (
    CreateRazorpayOrder,
    VerifyRazorpayPayment,
    RazorpayWebhook,
    CreateRefund,
    GetPaymentStatus,
    ValidateCoupon,
)


urlpatterns = [
    # Plan Management
    path('add-plan/', AddPlan.as_view()),
    path('get-plan/<int:pk>/', GetPlan.as_view()),
    path('get-plans/', GetPlan.as_view()),
    path('update-plan/<int:pk>/', UpdatePlan.as_view()),
    path('delete-plan/<int:pk>/', DeletePlan.as_view()),

    # Subscription Management
    path('create-subscription/', CreateSubscription.as_view()),
    path('get-subscription/<int:pk>/', GetSubscription.as_view()),
    path('get-subscription/', GetSubscription.as_view()),
    path('update-subscription/<int:pk>/', UpdateSubscription.as_view()),
    path('delete-subscription/<int:pk>/', DeleteSubscription.as_view()),

    # Transaction Management
    path('create-transaction/', CreateTransaction.as_view()),
    path('get-transaction/<int:pk>/', GetTransaction.as_view()),
    path('get-transaction/', GetTransaction.as_view()),
    path('update-transaction/<int:pk>/', UpdateTransaction.as_view()),
    path('delete-transaction/<int:pk>/', DeleteTransaction.as_view()),

    # Razorpay Payment Integration
    path('payment/create-order/', CreateRazorpayOrder.as_view(), name='razorpay_create_order'),
    path('payment/verify/', VerifyRazorpayPayment.as_view(), name='razorpay_verify'),
    path('payment/webhook/', RazorpayWebhook.as_view(), name='razorpay_webhook'),
    path('payment/refund/', CreateRefund.as_view(), name='razorpay_refund'),
    path('payment/status/<str:order_id>/', GetPaymentStatus.as_view(), name='payment_status'),
    path('payment/validate-coupon/', ValidateCoupon.as_view(), name='validate_coupon'),
]