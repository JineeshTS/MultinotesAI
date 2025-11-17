from rest_framework import serializers
from .models import (LLM, PromptResponse, Prompt, NoteBook, 
                     Folder, Document, LLM_Tokens, LLM_Ratings, 
                     UserLLM, UserContent, StorageUsage, Share, 
                     GroupResponse, AiProcess
                    )
from planandsubscription.models import Category
from authentication.models import CustomUser
from planandsubscription.models import Transaction, Subscription
from django.db.models import Sum

class GetCustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'profile_image']

class LlmSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLM
        fields = '__all__'
        extra_kwargs = {
            'api_key': {'required': True, 'write_only':True},
            'code_for_integrate': {'write_only':True},
        }

    def validate_model_string(self, value):
        # Exclude the current instance from the uniqueness check
        if self.instance:
            if LLM.objects.filter(model_string=value, is_delete=False).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("This LLM model is already in use. Please choose a different one.")
        else:
            if LLM.objects.filter(model_string=value, is_delete=False).exists():
                raise serializers.ValidationError({"model_string": ["This LLM model is already in use. Please choose a different one."]})
        return value

    def validate_name(self, value):
        # Exclude the current instance from the uniqueness check
        if self.instance:
            if LLM.objects.filter(name=value, is_delete=False).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("This name is already in use. Please choose a different one.")
        else:
            if LLM.objects.filter(name=value, is_delete=False).exists():
                raise serializers.ValidationError({"name": ["This name is already in use. Please choose a different one."]})
        return value

class LlmSerializerByAdmin(serializers.ModelSerializer):
    rating_by_users = serializers.SerializerMethodField()
    class Meta:
        model = LLM
        fields = '__all__'

    def get_rating_by_users(self, obj):
        return round(LLM_Ratings.get_average_rating_for_llm(obj.id), 1)

class LlmSerializerWOPage(serializers.ModelSerializer):
    class Meta:
        model = LLM
        fields = ['id', 'name', 'description', 'is_enabled', 'model_string', 'created_at', 'updated_at', 'test_status']

class LlmForCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LLM
        fields = ['id', 'name', 'is_enabled', 'model_string', 'source', 'created_at', 'test_status', 'image_sizes']

class DocumentContentSerializer(serializers.ModelSerializer):
    user = GetCustomUserSerializer()
    folder = serializers.CharField(source='folder.title', default=None)
    class Meta:
        model = Document
        fields = ['id', 'title', 'content', 'doc_type', 'user', 'folder', 'created_at']


class GetLlmSerializer(serializers.ModelSerializer):
    # text_token_used = serializers.SerializerMethodField()
    # file_token_used = serializers.SerializerMethodField()
    # rating_by_users = serializers.SerializerMethodField()

    class Meta:
        model = LLM
        fields = ['id', 'name', 'description', 'trained_lang', 'model_latensy', 'is_enabled', 'powered_by', 'llm_creator', 'test_status', 'model_string']


    # # def get_text_token_used(self, obj):
    # #     # obj represents the NoteBook instance
    # #     # userId = self.context['user_id']
    # #     user_text_tokens = LLM_Tokens.objects.filter(user_id=31).values('llm').annotate(total_text_tokens=Sum('text_token_used'))
    # #     return user_text_tokens

    # def get_text_token_used(self, obj):
    #     return LLM_Tokens.get_total_text_token_used_for_llm(obj.id)

    # def get_file_token_used(self, obj):
    #     return LLM_Tokens.get_total_file_token_used_for_llm(obj.id)

    # def get_rating_by_users(self, obj):
    #     return LLM_Ratings.get_average_rating_for_llm(obj.id)


class DeletePromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = '__all__'

class DocumentSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    class Meta:
        model = Document
        fields = '__all__'

class DocumentAddSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ResponseSerializer(serializers.ModelSerializer):
    llm = serializers.CharField(source='llm.name')
    response_type = serializers.SerializerMethodField()

    class Meta:
        model = PromptResponse
        fields = ['llm', 'response_text', 'response_image', 'response_audio','fileSize', 'response_type', 'category', 'created_at']

    def get_response_type(self, obj):
        if obj.response_text:
            return 'text'
        elif obj.response_image:
            return 'image'
        elif obj.response_audio:
            return 'audio'
        else:
            return 'unknown'

class ForPromptSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    class Meta:
        model = Prompt
        fields = ['id', 'prompt_text', 'prompt_image', 'prompt_audio', 'title', 'category']


class SingleRespSerializer(serializers.ModelSerializer):
    llm = serializers.CharField(source='llm.name')
    response_type = serializers.SerializerMethodField()
    prompt = ForPromptSerializer()

    class Meta:
        model = PromptResponse
        fields = ['id', 'llm', 'response_text', 'response_image', 'response_audio', 'response_type', 'prompt', 'category']

    def get_response_type(self, obj):
        if obj.response_text:
            return 'text'
        elif obj.response_image:
            return 'image'
        elif obj.response_audio:
            return 'audio'
        else:
            return 'unknown'

class PromptImageSerializer(serializers.ModelSerializer):
    llm = serializers.CharField(source='llm.name')
    prompt = serializers.CharField(source='prompt.prompt_text')
    class Meta:
        model = PromptResponse
        fields = ['id', 'response_image', 'prompt', 'llm', 'created_at']
        # fields = '__all__'
        

class PromptLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = ['id', 'title','prompt_text','folder']


class ContentLibrarySerializer(serializers.ModelSerializer):
    user = GetCustomUserSerializer()
    folder = serializers.CharField(source='folder.title', default=None)
    class Meta:
        model = UserContent
        fields = '__all__'


class NoteBookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteBook
        fields = ['id', 'label','folder']
        

class SinglePromptSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    responses = serializers.SerializerMethodField()
    class Meta:
        model = Prompt
        fields = ['id','prompt_text','prompt_image','title','description','category','timestamp','responses','enabled']

    def get_responses(self, obj):
        responses_queryset = obj.responses.all()
        responses_data = ResponseSerializer(responses_queryset, many=True).data

        # Transform the responses_data to the desired structure
        formatted_responses = []
        for response in responses_data:
            response_type = response['response_type']
            if response_type == 'text':
                formatted_responses.append({'type': 'text', 'response': response['response_text'],'model': response['llm']})
            elif response_type == 'image':
                formatted_responses.append({'type': 'image', 'response': response['response_image'],'model': response['llm']})
            elif response_type == 'audio':
                formatted_responses.append({'type': 'audio', 'response': response['response_audio'],'model': response['llm']})
            else:
                formatted_responses.append({'type': 'unknown', 'response': 'Unknown response type'})

        return formatted_responses
    


class PromptCreateSerializer(serializers.ModelSerializer):
    # description = serializers.CharField(required=False,allow_blank=True)
    class Meta:
        model = Prompt
        fields = ['user','prompt_text', 'category','prompt_image']

         
class PromptUpdateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False,allow_blank=True)
    class Meta:
        model = Prompt
        fields = [ 'description', 'title','folder','is_saved']
    

class SingleNoteBookSerializer(serializers.ModelSerializer):
    references = serializers.SerializerMethodField()

    class Meta:
        model = NoteBook
        fields = ['id','label', 'content', 'references','enabled']

    def get_references(self, obj):
        # obj represents the NoteBook instance
        prompts = obj.prompts.all()  # Retrieve all prompts associated with the notebook
        prompt_texts = [prompt.prompt_text for prompt in prompts]  # Extract prompt_text values
        return prompt_texts




class FolderSerializer(serializers.ModelSerializer):
    subfolders = serializers.SerializerMethodField()
    user = GetCustomUserSerializer()
    

    class Meta:
        model = Folder
        # fields = ['id', 'title', 'created_at', 'subfolders']
        fields = '__all__'

    # Override the __init__ method to accept isShare as a custom argument
    # def __init__(self, *args, **kwargs):
    #     self.isShare = kwargs.pop('isShare', None)  # Pop isShare from kwargs if passed
    #     super().__init__(*args, **kwargs)

    def get_subfolders(self, obj):
        # Retrieve all subfolders for the current folder object
        subfolders = obj.subfolders.all()
        # Serialize the subfolders recursively
        serializer = self.__class__(subfolders, many=True)
        return serializer.data

        # # Modify serialized data to include `isShare` key
        # subfolder_data = serializer.data
        # for subfolder in subfolder_data:
        #     # Add the custom `isShare` key
        #     subfolder['isShare'] = self.isShare

        # return subfolder_data

    def get_is_share(self, subfolder):
        # Logic to determine if the folder is shared
        # This is a placeholder logic, replace it with actual sharing logic
        # For example, you can check a flag in the database or compute it based on some conditions
        return subfolder.get('shared', False)  #


class CreateFolderSerializer(serializers.ModelSerializer):
    subfolders = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        # fields = ['id', 'title', 'created_at', 'subfolders']
        fields = '__all__'

    def get_subfolders(self, obj):
        # Retrieve all subfolders for the current folder object
        subfolders = obj.subfolders.all()
        # Serialize the subfolders recursively
        serializer = self.__class__(subfolders, many=True)
        return serializer.data

class FolderOutputSerializer(serializers.ModelSerializer):
    # subfolders = serializers.SerializerMethodField()
    class Meta:
        model = Folder
        # fields = ['id', 'title', 'created_at', 'subfolders']
        fields = '__all__'
    
class FolderListSerializer(serializers.ModelSerializer):
    user = GetCustomUserSerializer()
    class Meta:
        model = Folder
        # fields = ['id', 'title', 'created_at', 'subfolders']
        fields = '__all__'
    

class TextToTextSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    model = serializers.CharField()
    source = serializers.CharField()
    useFor = serializers.CharField()
    image = serializers.ImageField(required=False)
    category = serializers.IntegerField()
    promptWriter = serializers.BooleanField(required=False)


class PictureToTextSerializer(serializers.Serializer):
    image = serializers.ImageField()
    # image = serializers.FileField()
    # prompt = serializers.CharField(required=False)
    prompt = serializers.CharField()
    model = serializers.CharField()
    category = serializers.IntegerField()
    # mainCategory = serializers.IntegerField()
    source = serializers.CharField()
    useFor = serializers.CharField()

class TextToImageSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    model = serializers.CharField()
    category = serializers.IntegerField()
    source = serializers.CharField()
    useFor = serializers.CharField()

class SpeechToTextSerializer(serializers.Serializer):
    file = serializers.FileField()
    # prompt = serializers.CharField(required=False)
    # prompt = serializers.CharField()
    model = serializers.CharField()
    category = serializers.IntegerField()

class PromptSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    responses = serializers.SerializerMethodField()
    class Meta:
        model = Prompt
        fields = ['id','prompt_text','prompt_image', 'prompt_audio', 'response_type', 'description','category', 'responses', 'created_at']

    def get_responses(self, obj):
        # responses_queryset = obj.responses.all()
        # responses_data = ResponseSerializer(responses_queryset, many=True).data
        promptResponse = PromptResponse.objects.filter(prompt=obj.id, is_delete=False)

        serializer = ResponseSerializer(promptResponse, many=True)
        return serializer.data


        # # Transform the responses_data to the desired structure
        # formatted_responses = []
        # for response in responses_data:
        #     response_type = response['response_type']
        #     if response_type == 'text':
        #         formatted_responses.append({'type': 'text', 'response': response['response_text'],'model': response['llm']})
        #     elif response_type == 'image':
        #         formatted_responses.append({'type': 'image', 'response': response['response_image'],'model': response['llm']})
        #     elif response_type == 'audio':
        #         formatted_responses.append({'type': 'audio', 'response': response['response_audio'],'model': response['llm']})
        #     else:
        #         formatted_responses.append({'type': 'unknown', 'response': 'Unknown response type'})

        # return formatted_responses

class GroupHistorySerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    responses = serializers.SerializerMethodField()
    class Meta:
        model = Prompt
        fields = ['id','prompt_text','prompt_image', 'prompt_audio', 'response_type', 'description','category', 'responses', 'created_at']

    def get_responses(self, obj):
        # responses_queryset = obj.responses.all()
        # responses_data = ResponseSerializer(responses_queryset, many=True).data
        promptResponse = PromptResponse.objects.filter(prompt=obj.id, is_delete=False).first()

        serializer = ResponseSerializer(promptResponse)
        return serializer.data
    

class LatestUserSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'name', 
                  'profile_image', 'created_at', 'user_type', 
                  'is_blocked']
        
    def get_user_type(self, instance):
        subscription_status = Subscription.objects.filter(
                    user=instance.id, status__in=['active', 'expire']
                    ).values_list('status', flat=True)
        
        if 'active' in subscription_status:
            return 'paid'
        elif 'expire' in subscription_status:
            return 'expire'
        else:
            return 'free'

class LatestTransactionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    class Meta:
        model = Transaction
        fields = ['id', 'plan_name', 'amount', 
                  'payment_status', 'created_at', 
                  'user']
        
    def get_user(self, obj):
        user = CustomUser.objects.get(id=obj.user.id)
        data = {
            "userName": user.username,
            "email": user.email,
            "profile_image": user.profile_image
        }
        return data
    

class PerDayTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptResponse
        fields = ['created_at', 'tokenUsed']


class LlmRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLM_Ratings
        fields = '__all__'

class LlmRatingOutputSerializer(serializers.ModelSerializer):
    user = GetCustomUserSerializer()
    class Meta:
        model = LLM_Ratings
        fields = '__all__'


# class UserLlmGetSerializer(serializers.ModelSerializer):
#     text_token_used = serializers.SerializerMethodField()
#     file_token_used = serializers.SerializerMethodField()
#     rating_by_users = serializers.SerializerMethodField()
#     llm = GetLlmSerializer()

#     class Meta:
#         model = UserLLM
#         fields = '__all__'

#     # def get_text_token_used(self, obj):
#     #     # obj represents the NoteBook instance
#     #     # userId = self.context['user_id']
#     #     user_text_tokens = LLM_Tokens.objects.filter(user_id=31).values('llm').annotate(total_text_tokens=Sum('text_token_used'))
#     #     return user_text_tokens

#     def get_text_token_used(self, obj):
#         return LLM_Tokens.get_total_text_token_used_for_llm(obj.llm_id)

#     def get_file_token_used(self, obj):
#         return LLM_Tokens.get_total_file_token_used_for_llm(obj.llm_id)

#     def get_rating_by_users(self, obj):
#         return LLM_Ratings.get_average_rating_for_llm(obj.llm_id)

class UserLlmGetSerializer(serializers.ModelSerializer):
    text_token_used = serializers.SerializerMethodField()
    file_token_used = serializers.SerializerMethodField()
    rating_by_users = serializers.SerializerMethodField()
    is_review = serializers.SerializerMethodField()
    
    # llm = GetLlmSerializer()

    class Meta:
        model = LLM
        fields = ["id", "name", "description", "capabilities", "trained_lang", "model_latensy", "test_status", "powered_by", "llm_creator", "text_token_used", "rating_by_users", "file_token_used", "code_for_integrate", "is_review"]

    def get_text_token_used(self, obj):
        return LLM_Tokens.get_total_text_token_used_for_llm(obj.id)

    def get_file_token_used(self, obj):
        return LLM_Tokens.get_total_file_token_used_for_llm(obj.id)

    def get_rating_by_users(self, obj):
        return round(LLM_Ratings.get_average_rating_for_llm(obj.id), 1)
    
    def get_is_review(self, obj):
        review = LLM_Ratings.objects.filter(llm=obj.id, is_delete=False).exists()
        return review
    


class UserLlmSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLLM
        fields = '__all__'



class LlmTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLM_Tokens
        fields = '__all__'


class ContentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserContent
        fields = '__all__'

        
class ContentOutputSerializer(serializers.ModelSerializer):
    # document = DocumentContentSerializer()
    class Meta:
        model = UserContent
        fields = '__all__'


class ShareContentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Share
        fields = '__all__'

class ShareContentFolderSerializer(serializers.ModelSerializer):
    folder = FolderListSerializer()   
    owner = GetCustomUserSerializer()
    class Meta:
        model = Share
        fields = '__all__'

class ShareContentFileSerializer(serializers.ModelSerializer):
    file = ContentLibrarySerializer()
    document = DocumentContentSerializer()
    folder = serializers.CharField(source='folder.title', default=None)
    
    class Meta:
        model = Share
        fields = '__all__'

class ShareByMeSerializer(serializers.ModelSerializer):
    share_to_user = GetCustomUserSerializer()
    class Meta:
        model=Share
        fields = ['share_to_user']


class ShareContentOutputSerializer(serializers.ModelSerializer):
    owner = GetCustomUserSerializer()
    share_by_me = serializers.SerializerMethodField()
    # share_to_user = GetCustomUserSerializer()
    class Meta:
        model = Share
        # fields = '__all__'
        exclude = ["share_to_user"]

    def get_share_by_me(self,obj):
        if obj.content_type == 'file':
            share = Share.objects.filter(owner=obj.owner, file=obj.file, is_delete=False)
        elif obj.content_type == 'folder':
            share = Share.objects.filter(owner=obj.owner, folder=obj.folder, is_delete=False)
        elif obj.content_type == 'document':
            share = Share.objects.filter(owner=obj.owner,document=obj.document, is_delete=False)

        original_list = ShareByMeSerializer(share, many=True).data
        # Convert the list
        converted_list = [item["share_to_user"] for item in original_list]
        return converted_list


class StorageInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageUsage
        fields = '__all__'

class StorageOutputSerializer(serializers.ModelSerializer):
    storage_limit = serializers.SerializerMethodField()
    total_storage_used = serializers.SerializerMethodField()
    class Meta:
        model = StorageUsage
        fields = '__all__'

    def get_storage_limit(self, obj):
        return round(obj.storage_limit/(1024*1024*1024), 2)

    def get_total_storage_used(self, obj):
        return round(obj.total_storage_used/(1024*1024*1024), 2)


class GroupInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupResponse
        fields = '__all__'

class GroupOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupResponse
        fields = '__all__'

class AiProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiProcess
        fields = '__all__'
        

