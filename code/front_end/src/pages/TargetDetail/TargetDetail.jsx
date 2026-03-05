import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { targetApi } from '../../api';

const PHASE_COLORS = {
  'Phase 1': 'tag-blue',
  'Phase 2': 'tag-orange',
  'Phase 3': 'tag-red',
  'Approved': 'tag-green',
};

export default function TargetDetail() {
  const { targetId } = useParams();
  const [target, setTarget] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [publications, setPublications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTargetData();
  }, [targetId]);

  const fetchTargetData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [targetData, pipelinesData, publicationsData] = await Promise.all([
        targetApi.getDetail(targetId),
        targetApi.getPipelines(targetId, { limit: 50 }),
        targetApi.getPublications(targetId, { limit: 20 }),
      ]);

      setTarget(targetData);
      setPipelines(pipelinesData.items || pipelinesData || []);
      setPublications(publicationsData.items || publicationsData || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen py-12 px-6">
        <div className="container mx-auto max-w-6xl">
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 border-2 border-[#00ff88] border-t-transparent rounded-full animate-spin"></div>
              <span className="font-['JetBrains_Mono'] text-[#a0a0a0]">Loading target data...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen py-12 px-6">
        <div className="container mx-auto max-w-6xl">
          <div className="bg-[#1a1a1a] border border-[#ff4444]/20 rounded-lg p-8 text-center">
            <p className="font-['Source_Sans_3'] text-[#ff4444] mb-2">Error Loading Target</p>
            <p className="font-['JetBrains_Mono'] text-sm text-[#a0a0a0]">{error}</p>
            <Link
              to="/"
              className="inline-block mt-4 px-4 py-2 bg-[#00ff88] text-[#0a0a0a] font-['JetBrains_Mono'] text-sm font-bold rounded hover:bg-[#33ffaa] transition-colors"
            >
              Back to Search
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!target) {
    return (
      <div className="min-h-screen py-12 px-6">
        <div className="container mx-auto max-w-6xl">
          <div className="text-center py-20 bg-[#141414] rounded-lg border border-[#2a2a2a]">
            <p className="font-['Source_Sans_3'] text-[#666666] text-lg mb-4">Target not found</p>
            <Link
              to="/"
              className="inline-block px-4 py-2 bg-[#00ff88] text-[#0a0a0a] font-['JetBrains_Mono'] text-sm font-bold rounded hover:bg-[#33ffaa] transition-colors"
            >
              Back to Search
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-12 px-6">
      <div className="container mx-auto max-w-6xl">
        {/* Back Button */}
        <Link
          to="/"
          className="inline-flex items-center gap-2 font-['JetBrains_Mono'] text-sm text-[#00ff88] hover:text-[#33ffaa] transition-colors mb-8"
        >
          <span>←</span>
          <span>Back to Search</span>
        </Link>

        {/* Target Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="font-['JetBrains_Mono'] text-4xl font-bold text-[#e0e0e0] mb-2">
                <span className="text-[#00ff88]">◈</span> {target.standard_name}
              </h1>
              {target.aliases && target.aliases.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {target.aliases.map((alias, i) => (
                    <span key={i} className="tag tag-gray">{alias}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 max-w-lg">
            <div className="card text-center">
              <div className="font-['JetBrains_Mono'] text-2xl font-bold text-[#00ff88]">
                {pipelines.length}
              </div>
              <div className="text-xs text-[#666666] font-['JetBrains_Mono'] uppercase mt-1">
                Pipelines
              </div>
            </div>
            <div className="card text-center">
              <div className="font-['JetBrains_Mono'] text-2xl font-bold text-[#00ff88]">
                {publications.length}
              </div>
              <div className="text-xs text-[#666666] font-['JetBrains_Mono'] uppercase mt-1">
                Publications
              </div>
            </div>
            <div className="card text-center">
              <div className="font-['JetBrains_Mono'] text-2xl font-bold text-[#00ff88]">
                {target.category || '-'}
              </div>
              <div className="text-xs text-[#666666] font-['JetBrains_Mono'] uppercase mt-1">
                Category
              </div>
            </div>
          </div>
        </div>

        {/* Target Info Card */}
        <div className="card mb-8">
          <h3 className="font-['JetBrains_Mono'] font-bold text-[#e0e0e0] mb-4">Target Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {target.gene_id && (
              <div className="flex items-center gap-3 p-3 bg-[#141414] rounded border border-[#2a2a2a]">
                <span className="font-['JetBrains_Mono'] text-xs text-[#666666] uppercase w-20">
                  Gene ID
                </span>
                <span className="font-['JetBrains_Mono'] text-[#00ff88]">{target.gene_id}</span>
              </div>
            )}
            {target.uniprot_id && (
              <div className="flex items-center gap-3 p-3 bg-[#141414] rounded border border-[#2a2a2a]">
                <span className="font-['JetBrains_Mono'] text-xs text-[#666666] uppercase w-20">
                  UniProt
                </span>
                <a
                  href={`https://www.uniprot.org/uniprot/${target.uniprot_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-['JetBrains_Mono'] text-[#00ff88] hover:text-[#33ffaa] transition-colors"
                >
                  {target.uniprot_id}
                </a>
              </div>
            )}
            {target.description && (
              <div className="md:col-span-2">
                <p className="font-['Source_Sans_3'] text-sm text-[#a0a0a0]">
                  {target.description}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Related Pipelines */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-['JetBrains_Mono'] text-xl font-bold text-[#e0e0e0] flex items-center gap-2">
              <span className="text-[#00ff88]">▧</span> Related Pipelines
              <span className="tag tag-gray">{pipelines.length}</span>
            </h3>
            <Link
              to="/pipelines"
              className="font-['JetBrains_Mono'] text-sm text-[#00ff88] hover:text-[#33ffaa] transition-colors"
            >
              View All →
            </Link>
          </div>

          {pipelines.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pipelines.map((pipeline) => (
                <div key={pipeline.pipeline_id} className="card hover:border-[#00ff88]/50 transition-all duration-200">
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-['JetBrains_Mono'] font-bold text-[#00ff88]">
                      {pipeline.drug_code}
                    </h4>
                    <span className={`tag ${PHASE_COLORS[pipeline.phase] || 'tag-gray'}`}>
                      {pipeline.phase}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Company:</span>
                      <span className="text-[#e0e0e0] font-medium">{pipeline.company_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Indication:</span>
                      <span className="text-[#e0e0e0] truncate ml-2 max-w-xs" title={pipeline.indication}>
                        {pipeline.indication}
                      </span>
                    </div>
                    {pipeline.modality && (
                      <div className="flex justify-between">
                        <span className="text-[#666666]">Modality:</span>
                        <span className="text-[#e0e0e0]">{pipeline.modality}</span>
                      </div>
                    )}
                  </div>
                  {pipeline.source_url && (
                    <a
                      href={pipeline.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-3 font-['JetBrains_Mono'] text-xs text-[#666666] hover:text-[#00ff88] transition-colors"
                    >
                      Source →
                    </a>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-[#141414] rounded-lg border border-[#2a2a2a]">
              <p className="font-['Source_Sans_3'] text-[#666666]">No pipelines found for this target</p>
            </div>
          )}
        </div>

        {/* Related Publications */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-['JetBrains_Mono'] text-xl font-bold text-[#e0e0e0] flex items-center gap-2">
              <span className="text-[#00ff88]">◉</span> Related Publications
              <span className="tag tag-gray">{publications.length}</span>
            </h3>
            <Link
              to="/publications"
              className="font-['JetBrains_Mono'] text-sm text-[#00ff88] hover:text-[#33ffaa] transition-colors"
            >
              View All →
            </Link>
          </div>

          {publications.length > 0 ? (
            <div className="space-y-4">
              {publications.map((pub) => (
                <div key={pub.pmid} className="card hover:border-[#00ff88]/50 transition-all duration-200">
                  <div className="flex items-start gap-4">
                    <div className="flex-1">
                      <a
                        href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-['Source_Sans_3'] font-semibold text-[#00ff88] hover:text-[#33ffaa] transition-colors mb-2 block"
                      >
                        {pub.title}
                      </a>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-['JetBrains_Mono'] text-xs text-[#666666]">
                          {pub.journal}
                        </span>
                        <span className="text-[#2a2a2a]">•</span>
                        <span className="font-['JetBrains_Mono'] text-xs text-[#666666]">
                          {pub.pub_date ? new Date(pub.pub_date).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                      {pub.abstract && (
                        <p className="font-['Source_Sans_3'] text-sm text-[#a0a0a0] line-clamp-3">
                          {pub.abstract}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-[#141414] rounded-lg border border-[#2a2a2a]">
              <p className="font-['Source_Sans_3'] text-[#666666]">No publications found for this target</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
