import { expect, test, vi } from 'vitest';
import { PALETTE, complete, createNode, hole, paletteNode, reference, renderModule, replaceNode, validName } from './model';
import { consumeToken, isCurrent } from './api';
/** Reject a relation in a formula slot without changing the tree. @returns Nothing. */
function rejectsMismatch(): void {
  const root = hole('formula');
  expect(replaceNode(root,[],reference('Person'))).toBe(root);
}
/** Build a complete formula using a typed relation child. @returns Nothing. */
function buildsFormula(): void {
  const some = PALETTE.find(isSome);
  expect(some).toBeDefined();
  const node = replaceNode(createNode(some!),[0],reference('Person'));
  expect(complete(node)).toBe(true);
  expect(renderModule(['Person'],node)).toContain('some Person');
}
/** Identify the existential test palette item. @param item Palette entry. @returns Match flag. */
function isSome(item: {op: string}): boolean { return item.op === 'some'; }
/** Reject incomplete trees and invalid names. @returns Nothing. */
function rejectsInvalid(): void {
  expect(complete(hole('formula'))).toBe(false);
  expect(validName('sig')).toBe(false);
  expect(validName('Person')).toBe(true);
  expect(validName('Person} run {}')).toBe(false);
}
/** Reject forged reference drops without changing the typed candidate. @returns Nothing. */
function rejectsForgedReferences(): void {
  const names = ['Person'];
  const forged = 'ref:Person) }\nassert injected { no Person }\ncheck injected for 3\n// ';
  expect(paletteNode(forged,names)).toBeUndefined();
  expect(paletteNode('ref:univ',names)).toBeUndefined();
  expect(paletteNode('ref:Missing',names)).toBeUndefined();
  expect(paletteNode('ref:Person',['Person','bad name'])).toEqual(reference('Person'));
  expect(paletteNode('ref:bad name',['bad name'])).toBeUndefined();
  expect(paletteNode('some',names)?.op).toBe('some');
  expect(paletteNode('unknown',names)).toBeUndefined();
}
/** Check that revisions and edit epochs both control visibility. @returns Nothing. */
function rejectsStale(): void {
  expect(isCurrent({revision:1,epoch:2},1,2)).toBe(true);
  expect(isCurrent({revision:1,epoch:2},1,3)).toBe(false);
  expect(isCurrent({revision:1,epoch:2},2,2)).toBe(false);
}
/** Check that launch tokens leave browser address history. @returns Nothing. */
function erasesToken(): void {
  const replaceState = vi.fn();
  vi.stubGlobal('window',{location:{hash:'#token=secret',pathname:'/',search:''}});
  vi.stubGlobal('history',{replaceState});
  expect(consumeToken()).toBe('secret');
  expect(replaceState).toHaveBeenCalledWith(null,'','/');
  vi.unstubAllGlobals();
}
test('rejects mismatched drops',rejectsMismatch);
test('builds and renders a complete typed formula',buildsFormula);
test('rejects holes and invalid identifiers',rejectsInvalid);
test('rejects undeclared and source-injecting reference drops',rejectsForgedReferences);
test('filters stale results',rejectsStale);
test('erases the launch token',erasesToken);
