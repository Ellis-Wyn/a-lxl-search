import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { targetApi } from '../../api';

export default function Targets() {
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [filters, setFilters] = useState({
    keyword: '',
  });

  // Pagination
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
  });

  useEffect(() => {
    fetchTargets();
  }, [filters, pagination.page]);

  const fetchTargets = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        ...filters,
        limit: pagination.limit,
        offset: (pagination.page - 1) * pagination.limit,
      };
      const response = await targetApi.list(params);
      setTargets(response.items || response);
      setPagination(prev => ({ ...prev, total: response.total || response.length || 0 }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleReset = () => {
    setFilters({ keyword: '' });
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  return (
    <div style={{ minHeight: '100vh', paddingTop: '96px', paddingBottom: '48px', padding: '24px' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-['JetBrains_Mono'] text-4xl font-bold text-[#e0e0e0] mb-2">
            靶点库
          </h1>
          <p className="font-['Source_Sans_3'] text-[#a0a0a0]">
            Explore {pagination.total} targets in the database
          </p>
        </div>

        {/* Filters */}
        <div className="card mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-['JetBrains_Mono'] font-bold text-[#e0e0e0]">Filters</h3>
            <button
              onClick={handleReset}
              className="font-['JetBrains_Mono'] text-sm text-[#00ff88] hover:text-[#33ffaa] transition-colors"
            >
              Reset All
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                Keyword
              </label>
              <input
                type="text"
                value={filters.keyword}
                onChange={(e) => handleFilterChange('keyword', e.target.value)}
                placeholder="Target name, gene ID..."
                className="input"
              />
            </div>
          </div>
        </div>

        {/* Results */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 border-2 border-[#00ff88] border-t-transparent rounded-full animate-spin"></div>
              <span className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">Loading targets...</span>
            </div>
          </div>
        ) : error ? (
          <div className="bg-[#1a1a1a] border border-[#ff4444]/20 rounded-lg p-8 text-center">
            <p className="font-['Source_Sans_3'] text-[#ff4444] mb-2">Error Loading Targets</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">{error}</p>
          </div>
        ) : targets.length === 0 ? (
          <div className="text-center py-20 bg-[#141414] rounded-lg border border-[#2a2a2a]">
            <p className="font-['Source_Sans_3'] text-[#666666] text-lg mb-2">No targets found</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#666666]">Try adjusting your filters</p>
          </div>
        ) : (
          <>
            {/* Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: '24px'
            }}>
              {targets.map((target) => (
                <Link
                  key={target.target_id}
                  to={`/targets/${target.target_id}`}
                  style={{
                    background: 'rgba(26, 26, 26, 0.6)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(42, 42, 42, 0.8)',
                    borderRadius: '16px',
                    padding: '24px',
                    transition: 'all 0.3s',
                    cursor: 'pointer',
                    textDecoration: 'none',
                    display: 'block'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(0, 255, 136, 0.5)';
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 8px 32px rgba(0, 255, 136, 0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(42, 42, 42, 0.8)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <h4 style={{
                    fontFamily: 'JetBrains Mono',
                    fontWeight: 700,
                    fontSize: '18px',
                    color: '#00ff88',
                    marginBottom: '12px'
                  }}>
                    {target.standard_name}
                  </h4>
                  {target.aliases && target.aliases.length > 0 && (
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '8px',
                      marginBottom: '16px'
                    }}>
                      {target.aliases.slice(0, 3).map((alias, i) => (
                        <span key={i} style={{
                          padding: '4px 12px',
                          fontFamily: 'JetBrains Mono',
                          fontSize: '11px',
                          fontWeight: 600,
                          borderRadius: '6px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          background: 'rgba(255, 255, 255, 0.05)',
                          color: '#a0a0a0'
                        }}>
                          {alias}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '14px' }}>
                    {target.gene_id && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: '#666' }}>Gene:</span>
                        <span style={{
                          color: '#e0e0e0',
                          fontFamily: 'JetBrains Mono',
                          fontWeight: 500
                        }}>{target.gene_id}</span>
                      </div>
                    )}
                    {target.uniprot_id && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: '#666' }}>UniProt:</span>
                        <span style={{
                          color: '#e0e0e0',
                          fontFamily: 'JetBrains Mono',
                          fontWeight: 500
                        }}>{target.uniprot_id}</span>
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            {pagination.total > pagination.limit && (
              <div className="flex items-center justify-between mt-6">
                <p className="font-['JetBrains_Mono'] text-sm text-[#666666]">
                  Showing {(pagination.page - 1) * pagination.limit + 1} to{' '}
                  {Math.min(pagination.page * pagination.limit, pagination.total)} of {pagination.total}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                    disabled={pagination.page === 1}
                    className="px-4 py-2 font-['JetBrains_Mono'] text-sm rounded border border-[#2a2a2a] text-[#e0e0e0] hover:border-[#00ff88] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 font-['JetBrains_Mono'] text-sm text-[#00ff88]">
                    {pagination.page}
                  </span>
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                    disabled={pagination.page * pagination.limit >= pagination.total}
                    className="px-4 py-2 font-['JetBrains_Mono'] text-sm rounded border border-[#2a2a2a] text-[#e0e0e0] hover:border-[#00ff88] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
