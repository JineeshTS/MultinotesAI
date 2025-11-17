from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from .models import CustomUser
from datetime import timedelta
from django.utils import timezone


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.id) + str(user.email) + str(timestamp) + str(user.is_verified)


def generateToken(user):
    token_generator = EmailVerificationTokenGenerator()
    token = token_generator.make_token(user)
    return token

def generateJWTToken(user):
    # refresh = RefreshToken.for_user(user)
    # access = refresh.access_token

    access_token = AccessToken.for_user(user)
    return access_token


"""
from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_custom_email(subject, template_name, context, recipient_list):
    # Render the email template with the provided context data
    html_content = render_to_string(template_name, context)

    # Send the email
    send_mail(
        subject=subject,
        message='',  # We are sending HTML content, so no need for a plain text message
        html_message=html_content,
        from_email=settings.EMAIL_HOST_USER,  # Set your default from email here
        recipient_list=recipient_list,
    )



    from django.core.mail import EmailMessage

    # Create an EmailMessage object
    email = EmailMessage(
        'Subject',            # Subject of the email
        'Message',            # Body of the email
        'from@example.com',   # From email address
        ['to@example.com'],   # To email addresses
    )

    # Attach the PDF file
    with open('/path/to/your/file.pdf', 'rb') as f:
        email.attach('filename.pdf', f.read(), 'application/pdf')

    # Send the email
    email.send()


    from django.core.mail import EmailMessage
from email.mime.application import MIMEApplication

# Create an EmailMessage object
email = EmailMessage(
    'Subject',            # Subject of the email
    'Plain text message', # Plain text message
    'from@example.com',   # From email address
    ['to@example.com'],   # To email addresses
)

    # Set the HTML content
    html_content = "
    <html>
    <head></head>
    <body>
        <h1>Hello!</h1>
        <p>This is an HTML message.</p>
    </body>
    </html> "


    # Attach the HTML content
    email.attach_alternative(html_content, "text/html")

    # Attach the PDF file
    with open('path/to/your/pdf/file.pdf', 'rb') as pdf_file:
        pdf_attachment = pdf_file.read()
        email.attach('filename.pdf', pdf_attachment, 'application/pdf')

    # Send the email
    email.send()


    from django.core.mail import EmailMessage

    # Create an EmailMessage object with HTML body
    email = EmailMessage(
        subject='Subject',              # Subject of the email
        body='<html><body><h1>Hello!</h1><p>This is an HTML email.</p></body></html>',  # HTML body
        from_email='from@example.com',  # From email address
        to=['to@example.com'],          # To email addresses
    )

    # Set the content type to HTML
    email.content_subtype = 'html'

    # Send the email
    email.send()


    from django.core.mail import EmailMessage

    # Create an EmailMessage object with plain text message
    email = EmailMessage(
        subject='Subject',              # Subject of the email
        body='Plain text message',      # Plain text message
        from_email='from@example.com',  # From email address
        to=['to@example.com'],          # To email addresses
    )

    # Attach HTML content as alternative
    html_content = "
    <html>
    <head></head>
    <body>
        <h1>Hello!</h1>
        <p>This is an HTML message.</p>
    </body>
    </html>
    "
    email.attach_alternative(html_content, "text/html")

    # Send the email
    email.send()

"""


"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@authentication_classes([])  # No authentication
@permission_classes([AllowAny])  # No permissions required
def some_function_view(request):
    # Your view logic here


"""



# def push_message(data):
#     url = 'https://fcm.googleapis.com/fcm/send'
#     server_key = 'YOUR_SERVER_KEY'  # Replace with your FCM server key
#     headers = {
#         'Authorization': 'key=' + server_key,
#         'Content-Type': 'application/json'
#     }
#     payload = {
#         'to': data['token'],
#         'data': data
#     }
#     response = requests.post(url, json=payload, headers=headers)
#     if response.status_code == 200:
#         print('Notification sent successfully')
#     else:
#         print('Failed to send notification:', response.text)

# # Usage
# data = {
#     'token': 'DEVICE_TOKEN',  # FCM device token
#     'title': 'New Message',
#     'description': 'You have a new message!'
# }
# push_message(data)