import { createBrowserRouter, Navigate } from 'react-router';

import { Layout } from './components/Layout';
import { Approvals } from './pages/Approvals';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { RequestWizard } from './pages/RequestWizard';

export const router = createBrowserRouter([
  {
    path: '/', element: <Layout />, children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'requests/new', element: <RequestWizard /> },
      { path: 'approvals', element: <Approvals /> },
      { path: 'projects', element: <Projects /> },
    ],
  },
]);
