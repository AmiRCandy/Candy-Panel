import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom'; // Import router components
import App from './App.tsx'; // Your main admin panel app
import ClientDetailsPage from './ClientDetailsPage.tsx'; // Your new client details page
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter> {}
      <Routes>
        <Route path="/" element={<App />} /> {/* Your existing admin panel */}
        <Route path="/shortlink/:clientname/:clientpubkey" element={<ClientDetailsPage />} /> {/* New route for client details */}
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
