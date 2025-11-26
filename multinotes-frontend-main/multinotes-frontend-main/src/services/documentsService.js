import api from './api';

const documentsService = {
  getFolders: async (parentId = null) => {
    const params = parentId ? { parent_id: parentId } : {};
    const response = await api.get('/coreapp/folders/', { params });
    return response.data;
  },

  getFolderContents: async (folderId) => {
    const response = await api.get(`/coreapp/folders/${folderId}/contents/`);
    return response.data;
  },

  createFolder: async (data) => {
    const response = await api.post('/coreapp/folders/', data);
    return response.data;
  },

  updateFolder: async (folderId, data) => {
    const response = await api.patch(`/coreapp/folders/${folderId}/`, data);
    return response.data;
  },

  deleteFolder: async (folderId) => {
    await api.delete(`/coreapp/folders/${folderId}/`);
  },

  getDocuments: async (folderId = null) => {
    const params = folderId ? { folder_id: folderId } : {};
    const response = await api.get('/coreapp/documents/', { params });
    return response.data;
  },

  getDocument: async (documentId) => {
    const response = await api.get(`/coreapp/documents/${documentId}/`);
    return response.data;
  },

  uploadDocument: async (file, folderId = null, onProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (folderId) {
      formData.append('folder_id', folderId);
    }

    const response = await api.post('/coreapp/documents/', formData, {
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

  updateDocument: async (documentId, data) => {
    const response = await api.patch(`/coreapp/documents/${documentId}/`, data);
    return response.data;
  },

  deleteDocument: async (documentId) => {
    await api.delete(`/coreapp/documents/${documentId}/`);
  },

  downloadDocument: async (documentId) => {
    const response = await api.get(`/coreapp/documents/${documentId}/download/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  moveItems: async (items, targetFolderId) => {
    const response = await api.post('/coreapp/documents/move/', {
      items,
      target_folder_id: targetFolderId,
    });
    return response.data;
  },

  shareDocument: async (documentId, shareData) => {
    const response = await api.post(`/coreapp/documents/${documentId}/share/`, shareData);
    return response.data;
  },

  getSharedDocuments: async () => {
    const response = await api.get('/coreapp/documents/shared/');
    return response.data;
  },

  getStorageUsage: async () => {
    const response = await api.get('/coreapp/storage/usage/');
    return response.data;
  },

  searchDocuments: async (query) => {
    const response = await api.get('/coreapp/documents/search/', {
      params: { q: query },
    });
    return response.data;
  },
};

export default documentsService;
