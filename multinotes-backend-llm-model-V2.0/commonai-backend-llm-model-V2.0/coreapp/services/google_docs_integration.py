"""
Google Docs Integration Service for MultinotesAI.

This module provides:
- Export conversations and documents to Google Docs
- Import content from Google Docs
- Two-way sync capabilities
- OAuth authentication flow

WBS Item: 6.2.5 - Google Docs integration
"""

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Google Docs Configuration
# =============================================================================

class ExportFormat(Enum):
    """Export format options."""
    PLAIN_TEXT = 'text/plain'
    HTML = 'text/html'
    PDF = 'application/pdf'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


@dataclass
class GoogleDocMetadata:
    """Metadata for a Google Doc."""
    doc_id: str
    title: str
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    owner_email: Optional[str] = None
    web_view_link: Optional[str] = None
    revision_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'modified_time': self.modified_time.isoformat() if self.modified_time else None,
            'owner_email': self.owner_email,
            'web_view_link': self.web_view_link,
            'revision_id': self.revision_id,
        }


# =============================================================================
# Google API Client
# =============================================================================

class GoogleDocsClient:
    """
    Client for Google Docs API.

    Handles authentication and API calls.
    """

    def __init__(self, credentials: Dict[str, Any] = None):
        self.credentials = credentials
        self._docs_service = None
        self._drive_service = None

    def _get_credentials(self, access_token: str):
        """Get credentials from access token."""
        from google.oauth2.credentials import Credentials

        return Credentials(
            token=access_token,
            refresh_token=self.credentials.get('refresh_token') if self.credentials else None,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=getattr(settings, 'GOOGLE_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
        )

    def _get_docs_service(self, access_token: str):
        """Get Google Docs service."""
        from googleapiclient.discovery import build

        credentials = self._get_credentials(access_token)
        return build('docs', 'v1', credentials=credentials)

    def _get_drive_service(self, access_token: str):
        """Get Google Drive service."""
        from googleapiclient.discovery import build

        credentials = self._get_credentials(access_token)
        return build('drive', 'v3', credentials=credentials)

    # -------------------------------------------------------------------------
    # Document Operations
    # -------------------------------------------------------------------------

    def create_document(
        self,
        access_token: str,
        title: str,
        content: str = '',
        folder_id: Optional[str] = None,
    ) -> GoogleDocMetadata:
        """Create a new Google Doc."""
        docs_service = self._get_docs_service(access_token)
        drive_service = self._get_drive_service(access_token)

        # Create empty document
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')

        # Add content if provided
        if content:
            self.update_content(access_token, doc_id, content)

        # Move to folder if specified
        if folder_id:
            drive_service.files().update(
                fileId=doc_id,
                addParents=folder_id,
                fields='id, parents'
            ).execute()

        # Get metadata
        file_metadata = drive_service.files().get(
            fileId=doc_id,
            fields='id, name, createdTime, modifiedTime, owners, webViewLink'
        ).execute()

        return GoogleDocMetadata(
            doc_id=doc_id,
            title=file_metadata.get('name', title),
            created_time=datetime.fromisoformat(file_metadata.get('createdTime', '').replace('Z', '+00:00')) if file_metadata.get('createdTime') else None,
            modified_time=datetime.fromisoformat(file_metadata.get('modifiedTime', '').replace('Z', '+00:00')) if file_metadata.get('modifiedTime') else None,
            owner_email=file_metadata.get('owners', [{}])[0].get('emailAddress'),
            web_view_link=file_metadata.get('webViewLink'),
        )

    def get_document(
        self,
        access_token: str,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get document content and metadata."""
        docs_service = self._get_docs_service(access_token)
        drive_service = self._get_drive_service(access_token)

        try:
            # Get document content
            doc = docs_service.documents().get(documentId=doc_id).execute()

            # Get file metadata
            file_metadata = drive_service.files().get(
                fileId=doc_id,
                fields='id, name, createdTime, modifiedTime, owners, webViewLink'
            ).execute()

            return {
                'metadata': GoogleDocMetadata(
                    doc_id=doc_id,
                    title=doc.get('title', ''),
                    created_time=datetime.fromisoformat(file_metadata.get('createdTime', '').replace('Z', '+00:00')) if file_metadata.get('createdTime') else None,
                    modified_time=datetime.fromisoformat(file_metadata.get('modifiedTime', '').replace('Z', '+00:00')) if file_metadata.get('modifiedTime') else None,
                    owner_email=file_metadata.get('owners', [{}])[0].get('emailAddress'),
                    web_view_link=file_metadata.get('webViewLink'),
                    revision_id=doc.get('revisionId'),
                ),
                'content': doc,
            }

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    def update_content(
        self,
        access_token: str,
        doc_id: str,
        content: str,
        append: bool = False,
    ) -> bool:
        """Update document content."""
        docs_service = self._get_docs_service(access_token)

        try:
            if not append:
                # Get current document to find end index
                doc = docs_service.documents().get(documentId=doc_id).execute()
                body = doc.get('body', {})
                content_elements = body.get('content', [])

                # Find end index
                end_index = 1
                if content_elements:
                    last_element = content_elements[-1]
                    end_index = last_element.get('endIndex', 1) - 1

                # Delete existing content if any
                if end_index > 1:
                    requests = [
                        {
                            'deleteContentRange': {
                                'range': {
                                    'startIndex': 1,
                                    'endIndex': end_index,
                                }
                            }
                        }
                    ]
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()

            # Insert new content
            requests = [
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': content,
                    }
                }
            ]

            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False

    def append_content(
        self,
        access_token: str,
        doc_id: str,
        content: str,
    ) -> bool:
        """Append content to document."""
        docs_service = self._get_docs_service(access_token)

        try:
            # Get current document to find end index
            doc = docs_service.documents().get(documentId=doc_id).execute()
            body = doc.get('body', {})
            content_elements = body.get('content', [])

            # Find end index
            end_index = 1
            if content_elements:
                last_element = content_elements[-1]
                end_index = last_element.get('endIndex', 1) - 1

            # Insert at end
            requests = [
                {
                    'insertText': {
                        'location': {'index': end_index},
                        'text': '\n\n' + content,
                    }
                }
            ]

            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to append to document {doc_id}: {e}")
            return False

    def delete_document(
        self,
        access_token: str,
        doc_id: str,
    ) -> bool:
        """Delete a document (move to trash)."""
        drive_service = self._get_drive_service(access_token)

        try:
            drive_service.files().delete(fileId=doc_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    # -------------------------------------------------------------------------
    # Export Operations
    # -------------------------------------------------------------------------

    def export_document(
        self,
        access_token: str,
        doc_id: str,
        format: ExportFormat = ExportFormat.PLAIN_TEXT,
    ) -> Optional[bytes]:
        """Export document in specified format."""
        drive_service = self._get_drive_service(access_token)

        try:
            response = drive_service.files().export(
                fileId=doc_id,
                mimeType=format.value
            ).execute()

            return response

        except Exception as e:
            logger.error(f"Failed to export document {doc_id}: {e}")
            return None

    def get_plain_text(
        self,
        access_token: str,
        doc_id: str,
    ) -> Optional[str]:
        """Get document as plain text."""
        content = self.export_document(access_token, doc_id, ExportFormat.PLAIN_TEXT)
        if content:
            return content.decode('utf-8')
        return None

    # -------------------------------------------------------------------------
    # List and Search
    # -------------------------------------------------------------------------

    def list_documents(
        self,
        access_token: str,
        folder_id: Optional[str] = None,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Google Docs."""
        drive_service = self._get_drive_service(access_token)

        query = "mimeType='application/vnd.google-apps.document'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        try:
            results = drive_service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields='nextPageToken, files(id, name, createdTime, modifiedTime, owners, webViewLink)'
            ).execute()

            documents = []
            for file in results.get('files', []):
                documents.append(GoogleDocMetadata(
                    doc_id=file.get('id'),
                    title=file.get('name'),
                    created_time=datetime.fromisoformat(file.get('createdTime', '').replace('Z', '+00:00')) if file.get('createdTime') else None,
                    modified_time=datetime.fromisoformat(file.get('modifiedTime', '').replace('Z', '+00:00')) if file.get('modifiedTime') else None,
                    owner_email=file.get('owners', [{}])[0].get('emailAddress') if file.get('owners') else None,
                    web_view_link=file.get('webViewLink'),
                ))

            return {
                'documents': [d.to_dict() for d in documents],
                'next_page_token': results.get('nextPageToken'),
            }

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return {'documents': [], 'next_page_token': None}

    def search_documents(
        self,
        access_token: str,
        query: str,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for documents."""
        drive_service = self._get_drive_service(access_token)

        search_query = f"mimeType='application/vnd.google-apps.document' and fullText contains '{query}'"

        try:
            results = drive_service.files().list(
                q=search_query,
                pageSize=page_size,
                fields='files(id, name, createdTime, modifiedTime, webViewLink)'
            ).execute()

            documents = []
            for file in results.get('files', []):
                documents.append({
                    'doc_id': file.get('id'),
                    'title': file.get('name'),
                    'modified_time': file.get('modifiedTime'),
                    'web_view_link': file.get('webViewLink'),
                })

            return documents

        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []


# =============================================================================
# Google Docs Integration Service
# =============================================================================

class GoogleDocsIntegrationService:
    """
    Service for integrating MultinotesAI with Google Docs.

    Usage:
        service = GoogleDocsIntegrationService()

        # Export conversation to Google Docs
        doc = service.export_conversation(
            user_id=1,
            prompt_id=123,
            access_token="..."
        )

        # Import from Google Docs
        content = service.import_document(
            user_id=1,
            doc_id="...",
            access_token="..."
        )
    """

    def __init__(self):
        self.client = GoogleDocsClient()

    # -------------------------------------------------------------------------
    # OAuth Flow
    # -------------------------------------------------------------------------

    def get_auth_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> str:
        """Get Google OAuth authorization URL."""
        from urllib.parse import urlencode

        params = {
            'client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join([
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive.file',
            ]),
            'access_type': 'offline',
            'prompt': 'consent',
        }

        if state:
            params['state'] = state

        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        import requests

        try:
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
                    'client_secret': getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri,
                },
            )

            if response.status_code == 200:
                return response.json()

            logger.error(f"Token exchange failed: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None

    def refresh_token(
        self,
        refresh_token: str,
    ) -> Optional[Dict[str, Any]]:
        """Refresh access token."""
        import requests

        try:
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
                    'client_secret': getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                },
            )

            if response.status_code == 200:
                return response.json()

            logger.error(f"Token refresh failed: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Export Operations
    # -------------------------------------------------------------------------

    def export_conversation(
        self,
        user_id: int,
        prompt_id: int,
        access_token: str,
        folder_id: Optional[str] = None,
    ) -> Optional[GoogleDocMetadata]:
        """Export a conversation to Google Docs."""
        try:
            from coreapp.models import Prompt, PromptResponse

            prompt = Prompt.objects.get(id=prompt_id, user_id=user_id)
            responses = PromptResponse.objects.filter(prompt=prompt).order_by('created_at')

            # Build document content
            lines = [
                f"# {prompt.prompt[:50]}...\n",
                f"*Exported from MultinotesAI on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
                "---\n\n",
                "## Prompt\n",
                f"{prompt.prompt}\n\n",
            ]

            for i, response in enumerate(responses, 1):
                lines.append(f"## Response {i}\n")
                lines.append(f"*Model: {response.llm.name if response.llm else 'Unknown'}*\n\n")
                lines.append(f"{response.response}\n\n")

            content = '\n'.join(lines)

            # Create Google Doc
            title = f"MultinotesAI - {prompt.prompt[:30]}..."
            doc = self.client.create_document(
                access_token=access_token,
                title=title,
                content=content,
                folder_id=folder_id,
            )

            logger.info(f"Exported conversation {prompt_id} to Google Doc {doc.doc_id}")
            return doc

        except Exception as e:
            logger.exception(f"Failed to export conversation: {e}")
            return None

    def export_document(
        self,
        user_id: int,
        document_id: int,
        access_token: str,
        folder_id: Optional[str] = None,
    ) -> Optional[GoogleDocMetadata]:
        """Export a document to Google Docs."""
        try:
            from coreapp.models import Document

            document = Document.objects.get(id=document_id, user_id=user_id)

            # Get document content
            content = document.content if hasattr(document, 'content') else ''

            if not content and document.file:
                # Try to read file content
                try:
                    with document.file.open('r') as f:
                        content = f.read()
                except Exception:
                    content = f"[File: {document.file.name}]"

            # Create Google Doc
            doc = self.client.create_document(
                access_token=access_token,
                title=document.title or document.name,
                content=content,
                folder_id=folder_id,
            )

            logger.info(f"Exported document {document_id} to Google Doc {doc.doc_id}")
            return doc

        except Exception as e:
            logger.exception(f"Failed to export document: {e}")
            return None

    def export_text(
        self,
        access_token: str,
        title: str,
        content: str,
        folder_id: Optional[str] = None,
    ) -> Optional[GoogleDocMetadata]:
        """Export arbitrary text to Google Docs."""
        try:
            doc = self.client.create_document(
                access_token=access_token,
                title=title,
                content=content,
                folder_id=folder_id,
            )

            return doc

        except Exception as e:
            logger.exception(f"Failed to export text: {e}")
            return None

    # -------------------------------------------------------------------------
    # Import Operations
    # -------------------------------------------------------------------------

    def import_document(
        self,
        user_id: int,
        doc_id: str,
        access_token: str,
        save_as_document: bool = False,
        folder_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Import content from a Google Doc."""
        try:
            # Get document content
            doc_data = self.client.get_document(access_token, doc_id)
            if not doc_data:
                return None

            # Extract plain text
            plain_text = self.client.get_plain_text(access_token, doc_id)

            result = {
                'metadata': doc_data['metadata'].to_dict(),
                'content': plain_text,
            }

            # Optionally save as MultinotesAI document
            if save_as_document:
                from coreapp.models import Document

                document = Document.objects.create(
                    user_id=user_id,
                    title=doc_data['metadata'].title,
                    content=plain_text,
                    folder_id=folder_id,
                    metadata={
                        'source': 'google_docs',
                        'google_doc_id': doc_id,
                        'imported_at': datetime.now().isoformat(),
                    },
                )

                result['document_id'] = document.id

            return result

        except Exception as e:
            logger.exception(f"Failed to import document: {e}")
            return None

    # -------------------------------------------------------------------------
    # Sync Operations
    # -------------------------------------------------------------------------

    def sync_to_google(
        self,
        user_id: int,
        document_id: int,
        doc_id: str,
        access_token: str,
    ) -> bool:
        """Sync local document changes to Google Docs."""
        try:
            from coreapp.models import Document

            document = Document.objects.get(id=document_id, user_id=user_id)

            content = document.content if hasattr(document, 'content') else ''

            return self.client.update_content(
                access_token=access_token,
                doc_id=doc_id,
                content=content,
            )

        except Exception as e:
            logger.exception(f"Failed to sync to Google: {e}")
            return False

    def sync_from_google(
        self,
        user_id: int,
        document_id: int,
        doc_id: str,
        access_token: str,
    ) -> bool:
        """Sync Google Doc changes to local document."""
        try:
            from coreapp.models import Document

            document = Document.objects.get(id=document_id, user_id=user_id)

            # Get Google Doc content
            plain_text = self.client.get_plain_text(access_token, doc_id)
            if plain_text is None:
                return False

            # Update local document
            document.content = plain_text
            document.save()

            return True

        except Exception as e:
            logger.exception(f"Failed to sync from Google: {e}")
            return False

    # -------------------------------------------------------------------------
    # List and Browse
    # -------------------------------------------------------------------------

    def list_user_documents(
        self,
        access_token: str,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List user's Google Docs."""
        return self.client.list_documents(
            access_token=access_token,
            page_size=page_size,
            page_token=page_token,
        )

    def search_user_documents(
        self,
        access_token: str,
        query: str,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search user's Google Docs."""
        return self.client.search_documents(
            access_token=access_token,
            query=query,
            page_size=page_size,
        )


# =============================================================================
# Singleton Instance
# =============================================================================

google_docs_service = GoogleDocsIntegrationService()
