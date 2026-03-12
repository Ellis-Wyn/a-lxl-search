import api from './axios';

// Search API
export const searchApi = {
  unified: (params) => api.get('/api/search/unified', { params }),
  suggestions: (params) => api.get('/api/search/suggestions', { params }),
  facets: (params) => api.get('/api/search/facets', { params }),
};

// Pipeline API
export const pipelineApi = {
  search: (params) => api.get('/api/pipeline/search', { params }),
  getByCompany: (companyName, params) =>
    api.get(`/api/pipeline/company/${companyName}`, { params }),
  getByTarget: (targetId, params) =>
    api.get(`/api/pipeline/target/${targetId}`, { params }),
  getStats: (params) => api.get('/api/pipeline/statistics', { params }),
};

// Pipeline History API
export const pipelineHistoryApi = {
  getSummary: (pipelineId) => api.get(`/api/pipeline-history/${pipelineId}/summary`),
  getTimeline: (pipelineId) => api.get(`/api/pipeline-history/${pipelineId}`),
  getVelocity: (pipelineId) => api.get(`/api/pipeline-history/${pipelineId}/velocity`),
};

// Target API
export const targetApi = {
  list: (params) => api.get('/api/v1/targets', { params }),
  getDetail: (targetId) => api.get(`/api/v1/targets/${targetId}`),
  getPublications: (targetId, params) =>
    api.get(`/api/v1/targets/${targetId}/publications`, { params }),
  getPipelines: (targetId, params) =>
    api.get(`/api/v1/targets/${targetId}/pipelines`, { params }),
  getStats: () => api.get('/api/v1/targets/stats'),
};

// Publication API
export const publicationApi = {
  list: (params) => api.get('/api/v1/publications', { params }),
  getDetail: (pmid) => api.get(`/api/v1/publications/${pmid}`),
  getTargets: (pmid) => api.get(`/api/v1/publications/${pmid}/targets`),
  getStats: () => api.get('/api/v1/publications/stats'),
};

// CDE API
export const cdeApi = {
  getEvents: (params) => api.get('/api/cde/events', { params }),
  getStats: () => api.get('/api/cde/events/stats'),
  getDetail: (acceptanceNo) => api.get(`/api/cde/events/${acceptanceNo}`),
};
