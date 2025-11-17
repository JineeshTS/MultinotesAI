from django.db import models
from authentication.models import CustomUser
from ticketandcategory.models import Category




class UserPlan(models.Model):

    renewal_options = (("auto", 'auto'), ("manual", 'manual'))
    status_type = (("active", 'active'),("inactive", 'inactive'))
    plan_type = (("token", 'token'), ("storage", 'storage'))

    # category = models.ForeignKey(Category, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(choices=status_type, max_length=100, default='active')
    plan_for = models.CharField(choices=plan_type, max_length=100, default='token')
    storage_size = models.BigIntegerField(default=0) # Size store in Bytes
    amount = models.FloatField(null=False, blank=False)
    duration = models.IntegerField(default=30)
    totalToken = models.IntegerField(default=0)
    fileToken = models.IntegerField(default=0)
    feature = models.TextField(null=True, blank=True)
    discount = models.IntegerField(default=0)
    offer = models.CharField(max_length=255, null=True, blank=True)
    # renewal_option = models.CharField(choices=renewal_options, max_length=100, default='manual')
    is_for_cluster = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plan_name}"
    
    # def size_in_gb(self):
    #     return self.storage_size / (1024)
    

class Subscription(models.Model):
    status_type = (("active", 'active'),("expire", 'expire'),("trial", 'trial'))

    payment_detail = (("paid", 'paid'),("pending", 'pending'),
                      ("failed", 'failed'),("refunded", 'refunded'),
                      ("trial", 'trial')
                    )
    
    payment_type = (("online", 'online'),("mannual", 'mannual'))

    COUPON_TYPES = (
        ('percentage', 'percentage'),
        ('fixed', 'fixed'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey(UserPlan, on_delete=models.DO_NOTHING)
    subscriptionExpiryDate = models.DateTimeField()
    subscriptionEndDate = models.DateTimeField()
    balanceToken = models.IntegerField(default=0)
    usedToken = models.IntegerField(default=0)
    expireToken = models.IntegerField(default=0)
    fileToken = models.IntegerField(default=0)
    usedFileToken = models.IntegerField(default=0)
    expireFileToken = models.IntegerField(default=0)
    description = models.TextField(null=True, blank=True)

    plan_name = models.CharField(max_length=255)
    plan_for = models.CharField(max_length=100, default='token')
    amount = models.FloatField(default=0)
    duration = models.IntegerField(default=30)
    totalToken = models.IntegerField(default=0)
    totalFileToken = models.IntegerField(default=0)
    feature = models.TextField(null=True, blank=True)
    discount = models.IntegerField(default=0)

    coupon_code = models.CharField(max_length=25, null=True, blank=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPES, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bonus_token = models.IntegerField(default=0)

    status = models.CharField(choices=status_type, max_length=100, default='active')
    transactionId = models.CharField(max_length=255)
    payment_status = models.CharField(choices=payment_detail, max_length=100)
    payment_mode = models.CharField(choices=payment_type, max_length=100)
    cancellation_reason = models.TextField(null=True, blank=True)
    trialStartDate = models.DateTimeField(null=True, blank=True)
    trialEndDate = models.DateTimeField(null=True, blank=True)

    upgrade_from_plan = models.ForeignKey(UserPlan, on_delete=models.SET_NULL, related_name='upgraded_subscriptions', null=True, blank=True)

    downgrade_to_plan = models.ForeignKey(UserPlan, on_delete=models.SET_NULL, related_name='downgraded_subscriptions', null=True, blank=True)

    is_delete = models.BooleanField(default=False)
    isSubscribe = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plan.plan_name}"
    


class Transaction(models.Model):
    STATUS_CHOICES = (
        ('paid', 'paid'),
        ('failure', 'failure'),
        ('pending', 'pending')
    )
    # payment_methods = (("card", 'card'),("bank", 'bank'),("other", 'other'))

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.DO_NOTHING, null=True, blank=True)
    storage = models.ForeignKey('coreapp.StorageUsage', on_delete=models.DO_NOTHING, null=True, blank=True)
    transactionId = models.CharField(max_length=255, null=True, unique=True)
    amount = models.FloatField(null=False, blank=False)
    plan_name = models.CharField(max_length=255)
    duration = models.IntegerField()
    tokenCount = models.IntegerField()
    fileToken = models.IntegerField()
    payment_status = models.CharField(max_length=100, choices=STATUS_CHOICES,  default='pending')
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_id}"
    






 

