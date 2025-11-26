"""
Slack Integration Service for MultinotesAI.

This module provides:
- Send AI responses to Slack channels
- Receive prompts from Slack
- Slack bot interactions
- Webhook notifications

WBS Item: 6.2.6 - Slack integration
"""

import logging
import json
import hmac
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Slack Configuration
# =============================================================================

class MessageType(Enum):
    """Types of Slack messages."""
    TEXT = 'text'
    BLOCKS = 'blocks'
    ATTACHMENT = 'attachment'


@dataclass
class SlackMessage:
    """A Slack message."""
    channel: str
    text: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    thread_ts: Optional[str] = None
    reply_broadcast: bool = False
    unfurl_links: bool = True
    unfurl_media: bool = True

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'channel': self.channel,
            'text': self.text,
        }
        if self.blocks:
            result['blocks'] = self.blocks
        if self.attachments:
            result['attachments'] = self.attachments
        if self.thread_ts:
            result['thread_ts'] = self.thread_ts
        result['reply_broadcast'] = self.reply_broadcast
        result['unfurl_links'] = self.unfurl_links
        result['unfurl_media'] = self.unfurl_media
        return result


@dataclass
class SlackUser:
    """Slack user information."""
    user_id: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_bot: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'email': self.email,
            'is_bot': self.is_bot,
        }


# =============================================================================
# Slack API Client
# =============================================================================

class SlackClient:
    """
    Client for Slack API.
    """

    BASE_URL = 'https://slack.com/api'

    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or getattr(settings, 'SLACK_BOT_TOKEN', '')

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Make a request to Slack API."""
        import requests

        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.bot_token}',
        }

        if json_data:
            headers['Content-Type'] = 'application/json'
            response = requests.request(method, url, headers=headers, json=json_data)
        else:
            response = requests.request(method, url, headers=headers, data=data)

        return response.json()

    # -------------------------------------------------------------------------
    # Messaging
    # -------------------------------------------------------------------------

    def send_message(self, message: SlackMessage) -> Dict[str, Any]:
        """Send a message to a channel."""
        return self._request('POST', 'chat.postMessage', json_data=message.to_dict())

    def send_text(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a simple text message."""
        message = SlackMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
        )
        return self.send_message(message)

    def send_blocks(
        self,
        channel: str,
        blocks: List[Dict[str, Any]],
        text: str = '',
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message with blocks."""
        message = SlackMessage(
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts,
        )
        return self.send_message(message)

    def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update an existing message."""
        data = {
            'channel': channel,
            'ts': ts,
            'text': text,
        }
        if blocks:
            data['blocks'] = blocks

        return self._request('POST', 'chat.update', json_data=data)

    def delete_message(
        self,
        channel: str,
        ts: str,
    ) -> Dict[str, Any]:
        """Delete a message."""
        return self._request('POST', 'chat.delete', json_data={
            'channel': channel,
            'ts': ts,
        })

    def add_reaction(
        self,
        channel: str,
        ts: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """Add a reaction to a message."""
        return self._request('POST', 'reactions.add', json_data={
            'channel': channel,
            'timestamp': ts,
            'name': emoji,
        })

    # -------------------------------------------------------------------------
    # Channels
    # -------------------------------------------------------------------------

    def list_channels(
        self,
        types: str = 'public_channel,private_channel',
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List channels the bot has access to."""
        response = self._request('GET', 'conversations.list', data={
            'types': types,
            'limit': limit,
        })

        if response.get('ok'):
            return response.get('channels', [])
        return []

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information."""
        response = self._request('GET', 'conversations.info', data={
            'channel': channel_id,
        })

        if response.get('ok'):
            return response.get('channel')
        return None

    def join_channel(self, channel_id: str) -> Dict[str, Any]:
        """Join a channel."""
        return self._request('POST', 'conversations.join', json_data={
            'channel': channel_id,
        })

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def get_user_info(self, user_id: str) -> Optional[SlackUser]:
        """Get user information."""
        response = self._request('GET', 'users.info', data={
            'user': user_id,
        })

        if response.get('ok'):
            user = response.get('user', {})
            return SlackUser(
                user_id=user.get('id'),
                username=user.get('name'),
                display_name=user.get('profile', {}).get('display_name'),
                email=user.get('profile', {}).get('email'),
                is_bot=user.get('is_bot', False),
            )
        return None

    def list_users(self, limit: int = 100) -> List[SlackUser]:
        """List workspace users."""
        response = self._request('GET', 'users.list', data={
            'limit': limit,
        })

        users = []
        if response.get('ok'):
            for user in response.get('members', []):
                users.append(SlackUser(
                    user_id=user.get('id'),
                    username=user.get('name'),
                    display_name=user.get('profile', {}).get('display_name'),
                    email=user.get('profile', {}).get('email'),
                    is_bot=user.get('is_bot', False),
                ))
        return users

    # -------------------------------------------------------------------------
    # Files
    # -------------------------------------------------------------------------

    def upload_file(
        self,
        channels: str,
        content: str,
        filename: str,
        title: Optional[str] = None,
        filetype: str = 'text',
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to Slack."""
        data = {
            'channels': channels,
            'content': content,
            'filename': filename,
            'filetype': filetype,
        }
        if title:
            data['title'] = title
        if thread_ts:
            data['thread_ts'] = thread_ts

        return self._request('POST', 'files.upload', data=data)


# =============================================================================
# Block Builders
# =============================================================================

class SlackBlockBuilder:
    """Helper for building Slack blocks."""

    @staticmethod
    def section(text: str, accessory: Dict = None) -> Dict[str, Any]:
        """Create a section block."""
        block = {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': text,
            }
        }
        if accessory:
            block['accessory'] = accessory
        return block

    @staticmethod
    def divider() -> Dict[str, Any]:
        """Create a divider block."""
        return {'type': 'divider'}

    @staticmethod
    def header(text: str) -> Dict[str, Any]:
        """Create a header block."""
        return {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': text,
            }
        }

    @staticmethod
    def context(elements: List[str]) -> Dict[str, Any]:
        """Create a context block."""
        return {
            'type': 'context',
            'elements': [
                {'type': 'mrkdwn', 'text': el} for el in elements
            ]
        }

    @staticmethod
    def actions(elements: List[Dict]) -> Dict[str, Any]:
        """Create an actions block."""
        return {
            'type': 'actions',
            'elements': elements,
        }

    @staticmethod
    def button(
        text: str,
        action_id: str,
        value: str = '',
        style: str = None,
    ) -> Dict[str, Any]:
        """Create a button element."""
        button = {
            'type': 'button',
            'text': {
                'type': 'plain_text',
                'text': text,
            },
            'action_id': action_id,
            'value': value,
        }
        if style:
            button['style'] = style
        return button

    @staticmethod
    def input_block(
        label: str,
        action_id: str,
        placeholder: str = '',
        multiline: bool = False,
    ) -> Dict[str, Any]:
        """Create an input block."""
        return {
            'type': 'input',
            'label': {
                'type': 'plain_text',
                'text': label,
            },
            'element': {
                'type': 'plain_text_input',
                'action_id': action_id,
                'placeholder': {
                    'type': 'plain_text',
                    'text': placeholder,
                },
                'multiline': multiline,
            }
        }


# =============================================================================
# Slack Integration Service
# =============================================================================

class SlackIntegrationService:
    """
    Service for integrating MultinotesAI with Slack.

    Usage:
        service = SlackIntegrationService()

        # Send AI response to Slack
        service.send_ai_response(
            channel='#general',
            prompt="What is AI?",
            response="AI is...",
        )

        # Handle incoming Slack command
        service.handle_slash_command(payload)
    """

    def __init__(self):
        self.client = SlackClient()
        self.block_builder = SlackBlockBuilder()

    # -------------------------------------------------------------------------
    # OAuth Flow
    # -------------------------------------------------------------------------

    def get_oauth_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> str:
        """Get Slack OAuth authorization URL."""
        from urllib.parse import urlencode

        params = {
            'client_id': getattr(settings, 'SLACK_CLIENT_ID', ''),
            'redirect_uri': redirect_uri,
            'scope': 'chat:write,channels:read,users:read,commands,files:write',
            'user_scope': 'identify',
        }
        if state:
            params['state'] = state

        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"

    def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Optional[Dict[str, Any]]:
        """Exchange OAuth code for tokens."""
        import requests

        try:
            response = requests.post(
                'https://slack.com/api/oauth.v2.access',
                data={
                    'client_id': getattr(settings, 'SLACK_CLIENT_ID', ''),
                    'client_secret': getattr(settings, 'SLACK_CLIENT_SECRET', ''),
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
            )

            data = response.json()
            if data.get('ok'):
                return data
            return None

        except Exception as e:
            logger.error(f"Slack OAuth error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Request Verification
    # -------------------------------------------------------------------------

    def verify_request(
        self,
        timestamp: str,
        signature: str,
        body: str,
    ) -> bool:
        """Verify Slack request signature."""
        signing_secret = getattr(settings, 'SLACK_SIGNING_SECRET', '')

        # Check timestamp freshness (5 minutes)
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False

        # Compute signature
        sig_basestring = f'v0:{timestamp}:{body}'
        my_signature = 'v0=' + hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(my_signature, signature)

    # -------------------------------------------------------------------------
    # Send Messages
    # -------------------------------------------------------------------------

    def send_ai_response(
        self,
        channel: str,
        prompt: str,
        response: str,
        model_name: str = 'AI',
        thread_ts: Optional[str] = None,
        include_prompt: bool = True,
    ) -> Dict[str, Any]:
        """Send an AI response to Slack with formatting."""
        blocks = []

        if include_prompt:
            blocks.append(self.block_builder.header('Prompt'))
            blocks.append(self.block_builder.section(f"```{prompt[:2900]}```"))
            blocks.append(self.block_builder.divider())

        blocks.append(self.block_builder.header('Response'))
        blocks.append(self.block_builder.section(response[:2900]))
        blocks.append(self.block_builder.context([f"_Generated by {model_name} via MultinotesAI_"]))

        return self.client.send_blocks(
            channel=channel,
            blocks=blocks,
            text=f"AI Response: {response[:100]}...",
            thread_ts=thread_ts,
        )

    def send_conversation(
        self,
        channel: str,
        messages: List[Dict[str, str]],
        title: str = 'Conversation',
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a conversation thread to Slack."""
        blocks = [self.block_builder.header(title)]

        for msg in messages[:20]:  # Limit to 20 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:500]

            if role == 'user':
                blocks.append(self.block_builder.section(f"*User:*\n{content}"))
            else:
                blocks.append(self.block_builder.section(f"*Assistant:*\n{content}"))

        blocks.append(self.block_builder.divider())
        blocks.append(self.block_builder.context(['_Exported from MultinotesAI_']))

        return self.client.send_blocks(
            channel=channel,
            blocks=blocks,
            text=f"Conversation: {title}",
            thread_ts=thread_ts,
        )

    def send_notification(
        self,
        channel: str,
        title: str,
        message: str,
        level: str = 'info',
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a notification to Slack."""
        emoji_map = {
            'info': ':information_source:',
            'success': ':white_check_mark:',
            'warning': ':warning:',
            'error': ':x:',
        }

        emoji = emoji_map.get(level, ':bell:')
        text = f"{emoji} *{title}*\n{message}"

        return self.client.send_text(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
        )

    # -------------------------------------------------------------------------
    # Slash Commands
    # -------------------------------------------------------------------------

    def handle_slash_command(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle incoming slash command."""
        command = payload.get('command', '')
        text = payload.get('text', '')
        user_id = payload.get('user_id', '')
        channel_id = payload.get('channel_id', '')
        response_url = payload.get('response_url', '')

        logger.info(f"Slack command: {command} from {user_id}")

        if command == '/ask' or command == '/multinotes':
            return self._handle_ask_command(text, user_id, channel_id, response_url)
        elif command == '/summarize':
            return self._handle_summarize_command(text, user_id, channel_id, response_url)
        else:
            return {
                'response_type': 'ephemeral',
                'text': f"Unknown command: {command}",
            }

    def _handle_ask_command(
        self,
        text: str,
        user_id: str,
        channel_id: str,
        response_url: str,
    ) -> Dict[str, Any]:
        """Handle /ask command."""
        if not text:
            return {
                'response_type': 'ephemeral',
                'text': "Please provide a question. Usage: `/ask <your question>`",
            }

        # Queue async processing
        self._queue_ai_request(
            prompt=text,
            user_id=user_id,
            channel_id=channel_id,
            response_url=response_url,
        )

        return {
            'response_type': 'in_channel',
            'text': f"Processing your question: _{text}_\n:hourglass: Generating response...",
        }

    def _handle_summarize_command(
        self,
        text: str,
        user_id: str,
        channel_id: str,
        response_url: str,
    ) -> Dict[str, Any]:
        """Handle /summarize command."""
        if not text:
            return {
                'response_type': 'ephemeral',
                'text': "Please provide text to summarize. Usage: `/summarize <text>`",
            }

        prompt = f"Please summarize the following text:\n\n{text}"

        self._queue_ai_request(
            prompt=prompt,
            user_id=user_id,
            channel_id=channel_id,
            response_url=response_url,
        )

        return {
            'response_type': 'ephemeral',
            'text': ":hourglass: Generating summary...",
        }

    def _queue_ai_request(
        self,
        prompt: str,
        user_id: str,
        channel_id: str,
        response_url: str,
    ):
        """Queue AI request for async processing."""
        try:
            from coreapp.tasks import process_slack_ai_request

            process_slack_ai_request.delay(
                prompt=prompt,
                user_id=user_id,
                channel_id=channel_id,
                response_url=response_url,
            )
        except Exception as e:
            logger.error(f"Failed to queue Slack AI request: {e}")
            # Fall back to sync processing
            self._process_ai_request_sync(prompt, channel_id, response_url)

    def _process_ai_request_sync(
        self,
        prompt: str,
        channel_id: str,
        response_url: str,
    ):
        """Process AI request synchronously."""
        import requests

        try:
            from coreapp.services.llm_service import llm_service

            response = llm_service.generate(
                prompt=prompt,
                model='gpt-3.5-turbo',
                max_tokens=1000,
            )

            ai_response = response.get('text', 'No response generated.')

            # Send response
            requests.post(response_url, json={
                'response_type': 'in_channel',
                'text': ai_response,
            })

        except Exception as e:
            logger.error(f"Slack AI request failed: {e}")
            requests.post(response_url, json={
                'response_type': 'ephemeral',
                'text': f"Error: {str(e)}",
            })

    # -------------------------------------------------------------------------
    # Interactive Components
    # -------------------------------------------------------------------------

    def handle_interaction(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle interactive component callbacks."""
        action_type = payload.get('type', '')

        if action_type == 'block_actions':
            return self._handle_block_action(payload)
        elif action_type == 'view_submission':
            return self._handle_view_submission(payload)
        else:
            return {'ok': True}

    def _handle_block_action(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle block action callbacks."""
        actions = payload.get('actions', [])

        for action in actions:
            action_id = action.get('action_id', '')
            value = action.get('value', '')

            if action_id == 'regenerate_response':
                # Handle regeneration
                pass
            elif action_id == 'save_response':
                # Handle saving
                pass

        return {'ok': True}

    def _handle_view_submission(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle modal submission."""
        return {'ok': True}

    # -------------------------------------------------------------------------
    # Export to Slack
    # -------------------------------------------------------------------------

    def export_prompt_to_slack(
        self,
        user_id: int,
        prompt_id: int,
        channel: str,
        bot_token: str = None,
    ) -> bool:
        """Export a prompt and responses to Slack."""
        try:
            from coreapp.models import Prompt, PromptResponse

            if bot_token:
                self.client = SlackClient(bot_token)

            prompt = Prompt.objects.get(id=prompt_id, user_id=user_id)
            responses = PromptResponse.objects.filter(prompt=prompt).order_by('created_at')

            messages = [{'role': 'user', 'content': prompt.prompt}]
            for resp in responses:
                messages.append({
                    'role': 'assistant',
                    'content': resp.response,
                })

            result = self.send_conversation(
                channel=channel,
                messages=messages,
                title=f"Conversation: {prompt.prompt[:30]}...",
            )

            return result.get('ok', False)

        except Exception as e:
            logger.exception(f"Failed to export to Slack: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

slack_service = SlackIntegrationService()
