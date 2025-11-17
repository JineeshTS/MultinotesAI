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
from .models import LLM
from .utils import (generateUsingGemini, generateUsingTogether, 
                    generateTextByTogether, generateTextByTogetherTest, 
                    generateUsingGeminiTest
                )
import time
from rest_framework import status
import multiprocessing
from threading import Event, Thread
from queue import Queue
from django.utils import timezone

import asyncio
from django.http import StreamingHttpResponse
from django.utils.timezone import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


class TextGenerationAPIView(APIView):

    def post(self, request):
        groupName = request.data.get("groupName")
        models = request.data.get("models", [])
        prompt = request.data.get("prompt")
        category = request.data.get("category")

        tasks = []
        processes = []
        for model in models:
            try:
                llm_instance = LLM.objects.get(name=model)
                # llm_instance = await sync_to_async(LLM.objects.get)(name=model)
                model_string = llm_instance.model_string
            except LLM.DoesNotExist:
                return Response({
                    'message': f'Model "{model}" not found.',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if model == "Gemini Pro":
                process = Thread(
                    target=generateUsingGemini, 
                    args=(prompt, model_string, model, groupName))
                processes.append(process)
                process.start()

            # elif model == "GPT-4":
            #     process = threading.Thread(
            #         target=generateTextByOpenAI, 
            #         args=(prompt, model_string, model, groupName))
            #     processes.append(process)
            #     process.start()

            elif model in ['Llama 2', 'Mistral', 'Gemma Instruct']:
                process = Thread(
                    target=generateTextByTogether, 
                    args=(prompt, model_string, model, groupName))
                processes.append(process)
                process.start()

            else:
                return Response({
                    'message': f'Invalid model: {model}',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        for process in processes:
            process.join()
        return Response({"message": "All responses sent to WebSocket clients"}, status=status.HTTP_200_OK)
    


# class TextEventStream(APIView):
#     permission_classes = [AllowAny]
#     def get(self, request):
#         response = StreamingHttpResponse(generateUsingGeminiTest2("What is the future scope of Django?", "gemini-pro"))
#         response = StreamingHttpResponse(generateTextByTogetherTest2("What is the future scope of Django?", "mistralai/Mistral-7B-Instruct-v0.2"))
#         response['Content-Type'] = 'text/event-stream'
#         return response
    



# # Define your asynchronous generators for each function
# def generator_1():
    
#     for i in range(15):
#         yield "data: Response from function 1\n\n"
#         time.sleep(1)

# def generator_2():
#     for i in range(20):
#         yield "data: Response from function 2\n\n"
#         # time.sleep(1)

# # Combine the generators into a single asynchronous generator

# def combine_generators():
#     processes = []
#     process = threading.Thread(target=generator_1)
#     processes.append(process)
#     process.start
#     process = threading.Thread(target=generator_2)
#     processes.append(process)
#     process.start
#     # for data in threading.Thread(generator_1()):
#     #     yield data
#     # for data in threading.Thread(generator_2()):
#     #     yield data
    


####################################################################3333
# Combine the generators into a single asynchronous generator
def combine_generators(models, prompt):
# def combine_generators(param_1):
    threads = []
    queue_list = []
    for model in models:
        try:
            llm_instance = LLM.objects.get(name=model)
            model_string = llm_instance.model_string
        except LLM.DoesNotExist:
            my_dict = {
                'message': f'Model "{model}" not found.',
                'status': 400
            }
            yield f"data: {my_dict}\n\n"
            return
        
        if model == "Gemini Pro":
            queue_1 = Queue()
            thread_1 = Thread(
                target=generateUsingGeminiTest, 
                args=(prompt, model_string, model, queue_1))
            thread_1.start()
            threads.append(thread_1)
            queue_list.append(queue_1)

        elif model == 'Llama 2':
            queue_2 = Queue()
            thread_2 = Thread(
                target=generateTextByTogetherTest, 
                args=(prompt, model_string, model, queue_2))
            thread_2.start()
            threads.append(thread_2)
            queue_list.append(queue_2)

        elif model == 'Mistral':
            queue_3 = Queue()
            thread_3 = Thread(
                target=generateTextByTogetherTest, 
                args=(prompt, model_string, model, queue_3))
            thread_3.start()
            threads.append(thread_3)
            queue_list.append(queue_3)

        elif model == 'Gemma Instruct':
            queue_4 = Queue()
            thread_4 = Thread(
                target=generateTextByTogetherTest, 
                args=(prompt, model_string, model, queue_4))
            thread_4.start()
            threads.append(thread_4)
            queue_list.append(queue_4)

        else:
            my_dict = {
                'message': f'Invalid model: {model}',
                'status': 400
            }
            yield f"data: {my_dict}\n\n"
            return

    # Yield data from all queues concurrently
    done_count = 0
    while done_count < len(threads):
        for queue in queue_list:
            try:
                data = queue.get_nowait()
                if data == "DONE":
                    done_count += 1
                else:
                    yield data
            except Exception:
                pass  # Queue is empty, continue to the next one

    # # Wait for all threads to finish
    # for thread in threads:
    #     thread.join()

    

class TextEventStream(APIView):
    permission_classes = [AllowAny]

    # Define your view
    def post(self, request):
        # groupName = request.data.get("groupName")

        models = request.data.get("models", [])
        prompt = request.data.get("prompt")
        category = request.data.get("category")

        # models = ["Llama 2","Mistral","Gemma Instruct","Gemini Pro"]
        # prompt = "Tell me about Hemma Malini in 1000 Words"

        if not prompt or not models:
            return Response({"message": "Prompt and models are required."}, status=status.HTTP_400_BAD_REQUEST)


        response = StreamingHttpResponse(combine_generators(models, prompt))
        response['Content-Type'] = 'text/event-stream'
        response['Cache-Control'] = 'no-cache'
        return response
    
###################################################################################



    





# class TextEventStream(APIView):
#     permission_classes = [AllowAny]
#     def get(self, request, *args, **kwargs):
#         response = HttpResponse(content_type='text/event-stream')
#         response['Cache-Control'] = 'no-cache'
#         response['Connection'] = 'keep-alive'

#         # Infinite loop to send data periodically
#         while True:
#             # Construct the event data
#             event_data = f"data: {time.ctime()}\n\n"
            
#             # Write the event data to the response
#             response.write(event_data)
#             response.flush()  # Flush the buffer to send data immediately
            
#             # Sleep for a short interval (e.g., 1 second)
#             time.sleep(1)

#         return response