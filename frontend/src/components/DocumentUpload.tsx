import React, { useEffect } from 'react';
import clsx from 'clsx';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  FileText,
  Trash2,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import type { Document } from '../types';

interface DocumentUploadProps {
  collectionName: string;
  documents: Document[];
  uploading: boolean;
  uploadProgress: string | null;
  error: string | null;
  onUpload: (file: File) => void;
  onDelete: (documentId: number) => void;
  onClose: () => void;
  onRefresh: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function DocumentUpload({
  collectionName,
  documents,
  uploading,
  uploadProgress,
  error,
  onUpload,
  onDelete,
  onClose,
  onRefresh,
}: DocumentUploadProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      acceptedFiles.forEach((file) => onUpload(file));
    },
    accept: { 'application/pdf': ['.pdf'] },
    disabled: uploading,
    maxSize: 50 * 1024 * 1024,
    multiple: true,
  });

  useEffect(() => {
    onRefresh();
  }, []);

  return (
    <div className="fixed inset-0 bg-black/40 sidebar-overlay flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-2xl max-h-[85vh] flex flex-col animate-fade-in overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-text-primary">Manage Documents</h2>
            <p className="text-sm text-text-secondary mt-0.5">
              Collection: <span className="font-medium text-primary-600">{collectionName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
          >
            <X size={18} className="text-text-secondary" />
          </button>
        </div>

        {/* Upload Area */}
        <div className="p-6">
          <div
            {...getRootProps()}
            className={clsx(
              'border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all',
              isDragActive
                ? 'border-primary-400 bg-primary-50'
                : uploading
                ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
                : 'border-gray-200 hover:border-primary-300 hover:bg-primary-50/30'
            )}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={36} className="text-primary-500 animate-spin" />
                <p className="text-sm text-text-secondary">{uploadProgress || 'Processing...'}</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center">
                  <Upload size={24} className="text-primary-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {isDragActive
                      ? 'Drop your PDF files here...'
                      : 'Drag & drop PDF files here, or click to browse'}
                  </p>
                  <p className="text-xs text-text-secondary mt-1">Supports PDF files up to 50 MB</p>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 px-4 py-2.5 rounded-xl">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Uploaded Documents ({documents.length})
          </h3>
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="group flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100/80 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center flex-shrink-0">
                    <FileText size={18} className="text-primary-500" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {doc.filename}
                    </p>
                    <p className="text-xs text-text-secondary">
                      {formatFileSize(doc.file_size)} &middot; {doc.page_count} pages &middot;{' '}
                      {doc.chunk_count} chunks
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {doc.status === 'ready' && (
                    <CheckCircle2 size={16} className="text-emerald-500" />
                  )}
                  {doc.status === 'processing' && (
                    <Loader2 size={16} className="text-amber-500 animate-spin" />
                  )}
                  {doc.status === 'error' && (
                    <span title={doc.error_message || 'Processing failed'}>
                      <AlertCircle size={16} className="text-red-500" />
                    </span>
                  )}
                  <button
                    onClick={() => onDelete(doc.id)}
                    className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-50 rounded-lg transition-all"
                    title="Delete document"
                  >
                    <Trash2 size={14} className="text-red-400" />
                  </button>
                </div>
              </div>
            ))}
            {documents.length === 0 && (
              <p className="text-sm text-text-secondary text-center py-6">
                No documents uploaded yet. Drop a PDF above to get started.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
