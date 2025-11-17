import os
import json
from django.shortcuts import redirect, render
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.conf import settings
from django.http import JsonResponse
# from .models import UserCredentials
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from google.auth.transport.requests import Request
from rest_framework.permissions import IsAuthenticated, AllowAny
from .awsservice import getImageUrl, get_image, delete_file_from_s3
from coreapp.models import UserContent, Folder, StorageUsage, Document
from coreapp.models import Share
from coreapp.serializers import (FolderListSerializer, ShareContentFolderSerializer, 
                                 ContentLibrarySerializer, ShareContentFileSerializer)
import io

# scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/userinfo.email'];

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveAuthView(APIView):
    def post(self, request):
        flow = Flow.from_client_secrets_file(
            settings.BASE_DIR/"multinotes_google_cred.json",
            scopes=SCOPES,
            redirect_uri= settings.GOOGLE_REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        # request.session['state'] = state
        return Response({'auth_url': auth_url, 'message': 'redirect url'}, status=status.HTTP_200_OK)
    
    
class GoogleDriveCallbackView(APIView):
    # permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get('code')

        flow = Flow.from_client_secrets_file(
            settings.BASE_DIR/"multinotes_google_cred.json",
            scopes=SCOPES,
            # state=state,
            redirect_uri= settings.GOOGLE_REDIRECT_URI  # Match with the one used in GoogleDriveAuthView
        )

        flow.fetch_token(code=code)
        
        # authorization_response = request.build_absolute_uri()
        # flow.fetch_token(authorization_response=authorization_response)
        
        # Save the credentials for future use
        credentials = flow.credentials
        creds_json = credentials.to_json()


        user_creds = CustomUser.objects.get(id=request.user.id)
        user_creds.credentials = creds_json
        user_creds.save()

        return Response({'message': 'Authorization successful', "cred": creds_json}, status=status.HTTP_200_OK)


# class UploadFileToGoogleDriveView(APIView):
#     def post(self, request):
#         # s3_file_key = request.data.get('fileKey', None)
#         fileId = request.data.get('fileId')
#         try:
#             file_obj = UserContent.objects.get(id=fileId, is_delete=False)
#         except UserContent.DoesNotExist:
#             return Response({"message": "File not found"}, status=status.HTTP_404_NOT_FOUND)

#         if not file_obj.file:
#             return Response({"message": "No such file exits at this fileId"}, status=status.HTTP_400_BAD_REQUEST)
        
#         s3_file_key = file_obj.file
#         success, file_content = get_image(s3_file_key)

#         if success:
#             try:
#                 user_creds = CustomUser.objects.get(id=request.user.id)
#                 creds = Credentials.from_authorized_user_info(json.loads(user_creds.credentials))

                
#                 if creds and creds.expired and creds.refresh_token:
#                     creds.refresh(Request())
                
#                 drive_service = build('drive', 'v3', credentials=creds)

#                 # Get information about the user's Drive space
#                 about = drive_service.about().get(fields="storageQuota").execute()
    
#                 storage_quota = about.get('storageQuota', {})

#                 # Parse storage information
#                 total_space = int(storage_quota.get('limit', 0))
#                 # used_space = int(storage_quota.get('usage', 0))
#                 # available_space = total_space - used_space if total_space else None

                
#                 # File to upload
#                 # file_path = settings.BASE_DIR/"readme.md"
#                 # file_metadata = {'name': os.path.basename(file_path)}

#                 file_metadata = {
#                     'name': s3_file_key.split('/')[-1],  # Use the file name from the S3 key
#                 }   


#                 media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')

#                 # media = MediaFileUpload(file_path, mimetype='application/octet-stream')
#                 file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()


#                 sStatus = delete_file_from_s3(s3_file_key)

#                 storage = StorageUsage.objects.filter(user=request.user, is_delete=False).first()
#                 if storage:
#                     storage.total_storage_used -= file_obj.fileSize
#                     storage.save()

#                 file_obj.delete()

                
#                 return Response({'message': 'File uploaded successfully', 'file_id': file.get('id')})

#             # except UserCredentials.DoesNotExist:
#             except Exception as e:
#                 return Response({'error': 'User not authenticated'}, status=status.HTTP_403_FORBIDDEN)
            
#         else:
#             return Response({"error": {str(file_content)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





def create_google_drive_folder(service, title, parent_id=None):
    """
    Creates a folder in Google Drive and returns the folder ID.
    """
    folder_metadata = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.folder',
    }
    
    if parent_id:
        folder_metadata['parents'] = [parent_id]
    
    try:
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        # print(f'An error occurred: {error}')
        return None
    

# def upload_folder_structure_to_drive(user, service, folder_data, parent_id=None):
def upload_folder_structure_to_drive(user, service, folder_data, folder_list, parent_id=None):
    from coreapp.views import get_files, get_documents
    """
    Recursively uploads folders to Google Drive while maintaining the structure.
    """

    for folder in folder_data:
        files = get_files(user, folder['id'])
        documents = get_documents(user, folder['id'])
        folder_list.append(folder['id'])

        drive_folder_id = create_google_drive_folder(service, folder['title'], parent_id)

        if drive_folder_id:                    
            for document in documents:
                doc_obj = Document.objects.filter(id=document['id'], is_delete=False).first()
                doc_obj.folder = None
                doc_obj.save()

            storage = StorageUsage.objects.filter(user=user, is_delete=False).first()
            for file in files:
                # if file['content_type'] == 'document':
                #     file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()
                #     file_obj.folder = None
                #     file_obj.save()
                # else:

                s3_file_key = file['file']
                success, file_content = get_image(s3_file_key)

                if success:
                    file_metadata = {
                        'name': s3_file_key.split('/')[-1],  # Use the file name from the S3 key
                        'parents': [drive_folder_id]  # Place file in the created folder
                    }

                    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
                    # media = MediaFileUpload(file_path, mimetype='application/octet-stream')
                    u_file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                    sStatus = delete_file_from_s3(s3_file_key)

                    file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()

                    if storage:
                        storage.total_storage_used -= file_obj.fileSize
                        storage.save()

                    if file_obj: file_obj.delete()

            
            # Recursively create subfolders
            if folder['subfolders']:
                upload_folder_structure_to_drive(user, service, folder['subfolders'], folder_list, drive_folder_id)

    return folder_list


# Get file size for all subfolder file.
def get_sub_folder_file_size(user, folder_data, root_file_size):
    from coreapp.views import get_folder_file_size
    for folder in folder_data:
        files_size = get_folder_file_size(user, folder['id'])

        root_file_size += files_size
        
        # Recursively create subfolders
        if folder['subfolders']:
            root_file_size += get_sub_folder_file_size(user, folder['subfolders'], 0)

    return root_file_size


class UploadDataToGoogleDriveView(APIView):
    def post(self, request):
        from .tasks import upload_data_file_at_drive, upload_data_folder_at_drive
        from coreapp.views import get_folder_detail, get_folder_file_size
        # s3_file_key = request.data.get('fileKey', None)
        folderId = request.data.get('folderId', None)
        fileId = request.data.get('fileId', None)
        # data_type = request.data.get('dataType', None)
        user = request.user

        try:
            user_creds = CustomUser.objects.get(id=request.user.id)
            creds = Credentials.from_authorized_user_info(json.loads(user_creds.credentials))

            
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            drive_service = build('drive', 'v3', credentials=creds)

            # Get information about the user's Drive space
            about = drive_service.about().get(fields="storageQuota").execute()

            storage_quota = about.get('storageQuota', {})

            # Parse storage information
            total_space = int(storage_quota.get('limit', 0))
            used_space = int(storage_quota.get('usage', 0))
            available_space = total_space - used_space

        # except UserCredentials.DoesNotExist:

        except Exception as e:
            return Response({'message': 'Please connect your Google drive 1st'}, status=status.HTTP_400_BAD_REQUEST)

        # if not data_type:
        #     return Response({"message": "Data Type id required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if fileId:
            try:
                file_obj = UserContent.objects.get(id=fileId, is_delete=False)
                if available_space < file_obj.fileSize + 1000:
                    return Response(
                        {"message": "The available space in your Google Drive is less than the space required for the content you are trying to upload. Please free up some space in your Drive and try again."
                        }, status=status.HTTP_400_BAD_REQUEST)
                
            except UserContent.DoesNotExist:
                return Response({"message": "File not found"}, status=status.HTTP_404_NOT_FOUND)

            if not file_obj.file:
                return Response({"message": "No such file exits at this fileId"}, status=status.HTTP_400_BAD_REQUEST)
            
            upload_data_file_at_drive.delay(user.id, fileId, creds.to_json(), share_email=True)
            
            # s3_file_key = file_obj.file
            # success, file_content = get_image(s3_file_key)

            # if success:
            #     try:                    
            #         # File to upload
            #         # file_path = settings.BASE_DIR/"readme.md"
            #         # file_metadata = {'name': os.path.basename(file_path)}

            #         file_metadata = {
            #             'name': s3_file_key.split('/')[-1],  # Use the file name from the S3 key
            #         }   


            #         media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')

            #         # media = MediaFileUpload(file_path, mimetype='application/octet-stream')
            #         file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()


            #         sStatus = delete_file_from_s3(s3_file_key)

            #         storage = StorageUsage.objects.filter(user=user, is_delete=False).first()
            #         if storage:
            #             storage.total_storage_used -= file_obj.fileSize
            #             storage.save()

            #         file_obj.delete()

                    
            return Response({'message': 'An email will be sent once the file has been successfully uploaded to Google Drive.'})

            #     # except UserCredentials.DoesNotExist:
            #     except Exception as e:
            #         return Response({'error': 'error occured in file upload at drive.'}, status=status.HTTP_403_FORBIDDEN)
                
            # else:
            #     return Response({"error": {str(file_content)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        elif folderId:            
            if not Folder.objects.filter(id=folderId, is_delete=False).exists():
                return Response({"message": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)
               
            # try:
            #     user_creds = CustomUser.objects.get(id=user.id)
            #     creds = Credentials.from_authorized_user_info(json.loads(user_creds.credentials))
                
            #     if creds and creds.expired and creds.refresh_token:
            #         creds.refresh(Request())

            #     drive_service = build('drive', 'v3', credentials=creds)

            # # except UserCredentials.DoesNotExist:
            # except Exception as e:
            #     return Response({'error': 'User not authenticated'}, status=status.HTTP_403_FORBIDDEN)
            

            # folder_list = [folderId]       
            folderName, folder_data = get_folder_detail(user, folderId)
            # parent_id = create_google_drive_folder(drive_service, folderName)

            # files = get_files(user, folderId)

            folder_file_size = get_folder_file_size(user, folderId)


            # root_file_size = 0
            # for file in files:
            #     root_file_size += file['fileSize']
            
            total_file_size = get_sub_folder_file_size(user, folder_data, folder_file_size)


            if available_space < total_file_size + 1000:
                return Response(
                    {"message": "The available space in your Google Drive is less than the space required for the content you are trying to upload. Please free up some space in your Drive and try again."
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            upload_data_folder_at_drive.delay(user.id, folderId, creds.to_json(), folder_data, folderName, share_email=True)

            # documents = get_documents(user, folderId)

            # for document in documents:
            #     doc_obj = Document.objects.filter(id=document['id'], is_delete=False).first()
            #     doc_obj.folder = None
            #     doc_obj.save()

            # storage = StorageUsage.objects.filter(user=user, is_delete=False).first()
            # for file in files:
            #     # if file['content_type'] == 'document':
            #     #     file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()
            #     #     file_obj.folder = None
            #     #     file_obj.save()
            #     # else:
                    
            #     s3_file_key = file['file']
            #     success, file_content = get_image(s3_file_key)

            #     if success:
            #         file_metadata = {
            #             'name': s3_file_key.split('/')[-1],  # Use the file name from the S3 key
            #             'parents': [parent_id]  # Place file in the created folder
            #         }

            #         media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
                    
            #         u_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            #         sStatus = delete_file_from_s3(s3_file_key)

            #         file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()

            #         if storage:
            #             storage.total_storage_used -= file_obj.fileSize
            #             storage.save()

            #         if file_obj: file_obj.delete()

            # new_folder_list = upload_folder_structure_to_drive(user, drive_service, folder_data, folder_list, parent_id )

            # Folder.objects.filter(id__in=new_folder_list).delete()

                    
            return Response({'message': 'An email will be sent once the data has been successfully uploaded to Google Drive.'})       
        else:
            return Response({"message": "Please provide fileId or folderId for upload at drive"}, status=status.HTTP_400_BAD_REQUEST)


class UploadCompleteDataToDriveView(APIView):
    def post(self, request):
        from .tasks import upload_data_file_at_drive, upload_data_folder_at_drive
        from coreapp.views import get_folder_detail, get_folder_file_size

        user = request.user

        # Retrieve folders where the user is the owner
        folders = Folder.objects.filter(user=user, parent_folder__isnull=True, is_delete=False)

        # Retrieve shares where the user is the shared recipient and content_type is 'folder'
        shares = Share.objects.filter(share_to_user=user, content_type='folder', is_delete=False)
            
        # Combine the querysets
        combined_queryset = sorted(
            list(folders) + list(shares),
            key=lambda instance: instance.created_at,
            reverse=True
        )

        # Serialize the data
        user_folders = []
        for item in combined_queryset:
            if isinstance(item, Folder):
                root_data =  FolderListSerializer(item).data
                root_data['isShare'] = False
                user_folders.append(root_data)
            elif isinstance(item, Share):
                share_data = ShareContentFolderSerializer(item).data
                share_data['folder']['isShare'] = True
                user_folders.append(share_data['folder'])
                # data.append(share_data)

        root_files = UserContent.objects.filter(user=user, is_delete=False, folder__isnull=True)

        share_files = Share.objects.filter(share_to_user=user, content_type__in=['file', 'document'], is_delete=False)

        combined_queryset = sorted(
            list(root_files) + list(share_files),
            key=lambda instance: instance.created_at,
            reverse=True
        )

        user_files = []
        for item in combined_queryset:
            if isinstance(item, UserContent):
                root_data = ContentLibrarySerializer(item).data
                root_data['isShare'] = False
                # root_data['dataType'] = 'file'
                user_files.append(root_data)
            elif isinstance(item, Share):
                share_data = ShareContentFileSerializer(item).data
                
                if share_data['content_type'] == 'file':
                    share_data['file']['isShare'] = True
                    share_data['file']['dataType'] = 'share'
                    user_files.append(share_data['file'])
                # else:
                #     share_data['document']['isShare'] = True
                #     share_data['document']['dataType'] = 'share'
                #     user_files.append(share_data['document'])
                    
        if len(user_files) + len(user_folders) > 0:
            try:
                user_creds = CustomUser.objects.get(id=request.user.id)
                creds = Credentials.from_authorized_user_info(json.loads(user_creds.credentials))

                
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                
                drive_service = build('drive', 'v3', credentials=creds)

                # Get information about the user's Drive space
                about = drive_service.about().get(fields="storageQuota").execute()

                storage_quota = about.get('storageQuota', {})

                # Parse storage information
                total_space = int(storage_quota.get('limit', 0))
                used_space = int(storage_quota.get('usage', 0))
                available_space = total_space - used_space

            # except UserCredentials.DoesNotExist:

            except Exception as e:
                return Response({'message': 'Please connect your Google drive 1st'}, status=status.HTTP_400_BAD_REQUEST)

            total_data_size = 0
            # total_folder_data_size = 0
            for user_folder in user_folders:
                folderName, folder_data = get_folder_detail(user, user_folder['id'])

                folder_file_size = get_folder_file_size(user, user_folder['id'])

                
                total_file_size = get_sub_folder_file_size(user, folder_data, folder_file_size)

                total_data_size += total_file_size

            for user_file in user_files:
                total_data_size += int(user_file['fileSize'])

            if available_space < total_data_size + 10000:
                return Response(
                    {"message": "The available space in your Google Drive is less than the space required for the content you are trying to upload. Please free up some space in your Drive and try again."
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            share_email = False
            for idx, user_folder in enumerate(user_folders):
                folderName, folder_data = get_folder_detail(user, user_folder['id'])

                folder_file_size = get_folder_file_size(user, user_folder['id'])
        
                total_file_size = get_sub_folder_file_size(user, folder_data, folder_file_size)

                if idx == len(user_folders) - 1:
                    share_email = True
                upload_data_folder_at_drive.delay(user.id, user_folder['id'], creds.to_json(), folder_data, folderName, share_email=share_email)

            for ids, user_file in enumerate(user_files):
                if ids == len(user_files) - 1:
                    share_email = True

                upload_data_file_at_drive.delay(user.id, user_file['id'], creds.to_json(), share_email=share_email)
                      
            return Response({'message': 'An email will be sent once the file has been successfully uploaded to Google Drive.'})
   
        else:
            return Response({"message": "No File or Folder found for this user"}, status=status.HTTP_400_BAD_REQUEST)


def google_drive_auth(request):
    flow = Flow.from_client_secrets_file(
        settings.BASE_DIR/"multinotes_g_cred.json",
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # Save the state in the session to verify the response later
    request.session['state'] = state
    return redirect(authorization_url)

def google_drive_callback(request):
    state = request.session.get('state')
    
    flow = Flow.from_client_secrets_file(
        settings.BASE_DIR/"multinotes_g_cred.json",
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    authorization_response = request.build_absolute_uri()
    flow.fetch_token(authorization_response=authorization_response)

    # Save credentials
    credentials = flow.credentials
    creds_json = credentials.to_json()

    # print("Cred is ----> ", creds_json)
    # user_creds, created = UserCredentials.objects.get_or_create(user=request.user)
    # user_creds.credentials = creds_json
    # user_creds.save()

    return JsonResponse({'message': 'Authorization complete', "cred": creds_json})

# def upload_to_google_drive(request):
#     # try:
#         # user_creds = UserCredentials.objects.get(user=request.user)
#         # creds = Credentials.from_authorized_user_info(json.loads(user_creds.credentials))

#         creds = Credentials.from_authorized_user_info(cred)

        
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())

#         drive_service = build('drive', 'v3', credentials=creds)
        
#         # Upload file to the authenticated user's Google Drive
#         file_metadata = {'name': 'readme.md'}
#         media = MediaFileUpload(settings.BASE_DIR/"readme.md", mimetype='application/octet-stream')
#         file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
#         return JsonResponse({'message': 'File uploaded successfully', 'file_id': file.get('id')})

#     # # except UserCredentials.DoesNotExist:
#     # except Exception as e:
#     #     return JsonResponse({'error': 'User not authenticated'}, status=403)