# # genareting logic prompttest/utils.py
# import os
# import requests

# # for google
# import google.generativeai as genai
# from rest_framework.response import Response
# import json
# from PIL import Image
# import sseclient
# import io
# import httpx
# import time
# import asyncio
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from django.http import JsonResponse, HttpResponse
# from django.utils import timezone
# from channels.layers import get_channel_layer
# from together import Together
# from openai import OpenAI
# import openai
# from concurrent.futures import ThreadPoolExecutor
# import concurrent.futures
# from asgiref.sync import async_to_sync, sync_to_async


# GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
# LLama_API_KEY=os.getenv('LLama_API_KEY')
# genai.configure(api_key=GOOGLE_API_KEY)
# togetherClient = Together(api_key=LLama_API_KEY)
# openAiClient = OpenAI()


# # Gemini Api
# def generateUsingGemini(prompt, modelString, myModel, groupName):
#     # print()
#     # print(myModel, timezone.now())
#     try:
#         model = genai.GenerativeModel(modelString)
#         stream = model.generate_content(prompt, stream=True)

#         # j = 1
#         for chunk in stream:
#             # print("***********************************************************************")
#             data = {
#                 "Model": myModel,
#                 "Text": chunk.text or "",
#                 # "Time": str(timezone.now()),
#                 # "Count": j
#             }
#             # print(data)
#             send_response_to_socket(data, groupName)
#             # j += 1
#     except Exception as e:
#         send_response_to_socket({"Message": str(e)}, groupName)

# # Together Api
# def generateTextByTogether(prompt, modelString, model, groupName):
#     # print()
#     # print(model, timezone.now())
#     try:
#         stream = togetherClient.chat.completions.create(
#             model=modelString,
#             messages=[{"role": "user", "content": prompt}],
#             stream=True,
#         )
#         text = ""
#         i = 0
#         # j = 1
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 text += chunk.choices[0].delta.content
#                 i += 1
#                 if i >= 50:
#                     # print("***********************************************************************")
#                     data = {
#                         "Model": model,
#                         "Text": text,
#                         # "Time": str(timezone.now()),
#                         # "Count": j
#                     }
#                     # print(data)
#                     send_response_to_socket(data, groupName)
#                     text = ""
#                     i = 0
#                     # j += 1
#         # Send remaining text if any
#         if text:
#             # print("***********************************************************************")
#             data = {
#                 "Model": model,
#                 "Text": text,
#                 # "Time": str(timezone.now()),
#                 # "Response": "This is final text",
#                 # "Count": j
#             }
#             # print(data)
#             send_response_to_socket(data, groupName)
#     except Exception as e:
#         send_response_to_socket({"Message": str(e)}, groupName)


# channel_layer = get_channel_layer()

# thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

# def send_response_to_socket_async(data, group_name):
#     asyncio.run(send_response_to_socket(data, group_name))
# def send_response_to_socket(data, group_name):
#     async_to_sync(channel_layer.group_send)(group_name, {'type': 'send_response', 'response': json.dumps(data)})
#     # await channel_layer.group_send(group_name, {'type': 'send_response', 'response': json.dumps(data)})


# def background_task(data, group_name):
#     asyncio.run(send_response_to_socket(data, group_name))

# @require_http_methods(["POST"])
# @csrf_exempt
# def generateUsingOpenAi(request):
#     try:
#         stream = openAiClient.chat.completions.create(
#             model= "gpt-3.5-turbo",
#             # model= "gpt-4",
#             messages= [{"role": "user", "content": "Say this is a test!"}],
#             stream= True
#             # temperature= 0.7
#         )
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 print(chunk.choices[0].delta.content, end="", flush=True)
#         return HttpResponse(stream)
#     except openai.RateLimitError as limitError:
#         # print(limitError)
#         return HttpResponse(limitError)

# async def generateTextByOpenAI(prompt, modelString, model, groupName):
#     print()
#     print(model, timezone.now())
#     # await send_response_to_socket({"Message": model + " Start"}, groupName)
#     try:
#         stream = openAiClient.chat.completions.create(
#             # model="gpt-4",
#             model= modelString,
#             messages= [{"role": "user", "content": prompt}],
#             stream= True
#             # temperature= 0.7
#             # max_tokens=50
#         )
#         # print(model, timezone.now())
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 print(chunk.choices[0].delta.content, end="", flush=True)
#                 data = {
#                         "Model": model, 
#                         "Text": chunk.choices[0].delta.content,
#                         "Time": str(timezone.now())
#                         }                        
#                 await send_response_to_socket(data, groupName)
#                 # thread_pool.submit(send_response_to_socket_async, data, groupName)
#         # print()
#         # print("****************************************", model, timezone.now())
#                 # call_send_response_to_socket(data, groupName)
#                 # await channel_layer.group_send(
#                 #     groupName,
#                 #     {'type': 'send_response', 'response': json.dumps(
#                 #         {
#                 #             "Model": model, 
#                 #             "Text": chunk.choices[0].delta.content
#                 #         })
#                 #     }
#                 # )
#     except Exception as e:
#         await send_response_to_socket({"Message": str(e)}, groupName)
#         # thread_pool.submit(send_response_to_socket_async, {"Message": str(e)}, groupName)
#         # print("Error is ---> ", e)
#         # call_send_response_to_socket({"Message": str(e)}, groupName)
#         # await channel_layer.group_send(
#         #     groupName,
#         #     {'type': 'send_response', 'response': json.dumps({"Message": str(e)})}
#         # )



# def generateTextByTogether(prompt, modelString, model, groupName):
#     print()
#     print(model, timezone.now())
#     # await send_response_to_socket({"Message": model + " Start"}, groupName)
#     try:
#         stream = togetherClient.chat.completions.create(
#             model=modelString,
#             messages=[{"role": "user", "content": prompt}],
#             stream=True,
#         )
#         # print(model, timezone.now())

#         # with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
#         for chunk in stream:
#             data = {
#                 "Model": model,
#                 "Text": chunk.choices[0].delta.content or "",
#                 "Time": str(timezone.now())
#             }
#             send_response_to_socket(data, groupName)
#             # thread_pool.submit(send_response_to_socket_async, data, groupName)
#         # print()
#         # print("************************************",model, timezone.now())
#                 # call_send_response_to_socket(data, groupName)
#                 # await channel_layer.group_send(
#                 #     groupName,
#                 #     {'type': 'send_response', 'response': json.dumps(data)}
#                 # )
#                 # print(chunk.choices[0].delta.content or "", end="", flush=True)
#     except Exception as e:
#         send_response_to_socket({"Message": str(e)}, groupName)
#         # thread_pool.submit(send_response_to_socket_async, {"Message": str(e)}, groupName)
#         # call_send_response_to_socket({"Message": str(e)}, groupName)
        
#         # await channel_layer.group_send(
#         #     groupName,
#         #     {'type': 'send_response', 'response': json.dumps({"Message": e})}
#         # )

# @require_http_methods(["POST"])
# @csrf_exempt
# async def generateUsingTogether2(request):
#     data = json.loads(request.body.decode('utf-8'))
#     prompt = data.get('prompt')
#     groupName = data.get('groupName')
#     model = data.get('model')
#     modelString = data.get('modelString')
#     # send_response_to_socket({"Message": model + " Start"}, groupName)
#     try:
#         print(timezone.now())
#         stream = togetherClient.chat.completions.create(
#             model=modelString,
#             messages=[{"role": "user", "content": prompt}],
#             stream=True,
#         )
#         print(timezone.now())
#         for chunk in stream:
#             data = {
#                 "Model": model,
#                 "Text": chunk.choices[0].delta.content or "",
#                 "Time": str(timezone.now())
#             }
#             # await send_response_to_socket(data, groupName)
#             await send_response_to_socket({"Text": chunk.choices[0].delta.content or ""}, groupName)
#             # await channel_layer.group_send(
#             #     groupName,
#             #     {'type': 'send_response', 'response': json.dumps(data)}
#             # )
#             # print(chunk.choices[0].delta.content or "", end="", flush=True)
#         return JsonResponse({'data': "All data fetched successfully"})
#     except Exception as e:
#         send_response_to_socket({"Message": str(e)}, groupName)
#         # await channel_layer.group_send(
#         #     groupName,
#         #     {'type': 'send_response', 'response': json.dumps({"Message": e})}
#         # )



# @require_http_methods(["POST"])
# @csrf_exempt
# async def generateUsingGemini2(request):
#     data = json.loads(request.body.decode('utf-8'))
#     prompt = data.get('prompt')
#     groupName = data.get('groupName')
#     myModel = data.get('model')
#     modelString = data.get('modelString')
#     # print("Value is ---> ", prompt, groupName, myModel, modelString)
    
#     try:
#         print(timezone.now())
#         model = genai.GenerativeModel(modelString)
#         stream = model.generate_content(prompt, stream=True)
#         print(timezone.now())

#         for chunk in stream:
#             # print("chunk is ---> ", chunk)
#             data = {
#                 "Model": myModel,
#                 "Text": chunk.text or "",
#                 "Time": str(timezone.now())
#             }
#             # await send_response_to_socket(data, groupName)
#             await send_response_to_socket({"Text": chunk.text or ""}, groupName)
#         return JsonResponse({'data': "All data fetched successfully"})
#     except Exception as e:
#         print("Error is ----> ", e)
#         await send_response_to_socket({"Message": str(e)}, groupName)
#         return JsonResponse({'data': "No data fetch"})
#         # current_time_utc = timezone.now()

#         # # Convert the time to the 'Asia/Kolkata' time zone
#         # current_time_kolkata = current_time_utc.astimezone(timezone.get_current_timezone())

#         # print(current_time_kolkata)
#         # print(chunk.text)
#         # print("_"*80)

#     # try:
#     #     response.text
#     # except Exception as e:
#     #     print(f'{type(e).__name__}: {e}')

#     # # print("Res --------------------------------------------> ", res)

#     # # return res
#     # # return JsonResponse({'data': "All data fetched successfully"})


# ## Main Function
# # def generateUsingGemini(prompt):
# #     print(prompt)
# #     model = genai.GenerativeModel('gemini-pro')
# #     response = model.generate_content(f'{prompt}')
# #     # for candidate in response.candidates:
# #     #         return [part.text for part in candidate.content.parts]
# #     res = response.candidates[0].content.parts[0].text

# #     return res

# # async def generateUsingGemini(prompt):
# #         model = genai.GenerativeModel('gemini-pro')
# #         # response = model.generate_content(f'{prompt}', stream=True)
# #         response = model.generate_content(f'{prompt}')
# #         res = response.candidates[0].content.parts[0].text
# #         # for chunk in response:
# #         #      yield chunk.text
# #         #     # print(chunk.text)
# #         #     # print("_"*80)

# #         # print("Res --------------------------------------------> ", res)

# #         return res

# def generateUsingGemini(prompt, modelString, myModel, groupName):
#     print()
#     print(myModel, timezone.now())
#     # send_response_to_socket({"Message": myModel + " Start"}, groupName)
#     try:
#         model = genai.GenerativeModel(modelString)
#         stream = model.generate_content(prompt, stream=True)

#         # print(myModel, timezone.now())

#         for chunk in stream:
#             print("Google Data is --> ", chunk.text)
#             data = {
#                 "Model": myModel,
#                 "Text": chunk.text or "",
#                 "Time": str(timezone.now())
#             }
#             send_response_to_socket(data, groupName)
#             # thread_pool.submit(send_response_to_socket_async, data, groupName)
#         # print()
#         print("*****************************************", myModel, timezone.now())
#             # call_send_response_to_socket(data, groupName)

#             # await channel_layer.group_send(
#             #     groupName,
#             #     {'type': 'send_response', 'response': json.dumps(data)}
#             # )
            
#             # print({"Model": "Google", "Data": chunk.text or ""}, end="", flush=True)
#             # print(chunk.text or "", end="", flush=True)
#     except Exception as e:
#         send_response_to_socket({"Message": str(e)}, groupName)
#         # thread_pool.submit(send_response_to_socket_async, {"Message": str(e)}, groupName)
#         # call_send_response_to_socket({"Message": str(e)}, groupName)
#         # await channel_layer.group_send(
#         #     groupName,
#         #     {'type': 'send_response', 'response': json.dumps({"Message": e})}
#         # )


# def generateFromImageUsingGemini(prompt,img):
    
#     print(prompt,img)
#     # Convert the uploaded image to a PIL Image object
#     img_pil = Image.open(img)
#     print(img_pil)
#     model = genai.GenerativeModel('gemini-pro-vision')
#     response = model.generate_content([f'{prompt}',img_pil])
#     print(response)
#     print(response.text)
    

#     return response.text


# async def generateUsingTogether(prompt, model_string):
#     # asyncio.sleep(20)
#     # print("Prompt is ------->", prompt)
#     print("model_string is ------------------------>", model_string)
#     reqUrl = 'https://api.together.xyz/v1/chat/completions'
#     reqHeaders = {
#         # "accept": "application/json",
#         "accept": "text/event-stream",
#         # "content-type": "application/json",
#         "Authorization": f"Bearer {LLama_API_KEY}"
#     }

#     reqBody = {
#         "model": model_string,
#         "messages": [
#             {
#                 "role": "user",
#                 "content": f"{prompt}",
#             }
#         ],
#         "stream": True,
#         "temperature": 0.7,
#         "top_p": 0.7,
#         "top_k": 50,
#         "repetition_penalty": 1,
#         "stop": [
#             "[/INST]",
#             "</s>"
#         ],
#         "repetitive_penalty": 1,
#         "update_at": "2024-02-24T09:19:02.236Z"
#     } 
#     # async with httpx.AsyncClient() as client:
#     # s = requests.Session()
#     print(timezone.now())
#     # res = s.post(endpoint, json={
#     request = requests.post(reqUrl, stream=True, headers=reqHeaders, json=reqBody)

#     print(timezone.now())

#     client = sseclient.SSEClient(request)
#     for event in client.events():
#         if event.data != '[Done]':
#             print(json.loads(event.data)['choices'][0]['text'], end="", flust=True)

#     print(timezone.now())
#     # print("Value is ---> ", res)

#     # channel_layer = get_channel_layer()
#     # # response = res.json()
#     # # data = response['choices'][0]["message"]["content"]

#     # # await channel_layer.group_send(
#     # #         'user_group',
#     # #         # {'type': 'send_response', 'response': json.dumps({"text": chunk.text})}
#     # #         {'type': 'send_response', 'response': json.dumps(data)}
#     # #     )
#     # # print(timezone.now())

#     # for line in res.iter_lines():
#     #     if line:
#     #         decoded_line = line.decode('utf-8')
#     #         json_string = decoded_line.split("data: ")[-1]
#     #         try:
#     #             data = json.loads(json_string)
#     #             new_data = data["choices"][0]["text"]
                

#     #             await channel_layer.group_send(
#     #                 'user_group',
#     #                 # {'type': 'send_response', 'response': json.dumps({"text": chunk.text})}
#     #                 {'type': 'send_response', 'response': json.dumps(new_data)}
#     #             )
#     #         except json.JSONDecodeError:
#     #             # channel_layer = get_channel_layer()

#     #             await channel_layer.group_send(
#     #                 'user_group',
#     #                 # {'type': 'send_response', 'response': json.dumps({"text": chunk.text})}
#     #                 {'type': 'send_response', 'response': json.dumps("Data Finished")}
#     #             )




#             # print("Line is ----> ", data['choices'][0]["text"])
#             # chunk_str = chunk.decode('utf-8')
            
#             # # text = json.loads(chunk_str)['text']

#             # # print("Response is ---> ", text)
#             # channel_layer = get_channel_layer()

#             # await channel_layer.group_send(
#             #     'user_group',
#             #     # {'type': 'send_response', 'response': json.dumps({"text": chunk.text})}
#             #     {'type': 'send_response', 'response': json.dumps(chunk_str)}
#             # )

#     # Parse the JSON response
#     # print("Res is ---> ", res)
#     # response = res.json()
#     # print("Respones is ---> ", response)
#     # print("Response is -------------------------------------------> ", response)
#     # return response['choices'][0]["message"]["content"]
#     # return response

     
     
# # # Main Function
# # def generateUsingTogether(prompt, model_string):
# #     print("Prompt is --->",prompt)
# #     print("model_string is --->",model_string)
# #     endpoint = 'https://api.together.xyz/v1/chat/completions'
# #     headers = {
# #     "accept": "application/json",
# #     "content-type": "application/json",
# #     "Authorization": f"Bearer {LLama_API_KEY}"
# #     }

# #     res =  requests.post(endpoint, json={
# #     "model": model_string,
# #     # "prompt": f'''[INST]{prompt} [/INST]''',
# #     "messages":[

# #     {
# #     "role": "user",
# #     "content": f'''{prompt} ''',
# #     }
# #     ],
# #     "temperature": 0.7,
# #     "top_p": 0.7,
# #     "top_k": 50,
# #     "repetition_penalty": 1,
# #     "stop": [
# #     "[/INST]",
# #     "</s>"
# #     ],
# #     "repetitive_penalty": 1,
# #     "update_at": "2024-02-24T09:19:02.236Z"
# #     }, headers=headers)

# #     # Parse the JSON response
# #     # print(res.text,model_string)
# #     # print(res.text['choices'][0]["message"]["content"])
# #     response = res.json()

# #     return response['choices'][0]["message"]["content"]



# # async def generateUsingTogether(prompt, model_string):
# #     # Define constants
# #     endpoint = 'https://api.together.xyz/v1/chat/completions'
# #     headers = {
# #         "accept": "application/json",
# #         "content-type": "application/json",
# #         "Authorization": f"Bearer {LLama_API_KEY}"
# #     }
# #     timeout = 45

# #     async with httpx.AsyncClient() as client:
# #         # Make the POST request
# #         try:
# #             res = await client.post(
# #                 endpoint,
# #                 json={
# #                     "model": model_string,
# #                     "messages": [
# #                         {"role": "user", "content": f"{prompt}"}
# #                     ],
# #                     "temperature": 0.7,
# #                     "top_p": 0.7,
# #                     "top_k": 50,
# #                     "repetition_penalty": 1,
# #                     "stop": ["[/INST]", "</s>"],
# #                     "repetitive_penalty": 1,
# #                     "update_at": "2024-02-24T09:19:02.236Z"
# #                 },
# #                 headers=headers,
# #                 timeout=timeout
# #             )
# #             res.raise_for_status() 
# #             response = res.json() 
# #             return response
# #         except httpx.HTTPStatusError as exc:
# #             print(f"HTTP status error: {exc}")
# #             return None
# #         except httpx.RequestError as exc:
# #             print(f"Request error: {exc}")
# #             return None
        


# # async def generateUsingTogether(prompt, model_string):
# #     # asyncio.sleep(20)
# #     # print("Prompt is ------->", prompt)
# #     print("model_string is ------------------------>", model_string)
# #     endpoint = 'https://api.together.xyz/v1/chat/completions'
# #     headers = {
# #         "accept": "application/json",
# #         "content-type": "application/json",
# #         "Authorization": f"Bearer {LLama_API_KEY}"
# #     }

# #     async with httpx.AsyncClient() as client:
# #         res = await client.post(endpoint, json={
# #             "model": model_string,
# #             "messages": [
# #                 {
# #                     "role": "user",
# #                     "content": f"{prompt}",
# #                 }
# #             ],
# #             "temperature": 0.7,
# #             "top_p": 0.7,
# #             "top_k": 50,
# #             "repetition_penalty": 1,
# #             "stop": [
# #                 "[/INST]",
# #                 "</s>"
# #             ],
# #             "repetitive_penalty": 1,
# #             "update_at": "2024-02-24T09:19:02.236Z"
# #         }, headers=headers, timeout = 45)

# #     # Parse the JSON response
# #     response = res.json()
# #     print("Response is -------------------------------------------> ", response)
# #     # return response['choices'][0]["message"]["content"]
# #     return response



# def generateImageUsingTogether(prompt,model_string):

#         endpoint = 'https://api.together.xyz/inference'
#         payload = {
#         "model": model_string,
#         "prompt": prompt,
#         "n": 1, 
#         "steps": 20
#         }

#         headers = {
#         "Authorization": f"Bearer {LLama_API_KEY}",
#         "User-Agent": "multinotes.ai"
#         }

#         response = requests.post(endpoint, json=payload, headers=headers)
#         data = response.json()
#         print(data)
#         # Extract relevant image data
#         images = {
#         'choices': data['output']['choices'],
#         'result_type': data['output']['result_type']
#         }
#         return data['output']['choices'][0]






# #### *********************************** webSocket.py File ******************
# # from rest_framework.views import APIView
# from adrf.decorators import APIView
# from rest_framework.response import Response
# import httpx
# import asyncio
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync, sync_to_async
# from rest_framework.permissions import IsAuthenticated, AllowAny
# import json
# from django.http import JsonResponse
# from asgiref.sync import iscoroutinefunction, markcoroutinefunction
# from .models import LLM
# from .utils import generateUsingGemini, generateUsingTogether, generateTextByTogether, generateTextByOpenAI
# import time
# from rest_framework import status
# import multiprocessing
# import threading

# # async def fetch_data(prompt, mod_string):
# #     async with httpx.AsyncClient() as client:
# #         if mod_string == 'Gemini Pro':
# #             content = await generateUsingGemini(prompt)
# #             # pass
# #         else:
# #             # content =  await generateUsingTogether(prompt, mod_string)
# #             content =  await testTogether(prompt, mod_string)
# #         return {'data': "Task completed"}

# # async def fetch_data(prompt, mod_string):
# #     if mod_string == 'Gemini Pro':
# #         await generateUsingGemini(prompt)
# #     else:
# #         await testTogether(prompt, mod_string)
# #     return {'data': "Task completed"}  

# def thread_target(task_name):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(task_name) 


# class TextGenerationAPIView(APIView):

#     def post(self, request):
#         # start_time = time.time() 
#         groupName = request.data.get("groupName")
#         models = request.data.get("models", [])
#         prompt = request.data.get("prompt")
#         category = request.data.get("category")

#         # prompt = "what is the future socope of django framework?"
#         # models = ["Gemini Pro","Llama 2","Mistral","Gemma Instruct", "GPT-4"]
#         # models = ["Gemini Pro"]
#         # category = 1

#         tasks = []
#         processes = []
#         for model in models:
#             try:
#                 llm_instance = LLM.objects.get(name=model)
#                 # llm_instance = await sync_to_async(LLM.objects.get)(name=model)
#                 model_string = llm_instance.model_string
#             except LLM.DoesNotExist:
#                 return Response({
#                     'message': f'Model "{model}" not found.',
#                 }, status=status.HTTP_400_BAD_REQUEST)
            
#             if model == "Gemini Pro":
#                 # task = asyncio.create_task(generateUsingGemini(prompt, model_string, model, groupName))
#                 # task = generateUsingGemini(prompt, model_string, model, groupName)
#                 process = threading.Thread(target=generateUsingGemini, args=(prompt, model_string, model, groupName))
#                 processes.append(process)
#                 process.start()

#             # elif model == "GPT-4":
#             #     # task = asyncio.create_task(generateTextByOpenAI(prompt, model_string, model, groupName))
#             #     task = generateTextByOpenAI(prompt, model_string, model, groupName)
#             #     # process = threading.Thread(target=generateTextByOpenAI, args=(prompt, model_string, model, groupName))
#             #     # processes.append(process)
#             #     # process.start()

#             elif model in ['Llama 2', 'Mistral', 'Gemma Instruct']:
#                 # task = asyncio.create_task(generateTextByTogether(prompt, model_string, model, groupName))
#                 # task = generateTextByTogether(prompt, model_string, model, groupName)
#                 process = threading.Thread(target=generateTextByTogether, args=(prompt, model_string, model, groupName))
#                 processes.append(process)
#                 process.start()

#             else:
#                 return Response({
#                     'message': f'Invalid model: {model}',
#                 }, status=status.HTTP_400_BAD_REQUEST)
            
#             # tasks.append(task)

#         # threads = []
#         # for task_name in tasks:
#         #     thread = threading.Thread(target=thread_target, args=(task_name,))
#         #     thread.start()
#         #     threads.append(thread)

#         # for thread in threads:
#         #     thread.join()

#         # for task in tasks:
#         #     task.start()
        
#         for process in processes:
#             process.join()
        
            
#         # process1.start()

#         # process1.join()
        

#         # await asyncio.gather(*tasks, return_exceptions=True)
#         # await asyncio.gather(*tasks)
#         return Response({"message": "All responses sent to WebSocket clients"}, status=status.HTTP_200_OK)
    



# # async def fetch_data(prompt, mod_string):
# #     async with httpx.AsyncClient() as client:
# #         if mod_string == 'Gemini Pro':
# #             content = await generateUsingGemini(prompt)
# #         else:
# #             content =  await generateUsingTogether(prompt, mod_string)
# #         return {'data': content}
    

# # class TextGenerationAPIView(APIView):
# #     permission_classes = [AllowAny]

# #     async def post(self, request):
# #         start_time = time.time() 
# #         prompt = "what is the future socope of django framework?"
# #         # models = ["Gemini Pro","Llama 2","mistralai","Gemma Instruct"]
# #         models = ["Gemini Pro"]
# #         category = 1

# #         tasks = []
# #         for model in models:
# #             try:
# #                 llm_instance = await sync_to_async(LLM.objects.get)(name=model)
# #                 model_string = llm_instance.model_string
# #             except LLM.DoesNotExist:
# #                 return Response({
# #                     'status': 400,
# #                     'message': f'Model "{model}" not found.',
# #                 })
            
# #             if model == "Gemini Pro":
# #                 task = fetch_data(prompt, model)
            
# #             elif model in ['Llama 2','mistralai','Gemma Instruct']:
# #                 task = fetch_data(prompt, model_string)

# #             else:
# #                 return Response({
# #                     'status': 400,
# #                     'message': f'Invalid model: {model}',
# #                 })
            
# #             tasks.append(task)
                
# #         channel_layer = get_channel_layer()
# #         for task in asyncio.as_completed(tasks):
# #             response = await task
# #             await channel_layer.group_send(
# #                 'user_group',
# #                 {'type': 'send_response', 'response': json.dumps(response)}
# #             )
# #             time_taken = time.time() - start_time
# #             print("Time is ---> ", time_taken)
# #         return Response({"message": "All responses sent to WebSocket clients"})





    










# # async def fetch_data(url, data):
# #     async with httpx.AsyncClient() as client:
# #         # print("Value is ---> ", data['payload'])
# #         # response = await client.post(url, data.data, data.header)
# #         # return response.json()
# #         response = {
# #             'message': 'success'
# #         }
# #         return response
    

# # class TextGenerationAPIView(APIView):
# #     permission_classes = [AllowAny]

# #     async def post(self, request):
# #         # Send requests to all four APIs concurrently and receive responses
# #         data = {
# #             'payload': 'success',
# #             'header': 'header'
# #         }
# #         tasks = [
# #             fetch_data('url_to_gemini_pro_api', data),
# #             fetch_data('url_to_llama_2_api', data),
# #             fetch_data('url_to_mistralai_api', data),
# #             fetch_data('url_to_gemma_instruct_api', data),
# #         ]

# #         # Wait for responses and send each response to connected WebSocket clients
# #         channel_layer = get_channel_layer()
# #         for task in asyncio.as_completed(tasks):
# #             response = await task
# #             await channel_layer.group_send(
# #                 'user_group',
# #                 {'type': 'send_response', 'response': json.dumps(response)}
# #             )

# #         return Response({"message": "All responses sent to WebSocket clients"})
























# # async def fetch_data(url, data, header):
# #     async with httpx.AsyncClient() as client:
# #         response = await client.post(url, data, header)
# #         return response.json()
    
# # # async def fetch_data(url, method='POST', data=None):
# # #     async with httpx.AsyncClient() as client:
# # #         response = await client.request(method, url, data=data)
# # #         return response.json()



# # class TextGenerationAPIView(APIView):
# #     # async_capable = True
# #     # sync_capable = False
# #     permission_classes = [AllowAny]

# #     # def __init__(self):
# #     #     if iscoroutinefunction(self):
# #     #         markcoroutinefunction(self)

# #     async def post(self, request):
# #         # Send requests to all four APIs concurrently and receive responses
# #         tasks = [
# #             fetch_data('url_to_gemini_pro_api', method='POST', data=None),
# #             fetch_data('url_to_llama_2_api', method='POST', data=None),
# #             fetch_data('url_to_mistralai_api', method='POST', data=None),
# #             fetch_data('url_to_gemma_instruct_api', method='POST', data=None),
# #         ]

# #         # Wait for responses and send each response to connected WebSocket clients
# #         channel_layer = get_channel_layer()
# #         for task in asyncio.as_completed(tasks):
# #             response = await task
# #             await async_to_sync(channel_layer.group_send)(
# #                 'text_generation_group',
# #                 {'type': 'send_response', 'response': 'my name anil rana'}
# #             )


# #         # channel_layer = get_channel_layer()
# #         # response = {
# #         #     'name': 'anil',
# #         #     'village': 'rahra',
# #         #     'age': 35
# #         # }
# #         # await channel_layer.group_send(
# #         #         'user_group',
# #         #         {'type': 'send_response', 'response': json.dumps(response)}
# #         # )

# #         return Response({"message": "All responses sent to WebSocket clients"})
# #         # return JsonResponse({'message' : 'All responses sent to WebSocket clients'})




# # async def fetch_data(prompt, mod_string):
# #     async with httpx.AsyncClient() as client:
# #         if mod_string == 'Gemini Pro':
# #             content = generateUsingGemini(prompt)
# #         else:
# #             content = generateUsingTogether(prompt, mod_string)
# #         return {'data': content}

# # class TextGenerationAPIView(APIView):
# #     permission_classes = [AllowAny]

# #     async def post(self, request):
# #         prompt = "who is prime minister of indai ?"
# #         models = ["Gemini Pro","Llama 2","mistralai","Gemma Instruct"]
# #         category = 1

# #         tasks = []
# #         for model in models:
# #             try:
# #                 llm_instance = await sync_to_async(LLM.objects.get)(name=model)
# #                 model_string = llm_instance.model_string
# #             except LLM.DoesNotExist:
# #                 return Response({
# #                     'status': 400,
# #                     'message': f'Model "{model}" not found.',
# #                 })
            
# #             if model == "Gemini Pro":
# #                 task = fetch_data(prompt, model)
            
# #             elif model in ['Llama 2','mistralai','Gemma Instruct']:
# #                 task = fetch_data(prompt, model_string)

# #             else:
# #                 return Response({
# #                     'status': 400,
# #                     'message': f'Invalid model: {model}',
# #                 })
            
# #             tasks.append(task)
                
# #         channel_layer = get_channel_layer()
# #         for task in asyncio.as_completed(tasks):
# #             response = await task
# #             await channel_layer.group_send(
# #                 'user_group',
# #                 {'type': 'send_response', 'response': json.dumps(response)}
# #             )

# #         return Response({"message": "All responses sent to WebSocket clients"})








# # async def fetch_data(prompt, mod_string):
# #     async with httpx.AsyncClient() as client:
# #         print("type is ---> ", type(mod_string))
# #         print("stromg is ---> ", mod_string)
# #         if mod_string == 'Gemini Pro':
# #             # print("Anil 1 **********************")
# #             content = generateUsingGemini(prompt)
# #             print("gemini content  -----> ", content)

# #             channel_layer = get_channel_layer()
# #             await channel_layer.group_send(
# #                 "user_group",
# #                 {
# #                     'type': 'send_response',
# #                     'response': json.dumps(content),       
# #                 }
# #             )

# #             # send_to_group(content)
# #             # generated_content.append({'llm': model, 'response_text': content})
# #             # time.sleep(10)
# #             # return {'data': content}
# #         else:
# #             # print("Anil 2 ***************************")
# #             content = generateUsingTogether(prompt, mod_string)
# #             print("Together content is ---->", content)

# #             channel_layer = get_channel_layer()
# #             await channel_layer.group_send(
# #                 "user_group",
# #                 {
# #                     'type': 'send_response',
# #                     'response': json.dumps(content),       
# #                 }
# #             )


# #             # send_to_group(content)
# #             # generated_content.append({'llm': model, 'response_text': content})
# #         return {'data': content}
    

# # async def send_to_group(message):
# #         channel_layer = get_channel_layer()
# #         await channel_layer.group_send(
# #             "user_group",
# #             {
# #                 'type': 'send_response',  # The name of the consumer method to call
# #                 'response': json.dumps(message),       # The message to send
# #             }
# #         )


# # class TextGenerationAPIView(APIView):
# #     permission_classes = [AllowAny]

# #     async def post(self, request):
# #         # Send requests to all four APIs concurrently and receive responses
# #         prompt = "who is prime minister of indai ?"
# #         models = ["Gemini Pro","Llama 2","mistralai","Gemma Instruct"]
# #         category = 1

# #         tasks = []
# #         for model in models:
# #             try:
# #                 # print("model is ---> ", prompt_model)
# #                 # llm_instance = LLM.objects.get(name=model)  # Get the LLM instance by name
# #                 llm_instance = await sync_to_async(LLM.objects.get)(name=model)
# #                 model_string = llm_instance.model_string
# #                 # print('llm_instance name is  -----------------------> ', model_string)
# #             except LLM.DoesNotExist:
# #                 return Response({
# #                     'status': 400,
# #                     'message': f'Model "{model}" not found.',
# #                 })
            
# #             if model == "Gemini Pro":
# #                 # response = await fetch_data(prompt, model)
# #                 # task = await fetch_data(prompt, model)
# #                 task = fetch_data(prompt, model)
            
# #             elif model in ['Llama 2','mistralai','Gemma Instruct']:
# #                 # response = await fetch_data(prompt, model_string)
# #                 # task = await fetch_data(prompt, model_string)
# #                 task = fetch_data(prompt, model_string)

# #             else:
# #                 return Response({
# #                     'status': 400,
# #                     'message': f'Invalid model: {model}',
# #                 })
                

# #             # tasks.append(task)

                
# #         # sample_data = {
# #         #     'payload': 'success',
# #         #     'header': 'header'
# #         # }   

# #         # tasks = [
# #         #     fetch_data('url_to_gemini_pro_api', data),
# #         #     fetch_data('url_to_llama_2_api', data),
# #         #     fetch_data('url_to_mistralai_api', data),
# #         #     fetch_data('url_to_gemma_instruct_api', data),
# #         # ]

# #         # # Wait for responses and send each response to connected WebSocket clients
# #         # channel_layer = get_channel_layer()
# #         # for task in asyncio.as_completed(tasks):
# #         #     response = await task
# #         #     # print("############## Websocker calling ########", response)
# #         #     await channel_layer.group_send(
# #         #         'user_group',
# #         #         {'type': 'send_response', 'response': json.dumps(response)}
# #         #         # {'type': 'send_response', 'response': json.dumps(sample_data)}
# #         #         # {'type': 'send_response', 'response': response}
# #         #     )

# #         # # Send the response to the WebSocket group
# #         # print("response is ---> ", response)
# #         # await self.send_to_group("user_group", json.dumps(response))

# #         return Response({"message": "Responses sent to WebSocket clients"})





# def generator_1(param, queue):
#     print("1 ---> ", timezone.now())
#     for i in range(param):
#         queue.put(f"data: Response from function 1 with param\n\n")
#         time.sleep(1)
#     queue.put("DONE")

# def generator_2(param, queue):
#     print("2 ---> ", timezone.now())
#     for i in range(20):
#         queue.put(f"data: Response from function 2 with param\n\n")
#         # time.sleep(1)
#     queue.put("DONE")
    
# def generator_3(param, queue):
#     print("3 ---> ", timezone.now())

#     for i in range(param):
#         queue.put(f"data: Response from function 3 with param\n\n")
#         # time.sleep(1)
#     queue.put("DONE")

# def generator_4(param, queue):
#     print("4 ---> ", timezone.now())

#     for i in range(20):
#         queue.put(f"data: Response from function 4 with param\n\n")
#         # time.sleep(1)
#     queue.put("DONE")


# # # Combine the generators into a single asynchronous generator
# def combine_generators(param_1):

#     queue_1 = Queue()
#     queue_2 = Queue()
#     queue_3 = Queue()
#     queue_4 = Queue()
    
#     # Start generator_1 in a separate thread
#     thread_1 = Thread(target=generator_1, args=(param_1, queue_1))
#     thread_1.start()
    
#     # Start generator_2 in a separate thread
#     thread_2 = Thread(target=generator_2, args=(param_1, queue_2))
#     thread_2.start()
    
#     # Start generator_1 in a separate thread
#     thread_3 = Thread(target=generator_3, args=(param_1, queue_3))
#     thread_3.start()
    
#     # Start generator_2 in a separate thread
#     thread_4 = Thread(target=generator_4, args=(param_1, queue_4))
#     thread_4.start()
    
    
#     # Yield data from both queues
#     while True:
#         data_1 = queue_1.get()
#         if data_1 == "DONE":
#             break
#         yield data_1
        
#     while True:
#         data_2 = queue_2.get()
#         if data_2 == "DONE":
#             break
#         yield data_2

#     while True:
#         data_3 = queue_3.get()
#         if data_3 == "DONE":
#             break
#         yield data_3
        
#     while True:
#         data_4 = queue_4.get()
#         if data_4 == "DONE":
#             break
#         yield data_4

    

# class TextEventStream(APIView):
#     permission_classes = [AllowAny]

#     # Define your view
#     def get(self, request):

#         models = ["Llama 2","Mistral","Gemma Instruct","Gemini Pro"]
#         prompt = "Tell me about President of India in 50000 Words."

#         response = StreamingHttpResponse(combine_generators(15))
#         # Set any additional headers if needed
#         response['Content-Type'] = 'text/event-stream'
#         response['Cache-Control'] = 'no-cache'
#         return response


# # messages.py
# MESSAGES = {
#     'transaction_not_found': "Transaction Not Found",
#     'transaction_delete_success': "Transaction Deleted Successfully",
#     'validation_error': "There is a validation error."
# }


# from rest_framework import status
# from rest_framework.response import Response
# from .serializers import UpdateTransactionSerializer
# from .models import Transaction
# from .messages import MESSAGES  # Import the centralized messages

# class DeleteTransaction(APIView):
    
#     def patch(self, request, pk=None):
#         try:
#             transaction = Transaction.objects.get(pk=pk, is_delete=False)
#         except Transaction.DoesNotExist:
#             return Response({"message": MESSAGES['transaction_not_found'], "data": {}}, status=status.HTTP_404_NOT_FOUND)
        
#         serializer = UpdateTransactionSerializer(transaction, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": MESSAGES['transaction_delete_success'], "data": serializer.data}, status=status.HTTP_200_OK)
#         else:
#             return Response({"message": MESSAGES['validation_error'], "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# # migration file: <your_app>/migrations/000Y_populate_random_digit.py
# import random
# from django.db import migrations

# def generate_random_digits(apps, schema_editor):
#     YourModel = apps.get_model('<your_app>', '<YourModel>')
#     for obj in YourModel.objects.all():
#         obj.random_digit = random.randint(100000, 999999)
#         obj.save()

# class Migration(migrations.Migration):

#     dependencies = [
#         ('<your_app>', '000X_add_random_digit_field'),
#     ]

#     operations = [
#         migrations.RunPython(generate_random_digits),
#     ]


# def display_file_size(file_size_in_bytes):
#     if file_size_in_bytes < 1024:
#         return f"{file_size_in_bytes} Bytes"
#     elif file_size_in_bytes < 1024 * 1024:
#         return f"{file_size_in_bytes / 1024:.2f} KB"
#     elif file_size_in_bytes < 1024 * 1024 * 1024:
#         return f"{file_size_in_bytes / (1024 * 1024):.2f} MB"
#     else:
#         return f"{file_size_in_bytes / (1024 * 1024 * 1024):.2f} GB"




# class UploadToDriveView(View):
#     def post(self, request):
#         creds_dict = {
#             "token": "your_access_token",
#             "refresh_token": "your_refresh_token",
#             "token_uri": "https://oauth2.googleapis.com/token",
#             "client_id": "your_client_id",
#             "client_secret": "your_client_secret",
#             "scopes": ["https://www.googleapis.com/auth/drive.file"],
#             "expiry": "expiry_time_here"
#         }

#         # Convert dict to Credentials object
#         creds = Credentials.from_authorized_user_info(creds_dict)

#         # Build the Google Drive service
#         service = build('drive', 'v3', credentials=creds)

#         # Create a folder in Google Drive
#         folder_metadata = {
#             'name': 'MyFolder',  # Name of the folder
#             'mimeType': 'application/vnd.google-apps.folder'
#         }
#         folder = service.files().create(body=folder_metadata, fields='id').execute()
#         folder_id = folder.get('id')

#         # Save a file in the folder
#         file = request.FILES['file']  # Get the file from the request
#         file_metadata = {
#             'name': file.name,  # Name of the file
#             'parents': [folder_id]  # Place file in the created folder
#         }

#         # Prepare the media file upload object
#         media = MediaFileUpload(file.temporary_file_path(), resumable=True)

#         # Upload the file to the folder
#         uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

#         return JsonResponse({'folder_id': folder_id, 'file_id': uploaded_file.get('id')})



# # User File Management
# class GetRootRecentShareFileView(APIView):
#     pagination_class = PageNumberPagination

#     def get(self, request):
#         paginator = self.pagination_class()
#         folder_id = request.GET.get('folderId', None)
#         user = request.user

#         # share_value = request.GET.get('shareWithMe', 'false')
#         # share_bool = share_value.lower() == "true"

#         root_files = UserContent.objects.filter(user=user, is_delete=False, folder__isnull=True)
#         # root_files = root_files.order_by('-created_at')

#         # recent_files = []
#         # if len(root_files) < 10:
#         #     limit = 10 - len(root_files)
#         #     recent_files = UserContent.objects.filter(user=user, is_delete=False).order_by('-created_at')[:limit]

#         recent_files = UserContent.objects.filter(user=user, is_delete=False).order_by('-created_at')[:10]

#         files = list(root_files) + list(recent_files)

#         # Use a dictionary to keep only unique items by id
#         unique_records = {record.id: record for record in files}.values()

#         # Convert back to a list if needed
#         unique_files = list(unique_records)

#         # print("Root file ----> ", root_files)
#         # print("recent_files ----> ", recent_files)
#         # print("unique_files ----> ", unique_files)

#         share_files = Share.objects.filter(share_to_user=user, content_type__in=['file', 'document'], is_delete=False)

#         # print(share_files)

#         root_document = Document.objects.filter(user=user, is_delete=False, folder=None)

#         # print(root_document)

#         # page = paginator.paginate_queryset(files_serializer, request)

#         # files_serializer = ContentLibrarySerializer(page, many=True)

#         # print("share_files ---> ", share_files)

#         # Combine the querysets
#         combined_queryset = sorted(
#             list(unique_files) + list(share_files) + list(root_document),
#             key=lambda instance: instance.created_at,
#             reverse=True
#         )

#         page = paginator.paginate_queryset(combined_queryset, request)
#         # root_data = ContentLibrarySerializer(share_files, many=True).data

#         # Serialize the data
#         data = []
#         for item in page:
#             if isinstance(item, UserContent):
#                 root_data = ContentLibrarySerializer(item).data
#                 root_data['isShare'] = False
#                 data.append(root_data)
#             elif isinstance(item, Share):
#                 share_data = ShareContentFileSerializer(item).data
                
#                 if share_data['content_type'] == 'file':
#                     share_data['file']['isShare'] = True
#                     data.append(share_data['file'])
#                 else:
#                     share_data['document']['isShare'] = True
#                     data.append(share_data['document'])
#                 # share_data['isShare'] = True
#                 # data.append(share_data)
#             elif isinstance(item, Document):
#                 share_data = DocumentContentSerializer(item).data
#                 share_data['isShare'] = False
#                 data.append(share_data)

#         total_pages = paginator.page.paginator.num_pages

#         response_data = {
#             'total_pages': total_pages,
#             'results': data
#         }

#         return paginator.get_paginated_response(response_data)


############## Coupon Management *********************
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Coupon(models.Model):
    COUPON_TYPES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.code

    def is_valid(self):
        """Check if the coupon is currently valid."""
        now = timezone.now()
        if self.start_date <= now <= self.end_date and self.active:
            return True
        return False
    
    
class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, null=True, blank=True)
    used_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coupon', 'user', 'order_id')

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code} - {self.order_id}"
    

def apply_coupon(coupon_code, user, order_total):
    try:
        coupon = Coupon.objects.get(code=coupon_code)
        if not coupon.is_valid():
            return {"success": False, "message": "Coupon is not valid"}

        # Check if user has exceeded usage limit for this coupon
        if CouponUsage.objects.filter(coupon=coupon, user=user).count() >= coupon.usage_limit_per_user:
            return {"success": False, "message": "Coupon usage limit exceeded for this user"}

        # Check if the total usage of this coupon has exceeded its limit
        if CouponUsage.objects.filter(coupon=coupon).count() >= coupon.usage_limit:
            return {"success": False, "message": "Coupon usage limit exceeded"}

        # Check if order total meets minimum requirement
        if coupon.min_order_amount and order_total < coupon.min_order_amount:
            return {"success": False, "message": f"Minimum order amount to use this coupon is {coupon.min_order_amount}"}

        # Calculate discount
        if coupon.coupon_type == 'percentage':
            discount = (order_total * coupon.discount_value / 100)
            if coupon.max_discount_amount and discount > coupon.max_discount_amount:
                discount = coupon.max_discount_amount
        else:
            discount = coupon.discount_value

        return {"success": True, "discount": discount, "message": "Coupon applied successfully"}
    
    except Coupon.DoesNotExist:
        return {"success": False, "message": "Invalid coupon code"}
    


def download_video(url, output_path, userId):
    ydl_opts = {
        'format': 'bestaudio/best',  # This ensures you're getting the best available audio.
        # 'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),  # Save as the original audio format.
        'outtmpl': os.path.join(output_path, f"user_file_{userId}"),  # Save as the original audio format.

        'postprocessors': [{  # Post-process audio to convert to mp3.
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # Convert to mp3.
            'preferredquality': '192',  # Audio quality setting.
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        # info = ydl.extract_info(url, download=True)
        # userId = 101
        # file_path = os.path.join(output_path, f"{info['title']}.mp3")
        # audio_file = os.path.join(output_path, ydl_opts['outtmpl'])
        # print("Value is ----> ", f"{info['title']}.mp3" )
        # value = f"{info['title']}.mp3"

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
    
def convert_audio_into_text(audio_file_path):
    output_path = settings.BASE_DIR
    # return Response(f"Audio downloaded at: {audio_file}")
    url = "https://api.openai.com/v1/audio/transcriptions"

    # audio_file_path = output_path/f"user_file_1.mp3"

    audio = AudioSegment.from_mp3(audio_file_path)

    # Get the total length of the audio file in milliseconds
    audio_length_ms = len(audio)

    # print("Audio Length in minute ---->", audio_length_ms/60000)

    # Create output directory if it doesn't exist
    # os.makedirs(output_dir, exist_ok=True)

    # Split the audio file into chunks and export each chunk
    text = ""
    if audio_length_ms > 60000*20:
        for i in range(0, audio_length_ms, 1200000):
            start_time = i
            end_time = min(i + 1200000, audio_length_ms)  # Make sure the last chunk isn't too long
            # print("start_time is ----> ", start_time)
            # print("end_time is ----> ", end_time)
            chunk = audio[start_time:end_time]
            
            # Export the chunk as an MP3 file
            chunk_name = f"chunk_{i // 1200000 + 1}.mp3"
            # chunk_path = os.path.join(output_dir, chunk_name)
            chunk_path = output_path/chunk_name

            # print("Chunk Path is ----> ", chunk_path)
            chunk.export(chunk_path, format="mp3")
            # print(f"Exported {chunk_path}")

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
                # print("Response is ----> ", new_text)

                # print("Response 2 is ----> ", response.__dir__())
                if i == 0:
                    text += new_text
                else:
                    text += f" {new_text}"

        os.remove(audio_file_path)
        # content.url_output = text
        # content.save()
        # return Response(f"Audio downloaded at: {audio_file_path}")
        # return Response({"data": text}, status=status.HTTP_200_OK)

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

            # content.url_output = text
            # content.save()

        # return Response(f"Audio downloaded at: {audio_file_path}")
    return text
    

class DownloadVideoView(APIView):
    def post(self, request, pk=None):

        video_url = request.data.get('url')
        workflows = request.data.get('workflow')
        uploadFile = request.data.get('uploadFile')

        data = request.data.copy()
        data['user'] = request.user.id
        # Example usage:
        # video_url = 'https://www.youtube.com/watch?v=cC8MjoYGedk'

        if 'list' in video_url:
            return Response({"message": "Model can't process list of video. Please provide single video link."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AiProcessSerializer(data=data, many=False)

        if serializer.is_valid():
            content = serializer.save()
            output_path = settings.BASE_DIR

            if uploadFile:
                # Download the file from S3 bucket

                # Check if the local directory exists, if not, create it

                local_path = output_path/f"user_file_{request.user.id}.mp4"
                # local_path = output_path/"1729237187-spacex.mp4"
                # local_dir = os.path.dirname(local_path)
                # if not os.path.exists(local_dir):
                #     os.makedirs(local_dir)
                
                # Download the file
                result = download_s3_file(video_url, local_path)
                if result:
                    print(f"File downloaded successfully from S3 to {local_path}")

                    input_video = local_path
                    output_audio = output_path/f"user_audio_file_{request.user.id}.mp3"
                    result = convert_mp4_to_mp3(input_video, output_audio)

                    os.remove(local_path)

                    if result:
                        text = convert_audio_into_text(output_audio)

                    # return Response({"message": f"File downloaded successfully from S3 to {local_path}"}, status=status.HTTP_200_OK)
                else:
                    print("There is an error in file downloading.")
                    return Response({"message": f"File not downloaded"}, status=status.HTTP_400_BAD_REQUEST)

            else:
                # userID = 101
                # print("Path is ----> ", output_path)

                try:
                    audio_file_path = download_video(video_url, output_path, request.user.id)
                except yt_dlp.utils.DownloadError as e:
                    # return Response({"message": e.msg.split(": ")[-1]})
                    return Response({"message": e.msg})
                except Exception as e:
                    return Response({"message": "error occured"})
                
                text = convert_audio_into_text(audio_file_path)
                
                # print(f"Audio saved to {audio_file}")

                # os.remove(audio_file)

                ###########################################3
                # # return Response(f"Audio downloaded at: {audio_file}")
                # url = "https://api.openai.com/v1/audio/transcriptions"

                # # audio_file_path = output_path/f"user_file_1.mp3"

                # audio = AudioSegment.from_mp3(audio_file_path)
        
                # # Get the total length of the audio file in milliseconds
                # audio_length_ms = len(audio)

                # # print("Audio Length in minute ---->", audio_length_ms/60000)

                # # Create output directory if it doesn't exist
                # # os.makedirs(output_dir, exist_ok=True)

                # # Split the audio file into chunks and export each chunk
                # text = ""
                # if audio_length_ms > 60000*20:
                #     for i in range(0, audio_length_ms, 1200000):
                #         start_time = i
                #         end_time = min(i + 1200000, audio_length_ms)  # Make sure the last chunk isn't too long
                #         # print("start_time is ----> ", start_time)
                #         # print("end_time is ----> ", end_time)
                #         chunk = audio[start_time:end_time]
                        
                #         # Export the chunk as an MP3 file
                #         chunk_name = f"chunk_{i // 1200000 + 1}.mp3"
                #         # chunk_path = os.path.join(output_dir, chunk_name)
                #         chunk_path = output_path/chunk_name

                #         # print("Chunk Path is ----> ", chunk_path)
                #         chunk.export(chunk_path, format="mp3")
                #         # print(f"Exported {chunk_path}")

                #         with open(chunk_path, 'rb') as audio_file:
                #             # Prepare the multipart/form-data request
                #             files = {
                #                 'file': audio_file
                #             }
                            
                #             # Data for the request
                #             data = {
                #                 'model': 'whisper-1'
                #             }
                            
                #             # Headers
                #             headers = {
                #                 "Authorization": f"Bearer {OPENAI_API_KEY}",
                #             }
                            
                #             # Send the POST request
                #             response = requests.post(url, headers=headers, files=files, data=data)

                #             os.remove(chunk_path)
                #             new_text = json.loads(response.text)['text']
                #             # print("Response is ----> ", new_text)

                #             # print("Response 2 is ----> ", response.__dir__())
                #             if i == 0:
                #                 text += new_text
                #             else:
                #                 text += f" {new_text}"

                #     os.remove(audio_file_path)
                #     # content.url_output = text
                #     # content.save()
                #     # return Response(f"Audio downloaded at: {audio_file_path}")
                #     # return Response({"data": text}, status=status.HTTP_200_OK)

                # else:
                #     # audio_file_path = output_path/f"user_file_1.mp3"

                #     # Open the file in binary mode
                        
                #     with open(audio_file_path, 'rb') as audio_file:
                #         # Prepare the multipart/form-data request
                #         files = {
                #             'file': audio_file
                #         }
                        
                #         # Data for the request
                #         data = {
                #             'model': 'whisper-1'
                #         }
                        
                #         # Headers
                #         headers = {
                #             "Authorization": f"Bearer {OPENAI_API_KEY}",
                #         }
                        
                #         # Send the POST request
                #         response = requests.post(url, headers=headers, files=files, data=data)

                #         text = json.loads(response.text)['text']

                #         os.remove(audio_file_path)

                #         # content.url_output = text
                #         # content.save()

                #     # return Response(f"Audio downloaded at: {audio_file_path}")

                ######################################################33
                      
            workflows = json.loads(workflows)

            ai_text = text
            for workflow in workflows:
                print("AI text -------------------------------> ", ai_text)
                model = workflow['modelName']
                prompt = workflow['action']

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not available or not connected',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if llm_instance.source==2 and llm_instance.text:
                    ai_response = aiTogetherProcess(model_string, ai_text, prompt)
                    
                    print("Response 1 is ----> ", ai_response)
                
                elif llm_instance.source==3 and llm_instance.text:
                    ai_response = aiGeminiProcess(model_string, ai_text, prompt)
                    
                    print("Response 2 is ----> ", ai_response)
                
                elif llm_instance.source==4 and llm_instance.text:
                    ai_response = aiOpenAIProcess(model_string, ai_text, prompt)
                    
                    print("Response 3 is ----> ", ai_response)
                else:
                    return Response({'message': 'Please provide proper model for text generation.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                workflow['input'] = ai_text
                workflow['ouput'] = ai_response
                workflow['status'] = "done"

                content.workflow = json.dumps(workflows)
                content.save()
                ai_text = ai_response
            content.url_status = "done"
            content.url_output = text
            content.save()
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)      
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

########## Final ###############
def download_video(url, output_path, userId):
    ydl_opts = {
        'format': 'bestaudio/best',  # This ensures you're getting the best available audio.
        'outtmpl': os.path.join(output_path, f"user_file_{userId}"),  # Save as the original audio format.

        'postprocessors': [{  # Post-process audio to convert to mp3.
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # Convert to mp3.
            'preferredquality': '192',  # Audio quality setting.
        }]
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
    if audio_length_ms > 60000*20:
        for i in range(0, audio_length_ms, 1200000):
            start_time = i
            end_time = min(i + 1200000, audio_length_ms)  # Make sure the last chunk isn't too long
            chunk = audio[start_time:end_time]
            
            # Export the chunk as an MP3 file
            chunk_name = f"chunk_{i // 1200000 + 1}.mp3"
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
    
########################################################################
class DownloadVideoView(APIView):
    permission_classes = [IsAuthenticated, TextSubscriptionAuth]

    def post(self, request, pk=None):

        video_url = request.data.get('url')
        workflows = request.data.get('workflow')
        uploadFile = request.data.get('uploadFile')

        data = request.data.copy()
        data['user'] = request.user.id
        # Example usage:
        # video_url = 'https://www.youtube.com/watch?v=cC8MjoYGedk'

        if 'list' in video_url:
            return Response({"message": "Model can't process list of video. Please provide single video link."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AiProcessSerializer(data=data, many=False)

        if serializer.is_valid():
            content = serializer.save()
            output_path = settings.BASE_DIR

            if uploadFile:

                local_path = output_path/f"user_file_{request.user.id}.mp4"
                
                # Download the file
                result = download_s3_file(video_url, local_path)
                if result:
                    # print(f"File downloaded successfully from S3 to {local_path}")

                    input_video = local_path
                    output_audio = output_path/f"user_audio_file_{request.user.id}.mp3"
                    result = convert_mp4_to_mp3(input_video, output_audio)

                    os.remove(local_path)

                    if result:
                        text = convert_audio_into_text(output_audio, request.user)

                else:
                    # print("There is an error in file downloading.")
                    return Response({"message": f"There is an error in file downloading."}, status=status.HTTP_400_BAD_REQUEST)

            else:

                try:
                    audio_file_path = download_video(video_url, output_path, request.user.id)
                except yt_dlp.utils.DownloadError as e:
                    return Response({"message": e.msg})
                except Exception as e:
                    return Response({"message": "error occured"})
                
                text = convert_audio_into_text(audio_file_path, request.user)
                      
            workflows = json.loads(workflows)

            ai_text = text
            for workflow in workflows:
                model = workflow['modelName']
                prompt = workflow['action']

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    return Response({'message': f'Model "{model}" not available or not connected',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if llm_instance.source==2 and llm_instance.text:
                    ai_response = aiTogetherProcess(model_string, ai_text, prompt, request.user)
                    
                elif llm_instance.source==3 and llm_instance.text:
                    ai_response = aiGeminiProcess(model_string, ai_text, prompt, request.user)
                    
                elif llm_instance.source==4 and llm_instance.text:
                    ai_response = aiOpenAIProcess(model_string, ai_text, prompt, request.user)
                    
                else:
                    return Response({'message': 'Please provide proper model for text generation.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                workflow['input'] = ai_text
                workflow['ouput'] = ai_response
                workflow['status'] = "done"

                content.workflow = json.dumps(workflows)
                content.save()
                ai_text = ai_response

            content.url_status = "done"
            content.url_output = text
            content.save()
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)      
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
##############################################################################
        yt = YouTube(video_url, on_progress_callback = on_progress)
        print(yt.title)

        ys = yt.streams.get_highest_resolution()
        # output_path = settings.BASE_DIR
        # tmp_dir = output_path/f"user_file_{request.user.id}.mp4"
        ys.download(filename=f"user_file_{request.user.id}.mp4")

        input_video = settings.BASE_DIR/f"user_file_{request.user.id}.mp4"
        output_audio = settings.BASE_DIR/f"user_audio_file_{request.user.id}.mp3"
        result = convert_mp4_to_mp3(input_video, output_audio)

        # os.remove(input_video)

        # # Create YouTube object
        # yt = YouTube(video_url)
        # print("Value is ----> ", yt.__dir__())

        # # Download the highest resolution video
        # stream = yt.streaming_data.get_highest_resolution()

        # stream.download()

        # print("Download complete!")

        # return video_path
        return Response({"data": "Data fetched successfully"}, status=status.HTTP_200_OK)  
    
#################################################################
        # YouTube('https://www.youtube.com/watch?v=Czg_9C7gw0o').streams.first().download()

        # # Create a temporary directory to save the file
        # # tmp_dir = tempfile.mkdtemp()
        
        # # Initialize YouTube object from the provided URL
        # yt = YouTube(video_url)

        
        # # Get the highest resolution stream for the video
        # video_stream = yt.streams.get_highest_resolution()
        # # video_stream = yt.streams.filter(only_audio=True).first()
        # # Download video to the temp directory
        # # video_path = os.path.join(tmp_dir, f"{yt.title}.mp4")
        # # video_stream.download(output_path=tmp_dir, filename=f"{yt.title}.mp4")
        # video_stream.download()
        
        # https://github.com/JuanBindez/pytubefix/pull/209
    
        # Set Chrome options
        chrome_options = webdriver.ChromeOptions()

        # Define the path to your chromedriver
        chromedriver_path = '/home/anil/chromedriver-linux64/chromedriver'

        # Use the Service class to set up the ChromeDriver
        service = Service(executable_path=chromedriver_path)

        # Initialize the WebDriver with the service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(video_url)

        yt = YouTube(video_url)
        ys = yt.streams.get_highest_resolution()
        # ys.download()
        input_video = settings.BASE_DIR/f"user_file_{request.user.id}.mp4"
        ys.download(filename=f"user_file_{request.user.id}.mp4")

        audio_file_path = settings.BASE_DIR/f"user_audio_file_{request.user.id}.mp3"
        result = convert_mp4_to_mp3(input_video, output_audio)
        os.remove(input_video)


## Stop Celery Task.
        
# tasks.py
from celery import shared_task, current_task
import time

@shared_task(bind=True)
def long_running_task(self):
    for i in range(10):  # Simulating a long-running task
        if self.request.called_directly or self.is_revoked():
            print("Task was revoked. Exiting gracefully.")
            break
        # Simulate doing work
        print(f"Processing step {i + 1}")
        time.sleep(5)  # Sleep to simulate long processing
    return "Task completed"

# views.py
from celery import app
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

class StopTaskAPIView(APIView):
    def post(self, request, *args, **kwargs):
        task_id = request.data.get('task_id')
        
        if not task_id:
            return Response({"error": "Task ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            app.control.revoke(task_id, terminate=True)
            return Response({"message": f"Task {task_id} revoked successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# urls.py
from django.urls import path
from .views import StopTaskAPIView

urlpatterns = [
    path('api/stop-task/', StopTaskAPIView.as_view(), name='stop-task'),
]

# In some view or logic
from .tasks import long_running_task

task = long_running_task.delay()  # This returns an AsyncResult
task_id = task.id

from celery import shared_task
from celery.exceptions import Ignore
import time

@shared_task(bind=True)
def long_running_task(self):
    for i in range(10):  # Simulating a long-running task
        if self.request.called_directly or self.is_revoked():
            print("Task was revoked. Exiting gracefully.")
            self.update_state(state='REVOKED')  # Optionally set a custom state
            raise Ignore  # Exit immediately and prevent further processing
        # Simulate doing work
        print(f"Processing step {i + 1}")
        time.sleep(5)  # Sleep to simulate long processing
    return "Task completed"


@shared_task(time_limit=1800)  # Task will fail if it runs beyond 30 minutes
def aiprocess_data(userId, contentId, fileType):
    try:
        from coreapp.views import (
            convert_mp4_to_mp3, convert_audio_into_text, download_video, 
            extract_text_from_pdf, extract_text_from_excel, extract_text_from_docx, 
            extract_text_from_doc
        )
        from django.core.mail import send_mail
        import os
        import json
        from django.conf import settings

        output_path = settings.BASE_DIR
        user = CustomUser.objects.get(pk=userId)
        content = AiProcess.objects.get(pk=contentId)
        text = None

        # Perform file-based operations based on fileType
        if int(fileType) == 1:
            local_path = output_path / f"user_file_{userId}.mp4"
            result = download_s3_file(content.url, local_path)

            if result:
                output_audio = output_path / f"user_audio_file_{userId}.mp3"
                result = convert_mp4_to_mp3(local_path, output_audio)
                os.remove(local_path)

                if result:
                    text = convert_audio_into_text(output_audio, user)
                else:
                    raise Exception("Audio conversion failed.")
            else:
                raise Exception("File download failed.")

        # Add other `fileType` handling logic here (same as in your code)

        # Process workflows
        if text:
            workflows = json.loads(content.workflow)
            ai_text = text

            for workflow in workflows:
                model = workflow['modelName']
                prompt = workflow['action']

                try:
                    llm_instance = LLM.objects.get(
                        name=model, is_enabled=True, is_delete=False, test_status="connected"
                    )
                except LLM.DoesNotExist:
                    raise Exception(f'Model "{model}" not available or not connected.')

                if llm_instance.source == 2:
                    ai_response = aiTogetherProcess(llm_instance.model_string, ai_text, prompt, user)
                elif llm_instance.source == 3:
                    ai_response = aiGeminiProcess(llm_instance.model_string, ai_text, prompt, user)
                elif llm_instance.source == 4:
                    ai_response = aiOpenAIProcess(llm_instance.model_string, ai_text, prompt, user)
                else:
                    raise Exception("No proper model provided for text generation.")

                workflow['input'] = ai_text
                workflow['ouput'] = ai_response
                workflow['status'] = "done"

                content.workflow = json.dumps(workflows)
                content.save()
                ai_text = ai_response
                ai_process_text_email(user.email, ai_response)

            content.url_status = "done"
            content.url_output = text
            content.save()

        else:
            raise Exception("No data available in file. Please check again.")

    except Exception as e:
        # Handle failures: mark the process as failed and notify the user
        content.url_status = "failed"
        content.save()

        error_message = f"Task failed: {str(e)}"
        ai_process_text_email(user.email, error_message)
        raise  # Re-raise exception so Celery marks the task as failed

