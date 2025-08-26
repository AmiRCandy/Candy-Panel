import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import ClientDetailsPage from './ClientDetailsPage.tsx';
import './index.css';

// Get client name and public key from URL path
const pathParts = window.location.pathname.split('/');
const clientName = pathParts[2]; // /shortlink/name/pubkey
const clientPubKey = pathParts[3];

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClientDetailsPage />
  </StrictMode>
);
