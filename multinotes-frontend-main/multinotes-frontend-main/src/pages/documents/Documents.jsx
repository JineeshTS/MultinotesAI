import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import {
  FolderIcon,
  DocumentIcon,
  PlusIcon,
  Squares2X2Icon,
  ListBulletIcon,
  EllipsisVerticalIcon,
  ArrowUpTrayIcon,
  MagnifyingGlassIcon,
  CloudArrowUpIcon,
} from '@heroicons/react/24/outline';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import {
  fetchFolders,
  fetchDocuments,
  createFolder,
  uploadDocument,
  deleteDocument,
  deleteFolder,
  setViewMode,
  fetchStorageUsage,
} from '../../store/slices/documentsSlice';

const Documents = () => {
  const dispatch = useDispatch();
  const {
    folders,
    documents,
    viewMode,
    storageUsage,
    isLoading,
  } = useSelector((state) => state.documents);

  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadProgress, setUploadProgress] = useState(null);

  useEffect(() => {
    dispatch(fetchFolders());
    dispatch(fetchDocuments());
    dispatch(fetchStorageUsage());
  }, [dispatch]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: async (acceptedFiles) => {
      for (const file of acceptedFiles) {
        try {
          await dispatch(
            uploadDocument({
              file,
              folderId: null,
              onProgress: (progress) => setUploadProgress(progress),
            })
          ).unwrap();
          toast.success(`${file.name} uploaded successfully`);
        } catch (error) {
          toast.error(`Failed to upload ${file.name}`);
        }
      }
      setUploadProgress(null);
    },
    noClick: true,
  });

  const handleCreateFolder = async (e) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;

    try {
      await dispatch(createFolder({ name: newFolderName })).unwrap();
      toast.success('Folder created');
      setNewFolderName('');
      setShowNewFolderModal(false);
    } catch (error) {
      toast.error('Failed to create folder');
    }
  };

  const handleDeleteFolder = async (folderId) => {
    if (confirm('Are you sure you want to delete this folder?')) {
      try {
        await dispatch(deleteFolder(folderId)).unwrap();
        toast.success('Folder deleted');
      } catch (error) {
        toast.error('Failed to delete folder');
      }
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (confirm('Are you sure you want to delete this document?')) {
      try {
        await dispatch(deleteDocument(documentId)).unwrap();
        toast.success('Document deleted');
      } catch (error) {
        toast.error('Failed to delete document');
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const filteredItems = [
    ...folders.filter((f) =>
      f.name.toLowerCase().includes(searchQuery.toLowerCase())
    ),
    ...documents.filter((d) =>
      d.name.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  ];

  return (
    <div className="space-y-6" {...getRootProps()}>
      <input {...getInputProps()} />

      {/* Drag Overlay */}
      {isDragActive && (
        <div className="fixed inset-0 z-50 bg-indigo-600/90 flex items-center justify-center">
          <div className="text-center text-white">
            <CloudArrowUpIcon className="w-16 h-16 mx-auto mb-4" />
            <h2 className="text-2xl font-bold">Drop files to upload</h2>
            <p className="mt-2 text-indigo-200">
              Release to start uploading your files
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Documents</h1>
          <p className="text-slate-500 mt-1">
            Manage your files and folders
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNewFolderModal(true)}
            className="btn-secondary flex items-center gap-2"
          >
            <PlusIcon className="w-4 h-4" />
            New Folder
          </button>
          <label className="btn-primary flex items-center gap-2 cursor-pointer">
            <ArrowUpTrayIcon className="w-4 h-4" />
            Upload
            <input
              type="file"
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                files.forEach(async (file) => {
                  try {
                    await dispatch(uploadDocument({ file })).unwrap();
                    toast.success(`${file.name} uploaded`);
                  } catch {
                    toast.error(`Failed to upload ${file.name}`);
                  }
                });
              }}
            />
          </label>
        </div>
      </div>

      {/* Storage Usage */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-600">Storage Used</span>
          <span className="text-sm text-slate-500">
            {formatFileSize(storageUsage.used)} / {formatFileSize(storageUsage.total)}
          </span>
        </div>
        <div className="token-meter">
          <div
            className="token-meter-fill bg-indigo-500"
            style={{ width: `${storageUsage.percentage}%` }}
          />
        </div>
      </div>

      {/* Search and View Toggle */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files and folders..."
            className="input pl-10"
          />
        </div>
        <div className="flex items-center border border-slate-200 rounded-lg">
          <button
            onClick={() => dispatch(setViewMode('list'))}
            className={`p-2 ${
              viewMode === 'list'
                ? 'bg-slate-100 text-slate-900'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <ListBulletIcon className="w-5 h-5" />
          </button>
          <button
            onClick={() => dispatch(setViewMode('grid'))}
            className={`p-2 ${
              viewMode === 'grid'
                ? 'bg-slate-100 text-slate-900'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Squares2X2Icon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Upload Progress */}
      {uploadProgress !== null && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-600">Uploading...</span>
            <span className="text-sm text-slate-500">{uploadProgress}%</span>
          </div>
          <div className="token-meter">
            <div
              className="token-meter-fill bg-green-500"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="card p-4">
              <div className="skeleton h-12 w-12 rounded-xl mb-3" />
              <div className="skeleton h-4 w-3/4 mb-2" />
              <div className="skeleton h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : filteredItems.length > 0 ? (
        viewMode === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {folders.map((folder) => (
              <Link
                key={`folder-${folder.id}`}
                to={`/documents/folder/${folder.id}`}
                className="card p-4 hover:shadow-md transition-shadow group"
              >
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                    <FolderIcon className="w-6 h-6 text-indigo-600" />
                  </div>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      handleDeleteFolder(folder.id);
                    }}
                    className="p-1 hover:bg-slate-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <EllipsisVerticalIcon className="w-5 h-5 text-slate-400" />
                  </button>
                </div>
                <h3 className="font-medium text-slate-900 mt-3 truncate">
                  {folder.name}
                </h3>
                <p className="text-sm text-slate-500 mt-1">
                  {folder.item_count || 0} items
                </p>
              </Link>
            ))}

            {documents.map((doc) => (
              <div
                key={`doc-${doc.id}`}
                className="card p-4 hover:shadow-md transition-shadow group"
              >
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center">
                    <DocumentIcon className="w-6 h-6 text-slate-500" />
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="p-1 hover:bg-slate-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <EllipsisVerticalIcon className="w-5 h-5 text-slate-400" />
                  </button>
                </div>
                <h3 className="font-medium text-slate-900 mt-3 truncate">
                  {doc.name}
                </h3>
                <p className="text-sm text-slate-500 mt-1">
                  {formatFileSize(doc.size)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="card divide-y divide-slate-200">
            {folders.map((folder) => (
              <Link
                key={`folder-${folder.id}`}
                to={`/documents/folder/${folder.id}`}
                className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
              >
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <FolderIcon className="w-5 h-5 text-indigo-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate">
                    {folder.name}
                  </p>
                  <p className="text-sm text-slate-500">
                    {folder.item_count || 0} items
                  </p>
                </div>
                <span className="text-sm text-slate-400">{folder.updated_at}</span>
              </Link>
            ))}

            {documents.map((doc) => (
              <div
                key={`doc-${doc.id}`}
                className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
              >
                <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                  <DocumentIcon className="w-5 h-5 text-slate-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate">{doc.name}</p>
                  <p className="text-sm text-slate-500">
                    {formatFileSize(doc.size)}
                  </p>
                </div>
                <span className="text-sm text-slate-400">{doc.updated_at}</span>
                <button
                  onClick={() => handleDeleteDocument(doc.id)}
                  className="p-2 hover:bg-slate-100 rounded"
                >
                  <EllipsisVerticalIcon className="w-5 h-5 text-slate-400" />
                </button>
              </div>
            ))}
          </div>
        )
      ) : (
        <div className="card p-12 text-center">
          <FolderIcon className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-900">No files yet</h3>
          <p className="text-slate-500 mt-2 max-w-sm mx-auto">
            Drag and drop files here or click upload to get started
          </p>
          <label className="btn-primary mt-4 inline-flex items-center gap-2 cursor-pointer">
            <ArrowUpTrayIcon className="w-4 h-4" />
            Upload Files
            <input type="file" multiple className="hidden" />
          </label>
        </div>
      )}

      {/* New Folder Modal */}
      {showNewFolderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              Create New Folder
            </h2>
            <form onSubmit={handleCreateFolder}>
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="Folder name"
                className="input mb-4"
                autoFocus
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowNewFolderModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Documents;
