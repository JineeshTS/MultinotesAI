from rest_framework import serializers
from .models import Ticket, Category, TicketResponse, Notification, ContactUs, MainCategory, FAQ, Coupon
from authentication.awsservice import getImageUrl
import json
from coreapp.models import LLM
from coreapp.serializers import LlmForCategorySerializer

### Create Different Serializer for More Code and Logic Control.
class GetCategorySerializer(serializers.ModelSerializer):
    llm_models = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = '__all__'

    def get_llm_models(self, obj):
        llm_list = json.loads(obj.llm_models)
        llm_model = []
        for llmId in llm_list:
            llm = LLM.objects.filter(id=llmId, is_enabled=True, is_delete=False, test_status="connected").first()
            if llm:
                llm_model.append(LlmForCategorySerializer(llm).data)
        return llm_model
                
        # llm = LLM.objects.filter(category=obj.id, is_enabled=True, is_delete=False, test_status="connected")
        # return LlmForCategorySerializer(llm).data


class CreateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class getCategoryWOPaginationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'status']


class UpdateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


### Create Different Serializer for More Code and Logic Control.
class GetMainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = '__all__'


class GetCategoryForUser(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'llm_models', 'route']




class MainCategoryUserSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    class Meta:
        model = MainCategory
        fields = ['name', 'category']

    def get_category(self, obj):
        cats = Category.objects.filter(mainCategory=obj.id, status='active', is_delete=False)

        serializer = GetCategoryForUser(cats, many=True)
        return serializer.data


class CreateMainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = '__all__'


class UpdateMainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = '__all__'


class GetTicketSerializer(serializers.ModelSerializer):
    # category = serializers.CharField(source='category.name')
    user = serializers.SerializerMethodField()
    # user = serializers.CharField(source='user.username')
    # userProfile = serializers.SerializerMethodField()
    # ticketImage = serializers.SerializerMethodField()
    # category = GetCategorySerializer()
    class Meta:
        model = Ticket
        fields = '__all__'

    def get_user(self, instance):
        userData = {
            'username': instance.user.username,
            'profile_image': instance.user.profile_image
        }
        return userData

    # def get_userProfile(self, instance):
    #     user_profile_image = instance.user.profile_image
    #     if user_profile_image:
    #         return getImageUrl(user_profile_image)
    #     return None

    # def get_ticketImage(self, instance):
    #     ticket_image = instance.image
    #     if ticket_image:
    #         return getImageUrl(ticket_image)
    #     return None

class GetAllTicketSerializer(serializers.ModelSerializer):
    # user = serializers.CharField(source='user.username')
    # category = serializers.CharField(source='category.name')
    # imageUrl = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    class Meta:
        model = Ticket
        fields = '__all__'
    
    # def get_imageUrl(self, instance):
    #     user_profile_image = instance.user.profile_image
    #     if user_profile_image:
    #         return getImageUrl(user_profile_image)
    #     return None
    
    def get_user(self, instance):
        userData = {
            'username': instance.user.username,
            'email': instance.user.email,
            'profile_image': instance.user.profile_image
        }
        # if instance.user.profile_image:
        #     user_data['profile_image'] = getImageUrl(instance.user.profile_image)
        return userData


class CreateTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'


class UpdateTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'


class GetChatTicketSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    admin = serializers.SerializerMethodField()
    # useProfile = serializers.SerializerMethodField()
    # ticketImage = serializers.SerializerMethodField()
    class Meta:
        model = TicketResponse
        fields = '__all__'

    def get_user(self, instance):
        if instance.user:
            userData = {
                'username': instance.user.username,
                'profile_image': instance.user.profile_image
            }
            return userData

    def get_admin(self, instance):
        if instance.admin:
            userData = {
                'username': instance.admin.username,
                'profile_image': instance.admin.profile_image
            }
            return userData

    # def get_useProfile(self, instance):
    #     # user_profile_image = instance.user.profile_image
    #     if instance.user and instance.user.profile_image:
    #         return instance.user.profile_image
    #     elif instance.admin and instance.admin.profile_image:
    #         return instance.admin.profile_image
    #     return None
    
    # def get_ticketImage(self, instance):
    #     ticket_image = instance.image
    #     if ticket_image:
    #         return getImageUrl(ticket_image)
    #     return None


class AddChatTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResponse
        fields = '__all__'


class UpdateChatTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResponse
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = '__all__'

    def get_user(self, instance):
        userData = {
            'username': instance.user.username,
            'email': instance.user.email,
            'profile_image': instance.user.profile_image
        }
        return userData


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = '__all__'

class FAQInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'

class FAQOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'

class CouponInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class CouponOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

