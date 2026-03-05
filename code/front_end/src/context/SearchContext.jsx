import { createContext, useContext, useReducer, useCallback } from 'react';
import { searchApi } from '../api';

const SearchContext = createContext();

const initialState = {
  query: '',
  results: {
    pipelines: { count: 0, items: [] },
    publications: { count: 0, items: [] },
    targets: { count: 0, items: [] },
    cde_events: { count: 0, items: [] }
  },
  facets: {
    companies: {},
    phases: {},
    moa_types: {},
    journals: {}
  },
  loading: false,
  error: null,
  activeTab: 'all',
  suggestions: []
};

function searchReducer(state, action) {
  switch (action.type) {
    case 'SET_QUERY':
      return { ...state, query: action.payload };
    case 'SET_RESULTS':
      return { ...state, results: action.payload };
    case 'SET_FACETS':
      return { ...state, facets: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_SUGGESTIONS':
      return { ...state, suggestions: action.payload };
    default:
      return state;
  }
}

export function SearchProvider({ children }) {
  const [state, dispatch] = useReducer(searchReducer, initialState);

  const search = useCallback(async (query, filters = {}) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });
      dispatch({ type: 'SET_QUERY', payload: query });

      const results = await searchApi.unified({
        q: query,
        type: filters.type || 'all',
        ...filters
      });

      dispatch({ type: 'SET_RESULTS', payload: results.results });
      if (results.facets) {
        dispatch({ type: 'SET_FACETS', payload: results.facets });
      }
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const fetchSuggestions = useCallback(async (query) => {
    if (query.length < 2) {
      dispatch({ type: 'SET_SUGGESTIONS', payload: [] });
      return;
    }

    try {
      const suggestions = await searchApi.suggestions({ q: query, limit: 10 });
      dispatch({ type: 'SET_SUGGESTIONS', payload: suggestions });
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
    }
  }, []);

  const setActiveTab = useCallback((tab) => {
    dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
  }, []);

  const clearResults = useCallback(() => {
    dispatch({ type: 'SET_RESULTS', payload: initialState.results });
    dispatch({ type: 'SET_QUERY', payload: '' });
    dispatch({ type: 'SET_FACETS', payload: initialState.facets });
  }, []);

  return (
    <SearchContext.Provider
      value={{
        state,
        search,
        fetchSuggestions,
        setActiveTab,
        clearResults
      }}
    >
      {children}
    </SearchContext.Provider>
  );
}

export const useSearch = () => {
  const context = useContext(SearchContext);
  if (!context) {
    throw new Error('useSearch must be used within SearchProvider');
  }
  return context;
};
