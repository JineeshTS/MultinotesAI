from rest_framework import serializers
from .models import UserPlan, Subscription, Transaction
from decimal import Decimal, InvalidOperation

### Create Different Serializer for More Code and Logic Control.


def validate_positive_decimal(value, field_name="Value"):
    """Validate that a value is a positive decimal."""
    if value is None:
        return value
    try:
        decimal_value = Decimal(str(value))
        if decimal_value < 0:
            raise serializers.ValidationError(f"{field_name} must be a positive number.")
        return decimal_value
    except (InvalidOperation, ValueError):
        raise serializers.ValidationError(f"{field_name} must be a valid number.")


def validate_positive_integer(value, field_name="Value"):
    """Validate that a value is a positive integer."""
    if value is None:
        return value
    if not isinstance(value, int) or value < 0:
        raise serializers.ValidationError(f"{field_name} must be a positive integer.")
    return value


class ModelPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPlan
        fields = ["id", "plan_name", "plan_for", "duration", "totalToken", "fileToken", ]


class AddPlanSerializer(serializers.ModelSerializer):
    """Serializer for creating subscription plans with validation."""

    class Meta:
        model = UserPlan
        fields = '__all__'

    def validate_plan_name(self, value):
        """Validate plan name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Plan name must be at least 2 characters.")
        if len(value) > 100:
            raise serializers.ValidationError("Plan name cannot exceed 100 characters.")
        return value.strip()

    def validate_price(self, value):
        """Validate price is positive."""
        return validate_positive_decimal(value, "Price")

    def validate_totalToken(self, value):
        """Validate total tokens is positive."""
        return validate_positive_integer(value, "Total tokens")

    def validate_fileToken(self, value):
        """Validate file tokens is positive."""
        return validate_positive_integer(value, "File tokens")

    def validate_duration(self, value):
        """Validate duration is positive."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Duration must be greater than 0.")
        return value

    def validate_storage_size(self, value):
        """Validate storage size is positive."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Storage size must be non-negative.")
        return value


class GetPlanSerializer(serializers.ModelSerializer):
    storage_size = serializers.SerializerMethodField()
    class Meta:
        model = UserPlan
        fields = '__all__'

    def get_storage_size(self, obj):
        return round(obj.storage_size/(1024*1024*1024), 2)
    

class GetUserPlanSerializer(serializers.ModelSerializer):
    storage_size = serializers.SerializerMethodField()
    class Meta:
        model = UserPlan
        fields = '__all__'

    def get_storage_size(self, obj):
        return round(obj.storage_size/(1024*1024*1024), 2)


class UpdatePlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserPlan
        fields = '__all__'


# Subscription Section
class GetSubscriptionSerializer(serializers.ModelSerializer):
    plan = GetPlanSerializer()
    class Meta:
        model = Subscription
        fields = '__all__'

# Subscription Section
class GetClusterSerializer(serializers.ModelSerializer):
    plan = GetPlanSerializer()
    class Meta:
        model = Subscription
        fields = '__all__'


class CreateSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


class UpdateSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


# Transaction Section
class GetTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class CreateTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class UpdateTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

