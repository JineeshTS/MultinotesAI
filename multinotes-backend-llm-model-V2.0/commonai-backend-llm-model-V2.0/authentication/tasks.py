from celery import shared_task
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from .models import CustomUser
import os
from .utils import generateJWTToken
from django.core.serializers import deserialize
from django.conf import settings
import boto3
from .awsservice import getImageUrl, get_image, delete_file_from_s3, download_s3_file
from coreapp.models import UserContent, Folder, StorageUsage, Document, AiProcess, LLM
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .load_drive import create_google_drive_folder, upload_folder_structure_to_drive
import io
import json
from coreapp.utils import aiTogetherProcess, aiGeminiProcess, aiOpenAIProcess, extract_text_from_image
import yt_dlp


@shared_task
def send_verification_email(userId):

    user = CustomUser.objects.get(pk=userId)

    token = generateJWTToken(user)

    baseUrl = os.getenv('BASE_URL')


    # Compose email
    subject = 'Email Verification'
    message = f"Please click on the following link to verify your email: {baseUrl}/auth/user/verify-email?token={token}"

    url = f"{baseUrl}/auth/user/verify-email?token={token}"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Email Verification</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Email Verification</h1>

                </div>

                <div class="content">

                    <p>Hello,</p>

                    <p>Please click the button below to verify your email address.</p>

                    <a href="{url}" class="btn">Verify Email</a>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''

    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message,  
    #     recipient_list=[user.email], 
    #     from_email=None,   # Set Globaly from settiing.py file
    #     html_message=None  # If we send html message then message  will be None
    # )

    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [user.email],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()

@shared_task
def sendResetPasswordMail(userId):

    user = CustomUser.objects.get(pk=userId)

    token = generateJWTToken(user)
    
    baseUrl = os.getenv('BASE_URL')

    # Compose email
    subject = 'Password Reset'
    message = f"Please click on the following link to reset your password: {baseUrl}/auth/user/password-reset?token={token}"
    url = f"{baseUrl}/auth/user/password-reset?token={token}"
    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Reset Password</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Reset Password</h1>

                </div>

                <div class="content">

                    <p>Hello,</p>

                    <p>Please click the button below to reset your password.</p>

                    <a href="{url}" class="btn">Reset Password</a>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''
   
    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message, 
    #     recipient_list=[user.email], 
    #     from_email=None, 
    #     html_message=None
    # )


    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [user.email],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()

@shared_task
def otp_for_user_to_sub_admin(userId, email_otp):

    user = CustomUser.objects.get(pk=userId)

    # token = generateJWTToken(user)
    
    # baseUrl = os.getenv('BASE_URL')

    # Compose email
    subject = 'OTP for Change Status'
    message = f"Otp for change user status"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Otp for Change Status</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>OTP</h1>

                </div>

                <div class="content">

                    <p>Hello,</p>

                    <p>Please find the OTP below for change user status.</p>

                    <a class="btn">{email_otp}</a>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''
   
    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message, 
    #     recipient_list=[user.email], 
    #     from_email=None, 
    #     html_message=None
    # )


    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [user.email],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()


@shared_task
def send_support_ticket_mail(userId, tiketId):

    user = CustomUser.objects.get(pk=userId)

    user_name = user.username.capitalize()

    # token = generateJWTToken(user)
    
    # baseUrl = os.getenv('BASE_URL')

    # Compose email
    subject = 'Support Ticket Create'
    message = f"Otp for change user status"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Support Ticket</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Support Ticket</h1>

                </div>


                <div class="content">

                    <p>{user_name},</p>

                    <p>Thank you for contacting Multinotes Support. We wanted to let you know that we've received your message.</p>

                    <p>Ticket ID: {tiketId}</p>


                </div>

                <div class="content">

                    <p>Thank you!</p>

                    <p>The Multinotes Support Team</p>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''
   
    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message, 
    #     recipient_list=[user.email], 
    #     from_email=None, 
    #     html_message=None
    # )


    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [user.email],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()


@shared_task
def send_feedback_ticket_mail(userId, tiketId):

    user = CustomUser.objects.get(pk=userId)

    user_name = user.username.capitalize()

    # token = generateJWTToken(user)
    
    # baseUrl = os.getenv('BASE_URL')

    # Compose email
    subject = 'Thank You for Your Valuable Feedback!'
    message = f"Otp for change user status"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Feedback Created</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Feedback</h1>

                </div>

                <div class="content">

                    <p>{user_name},</p>

                    <p>Thank you for taking the time to provide us your feedback. We truly appreciate your effort in sharing your thoughts with us.</p>

                </div>

                <div class="content">

                    <p>Thank you!</p>

                    <p>The Multinotes Support Team</p>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''
   
    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message, 
    #     recipient_list=[user.email], 
    #     from_email=None, 
    #     html_message=None
    # )


    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [user.email],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()


@shared_task
def share_content_email(userId):

    user = CustomUser.objects.get(pk=userId)

    token = generateJWTToken(user)

    baseUrl = os.getenv('BASE_URL')


    # Compose email
    subject = 'Content Share Notification'
    message = f"Please click on the following link to get share content: {baseUrl}/auth/user/verify-email?token={token}"

    # url = f"{baseUrl}?userId={userId}"
    url = f"{baseUrl}/login"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Email Verification</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Content Share</h1>

                </div>

                <div class="content">

                    <p>Hello,</p>

                    <p>Please click the button below to get share content.</p>

                    <a href="{url}" class="btn">Show Content</a>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''

    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message,  
    #     recipient_list=[user.email], 
    #     from_email=None,   # Set Globaly from settiing.py file
    #     html_message=None  # If we send html message then message  will be None
    # )

    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [user.email],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()


@shared_task
def upload_file_data_email(userEmail):

    # user = CustomUser.objects.get(pk=userId)

    # token = generateJWTToken(user)

    baseUrl = os.getenv('BASE_URL')


    # Compose email
    subject = 'Upload file data at drive Notification'
    # message = f"Please click on the following link to get share content: {baseUrl}/auth/user/verify-email?token={token}"

    # url = f"{baseUrl}?userId={userId}"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Upload Data</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Content Share</h1>

                </div>

                <div class="content">

                    <p>Hello,</p>

                    <p>All file upload at your drive successfully.</p>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''

    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message,  
    #     recipient_list=[user.email], 
    #     from_email=None,   # Set Globaly from settiing.py file
    #     html_message=None  # If we send html message then message  will be None
    # )

    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [userEmail],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()

@shared_task
def upload_folder_data_email(userEmail):

    # user = CustomUser.objects.get(pk=userId)

    # token = generateJWTToken(user)

    baseUrl = os.getenv('BASE_URL')


    # Compose email
    subject = 'Upload folder data at drive Notification'
    # message = f"Please click on the following link to get share content: {baseUrl}/auth/user/verify-email?token={token}"

    # url = f"{baseUrl}?userId={userId}"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Upload Data</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="header">

                    <h1>Content Share</h1>

                </div>

                <div class="content">

                    <p>Hello, </p>

                    <p>All folder upload at your drive successfully.</p>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''

    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message,  
    #     recipient_list=[user.email], 
    #     from_email=None,   # Set Globaly from settiing.py file
    #     html_message=None  # If we send html message then message  will be None
    # )

    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [userEmail],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()
    

# from .tasks import upload_file_to_s3

# class FileUploadView(APIView):
#     def post(self, request):
#         file_obj = request.FILES.get('file')  # Assuming the file is sent as part of the request
#         if file_obj:
#             # Enqueue Celery task to upload the file to S3
#             task_result = upload_file_to_s3.delay(file_obj.name, file_obj.read(), file_obj.content_type)
#             return Response({"message": "File upload task queued", "task_id": task_result.id}, status=status.HTTP_202_ACCEPTED)
#         else:
#             return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

#     def get(self, request, task_id):
#         task_result = AsyncResult(task_id)
#         if task_result.ready():
#             # If the task has finished, return the result
#             return Response(task_result.result)
#         else:
#             # If the task is still pending, return a status message
#             return Response({"status": "Task is still in progress"}, status=status.HTTP_200_OK)
    

@shared_task
def ai_process_text_email(userEmail, text):

    # user = CustomUser.objects.get(pk=userId)

    # token = generateJWTToken(user)

    baseUrl = os.getenv('BASE_URL')


    # Compose email
    subject = 'AI Process Data'
    # message = f"Please click on the following link to get share content: {baseUrl}/auth/user/verify-email?token={token}"

    # url = f"{baseUrl}?userId={userId}"

    body = f'''
        <!DOCTYPE html>

        <html lang="en">
        
        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>AI Data</title>

            <style>

                /* Reset styles */

                body,

                h1,

                p {{

                    margin: 0;

                    padding: 0;

                }}
        
                /* Container styles */

                .container {{

                    max-width: 600px;

                    margin: 0 auto;

                    padding: 20px;

                    border: 1px solid #ccc;

                    border-radius: 5px;

                }}
        
                /* Header styles */

                .header {{

                    background-color: #007bff;

                    color: #fff;

                    padding: 10px;

                    text-align: center;

                    border-radius: 5px 5px 0 0;

                }}
        
                /* Content styles */

                .content {{

                    padding: 20px;

                }}
        
                /* Button styles */

                .btn {{
                
                    background-color: #007bff;

                    color: #fff !important;

                    display: inline-block;

                    padding: 10px 20px;

                    text-decoration: none;

                    border-radius: 5px;

                }}
        
                /* Footer styles */

                .footer {{

                    text-align: center;

                    padding-top: 20px;

                }}

            </style>

        </head>
        
        <body>

            <div class="container">

                <div class="content">

                    <p>{text}</p>

                </div>

                <div class="footer">

                    <p>If you didn't request this, you can safely ignore this email.</p>

                </div>

            </div>

        </body>
        
        </html>
    '''

    # to_email = os.getenv('EMAIL_TO')

    # # Send email
    # send_mail(
    #     subject=subject, 
    #     message=message,  
    #     recipient_list=[user.email], 
    #     from_email=None,   # Set Globaly from settiing.py file
    #     html_message=None  # If we send html message then message  will be None
    # )

    email = EmailMessage(
        subject= subject,        # Subject of the email
        body= body,              # Plain text message
        from_email= None,        # From email address
        to= [userEmail],          # To email addresses
    )
    email.content_subtype = 'html'
    email.send()
    

#*******************************************************************
    
@shared_task
def upload_data_file_at_drive(userId, fileId, creds_json, share_email):
    file_obj = UserContent.objects.get(id=fileId, is_delete=False)
    user = CustomUser.objects.get(pk=userId)

    creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    drive_service = build('drive', 'v3', credentials=creds)

    s3_file_key = file_obj.file
    success, file_content = get_image(s3_file_key)

    if success:
        try:                    
            file_metadata = {
                'name': s3_file_key.split('/')[-1],  # Use the file name from the S3 key
            }   

            media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')

            # media = MediaFileUpload(file_path, mimetype='application/octet-stream')
            file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()


            sStatus = delete_file_from_s3(s3_file_key)

            storage = StorageUsage.objects.filter(user=user, is_delete=False).first()
            if storage:
                storage.total_storage_used -= file_obj.fileSize
                storage.save()

            file_obj.delete()

            if share_email:
                upload_file_data_email(user.email)
        except Exception as e:
            pass


@shared_task
def upload_data_folder_at_drive(userId, folderId, creds_json, folder_data, folderName, share_email):
    from coreapp.views import get_folder_detail, get_files, get_documents, get_folder_file_size
    user = CustomUser.objects.get(pk=userId)

    creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    drive_service = build('drive', 'v3', credentials=creds)

    folder_list = [folderId]       
    # folderName, folder_data = get_folder_detail(user, folderId)
    parent_id = create_google_drive_folder(drive_service, folderName)

    files = get_files(user, folderId)

    documents = get_documents(user, folderId)

    for document in documents:
        doc_obj = Document.objects.filter(id=document['id'], is_delete=False).first()
        doc_obj.folder = None
        doc_obj.save()

    storage = StorageUsage.objects.filter(user=user, is_delete=False).first()
    for file in files:
            
        s3_file_key = file['file']
        success, file_content = get_image(s3_file_key)

        if success:
            try:
                file_metadata = {
                    'name': s3_file_key.split('/')[-1],  # Use the file name from the S3 key
                    'parents': [parent_id]  # Place file in the created folder
                }

                media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')
                
                u_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                sStatus = delete_file_from_s3(s3_file_key)

                file_obj = UserContent.objects.filter(id=file['id'], is_delete=False).first()

                if storage:
                    storage.total_storage_used -= file_obj.fileSize
                    storage.save()

                if file_obj: file_obj.delete()
            except Exception as e:
                pass

    new_folder_list = upload_folder_structure_to_drive(user, drive_service, folder_data, folder_list, parent_id )

    Folder.objects.filter(id__in=new_folder_list).delete()
    
    if share_email:
        upload_folder_data_email(user.email)

@shared_task()
def aiprocess_data(userId, contentId, fileType):
    try:
        from coreapp.views import (
                            convert_mp4_to_mp3, convert_audio_into_text,      
                            download_video, extract_text_from_pdf,
                            extract_text_from_excel, extract_text_from_docx,
                            extract_text_from_doc
                        )
        # print("userId is ----> ", userId)
        # print("contentId is ----> ", contentId)
        # print("uploadFile is ----> ", uploadFile)

        output_path = settings.BASE_DIR

        user = CustomUser.objects.get(pk=userId)
        content = AiProcess.objects.get(pk=contentId)

        text = None

        # upload_folder_data_email(user.email, 2)
        if int(fileType) == 1:
            # upload_folder_data_email(user.email, 3)
            local_path = output_path/f"user_file_{userId}.mp4"

            # Download the file
            result = download_s3_file(content.url, local_path)

            # upload_folder_data_email(user.email, 4)
            if result:
                # print(f"File downloaded successfully from S3 to {local_path}")

                input_video = local_path
                output_audio = output_path/f"user_audio_file_{userId}.mp3"

                # upload_folder_data_email(user.email, 5)
                result = convert_mp4_to_mp3(input_video, output_audio)

                # upload_folder_data_email(user.email, 6)

                os.remove(local_path)

                if result:
                    # upload_folder_data_email(user.email, 7)
                    text = convert_audio_into_text(output_audio, user)

            else:
                # # print("There is an error in file downloading.")
                # return Response({"message": f"There is an error in file downloading."}, status=status.HTTP_400_BAD_REQUEST)
                text = "There is an error in file downloading."
                ai_process_text_email(user.email, text)
        
        elif int(fileType) == 2:
            local_path = output_path/f"user_file_{userId}.mp3"

            # Download the file
            result = download_s3_file(content.url, local_path)

            if result:
                text = convert_audio_into_text(local_path, user)
        
        elif int(fileType) == 3:
            try:
                audio_file_path = download_video(content.url, output_path, userId)
            except yt_dlp.utils.DownloadError as e:
                # return Response({"message": e.msg})
                ai_process_text_email(user.email, e.msg)
            except Exception as e:
                # return Response({"message": "error occured"})
                ai_process_text_email(user.email, "Error Occured")
            
            text = convert_audio_into_text(audio_file_path, user)

        elif int(fileType) == 4:
            local_path = output_path/f"user_file_{userId}.pdf"

            # Download the file
            result = download_s3_file(content.url, local_path)

            if result:
                text = extract_text_from_pdf(local_path)
                # print("Text is ---> ", text)


        elif int(fileType) == 5:
            local_path = output_path/f"user_file_{userId}.xlsx"

            # Download the file
            result = download_s3_file(content.url, local_path)

            if result:
                text = extract_text_from_excel(local_path)


        elif int(fileType) == 6:
            # local_path = output_path/f"user_file_{userId}.docx"

            # # Download the file
            # result = download_s3_file(content.url, local_path)

            # if result:
            #     text = extract_text_from_docx(local_path)

            if content.url.split('.')[-1] == "docx":
                local_path = output_path/f"user_file_{userId}.docx"

                # Download the file
                result = download_s3_file(content.url, local_path)

                # text = extract_text_from_doc(local_path)

                if result:
                    text = extract_text_from_docx(local_path)
            else:
                local_path = output_path/f"user_file_{userId}.doc"
                # Download the file
                result = download_s3_file(content.url, local_path)

                if result:
                    text = extract_text_from_doc(local_path)

        elif int(fileType) == 7:
            ext = content.url.split('.')[-1]
            local_path = output_path/f"user_file_{userId}.{ext}"

            # Download the file
            result = download_s3_file(content.url, local_path)

            if result:
                text = extract_text_from_image(local_path)


        workflows = json.loads(content.workflow)

        # upload_folder_data_email(user.email, 7)
        # print("Text is ----> ", text)
        if text:
            # ai_process_text_email(user.email, text)
            ai_text = text
            for workflow in workflows:
                model = workflow['modelName']
                prompt = workflow['action']

                try:
                    llm_instance = LLM.objects.get(name=model, is_enabled=True, is_delete=False, test_status="connected")
                    model_string = llm_instance.model_string
                except LLM.DoesNotExist:
                    # return Response({'message': f'Model "{model}" not available or not connected',
                    # }, status=status.HTTP_400_BAD_REQUEST)
                    ai_process_text_email(user.email, f'Model "{model}" not available or not connected')
                
                if llm_instance.source==2 and llm_instance.text:
                    ai_response = aiTogetherProcess(model_string, ai_text, prompt, user)
                    
                elif llm_instance.source==3 and llm_instance.text:
                    ai_response = aiGeminiProcess(model_string, ai_text, prompt, user)
                    
                elif llm_instance.source==4 and llm_instance.text:
                    ai_response = aiOpenAIProcess(model_string, ai_text, prompt, user)
                    
                else:
                    # return Response({'message': 'Please provide proper model for text generation.'}, status=status.HTTP_400_BAD_REQUEST)
                    ai_process_text_email(user.email, 'Please provide proper model for text generation.')
                    

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
            text = "There is no data available in file. Please check again."
            ai_process_text_email(user.email, text)    
            content.url_status = "done"
            content.url_output = text
            content.save()

    except Exception as e:
        # Handle failures: mark the process as failed and notify the user

        error_message = f"Task failed: {str(e)}"
        ai_process_text_email(user.email, error_message)

        content.url_status = "failed"
        content.url_output = error_message
        content.save()

        raise  # Re-raise exception so Celery marks the task as failed
    
