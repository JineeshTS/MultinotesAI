"""
Comprehensive model tests for MultinotesAI backend.

Tests cover:
- Model creation and validation
- Field constraints and validation
- Model relationships (ForeignKey, OneToOne, ManyToMany)
- Model methods and properties
- Database constraints
- Signal handlers
- Custom validators
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import timedelta
from django.utils import timezone
from authentication.models import (
    CustomUser, Role, Cluster, Referral, ReferralSetting,
    TokenBlacklist, generate_unique_referral_code
)
from planandsubscription.models import UserPlan, Subscription, Transaction
from coreapp.models import (
    LLM, Prompt, PromptResponse, Folder, Document,
    GroupResponse, UserContent, StorageUsage, LLM_Ratings,
    LLM_Tokens, NoteBook, Share
)
from ticketandcategory.models import MainCategory, Category, Coupon


# =============================================================================
# USER MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestCustomUserModel:
    """Test CustomUser model functionality."""

    def test_user_creation(self, create_user):
        """Test basic user creation."""
        user = create_user(email='test@example.com', username='testuser')

        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.username == 'testuser'
        assert user.is_verified == True
        assert user.is_delete == False

    def test_user_password_hashing(self, create_user):
        """Test password is hashed on creation."""
        password = 'SecurePass123!'
        user = create_user(email='hash@example.com', password=password)

        assert user.password != password
        assert user.password.startswith('pbkdf2_sha256$')

    def test_user_referral_code_auto_generation(self, create_user):
        """Test referral code is automatically generated."""
        user = create_user(email='referral@example.com', username='referraluser')

        assert user.referral_code is not None
        assert len(user.referral_code) == 12
        assert user.referral_code.isalnum()

    def test_user_referral_code_uniqueness(self, create_user):
        """Test referral codes are unique."""
        user1 = create_user(email='user1@example.com', username='user1')
        user2 = create_user(email='user2@example.com', username='user2')

        assert user1.referral_code != user2.referral_code

    def test_user_email_uniqueness(self, create_user):
        """Test email must be unique."""
        create_user(email='unique@example.com', username='user1')

        # Attempting to create another user with same email should fail
        with pytest.raises(Exception):  # Could be IntegrityError or ValidationError
            create_user(email='unique@example.com', username='user2')

    def test_user_phone_number_uniqueness(self, db):
        """Test phone number must be unique if provided."""
        CustomUser.objects.create_user(
            email='phone1@example.com',
            username='phoneuser1',
            phone_number='1234567890',
            password='Pass123!'
        )

        # Should raise error for duplicate phone
        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(
                email='phone2@example.com',
                username='phoneuser2',
                phone_number='1234567890',
                password='Pass123!'
            )

    def test_user_tokens_method(self, user):
        """Test tokens() method generates JWT tokens."""
        tokens = user.tokens()

        assert 'access' in tokens
        assert 'refresh' in tokens
        assert isinstance(tokens['access'], str)
        assert isinstance(tokens['refresh'], str)

    def test_user_str_representation(self, user):
        """Test __str__ method."""
        assert str(user) == user.username

    def test_superuser_auto_gets_admin_role(self, create_user):
        """Test superuser automatically gets admin role."""
        admin = create_user(
            email='admin@example.com',
            username='admin',
            is_superuser=True
        )

        assert admin.roles.filter(name='admin').exists()

    def test_user_cluster_relationship(self, create_user, cluster):
        """Test user can belong to a cluster."""
        user = create_user(
            email='cluster@testcompany.com',
            username='clusteruser',
            cluster=cluster
        )

        assert user.cluster == cluster
        assert user.cluster.cluster_name == cluster.cluster_name

    def test_user_roles_many_to_many(self, user, db):
        """Test user can have multiple roles."""
        role1 = Role.objects.create(name='role1')
        role2 = Role.objects.create(name='role2')

        user.roles.add(role1, role2)

        assert user.roles.count() == 2
        assert role1 in user.roles.all()
        assert role2 in user.roles.all()

    def test_user_soft_delete(self, user):
        """Test user soft delete functionality."""
        user.is_delete = True
        user.save()

        user.refresh_from_db()
        assert user.is_delete == True

    def test_user_block_functionality(self, user):
        """Test user blocking functionality."""
        user.is_blocked = True
        user.save()

        user.refresh_from_db()
        assert user.is_blocked == True


# =============================================================================
# ROLE MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestRoleModel:
    """Test Role model functionality."""

    def test_role_creation(self, db):
        """Test role creation."""
        role = Role.objects.create(name='custom_role')

        assert role.id is not None
        assert role.name == 'custom_role'

    def test_role_name_uniqueness(self, db):
        """Test role names must be unique."""
        Role.objects.create(name='unique_role')

        with pytest.raises(IntegrityError):
            Role.objects.create(name='unique_role')

    def test_role_str_representation(self, db):
        """Test __str__ method."""
        role = Role.objects.create(name='test_role')

        assert str(role) == 'test_role'


# =============================================================================
# CLUSTER MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestClusterModel:
    """Test Cluster model functionality."""

    def test_cluster_creation(self, cluster):
        """Test cluster creation."""
        assert cluster.id is not None
        assert cluster.cluster_name == 'Test Company'
        assert cluster.domain == 'testcompany.com'
        assert cluster.is_enabled == True

    def test_cluster_domain_validator(self, db, free_plan, storage_plan):
        """Test domain cannot contain @ symbol."""
        with pytest.raises(ValidationError):
            cluster = Cluster(
                plan=free_plan,
                storage_plan=storage_plan,
                cluster_name='Invalid Cluster',
                org_name='Invalid Corp',
                email='test@invalid.com',
                domain='invalid@domain.com'  # Invalid
            )
            cluster.full_clean()  # Trigger validation

    def test_cluster_plan_relationship(self, cluster):
        """Test cluster has plan relationship."""
        assert cluster.plan is not None
        assert isinstance(cluster.plan, UserPlan)

    def test_cluster_subscription_relationship(self, db, cluster, free_plan):
        """Test cluster can have subscription."""
        subscription = Subscription.objects.create(
            user=CustomUser.objects.first(),
            plan=free_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=1000,
            transactionId='cluster_sub',
            payment_status='paid',
            payment_mode='online',
            plan_name=free_plan.plan_name,
            plan_for='token',
            amount=0,
            duration=30,
            totalToken=1000,
            totalFileToken=10
        )

        cluster.subscription = subscription
        cluster.save()

        assert cluster.subscription == subscription

    def test_cluster_str_representation(self, cluster):
        """Test __str__ method."""
        assert str(cluster) == cluster.cluster_name


# =============================================================================
# PLAN MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestUserPlanModel:
    """Test UserPlan model functionality."""

    def test_plan_creation(self, free_plan):
        """Test plan creation."""
        assert free_plan.id is not None
        assert free_plan.plan_name == 'Free Plan'
        assert free_plan.is_free == True
        assert free_plan.amount == 0

    def test_plan_token_fields(self, paid_plan):
        """Test plan token fields."""
        assert paid_plan.totalToken > 0
        assert paid_plan.fileToken > 0
        assert paid_plan.plan_for == 'token'

    def test_plan_storage_fields(self, storage_plan):
        """Test plan storage fields."""
        assert storage_plan.storage_size > 0
        assert storage_plan.plan_for == 'storage'

    def test_plan_status_choices(self, db):
        """Test plan status choices."""
        active_plan = UserPlan.objects.create(
            plan_name='Active Plan',
            amount=100,
            duration=30,
            status='active',
            plan_for='token'
        )

        inactive_plan = UserPlan.objects.create(
            plan_name='Inactive Plan',
            amount=100,
            duration=30,
            status='inactive',
            plan_for='token'
        )

        assert active_plan.status == 'active'
        assert inactive_plan.status == 'inactive'

    def test_plan_str_representation(self, free_plan):
        """Test __str__ method."""
        assert str(free_plan) == free_plan.plan_name

    def test_plan_soft_delete(self, free_plan):
        """Test plan soft delete."""
        free_plan.is_delete = True
        free_plan.save()

        free_plan.refresh_from_db()
        assert free_plan.is_delete == True


# =============================================================================
# SUBSCRIPTION MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionModel:
    """Test Subscription model functionality."""

    def test_subscription_creation(self, user_subscription):
        """Test subscription creation."""
        assert user_subscription.id is not None
        assert user_subscription.status == 'active'
        assert user_subscription.balanceToken > 0

    def test_subscription_user_relationship(self, user, user_subscription):
        """Test subscription belongs to user."""
        assert user_subscription.user == user

    def test_subscription_plan_relationship(self, user_subscription, free_plan):
        """Test subscription references plan."""
        assert user_subscription.plan == free_plan

    def test_subscription_token_tracking(self, user_subscription):
        """Test subscription tracks token usage."""
        initial_balance = user_subscription.balanceToken

        # Simulate token usage
        user_subscription.balanceToken -= 100
        user_subscription.usedToken += 100
        user_subscription.save()

        user_subscription.refresh_from_db()
        assert user_subscription.balanceToken == initial_balance - 100
        assert user_subscription.usedToken == 100

    def test_subscription_expiry_dates(self, user_subscription):
        """Test subscription has expiry dates."""
        assert user_subscription.subscriptionExpiryDate is not None
        assert user_subscription.subscriptionEndDate is not None
        assert user_subscription.subscriptionEndDate > user_subscription.subscriptionExpiryDate

    def test_subscription_status_choices(self, db, user, free_plan):
        """Test subscription status choices."""
        active = Subscription.objects.create(
            user=user,
            plan=free_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=1000,
            transactionId='active_test',
            payment_status='paid',
            payment_mode='online',
            plan_name='Active',
            plan_for='token',
            amount=0,
            duration=30,
            totalToken=1000,
            totalFileToken=10
        )

        assert active.status == 'active'

    def test_subscription_coupon_fields(self, db, user, paid_plan):
        """Test subscription can have coupon details."""
        subscription = Subscription.objects.create(
            user=user,
            plan=paid_plan,
            status='active',
            subscriptionExpiryDate=timezone.now() + timedelta(days=30),
            subscriptionEndDate=timezone.now() + timedelta(days=37),
            balanceToken=1000,
            transactionId='coupon_test',
            payment_status='paid',
            payment_mode='online',
            plan_name='Test',
            plan_for='token',
            amount=899,
            duration=30,
            totalToken=1000,
            totalFileToken=10,
            coupon_code='SAVE20',
            coupon_type='percentage',
            discount_value=20,
            bonus_token=50
        )

        assert subscription.coupon_code == 'SAVE20'
        assert subscription.bonus_token == 50

    def test_subscription_str_representation(self, user_subscription):
        """Test __str__ method."""
        assert str(user_subscription) == user_subscription.plan.plan_name


# =============================================================================
# TRANSACTION MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestTransactionModel:
    """Test Transaction model functionality."""

    def test_transaction_creation(self, transaction):
        """Test transaction creation."""
        assert transaction.id is not None
        assert transaction.payment_status == 'paid'

    def test_transaction_unique_id(self, db, user, paid_plan):
        """Test transaction ID must be unique."""
        Transaction.objects.create(
            user=user,
            transactionId='unique_123',
            amount=1000,
            plan_name='Test',
            duration=30,
            tokenCount=1000,
            fileToken=10,
            payment_status='paid',
            payment_method='razorpay'
        )

        with pytest.raises(IntegrityError):
            Transaction.objects.create(
                user=user,
                transactionId='unique_123',  # Duplicate
                amount=1000,
                plan_name='Test',
                duration=30,
                tokenCount=1000,
                fileToken=10,
                payment_status='paid',
                payment_method='razorpay'
            )

    def test_transaction_payment_status_choices(self, db, user, paid_plan):
        """Test transaction payment status choices."""
        paid_txn = Transaction.objects.create(
            user=user,
            transactionId='paid_123',
            amount=1000,
            plan_name='Test',
            duration=30,
            tokenCount=1000,
            fileToken=10,
            payment_status='paid',
            payment_method='razorpay'
        )

        pending_txn = Transaction.objects.create(
            user=user,
            transactionId='pending_123',
            amount=1000,
            plan_name='Test',
            duration=30,
            tokenCount=1000,
            fileToken=10,
            payment_status='pending',
            payment_method='razorpay'
        )

        assert paid_txn.payment_status == 'paid'
        assert pending_txn.payment_status == 'pending'


# =============================================================================
# LLM MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestLLMModel:
    """Test LLM model functionality."""

    def test_llm_creation(self, llm_together):
        """Test LLM creation."""
        assert llm_together.id is not None
        assert llm_together.name == 'Llama-3-70B'
        assert llm_together.is_enabled == True

    def test_llm_source_types(self, llm_together, llm_gemini, llm_openai):
        """Test different LLM sources."""
        assert llm_together.source == 2  # Together
        assert llm_gemini.source == 3    # Gemini
        assert llm_openai.source == 4    # OpenAI

    def test_llm_capability_flags(self, llm_together):
        """Test LLM capability boolean flags."""
        assert llm_together.text == True
        assert llm_together.code == True

    def test_llm_disabled_model(self, disabled_llm):
        """Test disabled LLM model."""
        assert disabled_llm.is_enabled == False
        assert disabled_llm.test_status == 'disconnected'

    def test_llm_str_representation(self, llm_together):
        """Test __str__ method."""
        assert str(llm_together) == llm_together.name

    def test_llm_soft_delete(self, llm_together):
        """Test LLM soft delete."""
        llm_together.is_delete = True
        llm_together.save()

        llm_together.refresh_from_db()
        assert llm_together.is_delete == True


# =============================================================================
# FOLDER MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestFolderModel:
    """Test Folder model functionality."""

    def test_folder_creation(self, folder):
        """Test folder creation."""
        assert folder.id is not None
        assert folder.title == 'Test Folder'
        assert folder.is_active == True

    def test_folder_user_relationship(self, folder, user):
        """Test folder belongs to user."""
        assert folder.user == user

    def test_folder_subfolder_relationship(self, db, user, folder):
        """Test folder can have subfolders."""
        subfolder = Folder.objects.create(
            title='Subfolder',
            user=user,
            parent_folder=folder
        )

        assert subfolder.parent_folder == folder
        assert subfolder in folder.subfolders.all()

    def test_folder_str_representation(self, folder):
        """Test __str__ method."""
        assert str(folder) == folder.title

    def test_folder_soft_delete(self, folder):
        """Test folder soft delete."""
        folder.is_delete = True
        folder.save()

        folder.refresh_from_db()
        assert folder.is_delete == True


# =============================================================================
# PROMPT MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestPromptModel:
    """Test Prompt model functionality."""

    def test_prompt_creation(self, prompt):
        """Test prompt creation."""
        assert prompt.id is not None
        assert prompt.prompt_text == 'Write a story about a robot'
        assert prompt.response_type == 2

    def test_prompt_user_relationship(self, prompt, user):
        """Test prompt belongs to user."""
        assert prompt.user == user

    def test_prompt_category_relationship(self, prompt, category):
        """Test prompt belongs to category."""
        assert prompt.category == category

    def test_prompt_group_relationship(self, db, user, category, llm_together):
        """Test prompt can belong to conversation group."""
        group = GroupResponse.objects.create(
            user=user,
            category=category,
            llm=llm_together,
            group_name='Test Group'
        )

        prompt = Prompt.objects.create(
            user=user,
            group=group,
            prompt_text='Test in group',
            category=category,
            response_type=2,
            title='Group Prompt'
        )

        assert prompt.group == group

    def test_prompt_auto_title_generation(self, db, user, category):
        """Test prompt generates default title if not provided."""
        prompt = Prompt.objects.create(
            user=user,
            prompt_text='Test',
            category=category,
            response_type=2
        )

        # Should have auto-generated title
        assert prompt.title is not None
        assert 'prompt-' in prompt.title

    def test_prompt_str_representation(self, prompt):
        """Test __str__ method."""
        expected = f"{prompt.user.username} - {prompt.title}"
        assert str(prompt) == expected

    def test_prompt_soft_delete(self, prompt):
        """Test prompt soft delete."""
        prompt.is_delete = True
        prompt.save()

        prompt.refresh_from_db()
        assert prompt.is_delete == True


# =============================================================================
# PROMPT RESPONSE MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestPromptResponseModel:
    """Test PromptResponse model functionality."""

    def test_prompt_response_creation(self, prompt_response):
        """Test prompt response creation."""
        assert prompt_response.id is not None
        assert prompt_response.response_text is not None
        assert prompt_response.tokenUsed > 0

    def test_prompt_response_relationships(self, prompt_response, user, prompt, llm_together, category):
        """Test prompt response relationships."""
        assert prompt_response.user == user
        assert prompt_response.prompt == prompt
        assert prompt_response.llm == llm_together
        assert prompt_response.category == category

    def test_prompt_response_type_method(self, prompt_response):
        """Test get_response_type method."""
        # Text response
        assert prompt_response.response_text is not None
        response_type = prompt_response.get_response_type()
        assert response_type == 'text'

    def test_prompt_response_image_type(self, db, user, prompt, llm_openai, category):
        """Test image response type."""
        response = PromptResponse.objects.create(
            user=user,
            prompt=prompt,
            llm=llm_openai,
            response_image='path/to/image.jpg',
            response_type=4,
            category=category,
            tokenUsed=50
        )

        assert response.get_response_type() == 'image'

    def test_prompt_response_str_representation(self, prompt_response):
        """Test __str__ method."""
        expected = f"Response for {prompt_response.llm.name}"
        assert str(prompt_response) == expected


# =============================================================================
# CATEGORY MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestCategoryModels:
    """Test Category and MainCategory models."""

    def test_main_category_creation(self, main_category):
        """Test main category creation."""
        assert main_category.id is not None
        assert main_category.name == 'Content Generation'
        assert main_category.status == 'active'

    def test_category_creation(self, category):
        """Test category creation."""
        assert category.id is not None
        assert category.name == 'Text Generation'
        assert category.alias_name == 'text-generation'

    def test_category_main_category_relationship(self, category, main_category):
        """Test category belongs to main category."""
        assert category.mainCategory == main_category


# =============================================================================
# COUPON MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestCouponModel:
    """Test Coupon model functionality."""

    def test_percentage_coupon_creation(self, percentage_coupon):
        """Test percentage coupon creation."""
        assert percentage_coupon.id is not None
        assert percentage_coupon.coupon_type == 'percentage'
        assert percentage_coupon.discount_value == 20

    def test_fixed_coupon_creation(self, fixed_coupon):
        """Test fixed amount coupon creation."""
        assert fixed_coupon.id is not None
        assert fixed_coupon.coupon_type == 'fixed'
        assert fixed_coupon.discount_value == 100

    def test_coupon_validity_dates(self, percentage_coupon):
        """Test coupon has validity dates."""
        assert percentage_coupon.start_date is not None
        assert percentage_coupon.end_date is not None
        assert percentage_coupon.end_date > percentage_coupon.start_date

    def test_expired_coupon(self, expired_coupon):
        """Test expired coupon."""
        assert expired_coupon.end_date < timezone.now()


# =============================================================================
# REFERRAL MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestReferralModels:
    """Test Referral and ReferralSetting models."""

    def test_referral_creation(self, referral):
        """Test referral creation."""
        assert referral.id is not None
        assert referral.referr_by is not None
        assert referral.referr_to is not None

    def test_referral_token_rewards(self, referral):
        """Test referral has token rewards."""
        assert referral.refer_by_token > 0
        assert referral.refer_to_token > 0

    def test_referral_reward_flag(self, referral):
        """Test referral reward flag."""
        assert referral.reward_given == False

        referral.reward_given = True
        referral.save()

        referral.refresh_from_db()
        assert referral.reward_given == True

    def test_referral_setting_creation(self, referral_setting):
        """Test referral setting creation."""
        assert referral_setting.id is not None
        assert referral_setting.isToken == True
        assert referral_setting.refer_by_token > 0

    def test_referral_unique_code_generation(self):
        """Test referral code generation utility."""
        code1 = generate_unique_referral_code()
        code2 = generate_unique_referral_code()

        assert len(code1) == 12
        assert len(code2) == 12
        # Codes should be different (statistically)
        assert code1 != code2


# =============================================================================
# STORAGE MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestStorageUsageModel:
    """Test StorageUsage model functionality."""

    def test_storage_creation(self, db, user, storage_plan):
        """Test storage usage creation."""
        storage = StorageUsage.objects.create(
            user=user,
            plan=storage_plan,
            storage_limit=1024 * 1024 * 100,  # 100 MB
            total_storage_used=0,
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

        assert storage.id is not None
        assert storage.storage_limit > 0

    def test_storage_usage_tracking(self, db, user, storage_plan):
        """Test storage usage tracking."""
        storage = StorageUsage.objects.create(
            user=user,
            plan=storage_plan,
            storage_limit=1024 * 1024 * 100,
            total_storage_used=1024 * 1024 * 50,  # 50 MB used
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

        assert storage.total_storage_used == 1024 * 1024 * 50

    def test_storage_str_representation(self, db, user, storage_plan):
        """Test __str__ method."""
        storage = StorageUsage.objects.create(
            user=user,
            plan=storage_plan,
            storage_limit=1024 * 1024 * 100,
            total_storage_used=1024 * 1024 * 25,
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

        expected = f"{user.username} - {storage.total_storage_used} bytes used"
        assert str(storage) == expected


# =============================================================================
# LLM RATINGS MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestLLMRatingsModel:
    """Test LLM_Ratings model functionality."""

    def test_rating_creation(self, db, user, llm_together):
        """Test LLM rating creation."""
        rating = LLM_Ratings.objects.create(
            user=user,
            llm=llm_together,
            review='Great model!',
            rating=5
        )

        assert rating.id is not None
        assert rating.rating == 5

    def test_rating_validation(self, db, user, llm_together):
        """Test rating must be between 1 and 5."""
        # Valid ratings
        for r in range(1, 6):
            rating = LLM_Ratings(
                user=user,
                llm=llm_together,
                rating=r
            )
            rating.full_clean()  # Should not raise

    def test_rating_average_calculation(self, db, user, create_user, llm_together):
        """Test average rating calculation."""
        # Create multiple ratings
        LLM_Ratings.objects.create(user=user, llm=llm_together, rating=5)
        user2 = create_user(email='user2@example.com', username='user2')
        LLM_Ratings.objects.create(user=user2, llm=llm_together, rating=3)
        user3 = create_user(email='user3@example.com', username='user3')
        LLM_Ratings.objects.create(user=user3, llm=llm_together, rating=4)

        avg = LLM_Ratings.get_average_rating_for_llm(llm_together.id)
        assert avg == 4.0  # (5+3+4)/3


# =============================================================================
# LLM TOKENS MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestLLMTokensModel:
    """Test LLM_Tokens model functionality."""

    def test_token_usage_tracking(self, db, user, llm_together, prompt):
        """Test token usage tracking."""
        token_usage = LLM_Tokens.objects.create(
            user=user,
            llm=llm_together,
            prompt=prompt,
            text_token_used=100,
            file_token_used=5
        )

        assert token_usage.id is not None
        assert token_usage.text_token_used == 100
        assert token_usage.file_token_used == 5

    def test_total_token_calculation(self, db, user, llm_together, prompt):
        """Test total token calculation methods."""
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

        total_text = LLM_Tokens.get_total_text_token_used_for_llm(llm_together.id)
        total_file = LLM_Tokens.get_total_file_token_used_for_llm(llm_together.id)

        assert total_text == 300
        assert total_file == 15
