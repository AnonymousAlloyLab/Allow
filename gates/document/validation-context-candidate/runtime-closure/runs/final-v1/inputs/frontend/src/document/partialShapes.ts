import type {Id,PartialFact,SchemaShape,Type,EnforcementViolation,ViolationIdentity} from './types';
/** Allocate the eight possible bounded widths without choosing any nominal column. @returns Finite shapes. */
export function unknownShapes():readonly SchemaShape[] {const shapes:SchemaShape[]=[];for(let width=1;width<=8;width++) shapes.push({columns:Array<Id|null>(width).fill(null)});return shapes;}
/** Convert an exact type to a partial fact without losing its constructor sort. @param type Exact type. @returns Fact. */
export function typeFact(type:Type):PartialFact {return type.kind==='formula'?{sort:'formula',shapes:[]}:{sort:'relation',shapes:[{columns:type.columns}]};}
/** Encode known facts canonically for stable enforcement identities. @param fact Partial fact. @returns Ordered exact fact tokens. */
export function factTokens(fact:PartialFact):readonly string[] {const tokens:string[]=[fact.sort];for(const shape of fact.shapes) tokens.push(JSON.stringify(shape.columns));return tokens;}
/** Build an exact structured violation key independently of its display message. @param identity Canonical identity. @param nodeId Display node. @param message Human explanation. @returns Violation. */
export function violation(identity:ViolationIdentity,nodeId:Id,message:string):EnforcementViolation {
  const {ownerId,role,rule,expected,actual,relatedIds}=identity;
  return {key:JSON.stringify([ownerId,role,rule,expected,actual,relatedIds]),identity,nodeId,message};
}
/** Intersect two same-width column facts; nominal disagreement has no support. @param a First shape. @param b Second shape. @returns Combined shape or null. */
export function mergeShape(a:SchemaShape,b:SchemaShape):SchemaShape|null {
  if(a.columns.length!==b.columns.length) return null;
  const columns:(Id|null)[]=[];
  for(let i=0;i<a.columns.length;i++) {
    const x=a.columns[i],y=b.columns[i];
    if(x!==null&&y!==null&&x!==y) return null;
    columns.push(x??y);
  }
  return {columns};
}
/** Keep only column facts entailed by every supported shape of each width. @param shapes Supports. @returns Canonical width alternatives. */
export function collapseShapes(shapes:readonly SchemaShape[]):readonly SchemaShape[] {
  const result:SchemaShape[]=[];
  for(let width=1;width<=8;width++) {
    const matches:SchemaShape[]=[];for(const shape of shapes) if(shape.columns.length===width) matches.push(shape);
    if(!matches.length) continue;
    const columns:(Id|null)[]=[];
    for(let index=0;index<width;index++) {
      let value=matches[0].columns[index];for(const shape of matches) if(shape.columns[index]!==value) value=null;columns.push(value);
    }
    result.push({columns});
  }
  return result;
}
/** Intersect finite width alternatives, never enumerating nominal assignments. @param a Current domain. @param b Required domain. @returns Refined domain. */
export function intersectShapes(a:readonly SchemaShape[],b:readonly SchemaShape[]):readonly SchemaShape[] {
  const result:SchemaShape[]=[];
  for(const x of a) for(const y of b) {const merged=mergeShape(x,y);if(merged) result.push(merged);}
  return collapseShapes(result);
}
/** Detect whether a finite domain changed. @param a Previous. @param b Next. @returns Exact structural equality. */
export function sameFact(a:PartialFact,b:PartialFact):boolean {return JSON.stringify(a)===JSON.stringify(b);}
