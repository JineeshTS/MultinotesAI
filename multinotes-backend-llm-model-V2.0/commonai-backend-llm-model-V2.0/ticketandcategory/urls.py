from django.urls import path
from .views import *

# from .FCMManager import TestNotification, send


urlpatterns=[
    path('create-ticket/', CreateTicket.as_view()),
    path('get-ticket/<int:pk>/', GetTicket.as_view()),
    path('get-tickets/', GetTicket.as_view()),
    path('get-all-tickets/', GetAllTicket.as_view()),
    path('update-ticket/<int:pk>/', UpdateTicket.as_view()),
    path('delete-ticket/<int:pk>/', DeleteTicket.as_view()),

    path('create-category/', CreateCategory.as_view()),
    path('get-category/<int:pk>/', GetCategory.as_view()),
    path('get-categories/', GetCategory.as_view()),
    path('update-category/<int:pk>/', UpdateCategory.as_view()),
    path('delete-category/<int:pk>/', DeleteCategory.as_view()),

    path('create_main_category/', CreateMainCategory.as_view()),
    path('get_main_category/<int:pk>/', GetMainCategory.as_view()),
    path('get_main_category_for_user/', GetMainCategoryForUser.as_view()),
    path('get_main_categories/', GetMainCategory.as_view()),
    path('update_main_category/<int:pk>/', UpdateMainCategory.as_view()),
    path('delete_main_category/<int:pk>/', UpdateMainCategory.as_view()),

    path('add-chat-ticket/', AddChatTicket.as_view()),
    path('get-chat-ticket/<int:pk>/', GetChatTicket.as_view()),
    path('get-chats-ticket/', GetAllChatTicket.as_view()),
    path('update-chat-ticket/<int:pk>/', UpdateChatTicket.as_view()),
    path('delete-chat-ticket/<int:pk>/', DeleteChatTicket.as_view()),
    path('deleteMultiple/', DeleteMultiple.as_view()),

    # path('testNotification/', TestNotification.as_view()),
    # path('send/', send),

    path('get_notification/<int:pk>/', ManageNotification.as_view()),
    path('get_notifications/', ManageNotification.as_view()),
    path('update_notification/<int:pk>/', ManageNotification.as_view()),
    path('delete_notification/<int:pk>/', ManageNotification.as_view()),

    path('contactus/<int:pk>/', ContactUsQuery.as_view()),
    path('contactus/', ContactUsQuery.as_view()),

    path('create_faq/', FAQSection.as_view()),
    path('get_faq/<int:pk>/', FAQSection.as_view()),
    path('get_faqs/', FAQSection.as_view()),
    path('update_faq/<int:pk>/', FAQSection.as_view()),
    path('delete_faq/<int:pk>/', FAQSection.as_view()),

    path('coupon/', ManageCouponView.as_view()),
    path('coupon/<int:pk>/', ManageCouponView.as_view()),
    path('apply_coupon/', ApplyCouponView.as_view()),
    
]