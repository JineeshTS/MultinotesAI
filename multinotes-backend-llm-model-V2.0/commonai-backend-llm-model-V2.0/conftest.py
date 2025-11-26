"""
Pytest configuration and fixtures for MultinotesAI tests.

This module provides shared fixtures used across all test modules:
- Database fixtures (users, subscriptions, plans)
- API client fixtures
- Mock fixtures for external services
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Import models
from authentication.models import CustomUser, Role, Cluster, Referral, ReferralSetting
from planandsubscription.models import UserPlan, Subscription, Transaction
from coreapp.models import LLM, Prompt, PromptResponse, Folder, Document, GroupResponse
from ticketandcategory.models import MainCategory, Category, Coupon


# =============================================================================
# USER FIXTURES
# =============================================================================

@pytest.fixture
def user_password():
    """Default password for test users."""
    return 'TestPass123!'


@pytest.fixture
def create_user(db, user_password):
    """Factory fixture to create users."""
    def _create_user(
        email='testuser@example.com',
        username='testuser',
        password=None,
        is_verified=True,
        is_blocked=False,
        **kwargs
    ):
        User = get_user_model()
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password or user_password,
            is_verified=is_verified,
            is_blocked=is_blocked,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def user(create_user):
    """Create a standard test user."""
    return create_user()


@pytest.fixture
def admin_user(create_user, db):
    """Create an admin user."""
    user = create_user(
        email='admin@example.com',
        username='admin',
        is_staff=True,
        is_superuser=True
    )
    # Add admin role
    admin_role, _ = Role.objects.get_or_create(name='admin')
    user.roles.add(admin_role)
    return user


@pytest.fixture
def enterprise_user(create_user, db, cluster):
    """Create an enterprise user with cluster."""
    user = create_user(
        email='enterprise@example.com',
        username='enterprise_user',
        cluster=cluster
    )
    enterprise_role, _ = Role.objects.get_or_create(name='enterprise_user')
    user.roles.add(enterprise_role)
    return user


# =============================================================================
# AUTHENTICATION FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    """Create an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Create an authenticated admin API client."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


# =============================================================================
# CLUSTER FIXTURES
# =============================================================================

@pytest.fixture
def cluster(db):
    """Create a test cluster."""
    return Cluster.objects.create(
        cluster_name='Test Company',
        org_name='Test Company Inc.',
        email='cluster@testcompany.com',
        domain='testcompany.com',
        is_active=True
    )


# =============================================================================
# PLAN & SUBSCRIPTION FIXTURES
# =============================================================================

@pytest.fixture
def free_plan(db):
    """Create a free plan."""
    return UserPlan.objects.create(
        plan_name='Free Plan',
        description='Free trial plan',
        amount=0,
        duration=30,
        totalToken=1000,
        fileToken=10,
        storage_size=1024 * 1024 * 100,  # 100 MB
        is_free=True,
        plan_for='token',
        status='active'
    )


@pytest.fixture
def paid_plan(db):
    """Create a paid plan."""
    return UserPlan.objects.create(
        plan_name='Pro Plan',
        description='Professional plan with more tokens',
        amount=999.00,
        duration=30,
        totalToken=50000,
        fileToken=100,
        storage_size=1024 * 1024 * 1024 * 5,  # 5 GB
        is_free=False,
        plan_for='token',
        status='active'
    )


@pytest.fixture
def storage_plan(db):
    """Create a storage plan."""
    return UserPlan.objects.create(
        plan_name='Storage Plan',
        description='Additional storage',
        amount=299.00,
        duration=30,
        storage_size=1024 * 1024 * 1024 * 10,  # 10 GB
        is_free=False,
        plan_for='storage',
        status='active'
    )


@pytest.fixture
def user_subscription(db, user, free_plan):
    """Create a subscription for the test user."""
    return Subscription.objects.create(
        user=user,
        plan=free_plan,
        status='active',
        subscriptionExpiryDate=timezone.now() + timedelta(days=30),
        subscriptionEndDate=timezone.now() + timedelta(days=37),
        balanceToken=free_plan.totalToken,
        fileToken=free_plan.fileToken,
        payment_status='paid',
        payment_mode='online',
        plan_name=free_plan.plan_name,
        plan_for=free_plan.plan_for,
        amount=free_plan.amount,
        duration=free_plan.duration,
        totalToken=free_plan.totalToken,
        totalFileToken=free_plan.fileToken
    )


@pytest.fixture
def expired_subscription(db, user, free_plan):
    """Create an expired subscription."""
    return Subscription.objects.create(
        user=user,
        plan=free_plan,
        status='expire',
        subscriptionExpiryDate=timezone.now() - timedelta(days=10),
        subscriptionEndDate=timezone.now() - timedelta(days=3),
        balanceToken=0,
        fileToken=0,
        expireToken=500,
        payment_status='paid',
        payment_mode='online',
        plan_name=free_plan.plan_name,
        plan_for=free_plan.plan_for,
        amount=free_plan.amount,
        duration=free_plan.duration,
        totalToken=free_plan.totalToken,
        totalFileToken=free_plan.fileToken
    )


# =============================================================================
# LLM FIXTURES
# =============================================================================

@pytest.fixture
def llm_together(db):
    """Create a Together AI LLM model."""
    return LLM.objects.create(
        name='Llama-3-70B',
        description='Meta Llama 3 70B model',
        api_key='test_api_key',
        model_string='meta-llama/Llama-3-70b-chat-hf',
        source=2,  # Together
        is_enabled=True,
        test_status='connected',
        text=True,
        code=True
    )


@pytest.fixture
def llm_gemini(db):
    """Create a Gemini LLM model."""
    return LLM.objects.create(
        name='Gemini Pro',
        description='Google Gemini Pro model',
        api_key='test_api_key',
        model_string='gemini-pro',
        source=3,  # Gemini
        is_enabled=True,
        test_status='connected',
        text=True,
        image_to_text=True,
        video_to_text=True
    )


@pytest.fixture
def llm_openai(db):
    """Create an OpenAI LLM model."""
    return LLM.objects.create(
        name='GPT-4',
        description='OpenAI GPT-4 model',
        api_key='test_api_key',
        model_string='gpt-4',
        source=4,  # OpenAI
        is_enabled=True,
        test_status='connected',
        text=True,
        text_to_image=True,
        text_to_audio=True,
        audio_to_text=True
    )


@pytest.fixture
def disabled_llm(db):
    """Create a disabled LLM model."""
    return LLM.objects.create(
        name='Disabled Model',
        description='A disabled model',
        api_key='test_api_key',
        model_string='disabled-model',
        source=2,
        is_enabled=False,
        test_status='disconnected',
        text=True
    )


# =============================================================================
# CATEGORY FIXTURES
# =============================================================================

@pytest.fixture
def main_category(db):
    """Create a main category."""
    return MainCategory.objects.create(
        name='Content Generation',
        description='AI content generation features',
        status='active',
        can_delete=False
    )


@pytest.fixture
def category(db, main_category):
    """Create a category."""
    return Category.objects.create(
        mainCategory=main_category,
        name='Text Generation',
        description='Generate text content',
        alias_name='text-generation',
        status='active'
    )


# =============================================================================
# CONTENT FIXTURES
# =============================================================================

@pytest.fixture
def folder(db, user):
    """Create a folder."""
    return Folder.objects.create(
        title='Test Folder',
        user=user,
        is_active=True
    )


@pytest.fixture
def prompt(db, user, category):
    """Create a prompt."""
    return Prompt.objects.create(
        user=user,
        prompt_text='Write a story about a robot',
        category=category,
        response_type=2,
        title='Test Prompt'
    )


@pytest.fixture
def prompt_response(db, user, prompt, llm_together, category):
    """Create a prompt response."""
    return PromptResponse.objects.create(
        user=user,
        llm=llm_together,
        prompt=prompt,
        response_text='Once upon a time, there was a robot...',
        response_type=2,
        category=category,
        tokenUsed=100
    )


@pytest.fixture
def group_response(db, user, category, llm_together):
    """Create a conversation group."""
    return GroupResponse.objects.create(
        user=user,
        category=category,
        llm=llm_together,
        group_name='Test Conversation'
    )


# =============================================================================
# COUPON FIXTURES
# =============================================================================

@pytest.fixture
def percentage_coupon(db):
    """Create a percentage discount coupon."""
    return Coupon.objects.create(
        coupon_name='20% Off',
        coupon_code='SAVE20',
        coupon_type='percentage',
        discount_value=20,
        max_discount_amount=500,
        min_order_amount=100,
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True
    )


@pytest.fixture
def fixed_coupon(db):
    """Create a fixed amount coupon."""
    return Coupon.objects.create(
        coupon_name='₹100 Off',
        coupon_code='FLAT100',
        coupon_type='fixed',
        discount_value=100,
        min_order_amount=500,
        bonus_token=50,
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True
    )


@pytest.fixture
def expired_coupon(db):
    """Create an expired coupon."""
    return Coupon.objects.create(
        coupon_name='Expired Coupon',
        coupon_code='EXPIRED',
        coupon_type='percentage',
        discount_value=10,
        start_date=timezone.now() - timedelta(days=30),
        end_date=timezone.now() - timedelta(days=1),
        is_active=True
    )


# =============================================================================
# TRANSACTION FIXTURES
# =============================================================================

@pytest.fixture
def transaction(db, user, paid_plan):
    """Create a transaction."""
    return Transaction.objects.create(
        user=user,
        transactionId='order_test123',
        amount=paid_plan.amount,
        plan_name=paid_plan.plan_name,
        duration=paid_plan.duration,
        tokenCount=paid_plan.totalToken,
        fileToken=paid_plan.fileToken,
        payment_status='paid',
        payment_method='razorpay'
    )


@pytest.fixture
def pending_transaction(db, user, paid_plan):
    """Create a pending transaction."""
    return Transaction.objects.create(
        user=user,
        transactionId='order_pending123',
        amount=paid_plan.amount,
        plan_name=paid_plan.plan_name,
        duration=paid_plan.duration,
        tokenCount=paid_plan.totalToken,
        fileToken=paid_plan.fileToken,
        payment_status='pending',
        payment_method='razorpay'
    )


# =============================================================================
# REFERRAL FIXTURES
# =============================================================================

@pytest.fixture
def referral_setting(db):
    """Create referral settings."""
    return ReferralSetting.objects.create(
        isToken=True,
        refer_by_token=100,
        refer_to_token=50,
        isFirstPayment=True
    )


@pytest.fixture
def referral(db, user, create_user, referral_setting):
    """Create a referral relationship."""
    referred_user = create_user(
        email='referred@example.com',
        username='referred_user'
    )
    return Referral.objects.create(
        referr_by=user,
        referr_to=referred_user,
        refer_by_token=referral_setting.refer_by_token,
        refer_to_token=referral_setting.refer_to_token,
        reward_given=False
    )


# =============================================================================
# MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_razorpay(mocker):
    """Mock Razorpay client."""
    mock_client = mocker.MagicMock()

    # Mock order creation
    mock_client.order.create.return_value = {
        'id': 'order_test123',
        'amount': 99900,
        'currency': 'INR',
        'status': 'created'
    }

    # Mock payment fetch
    mock_client.payment.fetch.return_value = {
        'id': 'pay_test123',
        'order_id': 'order_test123',
        'amount': 99900,
        'status': 'captured',
        'method': 'upi'
    }

    # Mock utility for signature verification
    mock_client.utility.verify_payment_signature.return_value = True

    mocker.patch(
        'planandsubscription.razorpay_service.get_razorpay_client',
        return_value=mock_client
    )

    return mock_client


@pytest.fixture
def mock_s3_upload(mocker):
    """Mock S3 upload function."""
    return mocker.patch(
        'authentication.awsservice.uploadImage',
        return_value='multinote/test/test_file.png'
    )


@pytest.fixture
def mock_llm_generation(mocker):
    """Mock LLM generation functions."""
    def mock_generator(*args, **kwargs):
        yield 'data: {"text": "Generated "}\n\n'
        yield 'data: {"text": "content "}\n\n'
        yield 'data: {"text": "here."}\n\n'
        yield 'data: [DONE]\n\n'

    mocker.patch(
        'coreapp.utils.generateTextToTextUsingTogether',
        side_effect=mock_generator
    )
    mocker.patch(
        'coreapp.utils.textToTextUsingGemini',
        side_effect=mock_generator
    )
    mocker.patch(
        'coreapp.utils.generateTextByOpenAI',
        side_effect=mock_generator
    )

    return mock_generator
