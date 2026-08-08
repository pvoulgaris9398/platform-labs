import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';

import { router } from './router';

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');
const queryClient = new QueryClient();

createRoot(root).render(<StrictMode><ThemeProvider theme={createTheme()}><CssBaseline /><QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider></ThemeProvider></StrictMode>);
