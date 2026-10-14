import axios, { AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error?: { code?: string; message?: string } }>) => {
    const errorMsg =
      error.response?.data?.error?.message ||
      error.response?.statusText ||
      error.message ||
      'خطای ارتباط با سرور رخ داده است';
    console.warn(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}: ${errorMsg}`);
    return Promise.reject(error);
  }
);
