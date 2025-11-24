"""
Migration to add database indexes for query performance optimization.

This migration adds indexes to frequently queried fields across all models
to improve query performance for common operations.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coreapp', '0001_initial'),
    ]

    operations = [
        # LLM Model Indexes
        migrations.AddIndex(
            model_name='llm',
            index=models.Index(fields=['name', 'is_enabled', 'is_delete'], name='llm_lookup_idx'),
        ),
        migrations.AddIndex(
            model_name='llm',
            index=models.Index(fields=['source', 'is_enabled'], name='llm_source_idx'),
        ),
        migrations.AddIndex(
            model_name='llm',
            index=models.Index(fields=['test_status'], name='llm_status_idx'),
        ),

        # LLM_Ratings Indexes
        migrations.AddIndex(
            model_name='llm_ratings',
            index=models.Index(fields=['llm', 'is_delete'], name='llm_ratings_llm_idx'),
        ),
        migrations.AddIndex(
            model_name='llm_ratings',
            index=models.Index(fields=['user', 'llm'], name='llm_ratings_user_llm_idx'),
        ),

        # UserLLM Indexes
        migrations.AddIndex(
            model_name='userllm',
            index=models.Index(fields=['user', 'is_delete'], name='userllm_user_idx'),
        ),

        # Folder Indexes
        migrations.AddIndex(
            model_name='folder',
            index=models.Index(fields=['user', 'is_delete'], name='folder_user_idx'),
        ),
        migrations.AddIndex(
            model_name='folder',
            index=models.Index(fields=['parent_folder', 'is_delete'], name='folder_parent_idx'),
        ),
        migrations.AddIndex(
            model_name='folder',
            index=models.Index(fields=['user', 'is_active', 'is_delete'], name='folder_active_idx'),
        ),

        # GroupResponse Indexes
        migrations.AddIndex(
            model_name='groupresponse',
            index=models.Index(fields=['user', 'is_delete'], name='groupresp_user_idx'),
        ),
        migrations.AddIndex(
            model_name='groupresponse',
            index=models.Index(fields=['user', 'category', 'is_delete'], name='groupresp_user_cat_idx'),
        ),
        migrations.AddIndex(
            model_name='groupresponse',
            index=models.Index(fields=['created_at'], name='groupresp_created_idx'),
        ),

        # Prompt Indexes (most critical for performance)
        migrations.AddIndex(
            model_name='prompt',
            index=models.Index(fields=['user', 'is_delete'], name='prompt_user_idx'),
        ),
        migrations.AddIndex(
            model_name='prompt',
            index=models.Index(fields=['user', 'category', 'is_delete'], name='prompt_user_cat_idx'),
        ),
        migrations.AddIndex(
            model_name='prompt',
            index=models.Index(fields=['group', 'is_delete'], name='prompt_group_idx'),
        ),
        migrations.AddIndex(
            model_name='prompt',
            index=models.Index(fields=['response_type', 'is_delete'], name='prompt_type_idx'),
        ),
        migrations.AddIndex(
            model_name='prompt',
            index=models.Index(fields=['user', 'created_at'], name='prompt_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='prompt',
            index=models.Index(fields=['is_saved', 'is_delete'], name='prompt_saved_idx'),
        ),

        # PromptResponse Indexes
        migrations.AddIndex(
            model_name='promptresponse',
            index=models.Index(fields=['user', 'is_delete'], name='promptresp_user_idx'),
        ),
        migrations.AddIndex(
            model_name='promptresponse',
            index=models.Index(fields=['prompt', 'is_delete'], name='promptresp_prompt_idx'),
        ),
        migrations.AddIndex(
            model_name='promptresponse',
            index=models.Index(fields=['llm', 'is_delete'], name='promptresp_llm_idx'),
        ),
        migrations.AddIndex(
            model_name='promptresponse',
            index=models.Index(fields=['user', 'category', 'is_delete'], name='promptresp_user_cat_idx'),
        ),
        migrations.AddIndex(
            model_name='promptresponse',
            index=models.Index(fields=['response_type', 'is_delete'], name='promptresp_type_idx'),
        ),
        migrations.AddIndex(
            model_name='promptresponse',
            index=models.Index(fields=['created_at'], name='promptresp_created_idx'),
        ),

        # StorageUsage Indexes
        migrations.AddIndex(
            model_name='storageusage',
            index=models.Index(fields=['status', 'is_delete'], name='storage_status_idx'),
        ),

        # LLM_Tokens Indexes
        migrations.AddIndex(
            model_name='llm_tokens',
            index=models.Index(fields=['user', 'is_delete'], name='llmtokens_user_idx'),
        ),
        migrations.AddIndex(
            model_name='llm_tokens',
            index=models.Index(fields=['llm', 'is_delete'], name='llmtokens_llm_idx'),
        ),
        migrations.AddIndex(
            model_name='llm_tokens',
            index=models.Index(fields=['user', 'created_at'], name='llmtokens_user_created_idx'),
        ),

        # NoteBook Indexes
        migrations.AddIndex(
            model_name='notebook',
            index=models.Index(fields=['user', 'is_delete'], name='notebook_user_idx'),
        ),
        migrations.AddIndex(
            model_name='notebook',
            index=models.Index(fields=['folder', 'is_delete'], name='notebook_folder_idx'),
        ),

        # Document Indexes
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['user', 'is_delete'], name='document_user_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['folder', 'is_delete'], name='document_folder_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['user', 'category', 'is_delete'], name='document_user_cat_idx'),
        ),

        # UserContent Indexes
        migrations.AddIndex(
            model_name='usercontent',
            index=models.Index(fields=['user', 'is_delete'], name='usercontent_user_idx'),
        ),
        migrations.AddIndex(
            model_name='usercontent',
            index=models.Index(fields=['folder', 'is_delete'], name='usercontent_folder_idx'),
        ),
        migrations.AddIndex(
            model_name='usercontent',
            index=models.Index(fields=['user', 'is_active', 'is_delete'], name='usercontent_active_idx'),
        ),

        # Share Indexes
        migrations.AddIndex(
            model_name='share',
            index=models.Index(fields=['owner', 'is_delete'], name='share_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='share',
            index=models.Index(fields=['share_to_user', 'is_delete'], name='share_recipient_idx'),
        ),
        migrations.AddIndex(
            model_name='share',
            index=models.Index(fields=['content_type', 'is_delete'], name='share_type_idx'),
        ),
        migrations.AddIndex(
            model_name='share',
            index=models.Index(fields=['folder', 'is_delete'], name='share_folder_idx'),
        ),

        # AiProcess Indexes
        migrations.AddIndex(
            model_name='aiprocess',
            index=models.Index(fields=['user', 'is_delete'], name='aiprocess_user_idx'),
        ),
        migrations.AddIndex(
            model_name='aiprocess',
            index=models.Index(fields=['url_status', 'is_delete'], name='aiprocess_status_idx'),
        ),
    ]
