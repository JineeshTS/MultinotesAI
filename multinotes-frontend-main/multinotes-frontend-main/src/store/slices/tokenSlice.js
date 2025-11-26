import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import tokenService from '../../services/tokenService';

const initialState = {
  balance: 0,
  usedTokens: 0,
  totalTokens: 0,
  usageHistory: [],
  usageBreakdown: [],
  dailyUsage: [],
  isLoading: false,
  error: null,
};

export const fetchTokenBalance = createAsyncThunk(
  'tokens/fetchBalance',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tokenService.getBalance();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch token balance');
    }
  }
);

export const fetchUsageHistory = createAsyncThunk(
  'tokens/fetchUsageHistory',
  async (params, { rejectWithValue }) => {
    try {
      const response = await tokenService.getUsageHistory(params);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch usage history');
    }
  }
);

export const fetchUsageBreakdown = createAsyncThunk(
  'tokens/fetchUsageBreakdown',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tokenService.getUsageBreakdown();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch usage breakdown');
    }
  }
);

export const fetchDailyUsage = createAsyncThunk(
  'tokens/fetchDailyUsage',
  async (days = 30, { rejectWithValue }) => {
    try {
      const response = await tokenService.getDailyUsage(days);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch daily usage');
    }
  }
);

const tokenSlice = createSlice({
  name: 'tokens',
  initialState,
  reducers: {
    updateBalance: (state, action) => {
      state.balance = action.payload.balance;
      state.usedTokens = action.payload.usedTokens || state.usedTokens;
    },
    deductTokens: (state, action) => {
      state.balance -= action.payload;
      state.usedTokens += action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Balance
      .addCase(fetchTokenBalance.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchTokenBalance.fulfilled, (state, action) => {
        state.isLoading = false;
        state.balance = action.payload.balance;
        state.usedTokens = action.payload.used_tokens;
        state.totalTokens = action.payload.total_tokens;
      })
      .addCase(fetchTokenBalance.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Fetch Usage History
      .addCase(fetchUsageHistory.fulfilled, (state, action) => {
        state.usageHistory = action.payload;
      })

      // Fetch Usage Breakdown
      .addCase(fetchUsageBreakdown.fulfilled, (state, action) => {
        state.usageBreakdown = action.payload;
      })

      // Fetch Daily Usage
      .addCase(fetchDailyUsage.fulfilled, (state, action) => {
        state.dailyUsage = action.payload;
      });
  },
});

export const { updateBalance, deductTokens } = tokenSlice.actions;
export default tokenSlice.reducer;
