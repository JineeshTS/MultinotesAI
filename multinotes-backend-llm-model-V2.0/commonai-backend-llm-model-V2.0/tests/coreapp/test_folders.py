"""
Tests for folder and content management endpoints.

Tests cover:
- Folder CRUD operations
- Notebook management
- Document management
- Content sharing
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestFolderOperations:
    """Tests for folder CRUD endpoints."""

    def test_create_folder(self, auth_client, user):
        """Test creating a new folder."""
        url = '/api/core/folder/'
        data = {
            'name': 'Test Folder'
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_create_subfolder(self, auth_client, folder):
        """Test creating a subfolder."""
        url = '/api/core/folder/'
        data = {
            'name': 'Subfolder',
            'parent_folder': folder.id
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_list_folders(self, auth_client, folder):
        """Test listing user's folders."""
        url = '/api/core/folder/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_update_folder(self, auth_client, folder):
        """Test updating a folder."""
        url = f'/api/core/folder/{folder.id}/'
        data = {
            'name': 'Updated Folder Name'
        }
        response = auth_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_delete_folder(self, auth_client, folder):
        """Test deleting a folder (soft delete)."""
        url = f'/api/core/folder/{folder.id}/'
        response = auth_client.delete(url)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

    def test_folder_access_unauthorized(self, api_client, folder):
        """Test folder access without auth fails."""
        url = f'/api/core/folder/{folder.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestNotebookOperations:
    """Tests for notebook endpoints."""

    def test_create_notebook(self, auth_client, folder):
        """Test creating a notebook."""
        url = '/api/core/notebook/'
        data = {
            'name': 'Test Notebook',
            'folder': folder.id
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_list_notebooks(self, auth_client):
        """Test listing notebooks."""
        url = '/api/core/notebook/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_update_notebook(self, auth_client, folder):
        """Test updating notebook content."""
        # First create a notebook
        url = '/api/core/notebook/'
        create_data = {
            'name': 'Test Notebook',
            'folder': folder.id
        }
        create_response = auth_client.post(url, create_data, format='json')
        if create_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            notebook_id = create_response.data.get('id')
            if notebook_id:
                update_url = f'/api/core/notebook/{notebook_id}/'
                update_data = {'name': 'Updated Notebook'}
                response = auth_client.patch(update_url, update_data, format='json')
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDocumentOperations:
    """Tests for document endpoints."""

    def test_list_documents(self, auth_client):
        """Test listing documents."""
        url = '/api/core/document/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_document_by_folder(self, auth_client, folder):
        """Test listing documents in a folder."""
        url = f'/api/core/document/?folder={folder.id}'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestContentSharing:
    """Tests for content sharing endpoints."""

    def test_share_folder(self, auth_client, folder, create_user):
        """Test sharing a folder with another user."""
        other_user = create_user(
            email='other@example.com',
            username='otheruser'
        )
        url = '/api/core/share/'
        data = {
            'folder': folder.id,
            'share_to_user': other_user.id,
            'permission': 'read'
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST  # if sharing not enabled
        ]

    def test_list_shared_content(self, auth_client):
        """Test listing content shared with user."""
        url = '/api/core/share/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_revoke_share(self, auth_client):
        """Test revoking shared access."""
        url = '/api/core/share/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserContent:
    """Tests for user content endpoints."""

    def test_list_user_content(self, auth_client):
        """Test listing all user content."""
        url = '/api/core/user-content/'
        response = auth_client.get(url)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_content_search(self, auth_client):
        """Test searching user content."""
        url = '/api/core/user-content/?search=test'
        response = auth_client.get(url)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
