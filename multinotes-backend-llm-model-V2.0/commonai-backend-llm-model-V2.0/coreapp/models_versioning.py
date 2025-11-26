"""
Content Versioning Models for MultinotesAI.

This module provides:
- Content version history tracking
- Revision management
- Diff generation
- Version restoration
"""

import json
import difflib
from datetime import datetime
from typing import Optional, List, Dict, Any

from django.db import models
from django.conf import settings
from django.utils import timezone


# =============================================================================
# Content Version Model
# =============================================================================

class ContentVersion(models.Model):
    """
    Stores historical versions of content.

    Each edit creates a new version record, enabling full history tracking
    and the ability to restore any previous version.
    """

    # Reference to the content
    content = models.ForeignKey(
        'coreapp.ContentGen',
        on_delete=models.CASCADE,
        related_name='versions'
    )

    # Version metadata
    version_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='content_versions'
    )

    # Snapshot of content at this version
    title = models.CharField(max_length=500)
    content_body = models.TextField(blank=True)
    user_prompt = models.TextField(blank=True)

    # Change metadata
    change_type = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('edited', 'Edited'),
            ('auto_saved', 'Auto-saved'),
            ('restored', 'Restored'),
            ('ai_generated', 'AI Generated'),
        ],
        default='edited'
    )
    change_summary = models.CharField(max_length=255, blank=True)

    # Size tracking for storage management
    size_bytes = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'content_versions'
        indexes = [
            models.Index(fields=['content', '-version_number']),
            models.Index(fields=['content', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
        ]
        ordering = ['-version_number']
        unique_together = ['content', 'version_number']

    def __str__(self):
        return f"{self.content.title} v{self.version_number}"

    def save(self, *args, **kwargs):
        # Calculate size
        self.size_bytes = len(self.content_body.encode('utf-8'))
        super().save(*args, **kwargs)

    def get_diff(self, other_version: 'ContentVersion') -> Dict[str, Any]:
        """
        Get diff between this version and another.

        Args:
            other_version: Version to compare against

        Returns:
            Dict with diff information
        """
        diff = {
            'title_changed': self.title != other_version.title,
            'content_diff': list(difflib.unified_diff(
                other_version.content_body.splitlines(keepends=True),
                self.content_body.splitlines(keepends=True),
                fromfile=f'v{other_version.version_number}',
                tofile=f'v{self.version_number}',
                lineterm=''
            )),
            'from_version': other_version.version_number,
            'to_version': self.version_number,
        }
        return diff


# =============================================================================
# Version Service
# =============================================================================

class ContentVersionService:
    """
    Service for managing content versions.

    Usage:
        service = ContentVersionService()
        version = service.create_version(content, user, change_type='edited')
        service.restore_version(content, version_number, user)
    """

    # Configuration
    MAX_VERSIONS_PER_CONTENT = 100  # Keep last 100 versions
    AUTO_SAVE_INTERVAL_SECONDS = 30  # Minimum time between auto-saves

    def create_version(
        self,
        content,
        user,
        change_type: str = 'edited',
        change_summary: str = ''
    ) -> ContentVersion:
        """
        Create a new version for content.

        Args:
            content: ContentGen instance
            user: User making the change
            change_type: Type of change
            change_summary: Brief description of changes

        Returns:
            Created ContentVersion instance
        """
        # Get next version number
        last_version = ContentVersion.objects.filter(
            content=content
        ).order_by('-version_number').first()

        next_version = (last_version.version_number + 1) if last_version else 1

        # Create version
        version = ContentVersion.objects.create(
            content=content,
            version_number=next_version,
            created_by=user,
            title=content.title,
            content_body=getattr(content, 'generatedResponse', '') or '',
            user_prompt=getattr(content, 'userPrompt', '') or '',
            change_type=change_type,
            change_summary=change_summary,
        )

        # Cleanup old versions if needed
        self._cleanup_old_versions(content)

        return version

    def get_versions(
        self,
        content,
        limit: int = 50
    ) -> List[ContentVersion]:
        """Get version history for content."""
        return list(ContentVersion.objects.filter(
            content=content
        ).select_related('created_by')[:limit])

    def get_version(
        self,
        content,
        version_number: int
    ) -> Optional[ContentVersion]:
        """Get a specific version."""
        try:
            return ContentVersion.objects.get(
                content=content,
                version_number=version_number
            )
        except ContentVersion.DoesNotExist:
            return None

    def restore_version(
        self,
        content,
        version_number: int,
        user
    ) -> Optional[ContentVersion]:
        """
        Restore content to a previous version.

        Args:
            content: ContentGen instance
            version_number: Version to restore
            user: User performing restoration

        Returns:
            New version created after restoration
        """
        # Get the version to restore
        old_version = self.get_version(content, version_number)
        if not old_version:
            return None

        # Update content with old version's data
        content.title = old_version.title
        content.generatedResponse = old_version.content_body
        if hasattr(content, 'userPrompt'):
            content.userPrompt = old_version.user_prompt
        content.save()

        # Create new version marking restoration
        new_version = self.create_version(
            content=content,
            user=user,
            change_type='restored',
            change_summary=f'Restored from version {version_number}'
        )

        return new_version

    def get_diff_between_versions(
        self,
        content,
        from_version: int,
        to_version: int
    ) -> Optional[Dict]:
        """Get diff between two versions."""
        v1 = self.get_version(content, from_version)
        v2 = self.get_version(content, to_version)

        if not v1 or not v2:
            return None

        return v2.get_diff(v1)

    def should_auto_save(self, content) -> bool:
        """Check if enough time has passed for auto-save."""
        last_version = ContentVersion.objects.filter(
            content=content,
            change_type='auto_saved'
        ).order_by('-created_at').first()

        if not last_version:
            return True

        elapsed = (timezone.now() - last_version.created_at).total_seconds()
        return elapsed >= self.AUTO_SAVE_INTERVAL_SECONDS

    def _cleanup_old_versions(self, content):
        """Remove old versions beyond the limit."""
        versions = ContentVersion.objects.filter(
            content=content
        ).order_by('-version_number')

        if versions.count() > self.MAX_VERSIONS_PER_CONTENT:
            # Keep only the newest versions
            ids_to_keep = versions[:self.MAX_VERSIONS_PER_CONTENT].values_list('id', flat=True)
            ContentVersion.objects.filter(
                content=content
            ).exclude(
                id__in=list(ids_to_keep)
            ).delete()

    def get_version_stats(self, content) -> Dict:
        """Get version statistics for content."""
        versions = ContentVersion.objects.filter(content=content)

        return {
            'total_versions': versions.count(),
            'total_size_bytes': sum(v.size_bytes for v in versions),
            'first_version': versions.order_by('version_number').first(),
            'latest_version': versions.order_by('-version_number').first(),
            'change_types': dict(
                versions.values_list('change_type').annotate(
                    count=models.Count('id')
                )
            ),
        }


# =============================================================================
# Soft Delete Mixin
# =============================================================================

class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted items by default."""

    def get_queryset(self):
        return super().get_queryset().filter(is_delete=False)

    def with_deleted(self):
        """Include soft-deleted items."""
        return super().get_queryset()

    def deleted_only(self):
        """Return only soft-deleted items."""
        return super().get_queryset().filter(is_delete=True)


class SoftDeleteMixin(models.Model):
    """
    Mixin for soft delete functionality with recovery.

    Usage:
        class MyModel(SoftDeleteMixin):
            name = models.CharField(max_length=100)

            objects = SoftDeleteManager()
            all_objects = models.Manager()
    """

    is_delete = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """Soft delete the instance."""
        self.is_delete = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_delete', 'deleted_at', 'deleted_by'])

    def restore(self):
        """Restore a soft-deleted instance."""
        self.is_delete = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_delete', 'deleted_at', 'deleted_by'])

    def hard_delete(self):
        """Permanently delete the instance."""
        super().delete()


# =============================================================================
# Trash/Recycle Bin Service
# =============================================================================

class TrashService:
    """
    Service for managing soft-deleted content (trash/recycle bin).

    Usage:
        service = TrashService()
        service.move_to_trash(content, user)
        service.restore_from_trash(content)
        service.empty_trash(user, older_than_days=30)
    """

    # Auto-delete items after this many days
    AUTO_DELETE_AFTER_DAYS = 30

    def move_to_trash(self, content, user) -> bool:
        """Move content to trash."""
        try:
            content.soft_delete(user=user)
            return True
        except Exception:
            return False

    def restore_from_trash(self, content) -> bool:
        """Restore content from trash."""
        try:
            content.restore()
            return True
        except Exception:
            return False

    def get_trash_items(self, user, model_class, limit: int = 100) -> List:
        """Get items in trash for a user."""
        return list(model_class.objects.with_deleted().filter(
            user=user,
            is_delete=True
        ).order_by('-deleted_at')[:limit])

    def empty_trash(
        self,
        user,
        model_class,
        older_than_days: int = None
    ) -> int:
        """
        Permanently delete items from trash.

        Args:
            user: User whose trash to empty
            model_class: Model class with soft delete
            older_than_days: Only delete items older than this

        Returns:
            Number of items deleted
        """
        queryset = model_class.objects.with_deleted().filter(
            user=user,
            is_delete=True
        )

        if older_than_days:
            cutoff = timezone.now() - timezone.timedelta(days=older_than_days)
            queryset = queryset.filter(deleted_at__lt=cutoff)

        count = queryset.count()
        queryset.delete()

        return count

    def auto_empty_trash(self, model_class) -> int:
        """Auto-delete old trash items system-wide."""
        cutoff = timezone.now() - timezone.timedelta(days=self.AUTO_DELETE_AFTER_DAYS)

        queryset = model_class.objects.with_deleted().filter(
            is_delete=True,
            deleted_at__lt=cutoff
        )

        count = queryset.count()
        queryset.delete()

        return count

    def get_trash_stats(self, user, model_class) -> Dict:
        """Get trash statistics for a user."""
        items = model_class.objects.with_deleted().filter(
            user=user,
            is_delete=True
        )

        return {
            'total_items': items.count(),
            'oldest_item': items.order_by('deleted_at').first(),
            'newest_item': items.order_by('-deleted_at').first(),
        }


# =============================================================================
# Singleton Instances
# =============================================================================

content_version_service = ContentVersionService()
trash_service = TrashService()
