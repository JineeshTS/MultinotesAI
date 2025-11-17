# genareting logic prompttest/utils.py
import os
import requests
from pathlib import Path
from django.conf import settings

# for google
import google.generativeai as genai
from rest_framework.response import Response
import json
from PIL import Image
import sseclient
import io
import httpx
import time
import asyncio
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.utils import timezone
from channels.layers import get_channel_layer
from together import Together
from openai import OpenAI
import openai
from concurrent.futures import ThreadPoolExecutor
from authentication.awsservice import uploadImage
import concurrent.futures
from asgiref.sync import async_to_sync, sync_to_async
from .models import LLM, PromptResponse, NoteBook, Folder, Prompt, LLM_Tokens,GroupResponse
from django.http import JsonResponse, StreamingHttpResponse
from planandsubscription.models import Subscription
from rest_framework import status
import threading
import concurrent.futures
from ticketandcategory.models import Category
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
# import tiktoken

GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
LLama_API_KEY=os.getenv('LLama_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
togetherClient = Together(api_key=LLama_API_KEY)
openAiClient = OpenAI()


channel_layer = get_channel_layer()

thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

def send_response_to_socket(data, group_name):
    async_to_sync(channel_layer.group_send)(group_name, {'type': 'send_response', 'response': json.dumps(data)})

def manage_token(user, tokenCount):
        cluster = user.cluster
        if cluster:
            subs = cluster.subscription
        else:
            subs = Subscription.objects.filter(user=user.id, status__in=['active', 'trial']).first()
        subs.balanceToken -= tokenCount
        subs.usedToken += tokenCount
        subs.save()


# Gemini Api
def textToTextUsingGemini(prompt, myModel, modelString, user, categoryID, llmId, promptWriter, groupId):
        if groupId:
            group = GroupResponse.objects.get(pk=groupId, is_delete=False)

            if not group.conversation_history:
                prompt_history = ""
                conversation_history = []
            else:
                conversation_history = json.loads(group.conversation_history, strict=False)

                prompt_history = "\n".join([f"{turn['role']}: {turn['content']}" for turn in conversation_history])
                
                # conversation_history.append({"role": "user", "content": prompt})
                # print("History is ---> ", conversation_history)


            model = genai.GenerativeModel(modelString)

            prompts = f"""Conversation History:
                {prompt_history}

                User: {prompt}
                Model:"""

            stream = model.generate_content(prompts, stream=True)
            

            # group.conversation_history = None
            # group.save()

            # model = genai.GenerativeModel(modelString)
            # stream = model.generate_content(prompt, stream=True)

        else:
            model = genai.GenerativeModel(modelString)
            stream = model.generate_content(prompt, stream=True)

        text = ""
        for chunk in stream:
            # for part in chunk.parts:
                # text += part.text
            text += chunk.text
            my_dict = json.dumps({"model": myModel,
                    "text": text})
            yield my_dict

        tokenCount = model.count_tokens((text)).total_tokens
        manage_token(user, tokenCount)

        if groupId:
            conversation_history.append({"role": "user", "content": prompt})
            conversation_history.append({"role": "model", "content": text})
            short_history = conversation_history[-20:]
            group.conversation_history = json.dumps(short_history)
            group.save()

        # Save the Prompt and Prompt Response
        # try:
        #     promp = Prompt.objects.get(
        #         prompt_text=prompt, 
        #         category=categoryID, 
        #         # mainCategory=mainCategory,
        #         user=user.id
        #     )
        #     response = PromptResponse.objects.create(
        #         llm_id=llmId, response_text=text, 
        #         prompt_id=promp.id, 
        #         user_id = user.id,
        #         category_id=categoryID, 
        #         response_type = 8 if promptWriter else 2,
        #         # mainCategory_id= mainCategory,
        #         tokenUsed = tokenCount
        #     )
        # except Prompt.DoesNotExist:
        promp = Prompt.objects.create(
            prompt_text=prompt, 
            user_id=user.id, 
            category_id=categoryID,
            group_id=groupId,
            response_type = 8 if promptWriter else 2,
            # mainCategory_id= mainCategory
        )
        response = PromptResponse.objects.create(
            llm_id=llmId, response_text=text, 
            prompt_id=promp.id, 
            user_id = user.id,
            category_id=categoryID, 
            # mainCategory_id=mainCategory,
            tokenUsed = tokenCount,
            response_type = 8 if promptWriter else 2
        )

        LLM_Tokens.objects.create(
            user_id = user.id,
            llm_id = llmId,
            prompt_id = promp.id,
            text_token_used = tokenCount
        )

        my_dict = json.dumps({"model": myModel, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
        yield my_dict

# Gemini Api
def textToCodeUsingGemini(prompt, myModel, modelString, user, categoryID, llmId, promptWriter, groupId):
        model = genai.GenerativeModel(
            model_name=modelString,
            tools='code_execution')
        stream = model.generate_content(prompt, stream=True)

        text = ""
        for chunk in stream:
            # for part in chunk.parts:
                # text += part.text
            text += chunk.text
            my_dict = json.dumps({"model": myModel,
                    "text": text})
            yield my_dict

        tokenCount = model.count_tokens((text)).total_tokens
        manage_token(user, tokenCount)

        promp = Prompt.objects.create(
            prompt_text=prompt, 
            user_id=user.id, 
            category_id=categoryID,
            group_id=groupId,
            response_type = 8 if promptWriter else 2,
            # mainCategory_id= mainCategory
        )
        response = PromptResponse.objects.create(
            llm_id=llmId, response_text=text, 
            prompt_id=promp.id, 
            user_id = user.id,
            category_id=categoryID, 
            # mainCategory_id=mainCategory,
            tokenUsed = tokenCount,
            response_type = 8 if promptWriter else 2
        )

        LLM_Tokens.objects.create(
            user_id = user.id,
            llm_id = llmId,
            prompt_id = promp.id,
            text_token_used = tokenCount
        )

        my_dict = json.dumps({"model": myModel, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
        yield my_dict

def is_utf8mb4_compatible(text):
    try:
        # Try encoding the string to UTF-8
        text.encode('utf-8')
        return True
    except UnicodeEncodeError:
        return False
    
# Together Api
def generateTextToTextUsingTogether(prompt, model, modelString, user, categoryID, llmId, promptWriter, groupId):

    try:   
        if groupId:
            group = GroupResponse.objects.get(pk=groupId, is_delete=False)

            conversation_history = [{"role": "system", "content": "You are a helpful assistant."}] if not group.conversation_history else json.loads(group.conversation_history, strict=False)


            conversation_history.append({"role": "user", "content": prompt})


            stream = togetherClient.chat.completions.create(
                model=modelString,
                messages= conversation_history,
                stream=True,
            )

            # group.conversation_history = None
            # group.save()

            # stream = togetherClient.chat.completions.create(
            #     model=modelString,
            #     messages=[{"role": "user", "content": prompt}],
            #     stream=True,
            # )

        else: 
            stream = togetherClient.chat.completions.create(
                model=modelString,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
    except Exception as e:
        json_part = e._message.split(' - ')[1]

        # Parse the JSON
        error_data = json.loads(json_part)

        # Get the message
        message = error_data['message']

        my_dict = json.dumps({"error": message, "status": 404})
        # yield f"data: {my_dict}\n\n"
        yield my_dict
        return

    text = ""
    for chunk in stream:
        # print("Value is ----> ", chunk.choices[0].delta)
        if chunk.choices and chunk.choices[0].delta.content is not None:
            text += chunk.choices[0].delta.content
            my_dict = json.dumps({"model": model, 
                        "text": text})
                            
            yield my_dict

    tokenCount = chunk.usage.total_tokens
    manage_token(user, tokenCount)

    if groupId:
        conversation_history.append({"role": "assistant", "content": text})
        short_history = conversation_history[-20:]
        group.conversation_history = json.dumps(short_history)
        group.save()

    # Save the Prompt and Prompt Response
    # try:
        # promp = Prompt.objects.get(
        #     prompt_text=prompt, 
        #     category=categoryID, 
        #     # mainCategory=mainCategory, 
        #     user=user.id
        # )
        # response = PromptResponse.objects.create(
        #     llm_id=llmId, 
        #     response_text=text, 
        #     prompt_id=promp.id,
        #     user_id = user.id,
        #     response_type = 8 if promptWriter else 2,
        #     category_id=categoryID,
        #     # mainCategory_id=mainCategory,
        #     tokenUsed = tokenCount
        # )
    # except Prompt.DoesNotExist:
    promp = Prompt.objects.create(
        prompt_text=prompt, 
        user_id=user.id, 
        category_id=categoryID,
        group_id=groupId,
        response_type = 8 if promptWriter else 2,
        # mainCategory_id=mainCategory
    )
    response = PromptResponse.objects.create(
        llm_id=llmId, 
        response_text= text, 
        prompt_id=promp.id,
        user_id = user.id,
        response_type = 8 if promptWriter else 2,
        tokenUsed = tokenCount,
        category_id=categoryID,
        # mainCategory_id=mainCategory
    )

    LLM_Tokens.objects.create(
        user_id = user.id,
        llm_id = llmId,
        prompt_id = promp.id,
        text_token_used = tokenCount
    )

    my_dict = json.dumps({"model": model, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
    yield my_dict


#Image To Text Api
def generateImageToTextUsingGemini(prompt, myModel, modelString, user, categoryID, llmId, img, groupId):

    # print(f"Uploading file...")
    # video_file = genai.upload_file(path=settings.BASE_DIR/img.name)
    # print(f"Completed upload: {video_file.uri}")

    # # Check whether the file is ready to be used.
    # while video_file.state.name == "PROCESSING":
    #     print('.', end='')
    #     time.sleep(10)
    #     video_file = genai.get_file(video_file.name)

    # if video_file.state.name == "FAILED":
    #     raise ValueError(video_file.state.name)
    
    # # Create the prompt.
    # prompt = "Summarize this video. Then create a quiz with answer key based on the information in the video."

    # # Choose a Gemini model.
    # model = genai.GenerativeModel(model_name="gemini-1.5-pro")

    # # Make the LLM request.
    # print("Making LLM inference request...")
    # stream = model.generate_content([video_file, prompt],
    #                                 request_options={"timeout": 600}, stream=True)

    # # Print the response, rendering any Markdown
    # # print(stream.text)
    
    # os.remove(settings.BASE_DIR/img.name)




    img_pil = Image.open(img)

    model = genai.GenerativeModel(modelString)
    stream = model.generate_content([prompt, img_pil], stream=True)
 

    text = ""
    for chunk in stream:
        if chunk.text is not None:
            for part in chunk.parts:
                text += part.text
            # text += chunk.text
                my_dict = json.dumps({"model": myModel, 
                        "text": text})
                yield my_dict


    imgKey = "multinote/imageToText/" + str(user.id) + "-" + img.name
    uploadImage(img, imgKey, img.content_type)

    tokenCount = model.count_tokens((text)).total_tokens
    manage_token(user, tokenCount)

    # Save the Prompt and Prompt Response
    # try:
    #     promp = Prompt.objects.get(
    #         prompt_text=prompt, category=categoryID, 
    #         user=user.id, prompt_image=imgKey, 
    #         # mainCategory=mainCategory
    #     )
    #     response = PromptResponse.objects.create(
    #         llm_id=llmId, response_text=text, 
    #         prompt_id=promp.id, 
    #         user_id = user.id,
    #         response_type = 3,
    #         tokenUsed = tokenCount,
    #         category_id=categoryID,
    #         # mainCategory_id=mainCategory
    #     )
    # except Prompt.DoesNotExist:
    promp = Prompt.objects.create(
        prompt_text=prompt, 
        user_id=user.id, 
        prompt_image=imgKey,
        category_id=categoryID, 
        group_id=groupId, 
        response_type = 3,
        # mainCategory_id=mainCategory
    )
    response = PromptResponse.objects.create(
        llm_id=llmId, response_text=text, 
        prompt_id=promp.id, 
        user_id = user.id,
        response_type = 3,
        tokenUsed = tokenCount,
        category_id=categoryID,
        # mainCategory_id=mainCategory
    )

    LLM_Tokens.objects.create(
        user_id = user.id,
        llm_id = llmId,
        prompt_id = promp.id,
        text_token_used = tokenCount
    )


    my_dict = json.dumps({"model": myModel, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
    yield my_dict

#Image To Text Api
def generateAudioToTextUsingGemini(modelString, audio_file):
    # audio_data = audio_file.read()
    # buffer = BytesIO(audio_data)
    # buffer.name = audio_file.name
    # response = openAiClient.audio.transcriptions.create(
    #     model=modelString,
    #     file=buffer
    # )
    # return response.text

    # myfile = genai.upload_file(media / "sample.mp3")
    myfile = genai.upload_file(path=settings.BASE_DIR/audio_file.name)
    # print(f"{myfile=}")

    model = genai.GenerativeModel(modelString)
    result = model.generate_content([myfile, "Describe this audio clip"])
    # print(f"{result.text=}")
    os.remove(settings.BASE_DIR/audio_file.name)
    return result.text


#Gemini Video To Text Api
def generateVideoToTextUsingGemini(prompt, myModel, modelString, user, categoryID, llmId, img, groupId):

    # print(f"Uploading file...")
    video_file = genai.upload_file(path=settings.BASE_DIR/img.name)
    # print(f"Completed upload: {video_file.uri}")

    # Check whether the file is ready to be used.
    while video_file.state.name == "PROCESSING":
        # print('.', end='')
        time.sleep(10)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(video_file.state.name)
    
    # Create the prompt.
    # prompt = "Summarize this video. Then create a quiz with answer key based on the information in the video."

    # Choose a Gemini model.
    model = genai.GenerativeModel(model_name=modelString)

    # Make the LLM request.
    # print("Making LLM inference request...")
    stream = model.generate_content([video_file, prompt],
                                    request_options={"timeout": 600}, stream=True)

    # Print the response, rendering any Markdown
    # print(stream.text)
    

    # img_pil = Image.open(img)

    # model = genai.GenerativeModel(modelString)
    # stream = model.generate_content([prompt, img_pil], stream=True)
 

    text = ""
    for chunk in stream:
        if chunk.text is not None:
            for part in chunk.parts:
                text += part.text
            # text += chunk.text
                my_dict = json.dumps({"model": myModel, 
                        "text": text})
                yield my_dict


    imgKey = "multinote/imageToText/" + str(user.id) + "-" + img.name
    uploadImage(img, imgKey, img.content_type)


    tokenCount = model.count_tokens((text)).total_tokens
    manage_token(user, tokenCount)


    promp = Prompt.objects.create(
        prompt_text=prompt, 
        user_id=user.id, 
        prompt_image=imgKey,
        category_id=categoryID, 
        group_id=groupId, 
        response_type = 3,
        # mainCategory_id=mainCategory
    )
    response = PromptResponse.objects.create(
        llm_id=llmId, response_text=text, 
        prompt_id=promp.id, 
        user_id = user.id,
        response_type = 3,
        tokenUsed = tokenCount,
        category_id=categoryID,
        # mainCategory_id=mainCategory
    )

    LLM_Tokens.objects.create(
        user_id = user.id,
        llm_id = llmId,
        prompt_id = promp.id,
        text_token_used = tokenCount
    )

    os.remove(settings.BASE_DIR/img.name)


    my_dict = json.dumps({"model": myModel, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
    yield my_dict


def generateTextToImageUsingTogether(prompt, model_string, width, height):
    response = togetherClient.images.generate(
        prompt=prompt,
        model=model_string,
        steps=4,
        n=1,
        width=width,
        height=height,
        response_format="b64_json"
    )
    return response.data[0].b64_json

def generateTextToImageUsingOpenai(prompt, model_string, widht, height):
    response = openAiClient.images.generate(
        prompt=prompt,
        model=model_string,
        n=1,
        # size="1024x1024",
        size=f"{widht}x{height}",
        response_format="b64_json"
)
    return response.data[0].b64_json


def generateCodeUsingTogether(prompt, myModel, model_string, user, categoryId, llmId, groupId):
    try:
        stream = togetherClient.completions.create(
            model= model_string,
            # model="codellama/CodeLlama-70b-hf",
            # model="Phind/Phind-CodeLlama-34B-Python-v1",
            # model="bigcode/starcoder",
            prompt= prompt,
            stream= True
        )
        # print(stream.choices[0].text)
        # return stream.choices[0].text
    except Exception as e:
        json_part = e._message.split(' - ')[1]

        # Parse the JSON
        error_data = json.loads(json_part)

        # Get the message
        message = error_data['message']

        my_dict = json.dumps({"error": message, "status": 404})
        yield my_dict
        return

    text = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            text += chunk.choices[0].delta.content
            my_dict = json.dumps({"model": myModel, 
                        "text": text})
            
            # print(text)
                            
            yield my_dict

    tokenCount = chunk.usage.total_tokens
    manage_token(user, tokenCount)

    # Save the Prompt and Prompt Response
    # try:
    #     promp = Prompt.objects.get(
    #         prompt_text=prompt, 
    #         category=categoryId, 
    #         # mainCategory=mainCategory, 
    #         user=user.id
    #     )
    #     response = PromptResponse.objects.create(
    #         llm_id=llmId, response_text=text, 
    #         prompt_id=promp.id, 
    #         user_id = user.id,
    #         response_type = 7,
    #         tokenUsed = tokenCount,
    #         category_id=categoryId, 
    #         # mainCategory_id=mainCategory, 
    #     )
    # except Prompt.DoesNotExist:
    promp = Prompt.objects.create(
        prompt_text=prompt, 
        user_id=user.id, 
        category_id=categoryId,
        group_id=groupId,
        response_type = 7,
        # mainCategory_id=mainCategory
    )
    response = PromptResponse.objects.create(
        llm_id=llmId, response_text=text, 
        prompt_id=promp.id, 
        user_id = user.id,
        response_type = 7,
        tokenUsed = tokenCount,
        category_id=categoryId,
        # mainCategory_id=mainCategory
    )

    LLM_Tokens.objects.create(
        user_id = user.id,
        llm_id = llmId,
        prompt_id = promp.id,
        text_token_used = tokenCount
    )

    my_dict = json.dumps({"model": myModel, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
    yield my_dict


# Gemini Api
def generateUsingGemini(prompt, modelString, myModel, groupName):
    try:
        model = genai.GenerativeModel(modelString)
        stream = model.generate_content(prompt, stream=True)

        for chunk in stream:
            data = {
                "Model": myModel,
                "Text": chunk.text or "",
            }
            send_response_to_socket(data, groupName)
    except Exception as e:
        send_response_to_socket({"Message": str(e)}, groupName)



# Together Api
def generateTextByTogether(prompt, modelString, model, groupName):
    try:
        stream = togetherClient.chat.completions.create(
            model=modelString,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        text = ""
        i = 0
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                text += chunk.choices[0].delta.content
                i += 1
                if i >= 50:
                    data = {
                        "Model": model,
                        "Text": text,
                    }
                    send_response_to_socket(data, groupName)
                    text = ""
                    i = 0
        # Send remaining text if any
        if text:
            data = {
                "Model": model,
                "Text": text,
            }
            send_response_to_socket(data, groupName)
    except Exception as e:
        send_response_to_socket({"Message": str(e)}, groupName)
    

        

# Gemini Api
def generateUsingGeminiTest(prompt, modelString, myModel, queue):
        # time.sleep(60)
        # print(myModel, timezone.now())
        model = genai.GenerativeModel(modelString)
        stream = model.generate_content(prompt, stream=True)
        
        text = ""
        for chunk in stream:
            for part in chunk.parts:
                text += part.text
                # text += chunk.text
                my_dict = json.dumps({"model": myModel, 
                        "text": text})
                queue.put(f"data: {my_dict}\n\n")

        my_dict = json.dumps({"model": myModel, "text": ["DONE"]})
        queue.put(f"data: {my_dict}\n\n")
        # print(myModel, timezone.now())
        queue.put("DONE")




# Together Api
def generateTextByTogetherTest(prompt, modelString, model, queue):
        # print(model, timezone.now())        
        stream = togetherClient.chat.completions.create(
            model=modelString,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        text = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                text += chunk.choices[0].delta.content
                my_dict = json.dumps({"model": model, 
                            "text": text
                          })
                queue.put(f"data: {my_dict}\n\n")

        my_dict = json.dumps({"model": model, "text": ["DONE"]})
        queue.put(f"data: {my_dict}\n\n")
        # print(model, timezone.now()) 
        queue.put("DONE")



# # OpenAI Api
# def generateTextByOpenAI(prompt, modelString, model, groupName):
#     try:
#         stream = openAiClient.chat.completions.create(
#             model= modelString,
#             messages= [{"role": "user", "content": prompt}],
#             stream= True
#             # temperature= 0.7
#             # max_tokens=50
#         )
#         text = ""
#         i = 0
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 text += chunk.choices[0].delta.content
#                 i += 1
#                 if i >= 50:
#                     data = {
#                         "Model": model,
#                         "Text": text,
#                     }
#                     send_response_to_socket(data, groupName)
#                     text = ""
#                     i = 0
#         # Send remaining text if any
#         if text:
#             data = {
#                 "Model": model,
#                 "Text": text,
#             }
#             send_response_to_socket(data, groupName)
#     except Exception as e:
#         send_response_to_socket({"Message": str(e)}, groupName)

# OpenAI Api
def generateTextByOpenAI(prompt, myModel, modelString, user, categoryID, llmId, promptWriter, groupId):

    if groupId:
        group = GroupResponse.objects.get(pk=groupId, is_delete=False)

        conversation_history = [{"role": "system", "content": "You are a helpful assistant."}] if not group.conversation_history else json.loads(group.conversation_history, strict=False)


        conversation_history.append({"role": "user", "content": prompt})


        stream = openAiClient.chat.completions.create(
            # model= "gpt-3.5-turbo",
            # model= "gpt-4",
            model= modelString,
            messages= conversation_history,
            stream= True,
            stream_options={"include_usage": True}
        )


    else: 
        stream = openAiClient.chat.completions.create(
            # model= "gpt-3.5-turbo",
            # model= "gpt-4",
            model= modelString,
            messages= [{"role": "user", "content": prompt}],
            stream= True,
            stream_options={"include_usage": True}
        )

    text = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            text += chunk.choices[0].delta.content
            # print(chunk.choices[0].delta.content, end="", flush=True)
            # print(text)
            my_dict = json.dumps({"model": myModel, 
                        "text": text})
            yield my_dict

    tokenCount = chunk.usage.total_tokens
    manage_token(user, tokenCount)

    if groupId:
        conversation_history.append({"role": "assistant", "content": text})
        short_history = conversation_history[-20:]

        group.conversation_history = json.dumps(short_history)
        group.save()

    # Save the Prompt and Prompt Response
    # try:
    #     promp = Prompt.objects.get(
    #         prompt_text=prompt, 
    #         category=categoryID, 
    #         # mainCategory=mainCategory, 
    #         user=user.id
    #     )
    #     response = PromptResponse.objects.create(
    #         llm_id=llmId, 
    #         response_text=text, 
    #         prompt_id=promp.id, 
    #         user_id = user.id,
    #         response_type = 8 if promptWriter else 2,
    #         tokenUsed = tokenCount,
    #         category_id=categoryID,
    #         # mainCategory_id = mainCategory
    #     )
    # except Prompt.DoesNotExist:
    promp = Prompt.objects.create(
        prompt_text=prompt, 
        user_id=user.id, 
        category_id=categoryID,
        group_id=groupId,
        response_type = 8 if promptWriter else 2,
        # mainCategory_id = mainCategory
    )
    response = PromptResponse.objects.create(
        llm_id=llmId, response_text=text, 
        prompt_id=promp.id, 
        user_id = user.id,
        response_type = 8 if promptWriter else 2,
        tokenUsed = tokenCount,
        category_id=categoryID,
        # mainCategory_id = mainCategory
    )

    LLM_Tokens.objects.create(
        user_id = user.id,
        llm_id = llmId,
        prompt_id = promp.id,
        text_token_used = tokenCount
    )

    my_dict = json.dumps({"model": myModel, "promptId": promp.id, "responseId": response.id, "groupId": groupId, "text": "DONE"})
    yield my_dict
            


def generateChatGPT():
    stream = openAiClient.chat.completions.create(
        # model= "gpt-3.5-turbo",
        model= "gpt-4",
        messages= [{"role": "user", "content": "what is the future socope of django framework?"}],
        stream= True
    )
    text = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            text += chunk.choices[0].delta.content
            # print(chunk.choices[0].delta.content, end="", flush=True)
            # print(text)
            yield f"data: {text}\n"


@require_http_methods(["POST"])
@csrf_exempt
def generateUsingOpenAi(request):
    try:


        response = StreamingHttpResponse(generateChatGPT())
        
        response['Content-Type'] = 'text/event-stream'
        response['Cache-Control'] = 'no-cache'
        return response
        # return HttpResponse(stream)
    except openai.RateLimitError as limitError:
        return HttpResponse(limitError)

# async def generateTextByOpenAI(prompt, modelString, model, groupName):
#     print()
#     print(model, timezone.now())
#     try:
#         stream = openAiClient.chat.completions.create(
#             model= modelString,
#             messages= [{"role": "user", "content": prompt}],
#             stream= True
#         )
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 print(chunk.choices[0].delta.content, end="", flush=True)
#                 data = {
#                         "Model": model, 
#                         "Text": chunk.choices[0].delta.content,
#                         "Time": str(timezone.now())
#                         }                        
#                 await send_response_to_socket(data, groupName)

#     except Exception as e:
#         await send_response_to_socket({"Message": str(e)}, groupName)




@require_http_methods(["POST"])
@csrf_exempt
async def generateUsingTogether2(request):
    data = json.loads(request.body.decode('utf-8'))
    prompt = data.get('prompt')
    groupName = data.get('groupName')
    model = data.get('model')
    modelString = data.get('modelString')
    try:
        # print(timezone.now())
        stream = togetherClient.chat.completions.create(
            model=modelString,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        # print(timezone.now())
        for chunk in stream:
            data = {
                "Model": model,
                "Text": chunk.choices[0].delta.content or "",
                "Time": str(timezone.now())
            }
            await send_response_to_socket({"Text": chunk.choices[0].delta.content or ""}, groupName)
        return JsonResponse({'data': "All data fetched successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        send_response_to_socket({"Message": str(e)}, groupName)



@require_http_methods(["POST"])
@csrf_exempt
async def generateUsingGemini2(request):
    data = json.loads(request.body.decode('utf-8'))
    prompt = data.get('prompt')
    groupName = data.get('groupName')
    myModel = data.get('model')
    modelString = data.get('modelString')
    
    try:
        # print(timezone.now())
        model = genai.GenerativeModel(modelString)
        stream = model.generate_content(prompt, stream=True)
        # print(timezone.now())

        for chunk in stream:
            data = {
                "Model": myModel,
                "Text": chunk.text or "",
                "Time": str(timezone.now())
            }
            await send_response_to_socket({"Text": chunk.text or ""}, groupName)
        return JsonResponse({'data': "All data fetched successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        # print("Error is ----> ", e)
        await send_response_to_socket({"Message": str(e)}, groupName)
        return JsonResponse({'data': "No data fetch"}, status=status.HTTP_404_NOT_FOUND)



def generateFromImageUsingGemini(prompt,img):
    
    # print(prompt,img)
    img_pil = Image.open(img)
    # print(img_pil)
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([f'{prompt}',img_pil])
    # print(response)
    # print(response.text)
    

    return response.text


async def generateUsingTogether(prompt, model_string):
    # print("model_string is ------------------------>", model_string)
    reqUrl = 'https://api.together.xyz/v1/chat/completions'
    reqHeaders = {
        "accept": "text/event-stream",
        "Authorization": f"Bearer {LLama_API_KEY}"
    }

    reqBody = {
        "model": model_string,
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}",
            }
        ],
        "stream": True,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
        "stop": [
            "[/INST]",
            "</s>"
        ],
        "repetitive_penalty": 1,
        "update_at": "2024-02-24T09:19:02.236Z"
    } 
    # print(timezone.now())
    request = requests.post(reqUrl, stream=True, headers=reqHeaders, json=reqBody)

    # print(timezone.now())

    client = sseclient.SSEClient(request)
    for event in client.events():
        if event.data != '[Done]':
            print(json.loads(event.data)['choices'][0]['text'], end="", flust=True)

    # print(timezone.now())



def generateImageUsingTogether(prompt,model_string):

        endpoint = 'https://api.together.xyz/inference'
        payload = {
        "model": model_string,
        "prompt": prompt,
        "n": 1, 
        "steps": 20
        }

        headers = {
        "Authorization": f"Bearer {LLama_API_KEY}",
        "User-Agent": "multinotes.ai"
        }

        response = requests.post(endpoint, json=payload, headers=headers)
        data = response.json()
        # print(data)
        # Extract relevant image data
        # images = {
        # 'choices': data['output']['choices'],
        # 'result_type': data['output']['result_type']
        # }
        # print("Response is ---> ", response.data[0].b64_json)
        return data['output']['choices'][0]


def generateTextToSpeech(prompt, model_string, voice):
    # speech_file_path = Path(__file__).parent / "speech.mp3"
    response = openAiClient.audio.speech.create(
        model= model_string,
        voice= voice,
        input= prompt
    )
    # response.stream_to_file(speech_file_path)
    return response.content


#Speech To Text Api
def speechToTextGenerator(modelString, audio_file):
    audio_data = audio_file.read()
    buffer = BytesIO(audio_data)
    buffer.name = audio_file.name
    response = openAiClient.audio.transcriptions.create(
        model=modelString,
        file=buffer
    )
    return response.text

def remove_llm_model(model_to_remove):
    # Step 1: Retrieve the current value of llm_models and convert it to a list
    categories = Category.objects.all()

    for category in categories:
        # try:
        llm_models_list = json.loads(category.llm_models)
        # except json.JSONDecodeError:
        #     return  # Handle the case where llm_models is not a valid JSON string

        # Step 2: Remove the desired element from the list
        if model_to_remove in llm_models_list:
            llm_models_list.remove(model_to_remove)

            # Step 3: Convert the list back to a JSON string
            llm_models = json.dumps(llm_models_list)

            # Step 4: Save the updated string back to the llm_models field
            category.llm_models = llm_models
            category.save()  

# Together Api
def TestTextByTogether(request, pk):

    # try:
    try:       
        llm_instance = LLM.objects.get(id=pk, is_delete=False)
    except LLM.DoesNotExist:
        return JsonResponse({"message": "LLM Model Not Found Please Add Model."}, status=status.HTTP_400_BAD_REQUEST)
    
    type = request.GET.get('type')

    if type == "connect":
        if llm_instance.source == 2 and (llm_instance.text or llm_instance.code):
            try:
                togetherLLMClient = Together(api_key=llm_instance.api_key)
                start_time = time.time()
                
                stream = togetherLLMClient.chat.completions.create(
                    model=llm_instance.model_string,
                    messages=[{"role": "user", "content": 'List all of the states in the USA'}],
                    max_tokens= 150,
                    temperature=0.7,
                    top_p=0.7,
                    top_k=50,
                    repetition_penalty=1,
                    stop=["</s>"],
                    # stream=True,
                )

                # print("Id is ---> ", stream.id)
                # print("Object is ---> ", stream.object)
                # print("created is ---> ", stream.created)
                # print("Usage is ---> ", stream.usage)

                latency = time.time()-start_time
                latency = round(latency, 2)

                string_response = stream.json()
                response = json.loads(string_response)
                # print("Response is ---> ", response)

                if 'id' in string_response and response['usage']['completion_tokens'] != 2:
                    llm_instance.model_latensy = latency
                    llm_instance.test_status = "connected"
                    llm_instance.save()
                    return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
                else:
                    return JsonResponse({'message': 'Model is down by Gemini'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                json_part = e._message.split(' - ')[1]

                # print(json_part)

                # Parse the JSON
                error_data = json.loads(json_part)

                # Get the message
                message = error_data['message']

                return JsonResponse({'message': message}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 3 and llm_instance.text:
            try:
                genai.configure(api_key=llm_instance.api_key)
                start_time = time.time()

                model = genai.GenerativeModel(llm_instance.model_string)
                stream = model.generate_content('List all of the states in the USA')
                
                # print("Stream is ---> ", stream.__dir__())
                # print("Stream is ---> ", stream._done)
                # print("Stream is ---> ", stream._error)
                # print("Stream is ---> ", stream.text)

                latency = time.time()-start_time
                latency = round(latency, 2)


                if stream._error == None:
                    llm_instance.model_latensy = latency
                    llm_instance.test_status = "connected"
                    llm_instance.save()
                    return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
                else:
                    return JsonResponse({'message': 'Model is down by Gemini'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                # print("Error is ----------> ", e.__dir__())
                # print("Message is ----------> ", e.message)
                # print("Message is ----------> ", e._errors)

                return JsonResponse({'message': e.message}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 4 and llm_instance.text:
            start_time = time.time()
            url = "https://api.openai.com/v1/chat/completions"
            # Headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm_instance.api_key}",
            }

            # Payload (body of the request)
            data = {
                "model": llm_instance.model_string,
                "messages": [{"role": "user", "content": "Say this is a test!"}],
                "temperature": 0.7
            }

            # Sending the request
            response = requests.post(url, headers=headers, data=json.dumps(data))

            latency = time.time()-start_time
            latency = round(latency, 2)
            # Get the response and status code
            # response_json = response.json()  # Get the response as JSON
            status_code = response.status_code  # Get the HTTP status code

            # Output response and status code
            # print("Response JSON:", response_json)
            # print("Status Code:", status_code)
            if status_code == 200:
                llm_instance.model_latensy = latency
                llm_instance.test_status = "connected"
                llm_instance.save()
                return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'message': 'Model is down by Openai'}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 4 and llm_instance.text_to_audio:
            start_time = time.time()
            url = "https://api.openai.com/v1/audio/speech"
            # Headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm_instance.api_key}",
            }

            # Payload (body of the request)
            data = {
                "model": llm_instance.model_string,
                "input": "The quick brown fox jumped over the lazy dog.",
                "voice": "alloy"
            }

            # Sending the request
            response = requests.post(url, headers=headers, data=json.dumps(data))

            latency = time.time()-start_time
            latency = round(latency, 2)
            # Get the response and status code
            # response_json = response.json()  # Get the response as JSON
            status_code = response.status_code  # Get the HTTP status code

            # Output response and status code
            # print("Response JSON:", response_json)
            # print("Status Code:", status_code)
            if status_code == 200:
                llm_instance.model_latensy = latency
                llm_instance.test_status = "connected"
                llm_instance.save()
                return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'message': 'Model is down by Openai'}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 4 and llm_instance.audio_to_text:
            start_time = time.time()
            url = "https://api.openai.com/v1/audio/transcriptions"

            # Open the file in binary mode
            with open('speech.mp3', 'rb') as audio_file:
                # Prepare the multipart/form-data request
                files = {
                    'file': audio_file
                }
                
                # Data for the request
                data = {
                    'model': llm_instance.model_string
                }
                
                # Headers
                headers = {
                    "Authorization": f"Bearer {llm_instance.api_key}",
                }
                
                # Send the POST request
                response = requests.post(url, headers=headers, files=files, data=data)

            latency = time.time()-start_time
            latency = round(latency, 2)
            # Get the response and status code
            # response_json = response.json()  # Get the response as JSON
            status_code = response.status_code  # Get the HTTP status code

            # Output response and status code
            # print("Response JSON:", response_json)
            # print("Status Code:", status_code)
            if status_code == 200:
                llm_instance.model_latensy = latency
                llm_instance.test_status = "connected"
                llm_instance.save()
                return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'message': 'Model is down by Openai'}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 3 and llm_instance.image_to_text:
            try:
                genai.configure(api_key=llm_instance.api_key)
                start_time = time.time()

                model = genai.GenerativeModel(llm_instance.model_string)
                # stream = model.generate_content('List all of the states in the USA')
                image = Image.open('pic3.jpg')
                stream = model.generate_content(["Tell me about this Image", image ])

                latency = time.time()-start_time
                latency = round(latency, 2)


                if stream._error == None:
                    llm_instance.model_latensy = latency
                    llm_instance.test_status = "connected"
                    llm_instance.save()
                    return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
                else:
                    return JsonResponse({'message': 'fail'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:

                return JsonResponse({'message': e.message}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 2 and llm_instance.text_to_image:
            try:
                start_time = time.time()
                response = togetherClient.images.generate(
                    prompt="Give me image of Narender Modi",
                    model=llm_instance.model_string,
                    steps=4,
                    n=1,
                )

                latency = time.time()-start_time
                latency = round(latency, 2)

                llm_instance.model_latensy = latency
                llm_instance.test_status = "connected"
                llm_instance.save()
                return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)


            except Exception as e:

                json_part = e._message.split(' - ')[1]

                # Parse the JSON
                error_data = json.loads(json_part)

                # Get the message
                message = error_data['message']

                return JsonResponse({'message': message}, status=status.HTTP_400_BAD_REQUEST)
            
        elif llm_instance.source == 4 and llm_instance.text_to_image:
            start_time = time.time()
            url = "https://api.openai.com/v1/images/generations"

            # Headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm_instance.api_key}",
            }

            # Payload (body of the request)
            data = {
                "model": llm_instance.model_string,
                "prompt": "A cute baby sea otter",
                "n": 1,
                "size": "1024x1024"
            }

            # Sending the request
            response = requests.post(url, headers=headers, data=json.dumps(data))

            latency = time.time()-start_time
            latency = round(latency, 2)
            # Get the response and status code
            # response_json = response.json()  # Get the response as JSON
            status_code = response.status_code  # Get the HTTP status code

            # Output response and status code
            # print("Response JSON:", response_json)
            # print("Status Code:", status_code)
            if status_code == 200:
                llm_instance.model_latensy = latency
                llm_instance.test_status = "connected"
                llm_instance.save()
                return JsonResponse({'message': 'success', 'latency': latency}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'message': 'Model is down by Openai'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse({'message': "Model for this source not available"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        llm_instance.test_status = "disconnected"
        remove_llm_model(llm_instance.id)
        llm_instance.save()
        return JsonResponse({'message': 'LLM Model Disconnected'}, status=status.HTTP_200_OK)
    
# def split_into_batches(text, max_tokens, model="gpt-4"):
#     """Splits a large text into manageable batches based on token count."""
#     encoding = tiktoken.encoding_for_model(model)
#     tokens = encoding.encode(text)
    
#     # Split tokens into chunks
#     batches = [tokens[i:i + max_tokens] for i in range(0, len(tokens), max_tokens)]
    
#     # Decode batches back into text
#     # return [encoding.decode(batch) for batch in batches]
#     text_batches =  [encoding.decode(batch) for batch in batches]


# Together Api
def aiTogetherProcess(modelString, text, prompt, user):    
    stream = togetherClient.chat.completions.create(
        model=modelString,
        messages=[{"role": "user", "content": f"{text} \n {prompt} for above text"}],
    )

    # print("Together Value is ----> ", stream.choices[0].message.content)
    tokenCount = stream.usage.total_tokens
    # print("Together Total Token is ----> ", tokenCount)
    manage_token(user, tokenCount)

    return stream.choices[0].message.content

# Gemini Api
def aiGeminiProcess(modelString, text, prompt, user):
    model = genai.GenerativeModel(modelString)
    stream = model.generate_content(f"{text} \n {prompt} for above text")

    # print("Gemini Value is ----> ", stream.text)

    tokenCount = model.count_tokens((text)).total_tokens
    # print("Gemini Total Token is ----> ", tokenCount)
    manage_token(user, tokenCount)

    return stream.text

# OpenAI Api
def aiOpenAIProcess(modelString, text, prompt, user):
    stream = openAiClient.chat.completions.create(
        model= modelString,
        messages= [{"role": "user", "content": f"{text} \n {prompt} for above text"}],
    )
    # print("OpenAI Value is ----> ", stream.choices[0].message.content)
    tokenCount = stream.usage.total_tokens
    # print("OpenAi Total Token is ----> ", tokenCount)
    manage_token(user, tokenCount)
    return stream.choices[0].message.content

# def aiOpenAIProcess(modelString, text, prompt, user, batch_size=9000):
#     """
#     Process large text input by splitting it into manageable batches.
#     """
#     # Split text into batches
#     batches = split_into_batches(text, batch_size, modelString)
#     results = []

#     for batch in batches:
#         # print("Batch are ----> ", batch)

#         # Create a custom prompt for each batch
#         batch_prompt = f"{batch} \n {prompt} for above text"

#         # API call for the current batch
#         response = openAiClient.chat.completions.create(
#             model=modelString,
#             messages=[{"role": "user", "content": batch_prompt}],
#         )
        
#         # Append the batch result
#         results.append(response.choices[0].message.content)

#         # print("Results is ---------------> ", results)

#         # Manage tokens for the user
#         token_count = response.usage.total_tokens
#         manage_token(user, token_count)
    
#     # Combine all results into a single response
#     return "\n".join(results)

def extract_text_from_image(file_path):
    model = genai.GenerativeModel("gemini-1.5-flash")
    organ = Image.open(file_path)
    response = model.generate_content(["Tell me about this instrument", organ])
    # print(response.text)
    os.remove(file_path)
    return response.text

    


