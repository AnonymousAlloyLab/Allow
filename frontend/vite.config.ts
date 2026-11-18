import {defineConfig} from 'vite';
import {resolve} from 'node:path';
export default defineConfig({build:{rollupOptions:{input:{workbench:resolve(import.meta.dirname,'index.html'),accessRequest:resolve(import.meta.dirname,'request-ai-access/index.html')}}}});
