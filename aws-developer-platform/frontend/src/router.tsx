import { createBrowserRouter, Navigate } from 'react-router';

import { ProtectedLayout } from './components/ProtectedLayout';
import { Approvals } from './pages/Approvals';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { Projects } from './pages/Projects';
import { RequestWizard } from './pages/RequestWizard';

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/', element: <ProtectedLayout />, children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'requests/new', element: <RequestWizard /> },
      { path: 'approvals', element: <Approvals /> },
      { path: 'projects', element: <Projects /> },
    ],
  },
]);
