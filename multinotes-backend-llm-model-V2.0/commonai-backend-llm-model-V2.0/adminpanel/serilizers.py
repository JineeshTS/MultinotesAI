from rest_framework import serializers
from authentication.models import CustomUser
from coreapp.models import Prompt, NoteBook
from coreapp.serializers import SinglePromptSerializer, SingleNoteBookSerializer


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id','email','username','is_blocked']


class SingleUserSerializer(serializers.ModelSerializer):
    prompts = serializers.SerializerMethodField()
    notebooks = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['id','email','username','is_blocked','prompts','notebooks']

    def get_prompts(self, obj):
        prompts_queryset = Prompt.objects.filter(user=obj)
        prompts_count = prompts_queryset.count()
        prompts_data = SinglePromptSerializer(prompts_queryset, many=True, context=self.context).data

        return {
            'count': prompts_count,
            'prompts': prompts_data
        }
    
    def get_notebooks(self, obj):
        notebooks_queryset = NoteBook.objects.filter(user=obj)
        notebooks_count = notebooks_queryset.count()
        notebooks_data = SingleNoteBookSerializer(notebooks_queryset, many=True, context=self.context).data

        return {
            'count': notebooks_count,
            'prompts': notebooks_data
        }
    


        