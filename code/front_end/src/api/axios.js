import axios from 'axios';

// ==============================================
// API配置 - 根据环境自动切换
// ==============================================
// 开发环境: http://localhost:8000
// 生产环境: https://api.your-domain.com
//
// 修改方法：
// 1. 直接修改下面的 API_BASE_URL
// 2. 或在构建时设置环境变量: VITE_API_BASE_URL=https://api.your-domain.com
// ==============================================
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
                    (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://api.your-domain.com');

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
