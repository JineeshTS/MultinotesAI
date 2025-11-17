from django.urls import path
from .views import *
from .webSocket import TextGenerationAPIView, TextEventStream
from .utils import generateUsingGemini2, generateUsingTogether2, generateUsingOpenAi, TestTextByTogether
from .aigenerator import *

urlpatterns=[
    # path('generate/',GenerateView.as_view()),
    # path('generate_image/',GenerateImage.as_view()),
    # path('generate_from_image/',GenerateFromImage.as_view()),

    path('get_model/<int:pk>/',GetLLMModel.as_view()),
    path('get_model_by_admin/<int:pk>/',GetLLMModelByAdmin.as_view()),
    path('get_models/',GetLLMModel.as_view()),
    # path('get_models_by_user/',GetLLMModelByUser.as_view()),
    path('get_models_by_user/',GetAllLLMModelByUser.as_view()),
    path('get_models_by_admin/',GetLLMModelByAdmin.as_view()),
    path('get_model_by_ids/',GetLLMModelByIds.as_view()),
    path('create_model/',CreateLLMModel.as_view()),
    path('update_model/<int:pk>/',UpdateLLMModel.as_view()),

    path('delete_model/<int:pk>/',DeleteLLMModel.as_view()),

    # ******************************
    # path('categories/',CategoryListingView.as_view()),

    path('prompt_library/',PromptLibraryView.as_view()),
    path('prompt_single/',PromptSingleView.as_view()),
    path('notebook_listing/',NoteBookListingView.as_view()),
    path('notebook/',NoteBookView.as_view()),
    path('prompt_library_folders/',PromptLibraryFolderList.as_view()),
    path('prompt_folder/',PromptsFolder.as_view()),
    path('notebook_folderlist/',NoteBookFolderList.as_view()),
    path('notebook_folder/',NotesFolder.as_view()),
    path('notebooks_existing/',NoteListForModal.as_view()),
    path('opened_notebook/',CurrentNoteBook.as_view()),
    path('close_notebook/',CloseNoteBook.as_view()),


    # path('generate_text_to_text/', TextGenerationAPIView.as_view()),
    # path('generate_text_to_text/', TextEventStream.as_view()),
    # path('generate_text_to_image/', TextToImage.as_view()),
    # path('generate_text_to_speech/', TextToSpeech.as_view()),
    # path('generate_image_to_text/', ImageToText.as_view()),
    # path('generate_speech_to_text/', SpeechToText.as_view()),
    # path('test_event_stream/',TextEventStream.as_view()),
    # path('test_genai/',generateUsingGemini2),
    # path('test_together/',generateUsingTogether2),

    # ****************************************

    path('test_openai/',generateUsingOpenAi),
    # For testing                

    # Text To Text Generator Api
    path('openai_text_to_text/', OpenAiTextToText.as_view()),                  # OpenAi Text
    path('mistral_text_to_text/', MistralTextToText.as_view()),                # Together Text
    path('llama2_text_to_text/', LlamaTextToText.as_view()),                   # Together Text
    path('gemma_instruct_text_to_text/', GemmaInstructTextToText.as_view()),   # Together Text
    path('gemini_pro_text_to_text/', GeminiProTextToText.as_view()),           # Gemini Text

    # Image To Text Generator Api
    path('gemini_picture_to_text/', GeminiPictureToText.as_view()),            # Gemini Image
    path('code_generate_together/', CodeGenerateByTogether.as_view()),         # Together Code

    path('gemini_text_to_image/', GeminiTextToImage.as_view()),                # Together Image
    path('text_to_speech_generate/', TextToSpeechGenerator.as_view()),         # OpenAi Image
    path('speech_to_text_generate/', SpeechToTextGenerator.as_view()),         # OpenAi Image

    path('document/<int:pk>/', PromptDocument.as_view()),
    path('document/', PromptDocument.as_view()),

    path('prompt_response/<int:pk>/', PromptResponseDetail.as_view()),
    path('prompt/<int:pk>/', PromptDetail.as_view()),
    path('prompt/', PromptDetail.as_view()),
    path('update_prompt/<int:pk>/', PromptDetail.as_view()),
    path('prompt_image/', PromptResponseImage.as_view()),

    path('update_response_type/', UpdateResponseType.as_view()),
    path('dashboard_count/', DashboardCount.as_view()),
    path('admin_dashboard_count/', AdminDashboardCount.as_view()),

    path('latest_user/', LatestUser.as_view()),
    path('latest_transaction/', LatestTransaction.as_view()),
    path('per_day_used_token/', PerDayUsedToken.as_view()),

    path('add_rating/', LLM_Rating.as_view()),
    path('get_rating/<int:pk>/', LLM_Rating.as_view()),
    path('get_ratings/', LLM_Rating.as_view()),
    path('get_ratings_by_admin/<int:pk>/', RatingByLlm.as_view()),
    path('update_rating/<int:pk>/', LLM_Rating.as_view()),
    path('delete_rating/<int:pk>/', LLM_Rating.as_view()),

    path('add_user_llm/', UserLlmMngt.as_view()),
    path('get_user_llm/<int:pk>/', UserLlmMngt.as_view()),
    path('get_user_llms/', UserLlmMngt.as_view()),
    path('update_user_llm/<int:pk>/', UserLlmMngt.as_view()),
    path('delete_user_llm/<int:pk>/', UserLlmMngt.as_view()),

    path('folder_library/',FolderLibraryView.as_view()),
    path('create_folder/', FolderMngt.as_view()),
    path('get_folder/<int:pk>/', FolderMngt.as_view()),
    path('get_folders/', FolderMngt.as_view()),
    path('get_user_folders/', GetUserFolderView.as_view()),
    path('update_folder/<int:pk>/', FolderMngt.as_view()),
    path('delete_folder/<int:pk>/', DeleteFolderView.as_view()),

    path('folder_list/', FolderDetailView.as_view()),
    path('get_root_recent_share_file/', GetRootRecentShareFileView.as_view()),
    path('sahre_with_me_file/', ShareWithMeView.as_view()),
    path('delete_common_file/<int:pk>/', DeleteCommonFileView.as_view()),

    path('create_content/', UserFileView.as_view()),
    path('get_content/<int:pk>/', UserFileView.as_view()),
    path('get_contents/', UserFileView.as_view()),
    path('update_content/<int:pk>/', UserFileView.as_view()),
    path('delete_content/<int:pk>/', UserFileView.as_view()),

    path('create_share_content/', ShareContentView.as_view()),
    path('get_share_content/<int:pk>/', ShareContentView.as_view()),
    path('get_share_contents/', ShareContentView.as_view()),
    path('update_share_content/<int:pk>/', ShareContentView.as_view()),
    path('delete_share_content/<int:pk>/', ShareContentView.as_view()),

    path('user_storage_view/', UserStorageDetailView.as_view()),

    path('create_storage/', UserStorageView.as_view()),
    path('get_storage/<int:pk>/', UserStorageView.as_view()),
    path('get_storages/', UserStorageView.as_view()),
    path('update_storage/<int:pk>/', UserStorageView.as_view()),
    path('delete_storage/<int:pk>/', UserStorageView.as_view()),

    # Single API for Text and File
    path('text_ai_generator/', TextAiGeneratorView.as_view()),
    path('file_ai_generator/', FileAiGeneratorView.as_view()), 
    path('dynamic_llm_generator/', DynamicLlmGeneratorView.as_view()), 
    path('test_model/<int:pk>/',TestTextByTogether),

    # Group Response
    path('group_response/', GroupResponseView.as_view()),
    path('group_response/<int:pk>/', GroupResponseView.as_view()),
    path('group_history/<int:pk>/', GroupHistoryView.as_view()),

    path('ai_chatbot/', AiProcessView.as_view()),
    path('ai_chatbot/<int:pk>/', AiProcessView.as_view()),

    path('url_process/', DownloadVideoView.as_view()),
    
]