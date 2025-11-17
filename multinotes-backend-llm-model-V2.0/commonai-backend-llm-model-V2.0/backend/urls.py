from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .settings import MEDIA_ROOT,MEDIA_URL
from django.conf.urls.static import static
from authentication.load_drive import GoogleDriveCallbackView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT API
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # path('account/callback/', GoogleDriveCallbackView.as_view(), name='google_drive_callback'),
    # path('drive/fetch_token/', GoogleDriveCallbackView.as_view(), name='google_drive_callback'),

    path('api/admin/',include('adminpanel.urls')),

    path('api/auth/',include('authentication.urls')),

    path('api/user/',include('coreapp.urls')),

    path('api/ticket/',include('ticketandcategory.urls')),

    path('api/category/',include('ticketandcategory.urls')),

    path('api/plan/',include('planandsubscription.urls')),

    path('api/subscription/',include('planandsubscription.urls')),

    path('api/transaction/',include('planandsubscription.urls')),


    
]+  static(MEDIA_URL, document_root=MEDIA_ROOT) 
