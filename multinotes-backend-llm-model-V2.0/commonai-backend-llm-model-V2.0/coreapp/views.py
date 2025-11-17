from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response as APIResponse
from .utils import (generateUsingGemini, generateUsingTogether, 
                        generateImageUsingTogether, generateFromImageUsingGemini,
                        remove_llm_model, aiTogetherProcess, aiGeminiProcess,
                        aiOpenAIProcess, extract_text_from_image
                   )
from rest_framework.permissions import IsAuthenticated
from .models import (LLM, PromptResponse, NoteBook, Folder, Prompt, 
                        Document, LLM_Ratings, LLM_Tokens, UserLLM, UserContent,
                        StorageUsage, Share, GroupResponse, AiProcess
                    ) 
from .serializers import (PromptCreateSerializer, LlmSerializer, 
                            CategorySerializer, FolderSerializer,
                            NoteBookListSerializer, SingleNoteBookSerializer,
                            PromptUpdateSerializer, PromptLibrarySerializer,
                            SinglePromptSerializer, DocumentSerializer, 
                            SingleRespSerializer, PromptSerializer,
                            PromptImageSerializer, LatestUserSerializer,
                            LatestTransactionSerializer, PerDayTokenSerializer,
                            DocumentAddSerializer, DeletePromptSerializer,
                            GetLlmSerializer, LlmSerializerWOPage,
                            LlmSerializerByAdmin, LlmRatingSerializer, UserLlmSerializer,
                            UserLlmGetSerializer, LlmRatingOutputSerializer,
                            ContentInputSerializer, ContentOutputSerializer,
                            ContentLibrarySerializer, StorageInputSerializer,
                            StorageOutputSerializer, FolderListSerializer,
                            ShareContentFolderSerializer, ShareContentInputSerializer,
                            ShareContentFileSerializer, ShareContentOutputSerializer,
                            DocumentContentSerializer, FolderOutputSerializer,
                            CreateFolderSerializer, GroupInputSerializer,
                            GroupOutputSerializer, GroupHistorySerializer,
                            AiProcessSerializer
                         )
from planandsubscription.models import Subscription, Transaction, UserPlan
from ticketandcategory.models import Category, MainCategory
from rest_framework.response import Response
from django.db.models import Q
from django.db import transaction
import base64
from django.core.files.base import ContentFile
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.pagination import PageNumberPagination
from authentication.awsservice import uploadImage
import time
import base64
from PIL import Image
from io import BytesIO
from rest_framework import status
from authentication.models import CustomUser, Cluster
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models.functions import TruncDay
from django.db.models.functions import TruncDate
from authentication.tasks import share_content_email, aiprocess_data
from authentication.awsservice import delete_file_from_s3, download_s3_file
from planandsubscription.serializers import UpdateTransactionSerializer
import re
import json
import os
from django.conf import settings
from .authenticaton import TextSubscriptionAuth, FileSubscriptionAuth

# from moviepy.editor import VideoFileClip
# from pytube import YouTube
# import tempfile

from pytubefix import YouTube
from pytubefix.cli import on_progress

from .aigenerator import manage_file_token
import yt_dlp
from pydub import AudioSegment
import subprocess
import fitz  # PyMuPDF for PDF
import pandas as pd
from docx import Document as word_docments
import textract
import csv
import tiktoken
from openai import OpenAI
openAiClient = OpenAI()

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service

OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')

# Create your views here.

class GenerateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        start_time = time.time() 
        user=request.user
        data=request.data
        # print('helloooo')
        try:
            prompt = data.get('prompt')
            models = data.get('models',[])
            category = data.get('category')   
            # print(prompt,models,category)

            if not prompt or not models:
                
                return APIResponse({
                    'status': 400,
                    'message': 'Prompt and models are required .',
                })

            generated_content = []

            for model in models:
                try:
                    llm_instance = LLM.objects.get(name=model)  # Get the LLM instance by name
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return APIResponse({
                        'status': 400,
                        'message': f'Model "{model}" not found.',
                    })
                if model == 'Gemini Pro':
                    content = generateUsingGemini(prompt)
                    # print(content,'--->gemini')
                    generated_content.append({'llm': model, 'response_text': content})

                elif model in ['Llama 2','mistralai','Gemma Instruct']:
                    content = generateUsingTogether(prompt,model_string)
                    # print(content,'-->llama 2')
                    generated_content.append({'llm': model, 'response_text': content})
                    
                else:
                    return APIResponse({
                        'status': 400,
                        'message': f'Invalid model: {model}',
                    })

             # Save the prompt 
            serializer = PromptCreateSerializer(data={"user":user.id,"prompt_text":prompt,"category":category})
            # print(serializer.is_valid())
            if serializer.is_valid():
                prompt_instance = serializer.save()
                # print(prompt_instance)

                # Handle the many-to-many field 'responses'
                for response_data in generated_content:
                    llm_name = response_data.get('llm')
                    response_text = response_data.get('response_text')
                    # print(llm_name,response_text)

                    # Get or create the LLM instance
                    llm_instance, created = LLM.objects.get_or_create(name=llm_name)
                    # print(llm_instance,'1232')

                    # Create the response
                    response_instance = PromptResponse.objects.create(llm=llm_instance, response_text=response_text, user_id = request.user.id)
                    # print(response_instance)

                    # Add the response to the prompt
                    prompt_instance.responses.add(response_instance)
                    
                time_taken = time.time() - start_time
                # print("Toal Run Time is ---> ", time_taken)
                return APIResponse({
                    'message': 'Content generated',
                    'generated_content': generated_content,
                    'prompt_id': prompt_instance.id, 
                    'status': 201})

            return APIResponse({
                'status': 400,
                'message': 'Serializer data is invalid.',
                'errors': serializer.errors
            })

        except Exception as e:
            return APIResponse({
                'status': 500,
                'message': 'An error occurred during content generation.',
                'error': str(e),
            })
        
def base64_to_image(base64_string):
    # Decode the Base64 string into bytes
    image_data = base64.b64decode(base64_string)
    
    # Open a BytesIO stream to read the decoded image data
    image_stream = BytesIO(image_data)
    
    # Open the image using PIL
    image = Image.open(image_stream)
    
    return image
        
class GenerateImage(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request):
        user=request.user
        data=request.data
        # print('helloooo')
        # try:
        prompt = data.get('prompt')
        models = data.get('models',[])
        category = data.get('category')   
        # print(prompt,models,category)

        if not prompt or not models:
            
            return APIResponse({
                'status': 400,
                'message': 'Prompt and models are required .',
            })

        generated_content = []
        # Save the prompt instance first
        serializer = PromptCreateSerializer(data={"user":user.id,"prompt_text":prompt,"category":category})
        if serializer.is_valid():
            prompt_instance = serializer.save()
            # print(prompt_instance)
        else:
            return APIResponse({
                'status': 400,
                'message': 'Serializer data is invalid.',
                'errors': serializer.errors
            })
        

        for model in models:
            try:
                llm_instance = LLM.objects.get(name=model)  
                model_string = llm_instance.model_string
            except LLM.DoesNotExist:
                return APIResponse({
                    'status': 400,
                    'message': f'Model "{model}" not found.',
                })
            if model in ['Openjourney v4','Stable Diffusion','Realistic Vision 3.0','Stable Diffusion 2.1','Analog Diffusion']:
                # image = generateImageUsingTogether(prompt,model_string)                 
                image_data = generateImageUsingTogether(prompt, model_string)
                # image_data_decoded = base64.b64decode(image_data['image_base64'])
                image_data_decoded = base64.b64decode(image_data)


                image_stream = BytesIO(image_data_decoded)



                with transaction.atomic():
                    response_instance = PromptResponse.objects.create(llm=llm_instance, prompt_id=prompt_instance.id, user_id = request.user.id)
                    response_instance.response_image=f'{model}-{response_instance.pk}.png'
                    response_instance.save()
                    # response_instance.response_image.save(f'{model}-{response_instance.pk}.png', ContentFile(image_data_decoded), save=True)
                    # prompt_instance.responses.add(response_instance)

                imgKey = "multinote/texttoimage/" + f"{model}-{response_instance.pk}.png"
                # print(img)
                uploadImage(BytesIO(image_data_decoded), imgKey, "image/png")
                # print(image)

                # generated_content.append({'llm': model, 'image': response_instance.response_image})
                generated_content.append({'llm': model, 'image': imgKey})
            
            else:
                return APIResponse({
                    'status': 400,
                    'message': f'Invalid model: {model}',
                })

        return APIResponse({
                'message': 'Content generated',
                'generated_content': generated_content,
                'prompt_id': prompt_instance.id, 
                'status': 201})

        # except Exception as e:
        #     return APIResponse({
        #         'status': 500,
        #         'message': 'An error occurred during content generation.',
        #         'error': str(e),
        #     })
class GenerateFromImage(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request):
        user=request.user
        data=request.data
        # print('helloooo',request.data,request.FILES)
        try:

            prompt = data.get('prompt')
            models = data.getlist('models')
           
            category = data.get('category') 
            

            uploaded_image = request.FILES.get('image')
            image_url = data.get('image_url')

            if not uploaded_image and not image_url:
                return APIResponse({
                    'status': 400,
                    'message': 'Add an image to use this model .',
                })
            # print(uploaded_image)
            if uploaded_image:
                # Case: User uploads an image file
                image_data = uploaded_image
            else:
                # Case: User selects a prompt from their library (image stored as URL)
                image_url = data.get('image')
                base_url = request.build_absolute_uri('/')  # Get base URL of Django application
                full_image_url = base_url + image_url  
                response = requests.get(full_image_url)
                image_content = response.content
                image_data = InMemoryUploadedFile(BytesIO(image_content), None, 'image.jpg', 'image/jpeg', len(image_content), None)
            

            
            if not prompt or not models:
                
                return APIResponse({
                    'status': 400,
                    'message': 'Prompt and models are required .',
                })

            generated_content = []
            # Save the prompt instance first
            serializer = PromptCreateSerializer(data={"user":user.id,"prompt_text":prompt,"prompt_image":image_data,"category":category})
            if serializer.is_valid():
                prompt_instance = serializer.save()
            else:
                return APIResponse({
                    'status': 400,
                    'message': 'Serializer data is invalid.',
                    'errors': serializer.errors
                })
            
            # print('models',type(models))
            for model in models:
                try:
                    llm_instance = LLM.objects.get(name=model)  
                   
                except LLM.DoesNotExist:
                    return APIResponse({
                        'status': 400,
                        'message': f'Model "{model}" not found.',
                    })
                if model in ['Gemini Pro Vision']:
                    response_data = generateFromImageUsingGemini(prompt, prompt_instance.prompt_image)
                    # print(response_data)
                    

                    with transaction.atomic():
                        response_instance = PromptResponse.objects.create(llm=llm_instance, response_text=response_data, user_id = request.user.id)
                        # print(response_instance)

                        # Add the response to the prompt
                        prompt_instance.responses.add(response_instance)

                    generated_content.append({'llm': model, 'response_text': response_data})
                
                else:
                    return APIResponse({
                        'status': 400,
                        'message': f'Invalid model: {model}',
                    })

            return APIResponse({
                    'message': 'Content generated',
                    'generated_content': generated_content,
                    'prompt_id': prompt_instance.id, 
                    'status': 201})

        except Exception as e:
            return APIResponse({
                'status': 500,
                'message': 'An error occurred during content generation.',
                'error': str(e),
            })

# class LlmListingView(ListAPIView):
#      permission_classes = [IsAuthenticated]
#      serializer_class=LlmSerializer

#      def get_queryset(self):
#         category_id = self.request.query_params.get('category_id')  
#         queryset = LLM.objects.filter(is_enabled=True)
#         if category_id:
#             queryset = queryset.filter(category_id=category_id)
#         return queryset
     
class CategoryListingView(ListAPIView):
     permission_classes = [IsAuthenticated]
     queryset=Category.objects.all()
     serializer_class=CategorySerializer

class PromptLibraryView(APIView):
    permission_classes = [IsAuthenticated]
    def get_folder_path(self, folder):
        # Recursively get the folder path until the root folder
        path = [{'id': folder.id, 'title': folder.title}]
        parent_folder = folder.parent_folder
        while parent_folder:
            path.insert(0, {'id': parent_folder.id, 'title': parent_folder.title})
            parent_folder = parent_folder.parent_folder
        return path
    

    def get_folder_data(self, folder):
        # Get folder data along with its path
        folder_data = {
            'id': folder.id,
            'title': folder.title,
            'path': self.get_folder_path(folder)
        }
        return folder_data

    def get(self,request):
        user = request.user
        folder_id = request.GET.get('id')
        search_query = request.GET.get('q')
        folder_path = []
        if folder_id:
            folder = Folder.objects.get(id=folder_id)
            folder_path = self.get_folder_path(folder)
            # Fetch prompts and folders linked with the provided folder ID
            linked_prompts = Prompt.objects.filter(user=user, is_saved=True, folder__id=folder_id)
            linked_folders = Folder.objects.filter(user=user, content_type='prompt', parent_folder__id=folder_id)
        else:
            # Fetch all prompts without a folder
            linked_prompts = Prompt.objects.filter(user=user, is_saved=True, folder=None)
            # Fetch all folders without a parent folder
            linked_folders = Folder.objects.filter(user=user, content_type='prompt', parent_folder=None)

        # Apply search filter if query exists
        if search_query:
            linked_prompts = linked_prompts.filter(Q(prompt_text__icontains=search_query) | Q(title__icontains=search_query) | Q(description__icontains = search_query))
            linked_folders = linked_folders.filter(title__icontains=search_query)

        linked_prompts = linked_prompts.order_by('-timestamp')
        linked_prompts_serializer = PromptLibrarySerializer(linked_prompts, many=True)
        linked_folders = linked_folders.order_by('-timestamp')
        linked_folders_serializer = FolderSerializer(linked_folders, many=True)

        return APIResponse({
            'root_files': linked_prompts_serializer.data,
            'root_folders': linked_folders_serializer.data,
            'folder_path': folder_path
        })
    
    
def get_files(user, folder_id):
    files = UserContent.objects.filter(user=user, is_delete=False, folder=folder_id)
    files = files.order_by('-created_at')
    files_serializer = ContentLibrarySerializer(files, many=True)
    return files_serializer.data
    
def get_folder_file_size(user, folder_id):
    files_size = UserContent.objects.filter(
        user=user, 
        is_delete=False, 
        folder=folder_id
    ).aggregate(total_size=Sum('fileSize'))

    return files_size.get('total_size', 0) or 0
    
def get_documents(user, folder_id):
    documents = Document.objects.filter(user=user, is_delete=False, folder=folder_id)
    documents = documents.order_by('-created_at')
    document_serializer = DocumentContentSerializer(documents, many=True)
    return document_serializer.data

    
def get_folder_detail(user, folder_id):
    folder = Folder.objects.get(id=folder_id)

    linked_folders = Folder.objects.filter(user=user, parent_folder__id=folder_id, is_delete=False)

    linked_folders = linked_folders.order_by('-created_at')
    linked_folders_serializer = FolderSerializer(linked_folders, many=True)

    sub_folders = linked_folders_serializer.data

    return folder.title, sub_folders


class FolderLibraryView(APIView):
    permission_classes = [IsAuthenticated]
    def get_folder_path(self, folder):
        # Recursively get the folder path until the root folder
        path = [{'id': folder.id, 'title': folder.title}]
        parent_folder = folder.parent_folder
        while parent_folder:
            path.insert(0, {'id': parent_folder.id, 'title': parent_folder.title})
            parent_folder = parent_folder.parent_folder
        return path
    

    def get_folder_data(self, folder):
        # Get folder data along with its path
        folder_data = {
            'id': folder.id,
            'title': folder.title,
            'path': self.get_folder_path(folder)
        }
        return folder_data

    def get(self,request):
        user = request.user
        folder_id = request.GET.get('id')
        isShare = request.GET.get('isShare', 'false')
        search_query = request.GET.get('q')
        folder_path = []

        isShare_bool = isShare.lower() == 'true'
        if folder_id and isShare_bool:
            # folder = Folder.objects.get(id=folder_id)
            # folder_path = self.get_folder_path(folder)

            # Fetch content and folders linked with the provided folder ID
            # linked_file_contents = UserContent.objects.filter(user=user, is_delete=False, folder=folder_id)
            
            # linked_document_contents = Document.objects.filter(user=user, is_delete=False, folder=folder_id)

            # linked_folders = Folder.objects.filter(parent_folder__id=folder_id, is_delete=False)

            linked_folders = Share.objects.filter(main_folder=folder_id, is_delete=False)
            linked_folders = linked_folders.order_by('-created_at')
            # linked_folders_serializer = FolderSerializer(linked_folders, many=True, isShare=isShare_bool)
            # linked_folders_serializer = FolderSerializer(linked_folders, many=True)

            data = []
            for item in linked_folders:
                    share_data = ShareContentFolderSerializer(item).data
                    share_data['folder']['isShare'] = True
                    share_data['folder']['shareId'] = share_data['id']
                    
                    data.append(share_data['folder'])

            return APIResponse({
                # 'linked_files': linked_file_contents_serializer.data,
                # 'linked_document': linked_document_contents_serializer.data,
                'child_folders': data,
                # 'folder_path': folder_path
            })


        elif folder_id and not isShare_bool:
            linked_folders = Folder.objects.filter(user=user, parent_folder=folder_id, is_delete=False)
        else:
            # Fetch all prompts without a folder
            # linked_file_contents = UserContent.objects.filter(user=user, is_delete=False, folder=None)

            # linked_document_contents = Document.objects.filter(user=user, is_delete=False, folder=None)
            # Fetch all folders without a parent folder
            linked_folders = Folder.objects.filter(user=user, parent_folder=None, is_delete=False)

        # Apply search filter if query exists
        if search_query:
            # linked_file_contents = linked_file_contents.filter(Q(prompt__prompt_text__icontains=search_query) | Q(fileName__icontains=search_query) | Q(description__icontains = search_query))

            linked_folders = linked_folders.filter(title__icontains=search_query)

        # linked_file_contents = linked_file_contents.order_by('-created_at')
        # linked_file_contents_serializer = ContentLibrarySerializer(linked_file_contents, many=True)

        # linked_document_contents = linked_document_contents.order_by('-created_at')
        # linked_document_contents_serializer = DocumentContentSerializer(linked_document_contents, many=True)

        linked_folders = linked_folders.order_by('-created_at')
        # linked_folders_serializer = FolderSerializer(linked_folders, many=True, isShare=isShare_bool)

        # linked_folders_serializer = FolderSerializer(linked_folders, many=True)
        data = []
        for item in linked_folders:
            folder_data = FolderSerializer(item).data
            folder_data['isShare'] = False
            data.append(folder_data)

        return APIResponse({
            # 'linked_files': linked_file_contents_serializer.data,
            # 'linked_document': linked_document_contents_serializer.data,
            'child_folders': data,
            # 'folder_path': folder_path
        })


class PromptSingleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        try:
            user = request.user
            prompt_id = request.GET.get('id')
            prompt = Prompt.objects.get(id=prompt_id, user=user)
            serializer = SinglePromptSerializer(prompt)
            return APIResponse({'payload':serializer.data,'status':200})
        except Prompt.DoesNotExist:
            return APIResponse({'error': 'Prompt not found.','status':400})

    def patch(self, request):
        try:
            data = request.data
            data=data.copy()
            promptId = data.get('prompt')
            data['is_saved'] = True
            
            prompt = Prompt.objects.get(id=promptId)
            serializer = PromptUpdateSerializer(instance=prompt,data=data)
            if serializer.is_valid():
                serializer.save()
            
                return APIResponse({'payload': serializer.data, 'status': 200})
            else:
                return APIResponse({'error': serializer.errors, 'status':400})
            
        except Prompt.DoesNotExist:
            return APIResponse({'error':'Prompt not found!', 'status': 404})

        except Exception as e:
            return APIResponse({'error': str(e), 'status': 500})
        
class NoteBookListingView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        folder_id = request.GET.get('id')
        search_query = request.GET.get('q')
        folder_path = []

        # Base queryset for linked notes and folders
        linked_notes = NoteBook.objects.filter(user=user)
        linked_folders = Folder.objects.filter(user=user, content_type='notebook')

        # Apply folder_id filter if provided
        if folder_id:
            linked_notes = linked_notes.filter(folder_id=folder_id)
            linked_folders = linked_folders.filter(parent_folder_id=folder_id)
        else:
            linked_notes = linked_notes.filter(folder=None)
            linked_folders = linked_folders.filter(parent_folder=None)

        # Apply search filter if search_query is provided
        if search_query:
            linked_notes = linked_notes.filter(
                Q(label__icontains=search_query) | Q(content__icontains=search_query)
            )
            linked_folders = linked_folders.filter(
                title__icontains=search_query
            )

        # Serialize data
        linked_notes_serializer = NoteBookListSerializer(linked_notes, many=True)
        linked_folders_serializer = FolderSerializer(linked_folders, many=True)

        return APIResponse({
            'root_files': linked_notes_serializer.data,
            'root_folders': linked_folders_serializer.data,
            'folder_path': folder_path
        })
   
        


    
class NoteBookView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        try:
            user = request.user
            note_id = request.GET.get('note_id')
            notebook = NoteBook.objects.get(id=note_id, user=user)
            serializer = SingleNoteBookSerializer(notebook)
            return APIResponse({'payload':serializer.data,'status':200})
        except NoteBook.DoesNotExist:
            return APIResponse({'error': 'note not found.','status':400})
    def post(self, request):
        prompt_ids = request.data.get('prompt_ids')
        content = request.data.get('content')
        note_id = request.data.get('note_id')
        
        try:
            with transaction.atomic():
                user = request.user

               
                note = NoteBook.objects.select_related('folder').get(pk=note_id, user=user)
                note.content = content

                if prompt_ids:
            

                    # Filter out existing prompts associated with the note
                    existing_prompt_ids = note.prompts.filter(id__in=prompt_ids).values_list('id', flat=True)
                    new_prompt_ids = [prompt_id for prompt_id in prompt_ids if prompt_id not in existing_prompt_ids]

                    # Bulk create Reference instances
                    references = [NoteBook.prompts.through(notebook_id=note.id, prompt_id=prompt_id) for prompt_id in new_prompt_ids]
                    NoteBook.prompts.through.objects.bulk_create(references)

                note.save()

                return APIResponse({'message': 'Added to NoteBook', 'status': 201, 'title': note.label})

        except (NoteBook.DoesNotExist, Folder.DoesNotExist):
            return APIResponse({'message': 'NoteBook or Folder not found.', 'status': 400})

        
    def patch(self,request):
        try:

            user = request.user
            content= request.data.get('content')
            note_id = request.data.get('note_id')
            notebook = NoteBook.objects.get(id=note_id, user=user)
            notebook.content = content
            notebook.save()
            return APIResponse({'message':'Edited','status':200})
        except Prompt.DoesNotExist:
            return APIResponse({'error': 'Prompt not found.','status':400})
        

class PromptLibraryFolderList(ListAPIView):
     permission_classes = [IsAuthenticated]
     serializer_class=FolderSerializer

     def get_queryset(self):
        
        user = self.request.user
        
        # Filter folders by user and content type 'prompt'
        queryset = Folder.objects.filter(user=user, content_type='prompt')
        
        return queryset

class PromptsFolder(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            folder_id = request.GET.get('id')
            if folder_id:
                # If folder_id is provided, fetch subfolders of the specified folder
                folder = Folder.objects.get(id=folder_id)
                subfolders = folder.subfolders.all()
                serializer = FolderSerializer(subfolders, many=True)
            else:
                # If folder_id is not provided, fetch top-level folders
                top_level_folders = Folder.objects.filter(user=request.user ,content_type='prompt', parent_folder=None)
                # print(top_level_folders)
                serializer = FolderSerializer(top_level_folders, many=True)
                
            return APIResponse(serializer.data)
        except Folder.DoesNotExist:
            return APIResponse({'error': 'Folder does not exist', 'status': 404})
        except Exception as e:
            return APIResponse({'error': str(e), 'status': 400})


    def post(self, request):
        try:
            title = request.data.get('title')
            user = request.user
            content_type = 'prompt'  
            parent_folder_id = request.data.get('parent_folder')

            # Check if parent_folder_id is provided
            if parent_folder_id:
                parent_folder = Folder.objects.get(id=parent_folder_id)
                folder = Folder.objects.create(title=title, user=user, content_type=content_type, parent_folder=parent_folder)
            else:
                folder = Folder.objects.create(title=title, user=user, content_type=content_type)


            serializer = FolderSerializer(folder)


            # Return success response with serialized folder data
            return APIResponse({'message':'folder created', 'status':201,'data':serializer.data})

        except Exception as e:
            # Return error response if an exception occurs
            return APIResponse({'error': str(e),'status':400})

class FolderMngt(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    # def get(self, request):
    #     try:
    #         folder_id = request.GET.get('id')
    #         if folder_id:
    #             # If folder_id is provided, fetch subfolders of the specified folder
    #             folder = Folder.objects.get(id=folder_id, is_delete=False)
    #             subfolders = folder.subfolders.all()
    #             serializer = FolderSerializer(subfolders, many=True)
    #         else:
    #             # If folder_id is not provided, fetch top-level folders
    #             top_level_folders = Folder.objects.filter(user=request.user, parent_folder=None)
    #             # print(top_level_folders)
    #             serializer = FolderSerializer(top_level_folders, many=True)
                
    #         return APIResponse(serializer.data, status=status.HTTP_200_OK)
    #     except Folder.DoesNotExist:
    #         return APIResponse({'message': 'Folder does not exist'}, status=status.HTTP_404_NOT_FOUND)
    #     except Exception as e:
    #         return APIResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # user_type = request.GET.get('userType', 'false')

        # user_bool = user_type.lower() == 'true'
        if pk is not None:
            try:
                folder = Folder.objects.get(id=pk, is_delete=False)
            except Folder.DoesNotExist:
                return Response("Folder does not exist", status=status.HTTP_404_NOT_FOUND)
            
            serializer = FolderOutputSerializer(folder)
            return Response(serializer.data, status=status.HTTP_200_OK)

        folder = Folder.objects.filter(is_delete=False)
        
        folder = folder.order_by('-created_at')
        page = paginator.paginate_queryset(folder, request)
        serializer = FolderOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)


    def post(self, request):
        title = request.data.get('title')
        user = request.user.id
        parent_folder_id = request.data.get('parent_folder', None)

        # Check if parent_folder_id is provided
        if parent_folder_id:
            is_folder = Folder.objects.filter(title=title, user=user, parent_folder=parent_folder_id).exists()
            if is_folder:
                return Response({"message": "A folder with this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                parent_folder = Folder.objects.get(id=parent_folder_id)
            except Folder.DoesNotExist:
                return Response({"message": "Provide Parent Folder Not Found"}, status=status.HTTP_404_NOT_FOUND)
            # folder = Folder.objects.create(title=title, user=user, parent_folder=parent_folder)
            data = {
                "title": title,
                "user": user,
                "parent_folder": parent_folder.id
            }
        else:
            is_folder = Folder.objects.filter(title=title, user=user, parent_folder__isnull=True).exists()
            if is_folder:
                return Response({"message": "A folder with this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
            
            # folder = Folder.objects.create(title=title, user=user)
            data = {
                "title": title,
                "user": user,
            }


        serializer = CreateFolderSerializer(data=data, many=False)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk=None):
        try:
            folder = Folder.objects.get(pk=pk, is_delete=False)
        except Folder.DoesNotExist:
            return Response({"message": "Folder Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateFolderSerializer(folder, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "Folder Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "Folder Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class GetUserFolderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):

        folder = Folder.objects.filter(user=request.user, is_delete=False, is_active=True)
        
        folder = folder.order_by('-created_at')
        serializer = FolderOutputSerializer(folder, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# def upload_folder_structure_to_drive(user, service, folder_data, parent_id=None):
def delete_folders_file(user, folder_data, folder_list):
    """
    Recursively uploads folders to Google Drive while maintaining the structure.
    """

    for folder in folder_data:
        files = get_files(user, folder['id'])

        documents = get_documents(user, folder['id'])

        folder_list.append(folder['id'])

        storage = StorageUsage.objects.filter(user=user, is_delete=False).first()

        for document in documents:
            doc_obj = Document.objects.filter(id=document['id'], is_delete=False).first()
            doc_obj.delete()
            
            if storage:
                storage.total_storage_used -= doc_obj.size
                storage.save()

        for file in files:
            file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()

            s3_file_key = file['file']

            sStatus = delete_file_from_s3(s3_file_key)

            file_obj.delete()

            if storage:
                storage.total_storage_used -= file_obj.fileSize
                storage.save()


        
        # Recursively create subfolders
        if folder['subfolders']:
            delete_folders_file(user, folder['subfolders'], folder_list)

    return folder_list  

class DeleteFolderView(APIView):
    def delete(self, request, pk=None):
        user = request.user
        try:
            folder = Folder.objects.get(pk=pk, is_delete=False)
        except Folder.DoesNotExist:
            return Response({"message": "Folder Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        folder_list = [pk]     
        folderName, folder_data = get_folder_detail(user, pk)

        files = get_files(user, pk)

        documents = get_documents(user, pk)

        storage = StorageUsage.objects.filter(user=user, is_delete=False).first()

        for document in documents:
            doc_obj = Document.objects.filter(id=document['id'], is_delete=False).first()
            doc_obj.delete()
            
            if storage:
                storage.total_storage_used -= doc_obj.size
                storage.save()

        for file in files:
            file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()

            # if file['content_type'] == 'document':
            #     file_obj.delete()
            #     if storage:
            #         storage.total_storage_used -= file_obj.fileSize
            #         storage.save()
            # else:
            s3_file_key = file['file']
            sStatus = delete_file_from_s3(s3_file_key)

            file_obj.delete()  
            if storage:
                storage.total_storage_used -= file_obj.fileSize
                storage.save()


        new_folder_list = delete_folders_file(user, folder_data, folder_list)

        # print("List is ---> ", new_folder_list)
        Folder.objects.filter(id__in=new_folder_list).delete()

        return Response({"message": "Folder Delete"}, status=status.HTTP_200_OK)
    


class FolderDetailView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        shareByMe = request.GET.get('shareByMe', 'false')
        shareByMe = shareByMe.lower() == 'true'
        shareToMe = request.GET.get('shareToMe', 'false')
        shareToMe = shareToMe.lower() == 'true'
        user = request.user
        
        folders = []

        if shareByMe:
            shares = Share.objects.filter(owner=user, content_type='folder', main_folder__isnull=True, is_delete=False)

        elif shareToMe:
            shares = Share.objects.filter(share_to_user=user, content_type='folder', main_folder__isnull=True, is_delete=False)
        else:
            # Retrieve folders where the user is the owner
            folders = Folder.objects.filter(user=user, parent_folder__isnull=True, is_delete=False)

            # Retrieve shares where the user is the shared recipient and content_type is 'folder'
            shares = Share.objects.filter(share_to_user=user, content_type='folder', main_folder__isnull=True, is_delete=False)

        if searchBy:
            folders = folders.filter(title__icontains=searchBy)

        if searchBy:
            shares = shares.filter(folder__title__icontains=searchBy)
            
        # Combine the querysets
        combined_queryset = sorted(
            list(folders) + list(shares),
            key=lambda instance: instance.created_at,
            reverse=True
        )

        page = paginator.paginate_queryset(combined_queryset, request)
        # page = paginator.paginate_queryset(folders, request)

        # data = FolderListSerializer(page, many=True).data

        # Serialize the data
        data = []
        for item in page:
            if isinstance(item, Folder):
                root_data =  FolderListSerializer(item).data
                root_data['isShare'] = False
                data.append(root_data)
            elif isinstance(item, Share):
                share_data = ShareContentFolderSerializer(item).data
                share_data['folder']['isShare'] = True
                share_data['folder']['shareId'] = share_data['id']
                
                data.append(share_data['folder'])
                # data.append(share_data)

        total_pages = paginator.page.paginator.num_pages

        response_data = {
            'total_pages': total_pages,
            'results': data
        }

        return paginator.get_paginated_response(response_data)


        

class NoteBookFolderList(ListAPIView):
     permission_classes = [IsAuthenticated]
     def get(self, request):
        try:
            folder_id = request.GET.get('id')
            if folder_id:
                # If folder_id is provided, fetch subfolders of the specified folder
                folder = Folder.objects.get(id=folder_id)
                subfolders = folder.subfolders.all()
                serializer = FolderSerializer(subfolders, many=True)
            else:
                # If folder_id is not provided, fetch top-level folders
                top_level_folders = Folder.objects.filter(user=request.user ,content_type='notebook', parent_folder=None)
                # print(top_level_folders)
                serializer = FolderSerializer(top_level_folders, many=True)
                
            return APIResponse(serializer.data)
        except Folder.DoesNotExist:
            return APIResponse({'error': 'Folder does not exist', 'status': 404})
        except Exception as e:
            return APIResponse({'error': str(e), 'status': 400})
     

class NotesFolder(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            title = request.data.get('title')
            user = request.user
            content_type = 'notebook'  
            parent_folder_id = request.data.get('parent_folder')

            # Check if parent_folder_id is provided
            if parent_folder_id:
                parent_folder = Folder.objects.get(id=parent_folder_id)
                folder = Folder.objects.create(title=title, user=user, content_type=content_type, parent_folder=parent_folder)
            else:
                folder = Folder.objects.create(title=title, user=user, content_type=content_type)


            serializer = FolderSerializer(folder)


            # Return success response with serialized folder data
            return APIResponse({'message':'folder created', 'status':201,'data':serializer.data})

        except Exception as e:
            # Return error response if an exception occurs
            return APIResponse({'error': str(e),'status':400})


class NoteListForModal(ListAPIView):
     permission_classes = [IsAuthenticated]
     serializer_class=NoteBookListSerializer

     def get_queryset(self):
        
        user = self.request.user
        queryset = NoteBook.objects.filter(user=user)
        
        return queryset
     

class CurrentNoteBook(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        try:
            user = request.user   
            notebook = NoteBook.objects.filter(user=user,is_open=True).first()
            
            if notebook:
                serializer = SingleNoteBookSerializer(notebook)
                return APIResponse({'payload': serializer.data, 'status': 200})
            else:
                # If no notebook with is_open=True is found, return a different response
                return APIResponse({'message': 'No open notebook found.', 'status': 404})
        except Exception as e:
            return APIResponse({'error': str(e), 'status': 500})
        

    def post(self,request):
        note_id = request.data.get('note_id')
        folder_id = request.data.get('folder')
        try:

            if note_id:  
                try:
                    note = NoteBook.objects.get(pk=note_id)
                    NoteBook.objects.exclude(pk=note_id).update(is_open=False)
                    note.is_open =True
                    note.save()

                    
                except NoteBook.DoesNotExist:
                    return APIResponse({'message': 'NoteBook not found.','status' : 400})
            else:
                NoteBook.objects.update(is_open=False)
                # Create a new NoteBook instance
                label = request.data.get('label')
                if not label:
                    return APIResponse({'message': 'Label is required for a new NoteBook.','status' : 400})
                try:
                    folder_instance= Folder.objects.get(id=folder_id)
                    note = NoteBook.objects.create(user=request.user, label=label,folder=folder_instance,is_open=True)
                except Folder.DoesNotExist:
                    note = NoteBook.objects.create(user=request.user, label=label,is_open=True)

            return APIResponse({'message': 'NoteBook opened','status':201,'title':note.label})

        except NoteBook.DoesNotExist:
            return APIResponse({'message': 'notebook not found.','status' : 400})

class CloseNoteBook(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self,request):
        try:
            user = request.user
            notebook_id = request.data.get('notebook_id')

            # Retrieve the notebook
            notebook = NoteBook.objects.get(pk=notebook_id, user=user)

            # Close the notebook by setting is_open to False
            notebook.is_open = False
            notebook.save()

            return APIResponse({'message': 'Notebook closed', 'status': 200})

        except NoteBook.DoesNotExist:
            return APIResponse({'error': 'Notebook not found.', 'status': 404})
        except Exception as e:
            return APIResponse({'error': str(e), 'status': 500})
        
def clean_string(s):
    s = s.replace('\\n', '')  # Remove literal \n
    s = s.replace('\\', '')   # Remove literal \
    return s
        

# Create LLM Model
class CreateLLMModel(APIView):

    def post(self, request):
        data = request.data.copy()
        # data['user'] = request.user.id

        code_string = request.data.get("code_for_integrate")
        source = request.data.get("source")

        # if 'client.chat.completions.create(' in code_string:
        #     return Response({"message": "True"}, status=status.HTTP_400_BAD_REQUEST)
        # else:
        #     return Response({"message": "False"}, status=status.HTTP_400_BAD_REQUEST)
            
        if not source:
            return Response({"message": "Please provide model source"}, status=status.HTTP_400_BAD_REQUEST)
        # Define a regular expression pattern to find the model parameter value

        if int(source) == 2:
            text_string = "Together"
        elif int(source) == 3:
            text_string = "Gemini"
        elif int(source) == 4:
            text_string = "OpenAI"

        if int(source) == 2:
            model_pattern = r'model="([^"]+)"'
        elif int(source) == 3:
            # model_pattern = r'model_name="([^"]+)"'
            model_pattern = r'genai\.GenerativeModel\(\"([^\"]*)\"\)'
        elif int(source) == 4:
            model_pattern = r'model="([^"]+)"'
        else:
            return Response({"message": "Source not in proper format/number"}, status=status.HTTP_400_BAD_REQUEST)

        new_code_string = clean_string(code_string)

        if 'client.chat.completions.create' in new_code_string and int(source)==2:
            data['text'] = True
            # data['prompt'] = True
        elif 'client.completions.create' in new_code_string and int(source)==2:
            data['code'] = True
            # data['prompt'] = True
        elif 'client.images.generate' in new_code_string and int(source)==2:
            data['text_to_image'] = True
            # data['prompt'] = True

        elif 'model.generate_content("' in new_code_string and int(source)==3:
            data['text'] = True
            # data['prompt'] = True
        elif 'model.generate_content([' in new_code_string and int(source)==3:
            # data['image_audio_to_text'] = True
            data['image_to_text'] = True
            # data['prompt'] = True
            # data['image'] = True
            # data['audio'] = True
            # data['audio_to_text'] = True
        elif 'request_options' in new_code_string and int(source)==3:
            data['video_to_text'] = True
            # data['prompt'] = True
            # data['video'] = True
        elif 'tools' in new_code_string and int(source)==3:
            data['code'] = True
            # data['prompt'] = True
            # data['tools'] = True

        elif 'chat.completions.create' in new_code_string and int(source)==4:
            data['text'] = True
            # data['prompt'] = True
        elif 'images.generate' in new_code_string and int(source)==4:
            data['text_to_image'] = True
            # data['prompt'] = True
        elif 'audio.speech.create' in new_code_string and int(source)==4:
            data['text_to_audio'] = True
            # data['prompt'] = True
        elif 'audio.transcriptions.create' or 'audio.translations.create' in new_code_string and int(source)==4:
            data['audio_to_text'] = True
            # data['audio'] = True

        else:
            return Response({"message": f"Please check code for integration format for {text_string} "}, status=status.HTTP_400_BAD_REQUEST)


        # max_tokens_pattern = r'max_tokens=(\d+)'
        # temperature_pattern = r'temperature=(-?\d+\.?\d*)'
        # top_p_pattern = r'top_p=(-?\d+\.?\d*)'
        # top_k_pattern = r'top_k=(\d+)'
        # repetition_penalty_pattern = r'repetition_penalty=(-?\d+\.?\d*)'
        
        # stop_pattern = r'stop=(\[[^\]]+\])'

        # Search the code string for the model parameter value
        match_model = re.search(model_pattern, new_code_string)

        # match_max_tokens = re.search(max_tokens_pattern, code_string)
        # match_temperature = re.search(temperature_pattern, code_string)
        # match_top_p = re.search(top_p_pattern, code_string)
        # match_top_k = re.search(top_k_pattern, code_string)
        # match_repetition_penalty = re.search(repetition_penalty_pattern, code_string)
        # match_stop = re.search(stop_pattern, code_string)

        # print("Max Token is ----> ", match_max_tokens)
        # print("match_temperature is ----> ", match_temperature)
        # print("match_top_p is ----> ", match_top_p)
        # print("match_top_k is ----> ", match_top_k)
        # print("match_repetition_penalty is ----> ", match_repetition_penalty)
        # print("match_stop is ----> ", match_stop)



        if match_model:
            model_name = match_model.group(1)
            data['model_string'] = model_name
            # print(f"Model Name: {model_name}")
        else:
            # print("Model parameter not found in the code string.")
            return Response({"message": f"Please check code for integration format for {text_string}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if match_max_tokens:
        #     max_tokens = match_max_tokens.group(1)
        #     data['max_tokens'] = max_tokens
        
        # if match_temperature:
        #     temperature = match_temperature.group(1)
        #     data['temperature'] = temperature
        
        # if match_top_p:
        #     top_p = match_top_p.group(1)
        #     data['top_p'] = top_p
        
        # if match_top_k:
        #     top_k = match_top_k.group(1)
        #     data['top_k'] = top_k
        
        # if match_repetition_penalty:
        #     repetition_penalty = match_repetition_penalty.group(1)
        #     data['repetition_penalty'] = repetition_penalty
        
        # if match_stop:
        #     stop = match_stop.group(1)
        #     data['stop'] = stop
        
        

        serializer = LlmSerializer(data=data, many=False)

        # Explicitly call validate_model_string to debug
        if 'model_string' in data:
            serializer.validate_model_string(data['model_string'])

        # # Explicitly call validate_model_string to debug
        if 'name' in data:
            serializer.validate_name(data['name'])

        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get LLM Model
class GetLLMModel(APIView):
    # pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        # paginator = self.pagination_class()
        show_all = request.GET.get('showAll', 'false')
        show_all = show_all.lower() == 'true'
        
        if pk is not None:
            try:
                llm = LLM.objects.get(pk=pk, is_delete=False)
            except LLM.DoesNotExist:
                return Response("Category Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = LlmSerializerWOPage(llm)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # category_id = request.query_params.get('category_id') 
        if show_all:
            queryset = LLM.objects.filter(is_delete=False)
        else:
            queryset = LLM.objects.filter(is_enabled=True, is_delete=False, test_status="connected")
        # if category_id != 'null':
            # queryset = queryset.filter(category_id=category_id)

        queryset = queryset.order_by('-created_at')
        # page = paginator.paginate_queryset(queryset, request)
        serializer = LlmSerializerWOPage(queryset, many=True)
        # total_pages = paginator.page.paginator.num_pages
        # response_data = {
        #     'total_pages': total_pages,
        #     'results': serializer.data
        # }

        # return paginator.get_paginated_response(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# # Get LLM Model For User
# class GetLLMModelByUser(APIView):
#     pagination_class = PageNumberPagination

#     def get(self, request, pk=None):
#         paginator = self.pagination_class()
#         if pk is not None:
#             try:
#                 user_llm = UserLLM.objects.get(pk=pk, is_delete=False)
#             except LLM.DoesNotExist:
#                 return Response("User LLM Not Found", status=status.HTTP_404_NOT_FOUND)
            
#             # serializer = GetLlmSerializer(llm, context={'user_id': request.user.id})
#             serializer = UserLlmGetSerializer(user_llm)
#             return Response(serializer.data, status=status.HTTP_200_OK)

#         # category_id = request.query_params.get('category_id') 
#         queryset = UserLLM.objects.filter(user=request.user.id, enabled=True, is_delete=False)
#         # if category_id != 'null':
#             # queryset = queryset.filter(category_id=category_id)

#         queryset = queryset.order_by('-created_at')
#         page = paginator.paginate_queryset(queryset, request)
#         serializer = UserLlmGetSerializer(page, many=True)
#         total_pages = paginator.page.paginator.num_pages
#         response_data = {
#             'total_pages': total_pages,
#             'results': serializer.data
#         }

#         return paginator.get_paginated_response(response_data)
#         # return Response(serializer.data, status=status.HTTP_200_OK)


# Get LLM Model For User
class GetAllLLMModelByUser(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        if pk is not None:
            try:
                user_llm = LLM.objects.get(pk=pk, is_delete=False, is_enabled=True)
            except LLM.DoesNotExist:
                return Response("LLM Not Found", status=status.HTTP_404_NOT_FOUND)
            
            # serializer = GetLlmSerializer(llm, context={'user_id': request.user.id})
            serializer = UserLlmGetSerializer(user_llm)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # category_id = request.query_params.get('category_id') 
        queryset = LLM.objects.filter(is_enabled=True, is_delete=False)

        if searchBy:
            queryset = queryset.filter(
                Q(name__icontains=searchBy) | 
                Q(powered_by__icontains=searchBy) |
                Q(trained_lang__icontains=searchBy) |
                Q(capabilities__icontains=searchBy))
        # if category_id != 'null':
            # queryset = queryset.filter(category_id=category_id)

        queryset = queryset.order_by('-created_at')
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserLlmGetSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
        # return Response(serializer.data, status=status.HTTP_200_OK)


# Get LLM Model For User
class GetLLMModelByAdmin(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()

        searchBy = request.GET.get('searchBy')
        connection = request.GET.get('connection')
        isEnabled = request.GET.get('isEnabled')
        rating = request.GET.get('rating')

        if pk is not None:
            try:
                llm = LLM.objects.get(pk=pk, is_delete=False)
            except LLM.DoesNotExist:
                return Response("LLM Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = LlmSerializerByAdmin(llm)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # category_id = request.query_params.get('category_id') 
        queryset = LLM.objects.filter(is_delete=False)
        if searchBy:
            queryset = queryset.filter(
                Q(name__icontains=searchBy) | 
                Q(powered_by__icontains=searchBy) |
                Q(trained_lang__icontains=searchBy) |
                Q(capabilities__icontains=searchBy))
            
        if connection:
            queryset = queryset.filter(test_status=connection)
            
        if isEnabled:
            queryset = queryset.filter(is_enabled=isEnabled)
            
        if rating:
            queryset = queryset.filter(llm_ratings__rating=rating)

        queryset = queryset.order_by('-created_at')
        page = paginator.paginate_queryset(queryset, request)
        serializer = LlmSerializerByAdmin(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
        # return Response(serializer.data, status=status.HTTP_200_OK)

# Get LLM Model
class GetLLMModelByIds(APIView):

    def post(self, request, pk=None):

        modleIds = request.data.get('llm_models', []) 
        models = LLM.objects.filter(id__in=modleIds, is_enabled=True, is_delete=False)

        serializer = LlmSerializer(models, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


# Update LLM Model
class UpdateLLMModel(APIView):
    
    def patch(self, request, pk=None):
        source = request.data.get("source")
        try:
            llm = LLM.objects.get(pk=pk, is_delete=False)
        except LLM.DoesNotExist:
            return Response("Model Not Found", status=status.HTTP_404_NOT_FOUND)
        
        data = request.data.copy()

        code_string = request.data.get("code_for_integrate", None)
        api_key = request.data.get("api_key", None)
        isEnabled = request.data.get("is_enabled", None)
        connection = request.data.get("test_status", None)

        if api_key:
            data["test_status"] = "disconnected"


        if code_string:
            # Define a regular expression pattern to find the model parameter value
            # model_pattern = r'model="([^"]+)"'

            if int(source) == 2:
                text_string = "Together"
            elif int(source) == 3:
                text_string = "Gemini"
            elif int(source) == 4:
                text_string = "OpenAI"

            if int(source) == 2:
                model_pattern = r'model="([^"]+)"'
            elif int(source) == 3:
                # model_pattern = r'model_name="([^"]+)"'
                model_pattern = r'genai\.GenerativeModel\(\"([^\"]*)\"\)'
            elif int(source) == 4:
                model_pattern = r'model="([^"]+)"'
            else:
                return Response({"message": "Source not in proper format/number"}, status=status.HTTP_400_BAD_REQUEST)

            new_code_string = clean_string(code_string)


            match_model = re.search(model_pattern, new_code_string)

            if match_model:
                model_name = match_model.group(1)
                data['model_string'] = model_name
                data["test_status"] = "disconnected"
                remove_llm_model(llm.id)
            else:
                return Response({"message": f"Please check code for integration format for {text_string}"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = LlmSerializer(llm, data=data, partial=True)
        # serializer = LlmSerializer(data=data, many=False)

        # Explicitly call validate_model_string to debug
        if 'model_string' in data:
            serializer.validate_model_string(data['model_string'])

        # # Explicitly call validate_model_string to debug
        if 'name' in data:
            serializer.validate_name(data['name'])
            
        if serializer.is_valid():
            serializer.save()

            if api_key or not isEnabled or connection == "disconnected":
                remove_llm_model(llm.id)
            
            # return Response(serializer.data, status=status.HTTP_200_OK)
            return Response("LLM Model Update", status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete LLM Model
class DeleteLLMModel(APIView):
    
    def patch(self, request, pk=None):
        try:
            llm = LLM.objects.get(pk=pk, is_delete=False)
        except LLM.DoesNotExist:
            return Response("Model Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = LlmSerializer(llm, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            remove_llm_model(llm.id)

            return Response("LLM Model Delete", status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Create Document
class PromptDocument(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        title = request.data.get('title', None)
        content = request.data.get('content', None)

        if not content and not title:
            return Response({"message": "Please provide title and content."}, status=status.HTTP_400_BAD_REQUEST)
        # Check user's current storage usage

        storage = StorageUsage.objects.filter(user=request.user.id, is_delete=False).first()

        if not storage:
            storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage").first()

            # Create Free Storage Plan for a User
            if storage_plan:
                storage = StorageUsage.objects.create(
                    user_id = request.user.id, 
                    plan_id = storage_plan.id,
                    storage_limit = storage_plan.storage_size,
                    subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                    subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                    description = "This is Free Plan For Trial Period", 
                    status = "trial", 
                    transactionId = "trial", 
                    payment_status = "trial", 
                    payment_mode = "online",

                    plan_name = storage_plan.plan_name,
                    plan_for = storage_plan.plan_for,
                    amount =  storage_plan.amount,
                    duration = storage_plan.duration,
                    feature = storage_plan.feature,
                    discount = storage_plan.discount
                )
        if storage:   
            byte_size = len(content.encode('utf-8'))
            # Calculate new total usage if this file is uploaded
            new_total_storage_used = storage.total_storage_used + byte_size

            if new_total_storage_used > storage.storage_limit:
                return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

            data['size'] = byte_size
            serializer = DocumentAddSerializer(data=data, many=False)
            if serializer.is_valid():

                serializer.save()

                storage.total_storage_used = new_total_storage_used
                storage.save()

                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"message": "No storage plan found. Plz buy a storage plan."}, status=status.HTTP_404_NOT_FOUND)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        search = request.GET.get('search')
        if pk is not None:
            try:
                document = Document.objects.get(pk=pk, is_delete=False)
            except Document.DoesNotExist:
                return Response("Document Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = DocumentSerializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # category_id = request.query_params.get('category_id') 
        queryset = Document.objects.filter(enabled=True, is_delete=False,user=request.user.id)

        if search != 'null':
            queryset = queryset.filter(
                Q(llm_model__icontains=search) | 
                Q(title__icontains=search) | 
                Q(content__icontains=search)
            )

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = DocumentSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            document = Document.objects.get(pk=pk, is_delete=False)
        except Document.DoesNotExist:
            return Response("Document Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = DocumentAddSerializer(document, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "Document Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "Document Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Get Prompt Response
class PromptResponseDetail(APIView):
    # pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        # paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                response = PromptResponse.objects.get(pk=pk, is_delete=False)
            except PromptResponse.DoesNotExist:
                return Response("Response Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = SingleRespSerializer(response)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # # category_id = request.query_params.get('category_id') 
        # queryset = Document.objects.filter(enabled=True, is_delete=False,user=request.user.id)

        # if search != 'null':
        #     queryset = queryset.filter(
        #         Q(llm_model__icontains=search) | 
        #         Q(title__icontains=search) | 
        #         Q(content__icontains=search)
        #     )

        # queryset = queryset.order_by('-created_at')

        # page = paginator.paginate_queryset(queryset, request)
        # serializer = DocumentSerializer(page, many=True)
        # total_pages = paginator.page.paginator.num_pages
        # response_data = {
        #     'total_pages': total_pages,
        #     'results': serializer.data
        # }

        # return paginator.get_paginated_response(response_data)


# Get Prompt Detail
class PromptDetail(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        categoryId = request.GET.get('categoryId')
        # groupId = request.GET.get('groupId')
        # chatbot = chatbot.lower() == 'true'

        paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                response = Prompt.objects.get(pk=pk, is_delete=False)
            except Prompt.DoesNotExist:
                return Response("Prompt Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = PromptSerializer(response)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # category_id = request.query_params.get('category_id') 

        # if search != 'null':
        #     queryset = queryset.filter(
        #         Q(llm_model__icontains=search) | 
        #         Q(title__icontains=search) | 
        #         Q(content__icontains=search)
        #     )

        # if groupId:
        #     queryset = Prompt.objects.filter(enabled=True, is_delete=False, user=request.user.id, group=groupId)

        #     queryset = queryset.order_by('-created_at')
        #     serializer = PromptSerializer(queryset, many=True)
        #     return Response(serializer.data, status=status.HTTP_200_OK)
        # else:
        if categoryId != 'null':
            queryset = Prompt.objects.filter(category=categoryId, enabled=True, is_delete=False, user=request.user.id)
        else:
            queryset = Prompt.objects.filter(enabled=True, is_delete=False, user=request.user.id)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = PromptSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            document = Prompt.objects.get(pk=pk, is_delete=False)
        except Prompt.DoesNotExist:
            return Response("Document Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = DeletePromptSerializer(document, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Prompt Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Get Prompt Detail
class GroupHistoryView(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        # categoryId = request.GET.get('categoryId')
        # groupId = request.GET.get('groupId')
        # chatbot = chatbot.lower() == 'true'

        paginator = self.pagination_class()


        queryset = Prompt.objects.filter(enabled=True, is_delete=False, user=request.user.id, group=pk)

        queryset = queryset.order_by('-created_at')
        serializer = GroupHistorySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
    

# Get Prompt Response Image
class PromptResponseImage(APIView):
    # pagination_class = PageNumberPagination

    def get(self, request):
        try:
            response = PromptResponse.objects.filter(user=request.user.id, is_delete=False).exclude(response_image__exact='').exclude(response_image__isnull=True)
            
            response = response.order_by('-created_at')[:10]
        except PromptResponse.DoesNotExist:
            return Response("Response Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = PromptImageSerializer(response, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

# Dashborad Count
class UpdateResponseType(APIView):
    # pagination_class = PageNumberPagination

    def get(self, request):

        promptValues = PromptResponse.objects.all()

        for promptValue in promptValues:
            if promptValue.llm.name in ['Gemini Pro', 'Llama 2', 'Mistral', 'Gemma Instruct', 'Gpt-3.5 Trubo', 'Gpt-4']:
                promptValue.response_type = 2
                promptValue.tokenUsed = 10
                promptValue.save()

            elif promptValue.llm.name in ['Gemini Pro Vision']:
                promptValue.response_type = 3
                promptValue.tokenUsed = 10
                promptValue.save()

            elif promptValue.llm.name in ['Stable Diffusion', 'Openjourney v4', 'Realistic Vision 3.0', 'Analog Diffusion', 'Stable Diffusion 2.1']:
                promptValue.response_type = 4
                promptValue.tokenUsed = 1
                promptValue.save()

            elif promptValue.llm.name in ['TTS']:
                promptValue.response_type = 5
                promptValue.tokenUsed = 1
                promptValue.save()

            elif promptValue.llm.name in ['Whisper']:
                promptValue.response_type = 6
                promptValue.tokenUsed = 1
                promptValue.save()

            elif promptValue.llm.name in ['StarCoder (16B)', 'Phind Code LLaMA v2 (34B)', 'Code Llama (70B)']:
                promptValue.response_type = 7
                promptValue.tokenUsed = 10
                promptValue.save()
                
        return Response({"message": "all data updated"}, status=status.HTTP_200_OK)
    
# Function for Count vaues in K, M , B,  T
def format_number(num):
    if abs(num) < 10000:
        return str(num)
    magnitude = 0
    while abs(num) >= 1000 and magnitude < 4:
        magnitude += 1
        num /= 1000.0
    suffixes = ['', 'K', 'M', 'B', 'T']
    return '{:.1f}{}'.format(num, suffixes[magnitude])

# Dashborad Count
class DashboardCount(APIView):
    # pagination_class = PageNumberPagination

    def get(self, request):
                
        textToTextCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=2,
        ).count()

        pictureToTextCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=3
        ).count()

        textToImageCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=4
        ).count()

        textToSpeechCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=5
        ).count()

        speechToTextCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=6
        ).count()

        codeGenerateCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=7
        ).count()

        promptWriteCount = PromptResponse.objects.filter(
            user=request.user.id, 
            is_delete=False, 
            response_type=8
        ).count()


        # totalPromptCount = Prompt.objects.filter(
        #     user=request.user.id, 
        #     is_delete=False
        # ).count()

        totalDocument = Document.objects.filter(
            user=request.user.id, 
            is_delete=False
        ).count()

        subs = Subscription.objects.filter(
            user=request.user.id, 
            status__in=['active', 'trial'],
            is_delete = False,
        ).first()

        if subs:
            avialableToken = subs.balanceToken
            usedTextToken = subs.usedToken
        else:
            usedTextToken = PromptResponse.objects.filter(
                user=request.user.id, 
                response_type__in=[2, 3, 7, 8]).aggregate(
                    total=Sum('tokenUsed')).get('total', 0)
            
            # if request.user.cluster and request.user.cluster.subscription:
            #     try:
            #         cluster_subs = Subscription.objects.get(id=request.user.cluster.subscription.id, status='active')
            #         avialableToken = cluster_subs.balanceToken
            #     except Subscription.DoesNotExist:
            #         avialableToken = 0
            # else:
            #     avialableToken = 0

            cluster = request.user.cluster
            subscription = getattr(cluster, 'subscription', None)

            avialableToken = (
                subscription.balanceToken 
                if subscription and (subscription.status == 'active' or subscription.status == 'trial') 
                else 0
            )


        data = {
            'textToTextCount': textToTextCount,
            'pictureToTextCount': pictureToTextCount,
            'textToImageCount': textToImageCount,
            'textToSpeechCount': textToSpeechCount,
            'speechToTextCount': speechToTextCount,
            'codeGenerateCount': codeGenerateCount,
            'totalPromptCount': promptWriteCount,
            'totalDocument': totalDocument,
            
            # 'avialableToken': subs.balanceToken if subs else 0,
            'avialableToken': avialableToken,
            'usedToken': 0 if usedTextToken is None else usedTextToken,
            'expireToken': subs.expireToken if subs else 0,

            'availableFileToken': subs.fileToken if subs else 0,
            'usedFileToken': subs.usedFileToken if subs else 0,
            'expireFileToken': subs.expireFileToken if subs else 0,
        }

        return Response({"data": data}, status=status.HTTP_200_OK)

# Admin Dashborad Count
class AdminDashboardCount(APIView):
    def get(self, request):
                
        totalRegisterUser = CustomUser.objects.filter(
            is_delete=False, 
            is_verified=True, 
            is_superuser=False
        ).count()

        current_month = datetime.now().month
        current_year = datetime.now().year

        currentMonthRegisterUser = CustomUser.objects.filter(
            is_delete=False, 
            is_verified=True, 
            is_superuser=False, 
            created_at__year=current_year, 
            created_at__month=current_month
        ).count()
                
        totalSubcription = Transaction.objects.filter(
            is_delete=False, 
            payment_status='paid'
        ).count()

        currentMonthSubscription = Transaction.objects.filter(
            is_delete=False,
            payment_status='paid', 
            created_at__year=current_year, 
            created_at__month=current_month
        ).count()


        data = {
            'totalRegisterUser': totalRegisterUser,
            'currentMonthRegisterUser': currentMonthRegisterUser,

            'totalSubcription': totalSubcription,
            'currentMonthSubscription': currentMonthSubscription,
        }

        return Response({"data": data}, status=status.HTTP_200_OK)


class LatestUser(APIView):

    def get(self, request):
        try:
            latestUser = CustomUser.objects.filter(is_blocked=False, is_delete=False, is_verified=True, is_superuser=False)
            
            response = latestUser.order_by('-created_at')[:10]
        except CustomUser.DoesNotExist:
            return Response("Users Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = LatestUserSerializer(response, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LatestTransaction(APIView):

    def get(self, request):
        try:
            response = Transaction.objects.filter(is_delete=False)
            
            response = response.order_by('-created_at')[:10]
        except Transaction.DoesNotExist:
            return Response("Transaction Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = LatestTransactionSerializer(response, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class PerDayUsedToken(APIView):

    def get(self, request):
        start_date = timezone.now() - timedelta(days=30)

        # day_wise_data = PromptResponse.objects.filter(
        #     created_at__gte=start_date)
        
        # day_wise_data = day_wise_data.annotate(date=TruncDate('created_at'))
        # day_wise_data = day_wise_data.values('date')
        # day_wise_data = day_wise_data.annotate(total_tokens=Sum('tokenUsed')) 
        # day_wise_data = day_wise_data.order_by('created_at')


        day_wise_data = PromptResponse.objects.filter(
            user=request.user.id, 
            created_at__gte=start_date,
            response_type__in=[2, 3, 7, 8]
            ).annotate(date=TruncDate('created_at')
            ).values('date'
            ).annotate(total_tokens=Sum('tokenUsed')
        )

        # day_wise_data.order_by('-date')
        
        # serializer = PerDayTokenSerializer(day_wise_data, many=True)
        # return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(day_wise_data, status=status.HTTP_200_OK)
    

# Review and Rating Management
class LLM_Rating(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id

        rating = LLM_Ratings.objects.filter(user=request.user.id, llm=data['llm'], is_delete=False).exists()
        if rating:
            return Response({"message": "You can give single rating for a Model"}, status=status.HTTP_403_FORBIDDEN)


        serializer = LlmRatingSerializer(data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                llm_rating = LLM_Ratings.objects.get(pk=pk, is_delete=False)
            except LLM_Ratings.DoesNotExist:
                return Response({"message": "LLM Rating Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = LlmRatingOutputSerializer(llm_rating)
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = LLM_Ratings.objects.filter(is_delete=False)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = LlmRatingOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            llm_rating = LLM_Ratings.objects.get(pk=pk, is_delete=False)
        except LLM_Ratings.DoesNotExist:
            return Response({"message": "LLM Ratings Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LlmRatingSerializer(llm_rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "LLM Rating Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "LLM Rating Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Review and Rating Management
class RatingByLlm(APIView):
    pagination_class = PageNumberPagination
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        rating = request.GET.get('rating')

        if rating:
            queryset = LLM_Ratings.objects.filter(llm=pk, rating=int(rating), is_delete=False)
        else:
            queryset = LLM_Ratings.objects.filter(llm=pk, is_delete=False)

        if searchBy:
            queryset = queryset.filter(
                Q(review__icontains=searchBy) |
                Q(user__username__icontains=searchBy))

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = LlmRatingOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    

# User LLM Management
class UserLlmMngt(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id

        serializer = UserLlmSerializer(data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                user_llm = UserLLM.objects.get(pk=pk, is_delete=False)
            except UserLLM.DoesNotExist:
                return Response({"message": "User LLM Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = UserLlmGetSerializer(user_llm)
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = UserLLM.objects.filter(is_delete=False)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = UserLlmGetSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            user_llm = UserLLM.objects.get(pk=pk, is_delete=False)
        except UserLLM.DoesNotExist:
            return Response({"message": "User LLM Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserLlmSerializer(user_llm, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "User LLM Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "User LLM Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# User File Management
class UserFileView(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        document_id = request.data.get("document", None)
        self_upload = request.data.get("self_upload", 'false')
        # self_upload = self_upload.lower() == 'true'

        fileSize = request.data.get("fileSize", None)
        uploadedFile = request.data.get("file", None)

        user = request.user
        user_cluster = user.cluster

        # if user_cluster and user_cluster.storage:


        if self_upload:
            if 'file' in request.data and request.data['file']:
                file = request.FILES.get('file')

                if user_cluster and user_cluster.storage:
                    storageId = user_cluster.storage.id
                    storage = StorageUsage.objects.get(id=storageId)

                    # Calculate new total usage if this file is uploaded
                    new_total_storage_used = storage.total_storage_used + file.size

                    if new_total_storage_used > storage.storage_limit:
                        return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

                    objectKey = "multinote/contents/" + str(int(time.time())) + '-' + file.name           
                    response = uploadImage(file, objectKey, file.content_type)

                    if response is None:
                        
                        data['file'] = objectKey
                        data['fileName'] = file.name
                        data['user'] = request.user.id
                        data['fileSize'] = file.size   # Size in Bytes
                        data['is_active'] = data.get('is_active', True) 

                        # if folder_id:
                        #     folder = Folder.objects.filter(id=folder_id, is_delete=False).first()
                        #     if not folder.parent_folder:
                        #         data['folder'] = None


                        serializer = ContentInputSerializer(data=data, many=False)
                        if serializer.is_valid():
                            serializer.save()

                            storage.total_storage_used = new_total_storage_used
                            storage.save()
                            
                            return Response(serializer.data, status=status.HTTP_200_OK)
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                    

                elif user_cluster:
                    storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage", is_for_cluster=True).first()

                    cluster = Cluster.objects.get(id=user_cluster.id)

                    cluster_user = CustomUser.objects.filter(cluster=user_cluster.id, is_cluster_owner=True).first()

                    # Create Free Storage Plan for a User
                    if storage_plan:
                        storage = StorageUsage.objects.create(
                            user_id = cluster_user.id, 
                            plan_id = storage_plan.id,
                            storage_limit = storage_plan.storage_size,
                            subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                            subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                            description = "This is Free Plan For Trial Period", 
                            status = "trial", 
                            transactionId = "trial", 
                            payment_status = "trial", 
                            payment_mode = "online",

                            plan_name = storage_plan.plan_name,
                            plan_for = storage_plan.plan_for,
                            amount =  storage_plan.amount,
                            duration = storage_plan.duration,
                            feature = storage_plan.feature,
                            discount = storage_plan.discount
                        )

                        cluster.storage = storage
                        cluster.save()

                    # if storage:           
                        # Calculate new total usage if this file is uploaded
                        new_total_storage_used = storage.total_storage_used + file.size

                        if new_total_storage_used > storage.storage_limit:
                            return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

                        objectKey = "multinote/contents/" + str(int(time.time())) + '-' + file.name           
                        response = uploadImage(file, objectKey, file.content_type)

                        if response is None:
                            
                            data['file'] = objectKey
                            data['fileName'] = file.name
                            data['user'] = request.user.id
                            data['fileSize'] = file.size   # Size in Bytes
                            data['is_active'] = data.get('is_active', True) 

                            # if folder_id:
                            #     folder = Folder.objects.filter(id=folder_id, is_delete=False).first()
                            #     if not folder.parent_folder:
                            #         data['folder'] = None


                            serializer = ContentInputSerializer(data=data, many=False)
                            if serializer.is_valid():
                                serializer.save()

                                storage.total_storage_used = new_total_storage_used
                                storage.save()
                                
                                return Response(serializer.data, status=status.HTTP_200_OK)
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                    else:
                        return Response({"message": "No Storage Plan Found Plz add a Storage Plan"}, status=status.HTTP_404_NOT_FOUND) 


                else:
                    # Check user's current storage usage
                    storage = StorageUsage.objects.filter(user=request.user.id, is_delete=False).first()

                    if not storage:
                        storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage").first()

                        # Create Free Storage Plan for a User
                        if storage_plan:
                            storage = StorageUsage.objects.create(
                                user_id = request.user.id, 
                                plan_id = storage_plan.id,
                                storage_limit = storage_plan.storage_size,
                                subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                                subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                                description = "This is Free Plan For Trial Period", 
                                status = "trial", 
                                transactionId = "trial", 
                                payment_status = "trial", 
                                payment_mode = "online",

                                plan_name = storage_plan.plan_name,
                                plan_for = storage_plan.plan_for,
                                amount =  storage_plan.amount,
                                duration = storage_plan.duration,
                                feature = storage_plan.feature,
                                discount = storage_plan.discount
                            )

                    if storage:           
                        # Calculate new total usage if this file is uploaded
                        new_total_storage_used = storage.total_storage_used + file.size

                        if new_total_storage_used > storage.storage_limit:
                            return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

                        objectKey = "multinote/contents/" + str(int(time.time())) + '-' + file.name           
                        response = uploadImage(file, objectKey, file.content_type)

                        if response is None:
                            
                            data['file'] = objectKey
                            data['fileName'] = file.name
                            data['user'] = request.user.id
                            data['fileSize'] = file.size   # Size in Bytes
                            data['is_active'] = data.get('is_active', True) 

                            # if folder_id:
                            #     folder = Folder.objects.filter(id=folder_id, is_delete=False).first()
                            #     if not folder.parent_folder:
                            #         data['folder'] = None


                            serializer = ContentInputSerializer(data=data, many=False)
                            if serializer.is_valid():
                                serializer.save()

                                storage.total_storage_used = new_total_storage_used
                                storage.save()
                                
                                return Response(serializer.data, status=status.HTTP_200_OK)
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                    else:
                        return Response({"message": "No Storage Plan Found Plz add a Storage Plan"}, status=status.HTTP_404_NOT_FOUND) 
                
            # elif 'document' in request.data:
            #     try:
            #         document = Document.objects.get(pk=document_id, is_delete=False)
            #     except Document.DoesNotExist:
            #         return Response({"message": "Document Not Found"}, status=status.HTTP_404_NOT_FOUND)
            #     # Check user's current storage usage
            #     storage = StorageUsage.objects.filter(user=request.user.id, is_delete=False).first()

            #     if storage:   
            #         byte_size = len(document.content.encode('utf-8'))
            #         # Calculate new total usage if this file is uploaded
            #         new_total_storage_used = storage.total_storage_used + byte_size

            #         if new_total_storage_used > storage.storage_limit:
            #             return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)
                    
            #         data['user'] = request.user.id
            #         data['fileSize'] = byte_size
            #         data['is_active'] = data.get('is_active', True) 

            #         serializer = ContentInputSerializer(data=data, many=False)
            #         if serializer.is_valid():
            #             serializer.save()

            #             storage.total_storage_used = new_total_storage_used
            #             storage.save()
                        
            #             return Response(serializer.data, status=status.HTTP_200_OK)
            #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"message": "Plz attach a file"}, status=status.HTTP_404_NOT_FOUND)
        else:
            if user_cluster and user_cluster.storage:
                storageId = user_cluster.storage.id
                storage = StorageUsage.objects.get(id=storageId)

                # Calculate new total usage if this file is uploaded
                new_total_storage_used = storage.total_storage_used + fileSize

                if new_total_storage_used > storage.storage_limit:
                    return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

                # objectKey = "multinote/contents/" + str(int(time.time())) + '-' + file.name           
                # response = uploadImage(file, objectKey, file.content_type)

                # if response is None:
                    
                data['file'] = uploadedFile
                data['fileName'] = uploadedFile.split('/')[-1]
                data['user'] = request.user.id
                data['fileSize'] = fileSize   # Size in Bytes
                data['is_active'] = data.get('is_active', True) 

                # if folder_id:
                #     folder = Folder.objects.filter(id=folder_id, is_delete=False).first()
                #     if not folder.parent_folder:
                #         data['folder'] = None


                serializer = ContentInputSerializer(data=data, many=False)
                if serializer.is_valid():
                    serializer.save()

                    storage.total_storage_used = new_total_storage_used
                    storage.save()
                    
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            

            elif user_cluster:
                storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage", is_for_cluster=True).first()

                cluster = Cluster.objects.get(id=user_cluster.id)

                cluster_user = CustomUser.objects.filter(cluster=user_cluster.id, is_cluster_owner=True).first()

                # Create Free Storage Plan for a User
                if storage_plan:
                    storage = StorageUsage.objects.create(
                        user_id = cluster_user.id, 
                        plan_id = storage_plan.id,
                        storage_limit = storage_plan.storage_size,
                        subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                        subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                        description = "This is Free Plan For Trial Period", 
                        status = "trial", 
                        transactionId = "trial", 
                        payment_status = "trial", 
                        payment_mode = "online",

                        plan_name = storage_plan.plan_name,
                        plan_for = storage_plan.plan_for,
                        amount =  storage_plan.amount,
                        duration = storage_plan.duration,
                        feature = storage_plan.feature,
                        discount = storage_plan.discount
                    )

                    cluster.storage = storage
                    cluster.save()

                    # Calculate new total usage if this file is uploaded
                    new_total_storage_used = storage.total_storage_used + fileSize

                    if new_total_storage_used > storage.storage_limit:
                        return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

                    # objectKey = "multinote/contents/" + str(int(time.time())) + '-' + file.name           
                    # response = uploadImage(file, objectKey, file.content_type)

                    # if response is None:
                        
                    data['file'] = uploadedFile
                    data['fileName'] = uploadedFile.split('/')[-1]
                    data['user'] = request.user.id
                    data['fileSize'] = fileSize   # Size in Bytes
                    data['is_active'] = data.get('is_active', True) 

                    # if folder_id:
                    #     folder = Folder.objects.filter(id=folder_id, is_delete=False).first()
                    #     if not folder.parent_folder:
                    #         data['folder'] = None


                    serializer = ContentInputSerializer(data=data, many=False)
                    if serializer.is_valid():
                        serializer.save()

                        storage.total_storage_used = new_total_storage_used
                        storage.save()
                        
                        return Response(serializer.data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                else:
                    return Response({"message": "No Storage Plan Found Plz add a Storage Plan"}, status=status.HTTP_404_NOT_FOUND) 
            
            else:
                # Check user's current storage usage
                storage = StorageUsage.objects.filter(user=request.user.id, is_delete=False).first()

                if not storage:
                    storage_plan = UserPlan.objects.filter(is_free=True, status='active', is_delete=False, plan_for="storage").first()

                    # Create Free Storage Plan for a User
                    if storage_plan:
                        storage = StorageUsage.objects.create(
                            user_id = request.user.id, 
                            plan_id = storage_plan.id,
                            storage_limit = storage_plan.storage_size,
                            subscriptionExpiryDate = timezone.now() + timedelta(days=storage_plan.duration),
                            subscriptionEndDate = timezone.now() + timedelta(days=storage_plan.duration + 7),
                            description = "This is Free Plan For Trial Period", 
                            status = "trial", 
                            transactionId = "trial", 
                            payment_status = "trial", 
                            payment_mode = "online",

                            plan_name = storage_plan.plan_name,
                            plan_for = storage_plan.plan_for,
                            amount =  storage_plan.amount,
                            duration = storage_plan.duration,
                            feature = storage_plan.feature,
                            discount = storage_plan.discount
                        )

                if storage:           
                    # Calculate new total usage if this file is uploaded
                    new_total_storage_used = storage.total_storage_used + fileSize

                    if new_total_storage_used > storage.storage_limit:
                        return Response({"message": "Storage limit exceeded. Please delete some files or Buy Plan to upload new ones."}, status=status.HTTP_403_FORBIDDEN)

                    # objectKey = "multinote/contents/" + str(int(time.time())) + '-' + file.name           
                    # response = uploadImage(file, objectKey, file.content_type)

                    # if response is None:
                        
                    data['file'] = uploadedFile
                    data['fileName'] = uploadedFile.split('/')[-1]
                    data['user'] = request.user.id
                    data['fileSize'] = fileSize   # Size in Bytes
                    data['is_active'] = data.get('is_active', True) 

                    # if folder_id:
                    #     folder = Folder.objects.filter(id=folder_id, is_delete=False).first()
                    #     if not folder.parent_folder:
                    #         data['folder'] = None


                    serializer = ContentInputSerializer(data=data, many=False)
                    if serializer.is_valid():
                        serializer.save()

                        storage.total_storage_used = new_total_storage_used
                        storage.save()
                        
                        return Response(serializer.data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # else:
                    #     return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                else:
                    return Response({"message": "No Storage Plan Found Plz add a Storage Plan"}, status=status.HTTP_404_NOT_FOUND) 
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        self_upload = request.GET.get('selfUpload', 'false')
        self_upload = self_upload.lower() == 'true'
        if pk is not None:
            try:
                content = UserContent.objects.get(pk=pk, is_delete=False)
            except UserContent.DoesNotExist:
                return Response({"message": "File Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ContentOutputSerializer(content)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        if self_upload:
            queryset = UserContent.objects.filter(user= request.user.id, self_upload= True, is_delete=False)
        else:
            queryset = UserContent.objects.filter(user= request.user.id, is_delete=False)

        if searchBy:
            queryset = queryset.filter(
                Q(fileName__icontains=searchBy) |
                Q(description__icontains=searchBy))

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = ContentOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            content = UserContent.objects.get(pk=pk, is_delete=False)
        except UserContent.DoesNotExist:
            return Response({"message": "File Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ContentInputSerializer(content, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "File Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "File Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ShareWithMeView(APIView):
    pagination_class = PageNumberPagination

    def get(self, request):
        searchBy = request.GET.get('searchBy')
        user = request.user
        paginator = self.pagination_class()
        # share_files = Share.objects.filter(share_to_user=user, content_type__in=['file', 'document'], is_delete=False)
        share_files = Share.objects.filter(share_to_user=user, is_delete=False)

        if searchBy:
            share_files = share_files.filter(
                Q(file__file__icontains=searchBy) |
                Q(file__description__icontains=searchBy))

        # print(share_files)
        page = paginator.paginate_queryset(share_files, request)

        # Serialize the data
        data = ShareContentFileSerializer(page, many=True).data

        # file_list = [
        #     {**item['file'], 'access_type': item['access_type']}
        #     for item in data
        # ]


        # file_list = [item['file'] for item in data]

        file_list = []
        for item in data:
            if item['file'] is not None:
                item['file']['access_type'] = item['access_type']
                file_list.append(item['file'])
            elif item['document'] is not None:
                item['document']['access_type'] = item['access_type']
                file_list.append(item['document'])
            elif item['folder'] is not None:
                item['folder']['access_type'] = item['access_type']
                file_list.append(item['folder'])

        total_pages = paginator.page.paginator.num_pages

        response_data = {
            'total_pages': total_pages,
            'results': file_list
        }

        return paginator.get_paginated_response(response_data)
    

# User File Management
class GetRootRecentShareFileView(APIView):
    pagination_class = PageNumberPagination

    def get(self, request):
        paginator = self.pagination_class()
        folder_id = request.GET.get('folderId', None)
        searchBy = request.GET.get('searchBy')

        shareByMe = request.GET.get('shareByMe', 'false')
        shareByMe = shareByMe.lower() == 'true'

        shareToMe = request.GET.get('shareToMe', 'false')
        shareToMe = shareToMe.lower() == 'true'

        selfUpload = request.GET.get('selfUpload', 'false')
        selfUpload = selfUpload.lower() == 'true'

        isShare = request.GET.get('isShare', 'false')
        isShare = isShare.lower() == 'true'


        user = request.user


        # share_value = request.GET.get('shareWithMe', 'false')
        # share_bool = share_value.lower() == "true"

        # if shareByMe:
        #     shares = Share.objects.filter(owner=user, content_type='folder', is_delete=False)

        # elif shareToMe:
        #     shares = Share.objects.filter(share_to_user=user, content_type='folder', is_delete=False)

        if folder_id:
            # if shareByMe:
            #     shares = Share.objects.filter(owner=user, content_type='folder', is_delete=False)

            # elif shareToMe:
            #     shares = Share.objects.filter(share_to_user=user, content_type='folder', is_delete=False)

            # files = UserContent.objects.filter(user=user, is_delete=False, folder=folder_id)
            # documents = Document.objects.filter(user=user, is_delete=False, folder=folder_id)
            if isShare:
                # Retrieve only the 'id' of files and documents
                file_ids = UserContent.objects.filter(is_delete=False, folder=folder_id).values_list('id', flat=True)
                document_ids = Document.objects.filter(is_delete=False, folder=folder_id).values_list('id', flat=True)

                # Convert QuerySets to lists if needed
                file_ids_list = list(file_ids)
                document_ids_list = list(document_ids)

                share_files = Share.objects.filter(share_to_user=user, file__in=file_ids_list, content_type='file', is_delete=False)

                share_documents = Share.objects.filter(share_to_user=user, document__in=document_ids_list, content_type='document', is_delete=False)

                combined_queryset = sorted(
                    list(share_files) + list(share_documents),
                    key=lambda instance: instance.created_at,
                    reverse=True
                )

                page = paginator.paginate_queryset(combined_queryset, request)

                # Serialize the data
                data = []
                for item in page:
                    share_data = ShareContentFileSerializer(item).data
                    
                    if share_data['content_type'] == 'file':
                        share_data['file']['isShare'] = True
                        share_data['file']['dataType'] = 'file'
                        share_data['file']['shareId'] = share_data['id']
                        data.append(share_data['file'])
                    else:
                        share_data['document']['isShare'] = True
                        share_data['document']['dataType'] = 'document'
                        share_data['document']['shareId'] = share_data['id']
                        data.append(share_data['document'])

                total_pages = paginator.page.paginator.num_pages

                response_data = {
                    'total_pages': total_pages,
                    'results': data
                }

                return paginator.get_paginated_response(response_data)

            else:
                files = UserContent.objects.filter(user=user, is_delete=False, folder=folder_id)
                documents = Document.objects.filter(user=user, is_delete=False, folder=folder_id)
            if searchBy:
                files = files.filter(
                    Q(fileName__icontains=searchBy) |
                    Q(description__icontains=searchBy))
                
            if searchBy:
                documents = documents.filter(
                    Q(title__icontains=searchBy) |
                    Q(content__icontains=searchBy))
                

            combined_queryset = sorted(
                list(files) + list(documents),
                key=lambda instance: instance.created_at,
                reverse=True
            )

            page = paginator.paginate_queryset(combined_queryset, request)

            # Serialize the data
            data = []
            for item in page:
                if isinstance(item, UserContent):
                    root_data = ContentLibrarySerializer(item).data
                    root_data['dataType'] = 'file'
                    root_data['isShare'] = False
                    data.append(root_data)

                elif isinstance(item, Document):
                    doc_data = DocumentContentSerializer(item).data
                    doc_data['dataType'] = 'document'
                    doc_data['isShare'] = False
                    data.append(doc_data)

            total_pages = paginator.page.paginator.num_pages

            response_data = {
                'total_pages': total_pages,
                'results': data
            }

            return paginator.get_paginated_response(response_data)
        
        else:
            if shareByMe or shareToMe:
                # shares = Share.objects.filter(owner=user, content_type='folder', is_delete=False)
                # Share.objects.filter(share_to_user=user, content_type='folder', is_delete=False)
                root_files = []
                recent_files = []
            else:
                root_files = UserContent.objects.filter(user=user, is_delete=False, folder__isnull=True)

                recent_files = UserContent.objects.filter(user=user, is_delete=False).order_by('-created_at')

            if searchBy:
                root_files = root_files.filter(
                    Q(fileName__icontains=searchBy) |
                    Q(description__icontains=searchBy))

            if searchBy:
                recent_files = recent_files.filter(
                    Q(fileName__icontains=searchBy) |
                    Q(description__icontains=searchBy))[:10]
            else:
                recent_files[:10]

            files = list(root_files) + list(recent_files)

            # Use a dictionary to keep only unique items by id
            unique_records = {record.id: record for record in files}.values()

            # Convert back to a list if needed
            unique_files = list(unique_records)

            if shareByMe:
                share_files = Share.objects.filter(owner=user, content_type__in=['file', 'document'], is_delete=False)
            else:
                share_files = Share.objects.filter(share_to_user=user, content_type__in=['file', 'document'], is_delete=False)

            if searchBy:
                share_files = share_files.filter(
                    Q(file__file__icontains=searchBy) |
                    Q(file__description__icontains=searchBy))

            # print(share_files)
            if shareByMe or shareToMe:
                root_document = []
            else:
                root_document = Document.objects.filter(user=user, is_delete=False, folder=None)

            if searchBy:
                root_document = root_document.filter(
                    Q(title__icontains=searchBy) |
                    Q(content__icontains=searchBy))
                
            if selfUpload:
                unique_files = UserContent.objects.filter(user= user, self_upload= True, is_delete=False)
                share_files = []
                root_document = []
                

            combined_queryset = sorted(
                list(unique_files) + list(share_files) + list(root_document),
                key=lambda instance: instance.created_at,
                reverse=True
            )

            page = paginator.paginate_queryset(combined_queryset, request)

            # Serialize the data
            data = []
            for item in page:
                if isinstance(item, UserContent):
                    root_data = ContentLibrarySerializer(item).data
                    root_data['isShare'] = False
                    root_data['dataType'] = 'file'
                    data.append(root_data)
                elif isinstance(item, Share):
                    share_data = ShareContentFileSerializer(item).data
                    
                    if share_data['content_type'] == 'file':
                        share_data['file']['isShare'] = True
                        share_data['file']['dataType'] = 'file'
                        share_data['file']['shareId'] = share_data['id']
                        data.append(share_data['file'])
                    else:
                        share_data['document']['isShare'] = True
                        share_data['document']['dataType'] = 'document'
                        share_data['document']['shareId'] = share_data['id']
                        data.append(share_data['document'])
                elif isinstance(item, Document):
                    share_data = DocumentContentSerializer(item).data
                    share_data['isShare'] = False
                    share_data['dataType'] = 'document'
                    data.append(share_data)

            total_pages = paginator.page.paginator.num_pages

            response_data = {
                'total_pages': total_pages,
                'results': data
            }

            return paginator.get_paginated_response(response_data)



# User Storage View 
class UserStorageDetailView(APIView):
    def get(self, request):
        storage = StorageUsage.objects.filter(user=request.user, is_delete=False, status__in=['active', 'trial']).first()


        if storage:
            if storage.total_storage_used < 0:
                total_used_storage = "0 BYTES"
            elif storage.total_storage_used < 1024:
                total_used_storage = f"{storage.total_storage_used} BYTES"
            elif storage.total_storage_used < 1024*1024:
                total_used_storage = f"{round(storage.total_storage_used/(1024), 2)} KB"
            elif storage.total_storage_used < 1024*1024*1024:
                total_used_storage = f"{round(storage.total_storage_used/(1024*1024), 2)} MB"
            else:
                total_used_storage = f"{round(storage.total_storage_used/(1024*1024*1024), 2)} GB"

            storage_limit = f"{round(storage.storage_limit/(1024*1024*1024), 2)} GB"

            return Response({
                "total_storage_used": total_used_storage,
                "storage_limit": storage_limit,
                # "remaining_storage": storage_limit - total_used_storage,
                "used_storage_in_bytes": storage.total_storage_used,
                "message": "Storage Detail Fetched Successfully"
            }, status=status.HTTP_200_OK)
        
        return Response({"message": "Storage not found/expire"}, status=status.HTTP_404_NOT_FOUND)
    
# Get file size for all subfolder file.
def get_sub_folder_detail(ownerId, shareToId, folder_data, access_type, folderId):
    for folder in folder_data:
        detail = {
            "folder": folder['id'],
            "owner": ownerId,
            "share_to_user": shareToId,
            "content_type": "folder",
            "access_type": access_type,
            "main_folder": folderId
        }
        serializer = ShareContentInputSerializer(data=detail, many=False)
        if serializer.is_valid():
            serializer.save()

            files = UserContent.objects.filter(user=ownerId,is_delete=False, folder=folder['id'])

            for userFile in files:
                detail = {
                    "file": userFile.id,
                    "owner": ownerId,
                    "share_to_user": shareToId,
                    "content_type": "file",
                    "access_type": access_type,
                }
                serializer = ShareContentInputSerializer(data=detail, many=False)
                if serializer.is_valid():
                    serializer.save()
            documents = Document.objects.filter(user=ownerId, is_delete=False, folder=folder['id'])
            for document in documents:
                detail = {
                    "document": document.id,
                    "owner": ownerId,
                    "share_to_user": shareToId,
                    "content_type": "document",
                    "access_type": access_type,
                }
                serializer = ShareContentInputSerializer(data=detail, many=False)
                if serializer.is_valid():
                    serializer.save()
        
        # Recursively create subfolders
        if folder['subfolders']:
            get_sub_folder_detail(ownerId, shareToId, folder['subfolders'], access_type, folder['id'])


# User Share Content Management
class ShareContentView(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        emails = request.data.get('emails')
        contentType = request.data.get('contentType', None)
        access_type = request.data.get('access_type', None)

        fileId = data.get("fileId", None)
        folderId = data.get("folderId", None)
        documentId = data.get("documentId", None)

        # print(fileId, folderId)

        if not fileId and not folderId and not documentId:
            return Response({"message": "Please Provide File Id, Folder Id or Document Id for Share"}, status=status.HTTP_404_NOT_FOUND)

        if not contentType or contentType not in ["file", "folder", "document"]:
            return Response({"message": "Content type should be file, folder or document"}, status=status.HTTP_404_NOT_FOUND)
        
        if emails and len(emails) < 1:
            return Response({"message": "Please Provide email for share Content "}, status=status.HTTP_404_NOT_FOUND)
        
        if contentType == "file":
            content = UserContent.objects.filter(id=data["fileId"], is_delete=False, is_active=True).exists()
            if not content:
                return Response({"message": "File Not Found"}, status=status.HTTP_404_NOT_FOUND)
                
        elif contentType == "document":
            content = Document.objects.filter(id=data["documentId"], is_delete=False, enabled=True).exists()
            if not content:
                return Response({"message": "Document Not Found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            folder = Folder.objects.filter(id=data["folderId"], is_delete=False, is_active=True).exists()
            if not folder:
                return Response({"message": "Folder Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        not_exits = []
        for email in emails:
            if email == request.user.email:
                return Response({"message": "You can't share content to yourself"}, status=status.HTTP_400_BAD_REQUEST)
            if not CustomUser.objects.filter(email=email, is_verified=True, is_delete=False).exists():
                not_exits.append(email)

        if len(not_exits) > 0:
            not_exits_string = ', '.join(not_exits)
            return Response({"message": f"{not_exits_string} not exits in our record please remove these email first."}, status=status.HTTP_400_BAD_REQUEST)
        
            

        not_exits = []
        # exits = []
        verified = []
        for email in emails:
            user = CustomUser.objects.filter(email=email, is_delete=False).first()
            # if user and user.is_verified and not user.is_blocked:

            if user and contentType == 'file':
                share = Share.objects.filter(
                    owner=request.user.id, 
                    share_to_user=user.id, 
                    content_type=contentType,
                    file= fileId,
                    is_delete=False
                ).exists()

                if share:
                    verified.append(email)
                    share_content_email.delay(user.id)
                else:
                    detail = {
                        "file": fileId,
                        "owner": request.user.id,
                        "share_to_user": user.id,
                        "content_type": contentType,
                        "access_type": access_type,
                    }
                    serializer = ShareContentInputSerializer(data=detail, many=False)
                    if serializer.is_valid():
                        serializer.save()

                        verified.append(email)
                        share_content_email.delay(user.id)
            elif user and contentType == "document":
                share = Share.objects.filter(
                    owner=request.user.id, 
                    share_to_user=user.id, 
                    content_type=contentType,
                    document = documentId,
                    is_delete=False
                ).exists()
                if share:
                    verified.append(email)
                    share_content_email.delay(user.id)

                else:
                    detail = {
                        "document": documentId,
                        "owner": request.user.id,
                        "share_to_user": user.id,
                        "content_type": contentType,
                        "access_type": access_type,
                    }
                    serializer = ShareContentInputSerializer(data=detail, many=False)
                    if serializer.is_valid():
                        serializer.save()

                        verified.append(email)
                        share_content_email.delay(user.id)
            elif user and contentType == "folder":
                share = Share.objects.filter(
                    owner=request.user.id, 
                    share_to_user=user.id, 
                    content_type=contentType,
                    folder = folderId,
                    is_delete=False
                ).exists()
                if share:
                    verified.append(email)
                    share_content_email.delay(user.id)
                    
                    files = UserContent.objects.filter(user=request.user,is_delete=False, folder=folderId)
                    for userFile in files:
                        try:
                            shareFile = Share.objects.get(file=userFile.id, is_delete=False)
                        except shareFile.DoesNotExist():
                            detail = {
                                "file": userFile.id,
                                "owner": request.user.id,
                                "share_to_user": user.id,
                                "content_type": "file",
                                "access_type": access_type,
                            }
                            serializer = ShareContentInputSerializer(data=detail, many=False)
                            if serializer.is_valid():
                                serializer.save()

                    documents = Document.objects.filter(user=request.user, is_delete=False, folder=folderId)
                    for document in documents:
                        try:
                            shareFile = Share.objects.get(document=document.id, is_delete=False)
                        except shareFile.DoesNotExist():
                            detail = {
                                "document": document.id,
                                "owner": request.user.id,
                                "share_to_user": user.id,
                                "content_type": "document",
                                "access_type": access_type,
                            }
                            serializer = ShareContentInputSerializer(data=detail, many=False)
                            if serializer.is_valid():
                                serializer.save()
                else:
                    detail = {
                        "folder": folderId,
                        "owner": request.user.id,
                        "share_to_user": user.id,
                        "content_type": contentType,
                        "access_type": access_type,
                    }
                    serializer = ShareContentInputSerializer(data=detail, many=False)
                    if serializer.is_valid():
                        serializer.save()

                        files = UserContent.objects.filter(user=request.user,is_delete=False, folder=folderId)
                        for userFile in files:
                            detail = {
                                "file": userFile.id,
                                "owner": request.user.id,
                                "share_to_user": user.id,
                                "content_type": "file",
                                "access_type": access_type,
                            }
                            serializer = ShareContentInputSerializer(data=detail, many=False)
                            if serializer.is_valid():
                                serializer.save()
                        documents = Document.objects.filter(user=request.user, is_delete=False, folder=folderId)
                        for document in documents:
                            detail = {
                                "document": document.id,
                                "owner": request.user.id,
                                "share_to_user": user.id,
                                "content_type": "document",
                                "access_type": access_type,
                            }
                            serializer = ShareContentInputSerializer(data=detail, many=False)
                            if serializer.is_valid():
                                serializer.save()

                        folderName, folder_data = get_folder_detail(request.user.id, folderId)

                        get_sub_folder_detail(request.user.id, user.id, folder_data, access_type, folderId)

                        verified.append(email)
                        share_content_email.delay(user.id)

            # elif user and (not user.is_verified or user.is_blocked):
            #     exits.append(email)
            else:
                not_exits.append(email)
         
        return Response({"content_sent_mails": verified, 
                        #  "not_verified_mails": exits,
                         "not_exists_mails": not_exits,
                          "message": "Content share Successfully" }, status=status.HTTP_200_OK)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        shareByMe = request.GET.get('shareByMe', 'false')

        user = request.user

        shareByMe = shareByMe.lower() == "true"

        if pk is not None:
            try:
                share_content = Share.objects.get(pk=pk, is_delete=False)
            except Share.DoesNotExist:
                return Response({"message": "Share Content Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ShareContentOutputSerializer(share_content)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        if shareByMe:
            queryset = Share.objects.filter(owner=user.id, is_delete=False, is_active=True)
        else:
            queryset = Share.objects.filter(share_to_user=user.id, is_delete=False, is_active=True)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = ShareContentOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            share_content = Share.objects.get(pk=pk, is_delete=False)
        except Share.DoesNotExist:
            return Response({"message": "Share Content Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ShareContentInputSerializer(share_content, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "Share Content Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "Share Content Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class DeleteShareContent(APIView):
#     def post(self, request):
#         share_to_user = request.data.get('shareByMeId')
    
class DeleteCommonFileView(APIView):
    def delete(self, request, pk=None):
        dataType = request.data.get('recordType')
        folderId = request.data.get('folderId')

        if dataType == 'share':
            if folderId:
                try:
                    share_content = Share.objects.get(pk=pk, is_delete=False)
                except Share.DoesNotExist:
                    return Response({"message": "Share Content not found"}, status=status.HTTP_404_NOT_FOUND)

                # Retrieve only the 'id' of files and documents
                file_ids = UserContent.objects.filter(is_delete=False, folder=folderId).values_list('id', flat=True)
                document_ids = Document.objects.filter(is_delete=False, folder=folderId).values_list('id', flat=True)

                # Convert QuerySets to lists if needed
                file_ids_list = list(file_ids)
                document_ids_list = list(document_ids)

                share_files = Share.objects.filter(share_to_user=request.user, file__in=file_ids_list, content_type='file', is_delete=False).delete()

                share_documents = Share.objects.filter(share_to_user=request.user, document__in=document_ids_list, content_type='document', is_delete=False).delete()

                share_content.delete()
                return Response({"message": "Share Content Deleted"}, status=status.HTTP_200_OK)
            else:
                try:
                    share_content = Share.objects.get(pk=pk, is_delete=False)
                except Share.DoesNotExist:
                    return Response({"message": "Share Content not found"}, status=status.HTTP_404_NOT_FOUND)

                share_content.delete()
                return Response({"message": "Share Content Deleted"}, status=status.HTTP_200_OK)

        elif dataType == 'file':
            try:
                user_content = UserContent.objects.get(pk=pk, is_delete=False)
            except UserContent.DoesNotExist:
                return Response({"message": "File not found"}, status=status.HTTP_404_NOT_FOUND)

            storage = StorageUsage.objects.filter(user=request.user, is_delete=False).first()
            if storage:
                storage.total_storage_used -= user_content.fileSize
                storage.save()
            user_content.delete()
            return Response({"message": "File Deleted"}, status=status.HTTP_200_OK)

        elif dataType == 'document':
            try:
                document = Document.objects.get(pk=pk, is_delete=False)
            except Document.DoesNotExist:
                return Response({"message": "File not found"}, status=status.HTTP_404_NOT_FOUND)
            
            storage = StorageUsage.objects.filter(user=request.user, is_delete=False).first()
            if storage:
                storage.total_storage_used -= document.size
                storage.save()
                
            document.delete()
            return Response({"message": "File Deleted"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "recordType should be file, share or document only."}, status=status.HTTP_400_BAD_REQUEST)
    

# User Storage Management
class UserStorageView(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        transactionId = request.data.get('transactionId')
        payment_status = request.data.get('payment_status')
        planId = request.data.get('plan')
        coupon_code = request.data.get('couponCode', None)
        coupon_type = request.data.get('couponType', None)
        discount_value = request.data.get('discountValue', None)
        # bonus_token = request.data.get('bonusToken', 0)

        data = request.data.copy()
        # data['user'] = request.user.id

        try:
            transaction = Transaction.objects.get(transactionId=transactionId)
            # print(transaction.id)
        except Transaction.DoesNotExist:
            return Response("No Such Payment Exist", status=status.HTTP_404_NOT_FOUND)
        
        plan = UserPlan.objects.filter(id=planId, is_delete=False, status='active').first()

        if not plan:
            return Response("No Such Plan Exist", status=status.HTTP_404_NOT_FOUND)

        subscriptionExpiryDate = timezone.now() + timedelta(days=plan.duration)
        subscriptionEndDate = timezone.now() + timedelta(days=plan.duration + 7)

        storage = StorageUsage.objects.filter(user=request.user.id, is_delete=False).first()


        if storage:
            new_data = {
                "subscriptionExpiryDate": subscriptionExpiryDate,
                "subscriptionEndDate": subscriptionEndDate,
                "status": 'active',
                "transactionId": transactionId,
                "payment_status": payment_status,
                "plan": plan.id,
                "storage_limit": plan.storage_size,

                "plan_name": plan.plan_name,
                "plan_for": plan.plan_for,
                "amount": plan.amount,
                "duration": plan.duration,
                "feature": plan.feature,
                "discount": plan.discount,

                "coupon_code": coupon_code,
                "coupon_type": coupon_type,
                "discount_value":discount_value,
                # "bonus_token": bonus_token
            }

            serializer = StorageInputSerializer(storage, data=new_data, partial=True)
            
            if serializer.is_valid():
                serializer.save()

                detail = serializer.data
                new_detail = detail.copy()

                new_detail['total_storage_used'] = round(detail['total_storage_used']/(1024*1024*1024), 2)
                new_detail['storage_limit'] = round(detail['storage_limit']/(1024*1024*1024), 2)

                return Response(new_detail, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            data['user'] = request.user.id
            data['subscriptionExpiryDate'] = subscriptionExpiryDate
            data['subscriptionEndDate'] = subscriptionEndDate
            data['storage_limit'] = plan.storage_size
            data['payment_mode'] = 'online'
            
            data['plan_name'] = plan.plan_name
            data['plan_for'] = plan.plan_for
            data['amount'] = plan.amount
            data['duration'] = plan.duration
            data['feature'] = plan.feature
            data['discount'] = plan.discount

            data["coupon_code"] = coupon_code
            data["coupon_type"] = coupon_type
            data["discount_value"] = discount_value
            # data["bonus_token"] = bonus_token

            serializer = StorageInputSerializer(data=data, many=False)

            if serializer.is_valid():
                payment_status = serializer.validated_data.get('payment_status')
                user_storage = serializer.save()

                detail = serializer.data
                new_detail = detail.copy()

                new_detail['total_storage_used'] = round(detail['total_storage_used']/(1024*1024*1024), 2)
                new_detail['storage_limit'] = round(detail['storage_limit']/(1024*1024*1024), 2)

                trans_data = {
                    "payment_status": payment_status,
                    "storage_id": user_storage.id
                }
                trans_serializer = UpdateTransactionSerializer(transaction, data=trans_data, partial=True)

                if trans_serializer.is_valid():
                    trans_serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # transaction.payment_status = payment_status
                # transaction.storage = user_subscript.id
                # transaction.save()
            
                return Response(new_detail, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                storage = StorageUsage.objects.get(pk=pk, is_delete=False)
            except StorageUsage.DoesNotExist:
                return Response({"message": "User Storage Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageOutputSerializer(storage)
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = StorageUsage.objects.filter(is_delete=False)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = StorageOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            storage = StorageUsage.objects.get(pk=pk, is_delete=False)
        except StorageUsage.DoesNotExist:
            return Response({"message": "User Storage Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = StorageInputSerializer(storage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            if "is_delete" in request.data and request.data["is_delete"] == True:
                return Response({"message": "User Storage Delete"}, status=status.HTTP_200_OK)
            return Response({"message": "User Storage Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Manage Group Response
class GroupResponseView(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        # question = request.data.get("question", None)

        serializer = GroupInputSerializer(data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        categoryId = request.GET.get('categoryId')
        llmId = request.GET.get('llm')
        # isActive = request.GET.get('isActive')
        # share_value = request.GET.get('shareWithMe', 'false')
        # active_bool = isActive.lower() == "true"

        if pk is not None:
            try:
                group = GroupResponse.objects.get(pk=pk, is_delete=False)
            except GroupResponse.DoesNotExist:
                return Response({"message": "Group Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = GroupOutputSerializer(group)
            return Response(serializer.data, status=status.HTTP_200_OK)


        if searchBy:
            queryset = GroupResponse.objects.filter(is_delete=False, user=request.user.id)
            
            queryset = queryset.filter(group_name__icontains=searchBy)
        else:
            queryset = GroupResponse.objects.filter(is_delete=False, user=request.user.id)

        if categoryId:
            queryset = queryset.filter(category=categoryId)

        if llmId:
            queryset = queryset.filter(llm=llmId)

        queryset = queryset.order_by('-created_at')

        # page = paginator.paginate_queryset(queryset, request)
        # serializer = GroupOutputSerializer(page, many=True)
        # total_pages = paginator.page.paginator.num_pages
        # response_data = {
        #     'total_pages': total_pages,
        #     'results': serializer.data
        # }

        # return paginator.get_paginated_response(response_data)
            
        serializer = GroupOutputSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, pk=None):
        try:
            group = GroupResponse.objects.get(pk=pk, is_delete=False)
        except GroupResponse.DoesNotExist:
            return Response({"message": "Group Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = GroupInputSerializer(group, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Group Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk=None):
        try:
            group = GroupResponse.objects.get(pk=pk, is_delete=False)
        except GroupResponse.DoesNotExist:
            return Response({"message": "Group Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        group.delete()
        return Response({"message": "Group Delete"}, status=status.HTTP_200_OK)


def download_video(url, output_path, userId):
    ydl_opts = {
        'format': 'bestaudio/best',  # This ensures you're getting the best available audio.
        'outtmpl': os.path.join(output_path, f"user_file_{userId}"),  # Save as the original audio format.

        'postprocessors': [{  # Post-process audio to convert to mp3.
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # Convert to mp3.
            'preferredquality': '192',  # Audio quality setting.
        }],
        # 'cookies': f'{output_path}/cookies.json',  # Path to cookies file
        # 'proxy': 'http://123.45.67.89:8080'

    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        file_path = output_path/f"user_file_{userId}.mp3"
        return file_path
    
def convert_mp4_to_mp3(input_file, output_file):
    try:
        # Using ffmpeg to convert mp4 to mp3
        # command = ['ffmpeg', '-i', input_file, '-q:a', '0', '-map', 'a', output_file]

        command = [
            'ffmpeg', '-i', input_file,  # Input file
            '-vn',  # No video (strip video stream)
            '-acodec', 'mp3',  # Specify the output audio codec as mp3
            output_file  # Output audio file
        ]       
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        return False
    
def convert_audio_into_text(audio_file_path, user):
    output_path = settings.BASE_DIR

    url = "https://api.openai.com/v1/audio/transcriptions"

    audio = AudioSegment.from_mp3(audio_file_path)

    # Get the total length of the audio file in milliseconds
    audio_length_ms = len(audio)

    # Split the audio file into chunks and export each chunk
    text = ""
    if audio_length_ms > 60000*15:
        for i in range(0, audio_length_ms, 900000):
            start_time = i
            end_time = min(i + 900000, audio_length_ms)  # Make sure the last chunk isn't too long
            chunk = audio[start_time:end_time]
            
            # Export the chunk as an MP3 file
            chunk_name = f"chunk_{i // 900000 + 1}.mp3"
            chunk_path = output_path/chunk_name

            chunk.export(chunk_path, format="mp3")

            with open(chunk_path, 'rb') as audio_file:
                # Prepare the multipart/form-data request
                files = {
                    'file': audio_file
                }
                
                # Data for the request
                data = {
                    'model': 'whisper-1'
                }
                
                # Headers
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                }
                
                # Send the POST request
                response = requests.post(url, headers=headers, files=files, data=data)

                os.remove(chunk_path)
                new_text = json.loads(response.text)['text']

                if i == 0:
                    text += new_text
                else:
                    text += f" {new_text}"
            manage_file_token(user)

        os.remove(audio_file_path)

    else:
        # audio_file_path = output_path/f"user_file_1.mp3"

        # Open the file in binary mode
            
        with open(audio_file_path, 'rb') as audio_file:
            # Prepare the multipart/form-data request
            files = {
                'file': audio_file
            }
            

            # Data for the request
            data = {
                'model': 'whisper-1'
            }
            
            # Headers
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            }
            
            # Send the POST request
            response = requests.post(url, headers=headers, files=files, data=data)

            text = json.loads(response.text)['text']

            os.remove(audio_file_path)

        manage_file_token(user)

    return text

def split_into_batches(text):
    """Splits a large text into manageable batches based on token count."""
    # model = "gpt-4"
    model = "gpt-4-turbo-2024-04-09"
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    
    # Split tokens into chunks
    batches = [tokens[i:i + 70000] for i in range(0, len(tokens), 70000)]
    
    # Decode batches back into text
    # return [encoding.decode(batch) for batch in batches]
    text_batches =  [encoding.decode(batch) for batch in batches]

    # Split text into batches
    # batches = split_into_batches(text, batch_size, modelString)
    results = []

    for batch in text_batches:
        # print("Batch are ----> ", batch)

        # Create a custom prompt for each batch
        batch_prompt = f"{batch} \n summarize this text"

        # API call for the current batch
        response = openAiClient.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": batch_prompt}],
        )
        
        time.sleep(1)
        # Append the batch result
        results.append(response.choices[0].message.content)

    # Combine all results into a single response
    return "\n".join(results)

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()

    os.remove(file_path)

    return text

    # summarize_text = split_into_batches(text)

    # return summarize_text

def extract_text_from_excel(file_path):
    df = pd.read_excel(file_path)
    text = df.to_string(index=False)

    os.remove(file_path)

    return text

    # summarize_text = split_into_batches(text)

    # return summarize_text

def extract_text_from_docx(file_path):
    doc = word_docments(file_path)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)

    os.remove(file_path)
    return '\n'.join(text)

    # new_text = '\n'.join(text)
    # summarize_text = split_into_batches(new_text)

    # return summarize_text

def extract_text_from_doc(file_path):
    text = textract.process(str(file_path))
    
    os.remove(file_path)
    return text.decode('utf-8')

    # new_text = text.decode('utf-8')

    # summarize_text = split_into_batches(new_text)

    # return summarize_text

def convert_csv_to_text(file_path):
    text = ""
    with open(file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            # Join each row by spaces (or any delimiter of your choice)
            text += " ".join(row) + "\n"
    return text

    

class DownloadVideoView(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request, pk=None):

        video_url = request.data.get('url')
        workflows = request.data.get('workflow')
        fileType = request.data.get('fileType')

        data = request.data.copy()
        data['user'] = request.user.id
        # Example usage:'https://www.youtube.com/watch?v=Czg_9C7gw0o'
        # video_url = 'https://www.youtube.com/watch?v=cC8MjoYGed'

        if int(fileType) not in [1, 2, 3, 4, 5, 6, 7]:
            return Response({"message": "Fite Type must be 1, 2, 3, 4, 5, 6 or 7 only."}, status=status.HTTP_400_BAD_REQUEST)
        
        if 'list' in video_url:
            return Response({"message": "Model can't process list of video. Please provide single video link."}, status=status.HTTP_400_BAD_REQUEST)
        
        text = None


        serializer = AiProcessSerializer(data=data, many=False)

        if serializer.is_valid():
            content = serializer.save()
            output_path = settings.BASE_DIR

            # print("User Id is ----> ", request.user.id)
            # print("content Id is ----> ", content.id)
            # print("uploadFile is ----> ", uploadFile)

            aiprocess_data.delay(request.user.id, content.id, fileType)

            # if int(fileType) == 1:

            #     local_path = output_path/f"user_file_{request.user.id}.mp4"

            #     # Download the file
            #     result = download_s3_file(video_url, local_path)
            #     if result:
            #         # print(f"File downloaded successfully from S3 to {local_path}")

            #         input_video = local_path
            #         output_audio = output_path/f"user_audio_file_{request.user.id}.mp3"
            #         result = convert_mp4_to_mp3(input_video, output_audio)

            #         os.remove(local_path)

            #         if result:
            #             text = convert_audio_into_text(output_audio, request.user)

            #     else:
            #         # print("There is an error in file downloading.")
            #         return Response({"message": f"There is an error in file downloading."}, status=status.HTTP_400_BAD_REQUEST)
                
            # elif int(fileType) == 2:
            #     local_path = output_path/f"user_file_{request.user.id}.mp3"

            #     # Download the file
            #     result = download_s3_file(content.url, local_path)

            #     if result:
            #         text = convert_audio_into_text(local_path, request.user)

            # elif int(fileType) == 3:
            #     try:
            #         audio_file_path = download_video(video_url, output_path, request.user.id)
            #     except yt_dlp.utils.DownloadError as e:
            #         return Response({"message": e.msg})
            #     except Exception as e:
            #         return Response({"message": "error occured"})

            #     # yt = YouTube(video_url, on_progress_callback = on_progress)
            #     # # print(yt.title)

            #     # ys = yt.streams.get_highest_resolution()
            #     # # output_path = settings.BASE_DIR
            #     # # tmp_dir = output_path/f"user_file_{request.user.id}.mp4"
            #     # input_video = settings.BASE_DIR/f"user_file_{request.user.id}.mp4"
            #     # ys.download(filename=f"user_file_{request.user.id}.mp4")

            #     # audio_file_path = settings.BASE_DIR/f"user_audio_file_{request.user.id}.mp3"
            #     # result = convert_mp4_to_mp3(input_video, output_audio)
            #     # os.remove(input_video)

                
            #     text = convert_audio_into_text(audio_file_path, request.user)


            # elif int(fileType) == 4:
            #     local_path = output_path/f"user_file_{request.user.id}.pdf"

            #     # Download the file
            #     result = download_s3_file(content.url, local_path)

            #     if result:
            #         text = extract_text_from_pdf(local_path)

            #     return Response({"data": text}, status=status.HTTP_200_OK)

            # elif int(fileType) == 5:

            #     # if content.url.split('.')[-1] == "xlsx":
            #     local_path = output_path/f"user_file_{request.user.id}.xlsx"

            #     # Download the file
            #     result = download_s3_file(content.url, local_path)


            #     if result:
            #         text = extract_text_from_excel(local_path)
            #     # elif content.url.split('.')[-1] == "csv":
            #     #     local_path = output_path/f"user_file_{request.user.id}.csv"

            #     #     # Download the file
            #     #     result = download_s3_file(content.url, local_path)

            #     #     if result:
            #     #         text = convert_csv_to_text(local_path)
            #     # else:
            #     #     return Response({"data": "File extension should be .xlsx or .csv"}, status=status.HTTP_200_OK)

            #     return Response({"data": text}, status=status.HTTP_200_OK)

            # elif int(fileType) == 6:

            #     if content.url.split('.')[-1] == "docx":
            #         local_path = output_path/f"user_file_{request.user.id}.docx"

            #         # Download the file
            #         result = download_s3_file(content.url, local_path)

            #         # text = extract_text_from_doc(local_path)

            #         if result:
            #             text = extract_text_from_docx(local_path)
            #     else:
            #         local_path = output_path/f"user_file_{request.user.id}.doc"
            #         # Download the file
            #         result = download_s3_file(content.url, local_path)

            #         if result:
            #             text = extract_text_from_doc(local_path)
                

            #     return Response({"data": text}, status=status.HTTP_200_OK)

            # elif int(fileType) == 7:
            #     ext = content.url.split('.')[-1]
            #     local_path = output_path/f"user_file_{request.user.id}.{ext}"

            #     # Download the file
            #     result = download_s3_file(content.url, local_path)

            #     if result:
            #         text = extract_text_from_image(local_path)

            #     return Response({"data": text}, status=status.HTTP_200_OK)

                        
            # workflows = json.loads(workflows)

            # if text:
            #     ai_text = text
            #     for workflow in workflows:
            #         model = workflow['modelName']
            #         prompt = workflow['action']

            #         try:
            #             llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
            #             model_string = llm_instance.model_string
            #         except LLM.DoesNotExist:
            #             return Response({'message': f'Model "{model}" not available or not connected',
            #             }, status=status.HTTP_400_BAD_REQUEST)
                    
            #         if llm_instance.source==2 and llm_instance.text:
            #             ai_response = aiTogetherProcess(model_string, ai_text, prompt, request.user)
                        
            #         elif llm_instance.source==3 and llm_instance.text:
            #             ai_response = aiGeminiProcess(model_string, ai_text, prompt, request.user)
                        
            #         elif llm_instance.source==4 and llm_instance.text:
            #             ai_response = aiOpenAIProcess(model_string, ai_text, prompt, request.user)
                        
            #         else:
            #             return Response({'message': 'Please provide proper model for text generation.',
            #             }, status=status.HTTP_400_BAD_REQUEST)

            #         workflow['input'] = ai_text
            #         workflow['ouput'] = ai_response
            #         workflow['status'] = "done"

            #         content.workflow = json.dumps(workflows)
            #         content.save()
            #         ai_text = ai_response

            #     content.url_status = "done"
            #     content.url_output = text
            #     content.save()
            #     return Response({"data": serializer.data}, status=status.HTTP_200_OK)     
            # else:
            #     return Response({"data": "There is no audio available in the given file. Please check."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Your request is being processed. You will receive an email notification once the process is complete."}, status=status.HTTP_200_OK)      
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# AI Process Crud
class AiProcessView(APIView):
    pagination_class = PageNumberPagination

    # def post(self, request):
    #     # data = request.data.copy()
    #     # data['user'] = request.user.id
    #     # question = request.data.get("question", None)


    #     serializer = AiProcessSerializer(data=request.data, many=False)
    #     if serializer.is_valid():
    #         serializer.save()
            
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        categoryId = request.GET.get('categoryId')
        # forUser = request.GET.get('forUser', 'false')
        # isActive = request.GET.get('isActive')
        # forUser = forUser.lower() == "true"
        # isActive = isActive.lower() == "true"

        if pk is not None:
            try:
                aiProcess = AiProcess.objects.get(pk=pk, is_delete=False)
            except AiProcess.DoesNotExist:
                return Response({"message": "Record Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = AiProcessSerializer(aiProcess)
            return Response(serializer.data, status=status.HTTP_200_OK)


        if searchBy:
            queryset = AiProcess.objects.filter(user=request.user.id, category=categoryId, is_delete=False)
            
            queryset = queryset.filter(url__icontains=searchBy)
        else:
            queryset = AiProcess.objects.filter(user=request.user.id, category=categoryId, is_delete=False)

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = AiProcessSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    # def patch(self, request, pk=None):
    #     try:
    #         coupon = Coupon.objects.get(pk=pk, is_delete=False)
    #     except Coupon.DoesNotExist:
    #         return Response({"message": "Coupon Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
    #     serializer = CouponInputSerializer(coupon, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         serializer.save()

    #         return Response({"message": "Coupon Update"}, status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk=None):
        try:
            aiProcess = AiProcess.objects.get(pk=pk, is_delete=False)
        except AiProcess.DoesNotExist:
            return Response({"message": "Record Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        aiProcess.delete()
        return Response({"message": "Ai Process Record Delete"}, status=status.HTTP_200_OK)

    





    


