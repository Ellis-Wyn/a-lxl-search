import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { SearchProvider } from './context/SearchContext';
import MainLayout from './components/layout/MainLayout';
import Home from './pages/Home/Home';
import Pipelines from './pages/Pipelines/Pipelines';
import Publications from './pages/Publications/Publications';
import Targets from './pages/Targets/Targets';
import TargetDetail from './pages/TargetDetail/TargetDetail';
import './styles/globals.css';

function App() {
  return (
    <SearchProvider>
      <Router>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Home />} />
            <Route path="pipelines" element={<Pipelines />} />
            <Route path="publications" element={<Publications />} />
            <Route path="targets" element={<Targets />} />
            <Route path="targets/:targetId" element={<TargetDetail />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Router>
    </SearchProvider>
  );
}

export default App;
