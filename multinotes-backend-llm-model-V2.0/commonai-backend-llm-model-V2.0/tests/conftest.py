"""
Pytest configuration and fixtures for MultinotesAI tests.

This module provides:
- Common test fixtures
- Test utilities
- Mock factories
- Database setup/teardown
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def db_setup(db):
    """Ensure database is available for tests."""
    pass


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture
def user_factory(db):
    """Factory for creating test users."""
    def create_user(
        email=None,
        password="testpassword123",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_staff=False,
        is_email_verified=True,
        **kwargs
    ):
        if email is None:
            import uuid
            email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_staff=is_staff,
            **kwargs
        )

        if hasattr(user, 'is_email_verified'):
            user.is_email_verified = is_email_verified
            user.save()

        return user

    return create_user


@pytest.fixture
def user(user_factory):
    """Create a standard test user."""
    return user_factory()


@pytest.fixture
def admin_user(user_factory):
    """Create an admin test user."""
    return user_factory(
        email="admin@example.com",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def inactive_user(user_factory):
    """Create an inactive test user."""
    return user_factory(
        email="inactive@example.com",
        is_active=False
    )


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Create an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Create an admin authenticated API client."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def auth_tokens(user):
    """Get authentication tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


# =============================================================================
# Subscription Fixtures
# =============================================================================

@pytest.fixture
def plan_factory(db):
    """Factory for creating subscription plans."""
    def create_plan(
        name="Basic Plan",
        price=999,
        duration_days=30,
        text_tokens=10000,
        file_tokens=100,
        storage_mb=1024,
        is_active=True,
        **kwargs
    ):
        from planandsubscription.models import Plan

        plan = Plan.objects.create(
            name=name,
            price=price,
            duration_days=duration_days,
            textToken=text_tokens,
            fileToken=file_tokens,
            storageMB=storage_mb,
            is_active=is_active,
            is_delete=False,
            **kwargs
        )
        return plan

    return create_plan


@pytest.fixture
def subscription_factory(db, plan_factory):
    """Factory for creating subscriptions."""
    def create_subscription(
        user,
        plan=None,
        status='active',
        balance_token=1000,
        file_token=10,
        **kwargs
    ):
        from planandsubscription.models import Subscription

        if plan is None:
            plan = plan_factory()

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            status=status,
            balanceToken=balance_token,
            fileToken=file_token,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            is_delete=False,
            **kwargs
        )
        return subscription

    return create_subscription


@pytest.fixture
def free_plan(plan_factory):
    """Create a free tier plan."""
    return plan_factory(
        name="Free",
        price=0,
        text_tokens=100,
        file_tokens=5,
        storage_mb=100
    )


@pytest.fixture
def pro_plan(plan_factory):
    """Create a pro plan."""
    return plan_factory(
        name="Pro",
        price=1999,
        text_tokens=100000,
        file_tokens=500,
        storage_mb=10240
    )


# =============================================================================
# Content Fixtures
# =============================================================================

@pytest.fixture
def folder_factory(db):
    """Factory for creating folders."""
    def create_folder(
        user,
        name="Test Folder",
        parent=None,
        **kwargs
    ):
        from coreapp.models import Folder

        folder = Folder.objects.create(
            user=user,
            name=name,
            parent=parent,
            is_delete=False,
            **kwargs
        )
        return folder

    return create_folder


@pytest.fixture
def note_factory(db):
    """Factory for creating notes/content."""
    def create_note(
        user,
        title="Test Note",
        content="Test content",
        folder=None,
        **kwargs
    ):
        from coreapp.models import ContentGen

        note = ContentGen.objects.create(
            user=user,
            title=title,
            generatedResponse=content,
            folder=folder,
            is_delete=False,
            **kwargs
        )
        return note

    return create_note


# =============================================================================
# LLM Model Fixtures
# =============================================================================

@pytest.fixture
def llm_model_factory(db):
    """Factory for creating LLM models."""
    def create_llm_model(
        name="GPT-4",
        provider="openai",
        model_id="gpt-4",
        is_active=True,
        **kwargs
    ):
        from coreapp.models import LLMModel

        model = LLMModel.objects.create(
            name=name,
            provider=provider,
            model_id=model_id,
            is_active=is_active,
            is_delete=False,
            **kwargs
        )
        return model

    return create_llm_model


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "This is a test AI response."
    mock_response.choices[0].finish_reason = "stop"
    mock_response.model = "gpt-4"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30

    return mock_response


@pytest.fixture
def mock_razorpay_order():
    """Mock Razorpay order response."""
    return {
        'id': 'order_test123',
        'entity': 'order',
        'amount': 99900,
        'amount_paid': 0,
        'amount_due': 99900,
        'currency': 'INR',
        'receipt': 'receipt_test123',
        'status': 'created',
    }


@pytest.fixture
def mock_razorpay_payment():
    """Mock Razorpay payment response."""
    return {
        'id': 'pay_test123',
        'entity': 'payment',
        'amount': 99900,
        'currency': 'INR',
        'status': 'captured',
        'order_id': 'order_test123',
        'method': 'card',
    }


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis cache."""
    mock_cache = mocker.patch('django.core.cache.cache')
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    return mock_cache


@pytest.fixture
def mock_celery_task(mocker):
    """Mock Celery task execution."""
    def mock_delay(*args, **kwargs):
        return Mock(id='task-123')

    return mock_delay


@pytest.fixture
def mock_email(mocker):
    """Mock email sending."""
    return mocker.patch('django.core.mail.send_mail', return_value=1)


# =============================================================================
# Request Fixtures
# =============================================================================

@pytest.fixture
def json_content_type():
    """Return JSON content type header."""
    return 'application/json'


@pytest.fixture
def sample_note_data():
    """Sample data for creating a note."""
    return {
        'title': 'Test Note',
        'content': 'This is test content',
        'prompt': 'Generate a test response',
    }


@pytest.fixture
def sample_user_data():
    """Sample data for user registration."""
    return {
        'email': 'newuser@example.com',
        'password': 'SecurePass123!',
        'password_confirm': 'SecurePass123!',
        'first_name': 'New',
        'last_name': 'User',
    }


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def freeze_time(mocker):
    """Fixture to freeze time for testing."""
    from freezegun import freeze_time as ft
    return ft


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    def create_temp_file(content="Test content", filename="test.txt"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path

    return create_temp_file


@pytest.fixture
def temp_image(tmp_path):
    """Create a temporary image for testing."""
    def create_temp_image(size=(100, 100), format='PNG'):
        from PIL import Image
        import io

        img = Image.new('RGB', size, color='red')
        img_path = tmp_path / f"test_image.{format.lower()}"
        img.save(img_path, format)
        return img_path

    return create_temp_image


# =============================================================================
# Test Markers
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
