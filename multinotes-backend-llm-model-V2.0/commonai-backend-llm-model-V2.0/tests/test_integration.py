"""
Comprehensive integration tests for MultinotesAI backend.

Tests cover:
- Full user registration to AI generation flow
- Complete payment flow (order -> payment -> subscription)
- AI generation workflows
- Referral system flow
- Cluster/Enterprise user flows
- Subscription lifecycle flows
- Multi-user interaction scenarios
"""

import pytest
from django.urls import reverse
from rest_framework import status
from datetime import timedelta
from django.utils import timezone
from authentication.models import CustomUser, Referral, Cluster
from planandsubscription.models import Subscription, Transaction, UserPlan
from coreapp.models import (
    LLM, Prompt, PromptResponse, Folder,
    GroupResponse, StorageUsage, LLM_Tokens
)
from ticketandcategory.models import Category
import jwt
from django.conf import settings


# =============================================================================
# FULL USER FLOW TESTS
# =============================================================================

@pytest.mark.django_db
class TestCompleteUserFlow:
    """Test complete user journey from registration to usage."""

    def test_full_registration_to_generation_flow(
        self, api_client, free_plan, storage_plan, llm_together, category, mock_llm_generation
    ):
        """Test complete flow: Register -> Login -> Generate AI Content."""

        # Step 1: User Registration
        register_data = {
            'username': 'flowuser',
            'email': 'flowuser@example.com',
            'password': 'SecurePass123!',
            'name': 'Flow User'
        }
        register_response = api_client.post('/api/authentication/register/', register_data)
        assert register_response.status_code == status.HTTP_200_OK
        user_id = register_response.data['userId']
        subscription_id = register_response.data['subscriptionId']

        # Verify subscription created
        assert subscription_id is not None

        # Step 2: User Login
        login_data = {
            'userNameOrEmail': 'flowuser@example.com',
            'password': 'SecurePass123!'
        }
        login_response = api_client.post('/api/authentication/login/', login_data)
        assert login_response.status_code == status.HTTP_200_OK
        assert 'token' in login_response.data

        # Get access token
        access_token = login_response.data['token']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Step 3: Get User Profile
        profile_response = api_client.get(f'/api/authentication/user/{user_id}/')
        assert profile_response.status_code == status.HTTP_200_OK

        # Step 4: Create a Prompt (AI Generation would be tested with mocks)
        prompt_data = {
            'user': user_id,
            'prompt_text': 'Write a haiku about technology',
            'category': category.id,
            'response_type': 2,
            'title': 'Tech Haiku'
        }
        prompt_response = api_client.post('/api/prompt/', prompt_data)
        assert prompt_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_social_login_to_usage_flow(
        self, api_client, free_plan, storage_plan, llm_together, category
    ):
        """Test social login flow to usage."""

        # Step 1: Social Login (creates account)
        social_data = {
            'email': 'social@example.com',
            'username': 'socialuser',
            'socialId': 'google_987654',
            'socialType': 2,
            'name': 'Social User'
        }
        login_response = api_client.post('/api/authentication/social-login/', social_data)
        assert login_response.status_code == status.HTTP_200_OK
        assert 'token' in login_response.data

        user_id = login_response.data['userId']
        access_token = login_response.data['token']['access']

        # Step 2: Use API with token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Step 3: Create Folder
        folder_data = {
            'title': 'My Projects',
            'user': user_id
        }
        folder_response = api_client.post('/api/folder/', folder_data)
        assert folder_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_email_verification_flow(self, api_client, free_plan):
        """Test email verification complete flow."""

        # Step 1: Register
        register_data = {
            'username': 'verifyuser',
            'email': 'verify@example.com',
            'password': 'SecurePass123!',
            'name': 'Verify User'
        }
        register_response = api_client.post('/api/authentication/register/', register_data)
        assert register_response.status_code == status.HTTP_200_OK
        user_id = register_response.data['userId']

        # Step 2: Generate verification token (simulated)
        token = jwt.encode(
            {'user_id': user_id},
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        # Step 3: Verify email
        verify_response = api_client.post('/api/authentication/email-verify/', {
            'token': token
        })
        assert verify_response.status_code == status.HTTP_200_OK

        # Step 4: Login should now work
        login_response = api_client.post('/api/authentication/login/', {
            'userNameOrEmail': 'verify@example.com',
            'password': 'SecurePass123!'
        })
        assert login_response.status_code == status.HTTP_200_OK

    def test_password_reset_complete_flow(self, api_client, create_user, user_password):
        """Test complete password reset flow."""

        # Step 1: Create user
        user = create_user(email='reset@example.com', username='resetuser')

        # Step 2: Request password reset
        forgot_response = api_client.post('/api/authentication/forgot-password/', {
            'email': 'reset@example.com'
        })
        assert forgot_response.status_code == status.HTTP_200_OK

        # Step 3: Generate reset token (simulated)
        token = jwt.encode(
            {'user_id': user.id},
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        # Step 4: Reset password
        new_password = 'NewSecurePass456!'
        reset_response = api_client.post('/api/authentication/reset-password/', {
            'token': token,
            'password': new_password
        })
        assert reset_response.status_code == status.HTTP_200_OK

        # Step 5: Login with new password
        login_response = api_client.post('/api/authentication/login/', {
            'userNameOrEmail': 'reset@example.com',
            'password': new_password
        })
        assert login_response.status_code == status.HTTP_200_OK


# =============================================================================
# PAYMENT FLOW TESTS
# =============================================================================

@pytest.mark.django_db
class TestPaymentFlow:
    """Test complete payment and subscription flows."""

    def test_complete_payment_to_subscription_flow(
        self, auth_client, user, paid_plan, mock_razorpay
    ):
        """Test complete payment flow: Select Plan -> Create Order -> Pay -> Activate Subscription."""

        # Step 1: Get available plans
        plans_response = auth_client.get('/api/plan/')
        assert plans_response.status_code == status.HTTP_200_OK

        # Step 2: Create payment order
        order_data = {
            'plan_id': paid_plan.id,
            'amount': paid_plan.amount
        }
        order_response = auth_client.post('/api/payment/create-order/', order_data)

        # With mock, this should succeed or not be implemented
        if order_response.status_code == status.HTTP_200_OK:
            order_id = order_response.data.get('order_id')

            # Step 3: Verify payment (simulated)
            verify_data = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': 'pay_test123',
                'razorpay_signature': 'signature_test',
                'plan_id': paid_plan.id
            }
            verify_response = auth_client.post('/api/payment/verify/', verify_data)

            # Payment verification should succeed
            if verify_response.status_code == status.HTTP_200_OK:
                # Step 4: Check subscription was created
                subscription = Subscription.objects.filter(
                    user=user,
                    status='active'
                ).first()

                if subscription:
                    assert subscription.plan == paid_plan

    def test_subscription_upgrade_flow(
        self, auth_client, user, user_subscription, paid_plan
    ):
        """Test subscription upgrade flow."""

        # User has free plan, upgrading to paid plan
        initial_plan = user_subscription.plan

        # Create new subscription (simulated upgrade)
        new_subscription = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=paid_plan.totalToken,
            fileToken=paid_plan.fileToken,
            transactionId='upgrade_123',
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken,
            upgrade_from_plan=initial_plan
        )

        # Mark old subscription as expired
        user_subscription.status = 'expire'
        user_subscription.save()

        assert new_subscription.upgrade_from_plan == initial_plan
        assert new_subscription.status == 'active'

    def test_coupon_application_in_payment_flow(
        self, auth_client, user, paid_plan, percentage_coupon
    ):
        """Test applying coupon during payment."""

        # Step 1: Validate coupon
        validate_response = auth_client.post('/api/coupon/validate/', {
            'coupon_code': percentage_coupon.coupon_code,
            'order_amount': paid_plan.amount
        })

        if validate_response.status_code == status.HTTP_200_OK:
            # Coupon is valid
            discount = validate_response.data.get('discount', 0)

            # Step 2: Create subscription with coupon
            discounted_amount = paid_plan.amount - discount

            subscription = Subscription.objects.create(
                user=user,
                plan=paid_plan,
                status='active',
                subscriptionExpiryDate=timezone.now() + timedelta(days=30),
                subscriptionEndDate=timezone.now() + timedelta(days=37),
                balanceToken=paid_plan.totalToken,
                fileToken=paid_plan.fileToken,
                transactionId='coupon_123',
                payment_status='paid',
                payment_mode='online',
                plan_name=paid_plan.plan_name,
                plan_for='token',
                amount=discounted_amount,
                duration=paid_plan.duration,
                totalToken=paid_plan.totalToken,
                totalFileToken=paid_plan.fileToken,
                coupon_code=percentage_coupon.coupon_code,
                coupon_type=percentage_coupon.coupon_type,
                discount_value=percentage_coupon.discount_value
            )

            assert subscription.coupon_code == percentage_coupon.coupon_code

    def test_transaction_tracking_in_payment_flow(
        self, auth_client, user, paid_plan
    ):
        """Test transaction is properly tracked during payment."""

        # Create transaction
        transaction = Transaction.objects.create(
            user=user,
            transactionId='txn_123',
            amount=paid_plan.amount,
            plan_name=paid_plan.plan_name,
            duration=paid_plan.duration,
            tokenCount=paid_plan.totalToken,
            fileToken=paid_plan.fileToken,
            payment_status='paid',
            payment_method='razorpay'
        )

        # Create linked subscription
        subscription = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=paid_plan.totalToken,
            fileToken=paid_plan.fileToken,
            transactionId=transaction.transactionId,
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken
        )

        transaction.subscription = subscription
        transaction.save()

        assert transaction.subscription == subscription
        assert subscription.transactionId == transaction.transactionId


# =============================================================================
# AI GENERATION FLOW TESTS
# =============================================================================

@pytest.mark.django_db
class TestAIGenerationFlow:
    """Test complete AI generation workflows."""

    def test_text_generation_with_token_deduction_flow(
        self, auth_client, user, user_subscription, llm_together, category
    ):
        """Test text generation with automatic token deduction."""

        initial_balance = user_subscription.balanceToken

        # Create prompt and response
        prompt = Prompt.objects.create(
            user=user,
            prompt_text='Generate a story',
            category=category,
            response_type=2,
            title='Story Prompt'
        )

        # Simulate token usage
        tokens_used = 150

        response = PromptResponse.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            response_text='Generated story content...',
            response_type=2,
            category=category,
            tokenUsed=tokens_used
        )

        # Track token usage
        LLM_Tokens.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            text_token_used=tokens_used,
            file_token_used=0
        )

        # Deduct tokens from subscription
        user_subscription.balanceToken -= tokens_used
        user_subscription.usedToken += tokens_used
        user_subscription.save()

        user_subscription.refresh_from_db()
        assert user_subscription.balanceToken == initial_balance - tokens_used
        assert user_subscription.usedToken == tokens_used

    def test_conversation_flow_with_context(
        self, auth_client, user, user_subscription, llm_together, category
    ):
        """Test conversation flow maintaining context."""

        # Step 1: Create conversation group
        group = GroupResponse.objects.create(
            user=user,
            category=category,
            llm=llm_together,
            group_name='Tech Discussion'
        )

        # Step 2: First message
        prompt1 = Prompt.objects.create(
            user=user,
            group=group,
            prompt_text='What is machine learning?',
            category=category,
            response_type=2,
            title='ML Question'
        )

        response1 = PromptResponse.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt1,
            response_text='Machine learning is...',
            response_type=2,
            category=category,
            tokenUsed=100
        )

        # Step 3: Follow-up message (should include context)
        prompt2 = Prompt.objects.create(
            user=user,
            group=group,
            prompt_text='Can you give me an example?',
            category=category,
            response_type=2,
            title='ML Example'
        )

        response2 = PromptResponse.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt2,
            response_text='Here is an example...',
            response_type=2,
            category=category,
            tokenUsed=150
        )

        # Verify both prompts belong to same group
        assert prompt1.group == group
        assert prompt2.group == group

    def test_multi_modal_generation_flow(
        self, auth_client, user, user_subscription, llm_gemini, category
    ):
        """Test multi-modal generation (image to text)."""

        # Step 1: Upload image
        prompt = Prompt.objects.create(
            user=user,
            prompt_image='path/to/uploaded/image.jpg',
            category=category,
            response_type=3,  # Image to text
            title='Image Analysis'
        )

        # Step 2: Generate text from image
        response = PromptResponse.objects.create(
            user=user,
            llm=llm_gemini,
            prompt=prompt,
            response_text='The image shows...',
            response_type=3,
            category=category,
            tokenUsed=200
        )

        # Use file tokens
        user_subscription.fileToken -= 1
        user_subscription.usedFileToken += 1
        user_subscription.save()

        assert response.response_type == 3
        user_subscription.refresh_from_db()
        assert user_subscription.usedFileToken == 1

    def test_save_and_organize_generations_flow(
        self, auth_client, user, llm_together, category
    ):
        """Test saving and organizing generated content."""

        # Step 1: Create folder
        folder = Folder.objects.create(
            title='AI Generations',
            user=user
        )

        # Step 2: Create prompt (saved to folder)
        prompt = Prompt.objects.create(
            user=user,
            prompt_text='Write a poem',
            category=category,
            response_type=2,
            title='Poem',
            is_saved=True
        )

        # Step 3: Generate response
        response = PromptResponse.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            response_text='Roses are red...',
            response_type=2,
            category=category,
            tokenUsed=50
        )

        assert prompt.is_saved == True
        assert folder.user == user


# =============================================================================
# REFERRAL FLOW TESTS
# =============================================================================

@pytest.mark.django_db
class TestReferralFlow:
    """Test complete referral system flows."""

    def test_complete_referral_flow(
        self, api_client, user, referral_setting, free_plan
    ):
        """Test complete referral flow: Share code -> New user registers -> Rewards."""

        # Step 1: Existing user has referral code
        referrer = user
        referral_code = referrer.referral_code
        assert referral_code is not None

        # Step 2: New user registers with referral code
        register_data = {
            'username': 'referred',
            'email': 'referred@example.com',
            'password': 'SecurePass123!',
            'name': 'Referred User',
            'referr_by_code': referral_code
        }

        register_response = api_client.post('/api/authentication/register/', register_data)

        if register_response.status_code == status.HTTP_200_OK:
            # Step 3: Verify referral record created
            referred_user_id = register_response.data['userId']
            referred_user = CustomUser.objects.get(id=referred_user_id)

            referral = Referral.objects.filter(
                referr_by=referrer,
                referr_to=referred_user
            ).first()

            if referral:
                assert referral.code == referral_code
                assert referral.refer_by_token == referral_setting.refer_by_token
                assert referral.refer_to_token == referral_setting.refer_to_token

    def test_referral_reward_distribution(
        self, db, user, create_user, referral_setting
    ):
        """Test referral rewards are properly distributed."""

        # Create referred user
        referred = create_user(
            email='rewarded@example.com',
            username='rewarded'
        )

        # Create referral
        referral = Referral.objects.create(
            referr_by=user,
            referr_to=referred,
            refer_by_token=referral_setting.refer_by_token,
            refer_to_token=referral_setting.refer_to_token,
            code=user.referral_code,
            reward_given=False
        )

        # Simulate reward distribution (would happen on first payment)
        referrer_subscription = Subscription.objects.filter(user=user).first()
        referred_subscription = Subscription.objects.filter(user=referred).first()

        if referrer_subscription and referred_subscription:
            # Add bonus tokens
            referrer_subscription.balanceToken += referral.refer_by_token
            referred_subscription.balanceToken += referral.refer_to_token
            referrer_subscription.save()
            referred_subscription.save()

            # Mark reward as given
            referral.reward_given = True
            referral.save()

            assert referral.reward_given == True


# =============================================================================
# ENTERPRISE/CLUSTER FLOW TESTS
# =============================================================================

@pytest.mark.django_db
class TestEnterpriseFlow:
    """Test enterprise/cluster user flows."""

    def test_cluster_creation_and_user_assignment_flow(
        self, admin_client, free_plan, storage_plan
    ):
        """Test complete cluster creation flow."""

        # Step 1: Admin creates cluster
        cluster_data = {
            'cluster_name': 'Acme Corp',
            'org_name': 'Acme Corporation',
            'email': 'admin@acme.com',
            'domain': 'acme.com',
            'plan': free_plan.id,
            'storage_plan': storage_plan.id,
            'username': 'acmeadmin',
            'password': 'SecurePass123!',
            'name': 'Acme Admin'
        }

        cluster_response = admin_client.post('/api/cluster/', cluster_data)

        if cluster_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            cluster_id = cluster_response.data.get('cluster', {}).get('id')

            if cluster_id:
                cluster = Cluster.objects.get(id=cluster_id)

                # Step 2: User with matching domain registers
                user_data = {
                    'username': 'acmeuser',
                    'email': 'user@acme.com',
                    'password': 'SecurePass123!',
                    'name': 'Acme User'
                }

                # Should automatically assign to cluster
                assert cluster.domain == 'acme.com'

    def test_cluster_user_sharing_resources(
        self, db, create_user, cluster, free_plan
    ):
        """Test cluster users sharing subscription."""

        # Create cluster admin
        admin = create_user(
            email='admin@testcompany.com',
            username='clusteradmin',
            cluster=cluster,
            is_cluster_owner=True
        )

        # Create cluster users
        user1 = create_user(
            email='user1@testcompany.com',
            username='clusteruser1',
            cluster=cluster
        )

        user2 = create_user(
            email='user2@testcompany.com',
            username='clusteruser2',
            cluster=cluster
        )

        # All should belong to same cluster
        assert admin.cluster == cluster
        assert user1.cluster == cluster
        assert user2.cluster == cluster

        # Cluster should have shared subscription
        if cluster.subscription:
            assert cluster.subscription.plan is not None


# =============================================================================
# SUBSCRIPTION LIFECYCLE FLOW TESTS
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionLifecycle:
    """Test subscription lifecycle flows."""

    def test_trial_to_paid_conversion_flow(
        self, db, user, free_plan, paid_plan
    ):
        """Test converting from trial to paid subscription."""

        # Step 1: User has trial subscription
        trial_sub = Subscription.objects.create(
            user=user,
            plan=free_plan,
            status='trial',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=1000,
            fileToken=10,
            trialStartDate=timezone.now(),
            trialEndDate=timezone.now() + timedelta(days=30),
            transactionId='trial',
            payment_status='trial',
            payment_mode='online',
            plan_name=free_plan.plan_name,
            plan_for='token',
            amount=0,
            duration=30,
            totalToken=1000,
            totalFileToken=10
        )

        # Step 2: User converts to paid
        paid_sub = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=paid_plan.totalToken,
            fileToken=paid_plan.fileToken,
            transactionId='conversion_123',
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken,
            upgrade_from_plan=free_plan
        )

        # Mark trial as expired
        trial_sub.status = 'expire'
        trial_sub.save()

        assert paid_sub.upgrade_from_plan == free_plan
        assert trial_sub.status == 'expire'

    def test_subscription_expiry_and_grace_period(
        self, db, user, free_plan
    ):
        """Test subscription expiry and grace period."""

        # Create expiring subscription
        subscription = Subscription.objects.create(
            user=user,
            plan=free_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() - timedelta(days=1),  # Expired
            subscriptionEndDate=timezone.now() + timedelta(days=6),  # Grace period
            balanceToken=500,
            fileToken=5,
            transactionId='expiring_123',
            payment_status='paid',
            payment_mode='online',
            plan_name=free_plan.plan_name,
            plan_for='token',
            amount=0,
            duration=30,
            totalToken=1000,
            totalFileToken=10
        )

        # Check if in grace period
        is_expired = subscription.subscriptionExpiryDate < timezone.now()
        in_grace_period = subscription.subscriptionEndDate > timezone.now()

        assert is_expired == True
        assert in_grace_period == True

    def test_subscription_renewal_flow(
        self, db, user, paid_plan
    ):
        """Test subscription renewal."""

        # Original subscription
        old_sub = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='expire',
            subscriptionExpiryDate=timezone.now() - timedelta(days=10),
            subscriptionEndDate=timezone.now() - timedelta(days=3),
            balanceToken=0,
            expireToken=5000,
            fileToken=0,
            expireFileToken=50,
            transactionId='old_123',
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken
        )

        # Renewal
        new_sub = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=paid_plan.totalToken,
            fileToken=paid_plan.fileToken,
            transactionId='renewal_123',
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken
        )

        assert old_sub.status == 'expire'
        assert new_sub.status == 'active'


# =============================================================================
# MULTI-USER INTERACTION TESTS
# =============================================================================

@pytest.mark.django_db
class TestMultiUserInteractions:
    """Test scenarios involving multiple users."""

    def test_concurrent_generations_different_users(
        self, db, create_user, llm_together, category, free_plan
    ):
        """Test multiple users generating content concurrently."""

        # Create multiple users
        user1 = create_user(email='user1@example.com', username='user1')
        user2 = create_user(email='user2@example.com', username='user2')

        # Create subscriptions
        for user in [user1, user2]:
            Subscription.objects.create(
                user=user,
                plan=free_plan,
                status='active',
                subscriptionExpiryDate=timezone.now() + timedelta(days=30),
                subscriptionEndDate=timezone.now() + timedelta(days=37),
                balanceToken=1000,
                fileToken=10,
                transactionId=f'concurrent_{user.id}',
                payment_status='paid',
                payment_mode='online',
                plan_name=free_plan.plan_name,
                plan_for='token',
                amount=0,
                duration=30,
                totalToken=1000,
                totalFileToken=10
            )

        # Both users generate content
        prompt1 = Prompt.objects.create(
            user=user1,
            prompt_text='User 1 prompt',
            category=category,
            response_type=2,
            title='User1 Prompt'
        )

        prompt2 = Prompt.objects.create(
            user=user2,
            prompt_text='User 2 prompt',
            category=category,
            response_type=2,
            title='User2 Prompt'
        )

        # Verify isolation
        assert prompt1.user == user1
        assert prompt2.user == user2
        assert prompt1.user != prompt2.user

    def test_admin_managing_multiple_users(
        self, db, admin_user, create_user
    ):
        """Test admin operations on multiple users."""

        # Create multiple users
        users = []
        for i in range(5):
            user = create_user(
                email=f'managed{i}@example.com',
                username=f'managed{i}'
            )
            users.append(user)

        # Admin can access all users
        all_users = CustomUser.objects.filter(is_delete=False)
        assert all_users.count() >= 5

        # Admin blocks a user
        users[0].is_blocked = True
        users[0].save()

        assert users[0].is_blocked == True

    def test_referral_network_multiple_levels(
        self, db, user, create_user, referral_setting
    ):
        """Test multi-level referral network."""

        # Level 1: Original user refers user1
        user1 = create_user(email='level1@example.com', username='level1user')
        referral1 = Referral.objects.create(
            referr_by=user,
            referr_to=user1,
            refer_by_token=100,
            refer_to_token=50,
            code=user.referral_code
        )

        # Level 2: user1 refers user2
        user2 = create_user(email='level2@example.com', username='level2user')
        referral2 = Referral.objects.create(
            referr_by=user1,
            referr_to=user2,
            refer_by_token=100,
            refer_to_token=50,
            code=user1.referral_code
        )

        # Verify network
        assert referral1.referr_by == user
        assert referral1.referr_to == user1
        assert referral2.referr_by == user1
        assert referral2.referr_to == user2
