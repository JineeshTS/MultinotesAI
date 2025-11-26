"""
Discord Integration Service for MultinotesAI.

This module provides:
- Send AI responses to Discord channels
- Discord bot interactions
- Webhook notifications
- Slash command support

WBS Item: 6.2.7 - Discord integration
"""

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Discord Configuration
# =============================================================================

class InteractionType(Enum):
    """Discord interaction types."""
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class InteractionResponseType(Enum):
    """Discord interaction response types."""
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    MODAL = 9


class EmbedColor(Enum):
    """Discord embed colors."""
    DEFAULT = 0x5865F2
    SUCCESS = 0x57F287
    WARNING = 0xFEE75C
    ERROR = 0xED4245
    INFO = 0x5865F2


@dataclass
class DiscordEmbed:
    """Discord embed message."""
    title: Optional[str] = None
    description: Optional[str] = None
    color: int = EmbedColor.DEFAULT.value
    url: Optional[str] = None
    timestamp: Optional[str] = None
    footer: Optional[Dict[str, str]] = None
    thumbnail: Optional[Dict[str, str]] = None
    image: Optional[Dict[str, str]] = None
    author: Optional[Dict[str, str]] = None
    fields: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        embed = {}
        if self.title:
            embed['title'] = self.title
        if self.description:
            embed['description'] = self.description
        if self.color:
            embed['color'] = self.color
        if self.url:
            embed['url'] = self.url
        if self.timestamp:
            embed['timestamp'] = self.timestamp
        if self.footer:
            embed['footer'] = self.footer
        if self.thumbnail:
            embed['thumbnail'] = self.thumbnail
        if self.image:
            embed['image'] = self.image
        if self.author:
            embed['author'] = self.author
        if self.fields:
            embed['fields'] = self.fields
        return embed

    def add_field(
        self,
        name: str,
        value: str,
        inline: bool = False,
    ):
        """Add a field to the embed."""
        self.fields.append({
            'name': name,
            'value': value,
            'inline': inline,
        })


# =============================================================================
# Discord API Client
# =============================================================================

class DiscordClient:
    """
    Client for Discord API.
    """

    BASE_URL = 'https://discord.com/api/v10'

    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or getattr(settings, 'DISCORD_BOT_TOKEN', '')

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Make a request to Discord API."""
        import requests

        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json',
        }

        response = requests.request(method, url, headers=headers, json=json_data)

        if response.status_code == 204:
            return {'ok': True}

        return response.json()

    # -------------------------------------------------------------------------
    # Messaging
    # -------------------------------------------------------------------------

    def send_message(
        self,
        channel_id: str,
        content: str = '',
        embeds: List[DiscordEmbed] = None,
        components: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Send a message to a channel."""
        data = {}
        if content:
            data['content'] = content
        if embeds:
            data['embeds'] = [e.to_dict() for e in embeds]
        if components:
            data['components'] = components

        return self._request('POST', f'channels/{channel_id}/messages', json_data=data)

    def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str = None,
        embeds: List[DiscordEmbed] = None,
    ) -> Dict[str, Any]:
        """Edit a message."""
        data = {}
        if content is not None:
            data['content'] = content
        if embeds:
            data['embeds'] = [e.to_dict() for e in embeds]

        return self._request('PATCH', f'channels/{channel_id}/messages/{message_id}', json_data=data)

    def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> Dict[str, Any]:
        """Delete a message."""
        return self._request('DELETE', f'channels/{channel_id}/messages/{message_id}')

    def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """Add a reaction to a message."""
        return self._request('PUT', f'channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me')

    # -------------------------------------------------------------------------
    # Webhooks
    # -------------------------------------------------------------------------

    def execute_webhook(
        self,
        webhook_url: str,
        content: str = '',
        embeds: List[DiscordEmbed] = None,
        username: str = None,
        avatar_url: str = None,
    ) -> Dict[str, Any]:
        """Execute a webhook."""
        import requests

        data = {}
        if content:
            data['content'] = content
        if embeds:
            data['embeds'] = [e.to_dict() for e in embeds]
        if username:
            data['username'] = username
        if avatar_url:
            data['avatar_url'] = avatar_url

        response = requests.post(webhook_url, json=data)

        if response.status_code == 204:
            return {'ok': True}

        return response.json()

    # -------------------------------------------------------------------------
    # Channels
    # -------------------------------------------------------------------------

    def get_channel(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information."""
        return self._request('GET', f'channels/{channel_id}')

    def list_guild_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        """List channels in a guild."""
        return self._request('GET', f'guilds/{guild_id}/channels')

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        return self._request('GET', f'users/{user_id}')

    def get_current_user(self) -> Dict[str, Any]:
        """Get current bot user."""
        return self._request('GET', 'users/@me')

    # -------------------------------------------------------------------------
    # Application Commands
    # -------------------------------------------------------------------------

    def register_global_command(
        self,
        application_id: str,
        name: str,
        description: str,
        options: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Register a global slash command."""
        data = {
            'name': name,
            'description': description,
        }
        if options:
            data['options'] = options

        return self._request('POST', f'applications/{application_id}/commands', json_data=data)

    def list_global_commands(
        self,
        application_id: str,
    ) -> List[Dict[str, Any]]:
        """List global slash commands."""
        return self._request('GET', f'applications/{application_id}/commands')


# =============================================================================
# Discord Embed Builder
# =============================================================================

class DiscordEmbedBuilder:
    """Helper for building Discord embeds."""

    @staticmethod
    def ai_response(
        prompt: str,
        response: str,
        model_name: str = 'AI',
    ) -> DiscordEmbed:
        """Create an embed for AI response."""
        embed = DiscordEmbed(
            title='AI Response',
            color=EmbedColor.INFO.value,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Truncate if necessary
        if len(prompt) > 1024:
            prompt = prompt[:1021] + '...'
        if len(response) > 4096:
            response = response[:4093] + '...'

        embed.add_field('Prompt', prompt, inline=False)
        embed.description = response
        embed.footer = {'text': f'Generated by {model_name} via MultinotesAI'}

        return embed

    @staticmethod
    def conversation(
        messages: List[Dict[str, str]],
        title: str = 'Conversation',
    ) -> List[DiscordEmbed]:
        """Create embeds for a conversation."""
        embeds = []

        main_embed = DiscordEmbed(
            title=title,
            color=EmbedColor.DEFAULT.value,
            timestamp=datetime.utcnow().isoformat(),
        )

        for i, msg in enumerate(messages[:10]):  # Limit to 10 messages
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')[:1024]
            main_embed.add_field(role, content, inline=False)

        main_embed.footer = {'text': 'Exported from MultinotesAI'}
        embeds.append(main_embed)

        return embeds

    @staticmethod
    def notification(
        title: str,
        message: str,
        level: str = 'info',
    ) -> DiscordEmbed:
        """Create a notification embed."""
        color_map = {
            'info': EmbedColor.INFO.value,
            'success': EmbedColor.SUCCESS.value,
            'warning': EmbedColor.WARNING.value,
            'error': EmbedColor.ERROR.value,
        }

        return DiscordEmbed(
            title=title,
            description=message,
            color=color_map.get(level, EmbedColor.DEFAULT.value),
            timestamp=datetime.utcnow().isoformat(),
        )

    @staticmethod
    def error(
        message: str,
        details: str = None,
    ) -> DiscordEmbed:
        """Create an error embed."""
        embed = DiscordEmbed(
            title='Error',
            description=message,
            color=EmbedColor.ERROR.value,
        )
        if details:
            embed.add_field('Details', details, inline=False)
        return embed


# =============================================================================
# Discord Integration Service
# =============================================================================

class DiscordIntegrationService:
    """
    Service for integrating MultinotesAI with Discord.

    Usage:
        service = DiscordIntegrationService()

        # Send AI response to Discord
        service.send_ai_response(
            channel_id='123456789',
            prompt="What is AI?",
            response="AI is...",
        )

        # Handle incoming interaction
        response = service.handle_interaction(payload)
    """

    def __init__(self):
        self.client = DiscordClient()
        self.embed_builder = DiscordEmbedBuilder()

    # -------------------------------------------------------------------------
    # Request Verification
    # -------------------------------------------------------------------------

    def verify_request(
        self,
        signature: str,
        timestamp: str,
        body: str,
    ) -> bool:
        """Verify Discord request signature."""
        public_key = getattr(settings, 'DISCORD_PUBLIC_KEY', '')

        try:
            verify_key = VerifyKey(bytes.fromhex(public_key))
            verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
            return True
        except BadSignatureError:
            return False
        except Exception as e:
            logger.error(f"Discord verification error: {e}")
            return False

    # -------------------------------------------------------------------------
    # OAuth Flow
    # -------------------------------------------------------------------------

    def get_oauth_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
        permissions: int = 2048,  # Send messages
    ) -> str:
        """Get Discord OAuth authorization URL."""
        from urllib.parse import urlencode

        params = {
            'client_id': getattr(settings, 'DISCORD_CLIENT_ID', ''),
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'bot applications.commands',
            'permissions': permissions,
        }
        if state:
            params['state'] = state

        return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"

    def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Optional[Dict[str, Any]]:
        """Exchange OAuth code for tokens."""
        import requests

        try:
            response = requests.post(
                'https://discord.com/api/oauth2/token',
                data={
                    'client_id': getattr(settings, 'DISCORD_CLIENT_ID', ''),
                    'client_secret': getattr(settings, 'DISCORD_CLIENT_SECRET', ''),
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.error(f"Discord OAuth error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Send Messages
    # -------------------------------------------------------------------------

    def send_ai_response(
        self,
        channel_id: str,
        prompt: str,
        response: str,
        model_name: str = 'AI',
    ) -> Dict[str, Any]:
        """Send an AI response to Discord."""
        embed = self.embed_builder.ai_response(prompt, response, model_name)
        return self.client.send_message(channel_id, embeds=[embed])

    def send_conversation(
        self,
        channel_id: str,
        messages: List[Dict[str, str]],
        title: str = 'Conversation',
    ) -> Dict[str, Any]:
        """Send a conversation to Discord."""
        embeds = self.embed_builder.conversation(messages, title)
        return self.client.send_message(channel_id, embeds=embeds)

    def send_notification(
        self,
        channel_id: str,
        title: str,
        message: str,
        level: str = 'info',
    ) -> Dict[str, Any]:
        """Send a notification to Discord."""
        embed = self.embed_builder.notification(title, message, level)
        return self.client.send_message(channel_id, embeds=[embed])

    def send_webhook(
        self,
        webhook_url: str,
        content: str = '',
        embeds: List[DiscordEmbed] = None,
        username: str = 'MultinotesAI',
    ) -> Dict[str, Any]:
        """Send a message via webhook."""
        return self.client.execute_webhook(
            webhook_url=webhook_url,
            content=content,
            embeds=embeds,
            username=username,
        )

    # -------------------------------------------------------------------------
    # Interaction Handling
    # -------------------------------------------------------------------------

    def handle_interaction(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle incoming Discord interaction."""
        interaction_type = payload.get('type')

        if interaction_type == InteractionType.PING.value:
            return {'type': InteractionResponseType.PONG.value}

        elif interaction_type == InteractionType.APPLICATION_COMMAND.value:
            return self._handle_command(payload)

        elif interaction_type == InteractionType.MESSAGE_COMPONENT.value:
            return self._handle_component(payload)

        elif interaction_type == InteractionType.MODAL_SUBMIT.value:
            return self._handle_modal(payload)

        return {
            'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE.value,
            'data': {
                'content': 'Unknown interaction type',
                'flags': 64,  # Ephemeral
            }
        }

    def _handle_command(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle slash command."""
        data = payload.get('data', {})
        command_name = data.get('name', '')
        options = {o['name']: o['value'] for o in data.get('options', [])}

        if command_name == 'ask':
            return self._handle_ask_command(payload, options)
        elif command_name == 'summarize':
            return self._handle_summarize_command(payload, options)
        elif command_name == 'help':
            return self._handle_help_command(payload)
        else:
            return {
                'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                'data': {
                    'content': f'Unknown command: {command_name}',
                    'flags': 64,
                }
            }

    def _handle_ask_command(
        self,
        payload: Dict[str, Any],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle /ask command."""
        question = options.get('question', '')

        if not question:
            return {
                'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                'data': {
                    'content': 'Please provide a question.',
                    'flags': 64,
                }
            }

        # Defer response for async processing
        self._queue_ai_request(
            prompt=question,
            interaction_id=payload.get('id'),
            interaction_token=payload.get('token'),
            channel_id=payload.get('channel_id'),
        )

        return {
            'type': InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE.value,
        }

    def _handle_summarize_command(
        self,
        payload: Dict[str, Any],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle /summarize command."""
        text = options.get('text', '')

        if not text:
            return {
                'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                'data': {
                    'content': 'Please provide text to summarize.',
                    'flags': 64,
                }
            }

        prompt = f"Please summarize the following text:\n\n{text}"

        self._queue_ai_request(
            prompt=prompt,
            interaction_id=payload.get('id'),
            interaction_token=payload.get('token'),
            channel_id=payload.get('channel_id'),
        )

        return {
            'type': InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE.value,
        }

    def _handle_help_command(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle /help command."""
        embed = DiscordEmbed(
            title='MultinotesAI Help',
            description='Available commands:',
            color=EmbedColor.INFO.value,
        )

        embed.add_field('/ask <question>', 'Ask the AI a question', inline=False)
        embed.add_field('/summarize <text>', 'Summarize text', inline=False)
        embed.add_field('/help', 'Show this help message', inline=False)

        return {
            'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE.value,
            'data': {
                'embeds': [embed.to_dict()],
            }
        }

    def _handle_component(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle message component interaction."""
        data = payload.get('data', {})
        custom_id = data.get('custom_id', '')

        if custom_id.startswith('regenerate_'):
            # Handle regeneration
            pass

        return {
            'type': InteractionResponseType.DEFERRED_UPDATE_MESSAGE.value,
        }

    def _handle_modal(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle modal submission."""
        return {
            'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE.value,
            'data': {
                'content': 'Modal submitted',
                'flags': 64,
            }
        }

    def _queue_ai_request(
        self,
        prompt: str,
        interaction_id: str,
        interaction_token: str,
        channel_id: str,
    ):
        """Queue AI request for async processing."""
        try:
            from coreapp.tasks import process_discord_ai_request

            process_discord_ai_request.delay(
                prompt=prompt,
                interaction_id=interaction_id,
                interaction_token=interaction_token,
                channel_id=channel_id,
            )
        except Exception as e:
            logger.error(f"Failed to queue Discord AI request: {e}")

    # -------------------------------------------------------------------------
    # Followup Messages
    # -------------------------------------------------------------------------

    def send_followup(
        self,
        application_id: str,
        interaction_token: str,
        content: str = '',
        embeds: List[DiscordEmbed] = None,
    ) -> Dict[str, Any]:
        """Send a followup message to an interaction."""
        import requests

        url = f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}"

        data = {}
        if content:
            data['content'] = content
        if embeds:
            data['embeds'] = [e.to_dict() for e in embeds]

        response = requests.post(url, json=data)
        return response.json()

    def edit_original(
        self,
        application_id: str,
        interaction_token: str,
        content: str = None,
        embeds: List[DiscordEmbed] = None,
    ) -> Dict[str, Any]:
        """Edit the original interaction response."""
        import requests

        url = f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}/messages/@original"

        data = {}
        if content is not None:
            data['content'] = content
        if embeds:
            data['embeds'] = [e.to_dict() for e in embeds]

        response = requests.patch(url, json=data)
        return response.json()

    # -------------------------------------------------------------------------
    # Export to Discord
    # -------------------------------------------------------------------------

    def export_prompt_to_discord(
        self,
        user_id: int,
        prompt_id: int,
        channel_id: str,
    ) -> bool:
        """Export a prompt and responses to Discord."""
        try:
            from coreapp.models import Prompt, PromptResponse

            prompt = Prompt.objects.get(id=prompt_id, user_id=user_id)
            responses = PromptResponse.objects.filter(prompt=prompt).order_by('created_at')

            messages = [{'role': 'user', 'content': prompt.prompt}]
            for resp in responses:
                messages.append({
                    'role': 'assistant',
                    'content': resp.response,
                })

            result = self.send_conversation(
                channel_id=channel_id,
                messages=messages,
                title=f"Conversation: {prompt.prompt[:30]}...",
            )

            return 'id' in result

        except Exception as e:
            logger.exception(f"Failed to export to Discord: {e}")
            return False

    # -------------------------------------------------------------------------
    # Command Registration
    # -------------------------------------------------------------------------

    def register_commands(
        self,
        application_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Register slash commands with Discord."""
        app_id = application_id or getattr(settings, 'DISCORD_APPLICATION_ID', '')

        commands = [
            {
                'name': 'ask',
                'description': 'Ask the AI a question',
                'options': [
                    {
                        'name': 'question',
                        'description': 'Your question',
                        'type': 3,  # STRING
                        'required': True,
                    }
                ],
            },
            {
                'name': 'summarize',
                'description': 'Summarize text',
                'options': [
                    {
                        'name': 'text',
                        'description': 'Text to summarize',
                        'type': 3,  # STRING
                        'required': True,
                    }
                ],
            },
            {
                'name': 'help',
                'description': 'Show help information',
            },
        ]

        results = []
        for cmd in commands:
            result = self.client.register_global_command(
                application_id=app_id,
                name=cmd['name'],
                description=cmd['description'],
                options=cmd.get('options'),
            )
            results.append(result)

        return results


# =============================================================================
# Singleton Instance
# =============================================================================

discord_service = DiscordIntegrationService()
