import {expect,test} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {DeclarationEditor} from './DeclarationEditor';
import {ExpressionEditor} from './ExpressionEditor';
import {Fixture,TAGS} from './fixtures';
import {construct,replaceSubtree} from './operations';
/** Accept component callbacks during static markup inspection. @param values Callback payloads. @returns Nothing. */
function ignore(...values:unknown[]):void {void values;}
/** Render every closed expression palette entry with accessible constraints and actions. @returns Nothing. */
function fullPaletteMarkup():void {
  const module=new Fixture().build('all_quant'),selected=module.predicates[0].bodyId;
  const markup=renderToStaticMarkup(<ExpressionEditor snapshot="snapshot" module={module} selected={selected} onSelect={ignore} onInsert={ignore} onClipboard={ignore} onPaste={ignore} onDelete={ignore} onDropNode={ignore} onCancel={ignore} onNotice={ignore}/>);
  for(const tag of TAGS) expect(markup).toContain(`data-operator="${tag}"`);
  expect(markup).toContain('Expected destination:');expect(markup).toContain('In-scope variables');
  expect(markup).toContain('Copy (Ctrl/Cmd+C)');expect(markup).toContain('Cut (Ctrl/Cmd+X)');expect(markup).toContain('Paste (Ctrl/Cmd+V)');
  expect(markup).toContain('aria-describedby=');expect(markup).toContain('aria-pressed="true"');
  expect(markup).toContain('Variable · local');expect(markup).toContain('For every variable · local:');
}
/** Render declaration schema/parameter controls without relying on color or drag. @returns Nothing. */
function declarationMarkup():void {
  const module=new Fixture().build('predicate_call');
  const markup=renderToStaticMarkup(<DeclarationEditor module={module} onChange={ignore} onSelect={ignore}/>);
  expect(markup).toContain('Owner signature');expect(markup).toContain('Ordered nominal schema (set-valued)');
  expect(markup).toContain('Ordered set-valued parameters');expect(markup).toContain('Parameter name');
  for(const tag of ['signature','field','predicate','fact','assertion','run','check']) expect(markup).toContain(`Add ${tag}`);
}
test('static markup exposes full palette and named keyboard-equivalent actions',fullPaletteMarkup);
test('static markup exposes declaration/parameter exact nominal editors',declarationMarkup);
/** Display a partial constructor's known result sort while leaving unresolved nominal schemas honest. @returns Nothing. */
function partialResultLabels():void {
  const original=new Fixture().build('not'),nodes=construct('not','',original),module=replaceSubtree(original,original.predicates[0].bodyId,nodes);
  const markup=renderToStaticMarkup(<ExpressionEditor snapshot="partial" module={module} selected={nodes[0].id} onSelect={ignore} onInsert={ignore} onClipboard={ignore} onPaste={ignore} onDelete={ignore} onDropNode={ignore} onCancel={ignore} onNotice={ignore}/>);
  expect(markup).toContain('>Not</span>');expect(markup).toContain('>formula</span>');expect(markup).toContain('Drop block · Unresolved hole');expect(markup).toContain('class="block-symbol" aria-hidden="true"');
}
test('partial block labels display known structural formula sort without invented relation schemas',partialResultLabels);
