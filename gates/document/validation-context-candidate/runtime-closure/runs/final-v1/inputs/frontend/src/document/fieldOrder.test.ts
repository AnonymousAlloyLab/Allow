import {expect,test} from 'vitest';
import type {DraftModule,Field} from './types';
import {Fixture} from './fixtures';
import {checkModule,freshId} from './model';
import {fieldsGrouped,groupDraftFields,fieldTransitionNotice} from './fieldOrder';
import {addDeclaration,updateDeclaration} from './declarations';
/** Construct a valid typed forest with two owners and distinct within-owner fields. @returns Grouped module. */
function groupedFixture():DraftModule {
  const module=new Fixture().build('and'),a=module.signatures[0].id,b=module.signatures[1].id;
  const first:Field={tag:'field',id:freshId(),name:'firstA',ownerSignatureId:a,rangeColumns:[b],multiplicity:'one'};
  const second:Field={tag:'field',id:freshId(),name:'secondA',ownerSignatureId:a,rangeColumns:[a,b],multiplicity:'set'};
  const third:Field={tag:'field',id:freshId(),name:'firstB',ownerSignatureId:b,rangeColumns:[a],multiplicity:'lone'};
  return {...module,fields:[first,second,third]};
}
/** Reject interleaved complete candidates without silently changing presentation. @returns Nothing. */
function rejectsInterleaving():void {
  const grouped=groupedFixture(),fields=[grouped.fields[0],grouped.fields[2],grouped.fields[1]],interleaved={...grouped,fields};
  expect(fieldsGrouped(grouped)).toBe(true);expect(checkModule(grouped).complete).toBe(true);
  expect(fieldsGrouped(interleaved)).toBe(false);
  const checked=checkModule(interleaved);
  expect(checked.complete).toBe(false);expect(checked.diagnostics).toHaveLength(1);
  expect(checked.diagnostics[0].message).toContain('submitted order is not normalized');
  expect(interleaved.fields).toBe(fields);expect(interleaved.fields[1].id).toBe(grouped.fields[2].id);
}
/** Keep node registry storage order separate from ordered expression-tree semantics. @returns Nothing. */
function shuffledRegistry():void {
  const module=groupedFixture(),shuffled={...module,nodes:[...module.nodes].reverse()};
  const original=checkModule(module),reordered=checkModule(shuffled);
  expect(reordered.complete).toBe(true);expect(reordered.diagnostics).toEqual([]);
  expect([...reordered.types]).toEqual([...original.types]);
  expect(shuffled.predicates).toBe(module.predicates);
  expect(shuffled.fields).toBe(module.fields);
}
/** Add a first-owner field explicitly before later owners while retaining existing group order. @returns Nothing. */
function groupedInsertion():void {
  const before=groupedFixture(),after=addDeclaration(before,'field');
  expect(fieldsGrouped(after)).toBe(true);expect(checkModule(after).complete).toBe(true);
  expect(after.fields.slice(0,2)).toEqual(before.fields.slice(0,2));
  expect(after.fields[2].ownerSignatureId).toBe(before.signatures[0].id);
  expect(after.fields[3]).toBe(before.fields[2]);
  expect(fieldTransitionNotice(before,after)).toContain('Draft field insertion/reassignment grouped');
  expect(before.fields).toHaveLength(3);
}
/** Reassign owner through explicit stable grouping without mutating prior fields. @returns Nothing. */
function groupedReassignment():void {
  const before=groupedFixture(),moved={...before.fields[0],ownerSignatureId:before.signatures[1].id};
  const after=updateDeclaration(before,moved);
  expect(fieldsGrouped(after)).toBe(true);expect(checkModule(after).complete).toBe(true);
  expect(after.fields).toEqual([before.fields[1],moved,before.fields[2]]);
  expect(before.fields[0].ownerSignatureId).toBe(before.signatures[0].id);
  expect(fieldTransitionNotice(before,after)).toContain('Accepted history unchanged');
  expect(fieldTransitionNotice(before,{...before,fields:[...before.fields]})).toBe(null);
}
/** Preserve unresolved draft fields visibly instead of silently dropping them during grouping. @returns Nothing. */
function unresolvedOwner():void {
  const module=groupedFixture(),unknown={...module.fields[0],id:freshId(),ownerSignatureId:'missing'};
  const fields=groupDraftFields(module,[unknown,...module.fields]);
  expect(fields.at(-1)).toBe(unknown);expect(fields).toHaveLength(4);
  expect(checkModule({...module,fields}).complete).toBe(false);
}
test('complete browser candidate rejects interleaved fields without normalization',rejectsInterleaving);
test('shuffled identity-indexed node registry preserves ordered forest checker results',shuffledRegistry);
test('field insertion explicitly maintains signature grouping and within-owner order',groupedInsertion);
test('owner reassignment explicitly groups draft and preserves prior history',groupedReassignment);
test('unknown draft owner is retained visibly and cannot pass validation',unresolvedOwner);
