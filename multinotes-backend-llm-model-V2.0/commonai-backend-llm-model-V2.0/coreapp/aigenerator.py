# from rest_framework.views import APIView
from adrf.decorators import APIView
from rest_framework.response import Response
import httpx
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async
from rest_framework.permissions import IsAuthenticated, AllowAny
import json
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from .models import LLM, LLM_Tokens, GroupResponse
from .utils import (generateUsingGemini, generateUsingTogether, 
                    generateTextByTogether, generateTextByTogetherTest, 
                    generateUsingGeminiTest, textToTextUsingGemini, 
                    generateTextToTextUsingTogether, generateImageToTextUsingGemini,
                    generateTextToImageUsingTogether, generateCodeUsingTogether,
                    generateTextByOpenAI, generateTextToSpeech, speechToTextGenerator,
                    generateTextToImageUsingOpenai, textToCodeUsingGemini,
                    generateVideoToTextUsingGemini, generateAudioToTextUsingGemini
                )
import time
from rest_framework import status
import multiprocessing
from threading import Event, Thread
from queue import Queue
from django.utils import timezone

import base64
from PIL import Image
from io import BytesIO

import asyncio
from django.http import StreamingHttpResponse
from django.utils.timezone import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from authentication.awsservice import uploadImage
from .models import Prompt, PromptResponse
from .serializers import TextToTextSerializer, PictureToTextSerializer, TextToImageSerializer, SpeechToTextSerializer
from .authenticaton import TextSubscriptionAuth, FileSubscriptionAuth
from planandsubscription.models import Subscription
from ticketandcategory.models import Category
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import uuid

def manage_file_token(user):
    cluster = user.cluster
    if cluster:
        subs = cluster.subscription
    else:
        subs = Subscription.objects.filter(user=user.id, status__in=['active', 'trial']).first()
    subs.fileToken -= 1
    subs.usedFileToken += 1
    subs.save()


class TextAiGeneratorView(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                promptWriter = serializer.validated_data.get('promptWriter')
                source = serializer.validated_data.get('source')
                useFor = serializer.validated_data.get('useFor')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not available or not connected',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                # category = Category.objects.get(id=category)
                if source == 'together':
                    if useFor == 'text':
                        response = StreamingHttpResponse(
                            generateTextToTextUsingTogether(
                                prompt, model, model_string, 
                                request.user, category, 
                                llm_instance.id, promptWriter)
                            )
                
                        response['Content-Type'] = 'text/event-stream'
                        response['Cache-Control'] = 'no-cache'
                        return response
                    elif useFor == 'code':
                        response = StreamingHttpResponse(
                            generateCodeUsingTogether(
                                prompt, model, model_string,
                                request.user, category, 
                                llm_instance.id
                            )
                        )
                
                        response['Content-Type'] = 'text/event-stream'
                        response['Cache-Control'] = 'no-cache'
                        return response
                elif source == 'gemini':
                    if useFor == 'text':
                        response = StreamingHttpResponse(
                            textToTextUsingGemini(prompt, model, model_string, 
                                    request.user, category, 
                                    llm_instance.id, promptWriter)
                                )

                        response['Content-Type'] = 'text/event-stream'
                        response['Cache-Control'] = 'no-cache'
                        return response
                elif source == 'openai':
                    if useFor == 'text':
                        response = StreamingHttpResponse(
                            generateTextByOpenAI(prompt, model, model_string, 
                                    request.user, category, llm_instance.id, promptWriter)
                                )

                        response['Content-Type'] = 'text/event-stream'
                        response['Cache-Control'] = 'no-cache'
                        return response
                else:
                   return Response({'message': 'Please provide source.'}, status=status.HTTP_400_BAD_REQUEST) 

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_group_name(input_string):
    # Split the string into words
    words = input_string.split()
    
    # If the number of words is greater than 3, return only the first 3
    if len(words) > 4:
        return ' '.join(words[:4])
    
    # If 3 or fewer words, return the entire string
    return ' '.join(words)

class DynamicLlmGeneratorView(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:
            prompt = request.data.get('prompt')
            model = request.data.get('model')
            category = request.data.get('category')
            promptWriter = request.data.get('promptWriter')
            voice = request.data.get('voice')
            groupId = request.data.get('groupId')
            width = request.data.get('width', None)
            height = request.data.get('height', None)
            # source = request.data.get('source')
            chatbot = request.data.get('chatbot', 'false')
            chatbot = chatbot.lower() == 'true'

            # print("chatbot is ----> ", chatbot)
            # print("groupId is ----> ", groupId)

            try:
                llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                model_string = llm_instance.model_string
            except LLM.DoesNotExist:
                return Response({'message': f'Model "{model}" not available or not connected',
                }, status=status.HTTP_400_BAD_REQUEST)

            if not llm_instance.model_string:
                return Response({'message': f'Model String against "{model}" not found.',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if chatbot and not groupId:
                if not prompt:
                    return Response({'message': f'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)
                
                groupName = get_group_name(prompt)
                
                group = GroupResponse.objects.create(
                    user_id=request.user.id, 
                    category_id= category,
                    llm_id=llm_instance.id, 
                    group_name= groupName,
                    # conversation_id = str(uuid.uuid4())
                )

                groupId = group.id
            
            
            ## Together Converter
            if llm_instance.source==2 and llm_instance.text:
                if not prompt:
                    return Response({'message': f'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)
                
                response = StreamingHttpResponse(
                    generateTextToTextUsingTogether(
                        prompt, model, model_string, 
                        request.user, category, 
                        llm_instance.id, promptWriter,
                        groupId)
                    )
        
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            elif llm_instance.source==2 and llm_instance.code:
                if not prompt:
                    return Response({'message': f'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)
                response = StreamingHttpResponse(
                    generateCodeUsingTogether(
                        prompt, model, model_string,
                        request.user, category, 
                        llm_instance.id, groupId
                    )
                )
        
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            
            elif llm_instance.source==2 and llm_instance.text_to_image: 
                if not prompt:
                    return Response({'message': f'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)
                
                image_width = int(width) if width else 1024
                image_height = int(height) if height else 1024

                # print("Image Widht is ---> ", image_width)
                # print("Image Hight is ---> ", image_height)
                
                image = generateTextToImageUsingTogether(prompt, model_string, image_width, image_height)

                decoded_image = base64.b64decode(image)

                imgKey = "multinote/texttoimage/" + str(time.time()) + ".png"
                uploadImage(BytesIO(decoded_image), imgKey, "image/png")

                manage_file_token(request.user)

                image_size = BytesIO(decoded_image).getbuffer().nbytes

                promp = Prompt.objects.create(
                    prompt_text=prompt, 
                    user_id=request.user.id, 
                    category_id=category,
                    group_id=groupId,
                    response_type = 4,
                    # mainCategory_id=mainCategory, 
                )
                prompt_instance = PromptResponse.objects.create(
                    llm_id=llm_instance.id, 
                    response_image=imgKey, 
                    prompt_id=promp.id, 
                    user_id = request.user.id,
                    response_type = 4,
                    tokenUsed = 1,
                    category_id=category,
                    fileSize= image_size
                    # mainCategory_id=mainCategory,
                )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )

                data = {
                    'model': model,
                    'generated_content': imgKey,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id,
                    'size': image_size,
                    'groupId': groupId
                }
                return Response(data, status=status.HTTP_200_OK)  

            ## Gemini Converter
            elif llm_instance.source==3 and llm_instance.text:      
                if not prompt:
                    return Response({'message': 'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)  
                
                response = StreamingHttpResponse(
                    textToTextUsingGemini(prompt, model, model_string, 
                            request.user, category, 
                            llm_instance.id, promptWriter,
                            groupId)
                        )

                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            
            elif llm_instance.source==3 and llm_instance.image_to_text: 
                # if not prompt:
                #     return Response({'message': 'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST) 

                if 'file' not in request.FILES:
                    return Response({'message': 'Please upload an audio file!',}, status=status.HTTP_400_BAD_REQUEST)

                uploaded_file = request.FILES.get('file')   

                if uploaded_file.name == '':
                    return Response({'message': 'No selected file!',}, status=status.HTTP_400_BAD_REQUEST)
                
                file_name, file_extension = os.path.splitext(uploaded_file.name)

                image_ext_list = ['.png', '.jpeg', '.jpg', '.webp', '.heic', '.heif']

                audio_ext_list = ['.mp3', '.wav', '.aiff', '.aac', '.ogg', '.flac']

                if file_extension.lower() in image_ext_list:
                    response = StreamingHttpResponse(
                        generateImageToTextUsingGemini(
                            prompt, model, model_string, 
                            request.user, category, 
                            llm_instance.id, uploaded_file,
                            groupId
                        )
                    )
                    
                    response['Content-Type'] = 'text/event-stream'
                    response['Cache-Control'] = 'no-cache'
                    return response
                elif file_extension.lower() in audio_ext_list:
                    fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR))

                    fs.save(uploaded_file.name, uploaded_file)
                    # print("Audio to text ***********")
                    # time.sleep(1)

                    text = generateAudioToTextUsingGemini(model_string, uploaded_file)
                    # print("text is ------> ", text)

                    fileKey = "multinote/speechToText/" + str(request.user.id) + "-" + uploaded_file.name
                    uploadImage(uploaded_file, fileKey, uploaded_file.content_type)

                    manage_file_token(request.user)

                    promp = Prompt.objects.create( 
                        user_id = request.user.id, 
                        prompt_audio = fileKey,
                        category_id= category,
                        group_id= groupId,
                        response_type = 6,
                        # mainCategory_id = mainCategory
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id = llm_instance.id, 
                        response_text = text, 
                        prompt_id = promp.id,
                        user_id = request.user.id,
                        response_type = 6,
                        tokenUsed = 1,
                        category_id= category,
                        # mainCategory_id = mainCategory
                    )

                    LLM_Tokens.objects.create(
                        user_id = request.user.id,
                        llm_id = llm_instance.id,
                        prompt_id = promp.id,
                        file_token_used = 1
                    )
                    
                    data = {
                        'model': model,
                        'text': text,
                        'promptId': promp.id, 
                        'responseId': prompt_instance.id,
                        'groupId': groupId
                    }

                    return Response(data, status=status.HTTP_200_OK)
            
                else :
                    return Response({'message': f'Please provide file in proper format. Model support {image_ext_list + audio_ext_list} format only!',}, status=status.HTTP_400_BAD_REQUEST)
                
                # fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR))

                # fs.save(uploaded_file.name, uploaded_file)

            elif llm_instance.source==3 and llm_instance.video_to_text: 
                if not prompt:
                    return Response({'message': 'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST) 
             
                if 'file' not in request.FILES:
                    return Response({'message': 'Please upload an audio file!',}, status=status.HTTP_400_BAD_REQUEST)

                uploaded_file = request.FILES.get('file')   

                if uploaded_file.name == '':
                    return Response({'message': 'No selected file!',}, status=status.HTTP_400_BAD_REQUEST)
                
                file_name, file_extension = os.path.splitext(uploaded_file.name)
                video_ext_list = ['.mp4', '.mpeg', '.mov', '.avi', '.x-flv', '.mpg', '.webm', '.wmv', '.3gpp']

                if file_extension.lower() not in video_ext_list:
                    return Response({'message': f'Please provide video file in proper format. Model support {video_ext_list} format only!',}, status=status.HTTP_400_BAD_REQUEST)
                
                fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR))

                fs.save(uploaded_file.name, uploaded_file)

                response = StreamingHttpResponse(
                            generateVideoToTextUsingGemini(
                                prompt, model, model_string, 
                                request.user, category, 
                                llm_instance.id, uploaded_file,
                                groupId
                            )
                        )
                
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response

            elif llm_instance.source==3 and llm_instance.code:      
                if not prompt:
                    return Response({'message': 'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)  
                
                response = StreamingHttpResponse(
                    textToCodeUsingGemini(prompt, model, model_string, 
                            request.user, category, 
                            llm_instance.id, promptWriter, groupId)
                        )

                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            
            ## Openai Converter
            elif llm_instance.source==4 and llm_instance.text:    
                if not prompt:
                    return Response({'message': 'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)  
                
                response = StreamingHttpResponse(
                    generateTextByOpenAI(prompt, model, model_string, 
                            request.user, category, llm_instance.id, promptWriter,
                            groupId)
                        )

                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
                
            elif llm_instance.source==4 and llm_instance.text_to_image:      
                if not prompt:
                    return Response({'message': f'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)
                
                image_width = int(width) if width else 1024
                image_height = int(height) if height else 1024
                
                image = generateTextToImageUsingOpenai(prompt, model_string, image_width, image_height)

                decoded_image = base64.b64decode(image)

                imgKey = "multinote/texttoimage/" + str(time.time()) + ".png"
                uploadImage(BytesIO(decoded_image), imgKey, "image/png")

                manage_file_token(request.user)

                image_size = BytesIO(decoded_image).getbuffer().nbytes

                promp = Prompt.objects.create(
                    prompt_text=prompt, 
                    user_id=request.user.id, 
                    category_id=category,
                    group_id=groupId,
                    response_type = 4,
                    # mainCategory_id=mainCategory, 
                )
                prompt_instance = PromptResponse.objects.create(
                    llm_id=llm_instance.id, 
                    response_image=imgKey, 
                    prompt_id=promp.id, 
                    user_id = request.user.id,
                    response_type = 4,
                    tokenUsed = 1,
                    category_id=category,
                    fileSize= image_size
                    # mainCategory_id=mainCategory,
                )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )

                data = {
                    'model': model,
                    'generated_content': imgKey,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id,
                    "groupId": groupId
                }
                return Response(data, status=status.HTTP_200_OK) 
                
            elif llm_instance.source==4 and llm_instance.text_to_audio:      
                if not prompt:
                    return Response({'message': f'Please provide prompt!',}, status=status.HTTP_400_BAD_REQUEST)
                if not voice:
                    return Response({'message': f'Please provide voice type!',}, status=status.HTTP_400_BAD_REQUEST)
                
                image = generateTextToSpeech(prompt, model_string, voice)

                fileKey = "multinote/textToSpeech/" + str(time.time()) + ".mp3"
                uploadImage(BytesIO(image), fileKey, "audio/mpeg")

                manage_file_token(request.user)

                image_size = BytesIO(image).getbuffer().nbytes

                promp = Prompt.objects.create(
                    prompt_text=prompt, 
                    user_id=request.user.id, 
                    category_id= category,
                    group_id= groupId,
                    response_type = 5,
                    # mainCategory_id = mainCategory
                )
                prompt_instance = PromptResponse.objects.create(
                    llm_id=llm_instance.id, 
                    response_audio=fileKey, 
                    prompt_id=promp.id,
                    user_id = request.user.id,
                    response_type = 5,
                    tokenUsed = 1,
                    category_id=category,
                    fileSize= image_size
                    # mainCategory_id = mainCategory
                )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )


                data = {
                    'model': model,
                    'generated_content': fileKey,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id,
                    'size': image_size,
                    'groupId': groupId
                }
                return Response(data, status=status.HTTP_200_OK)
                
            elif llm_instance.source==4 and llm_instance.audio_to_text:   
                if 'file' not in request.FILES:
                    return Response({'message': 'Please upload an audio file!',}, status=status.HTTP_400_BAD_REQUEST)

                uploaded_file = request.FILES.get('file')   

                if uploaded_file.name == '':
                    return Response({'message': 'No selected file!',}, status=status.HTTP_400_BAD_REQUEST)
                
                text = speechToTextGenerator(model_string, uploaded_file)

                fileKey = "multinote/speechToText/" + str(request.user.id) + "-" + uploaded_file.name
                uploadImage(uploaded_file, fileKey, uploaded_file.content_type)

                manage_file_token(request.user)

                promp = Prompt.objects.create( 
                    user_id = request.user.id, 
                    prompt_audio = fileKey,
                    category_id= category,
                    group_id= groupId,
                    response_type = 6,
                    # mainCategory_id = mainCategory
                )
                prompt_instance = PromptResponse.objects.create(
                    llm_id = llm_instance.id, 
                    response_text = text, 
                    prompt_id = promp.id,
                    user_id = request.user.id,
                    response_type = 6,
                    tokenUsed = 1,
                    category_id= category,
                    # mainCategory_id = mainCategory
                )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )
                
                data = {
                    'model': model,
                    'text': text,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id,
                    'groupId': groupId
                }

                return Response(data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class FileAiGeneratorView(APIView):
    permission_classes = [IsAuthenticated, FileSubscriptionAuth]

    def post(self, request):
        try:
            source = request.data.get('source')
            useFor = request.data.get('useFor')

            if source == "together":
                if useFor == 'text_to_image':
                    serializer = TextToImageSerializer(data=request.data)

                    if serializer.is_valid():
                        prompt = request.data.get('prompt')
                        model = request.data.get('model')
                        category = request.data.get('category')
                        # mainCategory = request.data.get('mainCategory')

                        try:
                            llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                            model_string = llm_instance.model_string
                        except LLM.DoesNotExist:
                            return Response({'message': f'Model "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)

                        if not llm_instance.model_string:
                            return Response({'message': f'Model String "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)
                                    
                        image = generateTextToImageUsingTogether(prompt, model_string)

                        decoded_image = base64.b64decode(image)

                        imgKey = "multinote/texttoimage/" + str(time.time()) + ".png"
                        uploadImage(BytesIO(decoded_image), imgKey, "image/png")

                        manage_file_token(request.user)

                        image_size = BytesIO(decoded_image).getbuffer().nbytes

                        
                        # Save the Prompt and Prompt Response
                        # try:
                        #     promp = Prompt.objects.get(
                        #         prompt_text=prompt, 
                        #         category=category, 
                        #         # mainCategory=mainCategory, 
                        #         user=request.user.id
                        #     )
                        #     prompt_instance = PromptResponse.objects.create(
                        #         llm_id=llm_instance.id, response_image=imgKey, 
                        #         prompt_id=promp.id, 
                        #         user_id = request.user.id,
                        #         response_type = 4,
                        #         tokenUsed = 1,
                        #         category_id=category, 
                        #         fileSize= image_size
                        #         # mainCategory_id=mainCategory, 
                        #     )
                        # except Prompt.DoesNotExist:
                        promp = Prompt.objects.create(
                            prompt_text=prompt, 
                            user_id=request.user.id, 
                            category_id=category,
                            response_type = 4,
                            # mainCategory_id=mainCategory, 
                        )
                        prompt_instance = PromptResponse.objects.create(
                            llm_id=llm_instance.id, 
                            response_image=imgKey, 
                            prompt_id=promp.id, 
                            user_id = request.user.id,
                            response_type = 4,
                            tokenUsed = 1,
                            category_id=category,
                            fileSize= image_size
                            # mainCategory_id=mainCategory,
                        )

                        LLM_Tokens.objects.create(
                            user_id = request.user.id,
                            llm_id = llm_instance.id,
                            prompt_id = promp.id,
                            file_token_used = 1
                        )

                        data = {
                            'model': model,
                            'generated_content': imgKey,
                            'promptId': promp.id, 
                            'responseId': prompt_instance.id
                        }
                        return Response(data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif source == "gemini":
                if useFor == 'image_to_text':
                    serializer = PictureToTextSerializer(data=request.data)

                    # print("Source 1 is ---> ", source)
                    # print("useFor 1 is ---> ", useFor)

                    if serializer.is_valid():
                        uploaded_image = request.FILES.get('image')
                        prompt = request.data.get('prompt')
                        model = request.data.get('model')
                        category = request.data.get('category')
                        # mainCategory = request.data.get('mainCategory')

                        # fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR))

                        # fs.save(uploaded_image.name, uploaded_image)

                        try:
                            llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                            model_string = llm_instance.model_string
                        except LLM.DoesNotExist:
                            return Response({'message': f'Model "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)

                        if not llm_instance.model_string:
                            return Response({'message': f'Model String against "{model}" not found.'}, status=status.HTTP_400_BAD_REQUEST)
                                    
                        response = StreamingHttpResponse(
                                    generateImageToTextUsingGemini(
                                        prompt, model, model_string, 
                                        request.user, category, 
                                        llm_instance.id, uploaded_image
                                    )
                                )
                        
                        response['Content-Type'] = 'text/event-stream'
                        response['Cache-Control'] = 'no-cache'
                        return response
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # if useFor == 'text_to_speech':
                #     pass
                # if useFor == 'speech_to_text':
                #     pass

            elif source == "openai":
                # if useFor == 'image_to_text':
                #     pass
                # if useFor == 'text_to_image':
                #     pass
                if useFor == 'text_to_speech':
                    serializer = TextToImageSerializer(data=request.data)

                    if serializer.is_valid():
                        prompt = request.data.get('prompt')
                        model = request.data.get('model')
                        category = request.data.get('category')
                        # mainCategory = request.data.get('mainCategory')
                        voice = request.data.get('voice')

                        try:
                            llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                            model_string = llm_instance.model_string
                        except LLM.DoesNotExist:
                            return Response({'message': f'Model "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)

                        if not llm_instance.model_string:
                            return Response({'message': f'Model String against "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)
                        
                        
                        image = generateTextToSpeech(prompt, model_string, voice)

                        fileKey = "multinote/textToSpeech/" + str(time.time()) + ".mp3"
                        uploadImage(BytesIO(image), fileKey, "audio/mpeg")

                        manage_file_token(request.user)

                        image_size = BytesIO(image).getbuffer().nbytes

                        # Save the Prompt and Prompt Response
                        # try:
                        #     promp = Prompt.objects.get(
                        #         prompt_text=prompt, 
                        #         category=category, 
                        #         # mainCategory=mainCategory, 
                        #         user=request.user.id
                        #     )
                        #     prompt_instance = PromptResponse.objects.create(
                        #         llm_id=llm_instance.id, 
                        #         response_audio=fileKey, 
                        #         prompt_id=promp.id,
                        #         user_id = request.user.id,
                        #         response_type = 5,
                        #         tokenUsed = 1,
                        #         category_id=category,
                        #         fileSize= image_size
                        #         # mainCategory_id = mainCategory
                        #     )
                        # except Prompt.DoesNotExist:
                        promp = Prompt.objects.create(
                            prompt_text=prompt, 
                            user_id=request.user.id, 
                            category_id= category,
                            response_type = 5,
                            # mainCategory_id = mainCategory
                        )
                        prompt_instance = PromptResponse.objects.create(
                            llm_id=llm_instance.id, 
                            response_audio=fileKey, 
                            prompt_id=promp.id,
                            user_id = request.user.id,
                            response_type = 5,
                            tokenUsed = 1,
                            category_id=category,
                            fileSize= image_size
                            # mainCategory_id = mainCategory
                        )

                        LLM_Tokens.objects.create(
                            user_id = request.user.id,
                            llm_id = llm_instance.id,
                            prompt_id = promp.id,
                            file_token_used = 1
                        )


                        data = {
                            'model': model,
                            'generated_content': fileKey,
                            'promptId': promp.id, 
                            'responseId': prompt_instance.id
                        }
                        return Response(data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                elif useFor == 'speech_to_text':
                    serializer = SpeechToTextSerializer(data=request.data)

                    if serializer.is_valid():
                        uploaded_file = request.FILES.get('file')
                        # prompt = request.data.get('prompt')
                        model = request.data.get('model')
                        category = request.data.get('category')
                        # mainCategory = request.data.get('mainCategory')


                        try:
                            llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                            model_string = llm_instance.model_string
                        except LLM.DoesNotExist:
                            return Response({'message': f'Model "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)

                        if not llm_instance.model_string:
                            return Response({'message': f'Model String against "{model}" not found.',
                            }, status=status.HTTP_400_BAD_REQUEST)
                                    
                        text = speechToTextGenerator(model_string, uploaded_file)

                        fileKey = "multinote/speechToText/" + str(request.user.id) + "-" + uploaded_file.name
                        uploadImage(uploaded_file, fileKey, uploaded_file.content_type)

                        manage_file_token(request.user)

                        # Save the Prompt and Prompt Response
                        # try:
                        #     promp = Prompt.objects.get(
                        #         category = category, 
                        #         # mainCategory = mainCategory, 
                        #         user = request.user.id, 
                        #         prompt_audio = fileKey
                        #     )
                        #     prompt_instance = PromptResponse.objects.create(
                        #         llm_id = llm_instance.id, 
                        #         response_text = text, 
                        #         prompt_id = promp.id,
                        #         user_id = request.user.id,
                        #         response_type = 6,
                        #         tokenUsed = 1,
                        #         category_id= category,
                        #         # mainCategory_id = mainCategory
                        #     )
                        # except Prompt.DoesNotExist:
                        promp = Prompt.objects.create( 
                            user_id = request.user.id, 
                            prompt_audio = fileKey,
                            category_id= category,
                            response_type = 6,
                            # mainCategory_id = mainCategory
                        )
                        prompt_instance = PromptResponse.objects.create(
                            llm_id = llm_instance.id, 
                            response_text = text, 
                            prompt_id = promp.id,
                            user_id = request.user.id,
                            response_type = 6,
                            tokenUsed = 1,
                            category_id= category,
                            # mainCategory_id = mainCategory
                        )

                        LLM_Tokens.objects.create(
                            user_id = request.user.id,
                            llm_id = llm_instance.id,
                            prompt_id = promp.id,
                            file_token_used = 1
                        )
                        
                        data = {
                            'model': model,
                            'text': text,
                            'promptId': promp.id, 
                            'responseId': prompt_instance.id 
                        }

                        return Response(data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GeminiProTextToText(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                promptWriter = serializer.validated_data.get('promptWriter')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                response = StreamingHttpResponse(
                    textToTextUsingGemini(prompt, model, model_string, 
                                          request.user, category, 
                                          llm_instance.id, promptWriter)
                                        )

                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MistralTextToText(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:       
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                promptWriter = serializer.validated_data.get('promptWriter')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                response = StreamingHttpResponse(
                            generateTextToTextUsingTogether(
                                prompt, model, model_string, 
                                request.user, category, 
                                llm_instance.id, promptWriter)
                            )
                
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LlamaTextToText(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:        
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                promptWriter = serializer.validated_data.get('promptWriter')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                response = StreamingHttpResponse(
                            generateTextToTextUsingTogether(
                                prompt, model, model_string, 
                                request.user, category, 
                                llm_instance.id, promptWriter
                            )
                        )
                
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GemmaInstructTextToText(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:            
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                promptWriter = serializer.validated_data.get('promptWriter')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                response = StreamingHttpResponse(
                            generateTextToTextUsingTogether(
                                prompt, model, model_string, 
                                request.user, category, 
                                llm_instance.id, promptWriter
                            )
                        )
                
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GeminiPictureToText(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:        
            serializer = PictureToTextSerializer(data=request.data)

            if serializer.is_valid():
                uploaded_image = request.FILES.get('image')
                prompt = request.data.get('prompt')
                model = request.data.get('model')
                category = request.data.get('category')
                # mainCategory = request.data.get('mainCategory')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                               
                response = StreamingHttpResponse(
                            generateImageToTextUsingGemini(
                                prompt, model, model_string, 
                                request.user, category, 
                                llm_instance.id, uploaded_image
                            )
                        )
                
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# Text To Image Generator
class GeminiTextToImage(APIView):
    permission_classes = [IsAuthenticated, FileSubscriptionAuth]

    def post(self, request):
        try:        
            serializer = TextToImageSerializer(data=request.data)

            if serializer.is_valid():
                prompt = request.data.get('prompt')
                model = request.data.get('model')
                category = request.data.get('category')
                # mainCategory = request.data.get('mainCategory')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                               
                image = generateTextToImageUsingTogether(prompt, model_string)

                decoded_image = base64.b64decode(image)

                imgKey = "multinote/texttoimage/" + str(time.time()) + ".png"
                uploadImage(BytesIO(decoded_image), imgKey, "image/png")

                manage_file_token(request.user)
                
                # Save the Prompt and Prompt Response
                try:
                    promp = Prompt.objects.get(
                        prompt_text=prompt, 
                        category=category, 
                        # mainCategory=mainCategory, 
                        user=request.user.id
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id=llm_instance.id, response_image=imgKey, 
                        prompt_id=promp.id, 
                        user_id = request.user.id,
                        response_type = 4,
                        tokenUsed = 1,
                        category_id=category, 
                        # mainCategory_id=mainCategory, 
                    )
                except Prompt.DoesNotExist:
                    promp = Prompt.objects.create(
                        prompt_text=prompt, 
                        user_id=request.user.id, 
                        category_id=category,
                        response_type = 4,
                        # mainCategory_id=mainCategory, 
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id=llm_instance.id, 
                        response_image=imgKey, 
                        prompt_id=promp.id, 
                        user_id = request.user.id,
                        response_type = 4,
                        tokenUsed = 1,
                        category_id=category,
                        # mainCategory_id=mainCategory,
                    )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )

                data = {
                    'model': model,
                    'generated_content': imgKey,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id
                }
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Text To Image Generator
class CodeGenerateByTogether(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:            
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                # mainCategory = serializer.validated_data.get('mainCategory')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                response = StreamingHttpResponse(
                            generateCodeUsingTogether(
                                prompt, model, model_string,
                                request.user, category, 
                                llm_instance.id
                            )
                        )
                
                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
                # response = generateCodeUsingTogether(prompt, model, model_string)
                # return Response({"data": response}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        




class OpenAiTextToText(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request):
        try:
            serializer = TextToTextSerializer(data=request.data)

            if serializer.is_valid():
                prompt = serializer.validated_data.get('prompt')
                model = serializer.validated_data.get('model')
                category = serializer.validated_data.get('category')
                promptWriter = serializer.validated_data.get('promptWriter')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                response = StreamingHttpResponse(
                    generateTextByOpenAI(prompt, model, model_string, 
                                          request.user, category, llm_instance.id, promptWriter)
                                        )

                response['Content-Type'] = 'text/event-stream'
                response['Cache-Control'] = 'no-cache'
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# Text To Speech Generator
class TextToSpeechGenerator(APIView):
    permission_classes = [IsAuthenticated, FileSubscriptionAuth]

    def post(self, request):
        try:        
            serializer = TextToImageSerializer(data=request.data)

            if serializer.is_valid():
                prompt = request.data.get('prompt')
                model = request.data.get('model')
                category = request.data.get('category')
                # mainCategory = request.data.get('mainCategory')
                voice = request.data.get('voice')

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                
                image = generateTextToSpeech(prompt, model_string, voice)

                fileKey = "multinote/textToSpeech/" + str(time.time()) + ".mp3"
                uploadImage(BytesIO(image), fileKey, "audio/mpeg")

                manage_file_token(request.user)

                # Save the Prompt and Prompt Response
                try:
                    promp = Prompt.objects.get(
                        prompt_text=prompt, 
                        category=category, 
                        # mainCategory=mainCategory, 
                        user=request.user.id
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id=llm_instance.id, 
                        response_audio=fileKey, 
                        prompt_id=promp.id,
                        user_id = request.user.id,
                        response_type = 5,
                        tokenUsed = 1,
                        category_id=category,
                        # mainCategory_id = mainCategory
                    )
                except Prompt.DoesNotExist:
                    promp = Prompt.objects.create(
                        prompt_text=prompt, 
                        user_id=request.user.id, 
                        category_id= category,
                        response_type = 5,
                        # mainCategory_id = mainCategory
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id=llm_instance.id, 
                        response_audio=fileKey, 
                        prompt_id=promp.id,
                        user_id = request.user.id,
                        response_type = 5,
                        tokenUsed = 1,
                        category_id=category,
                        # mainCategory_id = mainCategory
                    )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )


                data = {
                    'model': model,
                    'generated_content': fileKey,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id
                }
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class SpeechToTextGenerator(APIView):
    permission_classes = [IsAuthenticated, FileSubscriptionAuth]
    
    def post(self, request):
        try:        
            serializer = SpeechToTextSerializer(data=request.data)

            if serializer.is_valid():
                uploaded_file = request.FILES.get('file')
                # prompt = request.data.get('prompt')
                model = request.data.get('model')
                category = request.data.get('category')
                # mainCategory = request.data.get('mainCategory')


                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not llm_instance.model_string:
                    return Response({'message': f'Model String against "{model}" not found.',
                    }, status=status.HTTP_400_BAD_REQUEST)
                               
                text = speechToTextGenerator(model_string, uploaded_file)

                fileKey = "multinote/speechToText/" + str(request.user.id) + "-" + uploaded_file.name
                uploadImage(uploaded_file, fileKey, uploaded_file.content_type)

                manage_file_token(request.user)

                # Save the Prompt and Prompt Response
                try:
                    promp = Prompt.objects.get(
                        category = category, 
                        # mainCategory = mainCategory, 
                        user = request.user.id, 
                        prompt_audio = fileKey
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id = llm_instance.id, 
                        response_text = text, 
                        prompt_id = promp.id,
                        user_id = request.user.id,
                        response_type = 6,
                        tokenUsed = 1,
                        category_id= category,
                        # mainCategory_id = mainCategory
                    )
                except Prompt.DoesNotExist:
                    promp = Prompt.objects.create( 
                        user_id = request.user.id, 
                        prompt_audio = fileKey,
                        category_id= category,
                        response_type = 6,
                        # mainCategory_id = mainCategory
                    )
                    prompt_instance = PromptResponse.objects.create(
                        llm_id = llm_instance.id, 
                        response_text = text, 
                        prompt_id = promp.id,
                        user_id = request.user.id,
                        response_type = 6,
                        tokenUsed = 1,
                        category_id= category,
                        # mainCategory_id = mainCategory
                    )

                LLM_Tokens.objects.create(
                    user_id = request.user.id,
                    llm_id = llm_instance.id,
                    prompt_id = promp.id,
                    file_token_used = 1
                )
                
                data = {
                    'model': model,
                    'text': text,
                    'promptId': promp.id, 
                    'responseId': prompt_instance.id 
                }

                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'message': 'An error occurred during content generation.',
                'error': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

