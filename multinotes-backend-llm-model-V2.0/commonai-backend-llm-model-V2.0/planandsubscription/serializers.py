from rest_framework import serializers
from .models import UserPlan, Subscription, Transaction

### Create Different Serializer for More Code and Logic Control.

class ModelPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPlan
        fields = ["id", "plan_name", "plan_for", "duration", "totalToken", "fileToken", ]

class AddPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPlan
        fields = '__all__'



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

