import api from './api';

/**
 * Documents Service
 *
 * Handles folder and file management API calls.
 * Backend: /api/user/... (coreapp)
 */
const documentsService = {
  /**
   * Get all folders for the user
   */
  getFolders: async (parentId = null) => {
    const response = await api.get('/user/get_user_folders/');
    return response.data;
  },

  /**
   * Get folder details
   */
  getFolder: async (folderId) => {
    const response = await api.get(`/user/get_folder/${folderId}/`);
    return response.data;
  },

  /**
   * Get folder contents (files and subfolders)
   */
  getFolderContents: async (folderId) => {
    const response = await api.get('/user/folder_list/', {
      params: { folder_id: folderId },
    });
    return response.data;
  },

  /**
   * Get root, recent, and shared files
   */
  getRootRecentShared: async () => {
    const response = await api.get('/user/get_root_recent_share_file/');
    return response.data;
  },

  /**
   * Create a new folder
   */
  createFolder: async (data) => {
    const response = await api.post('/user/create_folder/', data);
    return response.data;
  },

  /**
   * Update folder
   */
  updateFolder: async (folderId, data) => {
    const response = await api.put(`/user/update_folder/${folderId}/`, data);
    return response.data;
  },

  /**
   * Delete folder
   */
  deleteFolder: async (folderId) => {
    await api.delete(`/user/delete_folder/${folderId}/`);
  },

  /**
   * Get all user content/files
   */
  getDocuments: async (folderId = null) => {
    const response = await api.get('/user/get_contents/');
    return response.data;
  },

  /**
   * Get document/content details
   */
  getDocument: async (documentId) => {
    const response = await api.get(`/user/get_content/${documentId}/`);
    return response.data;
  },

  /**
   * Upload a new document/file
   */
  uploadDocument: async (file, folderId = null, onProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (folderId) {
      formData.append('folder', folderId);
    }

    const response = await api.post('/user/create_content/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress
        ? (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(percentCompleted);
          }
        : undefined,
    });
    return response.data;
  },

  /**
   * Update document/content
   */
  updateDocument: async (documentId, data) => {
    const response = await api.put(`/user/update_content/${documentId}/`, data);
    return response.data;
  },

  /**
   * Delete document/content
   */
  deleteDocument: async (documentId) => {
    await api.delete(`/user/delete_content/${documentId}/`);
  },

  /**
   * Delete common file (folder, document, or file)
   */
  deleteCommonFile: async (fileId) => {
    await api.delete(`/user/delete_common_file/${fileId}/`);
  },

  /**
   * Share content with another user
   */
  shareDocument: async (shareData) => {
    const response = await api.post('/user/create_share_content/', shareData);
    return response.data;
  },

  /**
   * Get shared content
   */
  getSharedDocuments: async () => {
    const response = await api.get('/user/sahre_with_me_file/');
    return response.data;
  },

  /**
   * Get share content details
   */
  getShareContent: async (shareId) => {
    const response = await api.get(`/user/get_share_content/${shareId}/`);
    return response.data;
  },

  /**
   * Update share content
   */
  updateShareContent: async (shareId, data) => {
    const response = await api.put(`/user/update_share_content/${shareId}/`, data);
    return response.data;
  },

  /**
   * Delete share content
   */
  deleteShareContent: async (shareId) => {
    await api.delete(`/user/delete_share_content/${shareId}/`);
  },

  /**
   * Get user storage usage details
   */
  getStorageUsage: async () => {
    const response = await api.get('/user/user_storage_view/');
    return response.data;
  },

  /**
   * Get prompt library
   */
  getPromptLibrary: async () => {
    const response = await api.get('/user/prompt_library/');
    return response.data;
  },

  /**
   * Get prompt library folders
   */
  getPromptLibraryFolders: async () => {
    const response = await api.get('/user/prompt_library_folders/');
    return response.data;
  },

  /**
   * Get notebooks
   */
  getNotebooks: async () => {
    const response = await api.get('/user/notebook_listing/');
    return response.data;
  },

  /**
   * Create/update notebook
   */
  saveNotebook: async (data) => {
    const response = await api.post('/user/notebook/', data);
    return response.data;
  },

  /**
   * Get notebook folder list
   */
  getNotebookFolders: async () => {
    const response = await api.get('/user/notebook_folderlist/');
    return response.data;
  },

  /**
   * Get currently opened notebook
   */
  getOpenedNotebook: async () => {
    const response = await api.get('/user/opened_notebook/');
    return response.data;
  },

  /**
   * Close notebook
   */
  closeNotebook: async () => {
    const response = await api.post('/user/close_notebook/');
    return response.data;
  },
};

export default documentsService;
