import { createRoot } from 'react-dom/client';
import { consumeToken } from './api';
import { Bootstrap } from './Bootstrap';
import './style.css';
const token = consumeToken();
const root = document.getElementById('root');
if (!root) throw new Error('Missing application root.');
createRoot(root).render(<Bootstrap token={token}/>);
