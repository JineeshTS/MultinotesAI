from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import LLM
from ticketandcategory.models import Category,MainCategory
from planandsubscription.models import UserPlan


records = [
    {'name': 'Gemini Pro', 'model_string': 'gemini-pro'},
    {'name': 'Llama 2', 'model_string': 'meta-llama/Llama-2-70b-chat-hf'},
    {'name': 'Mistral', 'model_string':'mistralai/Mistral-7B-Instruct-v0.2'},
    {'name': 'Gemma Instruct', 'model_string':'google/gemma-7b-it'},
    {'name': 'Stable Diffusion', 'model_string':'runwayml/stable-diffusion-v1-5'},
    {'name': 'Openjourney v4', 'model_string':'prompthero/openjourney'},
    {'name': 'Realistic Vision 3.0', 'model_string':'SG161222/Realistic_Vision_V3.0_VAE'},
    {'name': 'Analog Diffusion', 'model_string':'wavymulder/Analog-Diffusion'},
    {'name': 'Stable Diffusion 2.1', 'model_string':'stabilityai/stable-diffusion-2-1'},
    {'name': 'Gemini Pro Vision', 'model_string':'gemini-pro-vision'},
    {'name': 'Phind Code LLaMA v2 (34B)', 'model_string':'Phind/Phind-CodeLlama-34B-v2'},
    {'name': 'Code Llama (70B)', 'model_string':'codellama/CodeLlama-70b-hf'},
    {'name': 'StarCoder (16B)', 'model_string':'bigcode/starcoder'},
    {'name': 'GPT-3.5 Turbo', 'model_string':'gpt-3.5-turbo'},
    {'name': 'GPT-4', 'model_string':'gpt-4'},
    {'name': 'TTS', 'model_string':'tts-1'},
    {'name': 'Whisper', 'model_string':'whisper-1'}
]


executed = False 

# @receiver(post_migrate)
# def add_static_llm_data(sender, **kwargs):
#     global executed
#     if not executed:
#         for record_data in records:
#             if not LLM.objects.filter(name=record_data['name'], model_string=record_data['model_string']).exists():
                
#                 LLM.objects.create(**record_data)
#                 print(f"Model {record_data['name']} Added In Database.")
#         executed = True



# categories = [
#     'AI Text Generator',
#     'AI Image Generator',
#     'AI Code Generator',
#     'AI Prompt Writer',
#     'Text To Speech',
#     'Speech To Text',
#     'Image To Text',
# ]


categories = [
    'category_1',
    'category_2',
    'category_3',
    'category_4',
    'category_5',
    'category_6',
    'category_7',
]


textToText = ['Gemini Pro', 'Llama 2', 'Mistral', 'Gemma Instruct', 'GPT-3.5 Turbo', 'GPT-4']

textToImage = ['Stable Diffusion', 'Openjourney v4', 'Realistic Vision 3.0', 'Analog Diffusion', 'Stable Diffusion 2.1']

audioToText = ['Whisper']

imageToText = ['Gemini Pro Vision']

codeGenerate = ['StarCoder (16B)', 'Phind Code LLaMA v2 (34B)', 'Code Llama (70B)']

textToAudio = ['TTS']


execute = False 

@receiver(post_migrate)
def add_static_category_data(sender, **kwargs):
    global execute
    if not execute:

        if not MainCategory.objects.filter(alias_name='main_category_1', is_delete=False).exists():
            name = 'AI Content Generators'
            alias_name = 'main_category_1'
            MainCategory.objects.create(name=name, alias_name=alias_name)
                
            print(f"Main Category 'AI Content Generators' Added In Database.")

        if not MainCategory.objects.filter(alias_name='main_category_2', is_delete=False).exists():
            name = 'AI Converters'
            alias_name = 'main_category_2'
            MainCategory.objects.create(name=name, alias_name=alias_name)
                
            print(f"Main Category 'AI Converters' Added In Database.")

        main_1 = MainCategory.objects.filter(alias_name='main_category_1', is_delete=False).first()
        main_2 = MainCategory.objects.filter(alias_name='main_category_2', is_delete=False).first()

        for category in categories:
            llm_models = []
            if not Category.objects.filter(alias_name=category, is_delete=False).exists():
                if category == 'category_1':
                    for value in textToText:
                        mainCategory = main_1.id
                        name = 'AI Text Generator'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)

                elif category == 'category_2':
                    for value in textToImage:
                        mainCategory = main_1.id
                        name = 'AI Image Generator'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)

                elif category == 'category_3':
                    for value in codeGenerate:
                        mainCategory = main_1.id
                        name = 'AI Code Generator'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)

                elif category == 'category_4':
                    for value in textToText:
                        mainCategory = main_1.id
                        name = 'AI Prompt Writer'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)

                elif category == 'category_5':
                    for value in textToAudio:
                        mainCategory = main_2.id
                        name = 'Text To Speech'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)

                elif category == 'category_6':
                    for value in audioToText:
                        mainCategory = main_2.id
                        name = 'Speech To Text'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)

                elif category == 'category_7':
                    for value in imageToText:
                        mainCategory = main_2.id
                        name = 'Image To Text'
                        model = LLM.objects.filter(name=value).first()
                        llm_models.append(model.id)
        
                Category.objects.create(name=name, alias_name=category, llm_models=llm_models, mainCategory_id=mainCategory)
                
                print(f"Category '{name}' Added In Database.")

        if not UserPlan.objects.filter(is_free=True, is_delete=False, plan_for='token').exists():
            UserPlan.objects.create(
                plan_name='Free', 
                description='This Plan is for Trial Period only',
                amount= 0,
                is_free= True,
                totalToken=10000,
                fileToken = 100
            )
            print("Token Plan Added In Database.")

        if not UserPlan.objects.filter(is_free=True, is_delete=False, plan_for='storage').exists():
            UserPlan.objects.create(
                plan_name='Free Storage', 
                description='This Storage Plan is for Trial Period only',
                amount= 0,
                storage_size = 5368709120,
                is_free= True,
                plan_for= 'storage'
            )
            print("Storage Plan Added In Database.")


        execute = True


