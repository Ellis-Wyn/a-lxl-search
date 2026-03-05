import { useState, useEffect } from 'react';
import { pipelineApi } from '../../api';

const PHASES = ['Phase 1', 'Phase 2', 'Phase 3', 'Approved'];
const PHASE_COLORS = {
  'Phase 1': 'tag-blue',
  'Phase 2': 'tag-orange',
  'Phase 3': 'tag-red',
  'Approved': 'tag-green',
};

export default function Pipelines() {
  const [pipelines, setPipelines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [filters, setFilters] = useState({
    keyword: '',
    company: '',
    phase: '',
    moa_type: '',
  });

  // Pagination
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
  });

  useEffect(() => {
    fetchPipelines();
  }, [filters, pagination.page]);

  const fetchPipelines = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        ...filters,
        limit: pagination.limit,
        offset: (pagination.page - 1) * pagination.limit,
      };
      const response = await pipelineApi.search(params);
      setPipelines(response.items || response);
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
    setFilters({ keyword: '', company: '', phase: '', moa_type: '' });
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  return (
    <div style={{ minHeight: '100vh', paddingTop: '96px', paddingBottom: '48px', padding: '24px' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-['JetBrains_Mono'] text-4xl font-bold text-[#e0e0e0] mb-2">
            <span className="text-[#00ff88]">▧</span> Pipeline Browser
          </h1>
          <p className="font-['Source_Sans_3'] text-[#a0a0a0]">
            Explore pharmaceutical R&D pipelines across {pagination.total} entries
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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                Keyword
              </label>
              <input
                type="text"
                value={filters.keyword}
                onChange={(e) => handleFilterChange('keyword', e.target.value)}
                placeholder="Drug code, indication..."
                className="input"
              />
            </div>
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                Company
              </label>
              <input
                type="text"
                value={filters.company}
                onChange={(e) => handleFilterChange('company', e.target.value)}
                placeholder="Company name..."
                className="input"
              />
            </div>
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                Phase
              </label>
              <select
                value={filters.phase}
                onChange={(e) => handleFilterChange('phase', e.target.value)}
                className="input"
              >
                <option value="">All Phases</option>
                {PHASES.map(phase => (
                  <option key={phase} value={phase}>{phase}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                MoA Type
              </label>
              <input
                type="text"
                value={filters.moa_type}
                onChange={(e) => handleFilterChange('moa_type', e.target.value)}
                placeholder="Small Molecule, ADC..."
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
              <span className="font-['JetBrains_Mono'] text-[#a0a0a0]">Loading pipelines...</span>
            </div>
          </div>
        ) : error ? (
          <div className="bg-[#1a1a1a] border border-[#ff4444]/20 rounded-lg p-8 text-center">
            <p className="font-['Source_Sans_3'] text-[#ff4444] mb-2">Error Loading Pipelines</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">{error}</p>
          </div>
        ) : pipelines.length === 0 ? (
          <div className="text-center py-20 bg-[#141414] rounded-lg border border-[#2a2a2a]">
            <p className="font-['Source_Sans_3'] text-[#666666] text-lg mb-2">No pipelines found</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#666666]">Try adjusting your filters</p>
          </div>
        ) : (
          <>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#2a2a2a]">
                    <th className="px-4 py-3 text-left font-['JetBrains_Mono'] text-xs font-bold text-[#666666] uppercase">
                      Drug Code
                    </th>
                    <th className="px-4 py-3 text-left font-['JetBrains_Mono'] text-xs font-bold text-[#666666] uppercase">
                      Company
                    </th>
                    <th className="px-4 py-3 text-left font-['JetBrains_Mono'] text-xs font-bold text-[#666666] uppercase">
                      Indication
                    </th>
                    <th className="px-4 py-3 text-left font-['JetBrains_Mono'] text-xs font-bold text-[#666666] uppercase">
                      Phase
                    </th>
                    <th className="px-4 py-3 text-left font-['JetBrains_Mono'] text-xs font-bold text-[#666666] uppercase">
                      Modality
                    </th>
                    <th className="px-4 py-3 text-left font-['JetBrains_Mono'] text-xs font-bold text-[#666666] uppercase">
                      Last Updated
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pipelines.map((pipeline) => (
                    <tr
                      key={pipeline.pipeline_id}
                      className="border-b border-[#1a1a1a] hover:bg-[#141414]/50 transition-colors"
                    >
                      <td className="px-4 py-4">
                        <span className="font-['JetBrains_Mono'] font-semibold text-[#00ff88]">
                          {pipeline.drug_code}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-['Source_Sans_3'] text-[#e0e0e0]">
                          {pipeline.company_name}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-['Source_Sans_3'] text-[#a0a0a0] truncate max-w-xs block">
                          {pipeline.indication}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`tag ${PHASE_COLORS[pipeline.phase] || 'tag-gray'}`}>
                          {pipeline.phase}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">
                          {pipeline.modality || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-['JetBrains_Mono'] text-xs text-[#666666]">
                          {pipeline.last_seen_at
                            ? new Date(pipeline.last_seen_at).toLocaleDateString()
                            : '-'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
