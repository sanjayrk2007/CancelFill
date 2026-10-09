import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import '@fontsource-variable/inter';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { OffersProvider } from './context/OffersContext';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <OffersProvider>
            <App />
          </OffersProvider>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
