import { useState, useCallback } from 'react';
import type { Document } from '../types';
import * as api from '../services/api';

export function useDocuments(collectionId: number | null) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    if (!collectionId) return;
    try {
      const data = await api.getDocuments(collectionId);
      setDocuments(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    }
  }, [collectionId]);

  const uploadDocument = useCallback(async (file: File) => {
    if (!collectionId) return;
    try {
      setUploading(true);
      setUploadProgress(`Uploading ${file.name}...`);
      setError(null);
      const doc = await api.uploadDocument(collectionId, file);
      setDocuments((prev) => [doc, ...prev]);
      setUploadProgress(null);
      return doc;
    } catch (err: any) {
      const message = err.response?.data?.error || err.message || 'Upload failed';
      setError(message);
      setUploadProgress(null);
      throw err;
    } finally {
      setUploading(false);
    }
  }, [collectionId]);

  const removeDocument = useCallback(async (documentId: number) => {
    try {
      await api.deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } catch (err: any) {
      setError(err.message || 'Failed to delete document');
    }
  }, []);

  return {
    documents,
    uploading,
    uploadProgress,
    error,
    fetchDocuments,
    uploadDocument,
    removeDocument,
  };
}

