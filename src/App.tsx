import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { DashboardPage } from './pages/Dashboard';
import { RoutePlanningPage } from './pages/RoutePlanning';
import { IncidentsPage } from './pages/Incidents';
import { RescueUnitsPage } from './pages/RescueUnits';
import { AIAnalysisPage } from './pages/AIAnalysis';
import { CommandCenterPage } from './pages/CommandCenter';
import { SimulationCenterPage } from './pages/SimulationCenter';
import { EvaluationCenter } from './pages/EvaluationCenter';

import { RequestRescuePage } from './pages/RequestRescue';
import { RescuerModePage } from './pages/RescuerMode';
import { PostDisasterAssessmentPage } from './pages/PostDisasterAssessmentPage';

export function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/post-disaster-assessment" element={<PostDisasterAssessmentPage />} />
          <Route path="/request-rescue" element={<RequestRescuePage />} />
          <Route path="/rescuer-mode" element={<RescuerModePage />} />
          <Route path="/evaluation-center" element={<EvaluationCenter />} />
          <Route path="/command-center" element={<CommandCenterPage />} />
          <Route path="/simulation-center" element={<SimulationCenterPage />} />
          <Route path="/route-planning" element={<RoutePlanningPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/rescue-units" element={<RescueUnitsPage />} />
          <Route path="/ai-analysis" element={<AIAnalysisPage />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}


export default App;
