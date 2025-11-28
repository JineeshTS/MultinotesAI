import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import documentsService from '../../services/documentsService';

const initialState = {
  folders: [],
  documents: [],
  currentFolder: null,
  sharedDocuments: [],
  storageUsage: {
    used: 0,
    total: 0,
    percentage: 0,
  },
  selectedItems: [],
  viewMode: 'list', // 'list' or 'grid'
  sortBy: 'updated_at',
  sortOrder: 'desc',
  isLoading: false,
  error: null,
};

export const fetchFolders = createAsyncThunk(
  'documents/fetchFolders',
  async (parentId = null, { rejectWithValue }) => {
    try {
      const response = await documentsService.getFolders(parentId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch folders');
    }
  }
);

export const fetchDocuments = createAsyncThunk(
  'documents/fetchDocuments',
  async (folderId = null, { rejectWithValue }) => {
    try {
      const response = await documentsService.getDocuments(folderId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch documents');
    }
  }
);

export const fetchFolderContents = createAsyncThunk(
  'documents/fetchFolderContents',
  async (folderId, { rejectWithValue }) => {
    try {
      const response = await documentsService.getFolderContents(folderId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch folder contents');
    }
  }
);

export const createFolder = createAsyncThunk(
  'documents/createFolder',
  async (data, { rejectWithValue }) => {
    try {
      const response = await documentsService.createFolder(data);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create folder');
    }
  }
);

export const updateFolder = createAsyncThunk(
  'documents/updateFolder',
  async ({ folderId, data }, { rejectWithValue }) => {
    try {
      const response = await documentsService.updateFolder(folderId, data);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update folder');
    }
  }
);

export const deleteFolder = createAsyncThunk(
  'documents/deleteFolder',
  async (folderId, { rejectWithValue }) => {
    try {
      await documentsService.deleteFolder(folderId);
      return folderId;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete folder');
    }
  }
);

export const uploadDocument = createAsyncThunk(
  'documents/uploadDocument',
  async ({ file, folderId, onProgress }, { rejectWithValue }) => {
    try {
      const response = await documentsService.uploadDocument(file, folderId, onProgress);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to upload document');
    }
  }
);

export const deleteDocument = createAsyncThunk(
  'documents/deleteDocument',
  async (documentId, { rejectWithValue }) => {
    try {
      await documentsService.deleteDocument(documentId);
      return documentId;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete document');
    }
  }
);

export const moveItems = createAsyncThunk(
  'documents/moveItems',
  async ({ items, targetFolderId }, { rejectWithValue }) => {
    try {
      const response = await documentsService.moveItems(items, targetFolderId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to move items');
    }
  }
);

export const shareDocument = createAsyncThunk(
  'documents/shareDocument',
  async ({ documentId, shareData }, { rejectWithValue }) => {
    try {
      const response = await documentsService.shareDocument(documentId, shareData);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to share document');
    }
  }
);

export const fetchSharedDocuments = createAsyncThunk(
  'documents/fetchSharedDocuments',
  async (_, { rejectWithValue }) => {
    try {
      const response = await documentsService.getSharedDocuments();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch shared documents');
    }
  }
);

export const fetchStorageUsage = createAsyncThunk(
  'documents/fetchStorageUsage',
  async (_, { rejectWithValue }) => {
    try {
      const response = await documentsService.getStorageUsage();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch storage usage');
    }
  }
);

const documentsSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {
    setCurrentFolder: (state, action) => {
      state.currentFolder = action.payload;
    },
    setViewMode: (state, action) => {
      state.viewMode = action.payload;
    },
    setSortBy: (state, action) => {
      state.sortBy = action.payload;
    },
    setSortOrder: (state, action) => {
      state.sortOrder = action.payload;
    },
    toggleItemSelection: (state, action) => {
      const itemId = action.payload;
      const index = state.selectedItems.indexOf(itemId);
      if (index === -1) {
        state.selectedItems.push(itemId);
      } else {
        state.selectedItems.splice(index, 1);
      }
    },
    selectAllItems: (state) => {
      const allIds = [
        ...state.folders.map((f) => `folder-${f.id}`),
        ...state.documents.map((d) => `doc-${d.id}`),
      ];
      state.selectedItems = allIds;
    },
    clearSelection: (state) => {
      state.selectedItems = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Folders
      .addCase(fetchFolders.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchFolders.fulfilled, (state, action) => {
        state.isLoading = false;
        state.folders = action.payload;
      })
      .addCase(fetchFolders.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Fetch Documents
      .addCase(fetchDocuments.fulfilled, (state, action) => {
        state.documents = action.payload;
      })

      // Fetch Folder Contents
      .addCase(fetchFolderContents.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchFolderContents.fulfilled, (state, action) => {
        state.isLoading = false;
        state.folders = action.payload.folders || [];
        state.documents = action.payload.documents || [];
        state.currentFolder = action.payload.current_folder || null;
      })
      .addCase(fetchFolderContents.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Create Folder
      .addCase(createFolder.fulfilled, (state, action) => {
        state.folders.push(action.payload);
      })

      // Update Folder
      .addCase(updateFolder.fulfilled, (state, action) => {
        const index = state.folders.findIndex((f) => f.id === action.payload.id);
        if (index !== -1) {
          state.folders[index] = action.payload;
        }
      })

      // Delete Folder
      .addCase(deleteFolder.fulfilled, (state, action) => {
        state.folders = state.folders.filter((f) => f.id !== action.payload);
      })

      // Upload Document
      .addCase(uploadDocument.fulfilled, (state, action) => {
        state.documents.push(action.payload);
      })

      // Delete Document
      .addCase(deleteDocument.fulfilled, (state, action) => {
        state.documents = state.documents.filter((d) => d.id !== action.payload);
      })

      // Move Items
      .addCase(moveItems.fulfilled, (state) => {
        state.selectedItems = [];
      })

      // Fetch Shared Documents
      .addCase(fetchSharedDocuments.fulfilled, (state, action) => {
        state.sharedDocuments = action.payload;
      })

      // Fetch Storage Usage
      .addCase(fetchStorageUsage.fulfilled, (state, action) => {
        state.storageUsage = action.payload;
      });
  },
});

export const {
  setCurrentFolder,
  setViewMode,
  setSortBy,
  setSortOrder,
  toggleItemSelection,
  selectAllItems,
  clearSelection,
} = documentsSlice.actions;

export default documentsSlice.reducer;
