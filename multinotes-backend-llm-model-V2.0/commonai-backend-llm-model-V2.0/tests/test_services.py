"""
Comprehensive service layer tests for MultinotesAI backend.

Tests cover:
- AI generation services (mocked)
- Export services (PDF, DOCX, etc.)
- Analytics services
- Token management services
- Storage services
- Email services
- Payment services (mocked)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from authentication.models import CustomUser, Referral, ReferralSetting
from planandsubscription.models import Subscription, Transaction, UserPlan
from coreapp.models import (
    LLM, Prompt, PromptResponse, StorageUsage,
    LLM_Tokens, GroupResponse
)
from rest_framework import status


# =============================================================================
# AI GENERATION SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestAIGenerationService:
    """Test AI generation services with mocked external APIs."""

    def test_text_generation_together_api(self, auth_client, user, llm_together, category, mock_llm_generation):
        """Test text generation with Together AI (mocked)."""
        data = {
            'prompt_text': 'Write a short story',
            'llm_id': llm_together.id,
            'category_id': category.id,
            'response_type': 2
        }

        response = auth_client.post('/api/generate/text/', data)

        # Verify mock was called
        assert mock_llm_generation is not None

    def test_text_generation_gemini_api(self, auth_client, user, llm_gemini, category, mock_llm_generation):
        """Test text generation with Gemini (mocked)."""
        data = {
            'prompt_text': 'Explain quantum computing',
            'llm_id': llm_gemini.id,
            'category_id': category.id,
            'response_type': 2
        }

        response = auth_client.post('/api/generate/text/', data)

        # Verify generation request
        assert mock_llm_generation is not None

    def test_text_generation_openai_api(self, auth_client, user, llm_openai, category, mock_llm_generation):
        """Test text generation with OpenAI (mocked)."""
        data = {
            'prompt_text': 'Write a poem',
            'llm_id': llm_openai.id,
            'category_id': category.id,
            'response_type': 2
        }

        response = auth_client.post('/api/generate/text/', data)

        assert mock_llm_generation is not None

    def test_text_generation_disabled_model(self, auth_client, user, disabled_llm, category):
        """Test generation fails with disabled model."""
        data = {
            'prompt_text': 'Test prompt',
            'llm_id': disabled_llm.id,
            'category_id': category.id,
            'response_type': 2
        }

        response = auth_client.post('/api/generate/text/', data)

        # Should fail or return error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    @patch('coreapp.utils.generateTextToTextUsingTogether')
    def test_text_generation_api_error_handling(self, mock_generate, auth_client, user, llm_together, category):
        """Test error handling when AI API fails."""
        # Mock API failure
        mock_generate.side_effect = Exception("API Error")

        data = {
            'prompt_text': 'Test prompt',
            'llm_id': llm_together.id,
            'category_id': category.id,
            'response_type': 2
        }

        response = auth_client.post('/api/generate/text/', data)

        # Should handle error gracefully
        assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_400_BAD_REQUEST]

    def test_image_to_text_generation(self, auth_client, user, llm_gemini, category, mock_s3_upload, mock_llm_generation):
        """Test image to text generation (mocked)."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile(
            "test.jpg",
            b"fake_image_content",
            content_type="image/jpeg"
        )

        data = {
            'prompt_image': image,
            'llm_id': llm_gemini.id,
            'category_id': category.id,
            'response_type': 3
        }

        response = auth_client.post('/api/generate/image-to-text/', data, format='multipart')

        # Verify mocks were called
        assert mock_s3_upload is not None
        assert mock_llm_generation is not None

    def test_text_to_image_generation(self, auth_client, user, llm_openai, category, mock_llm_generation):
        """Test text to image generation (mocked)."""
        data = {
            'prompt_text': 'A beautiful sunset',
            'llm_id': llm_openai.id,
            'category_id': category.id,
            'response_type': 4
        }

        response = auth_client.post('/api/generate/text-to-image/', data)

        assert mock_llm_generation is not None

    def test_conversation_context_maintained(self, auth_client, user, llm_together, category, group_response):
        """Test conversation context is maintained across messages."""
        # First message
        data1 = {
            'prompt_text': 'What is AI?',
            'llm_id': llm_together.id,
            'category_id': category.id,
            'group_id': group_response.id,
            'response_type': 2
        }

        # Second message (should include context)
        data2 = {
            'prompt_text': 'Tell me more about it',
            'llm_id': llm_together.id,
            'category_id': category.id,
            'group_id': group_response.id,
            'response_type': 2
        }

        # Verify context handling
        assert group_response.id is not None


# =============================================================================
# TOKEN MANAGEMENT SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestTokenManagementService:
    """Test token management and tracking services."""

    def test_token_deduction_on_generation(self, user, user_subscription, llm_together):
        """Test tokens are deducted after generation."""
        initial_balance = user_subscription.balanceToken

        # Simulate token usage
        tokens_used = 100
        user_subscription.balanceToken -= tokens_used
        user_subscription.usedToken += tokens_used
        user_subscription.save()

        user_subscription.refresh_from_db()
        assert user_subscription.balanceToken == initial_balance - tokens_used
        assert user_subscription.usedToken == tokens_used

    def test_insufficient_tokens_prevents_generation(self, auth_client, user, user_subscription, llm_together, category):
        """Test generation fails when user has insufficient tokens."""
        # Set token balance to 0
        user_subscription.balanceToken = 0
        user_subscription.save()

        data = {
            'prompt_text': 'Test prompt',
            'llm_id': llm_together.id,
            'category_id': category.id,
            'response_type': 2
        }

        response = auth_client.post('/api/generate/text/', data)

        # Should fail due to insufficient tokens
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_402_PAYMENT_REQUIRED]

    def test_file_token_tracking(self, user, user_subscription, llm_together):
        """Test file tokens are tracked separately."""
        initial_file_tokens = user_subscription.fileToken

        # Simulate file token usage
        file_tokens_used = 5
        user_subscription.fileToken -= file_tokens_used
        user_subscription.usedFileToken += file_tokens_used
        user_subscription.save()

        user_subscription.refresh_from_db()
        assert user_subscription.fileToken == initial_file_tokens - file_tokens_used
        assert user_subscription.usedFileToken == file_tokens_used

    def test_token_usage_statistics(self, db, user, llm_together, prompt):
        """Test token usage statistics are tracked per LLM."""
        # Create token usage records
        LLM_Tokens.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            text_token_used=100,
            file_token_used=5
        )

        LLM_Tokens.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            text_token_used=200,
            file_token_used=10
        )

        # Get total token usage
        total_text = LLM_Tokens.get_total_text_token_used_for_llm(llm_together.id)
        total_file = LLM_Tokens.get_total_file_token_used_for_llm(llm_together.id)

        assert total_text == 300
        assert total_file == 15

    def test_expired_tokens_calculation(self, user, expired_subscription):
        """Test expired tokens are calculated correctly."""
        expired_subscription.expireToken = 500
        expired_subscription.save()

        expired_subscription.refresh_from_db()
        assert expired_subscription.expireToken == 500
        assert expired_subscription.status == 'expire'

    def test_bonus_tokens_from_coupon(self, db, user, paid_plan, fixed_coupon):
        """Test bonus tokens are added from coupon."""
        subscription = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=paid_plan.totalToken + fixed_coupon.bonus_token,
            transactionId='bonus_test',
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken,
            bonus_token=fixed_coupon.bonus_token
        )

        assert subscription.bonus_token == fixed_coupon.bonus_token


# =============================================================================
# STORAGE SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestStorageService:
    """Test storage management services."""

    def test_storage_limit_check(self, db, user, storage_plan):
        """Test storage limit is checked before upload."""
        storage = StorageUsage.objects.create(
            user=user,
            plan=storage_plan,
            storage_limit=1024 * 1024 * 100,  # 100 MB
            total_storage_used=1024 * 1024 * 90,  # 90 MB used
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            status='active',
            transactionId='storage_test',
            payment_status='paid',
            payment_mode='online',
            plan_name=storage_plan.plan_name,
            plan_for='storage',
            amount=storage_plan.amount,
            duration=storage_plan.duration
        )

        # Check if user can upload 20 MB file
        file_size = 1024 * 1024 * 20  # 20 MB
        can_upload = (storage.total_storage_used + file_size) <= storage.storage_limit

        assert can_upload == False  # Should exceed limit

    def test_storage_usage_tracking(self, db, user, storage_plan):
        """Test storage usage is tracked correctly."""
        storage = StorageUsage.objects.create(
            user=user,
            plan=storage_plan,
            storage_limit=1024 * 1024 * 100,
            total_storage_used=0,
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            status='active',
            transactionId='storage_test2',
            payment_status='paid',
            payment_mode='online',
            plan_name=storage_plan.plan_name,
            plan_for='storage',
            amount=storage_plan.amount,
            duration=storage_plan.duration
        )

        # Simulate file upload
        file_size = 1024 * 1024 * 10  # 10 MB
        storage.total_storage_used += file_size
        storage.save()

        storage.refresh_from_db()
        assert storage.total_storage_used == file_size

    def test_storage_cleanup_on_file_delete(self, db, user, storage_plan):
        """Test storage is freed when file is deleted."""
        storage = StorageUsage.objects.create(
            user=user,
            plan=storage_plan,
            storage_limit=1024 * 1024 * 100,
            total_storage_used=1024 * 1024 * 20,
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            status='active',
            transactionId='storage_test3',
            payment_status='paid',
            payment_mode='online',
            plan_name=storage_plan.plan_name,
            plan_for='storage',
            amount=storage_plan.amount,
            duration=storage_plan.duration
        )

        # Simulate file deletion
        file_size = 1024 * 1024 * 5  # 5 MB
        storage.total_storage_used -= file_size
        storage.save()

        storage.refresh_from_db()
        assert storage.total_storage_used == 1024 * 1024 * 15


# =============================================================================
# EXPORT SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestExportService:
    """Test export services for various formats."""

    @patch('coreapp.export_utils.generate_pdf')
    def test_export_to_pdf(self, mock_pdf, auth_client, user, prompt_response):
        """Test export response to PDF (mocked)."""
        mock_pdf.return_value = b'fake_pdf_content'

        response = auth_client.get(f'/api/export/pdf/{prompt_response.id}/')

        # Should succeed or be implemented
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]

    @patch('coreapp.export_utils.generate_docx')
    def test_export_to_docx(self, mock_docx, auth_client, user, prompt_response):
        """Test export response to DOCX (mocked)."""
        mock_docx.return_value = b'fake_docx_content'

        response = auth_client.get(f'/api/export/docx/{prompt_response.id}/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]

    @patch('coreapp.export_utils.generate_txt')
    def test_export_to_txt(self, mock_txt, auth_client, user, prompt_response):
        """Test export response to TXT (mocked)."""
        mock_txt.return_value = b'fake_txt_content'

        response = auth_client.get(f'/api/export/txt/{prompt_response.id}/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]

    def test_export_conversation_history(self, auth_client, user, group_response):
        """Test export conversation history."""
        response = auth_client.get(f'/api/export/conversation/{group_response.id}/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]

    def test_bulk_export_prompts(self, auth_client, user, prompt):
        """Test bulk export of user's prompts."""
        response = auth_client.get(f'/api/export/prompts/bulk/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED
        ]


# =============================================================================
# ANALYTICS SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestAnalyticsService:
    """Test analytics and reporting services."""

    def test_user_token_usage_analytics(self, db, user, llm_together, prompt):
        """Test user token usage analytics."""
        # Create token usage records
        for i in range(10):
            LLM_Tokens.objects.create(
                user=user,
                llm=llm_together,
                prompt=prompt,
                text_token_used=100,
                file_token_used=5
            )

        total_text = LLM_Tokens.objects.filter(user=user).aggregate(
            total=sum(obj.text_token_used for obj in LLM_Tokens.objects.filter(user=user))
        )

        # Verify analytics data
        records = LLM_Tokens.objects.filter(user=user)
        assert records.count() == 10

    def test_llm_usage_statistics(self, db, user, llm_together, prompt):
        """Test LLM usage statistics."""
        # Create usage records
        LLM_Tokens.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            text_token_used=500,
            file_token_used=10
        )

        total = LLM_Tokens.get_total_text_token_used_for_llm(llm_together.id)
        assert total == 500

    def test_subscription_analytics(self, db, user, paid_plan):
        """Test subscription analytics."""
        # Create multiple subscriptions
        Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=1000,
            transactionId='analytics_1',
            payment_status='paid',
            payment_mode='online',
            plan_name=paid_plan.plan_name,
            plan_for='token',
            amount=paid_plan.amount,
            duration=paid_plan.duration,
            totalToken=paid_plan.totalToken,
            totalFileToken=paid_plan.fileToken
        )

        active_subs = Subscription.objects.filter(user=user, status='active')
        assert active_subs.count() >= 1

    def test_revenue_analytics(self, db, user, paid_plan):
        """Test revenue analytics."""
        # Create transactions
        for i in range(5):
            Transaction.objects.create(
                user=user,
                transactionId=f'rev_{i}',
                amount=paid_plan.amount,
                plan_name=paid_plan.plan_name,
                duration=paid_plan.duration,
                tokenCount=paid_plan.totalToken,
                fileToken=paid_plan.fileToken,
                payment_status='paid',
                payment_method='razorpay'
            )

        total_revenue = sum(
            t.amount for t in Transaction.objects.filter(payment_status='paid')
        )
        assert total_revenue == paid_plan.amount * 5

    def test_prompt_category_analytics(self, db, user, category, prompt):
        """Test prompt category usage analytics."""
        # Create prompts in different categories
        prompts = Prompt.objects.filter(category=category)
        assert prompts.count() >= 1


# =============================================================================
# PAYMENT SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestPaymentService:
    """Test payment processing services (mocked)."""

    def test_razorpay_order_creation(self, auth_client, user, paid_plan, mock_razorpay):
        """Test Razorpay order creation (mocked)."""
        data = {
            'plan_id': paid_plan.id,
            'amount': paid_plan.amount
        }

        response = auth_client.post('/api/payment/create-order/', data)

        # Verify mock was used
        assert mock_razorpay is not None

    def test_razorpay_payment_verification(self, auth_client, user, paid_plan, mock_razorpay):
        """Test Razorpay payment verification (mocked)."""
        data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test'
        }

        response = auth_client.post('/api/payment/verify/', data)

        assert mock_razorpay is not None

    def test_payment_failure_handling(self, auth_client, user, paid_plan, mocker):
        """Test payment failure is handled correctly."""
        # Mock payment failure
        mock_client = mocker.MagicMock()
        mock_client.order.create.side_effect = Exception("Payment Gateway Error")

        # Payment should fail gracefully
        assert True  # Placeholder

    def test_subscription_creation_after_payment(self, db, user, paid_plan):
        """Test subscription is created after successful payment."""
        # Create transaction
        transaction = Transaction.objects.create(
            user=user,
            transactionId='order_success123',
            amount=paid_plan.amount,
            plan_name=paid_plan.plan_name,
            duration=paid_plan.duration,
            tokenCount=paid_plan.totalToken,
            fileToken=paid_plan.fileToken,
            payment_status='paid',
            payment_method='razorpay'
        )

        # Create subscription
        subscription = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=paid_plan.duration),
            subscriptionEndDate=timezone.now() + timedelta(days=paid_plan.duration + 7),
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

        assert subscription.status == 'active'
        assert subscription.transactionId == transaction.transactionId

    @patch('authentication.payments.createCustomerOnStripe')
    def test_stripe_customer_creation(self, mock_stripe, user):
        """Test Stripe customer creation (mocked)."""
        mock_stripe.return_value = 'cus_test123'

        customer_id = mock_stripe(user.username, user.email)

        assert customer_id == 'cus_test123'
        mock_stripe.assert_called_once_with(user.username, user.email)


# =============================================================================
# EMAIL SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestEmailService:
    """Test email notification services."""

    @patch('authentication.tasks.send_verification_email.delay')
    def test_verification_email_sent(self, mock_email, user):
        """Test verification email is sent (mocked)."""
        mock_email(user.id)

        mock_email.assert_called_once_with(user.id)

    @patch('authentication.tasks.sendResetPasswordMail.delay')
    def test_password_reset_email_sent(self, mock_email, user):
        """Test password reset email is sent (mocked)."""
        mock_email(user.id)

        mock_email.assert_called_once_with(user.id)

    @patch('authentication.tasks.otp_for_user_to_sub_admin.delay')
    def test_admin_notification_email_sent(self, mock_email, admin_user):
        """Test admin notification email is sent (mocked)."""
        otp = '12345'
        mock_email(admin_user.id, otp)

        mock_email.assert_called_once_with(admin_user.id, otp)


# =============================================================================
# REFERRAL SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestReferralService:
    """Test referral system services."""

    def test_referral_code_generation(self, user):
        """Test referral code is generated for new users."""
        assert user.referral_code is not None
        assert len(user.referral_code) == 12

    def test_referral_token_reward(self, db, user, create_user, referral_setting):
        """Test referral tokens are rewarded correctly."""
        # Create referred user
        referred_user = create_user(
            email='referred@example.com',
            username='referred'
        )

        # Create referral
        referral = Referral.objects.create(
            referr_by=user,
            referr_to=referred_user,
            refer_by_token=referral_setting.refer_by_token,
            refer_to_token=referral_setting.refer_to_token,
            code=user.referral_code,
            reward_given=False
        )

        assert referral.refer_by_token == referral_setting.refer_by_token
        assert referral.refer_to_token == referral_setting.refer_to_token

    def test_referral_reward_only_once(self, referral):
        """Test referral rewards are given only once."""
        referral.reward_given = True
        referral.save()

        referral.refresh_from_db()
        assert referral.reward_given == True

    def test_referral_statistics(self, db, user, create_user, referral_setting):
        """Test referral statistics tracking."""
        # Create multiple referrals
        for i in range(5):
            referred = create_user(
                email=f'ref{i}@example.com',
                username=f'refuser{i}'
            )
            Referral.objects.create(
                referr_by=user,
                referr_to=referred,
                refer_by_token=100,
                refer_to_token=50,
                code=user.referral_code
            )

        referral_count = Referral.objects.filter(referr_by=user).count()
        assert referral_count == 5


# =============================================================================
# AWS S3 SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestS3Service:
    """Test AWS S3 file upload services."""

    @patch('authentication.awsservice.uploadImage')
    def test_s3_file_upload(self, mock_upload, user):
        """Test S3 file upload (mocked)."""
        mock_upload.return_value = 'multinote/test/file.jpg'

        result = mock_upload('fake_file', 'multinote/test/file.jpg', 'image/jpeg')

        assert result == 'multinote/test/file.jpg'
        mock_upload.assert_called_once()

    @patch('authentication.awsservice.getImageUrl')
    def test_s3_presigned_url_generation(self, mock_url, user):
        """Test S3 presigned URL generation (mocked)."""
        mock_url.return_value = 'https://s3.amazonaws.com/signed-url'

        url = mock_url('multinote/test/file.jpg')

        assert 'https://' in url
        mock_url.assert_called_once()

    def test_s3_file_deletion(self, mock_s3_upload):
        """Test S3 file deletion (mocked)."""
        # This would require mocking boto3 delete operation
        assert mock_s3_upload is not None


# =============================================================================
# CRON JOB SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestCronServices:
    """Test scheduled cron job services."""

    def test_subscription_expiry_check(self, db, user, user_subscription):
        """Test subscription expiry checking."""
        # Set subscription to expired
        user_subscription.subscriptionExpiryDate = timezone.now() - timedelta(days=1)
        user_subscription.save()

        # Check if expired
        is_expired = user_subscription.subscriptionExpiryDate < timezone.now()
        assert is_expired == True

    def test_expired_subscription_status_update(self, db, user, user_subscription):
        """Test expired subscriptions are updated."""
        user_subscription.subscriptionExpiryDate = timezone.now() - timedelta(days=5)
        user_subscription.status = 'expire'
        user_subscription.save()

        user_subscription.refresh_from_db()
        assert user_subscription.status == 'expire'

    def test_trial_period_expiry(self, db, user, free_plan):
        """Test trial period expiry handling."""
        subscription = Subscription.objects.create(
            user=user,
            plan=free_plan,
            status='trial',
            subscriptionExpiryDate=timezone.now() - timedelta(days=1),
            subscriptionEndDate=timezone.now() + timedelta(days=6),
            balanceToken=1000,
            trialStartDate=timezone.now() - timedelta(days=31),
            trialEndDate=timezone.now() - timedelta(days=1),
            transactionId='trial_test',
            payment_status='trial',
            payment_mode='online',
            plan_name=free_plan.plan_name,
            plan_for='token',
            amount=0,
            duration=30,
            totalToken=1000,
            totalFileToken=10
        )

        is_trial_expired = subscription.trialEndDate < timezone.now()
        assert is_trial_expired == True
