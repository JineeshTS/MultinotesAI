"""
Unit tests for coreapp views and functionality.

This module tests:
- Content/Note CRUD operations
- Folder management
- AI content generation
- File uploads
- Search functionality
- Sharing and export
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, Mock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status


# =============================================================================
# Content/Note Tests
# =============================================================================

@pytest.mark.django_db
class TestContentCRUD:
    """Tests for content/note CRUD operations."""

    def test_list_notes_authenticated(self, authenticated_client, note_factory, user):
        """Test listing notes when authenticated."""
        # Create some notes
        note_factory(user=user, title="Note 1")
        note_factory(user=user, title="Note 2")

        response = authenticated_client.get('/api/content/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results', response.data)) >= 2

    def test_list_notes_unauthenticated(self, api_client):
        """Test listing notes without authentication."""
        response = api_client.get('/api/content/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_notes_only_own(self, authenticated_client, note_factory, user, user_factory):
        """Test that users only see their own notes."""
        other_user = user_factory()
        note_factory(user=user, title="My Note")
        note_factory(user=other_user, title="Other User Note")

        response = authenticated_client.get('/api/content/')

        notes = response.data.get('results', response.data)
        titles = [n.get('title') for n in notes]

        assert "My Note" in titles
        assert "Other User Note" not in titles

    def test_create_note_success(self, authenticated_client, sample_note_data):
        """Test creating a note."""
        response = authenticated_client.post(
            '/api/content/',
            sample_note_data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get('title') == sample_note_data['title']

    def test_create_note_missing_title(self, authenticated_client):
        """Test creating note without title fails."""
        response = authenticated_client.post(
            '/api/content/',
            {'content': 'Content without title'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_note_detail(self, authenticated_client, note_factory, user):
        """Test getting note detail."""
        note = note_factory(user=user, title="Test Note")

        response = authenticated_client.get(f'/api/content/{note.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('title') == "Test Note"

    def test_get_note_not_found(self, authenticated_client):
        """Test getting non-existent note."""
        response = authenticated_client.get('/api/content/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_note_unauthorized(self, authenticated_client, note_factory, user_factory):
        """Test getting another user's note."""
        other_user = user_factory()
        note = note_factory(user=other_user, title="Other's Note")

        response = authenticated_client.get(f'/api/content/{note.id}/')

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN
        ]

    def test_update_note_success(self, authenticated_client, note_factory, user):
        """Test updating a note."""
        note = note_factory(user=user, title="Original Title")

        response = authenticated_client.patch(
            f'/api/content/{note.id}/',
            {'title': 'Updated Title'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('title') == 'Updated Title'

    def test_delete_note_success(self, authenticated_client, note_factory, user):
        """Test deleting a note (soft delete)."""
        note = note_factory(user=user, title="To Delete")

        response = authenticated_client.delete(f'/api/content/{note.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft deleted
        from coreapp.models import ContentGen
        note.refresh_from_db()
        assert note.is_delete is True


# =============================================================================
# Folder Tests
# =============================================================================

@pytest.mark.django_db
class TestFolderCRUD:
    """Tests for folder CRUD operations."""

    def test_list_folders(self, authenticated_client, folder_factory, user):
        """Test listing folders."""
        folder_factory(user=user, name="Folder 1")
        folder_factory(user=user, name="Folder 2")

        response = authenticated_client.get('/api/folders/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results', response.data)) >= 2

    def test_create_folder(self, authenticated_client):
        """Test creating a folder."""
        response = authenticated_client.post(
            '/api/folders/',
            {'name': 'New Folder'},
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get('name') == 'New Folder'

    def test_create_nested_folder(self, authenticated_client, folder_factory, user):
        """Test creating a nested folder."""
        parent = folder_factory(user=user, name="Parent")

        response = authenticated_client.post(
            '/api/folders/',
            {'name': 'Child Folder', 'parent': parent.id},
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get('parent') == parent.id

    def test_update_folder(self, authenticated_client, folder_factory, user):
        """Test updating a folder."""
        folder = folder_factory(user=user, name="Original Name")

        response = authenticated_client.patch(
            f'/api/folders/{folder.id}/',
            {'name': 'Updated Name'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('name') == 'Updated Name'

    def test_delete_folder(self, authenticated_client, folder_factory, user):
        """Test deleting a folder."""
        folder = folder_factory(user=user, name="To Delete")

        response = authenticated_client.delete(f'/api/folders/{folder.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_move_note_to_folder(self, authenticated_client, folder_factory, note_factory, user):
        """Test moving a note to a folder."""
        folder = folder_factory(user=user, name="Target Folder")
        note = note_factory(user=user, title="Note to Move")

        response = authenticated_client.patch(
            f'/api/content/{note.id}/',
            {'folder': folder.id},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('folder') == folder.id


# =============================================================================
# AI Generation Tests
# =============================================================================

@pytest.mark.django_db
class TestAIGeneration:
    """Tests for AI content generation."""

    @patch('coreapp.services.llm_service.llm_service.generate_text')
    def test_generate_content_success(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test successful AI content generation."""
        # Set up subscription with tokens
        subscription_factory(user=user, balance_token=1000)

        mock_generate.return_value = {
            'content': 'Generated AI content here.',
            'tokens_used': 100
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Write about AI'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_generate_content_no_subscription(self, authenticated_client):
        """Test AI generation without active subscription."""
        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Write about AI'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_402_PAYMENT_REQUIRED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_generate_content_insufficient_tokens(
        self, authenticated_client, subscription_factory, user
    ):
        """Test AI generation with insufficient tokens."""
        subscription_factory(user=user, balance_token=0)

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Write about AI'},
            format='json'
        )

        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    def test_generate_content_empty_prompt(self, authenticated_client, subscription_factory, user):
        """Test AI generation with empty prompt."""
        subscription_factory(user=user, balance_token=1000)

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': ''},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_content_unauthenticated(self, api_client):
        """Test AI generation without authentication."""
        response = api_client.post(
            '/api/content/generate/',
            {'prompt': 'Write about AI'},
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Search Tests
# =============================================================================

@pytest.mark.django_db
class TestContentSearch:
    """Tests for content search functionality."""

    def test_search_content_success(self, authenticated_client, note_factory, user):
        """Test searching content."""
        note_factory(user=user, title="Python Tutorial", content="Learn Python programming")
        note_factory(user=user, title="JavaScript Guide", content="Learn JavaScript")

        response = authenticated_client.get('/api/content/search/?q=Python')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert any('Python' in r.get('title', '') for r in results)

    def test_search_content_empty_query(self, authenticated_client):
        """Test search with empty query."""
        response = authenticated_client.get('/api/content/search/?q=')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_search_content_no_results(self, authenticated_client, note_factory, user):
        """Test search with no matching results."""
        note_factory(user=user, title="Python Tutorial")

        response = authenticated_client.get('/api/content/search/?q=nonexistentterm')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert len(results) == 0


# =============================================================================
# Export Tests
# =============================================================================

@pytest.mark.django_db
class TestContentExport:
    """Tests for content export functionality."""

    def test_export_note_pdf(self, authenticated_client, note_factory, user):
        """Test exporting note as PDF."""
        note = note_factory(user=user, title="Export Test", content="Content to export")

        response = authenticated_client.get(
            f'/api/content/{note.id}/export/?format=pdf'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED  # If async
        ]

    def test_export_note_markdown(self, authenticated_client, note_factory, user):
        """Test exporting note as Markdown."""
        note = note_factory(user=user, title="Export Test", content="Content to export")

        response = authenticated_client.get(
            f'/api/content/{note.id}/export/?format=md'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_export_invalid_format(self, authenticated_client, note_factory, user):
        """Test export with invalid format."""
        note = note_factory(user=user, title="Export Test")

        response = authenticated_client.get(
            f'/api/content/{note.id}/export/?format=invalid'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Sharing Tests
# =============================================================================

@pytest.mark.django_db
class TestContentSharing:
    """Tests for content sharing functionality."""

    def test_create_share_link(self, authenticated_client, note_factory, user):
        """Test creating a share link."""
        note = note_factory(user=user, title="Shareable Note")

        response = authenticated_client.post(
            f'/api/content/{note.id}/share/',
            {'expires_in_days': 7},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]
        assert 'share_url' in response.data or 'link' in response.data

    def test_access_shared_content(self, api_client, note_factory, user_factory):
        """Test accessing shared content via share link."""
        # This depends on how sharing is implemented
        pass

    def test_revoke_share_link(self, authenticated_client, note_factory, user):
        """Test revoking a share link."""
        note = note_factory(user=user, title="Shareable Note")

        # First create share
        authenticated_client.post(
            f'/api/content/{note.id}/share/',
            {},
            format='json'
        )

        # Then revoke
        response = authenticated_client.delete(f'/api/content/{note.id}/share/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]


# =============================================================================
# File Upload Tests
# =============================================================================

@pytest.mark.django_db
class TestFileUpload:
    """Tests for file upload functionality."""

    def test_upload_file_success(self, authenticated_client, temp_file, subscription_factory, user):
        """Test successful file upload."""
        subscription_factory(user=user, file_token=10)
        file = temp_file(content="Test file content", filename="test.txt")

        with open(file, 'rb') as f:
            response = authenticated_client.post(
                '/api/files/upload/',
                {'file': f},
                format='multipart'
            )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_upload_file_too_large(self, authenticated_client, tmp_path, subscription_factory, user):
        """Test upload with file too large."""
        subscription_factory(user=user, file_token=10)

        # Create large file (simulated)
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * (50 * 1024 * 1024 + 1))  # > 50MB

        with open(large_file, 'rb') as f:
            response = authenticated_client.post(
                '/api/files/upload/',
                {'file': f},
                format='multipart'
            )

        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_upload_invalid_file_type(self, authenticated_client, tmp_path, subscription_factory, user):
        """Test upload with invalid file type."""
        subscription_factory(user=user, file_token=10)

        exe_file = tmp_path / "test.exe"
        exe_file.write_bytes(b'\x00\x00')

        with open(exe_file, 'rb') as f:
            response = authenticated_client.post(
                '/api/files/upload/',
                {'file': f},
                format='multipart'
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Favorites Tests
# =============================================================================

@pytest.mark.django_db
class TestFavorites:
    """Tests for favorites functionality."""

    def test_add_to_favorites(self, authenticated_client, note_factory, user):
        """Test adding note to favorites."""
        note = note_factory(user=user, title="Favorite Note")

        response = authenticated_client.post(f'/api/content/{note.id}/favorite/')

        assert response.status_code == status.HTTP_200_OK

    def test_remove_from_favorites(self, authenticated_client, note_factory, user):
        """Test removing note from favorites."""
        note = note_factory(user=user, title="Favorite Note")

        # Add to favorites first
        authenticated_client.post(f'/api/content/{note.id}/favorite/')

        # Remove from favorites
        response = authenticated_client.delete(f'/api/content/{note.id}/favorite/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]

    def test_list_favorites(self, authenticated_client, note_factory, user):
        """Test listing favorite notes."""
        note = note_factory(user=user, title="Favorite Note")
        authenticated_client.post(f'/api/content/{note.id}/favorite/')

        response = authenticated_client.get('/api/content/favorites/')

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# LLM Model Selection Tests
# =============================================================================

@pytest.mark.django_db
class TestLLMModelSelection:
    """Tests for LLM model selection."""

    def test_list_available_models(self, authenticated_client, llm_model_factory):
        """Test listing available LLM models."""
        llm_model_factory(name="GPT-4", is_active=True)
        llm_model_factory(name="Claude", is_active=True)

        response = authenticated_client.get('/api/models/')

        assert response.status_code == status.HTTP_200_OK
        models = response.data.get('results', response.data)
        assert len(models) >= 2

    def test_generate_with_specific_model(
        self, authenticated_client, subscription_factory, llm_model_factory, user
    ):
        """Test generating content with specific model."""
        subscription_factory(user=user, balance_token=1000)
        model = llm_model_factory(name="GPT-4", model_id="gpt-4")

        with patch('coreapp.services.llm_service.llm_service.generate_text') as mock:
            mock.return_value = {'content': 'Generated', 'tokens_used': 50}

            response = authenticated_client.post(
                '/api/content/generate/',
                {'prompt': 'Write about AI', 'model_id': model.id},
                format='json'
            )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


# =============================================================================
# Pagination Tests
# =============================================================================

@pytest.mark.django_db
class TestPagination:
    """Tests for pagination."""

    def test_content_pagination(self, authenticated_client, note_factory, user):
        """Test content list pagination."""
        # Create 25 notes
        for i in range(25):
            note_factory(user=user, title=f"Note {i}")

        response = authenticated_client.get('/api/content/?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results', [])) == 10
        assert 'count' in response.data or 'total' in response.data

    def test_content_pagination_page_2(self, authenticated_client, note_factory, user):
        """Test getting second page of content."""
        for i in range(25):
            note_factory(user=user, title=f"Note {i}")

        response = authenticated_client.get('/api/content/?page=2&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results', [])) == 10
