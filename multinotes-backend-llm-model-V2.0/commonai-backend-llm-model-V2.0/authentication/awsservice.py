from rest_framework.views import APIView
from rest_framework.response import Response
import boto3
from django.conf import settings
from botocore.exceptions import NoCredentialsError, ClientError

# Initialize S3 client only if credentials are available
_aws_access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
_aws_secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

if _aws_access_key and _aws_secret_key:
    try:
        s3 = boto3.client('s3')
        bucketName = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    except Exception as e:
        print(f"Warning: AWS S3 client initialization failed: {e}")
        s3 = None
        bucketName = None
else:
    print("Warning: AWS credentials not configured - S3 features will be disabled")
    s3 = None
    bucketName = None

# get Image url from aws s3 bucket
def getImageUrl(imageKey):
    if s3 is None or bucketName is None:
        print("Warning: S3 not configured - cannot generate image URL")
        return None
    imageUrl = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucketName, 'Key': imageKey},
        ExpiresIn=3600
    )
    return imageUrl


# Upload image to s3 bucket
def uploadImage(file, imageKey, contentType):
    if s3 is None or bucketName is None:
        print("Warning: S3 not configured - cannot upload image")
        return Exception("S3 not configured")
    try:
        s3.upload_fileobj(
            Fileobj = file,
            Bucket = bucketName,
            Key = imageKey,
            # ExtraArgs={'ContentType': file.content_type}
            ExtraArgs={'ContentType': contentType}
        )
        return None
    except Exception as e:
        return e


def delete_file_from_s3(file_key):
    if s3 is None or bucketName is None:
        print("Warning: S3 not configured - cannot delete file")
        return False
    try:
        s3.delete_object(Bucket=bucketName, Key=file_key)
        return True
    except NoCredentialsError:
        # print("Credentials not available")
        return False
    except ClientError as e:
        # print(f"Error occurred: {e}")
        return False

def get_image(file_key):
    if s3 is None or bucketName is None:
        print("Warning: S3 not configured - cannot get image")
        return False, Exception("S3 not configured")
    try:
        s3_file = s3.get_object(Bucket=bucketName, Key=file_key)
        file_content = s3_file['Body'].read()  # Read the content of the file
        return True, file_content
    except Exception as e:
        return False, e

def download_s3_file(file_key, file_path):
    if s3 is None or bucketName is None:
        print("Warning: S3 not configured - cannot download file")
        return False
    try:
        # Download the file
        s3.download_file(bucketName, file_key, file_path)
        return True
    except Exception as e:
        return False

    
    


