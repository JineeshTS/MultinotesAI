"""
Monetization models for MultinotesAI.

Includes:
- Coupon management
- Referral program
- Invoice generation
- Usage-based billing
"""

from django.db import models
from django.utils import timezone
from authentication.models import CustomUser


class Coupon(models.Model):
    """Coupon codes for discounts."""
    TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('tokens', 'Bonus Tokens'),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Discount configuration
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Maximum discount for percentage coupons"
    )

    # Bonus tokens (for token type)
    bonus_tokens = models.IntegerField(default=0)

    # Restrictions
    min_purchase = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text="Minimum purchase amount required"
    )
    applicable_plans = models.JSONField(
        default=list,
        help_text="List of plan IDs this coupon applies to"
    )
    first_purchase_only = models.BooleanField(default=False)

    # Usage limits
    usage_limit = models.IntegerField(
        null=True, blank=True,
        help_text="Total number of times this coupon can be used"
    )
    usage_limit_per_user = models.IntegerField(default=1)
    times_used = models.IntegerField(default=0)

    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Tracking
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_coupons'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.code} - {self.discount_type}"

    def is_valid(self):
        """Check if coupon is currently valid."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True

    def can_use(self, user, purchase_amount=0):
        """Check if a user can use this coupon."""
        if not self.is_valid():
            return False, "Coupon is not valid"
        
        if purchase_amount < float(self.min_purchase):
            return False, f"Minimum purchase of {self.min_purchase} required"
        
        # Check per-user limit
        user_usage = CouponUsage.objects.filter(coupon=self, user=user).count()
        if user_usage >= self.usage_limit_per_user:
            return False, "Coupon usage limit reached for this account"
        
        if self.first_purchase_only:
            from planandsubscription.models import Transaction
            has_previous = Transaction.objects.filter(
                user=user,
                payment_status='paid'
            ).exists()
            if has_previous:
                return False, "Coupon is only valid for first purchase"
        
        return True, "Valid"

    def apply(self, amount):
        """Calculate discounted amount."""
        if self.discount_type == 'percentage':
            discount = amount * (float(self.discount_value) / 100)
            if self.max_discount:
                discount = min(discount, float(self.max_discount))
            return max(amount - discount, 0)
        elif self.discount_type == 'fixed':
            return max(amount - float(self.discount_value), 0)
        return amount


class CouponUsage(models.Model):
    """Track coupon usage."""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=255)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['coupon', 'user']),
        ]


class ReferralProgram(models.Model):
    """Referral program configuration."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Rewards
    referrer_tokens = models.IntegerField(default=1000)
    referee_tokens = models.IntegerField(default=500)
    referrer_discount_percent = models.IntegerField(default=10)
    referee_discount_percent = models.IntegerField(default=10)

    # Conditions
    require_purchase = models.BooleanField(default=True)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Referral(models.Model):
    """Track referrals."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('qualified', 'Qualified'),
        ('rewarded', 'Rewarded'),
        ('expired', 'Expired'),
    ]

    referrer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='referrals_made'
    )
    referee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='referred_by'
    )
    program = models.ForeignKey(
        ReferralProgram,
        on_delete=models.SET_NULL,
        null=True
    )

    referral_code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Reward tracking
    referrer_rewarded = models.BooleanField(default=False)
    referee_rewarded = models.BooleanField(default=False)
    referrer_tokens_given = models.IntegerField(default=0)
    referee_tokens_given = models.IntegerField(default=0)

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    qualified_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['referrer', 'referee']
        indexes = [
            models.Index(fields=['referrer', 'status']),
            models.Index(fields=['referral_code']),
        ]

    def __str__(self):
        return f"{self.referrer.email} -> {self.referee.email}"


class UserReferralCode(models.Model):
    """User's unique referral code."""
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='referral_code'
    )
    code = models.CharField(max_length=50, unique=True)
    total_referrals = models.IntegerField(default=0)
    successful_referrals = models.IntegerField(default=0)
    total_earnings = models.IntegerField(default=0)  # tokens

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.code}"


class Invoice(models.Model):
    """Generated invoices."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # Transaction reference
    transaction_id = models.CharField(max_length=255, blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Currency
    currency = models.CharField(max_length=3, default='INR')
    
    # Line items
    items = models.JSONField(default=list)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Dates
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    
    # PDF storage
    pdf_url = models.URLField(blank=True)
    
    # Notes
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.user.email}"


class UsageRecord(models.Model):
    """Track detailed usage for billing."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='usage_records')
    
    # What was used
    resource_type = models.CharField(
        max_length=50,
        choices=[
            ('text_token', 'Text Token'),
            ('file_token', 'File Token'),
            ('storage', 'Storage'),
            ('api_call', 'API Call'),
        ]
    )
    
    # Quantity and cost
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Context
    model_used = models.CharField(max_length=100, blank=True)
    prompt_id = models.IntegerField(null=True, blank=True)
    
    # Billing
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_records'
    )

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'billing_period_start', 'billing_period_end']),
            models.Index(fields=['resource_type']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.resource_type}: {self.quantity}"
