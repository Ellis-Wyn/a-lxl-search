import axios from 'axios';

// ==============================================
// API配置 - 根据环境自动切换
// ==============================================
// 开发环境: http://localhost:8000 (直连后端)
// 生产环境: /api (Vercel Serverless 代理，转发到后端)
//
// Vercel 代理会将 /api/* 转发到: http://119.45.167.80:8000/api/*
// ==============================================
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
                    (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '/api');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    config.params = {
      ...config.params,
      _t: Date.now()
    };
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      console.error('API Error:', error.response.data);
    } else if (error.request) {
      console.error('Network Error:', error.message);
    } else {
      console.error('Request Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;
