from django.db import models
from authentication.models import CustomUser
from ticketandcategory.models import Category, MainCategory

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Sum
from django.db.models import Avg
from planandsubscription.models import UserPlan

# Create your models here.

# class Purpose(models.Model):
#     name = models.CharField(max_length=255)

#     def __str__(self) -> str:
#         return self.name

class LLM(models.Model):
    name = models.CharField(max_length=255)
    # name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    capabilities = models.CharField(max_length=255, blank=True, null=True)
    trained_lang = models.CharField(max_length=255, blank=True, null=True)
    api_key = models.CharField(max_length=255)
    code_for_integrate = models.TextField(blank=True, null=True)
    powered_by = models.TextField(blank=True, null=True)
    llm_creator = models.CharField(max_length=255, blank=True, null=True)
    model_latensy = models.CharField(max_length=255, blank=True, null=True)
    test_status = models.CharField(max_length=20, choices=(('connected', 'connected'), ('disconnected', 'disconnected')), default="disconnected")


    # max_tokens = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4096)], default=512)
    # temperature = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(2)], default=0.7)
    # top_p = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)], default=0.7)
    # top_k = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)], default=50)
    # repetition_penalty = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(2)], default=1)
    # stop = models.CharField(max_length=255, default='["</s>"]')

    is_enabled = models.BooleanField(default=True)

    model_string = models.CharField(max_length=255)

    source = models.IntegerField(default=2)  # 2 for Together, 3 for Gemini, 4 for Openai

    useFor = models.IntegerField(default=2)  # 2 for text, 3 for file, 4 for code, 5 for image_to_text, 6 for text_to_image, 7 for text_to_speech, 8 for speech_to_text

    # category = models.ForeignKey(Category,on_delete=models.CASCADE, related_name='models')

    # model_string = models.CharField(max_length=255)
    is_delete = models.BooleanField(default=False)

    text = models.BooleanField(default=False)
    code = models.BooleanField(default=False)
    image_to_text = models.BooleanField(default=False)
    video_to_text = models.BooleanField(default=False)
    text_to_image = models.BooleanField(default=False)
    text_to_audio = models.BooleanField(default=False)
    audio_to_text = models.BooleanField(default=False)
    image_audio_to_text = models.BooleanField(default=False)
    image_sizes = models.TextField(blank=True, null=True)

    # audio = models.BooleanField(default=False)
    # prompt = models.BooleanField(default=False)
    # video = models.BooleanField(default=False)
    # tools = models.BooleanField(default=False)

    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    
class LLM_Ratings(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # assuming you have a User model
    llm = models.ForeignKey(LLM, on_delete=models.CASCADE)  # assuming you have an LLM model for the review
    review = models.TextField(blank=True, null=True)  # stores the review text
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])  # rating between 1 and 5
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.llm.name} - {self.rating} Stars"
    
    @staticmethod
    def get_average_rating_for_llm(llm_id):
        average_rating = LLM_Ratings.objects.filter(llm_id=llm_id, is_delete=False).aggregate(avg_rating=Avg('rating'))
        return average_rating['avg_rating'] or 0
    
class UserLLM(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    llm = models.ForeignKey(LLM, on_delete=models.CASCADE)
    enabled = models.BooleanField(default = True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Folder(models.Model):
    title = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # content_type = models.CharField(max_length=20, choices=(('prompt', 'prompt'), ('notebook', 'notebook')), default="prompt")
    parent_folder = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_all_prompts(self):
        # Retrieve all prompts under this folder
        prompts = Prompt.objects.filter(folder=self)

        # Recursively retrieve prompts from subfolders
        for subfolder in self.subfolders.all():
            prompts |= subfolder.get_all_prompts()



    # def get_descendant_folders(self, include_self=False):
    #     descendants = self.get_descendants(include_self=include_self)
    #     return Folder.objects.filter(id__in=descendants.values_list('id', flat=True))

    # def get_all_prompts(self):
    #     # Retrieve all prompts under this folder and its subfolders
    #     prompts = Prompt.objects.filter(folder__in=self.get_descendant_folders(include_self=True))

    #     return prompts
            
class GroupResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    llm = models.ForeignKey(LLM, on_delete=models.CASCADE)
    group_name = models.CharField(max_length=255)
    # conversation_id = models.CharField(max_length=255)
    conversation_history = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Prompt(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    group = models.ForeignKey(GroupResponse, on_delete=models.CASCADE, null=True, blank=True)
    prompt_text = models.TextField(null=True, blank=True)
    prompt_image = models.CharField(max_length=255, blank=True, null=True)
    prompt_audio = models.CharField(max_length=255, blank=True, null=True)
    # prompt_image = models.ImageField(upload_to='prompt_images/', blank=True, null=True)
    # responses = models.ManyToManyField(PromptResponse,blank=True, related_name='prompts')
    #For 1 prompt we have multiple respone so we can use foreign key in response for multiple response of each prompt. 

    response_type = models.IntegerField(null=True, blank=True)   # 2 for texttotext, 3 for pictureToText, 4 for textToImage, 5 for textToSpeech, 6 for speechToText, 7 for Code Generation, 8 for Prompt Generate, 9 for video to text.

    category=models.ForeignKey(Category, on_delete=models.CASCADE)
    # mainCategory=models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    description = models.TextField(blank=True,null=True)
    title = models.CharField(max_length=255)
    enabled = models.BooleanField(default = True)
    # folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='prompts', null=True, blank=True)
    is_saved = models.BooleanField(default = False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    
      
    def save(self, *args, **kwargs):
        # Check if the user has provided a custom title
        if not self.title:
            # Check the number of prompts saved by the user
            user_prompts_count = Prompt.objects.filter(user=self.user).count()

            # Assign a default title based on the prompt count
            self.title = f'prompt-{user_prompts_count + 1}'

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    

class PromptResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    llm = models.ForeignKey(LLM, on_delete=models.CASCADE)
    response_text = models.TextField(blank=True, null=True)
    # response_image = models.ImageField(upload_to='response_images/', blank=True, null=True)
    response_image = models.CharField(max_length=255, blank=True, null=True)
    # response_audio = models.FileField(upload_to='response_audios/', blank=True, null=True)
    response_audio = models.CharField(max_length=255, blank=True, null=True)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    response_type = models.IntegerField(null=True, blank=True)   # 2 for texttotext, 3 for imageToText, 4 for textToImage, 5 for textToSpeech, 6 for speechToText, 7 for Code Generation, 8 for Prompt Generate, 9 for video to text.
    fileSize = models.BigIntegerField(default=0) # Size in Byte
    category=models.ForeignKey(Category, on_delete=models.CASCADE)
    # mainCategory=models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    tokenUsed = models.IntegerField(null=True, blank=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Response for {self.llm.name}"
    

    def get_response_type(self):
        if self.response_text:
            return 'text'
        elif self.response_image:
            return 'image'
        elif self.response_audio:
            return 'audio'
        else:
            return 'unknown'
        
    
    
class StorageUsage(models.Model):
    status_type = (("active", 'active'),("expire", 'expire'),("trial", 'trial'))

    payment_detail = (("paid", 'paid'),("pending", 'pending'),
                      ("failed", 'failed'),("refunded", 'refunded'),
                      ("trial", 'trial')
                    )
    
    payment_type = (("online", 'online'),("mannual", 'mannual'))

    COUPON_TYPES = (
        ('percentage', 'percentage'),
        ('fixed', 'fixed'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey(UserPlan, on_delete=models.DO_NOTHING)
    subscriptionExpiryDate = models.DateTimeField()
    subscriptionEndDate = models.DateTimeField()
    description = models.TextField(null=True, blank=True)
    status = models.CharField(choices=status_type, max_length=100, default='active')
    transactionId = models.CharField(max_length=255)
    payment_status = models.CharField(choices=payment_detail, max_length=100)
    payment_mode = models.CharField(choices=payment_type, max_length=100)
    # cancellation_reason = models.TextField(null=True, blank=True)

    plan_name = models.CharField(max_length=255)
    plan_for = models.CharField(max_length=100, default='token')
    amount = models.FloatField(default=0)
    duration = models.IntegerField(default=30)
    feature = models.TextField(null=True, blank=True)
    discount = models.IntegerField(default=0)

    coupon_code = models.CharField(max_length=25, null=True, blank=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPES, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bonus_token = models.IntegerField(default=0)


    total_storage_used = models.BigIntegerField(default=0)  # store size in bytes
    storage_limit = models.BigIntegerField(default=0)  # Size store in bytes

    is_delete = models.BooleanField(default=False)
    isSubscribe = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.total_storage_used} bytes used"
        

class LLM_Tokens(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # assuming you have a User model
    llm = models.ForeignKey(LLM, on_delete=models.CASCADE)  # assuming you have an LLM model for the review
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    text_token_used = models.IntegerField(default=0)
    file_token_used = models.IntegerField(default=0)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Token Used by {self.user.username} for {self.llm.name} Model"
    
    @staticmethod
    def get_total_text_token_used_for_llm(llm_id):
        total_text_tokens = LLM_Tokens.objects.filter(llm_id=llm_id).aggregate(total_text_tokens=Sum('text_token_used'))
        return total_text_tokens['total_text_tokens'] or 0
    
    @staticmethod
    def get_total_file_token_used_for_llm(llm_id):
        total_file_tokens = LLM_Tokens.objects.filter(llm_id=llm_id).aggregate(total_file_tokens=Sum('file_token_used'))
        return total_file_tokens['total_file_tokens'] or 0


class NoteBook(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    label = models.CharField(max_length=255,unique=True)
    content = models.TextField(null=True,blank=True)
    enabled = models.BooleanField(default = True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='notebooks', null=True, blank=True)
    prompts = models.ManyToManyField(Prompt, related_name='notebooks', blank=True)
    is_open=models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.label


class Document(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    # mainCategory = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=255)
    llm_model = models.CharField(max_length=255)
    responseId = models.CharField(max_length=255)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    title = models.TextField()
    content = models.TextField()
    size = models.IntegerField()
    enabled = models.BooleanField(default = True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.category.name

class UserContent(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    # PromptResponse = models.ForeignKey(PromptResponse, on_delete=models.CASCADE, null=True, blank=True)

    # document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
    # content_type = models.CharField(max_length=20, choices=(('file', 'file'), ('document', 'document')), default="file")

    # prompt_text = models.TextField(null=True, blank=True)
    file = models.CharField(max_length=255)
    description = models.TextField(blank=True,null=True)
    fileName = models.CharField(max_length=255)
    # edit_status = models.IntegerField()  #2 for not editable, 3 for editabe
    
    fileSize = models.BigIntegerField(default=0) # Size in Byte
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    # is_parent_folder = models.BooleanField(default = False)
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    self_upload = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.fileName}"


# class FolderData(models.Model):
#     file = models.ForeignKey(UserContent, on_delete=models.CASCADE, null=True, blank=True)
#     folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
#     document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
#     owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     share_to_user = models.ForeignKey(CustomUser, related_name='shared_content', on_delete=models.CASCADE, null=True, blank=True)

#     content_type = models.CharField(max_length=20, choices=(('file', 'file'), ('folder', 'folder'), ('document', 'document')), default="file")

#     access_type = models.CharField(max_length=20, choices=(('can_view', 'can_view'), ('can_edit', 'can_edit')), default="can_view")

#     # edit_status = models.IntegerField()  #2 for not editable, 3 for editabe 
#     is_share = models.BooleanField(default=False)
#     is_active = models.BooleanField(default=True)
#     is_delete = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.fileName}"
    
    
class Share(models.Model):
    file = models.ForeignKey(UserContent, on_delete=models.CASCADE, null=True,  blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    share_to_user = models.ForeignKey(CustomUser, related_name='shared_content', on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20, choices=(('file', 'file'), ('folder', 'folder'), ('document', 'document')), default="file")
    access_type = models.CharField(max_length=20, choices=(('can_view', 'can_view'), ('can_edit', 'can_edit')), default="can_edit")
    
    main_folder = models.ForeignKey(Folder, related_name='main_folder',  on_delete=models.CASCADE, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.owner.username} shared with {self.share_to_user.username}"
    

class AiProcess(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    # llm = models.ForeignKey(LLM, on_delete=models.CASCADE)
    # llm = models.CharField(max_length=255, null=True, blank=True)
    url = models.TextField()
    title = models.TextField(null=True, blank=True)
    url_output = models.TextField(null=True, blank=True)
    workflow = models.TextField()
    url_status = models.CharField(max_length=20, choices=(('pending', 'pending'), ('done', 'done')), default="pending")
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    


    

    






    