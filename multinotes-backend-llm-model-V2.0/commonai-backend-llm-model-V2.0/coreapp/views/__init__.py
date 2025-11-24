"""
CoreApp Views Package.

This package contains all views for the coreapp module, organized by functionality.
For backwards compatibility, all views are re-exported from this __init__.py.

Module Structure:
- base.py: Common utilities, pagination, response helpers
- llm_views.py: LLM CRUD operations (TODO: migrate from views.py)
- generation_views.py: AI generation endpoints (TODO: migrate from views.py)
- folder_views.py: Folder management (TODO: migrate from views.py)
- document_views.py: Document handling (TODO: migrate from views.py)
- storage_views.py: Storage management (TODO: migrate from views.py)
- sharing_views.py: Content sharing (TODO: migrate from views.py)
"""

# Import base utilities
from .base import (
    StandardResultsSetPagination,
    LargeResultsSetPagination,
    format_number,
    calculate_storage_size,
    get_date_range,
    success_response,
    error_response,
    paginated_response,
    check_user_tokens,
    deduct_tokens,
    validate_ownership,
    get_user_subscription,
    get_user_storage,
)

# Re-export all views from the original views.py for backwards compatibility
# This allows existing imports to continue working while we migrate
from ..views import (
    # Generation Views
    GenerateView,
    GenerateImage,
    GenerateFromImage,

    # Category Views
    CategoryListingView,

    # Prompt Views
    PromptLibraryView,
    PromptSingleView,
    PromptLibraryFolderList,
    PromptsFolder,
    PromptDocument,
    PromptResponseDetail,
    PromptDetail,
    PromptResponseImage,
    UpdateResponseType,

    # Folder Views
    FolderLibraryView,
    FolderMngt,
    GetUserFolderView,
    DeleteFolderView,
    FolderDetailView,

    # Notebook Views
    NoteBookListingView,
    NoteBookView,
    NoteBookFolderList,
    NotesFolder,
    NoteListForModal,
    CurrentNoteBook,
    CloseNoteBook,

    # LLM Views
    CreateLLMModel,
    GetLLMModel,
    GetAllLLMModelByUser,
    GetLLMModelByAdmin,
    GetLLMModelByIds,
    UpdateLLMModel,
    DeleteLLMModel,

    # Group/History Views
    GroupHistoryView,
    GroupResponseView,

    # Dashboard Views
    DashboardCount,
    AdminDashboardCount,
    LatestUser,
    LatestTransaction,
    PerDayUsedToken,

    # Rating Views
    LLM_Rating,
    RatingByLlm,

    # User LLM Views
    UserLlmMngt,

    # File/Content Views
    UserFileView,

    # Share Views
    ShareWithMeView,
    GetRootRecentShareFileView,
    ShareContentView,
    DeleteCommonFileView,

    # Storage Views
    UserStorageDetailView,
    UserStorageView,

    # Other Views
    DownloadVideoView,
    AiProcessView,
)

__all__ = [
    # Base utilities
    'StandardResultsSetPagination',
    'LargeResultsSetPagination',
    'format_number',
    'calculate_storage_size',
    'get_date_range',
    'success_response',
    'error_response',
    'paginated_response',
    'check_user_tokens',
    'deduct_tokens',
    'validate_ownership',
    'get_user_subscription',
    'get_user_storage',

    # All views
    'GenerateView',
    'GenerateImage',
    'GenerateFromImage',
    'CategoryListingView',
    'PromptLibraryView',
    'FolderLibraryView',
    'PromptSingleView',
    'NoteBookListingView',
    'NoteBookView',
    'PromptLibraryFolderList',
    'PromptsFolder',
    'FolderMngt',
    'GetUserFolderView',
    'DeleteFolderView',
    'FolderDetailView',
    'NoteBookFolderList',
    'NotesFolder',
    'NoteListForModal',
    'CurrentNoteBook',
    'CloseNoteBook',
    'CreateLLMModel',
    'GetLLMModel',
    'GetAllLLMModelByUser',
    'GetLLMModelByAdmin',
    'GetLLMModelByIds',
    'UpdateLLMModel',
    'DeleteLLMModel',
    'PromptDocument',
    'PromptResponseDetail',
    'PromptDetail',
    'GroupHistoryView',
    'PromptResponseImage',
    'UpdateResponseType',
    'DashboardCount',
    'AdminDashboardCount',
    'LatestUser',
    'LatestTransaction',
    'PerDayUsedToken',
    'LLM_Rating',
    'RatingByLlm',
    'UserLlmMngt',
    'UserFileView',
    'ShareWithMeView',
    'GetRootRecentShareFileView',
    'UserStorageDetailView',
    'ShareContentView',
    'DeleteCommonFileView',
    'UserStorageView',
    'GroupResponseView',
    'DownloadVideoView',
    'AiProcessView',
]
