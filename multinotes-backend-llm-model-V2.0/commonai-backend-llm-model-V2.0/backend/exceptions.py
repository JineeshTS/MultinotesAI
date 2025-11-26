"""
Custom exception handlers and exception classes for MultinotesAI API.

This module provides standardized error responses across the application.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    Throttled,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCodes:
    """Centralized error codes for the application."""

    # Authentication Errors (AUTH_xxx)
    AUTH_INVALID_CREDENTIALS = 'AUTH_001'
    AUTH_EMAIL_EXISTS = 'AUTH_002'
    AUTH_USERNAME_EXISTS = 'AUTH_003'
    AUTH_USER_BLOCKED = 'AUTH_004'
    AUTH_USER_NOT_VERIFIED = 'AUTH_005'
    AUTH_INVALID_TOKEN = 'AUTH_006'
    AUTH_TOKEN_EXPIRED = 'AUTH_007'
    AUTH_PERMISSION_DENIED = 'AUTH_008'

    # Subscription Errors (SUB_xxx)
    SUB_INSUFFICIENT_TOKENS = 'SUB_001'
    SUB_EXPIRED = 'SUB_002'
    SUB_STORAGE_LIMIT = 'SUB_003'
    SUB_NOT_FOUND = 'SUB_004'
    SUB_ALREADY_ACTIVE = 'SUB_005'

    # LLM Errors (LLM_xxx)
    LLM_MODEL_NOT_FOUND = 'LLM_001'
    LLM_MODEL_DISCONNECTED = 'LLM_002'
    LLM_GENERATION_ERROR = 'LLM_003'
    LLM_RATE_LIMIT = 'LLM_004'
    LLM_INVALID_INPUT = 'LLM_005'

    # Payment Errors (PAY_xxx)
    PAY_INVALID_PAYMENT = 'PAY_001'
    PAY_FAILED = 'PAY_002'
    PAY_INVALID_COUPON = 'PAY_003'
    PAY_COUPON_EXPIRED = 'PAY_004'
    PAY_ORDER_NOT_FOUND = 'PAY_005'
    PAY_SIGNATURE_INVALID = 'PAY_006'

    # Resource Errors (RES_xxx)
    RES_NOT_FOUND = 'RES_001'
    RES_ALREADY_EXISTS = 'RES_002'
    RES_INVALID_DATA = 'RES_003'
    RES_FILE_TOO_LARGE = 'RES_004'
    RES_INVALID_FILE_TYPE = 'RES_005'

    # Server Errors (SRV_xxx)
    SRV_INTERNAL_ERROR = 'SRV_001'
    SRV_SERVICE_UNAVAILABLE = 'SRV_002'
    SRV_RATE_LIMITED = 'SRV_003'


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class BaseAPIException(APIException):
    """Base exception class for all custom API exceptions."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred.'
    default_code = 'error'
    error_code = None

    def __init__(self, detail=None, code=None, error_code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if error_code is None:
            error_code = self.error_code

        self.error_code = error_code
        super().__init__(detail, code)


class InvalidCredentialsError(BaseAPIException):
    """Raised when login credentials are invalid."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid email or password.'
    default_code = 'invalid_credentials'
    error_code = ErrorCodes.AUTH_INVALID_CREDENTIALS


class UserBlockedError(BaseAPIException):
    """Raised when a blocked user tries to access the system."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Your account has been blocked. Please contact support.'
    default_code = 'user_blocked'
    error_code = ErrorCodes.AUTH_USER_BLOCKED


class UserNotVerifiedError(BaseAPIException):
    """Raised when an unverified user tries to login."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Please verify your email before logging in.'
    default_code = 'user_not_verified'
    error_code = ErrorCodes.AUTH_USER_NOT_VERIFIED


class InsufficientTokensError(BaseAPIException):
    """Raised when user doesn't have enough tokens."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Insufficient tokens. Please upgrade your subscription.'
    default_code = 'insufficient_tokens'
    error_code = ErrorCodes.SUB_INSUFFICIENT_TOKENS


class SubscriptionExpiredError(BaseAPIException):
    """Raised when user's subscription has expired."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Your subscription has expired. Please renew to continue.'
    default_code = 'subscription_expired'
    error_code = ErrorCodes.SUB_EXPIRED


class StorageLimitExceededError(BaseAPIException):
    """Raised when user exceeds storage limit."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Storage limit exceeded. Please upgrade your plan.'
    default_code = 'storage_limit_exceeded'
    error_code = ErrorCodes.SUB_STORAGE_LIMIT


class LLMModelNotFoundError(BaseAPIException):
    """Raised when requested LLM model is not found."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'The requested AI model is not available.'
    default_code = 'model_not_found'
    error_code = ErrorCodes.LLM_MODEL_NOT_FOUND


class LLMModelDisconnectedError(BaseAPIException):
    """Raised when LLM model is not connected."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'The AI model is currently unavailable. Please try again later.'
    default_code = 'model_disconnected'
    error_code = ErrorCodes.LLM_MODEL_DISCONNECTED


class LLMGenerationError(BaseAPIException):
    """Raised when LLM generation fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An error occurred during content generation.'
    default_code = 'generation_error'
    error_code = ErrorCodes.LLM_GENERATION_ERROR


class PaymentFailedError(BaseAPIException):
    """Raised when payment processing fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Payment processing failed. Please try again.'
    default_code = 'payment_failed'
    error_code = ErrorCodes.PAY_FAILED


class InvalidCouponError(BaseAPIException):
    """Raised when coupon code is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid or expired coupon code.'
    default_code = 'invalid_coupon'
    error_code = ErrorCodes.PAY_INVALID_COUPON


class InvalidSignatureError(BaseAPIException):
    """Raised when payment signature verification fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Payment verification failed. Invalid signature.'
    default_code = 'invalid_signature'
    error_code = ErrorCodes.PAY_SIGNATURE_INVALID


class FileTooLargeError(BaseAPIException):
    """Raised when uploaded file exceeds size limit."""
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'File size exceeds the maximum allowed limit.'
    default_code = 'file_too_large'
    error_code = ErrorCodes.RES_FILE_TOO_LARGE


class InvalidFileTypeError(BaseAPIException):
    """Raised when file type is not supported."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'File type is not supported.'
    default_code = 'invalid_file_type'
    error_code = ErrorCodes.RES_INVALID_FILE_TYPE


# =============================================================================
# CUSTOM EXCEPTION HANDLER
# =============================================================================

def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides standardized error responses.

    Response format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {} or []  # Optional additional details
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Get request info for logging
    request = context.get('request')
    view = context.get('view')

    # Log the exception
    if response is not None and response.status_code >= 500:
        logger.error(
            f"Server error: {exc.__class__.__name__} - {str(exc)}",
            exc_info=True,
            extra={
                'request_path': request.path if request else None,
                'request_method': request.method if request else None,
                'view': view.__class__.__name__ if view else None,
            }
        )
    elif response is not None and response.status_code >= 400:
        logger.warning(
            f"Client error: {exc.__class__.__name__} - {str(exc)}",
            extra={
                'request_path': request.path if request else None,
                'request_method': request.method if request else None,
            }
        )

    # Handle custom API exceptions
    if isinstance(exc, BaseAPIException):
        return Response({
            'success': False,
            'error': {
                'code': exc.error_code,
                'message': str(exc.detail),
            }
        }, status=exc.status_code)

    # Handle DRF exceptions
    if response is not None:
        error_response = {
            'success': False,
            'error': {
                'code': get_error_code(exc),
                'message': get_error_message(exc, response),
            }
        }

        # Add details for validation errors
        if isinstance(exc, ValidationError):
            error_response['error']['details'] = response.data

        response.data = error_response
        return response

    # Handle Django exceptions not caught by DRF
    if isinstance(exc, DjangoValidationError):
        return Response({
            'success': False,
            'error': {
                'code': ErrorCodes.RES_INVALID_DATA,
                'message': 'Validation error.',
                'details': exc.messages if hasattr(exc, 'messages') else [str(exc)],
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, Http404):
        return Response({
            'success': False,
            'error': {
                'code': ErrorCodes.RES_NOT_FOUND,
                'message': 'Resource not found.',
            }
        }, status=status.HTTP_404_NOT_FOUND)

    # Unhandled exceptions - log and return generic error
    logger.exception(f"Unhandled exception: {exc}")
    return Response({
        'success': False,
        'error': {
            'code': ErrorCodes.SRV_INTERNAL_ERROR,
            'message': 'An unexpected error occurred. Please try again later.',
        }
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_error_code(exc):
    """Get appropriate error code for the exception."""
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return ErrorCodes.AUTH_INVALID_TOKEN
    elif isinstance(exc, PermissionDenied):
        return ErrorCodes.AUTH_PERMISSION_DENIED
    elif isinstance(exc, NotFound):
        return ErrorCodes.RES_NOT_FOUND
    elif isinstance(exc, ValidationError):
        return ErrorCodes.RES_INVALID_DATA
    elif isinstance(exc, Throttled):
        return ErrorCodes.SRV_RATE_LIMITED
    elif isinstance(exc, MethodNotAllowed):
        return ErrorCodes.RES_INVALID_DATA
    else:
        return ErrorCodes.SRV_INTERNAL_ERROR


def get_error_message(exc, response):
    """Get human-readable error message."""
    if isinstance(exc, NotAuthenticated):
        return 'Authentication credentials were not provided.'
    elif isinstance(exc, AuthenticationFailed):
        return 'Invalid or expired authentication token.'
    elif isinstance(exc, PermissionDenied):
        return 'You do not have permission to perform this action.'
    elif isinstance(exc, NotFound):
        return 'The requested resource was not found.'
    elif isinstance(exc, Throttled):
        wait = exc.wait
        return f'Request was throttled. Please wait {int(wait)} seconds.'
    elif isinstance(exc, ValidationError):
        return 'Invalid data provided.'
    elif isinstance(exc, MethodNotAllowed):
        return f'Method "{exc.detail}" is not allowed.'
    else:
        # Try to get detail from exception
        if hasattr(exc, 'detail'):
            detail = exc.detail
            if isinstance(detail, str):
                return detail
            elif isinstance(detail, dict):
                # Get first error message
                for key, value in detail.items():
                    if isinstance(value, list) and value:
                        return f"{key}: {value[0]}"
                    elif isinstance(value, str):
                        return f"{key}: {value}"
        return 'An error occurred.'


# =============================================================================
# SUCCESS RESPONSE HELPER
# =============================================================================

def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    """
    Helper function to create standardized success responses.

    Response format:
    {
        "success": true,
        "message": "Optional message",  # Only if provided
        "data": {}  # The actual response data
    }
    """
    response = {
        'success': True,
    }

    if message:
        response['message'] = message

    if data is not None:
        response['data'] = data

    return Response(response, status=status_code)
