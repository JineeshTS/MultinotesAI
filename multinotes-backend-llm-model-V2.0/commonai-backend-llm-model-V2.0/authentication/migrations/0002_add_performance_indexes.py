"""
Migration to add database indexes for authentication models.

This migration adds indexes to frequently queried fields in authentication
models to improve query performance.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        # CustomUser Indexes
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['email'], name='user_email_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['username'], name='user_username_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['is_blocked', 'is_delete'], name='user_blocked_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['cluster', 'is_delete'], name='user_cluster_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['referral_code'], name='user_referral_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['is_verified', 'is_delete'], name='user_verified_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['created_at'], name='user_created_idx'),
        ),

        # Cluster Indexes
        migrations.AddIndex(
            model_name='cluster',
            index=models.Index(fields=['domain', 'is_delete'], name='cluster_domain_idx'),
        ),
        migrations.AddIndex(
            model_name='cluster',
            index=models.Index(fields=['email'], name='cluster_email_idx'),
        ),

        # Referral Indexes
        migrations.AddIndex(
            model_name='referral',
            index=models.Index(fields=['referr_by', 'is_delete'], name='referral_by_idx'),
        ),
        migrations.AddIndex(
            model_name='referral',
            index=models.Index(fields=['referr_to', 'is_delete'], name='referral_to_idx'),
        ),
        migrations.AddIndex(
            model_name='referral',
            index=models.Index(fields=['referr_to', 'reward_given', 'is_delete'], name='referral_reward_idx'),
        ),
    ]
