"""
Migration to add database indexes for planandsubscription models.

This migration adds indexes to frequently queried fields in subscription
and transaction models to improve query performance.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planandsubscription', '0001_initial'),
    ]

    operations = [
        # UserPlan Indexes
        migrations.AddIndex(
            model_name='userplan',
            index=models.Index(fields=['status', 'is_delete'], name='plan_status_idx'),
        ),
        migrations.AddIndex(
            model_name='userplan',
            index=models.Index(fields=['plan_for', 'is_delete'], name='plan_type_idx'),
        ),
        migrations.AddIndex(
            model_name='userplan',
            index=models.Index(fields=['is_free', 'is_delete'], name='plan_free_idx'),
        ),
        migrations.AddIndex(
            model_name='userplan',
            index=models.Index(fields=['is_for_cluster', 'is_delete'], name='plan_cluster_idx'),
        ),

        # Subscription Indexes
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['user', 'is_delete'], name='sub_user_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['status', 'is_delete'], name='sub_status_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['user', 'status', 'is_delete'], name='sub_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['subscriptionExpiryDate'], name='sub_expiry_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['subscriptionEndDate'], name='sub_end_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['payment_status', 'is_delete'], name='sub_payment_idx'),
        ),

        # Transaction Indexes
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'is_delete'], name='trans_user_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['transactionId'], name='trans_id_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['payment_status', 'is_delete'], name='trans_status_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['created_at'], name='trans_created_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'created_at'], name='trans_user_created_idx'),
        ),
    ]
