import {defineConfig} from 'vite';
import {writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const root=resolve(import.meta.dirname,'..');
const evidence=resolve(root,'../gates/document/browser-benchmark-candidate/build-evidence');
/** Hash exact bytes for transform provenance. @param {string} text Source bytes. @returns {string} Digest. */
function hash(text) {return createHash('sha256').update(text).digest('hex');}
/** Add only a commit-phase view observer to the exact source anchor. @returns {object} Vite plugin. */
function instrument() {
  return {name:'allow-test-only-commit-marker',enforce:'pre',
    /** Instrument exactly one workbench source. @param {string} code Source. @param {string} id Module path. @returns {object|null} Transformation. */
    transform(code,id) {
    if(!id.endsWith('/src/DocumentWorkbench.tsx')) return null;
    const anchor='  const {view,controller}=useController(props.token);';
    if(code.split(anchor).length!==2) throw new Error('Workbench transform anchor missing or nonunique');
    const imports="import {useBenchmarkCommit} from '../bench/bridge';\n";
    const inject=anchor+"\n  useBenchmarkCommit(controller,view);";
    const transformed=imports+code.replace(anchor,inject);
    mkdirSync(evidence,{recursive:true});writeFileSync(resolve(evidence,'DocumentWorkbench.original.txt'),code);
    writeFileSync(resolve(evidence,'DocumentWorkbench.transformed.txt'),transformed);
    writeFileSync(resolve(evidence,'hashes.json'),JSON.stringify({original:hash(code),transformed:hash(transformed)},null,2)+'\n');
    return {code:transformed,map:null};
  }};
}
export default defineConfig({root,base:'/bench/',plugins:[instrument()],build:{outDir:resolve(root,'dist/benchmark'),emptyOutDir:true,rollupOptions:{input:resolve(root,'bench/index.html')}},server:{hmr:false}});
