from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (CreateTicketSerializer, GetTicketSerializer,
                          UpdateTicketSerializer, GetCategorySerializer,
                          CreateCategorySerializer, UpdateCategorySerializer,
                          AddChatTicketSerializer, GetChatTicketSerializer,
                          UpdateChatTicketSerializer, GetAllTicketSerializer,
                          NotificationSerializer, ContactUsSerializer,
                          CreateMainCategorySerializer, GetMainCategorySerializer,
                          UpdateMainCategorySerializer, MainCategoryUserSerializer,
                          FAQInputSerializer, FAQOutputSerializer,
                          CouponInputSerializer, CouponOutputSerializer,
                          getCategoryWOPaginationSerializer
                        )
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from rest_framework.renderers import JSONRenderer
from authentication.models import CustomUser
from .models import Ticket, Category, TicketResponse, Notification, ContactUs, MainCategory, FAQ, Coupon
from rest_framework.pagination import PageNumberPagination
from authentication.awsservice import uploadImage
from rest_framework.parsers import JSONParser
from .FCMManager import pushMessage
from coreapp.models import LLM
from django.db.models import Q
from django.utils import timezone
from authentication.tasks import send_support_ticket_mail, send_feedback_ticket_mail
import boto3
import time
import jwt
import os


# Create Ticket.
class CreateTicket(APIView):
    def post(self, request):
        ticketType = request.data.get('ticket_type')
        if 'file' in request.data and request.data['file']:
            # uploaded_file = request.data['file']
            file = request.FILES.get('file')

            objectKey = "multinote/ticket/" + str(int(time.time())) + '-' + file.name           
            response = uploadImage(file, objectKey, file.content_type)

            if response is None:   
                request.data['image'] = objectKey
                request.data['user'] = request.user.id   
                serializer = CreateTicketSerializer(data=request.data, many=False)   
                if serializer.is_valid():
                    ticket = serializer.save()    

                    admin = CustomUser.objects.filter(is_superuser=True, is_delete=False).first()
                    title = "New Ticket Create"
                    body = f"New Ticket Create By {(request.user.username).capitalize()}"

                    pushMessage(admin.deviceToken, title, body)
                    Notification.objects.create(user_id=admin.id, title=title, description=body, ticket_id=ticket.id, type=2)


                    return Response(serializer.data, status=status.HTTP_200_OK)   
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)           
            else:
                return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)           
        else:
            data = request.data.copy() 
            data['user'] = request.user.id     
            serializer = CreateTicketSerializer(data=data, many=False)

            if serializer.is_valid():
                ticket = serializer.save()

                # if request.user.deviceToken and request.user.deviceToken != 'null':
                admin = CustomUser.objects.filter(is_superuser=True, is_delete=False).first()
                title = "New Ticket Create"
                body = f"New Ticket Create By {(request.user.username).capitalize()}"
                
                pushMessage(admin.deviceToken, title, body)
                Notification.objects.create(user_id=admin.id, title=title, description=body, ticket_id=ticket.id, type=2)

                if ticketType == 'support':
                    send_support_ticket_mail.delay(request.user.id, ticket.id)
                elif ticketType == 'feedback':
                    send_feedback_ticket_mail.delay(request.user.id, ticket.id)

                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get Ticket
class GetTicket(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # For Single Record
        if pk is not None:
            try:
                ticket = Ticket.objects.get(pk=pk, is_delete=False)
            except Ticket.DoesNotExist:
                return Response("Ticket Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetTicketSerializer(ticket)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # For Multiple Record
        ticketStatus = request.GET.get('status')
        searchBy = request.GET.get('searchBy')
        ticketType = request.GET.get('ticketType')
        queryset = Ticket.objects.filter(is_delete=False, user=request.user.id)

        # If status is provided, filter by both status and is_delete
        if searchBy != 'null':
            queryset = queryset.filter(ticket_title__icontains=searchBy)

        if ticketStatus:
            # queryset = queryset.filter(Q(status=ticketStatus) & Q(priority='low'))
            queryset = queryset.filter(Q(status=ticketStatus))

        if ticketType:
            # queryset = queryset.filter(Q(status=ticketStatus) & Q(priority='low'))
            queryset = queryset.filter(Q(ticket_type=ticketType))
        
        queryset = queryset.order_by('-created_at')
        
        page = paginator.paginate_queryset(queryset, request)
        serializer = GetTicketSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    
class GetAllTicket(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):

        paginator = self.pagination_class()

        ticketStatus = request.GET.get('status')
        searchBy = request.GET.get('searchBy')
        ticketType = request.GET.get('ticketType')

        queryset = Ticket.objects.filter(is_delete=False)

        ########################################################################
        # # Define mapping of filter parameters to model fields
        # filter_mapping = {
        #     'title': 'ticket_title__icontains',
        #     'description': 'description__icontains',
        #     # Add more fields as needed
        # }

        # # Create an empty Q object to hold the OR conditions
        # q_objects = Q()

        # # Iterate over filter parameters and construct Q objects for OR filtering
        # for param, lookup in filter_mapping.items():
        #     value = request.GET.get(param)
        #     if value != "null":
        #         q_objects |= Q(**{lookup: value})

        # # Apply the combined filter to the queryset
        # if q_objects:
        #     queryset = queryset.filter(q_objects)

        # # Order queryset by created_at
        # queryset = queryset.order_by('-created_at')

        # page = paginator.paginate_queryset(queryset, request)
        # serializer = GetAllTicketSerializer(page, many=True)
        # total_pages = paginator.page.paginator.num_pages
        # response_data = {
        #     'total_pages': total_pages,
        #     'results': serializer.data
        # }

        # return paginator.get_paginated_response(response_data)


        ##################################################################
        # # Define mapping of filter parameters to model fields
        # filter_mapping = {
        #     'title': 'ticket_title__icontains',
        #     'description': 'description__icontains',
        #     # Add more fields as needed
        # }

        # # Iterate over filter parameters, apply (and) filters to queryset (AND filter)
        # for param, lookup in filter_mapping.items():
        #     value = request.GET.get(param)
        #     if value != "null":
        #         # Dynamically construct Q objects for OR filtering
        #         queryset = queryset.filter(Q(**{lookup: value}))

        ######################################################################

        # search_by = request.GET.get('searchBy')

        # # Apply filter if searchBy parameter is provided (or filter)
        # if search_by:
        #     queryset = queryset.filter(
        #         Q(title__icontains=search_by) | Q(description__icontains=search_by)
        #     )

        ##########################################################################

        # # Define mapping of filter parameters to model fields
        # filter_mapping = {
        #     'ticketStatus': 'status',
        # }

        # # Iterate over filter parameters and apply filters to queryset (AND filter)
        # for param, field in filter_mapping.items():
        #     value = request.GET.get(param)
        #     if value != "null":
        #         queryset = queryset.filter(**{field: value})

        ##############################################################################


        if ticketStatus != 'null':
            queryset = queryset.filter(Q(status=ticketStatus))
        
        if searchBy != 'null':
            queryset = queryset.filter(ticket_title__icontains=searchBy)

        if ticketType:
            # queryset = queryset.filter(Q(status=ticketStatus) & Q(priority='low'))
            queryset = queryset.filter(Q(ticket_type=ticketType))
                
        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = GetAllTicketSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
        

# Update Ticket.
class UpdateTicket(APIView):
    
    def patch(self, request, pk=None):
        try:
            ticket = Ticket.objects.get(pk=pk, is_delete=False)
        except Ticket.DoesNotExist:
            return Response("Ticket Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateTicketSerializer(ticket, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Ticket.
class DeleteTicket(APIView):
    
    def patch(self, request, pk=None):
        try:
            ticket = Ticket.objects.get(pk=pk, is_delete=False)
        except Ticket.DoesNotExist:
            return Response("Ticket Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateTicketSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Ticket Delete"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Create Category
class CreateCategory(APIView):

    def post(self, request):
        # data = request.data.copy()
        # data['user'] = request.user.id
        # llm_models = request.data.get('models', [])
        name = request.data.get('name')
        category = Category.objects.filter(
                name=name, 
                is_delete=False
            ).exists()

        if category:
                return Response({"Message": "Category already exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CreateCategorySerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get Category
class GetCategory(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        pagination = request.GET.get('pagination', 'true')
        pagination = pagination.lower() == 'false'

        # forUser = request.GET.get('forUser', 'false')
        # forUser = forUser.lower() == 'true'

        # mainCategory = request.GET.get('mainCategory')

        if pk is not None:
            try:
                category = Category.objects.get(pk=pk, is_delete=False)
            except Category.DoesNotExist:
                return Response("Category Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetCategorySerializer(category)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # if forUser:
        #     category = Category.objects.filter(is_delete=False, status='active')
        # else:
        category = Category.objects.filter(is_delete=False)

        if searchBy != 'null':
            category = category.filter(name__icontains=searchBy)
        category = category.order_by('-created_at')

        if pagination:
            serializer = getCategoryWOPaginationSerializer(category, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            page = paginator.paginate_queryset(category, request)
            serializer = GetCategorySerializer(page, many=True)
            total_pages = paginator.page.paginator.num_pages
            response_data = {
                'total_pages': total_pages,
                'results': serializer.data
            }

            return paginator.get_paginated_response(response_data)


# Update Category
class UpdateCategory(APIView):
    
    def patch(self, request, pk=None):
        name = request.data.get('name')

        if name:
            category = Category.objects.filter(name=name, is_delete=False).exclude(id=pk).exists()
            if category:
                return Response({"Message": "Category already exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            category = Category.objects.get(pk=pk, is_delete=False)
        except Category.DoesNotExist:
            return Response("Category Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
            # return Response({"message": "Category Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Create Main Category
class CreateMainCategory(APIView):

    def post(self, request):
        # data = request.data.copy()
        # data['user'] = request.user.id
        # llm_models = request.data.get('models', [])
        name = request.data.get('name')
        mainCategory = MainCategory.objects.filter(
                name=name, 
                is_delete=False
            ).exists()

        if mainCategory:
                return Response({"Message": "Main Category already exist"}, status=status.HTTP_400_BAD_REQUEST)

        totalCategory = MainCategory.objects.filter(is_delete=False).count()
        if totalCategory >= 7:
                return Response({"Message": "You can create max seven category only"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CreateMainCategorySerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get Main Category
class GetMainCategory(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        if pk is not None:
            try:
                mainCategory = MainCategory.objects.get(pk=pk, is_delete=False)
            except MainCategory.DoesNotExist:
                return Response("Main Category Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetMainCategorySerializer(mainCategory)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
        mainCategory = MainCategory.objects.filter(is_delete=False)
        if searchBy != 'null':
            mainCategory = mainCategory.filter(name__icontains=searchBy)
            
        mainCategory = mainCategory.order_by('-created_at')

        page = paginator.paginate_queryset(mainCategory, request)
        serializer = GetMainCategorySerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)


# Get Main Category
class GetMainCategoryForUser(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        mainCategory = MainCategory.objects.filter(is_delete=False, status='active')
        
        serializer = MainCategoryUserSerializer(mainCategory, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    




# Update Category
class UpdateMainCategory(APIView):
    
    def patch(self, request, pk=None):
        name = request.data.get('name')

        if name:
            mainCategory = MainCategory.objects.filter(name=name, is_delete=False).exclude(id=pk).exists()
            if mainCategory:
                return Response({"Message": "Main Category already exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            mainCategory = MainCategory.objects.get(pk=pk, is_delete=False)
        except MainCategory.DoesNotExist:
            return Response("Main Category Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateMainCategorySerializer(mainCategory, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
            # return Response({"message": "Category Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Category
class DeleteCategory(APIView):
    
    def patch(self, request, pk=None):
        try:
            category = Category.objects.get(pk=pk, is_delete=False)
        except Category.DoesNotExist:
            return Response("Category Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Category Delete"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# Ticket Chat Section
class AddChatTicket(APIView):
    def post(self, request):
        if 'file' in request.data and request.data['file']:
            # uploaded_file = request.data['file']
            file = request.FILES.get('file')

            objectKey = "multinote/TicketResponse/" + str(int(time.time())) + '-' + file.name           
            response = uploadImage(file, objectKey, file.content_type)

            if response is None:   
                request.data['image'] = objectKey
                # request.data['user'] = request.user.id 
                serializer = AddChatTicketSerializer(data=request.data, many=False)   
                if serializer.is_valid():
                    ticket = serializer.validated_data.get('ticket')
                    serializer.save()    

                    if request.user.is_superuser:
                        title = "New Ticket Response"
                        body = f"New Ticket Response Against Ticket-{ticket.id} by MultinotesAi"
                        
                        pushMessage(ticket.user.deviceToken, title, body)
                        Notification.objects.create(user_id=ticket.user.id, sendBy='admin', title=title, description=body, ticket_id=ticket.id, type=3)

                    else:
                        admin = CustomUser.objects.filter(is_superuser=True, is_delete=False).first()
                        title = "New Ticket Response"
                        body = f"New Ticket Response Against Ticket-{ticket.id} by {(request.user.username).capitalize()}"
                        
                        pushMessage(admin.deviceToken, title, body)
                        Notification.objects.create(user_id=admin.id, sendBy='user', title=title, description=body, ticket_id=ticket.id, type=3)


                    return Response(serializer.data, status=status.HTTP_200_OK)   
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)           
            else:
                return Response({'error': f'Failed to upload image: {response}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)           
        else:
            serializer = AddChatTicketSerializer(data=request.data, many=False)
            if serializer.is_valid():
                ticket = serializer.validated_data.get('ticket')
                serializer.save()

                if request.user.is_superuser:
                    title = "New Ticket Response"
                    body = f"New Ticket Response Against Ticket-{ticket.id} by MultinotesAi"
                    
                    pushMessage(ticket.user.deviceToken, title, body)
                    Notification.objects.create(user_id=ticket.user.id, sendBy='admin', title=title, description=body, ticket_id=ticket.id, type=3)

                else:
                    admin = CustomUser.objects.filter(is_superuser=True, is_delete=False).first()
                    title = "New Ticket Response"
                    body = f"New Ticket Response Against Ticket-{ticket.id} by {(request.user.username).capitalize()}"
                    
                    # print(request.user.deviceToken)
                    pushMessage(admin.deviceToken, title, body)
                    Notification.objects.create(user_id=admin.id, sendBy='user', title=title, description=body, ticket_id=ticket.id, type=3)

                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get ChatTicket
class GetChatTicket(APIView):
    pagination_class = PageNumberPagination

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        if pk is not None:
            try:
                ticketResponse = TicketResponse.objects.get(pk=pk, is_delete=False)
            except TicketResponse.DoesNotExist:
                return Response("No Chat Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetChatTicketSerializer(ticketResponse)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"message": "Please provide chat Id"}, status=status.HTTP_400_BAD_REQUEST)
    
#Get All Chat By Admin
class GetAllChatTicket(APIView):
    pagination_class = PageNumberPagination

    def post(self, request):
        paginator = self.pagination_class()
        ticketId = request.data.get('ticketId')

        ticketResponse = TicketResponse.objects.filter(is_delete=False, ticket=ticketId)
        ticketResponse = ticketResponse.order_by('-created_at')
        page = paginator.paginate_queryset(ticketResponse, request)
        serializer = GetChatTicketSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
        

# Update Ticket.
class UpdateChatTicket(APIView):
    
    def patch(self, request, pk=None):
        try:
            ticketResponse = TicketResponse.objects.get(pk=pk, is_delete=False)
        except TicketResponse.DoesNotExist:
            return Response("No Chat Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateChatTicketSerializer(ticketResponse, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Ticket.
class DeleteChatTicket(APIView):
    
    def patch(self, request, pk=None):
        try:
            ticketResponse = TicketResponse.objects.get(pk=pk, is_delete=False)
        except TicketResponse.DoesNotExist:
            return Response("No Chat Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateChatTicketSerializer(ticketResponse, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Chat Delete"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# DeleteMultiple Category.
class DeleteMultiple(APIView):
    
    def post(self, request):
        categories = request.data.get("categories", [])
        if len(categories) > 0:
            for id in categories:
                category = Category.objects.get(id=id)
                category.is_delete = True
                category.save()
            return Response({"message": "All Category Deleted"}, status=status.HTTP_200_OK)
        return Response({"message": "Pleaes Provide Category Id"}, status=status.HTTP_400_BAD_REQUEST)
    

# Manage Notification
class ManageNotification(APIView):
    pagination_class = PageNumberPagination    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        # search = request.GET.get('search')
        if pk is not None:
            try:
                notification = Notification.objects.get(pk=pk, is_delete=False)
            except Notification.DoesNotExist:
                return Response("Notification Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # category_id = request.query_params.get('category_id') 
        if request.user.is_superuser:
            queryset = Notification.objects.filter(sendBy='user', is_delete=False, isMarkRead=False)
        else:
            queryset = Notification.objects.filter(sendBy='admin', is_delete=False, isMarkRead=False, user=request.user.id)

        # if search != 'null':
        #     queryset = queryset.filter(
        #         Q(llm_model__icontains=search) | 
        #         Q(title__icontains=search) | 
        #         Q(content__icontains=search)
        #     )

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            notification = Notification.objects.get(pk=pk, is_delete=False)
        except Notification.DoesNotExist:
            return Response("Notification Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = NotificationSerializer(notification, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Notification Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Create ContactUs
class ContactUsQuery(APIView):
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def post(self, request):
        # data = request.data.copy()
        # data['user'] = request.user.id

        serializer = ContactUsSerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        queryStatus = request.GET.get('status')
        searchBy = request.GET.get('searchBy')
        if pk is not None:
            try:
                contact = ContactUs.objects.get(pk=pk, is_delete=False)
            except ContactUs.DoesNotExist:
                return Response("ContactUs Not Found", status=status.HTTP_404_NOT_FOUND)
            
            serializer = ContactUsSerializer(contact)
            return Response(serializer.data, status=status.HTTP_200_OK)


        if queryStatus != 'null':
            queryset = ContactUs.objects.filter(is_delete=False, status=queryStatus)
        else:
            queryset = ContactUs.objects.filter(is_delete=False)

        if searchBy != 'null':
            queryset = queryset.filter(
                Q(name__icontains=searchBy) | 
                Q(email__icontains=searchBy) | 
                Q(mobile__icontains=searchBy)
            )

        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = ContactUsSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            contact = ContactUs.objects.get(pk=pk, is_delete=False)
        except ContactUs.DoesNotExist:
            return Response("ContactUs Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = ContactUsSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "ContactUs Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Create FAQSection
class FAQSection(APIView):
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def post(self, request):
        # data = request.data.copy()
        # data['user'] = request.user.id
        question = request.data.get("question", None)

        if FAQ.objects.filter(question=question, is_delete=False).exists():
            return Response({"message": "FAQ Question already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FAQInputSerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        userType = request.GET.get('userType')
        if pk is not None:
            try:
                faq = FAQ.objects.get(pk=pk, is_delete=False)
            except FAQ.DoesNotExist:
                return Response({"message": "FAQ Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = FAQOutputSerializer(faq)
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = FAQ.objects.filter(is_delete=False)

        if searchBy:
            queryset = queryset.filter(question__icontains=searchBy)
        
        queryset = queryset.order_by('-created_at')
        if userType == 'user':
            queryset = queryset.filter(is_active=True)
            serializer = FAQOutputSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            page = paginator.paginate_queryset(queryset, request)
            serializer = FAQOutputSerializer(page, many=True)
            total_pages = paginator.page.paginator.num_pages
            response_data = {
                'total_pages': total_pages,
                'results': serializer.data
            }

            return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        question = request.data.get("question", None)
        try:
            faq = FAQ.objects.get(pk=pk, is_delete=False)
        except FAQ.DoesNotExist:
            return Response({"message": "FAQ Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        if FAQ.objects.filter(question=question, is_delete=False).exists():
            return Response({"message": "FAQ Question already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = FAQInputSerializer(faq, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "FAQ Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Coupon Section
class ManageCouponView(APIView):
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def post(self, request):
        # data = request.data.copy()
        # data['user'] = request.user.id
        # question = request.data.get("question", None)


        serializer = CouponInputSerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def get(self, request, pk=None):
        paginator = self.pagination_class()
        searchBy = request.GET.get('searchBy')
        forUser = request.GET.get('forUser', 'false')
        isActive = request.GET.get('isActive')
        forUser = forUser.lower() == "true"
        # isActive = isActive.lower() == "true"

        if pk is not None:
            try:
                coupon = Coupon.objects.get(pk=pk, is_delete=False)
            except Coupon.DoesNotExist:
                return Response({"message": "Coupon Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = CouponOutputSerializer(coupon)
            return Response(serializer.data, status=status.HTTP_200_OK)


        if searchBy:
            queryset = Coupon.objects.filter(is_delete=False)
            
            queryset = queryset.filter(
                Q(coupon_name__icontains=searchBy) |
                Q(coupon_code__icontains=searchBy)
            )
        else:
            queryset = Coupon.objects.filter(is_delete=False)

        if isActive == 'True' or isActive == 'False':
            isActive = isActive.lower() == 'true'
            queryset = queryset.filter(is_active=isActive)

        if forUser:
            queryset = queryset.filter(is_delete=False, is_active=True, end_date__gte=timezone.now())



        queryset = queryset.order_by('-created_at')

        page = paginator.paginate_queryset(queryset, request)
        serializer = CouponOutputSerializer(page, many=True)
        total_pages = paginator.page.paginator.num_pages
        response_data = {
            'total_pages': total_pages,
            'results': serializer.data
        }

        return paginator.get_paginated_response(response_data)
    
    def patch(self, request, pk=None):
        try:
            coupon = Coupon.objects.get(pk=pk, is_delete=False)
        except Coupon.DoesNotExist:
            return Response({"message": "Coupon Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CouponInputSerializer(coupon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response({"message": "Coupon Update"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk=None):
        try:
            coupon = Coupon.objects.get(pk=pk, is_delete=False)
        except Coupon.DoesNotExist:
            return Response({"message": "Coupon Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        coupon.delete()
        return Response({"message": "Coupon Delete"}, status=status.HTTP_200_OK)
    
class ApplyCouponView(APIView):
    # permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def post(self, request):
        data = request.data.copy()
        # data['user'] = request.user.id
        subs_amount = request.data.get('subsAmount')
        coupon_code = request.data.get('couponCode')

        try:
            coupon = Coupon.objects.get(coupon_code=coupon_code)
            if not coupon.is_valid():
                return Response({"message": "Coupon is not valid"}, status=status.HTTP_400_BAD_REQUEST)
            
            if subs_amount <= coupon.discount_value:
                return Response({"message": "Invalid coupon code. Amount is greater than discount value. "}, status=status.HTTP_400_BAD_REQUEST)

            # # Check if user has exceeded usage limit for this coupon
            # if CouponUsage.objects.filter(coupon=coupon, user=user).count() >= coupon.usage_limit_per_user:
            #     return {"success": False, "message": "Coupon usage limit exceeded for this user"}

            # # Check if the total usage of this coupon has exceeded its limit
            # if CouponUsage.objects.filter(coupon=coupon).count() >= coupon.usage_limit:
            #     return {"success": False, "message": "Coupon usage limit exceeded"}

            # Check if order total meets minimum requirement
            if coupon.min_order_amount and subs_amount < coupon.min_order_amount:
                return Response({"message": f"Minimum order amount to use this coupon is {coupon.min_order_amount}"}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discount
            if coupon.coupon_type == 'percentage':
                discount = (subs_amount * coupon.discount_value / 100)
                if coupon.max_discount_amount and discount > coupon.max_discount_amount:
                    discount = coupon.max_discount_amount
                # if discount >= subs_amount:
                    # discount = subs_amount - 1
            else:
                # if coupon.discount_value >= subs_amount:
                #     discount = subs_amount - 1
                # else:
                discount = coupon.discount_value

            data = {
                "finalAmount": subs_amount - discount,
                "couponCode": coupon_code,
                "couponType": coupon.coupon_type,
                "discountValue": discount,
                "bonusToken": coupon.bonus_token
            }

            return Response({"data": data, "message": "Coupon applied successfully"}, status=status.HTTP_200_OK)
        
        except Coupon.DoesNotExist:
            return Response({"message": "Invalid coupon code"}, status=status.HTTP_400_BAD_REQUEST)






