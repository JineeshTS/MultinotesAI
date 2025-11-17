from django.contrib import admin
from .models import Prompt, NoteBook, LLM, PromptResponse
from planandsubscription.models import Category
# # Register your models here.
# admin.site.register(Category)
# admin.site.register(Prompt)
# admin.site.register(NoteBook)
# admin.site.register(LLM)
# admin.site.register(PromptResponse)

# admin.site.register(Folder)


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     def get_model_fields(self, model):
#         return [field.name for field in model._meta.fields]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_display = self.get_model_fields(self.model)
#         self.ordering = ['id']

# @admin.register(Prompt)
# class PromptAdmin(admin.ModelAdmin):
#     def get_model_fields(self, model):
#         return [field.name for field in model._meta.fields]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_display = self.get_model_fields(self.model)
#         self.ordering = ['id']

# @admin.register(NoteBook)
# class NoteBookAdmin(admin.ModelAdmin):
#     def get_model_fields(self, model):
#         return [field.name for field in model._meta.fields]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_display = self.get_model_fields(self.model)
#         self.ordering = ['id']

# @admin.register(LLM)
# class LLMAdmin(admin.ModelAdmin):
#     def get_model_fields(self, model):
#         return [field.name for field in model._meta.fields]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_display = self.get_model_fields(self.model)
#         self.ordering = ['id']

# @admin.register(PromptResponse)
# class ResponseAdmin(admin.ModelAdmin):
#     def get_model_fields(self, model):
#         return [field.name for field in model._meta.fields]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_display = self.get_model_fields(self.model)
#         self.ordering = ['id']