import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';

const navItems = [
  { path: '/', label: '搜索' },
  { path: '/pipelines', label: '管线' },
  { path: '/publications', label: '文献' },
  { path: '/targets', label: '靶点' },
];

export default function Header() {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md" style={{
      background: 'rgba(10, 10, 10, 0.8)',
      borderBottom: '1px solid rgba(42, 42, 42, 0.8)'
    }}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16 relative">
          {/* Logo - 左侧 */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300"
                   style={{
                     background: 'linear-gradient(135deg, #00ff88 0%, #00cc6a 100%)',
                     boxShadow: '0 0 20px rgba(0, 255, 136, 0.3)'
                   }}>
                <span className="text-black font-bold text-xl" style={{ fontFamily: 'JetBrains Mono' }}>罗</span>
              </div>
              <div className="absolute -inset-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                   style={{
                     background: 'linear-gradient(135deg, #00ff88 0%, #00cc6a 100%)',
                     filter: 'blur(8px)',
                     zIndex: -1
                   }}>
              </div>
            </div>
            <div>
              <h1 className="font-bold text-lg" style={{
                fontFamily: 'JetBrains Mono',
                background: 'linear-gradient(135deg, #00ff88 0%, #00ff88 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                letterSpacing: '-0.02em'
              }}>
                罗小罗
              </h1>
              <p style={{
                fontSize: '10px',
                color: '#666',
                fontFamily: 'JetBrains Mono',
                letterSpacing: '0.1em',
                textTransform: 'uppercase'
              }}>
                药研情报库
              </p>
            </div>
          </Link>

          {/* Desktop Navigation - 居中 */}
          <nav className="hidden md:flex absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 items-center gap-8">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className="relative flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200"
                  style={{
                    fontFamily: 'JetBrains Mono',
                    fontSize: '14px',
                    color: isActive ? '#00ff88' : '#a0a0a0',
                    background: isActive ? 'rgba(0, 255, 136, 0.1)' : 'transparent'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.color = '#e0e0e0';
                      e.currentTarget.style.background = 'rgba(34, 34, 34, 0.5)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.color = '#a0a0a0';
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  <span>{item.label}</span>
                  {isActive && (
                    <span className="ml-1 w-1.5 h-1.5 rounded-full animate-pulse"
                          style={{ background: '#00ff88', boxShadow: '0 0 8px #00ff88' }}></span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Status Indicator */}
          <div className="hidden lg:flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
                 style={{
                   background: 'rgba(26, 26, 26, 0.8)',
                   border: '1px solid rgba(42, 42, 42, 0.8)',
                   backdropFilter: 'blur(8px)'
                 }}>
              <span className="w-2 h-2 rounded-full animate-pulse"
                    style={{ background: '#00ff88', boxShadow: '0 0 8px #00ff88' }}></span>
              <span style={{
                fontSize: '12px',
                fontFamily: 'JetBrains Mono',
                color: '#a0a0a0'
              }}>在线</span>
            </div>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 rounded-lg transition-colors"
            style={{ hover: { background: 'rgba(34, 34, 34, 0.5)' } }}
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: '#e0e0e0' }}>
              {isMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 animate-fade-in">
            <nav className="flex flex-col gap-2">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setIsMenuOpen(false)}
                    className="relative flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all duration-200"
                    style={{
                      fontFamily: 'JetBrains Mono',
                      fontSize: '14px',
                      color: isActive ? '#00ff88' : '#a0a0a0',
                      background: isActive ? 'rgba(0, 255, 136, 0.1)' : 'transparent'
                    }}
                  >
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
