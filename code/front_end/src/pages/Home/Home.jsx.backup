import { useState, useCallback, useEffect, useRef } from 'react';
import { useSearch } from '../../context/SearchContext';
import { Link } from 'react-router-dom';

const tabs = [
  { id: 'all', label: '全部' },
  { id: 'pipelines', label: '管线' },
  { id: 'publications', label: '文献' },
  { id: 'targets', label: '靶点' },
  { id: 'cde_events', label: 'CDE' },
];

export default function Home() {
  const { state, search, fetchSuggestions, setActiveTab, clearResults } = useSearch();
  const [inputValue, setInputValue] = useState('');
  const searchTimeoutRef = useRef(null);

  const performSearch = useCallback((query) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (!query.trim()) {
      clearResults();
      return;
    }

    searchTimeoutRef.current = setTimeout(() => {
      search(query, { type: state.activeTab });
    }, 400);
  }, [search, state.activeTab, clearResults]);

  useEffect(() => {
    if (inputValue.length >= 2) {
      const timer = setTimeout(() => {
        fetchSuggestions(inputValue);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [inputValue, fetchSuggestions]);

  const handleSearch = (e) => {
    e.preventDefault();
    performSearch(inputValue);
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    if (inputValue.trim()) {
      search(inputValue, { type: tabId });
    }
  };

  const getTotalCount = () => {
    return Object.values(state.results).reduce((sum, type) => sum + (type.count || 0), 0);
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', overflow: 'hidden' }}>
      {/* Hero Section - 极致3D分层效果 */}
      <section style={{
        position: 'relative',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '120px 24px 80px',
        overflow: 'hidden'
      }}>
        {/* 第一层：图片背景 */}
        <div style={{
          position: 'absolute',
          inset: 0,
          zIndex: 1,
          backgroundImage: 'url("/images/1.jpg")',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }}></div>

        {/* 背景遮罩 - 让文字更清晰 */}
        <div style={{
          position: 'absolute',
          inset: 0,
          zIndex: 1,
          background: 'rgba(0, 0, 0, 0.2)'
        }}></div>

        {/* 第二层：LXL 巨大背景文字 - 左下角 + 纯白色 + 浮现动画 */}
        <div style={{
          position: 'absolute',
          bottom: '80px',
          left: '60px',
          zIndex: 2,
          pointerEvents: 'none',
          userSelect: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          fontFamily: 'JetBrains Mono',
          fontSize: 'clamp(150px, 20vw, 300px)',
          fontWeight: 900,
          lineHeight: 0.75,
          whiteSpace: 'nowrap',
          letterSpacing: '0',
          color: 'rgba(255, 255, 255, 0.85)'
        }}>
          <span style={{
            display: 'inline-block',
            animation: 'letterReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            opacity: 0,
            transform: 'translateY(100px)'
          }}>L</span>
          <span style={{
            display: 'inline-block',
            animation: 'letterReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.15s forwards',
            opacity: 0,
            transform: 'translateY(100px)'
          }}>X</span>
          <span style={{
            display: 'inline-block',
            animation: 'letterReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.3s forwards',
            opacity: 0,
            transform: 'translateY(100px)'
          }}>L</span>
        </div>

        {/* 第三层：装饰性图形元素 - 简洁版 */}
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 3,
          pointerEvents: 'none',
          width: '100%',
          height: '100%',
          maxWidth: '1400px'
        }}>
          {/* 简洁的圆环装饰 */}
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '600px',
            height: '600px',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '50%',
            opacity: 0.5
          }}></div>
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '800px',
            height: '800px',
            border: '1px solid rgba(255, 255, 255, 0.03)',
            borderRadius: '50%',
            opacity: 0.3
          }}></div>
        </div>

        {/* 第四层：前景内容 */}
        <div style={{
          position: 'relative',
          zIndex: 10,
          maxWidth: '800px',
          width: '100%',
          margin: '0 auto',
          textAlign: 'center'
        }}>
          {/* 搜索框 - 简洁版 */}
          <form onSubmit={handleSearch} style={{ marginBottom: '48px' }}>
            <div style={{
              position: 'relative',
              maxWidth: '640px',
              margin: '0 auto',
              animation: 'slideUp 0.8s ease-out 0.7s both'
            }}>
              {/* 搜索框主体 */}
              <div style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                background: 'rgba(20, 20, 20, 0.8)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '16px',
                padding: '8px',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
                transition: 'all 0.3s'
              }}>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="搜索靶点、管线、文献..."
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    padding: '16px 16px',
                    fontSize: '17px',
                    fontFamily: 'Source Sans 3',
                    color: '#ffffff',
                    fontWeight: 300
                  }}
                />
                <button
                  type="submit"
                  disabled={state.loading}
                  style={{
                    padding: '16px 32px',
                    background: state.loading
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(255, 255, 255, 0.9)',
                    color: '#0a0a0a',
                    border: 'none',
                    borderRadius: '12px',
                    fontSize: '14px',
                    fontFamily: 'JetBrains Mono',
                    fontWeight: 600,
                    cursor: state.loading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.3s',
                    letterSpacing: '0.05em'
                  }}
                >
                  {state.loading ? '搜索中...' : '搜索'}
                </button>
              </div>

              {/* 搜索建议 */}
              {state.suggestions.length > 0 && inputValue.length >= 2 && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 12px)',
                  left: 0,
                  right: 0,
                  background: 'rgba(20, 20, 20, 0.98)',
                  backdropFilter: 'blur(30px)',
                  border: '1px solid rgba(42, 42, 42, 0.8)',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
                  zIndex: 100
                }}>
                  {state.suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        setInputValue(suggestion.text);
                        performSearch(suggestion.text);
                      }}
                      style={{
                        width: '100%',
                        padding: '18px 28px',
                        background: 'transparent',
                        border: 'none',
                        borderBottom: index < state.suggestions.length - 1
                          ? '1px solid rgba(42, 42, 42, 0.5)'
                          : 'none',
                        cursor: 'pointer',
                        transition: 'background 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(34, 34, 34, 0.6)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      <span style={{
                        fontFamily: 'Source Sans 3',
                        fontSize: '16px',
                        color: '#e0e0e0'
                      }}>{suggestion.text}</span>
                      <span style={{
                        padding: '6px 14px',
                        fontFamily: 'JetBrains Mono',
                        fontSize: '11px',
                        background: 'rgba(0, 255, 136, 0.15)',
                        color: '#00ff88',
                        borderRadius: '6px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>{suggestion.type}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </form>

          {/* 快速统计 - 简洁版 */}
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '24px',
            flexWrap: 'wrap',
            animation: 'slideUp 0.8s ease-out 0.9s both'
          }}>
            {[
              { value: '167', label: '管线数据' },
              { value: '7', label: '靶点信息' },
              { value: '14', label: '药企覆盖' }
            ].map((stat, index) => (
              <div
                key={index}
                style={{
                  textAlign: 'center',
                  padding: '20px 32px',
                  background: 'rgba(20, 20, 20, 0.5)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '14px',
                  transition: 'all 0.3s',
                  minWidth: '160px'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                  e.currentTarget.style.background = 'rgba(30, 30, 30, 0.6)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)';
                  e.currentTarget.style.background = 'rgba(20, 20, 20, 0.5)';
                }}
              >
                <div style={{
                  fontFamily: 'JetBrains Mono',
                  fontSize: '36px',
                  fontWeight: 700,
                  color: '#ffffff',
                  marginBottom: '8px',
                  letterSpacing: '-0.02em'
                }}>
                  {stat.value}
                </div>
                <div style={{
                  fontFamily: 'JetBrains Mono',
                  fontSize: '11px',
                  color: '#888',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  fontWeight: 500
                }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Results Section */}
      {state.query && (
        <section style={{
          padding: '80px 24px',
          background: 'rgba(10, 10, 10, 0.5)',
          position: 'relative',
          zIndex: 20
        }}>
          <div style={{
            maxWidth: '1200px',
            margin: '0 auto'
          }}>
            {/* Results Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '48px',
              flexWrap: 'wrap',
              gap: '24px'
            }}>
              <div>
                <h2 style={{
                  fontFamily: 'JetBrains Mono',
                  fontSize: '32px',
                  fontWeight: 700,
                  color: '#e0e0e0',
                  marginBottom: '12px'
                }}>
                  搜索结果
                </h2>
                <p style={{
                  fontFamily: 'Source Sans 3',
                  fontSize: '16px',
                  color: '#a0a0a0'
                }}>
                  找到 <span style={{ color: '#00ff88', fontFamily: 'JetBrains Mono' }}>
                    {getTotalCount()}
                  </span> 条结果 for <span style={{ color: '#00ff88' }}>"{state.query}"</span>
                </p>
              </div>

              {/* Tabs */}
              <div style={{
                display: 'flex',
                gap: '8px',
                flexWrap: 'wrap'
              }}>
                {tabs.map((tab) => {
                  const count = state.results[tab.id === 'all' ? 'pipelines' : tab.id]?.count || 0;
                  const isActive = state.activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabChange(tab.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '12px 20px',
                        borderRadius: '12px',
                        fontFamily: 'JetBrains Mono',
                        fontSize: '14px',
                        fontWeight: 600,
                        transition: 'all 0.3s',
                        background: isActive
                          ? 'rgba(0, 255, 136, 0.1)'
                          : 'rgba(26, 26, 26, 0.8)',
                        border: isActive
                          ? '1px solid rgba(0, 255, 136, 0.3)'
                          : '1px solid rgba(42, 42, 42, 0.8)',
                        color: isActive ? '#00ff88' : '#a0a0a0',
                        cursor: 'pointer',
                        backdropFilter: 'blur(8px)'
                      }}
                    >
                      <span>{tab.label}</span>
                      {count > 0 && (
                        <span style={{
                          padding: '4px 10px',
                          background: 'rgba(0, 255, 136, 0.2)',
                          color: '#00ff88',
                          borderRadius: '6px',
                          fontSize: '12px'
                        }}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Loading State */}
            {state.loading && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '80px 0'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px'
                }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    border: '3px solid rgba(0, 255, 136, 0.2)',
                    borderTopColor: '#00ff88',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                  <span style={{
                    fontFamily: 'JetBrains Mono',
                    color: '#a0a0a0'
                  }}>搜索数据库中...</span>
                </div>
              </div>
            )}

            {/* Error State */}
            {state.error && (
              <div style={{
                background: 'rgba(26, 26, 26, 0.8)',
                border: '1px solid rgba(255, 68, 68, 0.2)',
                borderRadius: '16px',
                padding: '48px',
                textAlign: 'center'
              }}>
                <p style={{
                  fontFamily: 'Source Sans 3',
                  color: '#ff4444',
                  fontSize: '18px',
                  marginBottom: '8px'
                }}>搜索出错</p>
                <p style={{
                  fontFamily: 'JetBrains Mono',
                  fontSize: '14px',
                  color: '#a0a0a0'
                }}>{state.error}</p>
              </div>
            )}

            {/* Results Display */}
            {!state.loading && !state.error && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '48px' }}>
                {/* Pipeline Results */}
                {(state.activeTab === 'all' || state.activeTab === 'pipelines') && (
                  <div>
                    <h3 style={{
                      fontFamily: 'JetBrains Mono',
                      fontSize: '20px',
                      fontWeight: 700,
                      color: '#e0e0e0',
                      marginBottom: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px'
                    }}>
                      管线
                      <span style={{
                        padding: '4px 12px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: '#a0a0a0',
                        borderRadius: '6px',
                        fontSize: '14px'
                      }}>{state.results.pipelines.count}</span>
                    </h3>
                    {state.results.pipelines.items.length > 0 ? (
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                        gap: '24px'
                      }}>
                        {state.results.pipelines.items.map((pipeline) => (
                          <Link
                            key={pipeline.pipeline_id}
                            to="/pipelines"
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
                            <div style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              justifyContent: 'space-between',
                              marginBottom: '16px'
                            }}>
                              <h4 style={{
                                fontFamily: 'JetBrains Mono',
                                fontWeight: 700,
                                fontSize: '18px',
                                color: '#00ff88'
                              }}>
                                {pipeline.drug_code}
                              </h4>
                              <span style={{
                                padding: '6px 14px',
                                fontFamily: 'JetBrains Mono',
                                fontSize: '11px',
                                fontWeight: 600,
                                borderRadius: '8px',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                background: 'rgba(0, 255, 136, 0.1)',
                                color: '#00ff88'
                              }}>
                                {pipeline.phase}
                              </span>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: '#666' }}>公司:</span>
                                <span style={{ color: '#e0e0e0', fontWeight: 500 }}>{pipeline.company_name}</span>
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: '#666' }}>适应症:</span>
                                <span style={{ color: '#e0e0e0', fontWeight: 500, maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={pipeline.indication}>
                                  {pipeline.indication}
                                </span>
                              </div>
                              {pipeline.modality && (
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                  <span style={{ color: '#666' }}>类型:</span>
                                  <span style={{ color: '#e0e0e0' }}>{pipeline.modality}</span>
                                </div>
                              )}
                            </div>
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <div style={{
                        textAlign: 'center',
                        padding: '64px 24px',
                        background: 'rgba(20, 20, 20, 0.5)',
                        borderRadius: '16px',
                        border: '1px solid rgba(42, 42, 42, 0.8)'
                      }}>
                        <p style={{ fontFamily: 'Source Sans 3', color: '#666', fontSize: '16px' }}>
                          未找到管线结果
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Publication Results */}
                {(state.activeTab === 'all' || state.activeTab === 'publications') && (
                  <div>
                    <h3 style={{
                      fontFamily: 'JetBrains Mono',
                      fontSize: '20px',
                      fontWeight: 700,
                      color: '#e0e0e0',
                      marginBottom: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px'
                    }}>
                      文献
                      <span style={{
                        padding: '4px 12px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: '#a0a0a0',
                        borderRadius: '6px',
                        fontSize: '14px'
                      }}>{state.results.publications.count}</span>
                    </h3>
                    {state.results.publications.items.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        {state.results.publications.items.slice(0, 5).map((pub) => (
                          <div
                            key={pub.pmid}
                            style={{
                              background: 'rgba(26, 26, 26, 0.6)',
                              backdropFilter: 'blur(8px)',
                              border: '1px solid rgba(42, 42, 42, 0.8)',
                              borderRadius: '16px',
                              padding: '24px',
                              transition: 'all 0.3s'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px' }}>
                              <div style={{ flex: 1 }}>
                                <a
                                  href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    fontFamily: 'Source Sans 3',
                                    fontWeight: 600,
                                    fontSize: '18px',
                                    color: '#00ff88',
                                    textDecoration: 'none',
                                    display: 'block',
                                    marginBottom: '12px',
                                    lineHeight: 1.4
                                  }}
                                >
                                  {pub.title}
                                </a>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '12px',
                                  marginBottom: '12px',
                                  fontSize: '13px',
                                  fontFamily: 'JetBrains Mono',
                                  color: '#666'
                                }}>
                                  <span>{pub.journal}</span>
                                  <span>•</span>
                                  <span>{pub.pub_date ? new Date(pub.pub_date).getFullYear() : 'N/A'}</span>
                                </div>
                                {pub.abstract && (
                                  <p style={{
                                    fontFamily: 'Source Sans 3',
                                    fontSize: '14px',
                                    color: '#a0a0a0',
                                    lineHeight: 1.6,
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden',
                                    marginBottom: '16px'
                                  }}>
                                    {pub.abstract}
                                  </p>
                                )}
                                {pub.clinical_data_tags && pub.clinical_data_tags.length > 0 && (
                                  <div style={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: '8px'
                                  }}>
                                    {pub.clinical_data_tags.slice(0, 5).map((tag, i) => (
                                      <span key={i} style={{
                                        padding: '4px 12px',
                                        fontFamily: 'JetBrains Mono',
                                        fontSize: '11px',
                                        fontWeight: 600,
                                        borderRadius: '6px',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.05em',
                                        background: 'rgba(0, 212, 255, 0.1)',
                                        color: '#00d4ff'
                                      }}>
                                        {tag}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{
                        textAlign: 'center',
                        padding: '64px 24px',
                        background: 'rgba(20, 20, 20, 0.5)',
                        borderRadius: '16px',
                        border: '1px solid rgba(42, 42, 42, 0.8)'
                      }}>
                        <p style={{ fontFamily: 'Source Sans 3', color: '#666', fontSize: '16px' }}>
                          未找到文献结果
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Target Results */}
                {(state.activeTab === 'all' || state.activeTab === 'targets') && (
                  <div>
                    <h3 style={{
                      fontFamily: 'JetBrains Mono',
                      fontSize: '20px',
                      fontWeight: 700,
                      color: '#e0e0e0',
                      marginBottom: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px'
                    }}>
                      靶点
                      <span style={{
                        padding: '4px 12px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: '#a0a0a0',
                        borderRadius: '6px',
                        fontSize: '14px'
                      }}>{state.results.targets.count}</span>
                    </h3>
                    {state.results.targets.items.length > 0 ? (
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                        gap: '24px'
                      }}>
                        {state.results.targets.items.map((target) => (
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
                    ) : (
                      <div style={{
                        textAlign: 'center',
                        padding: '64px 24px',
                        background: 'rgba(20, 20, 20, 0.5)',
                        borderRadius: '16px',
                        border: '1px solid rgba(42, 42, 42, 0.8)'
                      }}>
                        <p style={{ fontFamily: 'Source Sans 3', color: '#666', fontSize: '16px' }}>
                          未找到靶点结果
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
