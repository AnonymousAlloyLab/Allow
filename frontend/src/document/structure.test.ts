import {expect,test} from 'vitest';
import {emptyModule} from './model';
import {appendSignature,insertField,maskSource,nameProblem,nextName,sourceSignatures,topLevelNames,unownedFields,withField,withSignature,withoutSignature} from './structure';
/** Generate fresh names and explain rejected ones. @returns Nothing. */
function namesAndProblems():void {
  expect(nextName('Sig',new Set(['Sig1','Sig2']))).toBe('Sig3');
  expect(nameProblem('Person',new Set())).toBeNull();
  expect(nameProblem('Person',new Set(['Person']))).toContain('already used');
  expect(nameProblem('sig',new Set())).toContain('can’t be used');
  expect(nameProblem('2files',new Set())).toContain('can’t be used');
  expect(nameProblem('allow_x',new Set())).toContain('reserved');
}
/** Add, group and remove signatures and fields without touching other declarations. @returns Nothing. */
function moduleEdits():void {
  let module=withSignature(withSignature(emptyModule(),'Person'),'File');
  const [person,file]=module.signatures;
  module=withField(module,{owner:file.id,name:'owner',multiplicity:'one',range:[person.id]});
  module=withField(module,{owner:person.id,name:'friends',multiplicity:'set',range:[person.id]});
  expect(module.fields.map(fieldName)).toEqual(['friends','owner']);
  expect(topLevelNames(module)).toEqual(new Set(['Person','File']));
  const removed=withoutSignature(module,file);
  expect(removed.signatures.map(fieldName)).toEqual(['Person']);
  expect(removed.fields.map(fieldName)).toEqual(['friends']);
  expect(unownedFields({...module,signatures:[file]}).map(fieldName)).toEqual(['friends']);
}
/** Read a declaration name. @param item Named declaration. @returns Name. */
function fieldName(item:{readonly name:string}):string {return item.name;}
/** Find signature bodies while ignoring comments, strings, extends clauses and appended facts. @returns Nothing. */
function scanSource():void {
  const source='// sig Fake {}\nabstract sig A, B extends C { f: set A } { some f }\n/* sig Hidden { } */\none sig D in A {}\npred p { "sig S {" = "x" }\n';
  expect(maskSource(source).length).toBe(source.length);
  const found=sourceSignatures(source);
  expect(found.map(joinNames)).toEqual(['A,B','D']);
  expect(source.slice(found[0].open,found[0].close+1)).toBe('{ f: set A }');
}
/** Join the names of one declaration. @param item Declaration. @returns Comma-joined names. */
function joinNames(item:{readonly names:readonly string[]}):string {return item.names.join();}
/** Insert fields into empty, server-formatted, populated, trailing-comma and comment-only bodies. @returns Nothing. */
function insertFields():void {
  /** Insert into the first signature. @param source Alloy text. @returns New text. */
  function first(source:string):string {return insertField(source,sourceSignatures(source)[0],'g: one B');}
  expect(first('sig A {}')).toBe('sig A {\n  g: one B\n}');
  expect(first('sig A {\n\n}\n')).toBe('sig A {\n  g: one B\n}\n');
  expect(first('sig A {\n  f: set A\n}')).toBe('sig A {\n  f: set A,\n  g: one B\n}');
  expect(first('sig A { f: set A, }')).toBe('sig A { f: set A,\n  g: one B }');
  expect(first('sig A { f: set A -- note }\n}')).toBe('sig A { f: set A,\n  g: one B -- note }\n}');
  expect(first('sig A { /* {nested} */ }')).toBe('sig A {\n  g: one B /* {nested} */ }');
}
/** Append signatures after the last declaration, or at the end when it has an appended fact. @returns Nothing. */
function appendSignatures():void {
  expect(appendSignature('','A')).toBe('sig A {}\n');
  expect(appendSignature('sig A {}\npred p { some A }','B')).toBe('sig A {}\nsig B {}\npred p { some A }');
  expect(appendSignature('sig A {} { some A }','B')).toBe('sig A {} { some A }\nsig B {}\n');
}
test('structure names are fresh and rejected names explain why',namesAndProblems);
test('structure edits keep fields grouped with their signature',moduleEdits);
test('source scanning finds only real signature bodies',scanSource);
test('text-mode field insertion keeps existing text and comments',insertFields);
test('text-mode signature insertion never splits an appended fact',appendSignatures);
