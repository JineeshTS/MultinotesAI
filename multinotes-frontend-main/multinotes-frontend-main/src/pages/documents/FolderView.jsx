import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { ChevronRightIcon, HomeIcon } from '@heroicons/react/24/outline';
import { fetchFolderContents } from '../../store/slices/documentsSlice';
import Documents from './Documents';

const FolderView = () => {
  const { folderId } = useParams();
  const dispatch = useDispatch();
  const { currentFolder } = useSelector((state) => state.documents);

  useEffect(() => {
    dispatch(fetchFolderContents(folderId));
  }, [dispatch, folderId]);

  // Build breadcrumb path
  const breadcrumbs = [];
  if (currentFolder) {
    let folder = currentFolder;
    while (folder) {
      breadcrumbs.unshift(folder);
      folder = folder.parent;
    }
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center space-x-2 text-sm">
        <Link
          to="/documents"
          className="flex items-center gap-1 text-slate-500 hover:text-slate-700"
        >
          <HomeIcon className="w-4 h-4" />
          <span>Documents</span>
        </Link>
        {breadcrumbs.map((folder) => (
          <div key={folder.id} className="flex items-center gap-2">
            <ChevronRightIcon className="w-4 h-4 text-slate-400" />
            <Link
              to={`/documents/folder/${folder.id}`}
              className={`${
                folder.id === currentFolder?.id
                  ? 'text-slate-900 font-medium'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {folder.name}
            </Link>
          </div>
        ))}
      </nav>

      {/* Reuse Documents component for content display */}
      <Documents />
    </div>
  );
};

export default FolderView;
