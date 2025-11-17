from django.contrib import admin
from .models import Category, Ticket, TicketResponse
# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    def get_model_fields(self, model):
        return [field.name for field in model._meta.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display = self.get_model_fields(self.model)
        self.ordering = ['id']

# @admin.register(SubCategory)
# class SubCategoryAdmin(admin.ModelAdmin):
#     def get_model_fields(self, model):
#         return [field.name for field in model._meta.fields]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_display = self.get_model_fields(self.model)
#         self.ordering = ['id']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    def get_model_fields(self, model):
        return [field.name for field in model._meta.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display = self.get_model_fields(self.model)
        self.ordering = ['id']

@admin.register(TicketResponse)
class TicketResponseAdmin(admin.ModelAdmin):
    def get_model_fields(self, model):
        return [field.name for field in model._meta.fields]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display = self.get_model_fields(self.model)
        self.ordering = ['id']
