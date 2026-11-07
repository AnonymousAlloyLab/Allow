import {createRoot} from 'react-dom/client';
import {AccessRequest} from './AccessRequest';
import './style.css';
const root=document.getElementById('root');
if(!root) throw new Error('Missing application root.');
createRoot(root).render(<AccessRequest/>);
