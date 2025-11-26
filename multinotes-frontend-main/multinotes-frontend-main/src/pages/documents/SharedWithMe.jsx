import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  DocumentIcon,
  UserCircleIcon,
  EyeIcon,
  PencilIcon,
} from '@heroicons/react/24/outline';
import { fetchSharedDocuments } from '../../store/slices/documentsSlice';

const SharedWithMe = () => {
  const dispatch = useDispatch();
  const { sharedDocuments, isLoading } = useSelector((state) => state.documents);

  useEffect(() => {
    dispatch(fetchSharedDocuments());
  }, [dispatch]);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getPermissionBadge = (permission) => {
    switch (permission) {
      case 'edit':
        return (
          <span className="badge-success flex items-center gap-1">
            <PencilIcon className="w-3 h-3" />
            Can Edit
          </span>
        );
      case 'view':
      default:
        return (
          <span className="badge-info flex items-center gap-1">
            <EyeIcon className="w-3 h-3" />
            View Only
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Shared with Me</h1>
        <p className="text-slate-500 mt-1">
          Documents and folders that others have shared with you
        </p>
      </div>

      {isLoading ? (
        <div className="card divide-y divide-slate-200">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-4">
              <div className="skeleton w-10 h-10 rounded-lg" />
              <div className="flex-1">
                <div className="skeleton h-4 w-48 mb-2" />
                <div className="skeleton h-3 w-32" />
              </div>
            </div>
          ))}
        </div>
      ) : sharedDocuments.length > 0 ? (
        <div className="card divide-y divide-slate-200">
          {sharedDocuments.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
            >
              <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                <DocumentIcon className="w-5 h-5 text-slate-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-slate-900 truncate">{doc.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex items-center gap-1 text-sm text-slate-500">
                    <UserCircleIcon className="w-4 h-4" />
                    <span>{doc.shared_by?.name || 'Unknown'}</span>
                  </div>
                  <span className="text-slate-300">•</span>
                  <span className="text-sm text-slate-500">
                    {formatFileSize(doc.size)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {getPermissionBadge(doc.permission)}
                <span className="text-sm text-slate-400">{doc.shared_at}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <DocumentIcon className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-900">
            No shared documents
          </h3>
          <p className="text-slate-500 mt-2">
            Documents shared with you will appear here
          </p>
        </div>
      )}
    </div>
  );
};

export default SharedWithMe;
