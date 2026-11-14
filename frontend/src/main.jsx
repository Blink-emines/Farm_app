import { createRoot } from 'react-dom/client';
import 'leaflet/dist/leaflet.css';
import '@fontsource/ibm-plex-sans/latin-400.css';
import '@fontsource/ibm-plex-sans/latin-500.css';
import '@fontsource/ibm-plex-sans/latin-600.css';
import '@fontsource/ibm-plex-sans-arabic/arabic-400.css';
import '@fontsource/ibm-plex-sans-arabic/arabic-500.css';
import '@fontsource/ibm-plex-sans-arabic/arabic-600.css';
import './styles.css';
import { LangProvider } from './i18n/index.jsx';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <LangProvider>
    <App />
  </LangProvider>,
);
