import json
from channels.generic.websocket import WebsocketConsumer
from channels.consumer import AsyncConsumer, SyncConsumer
from channels.exceptions import StopConsumer
from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from authentication.models import CustomUser
# from django.contrib.auth.models import User

@sync_to_async
def save_user_async(user):
    user.save()



class BoardConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        userId = self.scope['url_route']['kwargs']['user_id']
        groupName = f"userGroup_{userId}"
        self.group_name = groupName

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        user = await sync_to_async(CustomUser.objects.get)(id=userId)
        if not user.groupName:
             user.groupName = self.group_name
             await save_user_async(user)

        await self.accept()
        await self.send(text_data=json.dumps({'status': 'connected', 'groupName': user.groupName}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_response(self, event):
        response = event['response']
        await self.send(text_data=response)  # Assuming the response is text data







# class BoardConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         userId = self.scope['url_route']['kwargs']['user_id']

#         groupName = f"userGroup_{userId}"

#         self.group_name = groupName

#         await self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )
#         user = await sync_to_async(CustomUser.objects.get)(id=userId)
#         if not user.groupName:
#              user.groupName = self.group_name
#              await save_user_async(user)

#         await self.accept()
#         await self.send(text_data=json.dumps({'status': 'connected', 'groupName': user.groupName}))

        
#         # await self.add_user_to_group()
#         # await self.send(text_data=json.dumps({'status': 'connected'}))
#         # else:
#         #     print("Not Authenticate")
#         #     await self.close()

            
#     # async def receive(self, text_data):
#     #     data = json.loads(text_data)
#     #     userId = data.get('userId')

#     #     groupName = f"userGroup_{userId}"

#     #     self.group_name = groupName

#     #     await self.channel_layer.group_add(
#     #         self.group_name,
#     #         self.channel_name
#     #     )
#     #     user = CustomUser.objects.get(id=userId)
#     #     if not user.groupName:
#     #          user.groupName = self.group_name
#     #          user.save()

#     #     await self.send(text_data=json.dumps({'groupName': user.groupName}))


#     # # @database_sync_to_async
#     # def get_user_id(self):
#     #     # return self.scope["user"].id


#     # async def add_user_to_group(self):
#     #     user_id = self.get_user_id()
#     #     if user_id:
#     #         group_name = f"user_group_{user_id}"
#     #         await self.channel_layer.group_add(group_name, self.channel_name)


#     # async def connect(self):
#     #     await self.channel_layer.group_add(
#     #         'text_generation_group',
#     #         self.channel_name
#     #     )
#     #     await self.accept()

#     # async def connect(self):
#     #     # self.room_name = "test_consumer"
#     #     self.room_group_name = f"text_generation_group_{self.scope['user'].id}"
#     #     # self.room_group_name = "text_generation_group"
#     #     await self.channel_layer.group_add(
#     #         self.room_group_name,
#     #         self.channel_name
#     #     )
#     #     await self.accept()
#     #     await self.send(text_data=json.dumps({'status': 'connected'}))
#     #     # await self.send(text_data=json.dumps({'group_name': self.room_group_name}))


#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             'text_generation_group',
#             self.channel_name
#         )

#     async def send_response(self, event):
#         response = event['response']
#         await self.send(text_data=response)  # Assuming the response is text data






# class TextGenerationConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         await self.channel_layer.group_add(
#             'text_generation_group',
#             self.channel_name
#         )
#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             'text_generation_group',
#             self.channel_name
#         )

#     async def send_response(self, event):
#         response = event['response']
#         await self.send(text_data=response)  # Assuming the response is text data


    # async def receive(self, text_data):
    #     text_data_json = json.loads(text_data)
    #     message = text_data_json['message']

    #     # Send message to room group
    #     await self.channel_layer.group_send(
    #         self.room_group_name,
    #         {
    #             'type': 'chat_message',
    #             'message': message
    #         }
    #     )




# class BoardConsumer(WebsocketConsumer):

#     def connect(self):
#         userId = self.scope['url_route']['kwargs']['user_id']

#         groupName = f"userGroup_{userId}"

#         self.group_name = groupName

#         self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )
#         user = CustomUser.objects.get(id=userId)
#         if not user.groupName:
#              user.groupName = self.group_name
#              user.save()

#         self.accept()
#         self.send(text_data=json.dumps({'status': 'connected', 'groupName': user.groupName}))
#         # self.send(text_data=json.dumps({'status': 'connected', 'groupName': "user_group"}))


#     def disconnect(self, close_code):
#         self.channel_layer.group_discard(
#             'text_generation_group',
#             self.channel_name
#         )

#     def send_response(self, event):
#         response = event['response']
#         self.send(text_data=response)  # Assuming the response is text data

# The client includes the user identification information in the WebSocket handshake request (e.g., as a query parameter).
# The server extracts the user identification information from the WebSocket scope during connection establishment and uses it to associate the WebSocket connection with the authenticated user.

