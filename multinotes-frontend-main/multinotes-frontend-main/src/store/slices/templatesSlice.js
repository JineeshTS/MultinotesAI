import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import templatesService from '../../services/templatesService';

const initialState = {
  templates: [],
  categories: [],
  favorites: [],
  trending: [],
  userTemplates: [],
  selectedCategory: null,
  searchQuery: '',
  isLoading: false,
  error: null,
};

export const fetchTemplates = createAsyncThunk(
  'templates/fetchTemplates',
  async (params = {}, { rejectWithValue }) => {
    try {
      const response = await templatesService.getTemplates(params);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch templates');
    }
  }
);

export const fetchCategories = createAsyncThunk(
  'templates/fetchCategories',
  async (_, { rejectWithValue }) => {
    try {
      const response = await templatesService.getCategories();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch categories');
    }
  }
);

export const fetchFavorites = createAsyncThunk(
  'templates/fetchFavorites',
  async (_, { rejectWithValue }) => {
    try {
      const response = await templatesService.getFavorites();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch favorites');
    }
  }
);

export const fetchTrending = createAsyncThunk(
  'templates/fetchTrending',
  async (_, { rejectWithValue }) => {
    try {
      const response = await templatesService.getTrending();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch trending templates');
    }
  }
);

export const fetchUserTemplates = createAsyncThunk(
  'templates/fetchUserTemplates',
  async (_, { rejectWithValue }) => {
    try {
      const response = await templatesService.getUserTemplates();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch user templates');
    }
  }
);

export const createTemplate = createAsyncThunk(
  'templates/createTemplate',
  async (data, { rejectWithValue }) => {
    try {
      const response = await templatesService.createTemplate(data);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create template');
    }
  }
);

export const updateTemplate = createAsyncThunk(
  'templates/updateTemplate',
  async ({ templateId, data }, { rejectWithValue }) => {
    try {
      const response = await templatesService.updateTemplate(templateId, data);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update template');
    }
  }
);

export const deleteTemplate = createAsyncThunk(
  'templates/deleteTemplate',
  async (templateId, { rejectWithValue }) => {
    try {
      await templatesService.deleteTemplate(templateId);
      return templateId;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete template');
    }
  }
);

export const toggleFavorite = createAsyncThunk(
  'templates/toggleFavorite',
  async (templateId, { rejectWithValue }) => {
    try {
      const response = await templatesService.toggleFavorite(templateId);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to toggle favorite');
    }
  }
);

export const useTemplate = createAsyncThunk(
  'templates/useTemplate',
  async ({ templateId, variables }, { rejectWithValue }) => {
    try {
      const response = await templatesService.useTemplate(templateId, variables);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to use template');
    }
  }
);

const templatesSlice = createSlice({
  name: 'templates',
  initialState,
  reducers: {
    setSelectedCategory: (state, action) => {
      state.selectedCategory = action.payload;
    },
    setSearchQuery: (state, action) => {
      state.searchQuery = action.payload;
    },
    clearFilters: (state) => {
      state.selectedCategory = null;
      state.searchQuery = '';
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Templates
      .addCase(fetchTemplates.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchTemplates.fulfilled, (state, action) => {
        state.isLoading = false;
        state.templates = action.payload;
      })
      .addCase(fetchTemplates.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Fetch Categories
      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.categories = action.payload;
      })

      // Fetch Favorites
      .addCase(fetchFavorites.fulfilled, (state, action) => {
        state.favorites = action.payload;
      })

      // Fetch Trending
      .addCase(fetchTrending.fulfilled, (state, action) => {
        state.trending = action.payload;
      })

      // Fetch User Templates
      .addCase(fetchUserTemplates.fulfilled, (state, action) => {
        state.userTemplates = action.payload;
      })

      // Create Template
      .addCase(createTemplate.fulfilled, (state, action) => {
        state.userTemplates.push(action.payload);
      })

      // Update Template
      .addCase(updateTemplate.fulfilled, (state, action) => {
        const index = state.userTemplates.findIndex((t) => t.id === action.payload.id);
        if (index !== -1) {
          state.userTemplates[index] = action.payload;
        }
      })

      // Delete Template
      .addCase(deleteTemplate.fulfilled, (state, action) => {
        state.userTemplates = state.userTemplates.filter((t) => t.id !== action.payload);
      })

      // Toggle Favorite
      .addCase(toggleFavorite.fulfilled, (state, action) => {
        const { id, is_favorite } = action.payload;
        const template = state.templates.find((t) => t.id === id);
        if (template) {
          template.is_favorite = is_favorite;
        }
        if (is_favorite) {
          if (!state.favorites.find((f) => f.id === id)) {
            state.favorites.push(action.payload);
          }
        } else {
          state.favorites = state.favorites.filter((f) => f.id !== id);
        }
      });
  },
});

export const { setSelectedCategory, setSearchQuery, clearFilters } = templatesSlice.actions;
export default templatesSlice.reducer;
