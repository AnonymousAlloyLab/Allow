import { createRoot } from 'react-dom/client';
import { consumeToken } from './api';
import { Workbench } from './Workbench';
import './style.css';
const token = consumeToken();
const root = document.getElementById('root');
if (!root) throw new Error('Missing application root.');
createRoot(root).render(<Workbench token={token}/>);
