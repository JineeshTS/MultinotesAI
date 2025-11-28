import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import chatService from '../../services/chatService';

const initialState = {
  conversations: [],
  currentConversation: null,
  messages: [],
  models: [],
  selectedModel: null,
  isGenerating: false,
  isLoading: false,
  error: null,
  streamingMessage: '',
};

export const fetchConversations = createAsyncThunk(
  'chat/fetchConversations',
  async (_, { rejectWithValue }) => {
    try {
      const response = await chatService.getConversations();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch conversations');
    }
  }
);

export const fetchConversation = createAsyncThunk(
  'chat/fetchConversation',
  async (conversationId, { rejectWithValue }) => {
    try {
      const response = await chatService.getConversation(conversationId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch conversation');
    }
  }
);

export const fetchModels = createAsyncThunk(
  'chat/fetchModels',
  async (_, { rejectWithValue }) => {
    try {
      const response = await chatService.getModels();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch models');
    }
  }
);

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ prompt, modelId, conversationId }, { rejectWithValue }) => {
    try {
      const response = await chatService.sendMessage({
        prompt,
        llm_id: modelId,
        conversation_id: conversationId,
      });
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to send message');
    }
  }
);

export const createConversation = createAsyncThunk(
  'chat/createConversation',
  async (data, { rejectWithValue }) => {
    try {
      const response = await chatService.createConversation(data);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create conversation');
    }
  }
);

export const deleteConversation = createAsyncThunk(
  'chat/deleteConversation',
  async (conversationId, { rejectWithValue }) => {
    try {
      await chatService.deleteConversation(conversationId);
      return conversationId;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete conversation');
    }
  }
);

export const rateResponse = createAsyncThunk(
  'chat/rateResponse',
  async ({ responseId, rating }, { rejectWithValue }) => {
    try {
      const response = await chatService.rateResponse(responseId, rating);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to rate response');
    }
  }
);

export const regenerateResponse = createAsyncThunk(
  'chat/regenerateResponse',
  async ({ responseId }, { rejectWithValue }) => {
    try {
      const response = await chatService.regenerateResponse(responseId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to regenerate response');
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setSelectedModel: (state, action) => {
      state.selectedModel = action.payload;
    },
    clearCurrentConversation: (state) => {
      state.currentConversation = null;
      state.messages = [];
    },
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    updateStreamingMessage: (state, action) => {
      state.streamingMessage = action.payload;
    },
    clearStreamingMessage: (state) => {
      state.streamingMessage = '';
    },
    setIsGenerating: (state, action) => {
      state.isGenerating = action.payload;
    },
    updateMessageRating: (state, action) => {
      const { messageId, rating } = action.payload;
      const message = state.messages.find((m) => m.id === messageId);
      if (message) {
        message.rating = rating;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Conversations
      .addCase(fetchConversations.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.isLoading = false;
        state.conversations = action.payload;
      })
      .addCase(fetchConversations.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Fetch Single Conversation
      .addCase(fetchConversation.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConversation.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentConversation = action.payload;
        state.messages = action.payload.messages || [];
      })
      .addCase(fetchConversation.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Fetch Models
      .addCase(fetchModels.fulfilled, (state, action) => {
        state.models = action.payload;
        if (!state.selectedModel && action.payload.length > 0) {
          state.selectedModel = action.payload[0];
        }
      })

      // Send Message
      .addCase(sendMessage.pending, (state) => {
        state.isGenerating = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isGenerating = false;
        state.messages.push(action.payload);
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isGenerating = false;
        state.error = action.payload;
      })

      // Create Conversation
      .addCase(createConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload);
        state.currentConversation = action.payload;
        state.messages = [];
      })

      // Delete Conversation
      .addCase(deleteConversation.fulfilled, (state, action) => {
        state.conversations = state.conversations.filter((c) => c.id !== action.payload);
        if (state.currentConversation?.id === action.payload) {
          state.currentConversation = null;
          state.messages = [];
        }
      })

      // Rate Response
      .addCase(rateResponse.fulfilled, (state, action) => {
        const message = state.messages.find((m) => m.id === action.payload.id);
        if (message) {
          message.rating = action.payload.rating;
        }
      })

      // Regenerate Response
      .addCase(regenerateResponse.pending, (state) => {
        state.isGenerating = true;
      })
      .addCase(regenerateResponse.fulfilled, (state, action) => {
        state.isGenerating = false;
        const index = state.messages.findIndex((m) => m.id === action.payload.original_id);
        if (index !== -1) {
          state.messages[index] = action.payload;
        }
      })
      .addCase(regenerateResponse.rejected, (state, action) => {
        state.isGenerating = false;
        state.error = action.payload;
      });
  },
});

export const {
  setSelectedModel,
  clearCurrentConversation,
  addMessage,
  updateStreamingMessage,
  clearStreamingMessage,
  setIsGenerating,
  updateMessageRating,
} = chatSlice.actions;

export default chatSlice.reducer;
