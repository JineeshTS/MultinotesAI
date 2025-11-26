"""
Export API Views for MultinotesAI.

This module provides REST API endpoints for exporting:
- Documents
- Conversations
- Prompts and responses

WBS Items:
- 4.4.9: Build export functionality (PDF, DOCX, MD)
- 6.2.1-6.2.3: Export formats
"""

import logging
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from coreapp.services.export_service import (
    export_service,
    ExportFormat,
    ExportContent,
    ConversationExport,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Export Formats View
# =============================================================================

class ExportFormatsView(APIView):
    """
    Get available export formats.

    GET /api/export/formats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of available export formats."""
        formats = export_service.get_available_formats()
        return Response({
            'formats': formats,
            'default': 'md'
        })


# =============================================================================
# Document Export View
# =============================================================================

class DocumentExportView(APIView):
    """
    Export a document in various formats.

    GET /api/export/document/<document_id>/?format=pdf
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        """Export a document."""
        from coreapp.models import Document

        # Get format parameter
        format_str = request.query_params.get('format', 'md').lower()
        try:
            export_format = ExportFormat(format_str)
        except ValueError:
            return Response(
                {'error': f'Invalid format: {format_str}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get document
        try:
            document = Document.objects.get(
                id=document_id,
                user=request.user,
                is_delete=False
            )
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prepare export content
        content = ExportContent(
            title=document.title or 'Untitled Document',
            content=document.content or '',
            created_at=document.created_at,
            updated_at=document.updated_at,
            author=request.user.get_full_name() or request.user.username,
            metadata={
                'document_id': str(document.id),
                'folder_id': str(document.folder_id) if document.folder_id else None,
            }
        )

        try:
            # Export
            exported = export_service.export_content(content, export_format)

            # Build response
            content_type = export_service.get_content_type(export_format)
            extension = export_service.get_file_extension(export_format)
            filename = f"{document.title or 'document'}_{timezone.now().strftime('%Y%m%d')}.{extension}"

            # Clean filename
            filename = "".join(c for c in filename if c.isalnum() or c in '._- ')

            if isinstance(exported, bytes):
                response = HttpResponse(exported, content_type=content_type)
            else:
                response = HttpResponse(exported.encode('utf-8'), content_type=content_type)

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except ImportError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            logger.exception(f"Export failed for document {document_id}")
            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Conversation Export View
# =============================================================================

class ConversationExportView(APIView):
    """
    Export a conversation/prompt with responses.

    GET /api/export/conversation/<prompt_id>/?format=pdf
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, prompt_id):
        """Export a conversation."""
        from coreapp.models import Prompt, PromptResponse

        # Get format parameter
        format_str = request.query_params.get('format', 'md').lower()
        try:
            export_format = ExportFormat(format_str)
        except ValueError:
            return Response(
                {'error': f'Invalid format: {format_str}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get prompt
        try:
            prompt = Prompt.objects.get(
                id=prompt_id,
                user=request.user,
                is_delete=False
            )
        except Prompt.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get responses
        responses = PromptResponse.objects.filter(
            prompt=prompt,
            is_delete=False
        ).order_by('created_at').select_related('llm')

        # Build messages
        messages = [
            {'role': 'user', 'content': prompt.prompt_text}
        ]

        for response in responses:
            messages.append({
                'role': 'assistant',
                'content': response.response_text,
            })

        # Get model name
        model_name = None
        if responses.exists():
            first_response = responses.first()
            if first_response and first_response.llm:
                model_name = first_response.llm.name

        # Calculate total tokens
        total_tokens = sum(r.tokens_used or 0 for r in responses)

        # Prepare conversation export
        conversation = ConversationExport(
            title=prompt.title or prompt.prompt_text[:50] + '...',
            messages=messages,
            model_name=model_name,
            created_at=prompt.created_at,
            total_tokens=total_tokens if total_tokens > 0 else None
        )

        try:
            # Export
            exported = export_service.export_conversation(conversation, export_format)

            # Build response
            content_type = export_service.get_content_type(export_format)
            extension = export_service.get_file_extension(export_format)
            filename = f"conversation_{prompt_id}_{timezone.now().strftime('%Y%m%d')}.{extension}"

            if isinstance(exported, bytes):
                response = HttpResponse(exported, content_type=content_type)
            else:
                response = HttpResponse(exported.encode('utf-8'), content_type=content_type)

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except ImportError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            logger.exception(f"Export failed for conversation {prompt_id}")
            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Bulk Export View
# =============================================================================

class BulkExportView(APIView):
    """
    Export multiple items at once.

    POST /api/export/bulk/
    {
        "type": "documents" | "conversations",
        "ids": [1, 2, 3],
        "format": "pdf"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Export multiple items."""
        from coreapp.models import Document, Prompt, PromptResponse
        import zipfile
        import io

        export_type = request.data.get('type')
        ids = request.data.get('ids', [])
        format_str = request.data.get('format', 'md').lower()

        if not export_type or not ids:
            return Response(
                {'error': 'type and ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            export_format = ExportFormat(format_str)
        except ValueError:
            return Response(
                {'error': f'Invalid format: {format_str}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create zip buffer
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                if export_type == 'documents':
                    documents = Document.objects.filter(
                        id__in=ids,
                        user=request.user,
                        is_delete=False
                    )

                    for doc in documents:
                        content = ExportContent(
                            title=doc.title or 'Untitled',
                            content=doc.content or '',
                            created_at=doc.created_at,
                            author=request.user.username
                        )
                        exported = export_service.export_content(content, export_format)

                        filename = f"{doc.title or 'document'}_{doc.id}.{export_format.value}"
                        filename = "".join(c for c in filename if c.isalnum() or c in '._- ')

                        if isinstance(exported, bytes):
                            zip_file.writestr(filename, exported)
                        else:
                            zip_file.writestr(filename, exported.encode('utf-8'))

                elif export_type == 'conversations':
                    prompts = Prompt.objects.filter(
                        id__in=ids,
                        user=request.user,
                        is_delete=False
                    )

                    for prompt in prompts:
                        responses = PromptResponse.objects.filter(
                            prompt=prompt,
                            is_delete=False
                        ).order_by('created_at')

                        messages = [{'role': 'user', 'content': prompt.prompt_text}]
                        for response in responses:
                            messages.append({
                                'role': 'assistant',
                                'content': response.response_text
                            })

                        conversation = ConversationExport(
                            title=prompt.title or prompt.prompt_text[:30],
                            messages=messages,
                            created_at=prompt.created_at
                        )
                        exported = export_service.export_conversation(conversation, export_format)

                        filename = f"conversation_{prompt.id}.{export_format.value}"

                        if isinstance(exported, bytes):
                            zip_file.writestr(filename, exported)
                        else:
                            zip_file.writestr(filename, exported.encode('utf-8'))
                else:
                    return Response(
                        {'error': 'Invalid export type'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Return zip file
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'
            return response

        except Exception as e:
            logger.exception("Bulk export failed")
            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Folder Export View
# =============================================================================

class FolderExportView(APIView):
    """
    Export all documents in a folder.

    GET /api/export/folder/<folder_id>/?format=md
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, folder_id):
        """Export all documents in a folder."""
        from coreapp.models import Folder, Document
        import zipfile
        import io

        format_str = request.query_params.get('format', 'md').lower()
        try:
            export_format = ExportFormat(format_str)
        except ValueError:
            return Response(
                {'error': f'Invalid format: {format_str}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get folder
        try:
            folder = Folder.objects.get(
                id=folder_id,
                user=request.user,
                is_delete=False
            )
        except Folder.DoesNotExist:
            return Response(
                {'error': 'Folder not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get documents in folder
        documents = Document.objects.filter(
            folder=folder,
            user=request.user,
            is_delete=False
        )

        if not documents.exists():
            return Response(
                {'error': 'No documents in folder'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create zip
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for doc in documents:
                    content = ExportContent(
                        title=doc.title or 'Untitled',
                        content=doc.content or '',
                        created_at=doc.created_at,
                        author=request.user.username
                    )
                    exported = export_service.export_content(content, export_format)

                    filename = f"{doc.title or 'document'}_{doc.id}.{export_format.value}"
                    filename = "".join(c for c in filename if c.isalnum() or c in '._- ')

                    if isinstance(exported, bytes):
                        zip_file.writestr(filename, exported)
                    else:
                        zip_file.writestr(filename, exported.encode('utf-8'))

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            folder_name = "".join(c for c in (folder.name or 'folder') if c.isalnum() or c in '._- ')
            response['Content-Disposition'] = f'attachment; filename="{folder_name}_export.zip"'
            return response

        except Exception as e:
            logger.exception(f"Folder export failed for folder {folder_id}")
            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
