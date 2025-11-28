import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { toggleCommandPalette } from '../store/slices/uiSlice';

const useKeyboardShortcuts = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (event) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const cmdKey = isMac ? event.metaKey : event.ctrlKey;

      // Command Palette: Cmd/Ctrl + K
      if (cmdKey && event.key === 'k') {
        event.preventDefault();
        dispatch(toggleCommandPalette());
      }

      // New Chat: Cmd/Ctrl + N
      if (cmdKey && event.key === 'n') {
        event.preventDefault();
        navigate('/ai/chat');
      }

      // Search: Cmd/Ctrl + /
      if (cmdKey && event.key === '/') {
        event.preventDefault();
        dispatch(toggleCommandPalette());
      }

      // Settings: Cmd/Ctrl + ,
      if (cmdKey && event.key === ',') {
        event.preventDefault();
        navigate('/settings');
      }

      // Escape: Close modals/panels
      if (event.key === 'Escape') {
        // Handle by individual components
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dispatch, navigate]);
};

export default useKeyboardShortcuts;
