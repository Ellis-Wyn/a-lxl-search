import { useState, useEffect, useRef } from 'react';
import { publicationApi } from '../../api';

export default function Publications() {
  const [publications, setPublications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  // Filters
  const [filters, setFilters] = useState({
    keyword: '',
    journal: '',
    date_from: '',
    date_to: '',
  });

  const observerTarget = useRef(null);

  useEffect(() => {
    fetchPublications(true);
  }, [filters]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          fetchPublications(false);
        }
      },
      { threshold: 0.1 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loading]);

  const fetchPublications = async (reset = false) => {
    try {
      if (reset) {
        setLoading(true);
        setError(null);
      }
      const params = {
        ...filters,
        limit: 20,
        offset: reset ? 0 : publications.length,
      };
      const response = await publicationApi.list(params);
      const newItems = response.items || response;

      if (reset) {
        setPublications(newItems);
      } else {
        setPublications(prev => [...prev, ...newItems]);
      }

      setHasMore(newItems.length >= 20);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleReset = () => {
    setFilters({ keyword: '', journal: '', date_from: '', date_to: '' });
  };

  return (
    <div style={{ minHeight: '100vh', paddingTop: '96px', paddingBottom: '48px', padding: '24px' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-['JetBrains_Mono'] text-4xl font-bold text-[#e0e0e0] mb-2">
            <span className="text-[#00ff88]">◉</span> Publication Stream
          </h1>
          <p className="font-['Source_Sans_3'] text-[#a0a0a0]">
            Clinical trial publications and research literature
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
                placeholder="Search titles, abstracts..."
                className="input"
              />
            </div>
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                Journal
              </label>
              <input
                type="text"
                value={filters.journal}
                onChange={(e) => handleFilterChange('journal', e.target.value)}
                placeholder="Journal name..."
                className="input"
              />
            </div>
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                From Date
              </label>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => handleFilterChange('date_from', e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="block font-['JetBrains_Mono'] text-xs text-[#666666] uppercase mb-2">
                To Date
              </label>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => handleFilterChange('date_to', e.target.value)}
                className="input"
              />
            </div>
          </div>
        </div>

        {/* Publications */}
        {error && (
          <div className="bg-[#1a1a1a] border border-[#ff4444]/20 rounded-lg p-8 text-center mb-8">
            <p className="font-['Source_Sans_3'] text-[#ff4444] mb-2">Error Loading Publications</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">{error}</p>
          </div>
        )}

        {publications.length === 0 && !loading && !error && (
          <div className="text-center py-20 bg-[#141414] rounded-lg border border-[#2a2a2a]">
            <p className="font-['Source_Sans_3'] text-[#666666] text-lg mb-2">No publications found</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#666666]">Try adjusting your filters</p>
          </div>
        )}

        <div className="space-y-6">
          {publications.map((pub, index) => (
            <div
              key={`${pub.pmid}-${index}`}
              className="card hover:border-[#00ff88]/50 transition-all duration-200"
            >
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  {/* Title */}
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-['Source_Sans_3'] font-semibold text-lg text-[#00ff88] hover:text-[#33ffaa] transition-colors mb-2 block"
                  >
                    {pub.title}
                  </a>

                  {/* Meta */}
                  <div className="flex flex-wrap items-center gap-3 mb-3">
                    <span className="font-['JetBrains_Mono'] text-xs text-[#666666]">
                      {pub.journal}
                    </span>
                    <span className="text-[#2a2a2a]">•</span>
                    <span className="font-['JetBrains_Mono'] text-xs text-[#666666]">
                      {pub.pub_date ? new Date(pub.pub_date).toLocaleDateString() : 'N/A'}
                    </span>
                    <span className="text-[#2a2a2a]">•</span>
                    <a
                      href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-['JetBrains_Mono'] text-xs text-[#00ff88] hover:text-[#33ffaa] transition-colors"
                    >
                      PMID: {pub.pmid}
                    </a>
                  </div>

                  {/* Abstract */}
                  {pub.abstract && (
                    <p className="font-['Source_Sans_3'] text-sm text-[#a0a0a0] mb-4 line-clamp-4">
                      {pub.abstract}
                    </p>
                  )}

                  {/* Tags */}
                  <div className="flex flex-wrap gap-2">
                    {pub.clinical_data_tags && pub.clinical_data_tags.length > 0 && (
                      <>
                        {pub.clinical_data_tags.slice(0, 5).map((tag, i) => (
                          <span key={i} className="tag tag-blue">{tag}</span>
                        ))}
                      </>
                    )}
                    {pub.mesh_terms && pub.mesh_terms.length > 0 && (
                      <>
                        {pub.mesh_terms.slice(0, 3).map((term, i) => (
                          <span key={i} className="tag tag-gray">{term}</span>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Loading More */}
        <div ref={observerTarget} className="py-8">
          {loading && publications.length > 0 && (
            <div className="flex items-center justify-center">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 border-2 border-[#00ff88] border-t-transparent rounded-full animate-spin"></div>
                <span className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">Loading more...</span>
              </div>
            </div>
          )}
        </div>

        {!hasMore && publications.length > 0 && (
          <div className="text-center py-8">
            <p className="font-['JetBrains_Mono'] text-sm text-[#666666]">
              End of results
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
