// Frontend/src/hooks/useApi.ts
import { useState, useEffect, useCallback } from 'react';

interface UseApiOptions<T> {
  immediate?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: string) => void;
}

export function useApi<T>(
  apiCall: () => Promise<T>, // Changed this line: Expects a Promise that resolves directly to type T
  options: UseApiOptions<T> = {}
) {
  const { immediate = true, onSuccess, onError } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // The apiCall function is now expected to return the direct data (T)
      // and handle the FlaskResponse unwrapping internally, as implemented in serverService.ts
      const resultData = await apiCall();

      setData(resultData);
      onSuccess?.(resultData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiCall, onSuccess, onError]);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate]);

  const refetch = useCallback(() => {
    execute();
  }, [execute]);

  return {
    data,
    loading,
    error,
    execute,
    refetch,
  };
}

export function useMutation<T, P = any>(
  apiCall: (params: P) => Promise<T>, // Changed this line: Expects a Promise that resolves directly to type T
  options: UseApiOptions<T> = {}
) {
  const { onSuccess, onError } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(async (params: P) => {
    try {
      setLoading(true);
      setError(null);

      // The apiCall function is now expected to return the direct data (T)
      // and handle the FlaskResponse unwrapping internally.
      const resultData = await apiCall(params);

      setData(resultData);
      onSuccess?.(resultData);
      return resultData;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      onError?.(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, onSuccess, onError]);

  return {
    data,
    loading,
    error,
    mutate,
  };
}
