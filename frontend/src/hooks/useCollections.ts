import { useState, useEffect, useCallback } from 'react';
import type { Collection } from '../types';
import * as api from '../services/api';

export function useCollections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeCollection, setActiveCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCollections = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getCollections();
      setCollections(data);
      // Auto-select first collection if none selected
      if (!activeCollection && data.length > 0) {
        setActiveCollection(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load collections');
    } finally {
      setLoading(false);
    }
  }, []);

  const createCollection = useCallback(async (name: string, description: string = '') => {
    try {
      const newCollection = await api.createCollection(name, description);
      setCollections((prev) => [newCollection, ...prev]);
      setActiveCollection(newCollection);
      return newCollection;
    } catch (err: any) {
      setError(err.message || 'Failed to create collection');
      throw err;
    }
  }, []);

  const removeCollection = useCallback(async (id: number) => {
    try {
      await api.deleteCollection(id);
      setCollections((prev) => prev.filter((c) => c.id !== id));
      if (activeCollection?.id === id) {
        setActiveCollection(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete collection');
    }
  }, [activeCollection]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  return {
    collections,
    activeCollection,
    setActiveCollection,
    createCollection,
    removeCollection,
    refreshCollections: fetchCollections,
    loading,
    error,
  };
}

