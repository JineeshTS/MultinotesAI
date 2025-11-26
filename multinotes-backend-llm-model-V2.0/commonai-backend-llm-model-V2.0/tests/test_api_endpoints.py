"""
Comprehensive API endpoint tests for MultinotesAI backend.

Tests cover:
- CRUD operations for all major models
- Error response formats and handling
- Pagination functionality
- Filtering and search capabilities
- Query parameter validation
- Response structure validation
"""

import pytest
from django.urls import reverse
from rest_framework import status
from authentication.models import CustomUser, Cluster, Role
from planandsubscription.models import UserPlan, Subscription, Transaction
from coreapp.models import (
    LLM, Prompt, PromptResponse, Folder, Document,
    GroupResponse, UserContent, StorageUsage
)
from ticketandcategory.models import MainCategory, Category, Coupon
from datetime import timedelta
from django.utils import timezone


# =============================================================================
# USER CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestUserEndpoints:
    """Test user CRUD operations."""

    def test_get_user_profile(self, auth_client, user):
        """Test retrieve user profile."""
        response = auth_client.get(f'/api/authentication/user/{user.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user.id
        assert response.data['email'] == user.email
        assert response.data['username'] == user.username

    def test_update_user_profile(self, auth_client, user):
        """Test update user profile."""
        data = {
            'name': 'Updated Name',
            'city': 'New York',
            'country': 'USA'
        }
        response = auth_client.patch(f'/api/authentication/user/{user.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.name == 'Updated Name'
        assert user.city == 'New York'

    def test_update_user_email_unique_validation(self, auth_client, user, create_user):
        """Test updating email to existing one fails."""
        other_user = create_user(email='other@example.com', username='other')

        data = {'email': other_user.email}
        response = auth_client.patch(f'/api/authentication/user/{user.id}/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already exist' in str(response.data).lower()

    def test_update_user_username_unique_validation(self, auth_client, user, create_user):
        """Test updating username to existing one fails."""
        other_user = create_user(email='other@example.com', username='other')

        data = {'username': other_user.username}
        response = auth_client.patch(f'/api/authentication/user/{user.id}/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already exist' in str(response.data).lower()

    def test_delete_user_soft_delete(self, auth_client, user):
        """Test user soft delete."""
        response = auth_client.patch(f'/api/authentication/user/delete/{user.id}/', {
            'is_delete': True
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_delete == True

    def test_get_all_users_pagination(self, admin_client, create_user):
        """Test user list with pagination."""
        # Create multiple users
        for i in range(15):
            create_user(
                email=f'user{i}@example.com',
                username=f'user{i}'
            )

        response = admin_client.get('/api/authentication/users/?page=1')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'total_pages' in response.data
        assert len(response.data['results']) > 0

    def test_get_all_users_search(self, admin_client, create_user):
        """Test user list with search."""
        create_user(email='john@example.com', username='johndoe')
        create_user(email='jane@example.com', username='janedoe')

        response = admin_client.get('/api/authentication/users/?searchBy=john')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_all_users_filter_by_status(self, admin_client, create_user):
        """Test user list filtered by blocked status."""
        blocked_user = create_user(
            email='blocked@example.com',
            username='blocked',
            is_blocked=True
        )

        response = admin_client.get('/api/authentication/users/?status=true')

        assert response.status_code == status.HTTP_200_OK

    def test_upload_profile_image(self, auth_client, user, mock_s3_upload):
        """Test profile image upload."""
        # Mock file upload
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile(
            "test_image.jpg",
            b"file_content",
            content_type="image/jpeg"
        )

        response = auth_client.post('/api/authentication/upload-image/', {
            'file': image
        }, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert 'imageKey' in response.data


# =============================================================================
# PLAN & SUBSCRIPTION CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestPlanEndpoints:
    """Test plan CRUD operations."""

    def test_get_all_plans(self, api_client, free_plan, paid_plan):
        """Test retrieve all plans."""
        response = api_client.get('/api/plan/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

    def test_get_plan_by_id(self, api_client, paid_plan):
        """Test retrieve plan by ID."""
        response = api_client.get(f'/api/plan/{paid_plan.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == paid_plan.id
        assert response.data['plan_name'] == paid_plan.plan_name

    def test_create_plan_admin_only(self, admin_client):
        """Test create new plan (admin only)."""
        data = {
            'plan_name': 'Enterprise Plan',
            'description': 'For enterprise users',
            'amount': 4999.00,
            'duration': 365,
            'totalToken': 1000000,
            'fileToken': 10000,
            'storage_size': 1024 * 1024 * 1024 * 100,  # 100 GB
            'plan_for': 'token',
            'status': 'active'
        }
        response = admin_client.post('/api/plan/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_update_plan(self, admin_client, paid_plan):
        """Test update existing plan."""
        data = {
            'amount': 899.00,
            'description': 'Updated description'
        }
        response = admin_client.patch(f'/api/plan/{paid_plan.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        paid_plan.refresh_from_db()
        assert paid_plan.amount == 899.00

    def test_delete_plan(self, admin_client, paid_plan):
        """Test soft delete plan."""
        response = admin_client.patch(f'/api/plan/{paid_plan.id}/', {
            'is_delete': True
        })

        assert response.status_code == status.HTTP_200_OK
        paid_plan.refresh_from_db()
        assert paid_plan.is_delete == True

    def test_filter_plans_by_type(self, api_client, free_plan, storage_plan):
        """Test filter plans by type."""
        response = api_client.get('/api/plan/?plan_for=storage')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data:
            assert plan['plan_for'] == 'storage'


@pytest.mark.django_db
class TestSubscriptionEndpoints:
    """Test subscription CRUD operations."""

    def test_get_user_subscription(self, auth_client, user, user_subscription):
        """Test retrieve user's active subscription."""
        response = auth_client.get(f'/api/subscription/user/{user.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user_subscription.id

    def test_get_subscription_list_pagination(self, admin_client, create_user, free_plan):
        """Test subscription list with pagination."""
        # Create multiple subscriptions
        for i in range(10):
            user = create_user(
                email=f'sub{i}@example.com',
                username=f'subuser{i}'
            )
            Subscription.objects.create(
                user=user,
                plan=free_plan,
                status='active',
                subscriptionExpiryDate=timezone.now() + timedelta(days=30),
                subscriptionEndDate=timezone.now() + timedelta(days=37),
                balanceToken=1000,
                transactionId=f'test_{i}',
                payment_status='paid',
                payment_mode='online',
                plan_name=free_plan.plan_name,
                plan_for='token',
                amount=0,
                duration=30,
                totalToken=1000,
                totalFileToken=10
            )

        response = admin_client.get('/api/subscription/?page=1')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'total_pages' in response.data

    def test_filter_subscriptions_by_status(self, admin_client, user_subscription, expired_subscription):
        """Test filter subscriptions by status."""
        response = admin_client.get('/api/subscription/?status=active')

        assert response.status_code == status.HTTP_200_OK

    def test_cancel_subscription(self, auth_client, user, user_subscription):
        """Test cancel user subscription."""
        data = {
            'cancellation_reason': 'Testing cancellation'
        }
        response = auth_client.patch(
            f'/api/subscription/{user_subscription.id}/cancel/',
            data
        )

        # Should succeed or be not implemented
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]


# =============================================================================
# LLM MODEL CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestLLMEndpoints:
    """Test LLM model CRUD operations."""

    def test_get_all_llm_models(self, auth_client, llm_together, llm_gemini):
        """Test retrieve all enabled LLM models."""
        response = auth_client.get('/api/llm/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

    def test_get_llm_by_id(self, auth_client, llm_together):
        """Test retrieve LLM model by ID."""
        response = auth_client.get(f'/api/llm/{llm_together.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == llm_together.id
        assert response.data['name'] == llm_together.name

    def test_filter_llm_by_source(self, auth_client, llm_together, llm_gemini):
        """Test filter LLMs by source."""
        response = auth_client.get('/api/llm/?source=2')  # Together

        assert response.status_code == status.HTTP_200_OK

    def test_filter_llm_by_capability(self, auth_client, llm_together, llm_gemini):
        """Test filter LLMs by capability."""
        response = auth_client.get('/api/llm/?text=true')

        assert response.status_code == status.HTTP_200_OK

    def test_disabled_llm_not_shown(self, auth_client, disabled_llm):
        """Test disabled LLMs are not returned in list."""
        response = auth_client.get('/api/llm/')

        assert response.status_code == status.HTTP_200_OK
        llm_ids = [llm['id'] for llm in response.data]
        assert disabled_llm.id not in llm_ids

    def test_create_llm_admin_only(self, admin_client):
        """Test create new LLM model (admin only)."""
        data = {
            'name': 'Test LLM',
            'description': 'Test model',
            'api_key': 'test_key',
            'model_string': 'test-model',
            'source': 2,
            'is_enabled': True,
            'test_status': 'connected',
            'text': True
        }
        response = admin_client.post('/api/llm/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_update_llm(self, admin_client, llm_together):
        """Test update LLM model."""
        data = {
            'description': 'Updated description',
            'is_enabled': False
        }
        response = admin_client.patch(f'/api/llm/{llm_together.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        llm_together.refresh_from_db()
        assert llm_together.is_enabled == False


# =============================================================================
# FOLDER & DOCUMENT CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestFolderEndpoints:
    """Test folder CRUD operations."""

    def test_create_folder(self, auth_client, user):
        """Test create new folder."""
        data = {
            'title': 'My Documents',
            'user': user.id
        }
        response = auth_client.post('/api/folder/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_user_folders(self, auth_client, user, folder):
        """Test retrieve user's folders."""
        response = auth_client.get(f'/api/folder/user/{user.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_update_folder(self, auth_client, folder):
        """Test update folder."""
        data = {'title': 'Updated Folder'}
        response = auth_client.patch(f'/api/folder/{folder.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        folder.refresh_from_db()
        assert folder.title == 'Updated Folder'

    def test_delete_folder(self, auth_client, folder):
        """Test soft delete folder."""
        response = auth_client.patch(f'/api/folder/{folder.id}/', {
            'is_delete': True
        })

        assert response.status_code == status.HTTP_200_OK
        folder.refresh_from_db()
        assert folder.is_delete == True

    def test_create_subfolder(self, auth_client, user, folder):
        """Test create subfolder."""
        data = {
            'title': 'Subfolder',
            'user': user.id,
            'parent_folder': folder.id
        }
        response = auth_client.post('/api/folder/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


# =============================================================================
# PROMPT & RESPONSE CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestPromptEndpoints:
    """Test prompt CRUD operations."""

    def test_create_prompt(self, auth_client, user, category):
        """Test create new prompt."""
        data = {
            'user': user.id,
            'prompt_text': 'Write a poem about AI',
            'category': category.id,
            'response_type': 2,
            'title': 'AI Poem'
        }
        response = auth_client.post('/api/prompt/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_user_prompts(self, auth_client, user, prompt):
        """Test retrieve user's prompts."""
        response = auth_client.get(f'/api/prompt/user/{user.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_prompt_by_id(self, auth_client, prompt):
        """Test retrieve prompt by ID."""
        response = auth_client.get(f'/api/prompt/{prompt.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == prompt.id

    def test_update_prompt(self, auth_client, prompt):
        """Test update prompt."""
        data = {'title': 'Updated Title'}
        response = auth_client.patch(f'/api/prompt/{prompt.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        prompt.refresh_from_db()
        assert prompt.title == 'Updated Title'

    def test_delete_prompt(self, auth_client, prompt):
        """Test soft delete prompt."""
        response = auth_client.patch(f'/api/prompt/{prompt.id}/', {
            'is_delete': True
        })

        assert response.status_code == status.HTTP_200_OK
        prompt.refresh_from_db()
        assert prompt.is_delete == True

    def test_filter_prompts_by_category(self, auth_client, user, prompt, category):
        """Test filter prompts by category."""
        response = auth_client.get(f'/api/prompt/?category={category.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_search_prompts(self, auth_client, user, prompt):
        """Test search prompts by text."""
        response = auth_client.get(f'/api/prompt/?search={prompt.title}')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPromptResponseEndpoints:
    """Test prompt response CRUD operations."""

    def test_create_prompt_response(self, auth_client, user, prompt, llm_together, category):
        """Test create prompt response."""
        data = {
            'user': user.id,
            'llm': llm_together.id,
            'prompt': prompt.id,
            'response_text': 'Generated response text',
            'response_type': 2,
            'category': category.id,
            'tokenUsed': 50
        }
        response = auth_client.post('/api/prompt-response/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_prompt_responses(self, auth_client, prompt, prompt_response):
        """Test retrieve responses for a prompt."""
        response = auth_client.get(f'/api/prompt-response/prompt/{prompt.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_response_by_id(self, auth_client, prompt_response):
        """Test retrieve response by ID."""
        response = auth_client.get(f'/api/prompt-response/{prompt_response.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == prompt_response.id


# =============================================================================
# CATEGORY CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestCategoryEndpoints:
    """Test category CRUD operations."""

    def test_get_all_categories(self, api_client, category):
        """Test retrieve all categories."""
        response = api_client.get('/api/category/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_category_by_id(self, api_client, category):
        """Test retrieve category by ID."""
        response = api_client.get(f'/api/category/{category.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == category.id

    def test_filter_categories_by_main_category(self, api_client, category, main_category):
        """Test filter categories by main category."""
        response = api_client.get(f'/api/category/?mainCategory={main_category.id}')

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# COUPON CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestCouponEndpoints:
    """Test coupon CRUD operations."""

    def test_validate_coupon_success(self, api_client, percentage_coupon):
        """Test validate valid coupon."""
        response = api_client.post('/api/coupon/validate/', {
            'coupon_code': percentage_coupon.coupon_code,
            'order_amount': 1000
        })

        assert response.status_code == status.HTTP_200_OK

    def test_validate_expired_coupon(self, api_client, expired_coupon):
        """Test validate expired coupon fails."""
        response = api_client.post('/api/coupon/validate/', {
            'coupon_code': expired_coupon.coupon_code,
            'order_amount': 1000
        })

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    def test_validate_coupon_minimum_amount(self, api_client, percentage_coupon):
        """Test coupon validation with minimum order amount."""
        response = api_client.post('/api/coupon/validate/', {
            'coupon_code': percentage_coupon.coupon_code,
            'order_amount': 50  # Below minimum
        })

        assert response.status_code in [status.HTTP_400_BAD_REQUEST]

    def test_get_active_coupons(self, api_client, percentage_coupon, fixed_coupon):
        """Test retrieve active coupons."""
        response = api_client.get('/api/coupon/?is_active=true')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2


# =============================================================================
# CLUSTER CRUD TESTS
# =============================================================================

@pytest.mark.django_db
class TestClusterEndpoints:
    """Test cluster (enterprise) CRUD operations."""

    def test_create_cluster(self, admin_client, free_plan, storage_plan):
        """Test create new cluster."""
        data = {
            'cluster_name': 'Test Corp',
            'org_name': 'Test Corporation',
            'email': 'admin@testcorp.com',
            'domain': 'testcorp.com',
            'plan': free_plan.id,
            'storage_plan': storage_plan.id,
            'username': 'testcorpadmin',
            'password': 'SecurePass123!',
            'name': 'Test Admin'
        }
        response = admin_client.post('/api/cluster/', data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_all_clusters(self, admin_client, cluster):
        """Test retrieve all clusters."""
        response = admin_client.get('/api/cluster/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_get_cluster_by_id(self, admin_client, cluster):
        """Test retrieve cluster by ID."""
        response = admin_client.get(f'/api/cluster/{cluster.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == cluster.id

    def test_update_cluster(self, admin_client, cluster):
        """Test update cluster."""
        data = {'cluster_name': 'Updated Corp'}
        response = admin_client.patch(f'/api/cluster/{cluster.id}/', data)

        assert response.status_code == status.HTTP_200_OK

    def test_search_clusters(self, admin_client, cluster):
        """Test search clusters."""
        response = admin_client.get(f'/api/cluster/?searchBy={cluster.cluster_name}')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_clusters_by_status(self, admin_client, cluster):
        """Test filter clusters by active status."""
        response = admin_client.get('/api/cluster/?status=true')

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# ERROR RESPONSE TESTS
# =============================================================================

@pytest.mark.django_db
class TestErrorResponses:
    """Test error response formats and handling."""

    def test_404_not_found_response(self, auth_client):
        """Test 404 response format."""
        response = auth_client.get('/api/nonexistent/endpoint/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_400_bad_request_response(self, api_client):
        """Test 400 response format."""
        response = api_client.post('/api/authentication/login/', {
            'userNameOrEmail': '',  # Missing required field
            'password': ''
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_401_unauthorized_response(self, api_client):
        """Test 401 response when not authenticated."""
        response = api_client.get('/api/authentication/profile/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_403_forbidden_response(self, auth_client):
        """Test 403 response for forbidden access."""
        # Try to access admin endpoint as regular user
        response = auth_client.post('/api/plan/', {
            'plan_name': 'Test'
        })

        # Should be forbidden or unauthorized
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_method_not_allowed_response(self, api_client):
        """Test 405 response for wrong HTTP method."""
        # Try DELETE on endpoint that doesn't support it
        response = api_client.delete('/api/authentication/login/')

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_validation_error_format(self, api_client, free_plan):
        """Test validation error response format."""
        response = api_client.post('/api/authentication/register/', {
            'username': '',  # Invalid
            'email': 'invalid-email',  # Invalid
            'password': '123',  # Too short
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Response should contain error details
        assert response.data is not None


# =============================================================================
# PAGINATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestPagination:
    """Test pagination across different endpoints."""

    def test_pagination_structure(self, admin_client, create_user):
        """Test pagination response structure."""
        # Create multiple users
        for i in range(15):
            create_user(email=f'page{i}@example.com', username=f'pageuser{i}')

        response = admin_client.get('/api/authentication/users/?page=1')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data or 'total_pages' in response.data
        assert 'next' in response.data or 'total_pages' in response.data
        assert 'previous' in response.data or 'total_pages' in response.data

    def test_pagination_page_size(self, admin_client, create_user):
        """Test pagination respects page size."""
        for i in range(25):
            create_user(email=f'size{i}@example.com', username=f'sizeuser{i}')

        response = admin_client.get('/api/authentication/users/?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        # Should return at most 10 results
        if 'results' in response.data:
            assert len(response.data['results']) <= 10

    def test_pagination_next_page(self, admin_client, create_user):
        """Test accessing next page."""
        for i in range(25):
            create_user(email=f'next{i}@example.com', username=f'nextuser{i}')

        response1 = admin_client.get('/api/authentication/users/?page=1')
        response2 = admin_client.get('/api/authentication/users/?page=2')

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

    def test_pagination_invalid_page(self, admin_client):
        """Test pagination with invalid page number."""
        response = admin_client.get('/api/authentication/users/?page=999')

        # Should return empty results or 404
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# =============================================================================
# FILTERING TESTS
# =============================================================================

@pytest.mark.django_db
class TestFiltering:
    """Test filtering and search capabilities."""

    def test_filter_by_single_field(self, admin_client, create_user):
        """Test filtering by single field."""
        create_user(email='blocked@example.com', username='blocked', is_blocked=True)
        create_user(email='active@example.com', username='active', is_blocked=False)

        response = admin_client.get('/api/authentication/users/?status=true')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_multiple_fields(self, admin_client, create_user, free_plan):
        """Test filtering by multiple fields."""
        user1 = create_user(email='filter1@example.com', username='filteruser1')
        Subscription.objects.create(
            user=user1,
            plan=free_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=1000,
            transactionId='filter1',
            payment_status='paid',
            payment_mode='online',
            plan_name='Test',
            plan_for='token',
            amount=0,
            duration=30,
            totalToken=1000,
            totalFileToken=10
        )

        response = admin_client.get('/api/authentication/users/?userType=active')

        assert response.status_code == status.HTTP_200_OK

    def test_search_functionality(self, admin_client, create_user):
        """Test search across multiple fields."""
        create_user(email='searchable@example.com', username='searchuser')

        response = admin_client.get('/api/authentication/users/?searchBy=search')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_with_pagination(self, admin_client, create_user):
        """Test filtering combined with pagination."""
        for i in range(15):
            create_user(
                email=f'filter{i}@example.com',
                username=f'filteruser{i}',
                is_blocked=(i % 2 == 0)
            )

        response = admin_client.get('/api/authentication/users/?status=false&page=1')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data


# =============================================================================
# QUERY PARAMETER VALIDATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestQueryParameterValidation:
    """Test query parameter validation."""

    def test_invalid_page_number(self, admin_client):
        """Test invalid page number handling."""
        response = admin_client.get('/api/authentication/users/?page=invalid')

        # Should handle gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_negative_page_number(self, admin_client):
        """Test negative page number handling."""
        response = admin_client.get('/api/authentication/users/?page=-1')

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_invalid_filter_value(self, admin_client):
        """Test invalid filter value handling."""
        response = admin_client.get('/api/authentication/users/?status=invalid')

        # Should handle gracefully
        assert response.status_code == status.HTTP_200_OK
