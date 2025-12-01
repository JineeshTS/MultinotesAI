import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http.request import HttpHeaders
from django.shortcuts import render

from django.http import HttpResponse
from pyfcm import FCMNotification
import os
import requests
import json


# # cred = credentials.Certificate(settings.BASE_DIR /"serviceAccountKey.json")
# cred = credentials.Certificate(settings.BASE_DIR /"serviceAccountKey.json")
# firebase_admin.initialize_app(cred)

# Initialize FCM client with the server key (only if available)
_server_key = os.getenv('SERVER_KEY')
if _server_key:
    try:
        fcm = FCMNotification(api_key=_server_key)
    except Exception as e:
        print(f"Warning: FCM initialization failed: {e}")
        fcm = None
else:
    print("Warning: SERVER_KEY not configured - push notifications will be disabled")
    fcm = None


# Send a notification to a single device
def pushMessage(deviceToken, title, body):
    if fcm is None:
        print("FCM not configured - push notification skipped")
        return None
    try:
        result = fcm.notify_single_device(
            registration_id=deviceToken,
            message_title=title,
            message_body=body,
            message_icon = "https://multinotes.ai/favicon.svg",
            timeout=5,
        )
        print(result)
        return result
    except Exception as e:
        print(f"FCM push notification failed: {e}")
        return None


# class TestNotification(APIView):
#     # def pushMessage(device_token, title, body):
#     def post(self, request):
#         # Construct a message
#         message = messaging.Message(
#             notification=messaging.Notification(
#                 title="Hi",
#                 body="First Notification for Test"
#             ),
#             data=None,
#             token="ffPaYmp7Hn9hjjdhkabUlv:APA91bF_9Ar6s9sf8BbyhUjTBUiLGJ9Hab4w_0pF2vIYZXNcjahC45HJcxiue96B17T0mnhmh2Ckx4_rlC9xpx5GLjjAKbF0wwylkDlIlGje_L280g1SiL2RKO-iY2pIbXScb9uE8cw7",
#         )

#         # Send the message
#         try:
#             response = messaging.send(message)
#             # print("Type is ---> ", response._responses[0].__dict__)
#             # print("Type is ---> ", type(response))
#             print("Successfully sent message:", response)
#             return Response({"message": response}, status=status.HTTP_200_OK)
#         except Exception as e:
#             print("Error sending message:", e)
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST) 




# class TestNotification(APIView):
#     # def pushMessage(device_token, title, body):
#     def post(self, request):
#         # Construct a message
#         message = messaging.MulticastMessage(
#             notification=messaging.Notification(
#                 title="Hi",
#                 body="First Notification for Test"
#             ),
#             data=None,
#             tokens=["euLIOCo7dqKYvPFsQnnfHE:APA91bG7CUrpkehmaJLlriAtgHXVa1PiOtNkGvHGBaMXEpwXbZCzfPSA6yTZi53ml4_o4gp0Fjkl0R5jWz5Fh5-j7Lk-0B6efh7tdDwnA7aE5Wy-dQOm2nLi_ktfVVmxsVe5z23hHCWP"]
#         )

#         # Send the message
#         try:
#             response = messaging.send_multicast(message)
#             # print("Type is ---> ", response['_responses'][0].__dict__)
#             print("Type is ---> ", response._responses[0].__dict__)
#             print("Successfully sent message:", response)
#             return Response({"message": str(response)}, status=status.HTTP_200_OK)
#         except Exception as e:
#             print("Error sending message:", e)
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)  
        




        

# def send_notification(registration_ids , message_title , message_desc):
#     fcm_api = "AAAABb2QGEo:APA91bGqf7cHz8HFFUip0SywUhrVFc9MQRkwK8kX8iedoZGS9Yt8I_U2WDART_OlJIhj9oN8WlkW1nw9A7-OUdNUBHFhDqtq5c2GmTZPlPnRRgQzhzhKcyCUob2CXLi_f3oxVh9g5ZgZ"

#     # fcm_api = "AAAAx9XQYBc:APA91bF30uz2WxJCuKqgWMH9v0EPv0j60l4G3_rBruJW-7T9ludB-lSBW8_ZEIi1ii0oXAs9QPhj6afyt47gMuizVMq8jH7lLNNKHbiiEl9zVjLfy1ufbqiD2rVf64bQBRfaSNJ8x42z"

#     url = "https://fcm.googleapis.com/fcm/send"
    
#     headers = {
#     "Content-Type":"application/json",
#     "Authorization": 'key='+fcm_api}

#     payload = {
#         "registration_ids" :registration_ids,
#         "priority" : "high",
#         "notification" : {
#             "body" : message_desc,
#             "title" : message_title,
#             "image" : "https://i.ytimg.com/vi/m5WUPHRgdOA/hqdefault.jpg?sqp=-oaymwEXCOADEI4CSFryq4qpAwkIARUAAIhCGAE=&rs=AOn4CLDwz-yjKEdwxvKjwMANGk5BedCOXQ",
#             "icon": "https://yt3.ggpht.com/ytc/AKedOLSMvoy4DeAVkMSAuiuaBdIGKC7a5Ib75bKzKO3jHg=s900-c-k-c0x00ffffff-no-rj",
            
#         }
#     }
#     result = requests.post(url,  data=json.dumps(payload), headers=headers, timeout=5 )
#     # print(type(result))
#     # print(result.__dict__)
#     print(result.json())
        




# def send(request):
#     resgistration  = ["ffPaYmp7Hn9hjjdhkabUlv:APA91bF_9Ar6s9sf8BbyhUjTBUiLGJ9Hab4w_0pF2vIYZXNcjahC45HJcxiue96B17T0mnhmh2Ckx4_rlC9xpx5GLjjAKbF0wwylkDlIlGje_L280g1SiL2RKO-iY2pIbXScb9uE8cw7"]

#     send_notification(resgistration , 'Code Keen added a new video' , 'Code Keen new video alert')
#     return HttpResponse("sent")

#     # # Construct the message
#     # message = {
#     #     "registration_ids": resgistration,
#     #     "notification": {
#     #         "title": "Title of the notification",
#     #         "body": "Body of the notification"
#     #     }
#     # }

#     # # Send the message
#     # response = fcm.notify_single_device(**message)

#     # # Send a notification to a single device
#     # try:
#     #     registration_id = "ef8GT1qOuml-F0hd6gTd1S:APA91bFEJ5_Hwd7jLtmk8ldY8-ea6ayYB6OMiL4eKo1ChyfaUGm7OBDZwTxIQbcFQ4B92A8sBmi-djpwpJjBE42aLx0k75R9rigKz-0vvshnoVgFW7Kk9bZ-fFtBH2Y64dkl094FDy-K"
#     #     message_title = "Uber update"
#     #     message_body = "Hi john, your customized news for today is ready"

#     #     result = fcm.notify_single_device(registration_id=registration_id, message_title=message_title, message_body=message_body)

#     #     print(result)
#     # except Exception as e:
#     #     print(e)
#     #     result = e

#     # # # Send to multiple devices by passing a list of ids.
#     # # registration_ids = ["<device registration_id 1>", "<device registration_id 2>", ...]
#     # # message_title = "Uber update"
#     # # message_body = "Hope you're having fun this weekend, don't forget to check today's news"
#     # # result = fcm.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title, message_body=message_body)

#     # # print(result)
#     # return HttpResponse(str(result))