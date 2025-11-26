"""
Storage Service for MultinotesAI.

This module provides unified file storage operations supporting:
- Local file storage
- AWS S3 storage
- File validation and processing
"""

import os
import uuid
import hashlib
import mimetypes
import logging
from typing import Optional, Tuple, BinaryIO
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


# =============================================================================
# Storage Configuration
# =============================================================================

class StorageConfig:
    """Storage configuration settings."""

    # File size limits (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 25 * 1024 * 1024  # 25MB

    # Allowed file types
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    ALLOWED_DOCUMENT_TYPES = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
    ]
    ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg']

    # Storage paths
    USER_UPLOADS_PATH = 'uploads/users/{user_id}/{year}/{month}/'
    TEMP_PATH = 'temp/'
    EXPORTS_PATH = 'exports/{user_id}/'


# =============================================================================
# File Validator
# =============================================================================

class FileValidator:
    """Validate uploaded files."""

    @staticmethod
    def validate_file(
        file,
        max_size: int = None,
        allowed_types: list = None
    ) -> Tuple[bool, str]:
        """
        Validate an uploaded file.

        Args:
            file: File object
            max_size: Maximum file size in bytes
            allowed_types: List of allowed MIME types

        Returns:
            Tuple of (is_valid, error_message)
        """
        max_size = max_size or StorageConfig.MAX_FILE_SIZE

        # Check file size
        if hasattr(file, 'size'):
            if file.size > max_size:
                return False, f"File size exceeds {max_size // (1024 * 1024)}MB limit"

        # Check file type
        if allowed_types:
            content_type = getattr(file, 'content_type', None)
            if content_type and content_type not in allowed_types:
                return False, f"File type '{content_type}' is not allowed"

        return True, ""

    @staticmethod
    def validate_image(file) -> Tuple[bool, str]:
        """Validate an image file."""
        return FileValidator.validate_file(
            file,
            max_size=StorageConfig.MAX_IMAGE_SIZE,
            allowed_types=StorageConfig.ALLOWED_IMAGE_TYPES
        )

    @staticmethod
    def validate_document(file) -> Tuple[bool, str]:
        """Validate a document file."""
        return FileValidator.validate_file(
            file,
            max_size=StorageConfig.MAX_DOCUMENT_SIZE,
            allowed_types=StorageConfig.ALLOWED_DOCUMENT_TYPES
        )


# =============================================================================
# Storage Service
# =============================================================================

class StorageService:
    """
    Unified storage service for file operations.

    Usage:
        service = StorageService()
        url = service.save_file(file, user_id=123, category='images')
        service.delete_file(url)
    """

    def __init__(self):
        self.storage = default_storage
        self.config = StorageConfig

    def save_file(
        self,
        file,
        user_id: int,
        category: str = 'files',
        custom_name: str = None,
        validate: bool = True
    ) -> Optional[str]:
        """
        Save a file to storage.

        Args:
            file: File object to save
            user_id: User ID for path organization
            category: File category (images, documents, etc.)
            custom_name: Custom filename (optional)
            validate: Whether to validate the file

        Returns:
            File URL or path, None on failure
        """
        try:
            # Validate file
            if validate:
                is_valid, error = FileValidator.validate_file(file)
                if not is_valid:
                    logger.warning(f"File validation failed: {error}")
                    return None

            # Generate filename
            filename = self._generate_filename(file, custom_name)

            # Generate path
            path = self._generate_path(user_id, category, filename)

            # Save file
            saved_path = self.storage.save(path, file)

            logger.info(f"File saved: {saved_path}")
            return saved_path

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return None

    def save_content(
        self,
        content: bytes,
        filename: str,
        user_id: int,
        category: str = 'files'
    ) -> Optional[str]:
        """
        Save content bytes to storage.

        Args:
            content: File content as bytes
            filename: Filename
            user_id: User ID
            category: File category

        Returns:
            File URL or path, None on failure
        """
        try:
            path = self._generate_path(user_id, category, filename)
            saved_path = self.storage.save(path, ContentFile(content))

            logger.info(f"Content saved: {saved_path}")
            return saved_path

        except Exception as e:
            logger.error(f"Error saving content: {e}")
            return None

    def get_file(self, path: str) -> Optional[BinaryIO]:
        """
        Get a file from storage.

        Args:
            path: File path

        Returns:
            File object or None
        """
        try:
            if self.storage.exists(path):
                return self.storage.open(path, 'rb')
            return None
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return None

    def get_url(self, path: str) -> Optional[str]:
        """
        Get the URL for a file.

        Args:
            path: File path

        Returns:
            File URL or None
        """
        try:
            if self.storage.exists(path):
                return self.storage.url(path)
            return None
        except Exception as e:
            logger.error(f"Error getting URL: {e}")
            return None

    def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: File path

        Returns:
            True if successful
        """
        try:
            if self.storage.exists(path):
                self.storage.delete(path)
                logger.info(f"File deleted: {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        try:
            return self.storage.exists(path)
        except Exception:
            return False

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            if self.storage.exists(path):
                return self.storage.size(path)
            return 0
        except Exception:
            return 0

    def get_user_storage_usage(self, user_id: int) -> int:
        """
        Calculate total storage used by a user.

        Args:
            user_id: User ID

        Returns:
            Total bytes used
        """
        total_size = 0
        base_path = f"uploads/users/{user_id}/"

        try:
            # This works for local storage, may need adaptation for S3
            directories, files = self.storage.listdir(base_path)
            for filename in files:
                total_size += self.get_file_size(os.path.join(base_path, filename))

            # Recursively check subdirectories
            for directory in directories:
                dir_path = os.path.join(base_path, directory)
                total_size += self._get_directory_size(dir_path)

        except Exception as e:
            logger.error(f"Error calculating storage usage: {e}")

        return total_size

    def _get_directory_size(self, path: str) -> int:
        """Recursively calculate directory size."""
        total_size = 0
        try:
            directories, files = self.storage.listdir(path)
            for filename in files:
                total_size += self.get_file_size(os.path.join(path, filename))
            for directory in directories:
                total_size += self._get_directory_size(os.path.join(path, directory))
        except Exception:
            pass
        return total_size

    def _generate_filename(self, file, custom_name: str = None) -> str:
        """Generate a unique filename."""
        if custom_name:
            return custom_name

        # Get original extension
        original_name = getattr(file, 'name', 'file')
        ext = os.path.splitext(original_name)[1].lower()

        # Generate unique name
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return f"{timestamp}_{unique_id}{ext}"

    def _generate_path(self, user_id: int, category: str, filename: str) -> str:
        """Generate storage path."""
        now = datetime.now()
        path = self.config.USER_UPLOADS_PATH.format(
            user_id=user_id,
            year=now.year,
            month=f"{now.month:02d}"
        )
        return os.path.join(path, category, filename)

    def generate_download_url(self, path: str, expiry_seconds: int = 3600) -> Optional[str]:
        """
        Generate a temporary download URL (for S3).

        Args:
            path: File path
            expiry_seconds: URL expiry time

        Returns:
            Temporary URL or None
        """
        try:
            # For S3 storage with boto3
            if hasattr(self.storage, 'bucket'):
                import boto3
                s3_client = boto3.client('s3')
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Key': path,
                    },
                    ExpiresIn=expiry_seconds
                )
                return url

            # For local storage, return regular URL
            return self.get_url(path)

        except Exception as e:
            logger.error(f"Error generating download URL: {e}")
            return None


# =============================================================================
# File Hash Service
# =============================================================================

class FileHashService:
    """Service for file hashing and deduplication."""

    @staticmethod
    def calculate_hash(file) -> str:
        """Calculate SHA-256 hash of file content."""
        hasher = hashlib.sha256()

        # Reset file position
        file.seek(0)

        for chunk in iter(lambda: file.read(8192), b''):
            hasher.update(chunk)

        # Reset file position for subsequent reads
        file.seek(0)

        return hasher.hexdigest()

    @staticmethod
    def get_content_type(filename: str) -> str:
        """Get MIME type from filename."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'


# =============================================================================
# Singleton Instance
# =============================================================================

storage_service = StorageService()
file_hash_service = FileHashService()
