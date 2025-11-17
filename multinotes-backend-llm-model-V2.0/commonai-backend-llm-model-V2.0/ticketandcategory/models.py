from django.db import models
from authentication.models import CustomUser
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator


class MainCategory(models.Model):
    status_type = (("active", 'active'),("inactive", 'inactive'))

    # user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(choices=status_type, max_length=100, default='active')
    alias_name = models.CharField(max_length=255, blank=True, null=True)
    # llm_models = models.CharField(max_length=255)
    can_delete = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # def save(self, *args, **kwargs):
    #     if not self.alias_name:
    #         cat_count = MainCategory.objects.all().count()
    #         self.alias_name = f'main-{cat_count + 1}'
    #     super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Category(models.Model):
    status_type = (("active", 'active'),("inactive", 'inactive'))

    mainCategory = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(choices=status_type, max_length=100, default='active')
    alias_name = models.CharField(max_length=255)
    llm_models = models.CharField(max_length=255)
    route = models.CharField(max_length=255, blank=True, null=True)
    can_delete = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.alias_name:
            cat_count = Category.objects.all().count()
            self.alias_name = f'category-{cat_count + 1}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


# class SubCategory(models.Model):
#     status_type = (("active", 'active'),("inactive", 'inactive'))
    
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE)
#     name = models.CharField(max_length=255, null=False, blank=False)
#     description = models.TextField(null=True, blank=True)
#     status = models.CharField(choices=status_type, max_length=100, default='active')
#     is_delete = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name}"
    

class Ticket(models.Model):

    status_type = (("open", 'open'),("in-progress", 'in-progress'),("closed", 'closed'))
    priorities = (("low", 'low'),("medium", 'medium'),("high", 'high'))
    ticket_choice = (("support", 'support'),("feedback", 'feedback'))
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # category = models.ForeignKey(Category, on_delete=models.CASCADE)
    ticket_title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    addition_information = models.TextField(null=True, blank=True)
    image = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(choices=status_type, max_length=100, default='open')
    priority = models.CharField(choices=priorities, max_length=100, default='low')
    ticket_type = models.CharField(choices=ticket_choice, max_length=20)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_title}"
    

    

class TicketResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='userChat', null=True)
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='adminChat', null=True)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='TicketResponse')
    chat = models.TextField(null=True, blank=True)
    image = models.CharField(max_length=255, null=True, blank=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # def __str__(self):
    #     return f"{self.ticket_title}"
    

class Notification(models.Model):
    status_type = (("open", 'open'),("closed", 'closed'))
    sender_type = (("user", 'user'),("admin", 'admin'))

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    sendBy = models.CharField(choices=sender_type, max_length=100, default='user')
    title = models.CharField(max_length=255)
    # admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='adminChat', null=True)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    type = models.IntegerField() # 2 for ticket, 3 for ticket Response
    status = models.CharField(choices=status_type, max_length=100, default='open')
    isMarkRead = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"
    

class ContactUs(models.Model):
    status_choices = (("open", 'open'),("closed", 'closed'))
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=20, null=True, blank=True)
    country_code = models.CharField(max_length=20, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(choices=status_choices, max_length=100, default='open')
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject
    
class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.question
    
    
class Coupon(models.Model):
    COUPON_TYPES = (
        ('percentage', 'percentage'),
        ('fixed', 'fixed'),
    )

    coupon_name = models.CharField(max_length=100, unique=True)
    coupon_code = models.CharField(max_length=25, unique=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bonus_token = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    # usage_limit = models.PositiveIntegerField(null=True, blank=True)
    # usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    def is_valid(self):
        """Check if the coupon is currently valid."""
        now = timezone.now()
        if self.start_date <= now <= self.end_date and self.is_active:
            return True
        return False
    





 
