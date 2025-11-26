"""
Streaming response handler for MultinotesAI.

This module provides:
- Server-Sent Events (SSE) streaming
- WebSocket message handling
- Chunked response generation
- Stream buffering and rate limiting
"""

import json
import asyncio
import logging
from typing import Generator, AsyncGenerator, Optional, Callable, Any
from datetime import datetime

from django.http import StreamingHttpResponse
from rest_framework.response import Response
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


# =============================================================================
# SSE Response Handler
# =============================================================================

class SSEEvent:
    """Represents a Server-Sent Event."""

    def __init__(
        self,
        data: Any,
        event: str = None,
        id: str = None,
        retry: int = None
    ):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def encode(self) -> str:
        """Encode event to SSE format."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        if self.event:
            lines.append(f"event: {self.event}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Handle data (can be multi-line)
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)

        for line in data_str.split('\n'):
            lines.append(f"data: {line}")

        lines.append('')  # Empty line to end event
        lines.append('')

        return '\n'.join(lines)


class SSEStreamingResponse(StreamingHttpResponse):
    """
    Streaming HTTP response for Server-Sent Events.

    Usage:
        def event_generator():
            for chunk in get_ai_response():
                yield SSEEvent(data=chunk, event='message')

        return SSEStreamingResponse(event_generator())
    """

    def __init__(self, generator, *args, **kwargs):
        super().__init__(
            streaming_content=self._encode_events(generator),
            content_type='text/event-stream',
            *args,
            **kwargs
        )
        self['Cache-Control'] = 'no-cache'
        self['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        self['Connection'] = 'keep-alive'

    def _encode_events(self, generator):
        """Encode generator items as SSE events."""
        for item in generator:
            if isinstance(item, SSEEvent):
                yield item.encode()
            elif isinstance(item, dict):
                yield SSEEvent(data=item).encode()
            else:
                yield SSEEvent(data=str(item)).encode()


# =============================================================================
# AI Stream Handler
# =============================================================================

class AIStreamHandler:
    """
    Handler for streaming AI responses.

    Usage:
        handler = AIStreamHandler()

        def get_response():
            return handler.stream_response(
                ai_generator=openai_client.chat.completions.create(...),
                user_id=request.user.id,
            )
    """

    def __init__(
        self,
        buffer_size: int = 10,
        timeout: float = 60.0,
        heartbeat_interval: float = 15.0
    ):
        self.buffer_size = buffer_size
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval

    def stream_response(
        self,
        ai_generator: Generator,
        user_id: int = None,
        on_start: Callable = None,
        on_chunk: Callable = None,
        on_complete: Callable = None,
        on_error: Callable = None,
    ) -> Generator[SSEEvent, None, None]:
        """
        Stream AI response with callbacks.

        Args:
            ai_generator: Generator yielding AI response chunks
            user_id: User ID for logging
            on_start: Callback when streaming starts
            on_chunk: Callback for each chunk
            on_complete: Callback when streaming completes
            on_error: Callback on error

        Yields:
            SSEEvent objects
        """
        start_time = datetime.now()
        total_tokens = 0
        full_response = []

        try:
            # Start event
            yield SSEEvent(
                data={'status': 'started', 'timestamp': start_time.isoformat()},
                event='start'
            )

            if on_start:
                on_start()

            # Stream chunks
            for chunk in ai_generator:
                chunk_data = self._process_chunk(chunk)

                if chunk_data:
                    full_response.append(chunk_data.get('content', ''))
                    total_tokens += chunk_data.get('tokens', 0)

                    yield SSEEvent(
                        data=chunk_data,
                        event='message'
                    )

                    if on_chunk:
                        on_chunk(chunk_data)

            # Complete event
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            completion_data = {
                'status': 'completed',
                'duration_seconds': duration,
                'total_tokens': total_tokens,
                'timestamp': end_time.isoformat(),
            }

            yield SSEEvent(
                data=completion_data,
                event='complete'
            )

            if on_complete:
                on_complete(''.join(full_response), total_tokens)

            logger.info(
                f"AI stream completed for user {user_id}: "
                f"{total_tokens} tokens in {duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"AI stream error for user {user_id}: {e}")

            yield SSEEvent(
                data={'error': str(e), 'status': 'error'},
                event='error'
            )

            if on_error:
                on_error(e)

            raise

    def _process_chunk(self, chunk) -> Optional[dict]:
        """
        Process a chunk from the AI provider.

        Handles different provider formats (OpenAI, Anthropic, etc.)
        """
        try:
            # OpenAI format
            if hasattr(chunk, 'choices') and chunk.choices:
                choice = chunk.choices[0]
                if hasattr(choice, 'delta') and choice.delta:
                    content = getattr(choice.delta, 'content', None)
                    if content:
                        return {
                            'content': content,
                            'tokens': 1,  # Approximate
                        }

            # Anthropic format
            elif hasattr(chunk, 'type'):
                if chunk.type == 'content_block_delta':
                    return {
                        'content': chunk.delta.text,
                        'tokens': 1,
                    }

            # Generic dict format
            elif isinstance(chunk, dict):
                return {
                    'content': chunk.get('content', ''),
                    'tokens': chunk.get('tokens', 1),
                }

            # String chunk
            elif isinstance(chunk, str):
                return {
                    'content': chunk,
                    'tokens': 1,
                }

        except Exception as e:
            logger.warning(f"Error processing chunk: {e}")

        return None


# =============================================================================
# WebSocket Consumer for Real-time AI
# =============================================================================

class AIWebSocketConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time AI interactions.

    Handles:
    - Connection management
    - Message streaming
    - User authentication
    - Rate limiting
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)  # Unauthorized
            return

        self.user_id = self.user.id
        self.room_name = f"ai_user_{self.user_id}"

        # Join user-specific room
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send_json({
            'type': 'connection',
            'status': 'connected',
            'user_id': self.user_id,
        })

        logger.info(f"WebSocket connected for user {self.user_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(
                self.room_name,
                self.channel_name
            )

        logger.info(f"WebSocket disconnected for user {getattr(self, 'user_id', 'unknown')}")

    async def receive_json(self, content):
        """Handle incoming WebSocket messages."""
        message_type = content.get('type')

        handlers = {
            'generate': self.handle_generate,
            'stop': self.handle_stop,
            'ping': self.handle_ping,
        }

        handler = handlers.get(message_type)
        if handler:
            await handler(content)
        else:
            await self.send_json({
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            })

    async def handle_generate(self, content):
        """Handle AI generation request."""
        prompt = content.get('prompt', '')
        model = content.get('model', 'gpt-4')

        if not prompt:
            await self.send_json({
                'type': 'error',
                'message': 'Prompt is required'
            })
            return

        # Send start event
        await self.send_json({
            'type': 'generation_start',
            'timestamp': datetime.now().isoformat(),
        })

        try:
            # Stream AI response
            async for chunk in self._generate_ai_response(prompt, model):
                await self.send_json({
                    'type': 'chunk',
                    'content': chunk,
                })

            # Send completion
            await self.send_json({
                'type': 'generation_complete',
                'timestamp': datetime.now().isoformat(),
            })

        except Exception as e:
            logger.error(f"AI generation error: {e}")
            await self.send_json({
                'type': 'error',
                'message': str(e),
            })

    async def _generate_ai_response(
        self,
        prompt: str,
        model: str
    ) -> AsyncGenerator[str, None]:
        """
        Generate AI response (placeholder for actual implementation).

        In production, this would call the actual AI provider.
        """
        # Placeholder - replace with actual AI call
        response = f"AI response to: {prompt}"
        for word in response.split():
            await asyncio.sleep(0.1)  # Simulate streaming delay
            yield word + " "

    async def handle_stop(self, content):
        """Handle stop generation request."""
        # Set flag to stop current generation
        self.stop_generation = True

        await self.send_json({
            'type': 'generation_stopped',
            'timestamp': datetime.now().isoformat(),
        })

    async def handle_ping(self, content):
        """Handle ping/heartbeat."""
        await self.send_json({
            'type': 'pong',
            'timestamp': datetime.now().isoformat(),
        })

    # Group message handlers
    async def ai_message(self, event):
        """Handle AI message from channel layer."""
        await self.send_json(event['message'])


# =============================================================================
# Chunked Response Builder
# =============================================================================

class ChunkedResponseBuilder:
    """
    Build chunked responses for large data transfers.

    Usage:
        builder = ChunkedResponseBuilder(chunk_size=1024)
        response = builder.build_response(
            data_generator=fetch_large_data(),
            content_type='application/json'
        )
    """

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size

    def build_response(
        self,
        data_generator: Generator,
        content_type: str = 'application/octet-stream',
        filename: str = None
    ) -> StreamingHttpResponse:
        """
        Build streaming HTTP response from generator.

        Args:
            data_generator: Generator yielding data chunks
            content_type: MIME type of response
            filename: Optional filename for download

        Returns:
            StreamingHttpResponse
        """
        response = StreamingHttpResponse(
            streaming_content=self._chunk_generator(data_generator),
            content_type=content_type
        )

        if filename:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    def _chunk_generator(self, data_generator: Generator) -> Generator[bytes, None, None]:
        """Process and yield data in chunks."""
        buffer = b''

        for data in data_generator:
            if isinstance(data, str):
                data = data.encode('utf-8')

            buffer += data

            while len(buffer) >= self.chunk_size:
                yield buffer[:self.chunk_size]
                buffer = buffer[self.chunk_size:]

        if buffer:
            yield buffer


# =============================================================================
# Stream Rate Limiter
# =============================================================================

class StreamRateLimiter:
    """
    Rate limiter for streaming responses.

    Prevents abuse by limiting the rate of chunks sent.
    """

    def __init__(
        self,
        max_chunks_per_second: float = 100,
        max_bytes_per_second: int = 1024 * 1024  # 1MB/s
    ):
        self.max_chunks_per_second = max_chunks_per_second
        self.max_bytes_per_second = max_bytes_per_second
        self.chunk_interval = 1.0 / max_chunks_per_second

    async def rate_limited_generator(
        self,
        generator: AsyncGenerator
    ) -> AsyncGenerator:
        """
        Wrap generator with rate limiting.

        Args:
            generator: Async generator to rate limit

        Yields:
            Rate-limited chunks
        """
        last_chunk_time = 0
        bytes_this_second = 0
        second_start = asyncio.get_event_loop().time()

        async for chunk in generator:
            current_time = asyncio.get_event_loop().time()

            # Reset byte counter every second
            if current_time - second_start >= 1.0:
                bytes_this_second = 0
                second_start = current_time

            # Check byte rate limit
            chunk_size = len(chunk) if isinstance(chunk, (bytes, str)) else 0
            if bytes_this_second + chunk_size > self.max_bytes_per_second:
                await asyncio.sleep(1.0 - (current_time - second_start))
                bytes_this_second = 0
                second_start = asyncio.get_event_loop().time()

            # Check chunk rate limit
            time_since_last = current_time - last_chunk_time
            if time_since_last < self.chunk_interval:
                await asyncio.sleep(self.chunk_interval - time_since_last)

            bytes_this_second += chunk_size
            last_chunk_time = asyncio.get_event_loop().time()

            yield chunk


# =============================================================================
# Utility Functions
# =============================================================================

def create_sse_response(generator: Generator) -> SSEStreamingResponse:
    """
    Create an SSE streaming response from a generator.

    Args:
        generator: Generator yielding data

    Returns:
        SSEStreamingResponse
    """
    return SSEStreamingResponse(generator)


def stream_json_array(items_generator: Generator) -> Generator[str, None, None]:
    """
    Stream items as a JSON array.

    Useful for streaming large lists without loading everything into memory.

    Args:
        items_generator: Generator yielding items

    Yields:
        JSON chunks forming an array
    """
    yield '['

    first = True
    for item in items_generator:
        if not first:
            yield ','
        yield json.dumps(item)
        first = False

    yield ']'
