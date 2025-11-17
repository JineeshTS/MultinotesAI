from django.urls import path
from .views import *
from .payments import *
from .load_drive import *
from .import load_drive


urlpatterns=[
    
        # Basic Public Api
        path('v1/register/', Register.as_view(), name = 'register-user'),       
        path('v1/login/', LoginByEmailAndPassword.as_view(), name = 'user-login'),
        path('v1/verify-email-token/', EmailVerificationAPIView.as_view(), name='verify_email'),
        path('v1/forgot-password/', ForgotPasswordRequestView.as_view()),
        path('v1/reset-password/', ResetPasswordAPIView.as_view()),
        path('v1/social-login/', SocialLogin.as_view()),
        path('resend_verification/', ResendVerification.as_view()),
        path('generate_password/', GeneratePassword.as_view()),
        path('otp_for_user_to_sub_admin/<int:pk>/', UserToSubAdminOTP.as_view()),
        path('user_to_sub_admin/<int:pk>/', UserToSubAdmin.as_view()),
        path('sub_admin_to_user/<int:pk>/', SubAdminToUserView.as_view()),
        path('otp_for_cluster_to_admin/<int:pk>/', ClusterUserToAdminOTP.as_view()),
        path('cluster_user_to_admin/<int:pk>/', ClusterUserToAdminView.as_view()),
        path('cluster_sub_admin_to_user/<int:pk>/', ClusterAdminToUserView.as_view()),


        path('update-user/<int:pk>/', UpdateUser.as_view()),
        path('media/preview/', getImageUrlView.as_view()),
        path('uploadImage/', ImageUploadView.as_view(), name='image-upload'),
        path('change-password/', ChangePasswordView.as_view()),
        path('get-user/<int:pk>/', GetUser.as_view()),
        path('get-users/', GetAllUsers.as_view()),
        path('delete-user/<int:pk>/', DeleteUser.as_view()),
        path('test_cron/', subscriptions),

        # Stripe Paymeent Gateway API
        path('payment_intents/', CreatePaymentIntent.as_view(), name='create_payment_intent'),
        # path('add_customer/', AddCustomer.as_view(), name='create_payment_intent'),
        path('add_card/', AddCard.as_view(), name='add_card'),
        # path('make_payment/', MakePayment.as_view(), name='make_payment'),
        path('get_cards/', GetCards.as_view(), name='make_payment'),
        path('update_card/', UpdateCard.as_view(), name='make_payment'),
        path('delete_card/', DeleteCard.as_view(), name='make_payment'),

        path('get_customer_details/<str:custId>/', GetCustomerDetails.as_view(), name='make_payment'),
        path('mark_card_default/', MarkCardDefault.as_view(), name='make_payment'),
        # path('generate_card_token/', GenerateCardToken.as_view(), name='make_payment'),
        
        path('add_cluster/', ClusterMngt.as_view()),
        path('get_cluster/<int:pk>/', ClusterMngt.as_view()),
        path('get_clusters/', ClusterMngt.as_view()),
        path('update_cluster/<int:pk>/', ClusterMngt.as_view()),
        path('delete_cluster/<int:pk>/', ClusterMngt.as_view()),
        
        path('add_setting/', ReferralMngt.as_view()),
        path('get_setting/<int:pk>/', ReferralMngt.as_view()),
        path('get_settings/', ReferralMngt.as_view()),
        path('update_setting/<int:pk>/', ReferralMngt.as_view()),
        path('delete_setting/<int:pk>/', ReferralMngt.as_view()),

        path('get_referrrals_detail/', UserReferralView.as_view()),

        path('change_user_role/', ChangeUserRole.as_view()),

        path('google-drive/auth/', GoogleDriveAuthView.as_view(), name='google_drive_auth'),
        path('google-drive/callback/', GoogleDriveCallbackView.as_view(), name='google_drive_callback'),
        # path('upload_file/', UploadFileToGoogleDriveView.as_view(), name='upload_to_google_drive'),
        path('upload_data/', UploadDataToGoogleDriveView.as_view(), name='upload_to_google_drive'),
        path('upload_complete_data/', UploadCompleteDataToDriveView.as_view()),

        # path('google-drive/auth/', load_drive.google_drive_auth, name='google_drive_auth'),
        # path('google-drive/callback/', load_drive.google_drive_callback, name='google_drive_callback'),
        # path('upload/', load_drive.upload_to_google_drive, name='upload_to_google_drive'),
]
