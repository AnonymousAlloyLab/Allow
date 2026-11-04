import {createRoot} from 'react-dom/client';
import {AllowApp} from '../src/AllowApp';
import {consumeToken} from '../src/api';
import {runBenchmark} from './runner';
import '../src/style.css';

const token=consumeToken(),root=document.getElementById('root'),button=document.getElementById('benchmark-start');
if(!root||!(button instanceof HTMLButtonElement)) throw new Error('Missing benchmark root or control.');
createRoot(root).render(<AllowApp token={token}/>);
/** Run one test-only benchmark at a time. @returns Completion. */
async function start():Promise<void> {
  if(!(button instanceof HTMLButtonElement)||button.disabled) return;
  button.disabled=true;
  try {await runBenchmark();} finally {button.disabled=false;}
}
button.addEventListener('click',start);
