import { Outlet } from 'react-router-dom';
import Header from './Header';

export default function MainLayout() {
  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a' }}>
      <Header />

      <main>
        <Outlet />
      </main>

      <footer style={{
        marginTop: '80px',
        paddingTop: '32px',
        paddingBottom: '32px',
        borderTop: '1px solid rgba(42, 42, 42, 0.8)'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 24px'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            md: {
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between'
            },
            gap: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                color: '#666',
                fontFamily: 'JetBrains Mono',
                fontSize: '14px'
              }}>
                罗小罗
              </span>
              <span style={{ color: '#2a2a2a' }}>•</span>
              <span style={{
                color: '#666',
                fontFamily: 'Source Sans 3',
                fontSize: '14px'
              }}>
                药研情报数据库
              </span>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '24px',
              fontSize: '14px',
              fontFamily: 'JetBrains Mono'
            }}>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#666',
                  textDecoration: 'none',
                  transition: 'color 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = '#00ff88'}
                onMouseLeave={(e) => e.currentTarget.style.color = '#666'}
              >
                API 文档
              </a>
              <span style={{ color: '#2a2a2a' }}>•</span>
              <span style={{ color: '#666' }}>v1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
