export type Kind = 'formula' | 'relation';
export type Op = 'hole' | 'ref' | 'and' | 'or' | 'implies' | 'not' | 'some' | 'no' | 'union';
export interface Node { readonly op: Op; readonly kind: Kind; readonly name?: string; readonly children: readonly Node[] }
export interface PaletteItem { readonly op: Op; readonly label: string; readonly kind: Kind; readonly inputs: readonly Kind[] }
export const PALETTE: readonly PaletteItem[] = [
  {op:'and', label:'And', kind:'formula', inputs:['formula','formula']},
  {op:'or', label:'Or', kind:'formula', inputs:['formula','formula']},
  {op:'implies', label:'Implies', kind:'formula', inputs:['formula','formula']},
  {op:'not', label:'Not', kind:'formula', inputs:['formula']},
  {op:'some', label:'Some', kind:'formula', inputs:['relation']},
  {op:'no', label:'No', kind:'formula', inputs:['relation']},
  {op:'union', label:'Union', kind:'relation', inputs:['relation','relation']},
];
/** Create a typed empty slot. @param kind Expected type. @returns Empty node. */
export function hole(kind: Kind): Node { return {op:'hole',kind,children:[]}; }
/** Construct a palette node with typed holes. @param item Palette descriptor. @returns New tree node. */
export function createNode(item: PaletteItem): Node {
  return {op:item.op,kind:item.kind,children:item.inputs.map(hole)};
}
/** Construct a relation reference. @param name Validated declaration name. @returns Relation node. */
export function reference(name: string): Node { return {op:'ref',kind:'relation',name,children:[]}; }
/** Resolve untrusted palette data without accepting invented symbols. @param item Dragged palette identifier. @param names Declared signature names. @returns Supported node or undefined. */
export function paletteNode(item: string, names: readonly string[]): Node | undefined {
  const descriptor = PALETTE.find(matchesPalette.bind(null,item));
  if (descriptor) return createNode(descriptor);
  if (!item.startsWith('ref:')) return undefined;
  const name = item.slice(4);
  return validName(name) && names.includes(name) ? reference(name) : undefined;
}
/** Compare a closed palette operator with an untrusted identifier. @param identifier Dragged item identifier. @param item Supported palette descriptor. @returns Whether the operator matches exactly. */
function matchesPalette(identifier: string, item: PaletteItem): boolean { return item.op === identifier; }
/** Validate a simple Alloy identifier. @param name User label. @returns Whether the label is supported. */
export function validName(name: string): boolean {
  return /^[A-Za-z][A-Za-z0-9_]*$/.test(name) && !RESERVED.has(name);
}
const RESERVED = new Set(['sig','one','lone','some','no','all','fact','pred','run','check','and','or','not','implies','univ','none','Int','abstract','as','assert','but','check','disj','else','enum','exactly','expect','extends','for','fun','iden','iff','in','let','module','open','private','seq','set','sum','this','var','always','eventually','after','before','until','releases','historically','once','since','triggered']);
/** Read a node at a path. @param root Tree root. @param path Child indices. @returns Selected node or undefined. */
export function atPath(root: Node, path: readonly number[]): Node | undefined {
  let current: Node | undefined = root;
  for (const index of path) current = current?.children[index];
  return current;
}
/** Replace a compatible tree node immutably. @param root Current tree. @param path Target path. @param next Replacement. @returns New tree or original on mismatch. */
export function replaceNode(root: Node, path: readonly number[], next: Node): Node {
  if (path.length === 0) return root.kind === next.kind ? next : root;
  const index = path[0];
  const child = root.children[index];
  if (!child) return root;
  const replacement = replaceNode(child,path.slice(1),next);
  if (replacement === child) return root;
  const children = root.children.slice();
  children[index] = replacement;
  return {...root,children};
}
/** Check that every slot is filled. @param root Candidate tree. @returns True when complete. */
export function complete(root: Node): boolean {
  return root.op !== 'hole' && root.children.every(complete);
}
/** Render a complete tree as readable Alloy. @param root Expression tree. @returns Alloy expression. @throws Error for a hole. */
export function renderExpr(root: Node): string {
  if (root.op === 'hole') throw new Error('Fill every slot before applying.');
  if (root.op === 'ref') return root.name ?? '';
  const children = root.children.map(renderExpr);
  if (root.op === 'not' || root.op === 'some' || root.op === 'no') return `(${root.op} ${children[0]})`;
  const operator = root.op === 'union' ? '+' : root.op;
  return `(${children[0]} ${operator} ${children[1]})`;
}
/** Render a composer candidate. @param names Declared signature names. @param root Complete formula. @returns Alloy module text. */
export function renderModule(names: readonly string[], root: Node): string {
  const declarations = names.map(renderSignature).join('\n');
  return `${declarations}\n\npred model { ${renderExpr(root)} }\nrun model for 3\n`;
}
/** Render one signature declaration. @param name Signature label. @returns Declaration text. */
function renderSignature(name: string): string { return `sig ${name} {}`; }
