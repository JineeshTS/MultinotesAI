from rest_framework.views import APIView
from rest_framework.response import Response
import boto3
from django.conf import settings
from botocore.exceptions import NoCredentialsError, ClientError

s3 = boto3.client('s3')
bucketName = settings.AWS_STORAGE_BUCKET_NAME

# get Image url from aws s3 bucket
def getImageUrl(imageKey):
    imageUrl = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucketName, 'Key': imageKey},
        ExpiresIn=3600 
    )
    return imageUrl


# Upload image to s3 bucket
def uploadImage(file, imageKey, contentType):
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
    try:
        s3_file = s3.get_object(Bucket=bucketName, Key=file_key)
        file_content = s3_file['Body'].read()  # Read the content of the file
        return True, file_content
    except Exception as e:
        return False, e
    
def download_s3_file(file_key, file_path):
    try:   
        # Download the file
        s3.download_file(bucketName, file_key, file_path)
        return True
    except Exception as e:
        return False

    
    


