import { configureStore, combineReducers } from '@reduxjs/toolkit';
import { persistStore, persistReducer, FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER } from 'redux-persist';
import storage from 'redux-persist/lib/storage';

import authReducer from './slices/authSlice';
import uiReducer from './slices/uiSlice';
import tokenReducer from './slices/tokenSlice';
import chatReducer from './slices/chatSlice';
import documentsReducer from './slices/documentsSlice';
import templatesReducer from './slices/templatesSlice';

const rootReducer = combineReducers({
  auth: authReducer,
  ui: uiReducer,
  tokens: tokenReducer,
  chat: chatReducer,
  documents: documentsReducer,
  templates: templatesReducer,
});

const persistConfig = {
  key: 'multinotes',
  version: 1,
  storage,
  whitelist: ['auth', 'ui'], // Only persist auth and ui state
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }),
  devTools: import.meta.env.DEV,
});

export const persistor = persistStore(store);
