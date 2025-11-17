from django.contrib import admin
from .models import UserPlan, Subscription, Transaction
# Register your models here.
@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    def get_model_fields(self, model):
        return [field.name for field in model._meta.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display = self.get_model_fields(self.model)
        self.ordering = ['id']
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    def get_model_fields(self, model):
        return [field.name for field in model._meta.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display = self.get_model_fields(self.model)
        self.ordering = ['id']
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    def get_model_fields(self, model):
        return [field.name for field in model._meta.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display = self.get_model_fields(self.model)
        self.ordering = ['id']
