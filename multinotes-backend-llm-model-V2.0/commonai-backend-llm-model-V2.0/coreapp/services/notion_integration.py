"""
Notion Integration Service for MultinotesAI.

This module provides:
- Export content to Notion pages
- Sync documents with Notion
- Create Notion databases from conversations
- OAuth integration with Notion

WBS Item: 4.4.10 - Add Notion integration for exports
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

NOTION_API_VERSION = '2022-06-28'
NOTION_API_BASE = 'https://api.notion.com/v1'


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NotionBlock:
    """Represents a Notion block."""
    type: str
    content: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'object': 'block',
            'type': self.type,
            self.type: self.content,
        }


@dataclass
class NotionPage:
    """Represents a Notion page."""
    id: str
    title: str
    url: str
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'last_edited_time': self.last_edited_time.isoformat() if self.last_edited_time else None,
        }


# =============================================================================
# Notion Client
# =============================================================================

class NotionClient:
    """
    Client for Notion API.

    Usage:
        client = NotionClient(access_token='secret_xxx')
        pages = client.search_pages('My Document')
    """

    def __init__(self, access_token: str):
        """
        Initialize Notion client.

        Args:
            access_token: Notion integration token or OAuth token
        """
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Notion-Version': NOTION_API_VERSION,
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request to Notion."""
        url = f'{NOTION_API_BASE}{endpoint}'

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )

            if response.status_code == 401:
                raise NotionAuthError('Invalid or expired access token')

            if response.status_code == 403:
                raise NotionPermissionError('Insufficient permissions')

            if response.status_code == 404:
                raise NotionNotFoundError('Resource not found')

            if response.status_code >= 400:
                error_data = response.json()
                raise NotionAPIError(
                    f"API error: {error_data.get('message', 'Unknown error')}"
                )

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Notion API request failed: {e}")
            raise NotionAPIError(f"Request failed: {e}")

    def get_user(self) -> Dict[str, Any]:
        """Get current user info."""
        return self._request('GET', '/users/me')

    def search_pages(
        self,
        query: str = '',
        filter_type: str = 'page'
    ) -> List[Dict[str, Any]]:
        """
        Search for pages in Notion.

        Args:
            query: Search query
            filter_type: 'page' or 'database'

        Returns:
            List of matching pages/databases
        """
        data = {
            'filter': {'property': 'object', 'value': filter_type},
        }
        if query:
            data['query'] = query

        response = self._request('POST', '/search', data)
        return response.get('results', [])

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a specific page."""
        return self._request('GET', f'/pages/{page_id}')

    def create_page(
        self,
        parent_id: str,
        title: str,
        blocks: List[Dict[str, Any]],
        is_database: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new page in Notion.

        Args:
            parent_id: Parent page or database ID
            title: Page title
            blocks: List of block contents
            is_database: Whether parent is a database

        Returns:
            Created page data
        """
        if is_database:
            parent = {'database_id': parent_id}
            properties = {
                'Name': {
                    'title': [{'text': {'content': title}}]
                }
            }
        else:
            parent = {'page_id': parent_id}
            properties = {
                'title': {
                    'title': [{'text': {'content': title}}]
                }
            }

        data = {
            'parent': parent,
            'properties': properties,
        }

        if blocks:
            data['children'] = blocks

        return self._request('POST', '/pages', data)

    def append_blocks(
        self,
        page_id: str,
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Append blocks to a page.

        Args:
            page_id: Page ID
            blocks: Blocks to append

        Returns:
            API response
        """
        data = {'children': blocks}
        return self._request('PATCH', f'/blocks/{page_id}/children', data)

    def get_databases(self) -> List[Dict[str, Any]]:
        """Get all accessible databases."""
        return self.search_pages(filter_type='database')

    def create_database(
        self,
        parent_id: str,
        title: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new database.

        Args:
            parent_id: Parent page ID
            title: Database title
            properties: Database properties schema

        Returns:
            Created database data
        """
        data = {
            'parent': {'page_id': parent_id},
            'title': [{'type': 'text', 'text': {'content': title}}],
            'properties': properties,
        }

        return self._request('POST', '/databases', data)


# =============================================================================
# Content Converter
# =============================================================================

class NotionContentConverter:
    """
    Convert content to Notion blocks.

    Supports:
    - Markdown to Notion blocks
    - Plain text to paragraphs
    - Code blocks
    - Lists
    - Headings
    """

    MAX_TEXT_LENGTH = 2000  # Notion's limit

    def convert_markdown(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Convert Markdown to Notion blocks.

        Args:
            markdown: Markdown text

        Returns:
            List of Notion blocks
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Code blocks
            if line.startswith('```'):
                code_lines = []
                language = line[3:].strip() or 'plain text'
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append(self._create_code_block('\n'.join(code_lines), language))
                i += 1
                continue

            # Headings
            if line.startswith('# '):
                blocks.append(self._create_heading(line[2:], 1))
            elif line.startswith('## '):
                blocks.append(self._create_heading(line[3:], 2))
            elif line.startswith('### '):
                blocks.append(self._create_heading(line[4:], 3))

            # Bullet list
            elif line.startswith('- ') or line.startswith('* '):
                blocks.append(self._create_bullet_item(line[2:]))

            # Numbered list
            elif re.match(r'^\d+\.\s', line):
                text = re.sub(r'^\d+\.\s', '', line)
                blocks.append(self._create_numbered_item(text))

            # Blockquote
            elif line.startswith('> '):
                blocks.append(self._create_quote(line[2:]))

            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                blocks.append(self._create_divider())

            # Regular paragraph
            elif line.strip():
                blocks.append(self._create_paragraph(line))

            i += 1

        return blocks

    def convert_conversation(
        self,
        messages: List[Dict[str, str]],
        title: str = 'Conversation'
    ) -> List[Dict[str, Any]]:
        """
        Convert conversation to Notion blocks.

        Args:
            messages: List of message dicts with 'role' and 'content'
            title: Conversation title

        Returns:
            List of Notion blocks
        """
        blocks = []

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            # Add role header
            role_text = '👤 User' if role == 'user' else '🤖 Assistant'
            blocks.append(self._create_heading(role_text, 3))

            # Add content
            if '```' in content:
                # Has code blocks, parse as markdown
                blocks.extend(self.convert_markdown(content))
            else:
                # Split into paragraphs
                for para in content.split('\n\n'):
                    if para.strip():
                        blocks.append(self._create_paragraph(para))

            # Add divider between messages
            blocks.append(self._create_divider())

        return blocks

    def convert_plain_text(self, text: str) -> List[Dict[str, Any]]:
        """Convert plain text to paragraphs."""
        blocks = []

        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                blocks.append(self._create_paragraph(para))

        return blocks

    # -------------------------------------------------------------------------
    # Block Creators
    # -------------------------------------------------------------------------

    def _create_paragraph(self, text: str) -> Dict[str, Any]:
        """Create paragraph block."""
        return {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': self._create_rich_text(text)
            }
        }

    def _create_heading(self, text: str, level: int) -> Dict[str, Any]:
        """Create heading block."""
        heading_type = f'heading_{level}'
        return {
            'object': 'block',
            'type': heading_type,
            heading_type: {
                'rich_text': self._create_rich_text(text)
            }
        }

    def _create_bullet_item(self, text: str) -> Dict[str, Any]:
        """Create bullet list item."""
        return {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': self._create_rich_text(text)
            }
        }

    def _create_numbered_item(self, text: str) -> Dict[str, Any]:
        """Create numbered list item."""
        return {
            'object': 'block',
            'type': 'numbered_list_item',
            'numbered_list_item': {
                'rich_text': self._create_rich_text(text)
            }
        }

    def _create_code_block(self, code: str, language: str) -> Dict[str, Any]:
        """Create code block."""
        return {
            'object': 'block',
            'type': 'code',
            'code': {
                'rich_text': self._create_rich_text(code),
                'language': self._normalize_language(language)
            }
        }

    def _create_quote(self, text: str) -> Dict[str, Any]:
        """Create quote block."""
        return {
            'object': 'block',
            'type': 'quote',
            'quote': {
                'rich_text': self._create_rich_text(text)
            }
        }

    def _create_divider(self) -> Dict[str, Any]:
        """Create divider block."""
        return {
            'object': 'block',
            'type': 'divider',
            'divider': {}
        }

    def _create_rich_text(self, text: str) -> List[Dict[str, Any]]:
        """Create rich text array, handling length limits."""
        rich_text = []

        # Split if too long
        while text:
            chunk = text[:self.MAX_TEXT_LENGTH]
            text = text[self.MAX_TEXT_LENGTH:]

            rich_text.append({
                'type': 'text',
                'text': {'content': chunk}
            })

        return rich_text

    def _normalize_language(self, language: str) -> str:
        """Normalize programming language name for Notion."""
        language_map = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'rb': 'ruby',
            'yml': 'yaml',
            'sh': 'bash',
            'shell': 'bash',
        }
        return language_map.get(language.lower(), language.lower())


# =============================================================================
# Notion Integration Service
# =============================================================================

class NotionIntegrationService:
    """
    Service for integrating with Notion.

    Usage:
        service = NotionIntegrationService()
        page = service.export_document(user_id=123, document_id=456, parent_id='xxx')
    """

    def __init__(self):
        self.converter = NotionContentConverter()

    def get_client(self, user_id: int) -> NotionClient:
        """
        Get Notion client for user.

        Args:
            user_id: User ID

        Returns:
            NotionClient instance

        Raises:
            NotionNotConnectedError if user hasn't connected Notion
        """
        access_token = self._get_access_token(user_id)
        if not access_token:
            raise NotionNotConnectedError('Notion account not connected')

        return NotionClient(access_token)

    def is_connected(self, user_id: int) -> bool:
        """Check if user has connected Notion."""
        return self._get_access_token(user_id) is not None

    def export_document(
        self,
        user_id: int,
        document_id: int,
        parent_id: str,
        as_child_page: bool = True
    ) -> NotionPage:
        """
        Export a document to Notion.

        Args:
            user_id: User ID
            document_id: Document ID
            parent_id: Notion parent page/database ID
            as_child_page: Create as child page vs database entry

        Returns:
            Created NotionPage
        """
        from coreapp.models import Document

        document = Document.objects.get(id=document_id, user_id=user_id)
        client = self.get_client(user_id)

        # Convert content to blocks
        if document.content:
            blocks = self.converter.convert_markdown(document.content)
        else:
            blocks = []

        # Create page
        result = client.create_page(
            parent_id=parent_id,
            title=document.title or 'Untitled Document',
            blocks=blocks,
            is_database=not as_child_page
        )

        return NotionPage(
            id=result['id'],
            title=document.title or 'Untitled Document',
            url=result.get('url', ''),
            created_time=datetime.now(),
        )

    def export_conversation(
        self,
        user_id: int,
        prompt_id: int,
        parent_id: str
    ) -> NotionPage:
        """
        Export a conversation to Notion.

        Args:
            user_id: User ID
            prompt_id: Prompt ID
            parent_id: Notion parent page ID

        Returns:
            Created NotionPage
        """
        from coreapp.models import Prompt, PromptResponse

        prompt = Prompt.objects.get(id=prompt_id, user_id=user_id)
        responses = PromptResponse.objects.filter(
            prompt=prompt,
            is_delete=False
        ).order_by('created_at')

        # Build messages
        messages = [{'role': 'user', 'content': prompt.prompt_text}]
        for response in responses:
            messages.append({
                'role': 'assistant',
                'content': response.response_text
            })

        client = self.get_client(user_id)

        # Convert to blocks
        blocks = self.converter.convert_conversation(messages)

        # Create page
        title = prompt.title or prompt.prompt_text[:50] + '...'
        result = client.create_page(
            parent_id=parent_id,
            title=title,
            blocks=blocks
        )

        return NotionPage(
            id=result['id'],
            title=title,
            url=result.get('url', ''),
            created_time=datetime.now(),
        )

    def get_available_pages(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get pages user can export to.

        Args:
            user_id: User ID

        Returns:
            List of available pages
        """
        client = self.get_client(user_id)
        pages = client.search_pages(filter_type='page')

        return [
            {
                'id': page['id'],
                'title': self._extract_title(page),
                'url': page.get('url', ''),
            }
            for page in pages
        ]

    def get_available_databases(self, user_id: int) -> List[Dict[str, Any]]:
        """Get databases user can export to."""
        client = self.get_client(user_id)
        databases = client.get_databases()

        return [
            {
                'id': db['id'],
                'title': self._extract_title(db),
                'url': db.get('url', ''),
            }
            for db in databases
        ]

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _get_access_token(self, user_id: int) -> Optional[str]:
        """Get Notion access token for user."""
        # Try cache first
        cache_key = f'notion_token:{user_id}'
        token = cache.get(cache_key)
        if token:
            return token

        # Try database
        try:
            from coreapp.models import UserIntegration

            integration = UserIntegration.objects.filter(
                user_id=user_id,
                provider='notion',
                is_active=True
            ).first()

            if integration and integration.access_token:
                # Cache for 1 hour
                cache.set(cache_key, integration.access_token, 3600)
                return integration.access_token

        except Exception as e:
            logger.debug(f"Could not get Notion token: {e}")

        return None

    def _extract_title(self, page: Dict) -> str:
        """Extract title from Notion page object."""
        properties = page.get('properties', {})

        # Try 'title' property
        if 'title' in properties:
            title_data = properties['title'].get('title', [])
            if title_data:
                return title_data[0].get('text', {}).get('content', 'Untitled')

        # Try 'Name' property (for database items)
        if 'Name' in properties:
            name_data = properties['Name'].get('title', [])
            if name_data:
                return name_data[0].get('text', {}).get('content', 'Untitled')

        return 'Untitled'


# =============================================================================
# OAuth Handler
# =============================================================================

class NotionOAuthHandler:
    """Handle Notion OAuth flow."""

    def __init__(self):
        self.client_id = getattr(settings, 'NOTION_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'NOTION_CLIENT_SECRET', '')
        self.redirect_uri = getattr(settings, 'NOTION_REDIRECT_URI', '')

    def get_authorization_url(self, state: str) -> str:
        """
        Get OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'owner': 'user',
            'state': state,
        }

        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        return f'https://api.notion.com/v1/oauth/authorize?{query_string}'

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code

        Returns:
            Token data including access_token
        """
        import base64

        credentials = base64.b64encode(
            f'{self.client_id}:{self.client_secret}'.encode()
        ).decode()

        response = requests.post(
            'https://api.notion.com/v1/oauth/token',
            headers={
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json',
            },
            json={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri,
            },
            timeout=30
        )

        if response.status_code != 200:
            raise NotionAuthError('Failed to exchange authorization code')

        return response.json()

    def save_token(self, user_id: int, token_data: Dict[str, Any]) -> None:
        """
        Save Notion token for user.

        Args:
            user_id: User ID
            token_data: Token data from OAuth
        """
        try:
            from coreapp.models import UserIntegration

            UserIntegration.objects.update_or_create(
                user_id=user_id,
                provider='notion',
                defaults={
                    'access_token': token_data.get('access_token'),
                    'workspace_id': token_data.get('workspace_id'),
                    'workspace_name': token_data.get('workspace_name'),
                    'is_active': True,
                }
            )

            # Cache token
            cache.set(f'notion_token:{user_id}', token_data.get('access_token'), 3600)

        except Exception as e:
            logger.error(f"Failed to save Notion token: {e}")
            raise


# =============================================================================
# Exceptions
# =============================================================================

class NotionError(Exception):
    """Base exception for Notion errors."""
    pass


class NotionAPIError(NotionError):
    """API error from Notion."""
    pass


class NotionAuthError(NotionError):
    """Authentication error."""
    pass


class NotionPermissionError(NotionError):
    """Permission denied error."""
    pass


class NotionNotFoundError(NotionError):
    """Resource not found error."""
    pass


class NotionNotConnectedError(NotionError):
    """User hasn't connected Notion."""
    pass


# =============================================================================
# Singleton Instances
# =============================================================================

notion_service = NotionIntegrationService()
notion_oauth = NotionOAuthHandler()
