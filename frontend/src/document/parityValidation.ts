/** Closed successful parity payload fields including the common authority envelope. */
const FIELDS=['synthesizedSourceHash','categories','classification','moduleHash','scope','bitwidth','maxseq','sourceHash','left','right','correspondence','targetId','oracle','requestHash','documentId','draftId','draftEpoch','baseRevision','artifactId','policyVersion','dependencyHash'];
/** Require an invariant at the untrusted response boundary. @param condition Required invariant. @returns Nothing. */
function requireValue(condition:unknown):asserts condition {if(!condition) throw new Error('Malformed parity evidence.');}
/** Check an exact closed object before reading any nested values. @param value Untrusted object. @param fields Exact keys. @returns Checked object. */
function closed(value:unknown,fields:readonly string[]):Record<string,unknown> {
  requireValue(!!value&&typeof value==='object'&&!Array.isArray(value));const object=value as Record<string,unknown>;
  requireValue(Object.keys(object).length===fields.length&&fields.every(has.bind(null,object)));return object;
}
/** Recognize an own field without following prototype properties. @param object Checked object. @param key Field. @returns Whether own. */
function has(object:Record<string,unknown>,key:string):boolean {return Object.prototype.hasOwnProperty.call(object,key);}
/** Require a bounded plain string. @param value Untrusted value. @param maximum Length bound. @returns Checked text. */
function text(value:unknown,maximum=512):string {requireValue(typeof value==='string'&&value.length>0&&value.length<=maximum);return value;}
/** Require an exact lowercase SHA256. @param value Untrusted hash. @returns Checked hash. */
function hash(value:unknown):string {const result=text(value,64);requireValue(/^[a-f0-9]{64}$/.test(result));return result;}
/** Require a bounded array. @param value Untrusted value. @param maximum Cardinality bound. @returns Checked array. */
function array(value:unknown,maximum:number):unknown[] {requireValue(Array.isArray(value)&&value.length<=maximum);return value;}
/** Require exact integral metadata without coercion. @param value Untrusted number. @param minimum Inclusive minimum. @param maximum Inclusive maximum. @returns Checked number. */
function integer(value:unknown,minimum:number,maximum:number):number {requireValue(typeof value==='number'&&Number.isSafeInteger(value)&&value>=minimum&&value<=maximum);return value;}
/** Check nominal product names or atom identities. @param value Array value. @param maximum Cardinality bound. @param nonempty Whether at least one. @returns Checked strings. */
function strings(value:unknown,maximum:number,nonempty=false):string[] {const values=array(value,maximum);requireValue(!nonempty||values.length>0);return values.map(checkedText);}
/** Validate one bounded display string. @param value Untrusted text. @returns Checked string. */
function checkedText(value:unknown):string {return text(value);}
/** Validate fixed-width tuple projections. @param value Tuples. @param width Exact relation width. @returns Nothing. */
function tuples(value:unknown,width:number):void {for(const row of array(value,1000)) requireValue(strings(row,8).length===width);}
/** Validate closed atoms and relation projections in one trace state. @param value Untrusted state. @returns Nothing. */
function state(value:unknown):void {
  const object=closed(value,['atoms','relations']),ids=new Set<string>(),names=new Set<string>();
  for(const item of array(object.atoms,1000)) {const atom=closed(item,['id','memberships']),id=text(atom.id);requireValue(!ids.has(id));ids.add(id);strings(atom.memberships,2048,true);}
  for(const item of array(object.relations,128)) {const relation=closed(item,['name','arity','tuples']),name=text(relation.name);requireValue(!names.has(name));names.add(name);tuples(relation.tuples,integer(relation.arity,1,8));}
}
/** Validate complete static trace metadata and its displayed states. @param value Untrusted witness. @returns Nothing. */
function witness(value:unknown):void {
  const object=closed(value,['states','traceLength','loopState','truncated','fullInstanceHash']),length=integer(object.traceLength,1,10);
  integer(object.loopState,-1,length-1);requireValue(typeof object.truncated==='boolean');hash(object.fullInstanceHash);
  const states=array(object.states,10);requireValue(states.length===length);for(const item of states) state(item);
}
/** Validate one exact shared assignment including positional predicate names. @param value Untrusted binding. @returns Checked binding. */
function binding(value:unknown):Record<string,unknown> {
  const object=closed(value,['id','name','columns','truncated','tuples','leftName','rightName']);
  text(object.id,128);text(object.name,128);text(object.leftName,128);text(object.rightName,128);requireValue(typeof object.truncated==='boolean');tuples(object.tuples,strings(object.columns,8,true).length);return object;
}
/** Validate the complete four-category truth partition independently of presentation labels. @param value Untrusted categories. @returns Derived completed classification. */
function categories(value:unknown):string {
  const names=['both','leftOnly','rightOnly','neither'],object=closed(value,names);let any=false,difference=false;
  for(let index=0;index<4;index++) {
    const item=object[names[index]];requireValue(!!item&&typeof item==='object');const status=(item as Record<string,unknown>).status;
    if(status==='UNSAT') {closed(item,['status']);continue;}
    const category=closed(item,['status','left','right','witness','assignment','evidenceHash']);requireValue(status==='SAT'&&category.left===(index<2)&&category.right===(index===0||index===2));
    hash(category.evidenceHash);witness(category.witness);const ids=new Set<string>();
    for(const assignment of array(category.assignment,32)) {const checked=binding(assignment),id=String(checked.id);requireValue(!ids.has(id));ids.add(id);}
    any=true;if(index===1||index===2) difference=true;
  }
  return !any?'NO_INSTANCES':difference?'DISTINGUISHED':'AGREEMENT';
}
/** Validate exact source and predicate selection identities. @param value Untrusted selection. @returns Checked selection. */
function selection(value:unknown):Record<string,unknown> {const object=closed(value,['sourceHash','predicate']);hash(object.sourceHash);text(object.predicate,128);return object;}
/** Check ordered shared parameter correspondence and all SAT assignment bindings. @param value Untrusted mapping. @param outcomes Validated categories. @returns Checked mapping. */
function correspondence(value:unknown,outcomes:Record<string,unknown>):Record<string,unknown> {
  const object=closed(value,['leftPredicate','rightPredicate','parameters','declarations']),parameters=array(object.parameters,16),ids=new Set<string>();text(object.leftPredicate,128);text(object.rightPredicate,128);
  for(const item of parameters) {const parameter=closed(item,['leftName','rightName','columns','sharedId']),id=text(parameter.sharedId,128);text(parameter.leftName,128);text(parameter.rightName,128);strings(parameter.columns,8,true);requireValue(!ids.has(id));ids.add(id);}
  for(const item of array(object.declarations,2048)) {const declaration=closed(item,['kind','name']);text(declaration.name,128);requireValue(declaration.kind==='signature'||declaration.kind==='field');}
  for(const value of Object.values(outcomes)) {
    const category=value as Record<string,unknown>;if(category.status!=='SAT') continue;
    const assignments=category.assignment as Record<string,unknown>[];requireValue(assignments.length===parameters.length);
    for(const item of parameters) {const parameter=item as Record<string,unknown>,match=assignments.find(assignmentMatches.bind(null,parameter.sharedId));requireValue(!!match&&match.name===parameter.leftName&&match.leftName===parameter.leftName&&match.rightName===parameter.rightName&&JSON.stringify(match.columns)===JSON.stringify(parameter.columns));}
  }
  return object;
}
/** Match an already validated shared assignment identity. @param id Shared identity. @param item Checked assignment. @returns Match. */
function assignmentMatches(id:unknown,item:Record<string,unknown>):boolean {return item.id===id;}
/** Validate the entire closed payload before witness rendering or any frame color. @param value Untrusted successful payload. @returns Whether structurally valid. */
export function validParityPayload(value:unknown):boolean {
  try {
    const object=closed(value,FIELDS);for(const key of ['synthesizedSourceHash','moduleHash','sourceHash','requestHash']) hash(object[key]);
    for(const key of ['documentId','draftId','artifactId','dependencyHash','targetId']) text(object[key],512);
    integer(object.draftEpoch,0,Number.MAX_SAFE_INTEGER);integer(object.baseRevision,0,Number.MAX_SAFE_INTEGER);integer(object.scope,1,5);requireValue(object.bitwidth===4&&object.maxseq===3&&(typeof object.policyVersion==='string'||typeof object.policyVersion==='number'));
    const left=selection(object.left),right=selection(object.right),oracle=selection(object.oracle);requireValue(right.sourceHash===oracle.sourceHash&&right.predicate===oracle.predicate);
    requireValue(object.classification===categories(object.categories));const mapping=correspondence(object.correspondence,object.categories as Record<string,unknown>);
    requireValue(mapping.leftPredicate===left.predicate&&mapping.rightPredicate===right.predicate);return true;
  } catch {return false;}
}
/** Check category evidence alone for a conservative truth-table verdict. @param value Untrusted categories. @returns Whether fully well formed. */
export function validParityCategories(value:unknown):boolean {try {categories(value);return true;} catch {return false;}}
