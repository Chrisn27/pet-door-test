import axios from 'axios';
import type { Detection, SystemStatus, Config } from './types';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export const getStatus = async (): Promise<SystemStatus> => {
  const response = await api.get<SystemStatus>('/status');
  return response.data;
};

export const getDetections = async (
  category: 'all' | 'cats' | 'dogs' | 'unknown' = 'all',
  limit: number = 100
): Promise<{ detections: Detection[]; total: number }> => {
  const response = await api.get('/detections', {
    params: { category, limit },
  });
  return response.data;
};

export const toggleDetection = async (): Promise<{ active: boolean; message: string }> => {
  const response = await api.post('/toggle');
  return response.data;
};

export const getConfig = async (): Promise<Config> => {
  const response = await api.get<Config>('/config');
  return response.data;
};

export const updateConfig = async (config: Partial<Config>): Promise<{ success: boolean }> => {
  const response = await api.post('/config', config);
  return response.data;
};

export const deleteDetection = async (category: string, imageId: string): Promise<void> => {
  await api.delete(`/delete/${category}/${imageId}`);
};
