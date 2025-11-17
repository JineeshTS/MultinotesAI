from django.contrib import admin
from .models import CustomUser
# Register your models here.
# admin.site.register(CustomUser)

@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
 list_display = ('id', 'name', 'username', 'email', 'phone_number', 'gender', 
                 'city', 'country', 'state', 'zipcode', 'is_verified', 'is_blocked' )
    # def get_model_fields(self, model):
    #     return [field.name for field in model._meta.fields]

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.list_display = self.get_model_fields(self.model)
    #     # self.list_display_links = ['username']
    #     self.ordering = ['id']