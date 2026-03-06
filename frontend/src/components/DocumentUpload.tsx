import React, { useEffect } from 'react';
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
    accept: { 'application/pdf': ['.pdf']},
    disabled: uploading,
    maxSize: 50 * 1024 * 1024, // 50 MB
    multiple: true,
  });

  useEffect(() => {
    onRefresh();
  }, []);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Manage Documents</h2>
            <p className="text-sm text-gray-500">Collection: {collectionName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Upload Area */}
        <div className="p-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-indigo-500 bg-indigo-50'
                : uploading
                ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
                : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 size={36} className="text-indigo-500 animate-spin" />
                <p className="text-sm text-gray-600">{uploadProgress || 'Processing...'}</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload size={36} className="text-gray-400" />
                <p className="text-sm font-medium text-gray-700">
                  {isDragActive
                    ? 'Drop your PDF files here...'
                    : 'Drag & drop PDF files here, or click to browse'}
                </p>
                <p className="text-xs text-gray-400">Supports PDF files up to 50 MB</p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Uploaded Documents ({documents.length})
          </h3>
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText size={20} className="text-indigo-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {doc.filename}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(doc.file_size)} &middot; {doc.page_count} pages &middot;{' '}
                      {doc.chunk_count} chunks
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {doc.status === 'ready' && (
                    <CheckCircle2 size={16} className="text-green-500" />
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
                    className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-100 rounded transition-all"
                    title="Delete document"
                  >
                    <Trash2 size={14} className="text-red-500" />
                  </button>
                </div>
              </div>
            ))}
            {documents.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-4">
                No documents uploaded yet. Drop a PDF above to get started.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

