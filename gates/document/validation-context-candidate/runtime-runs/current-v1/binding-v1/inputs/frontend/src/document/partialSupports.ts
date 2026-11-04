import type {SchemaShape} from './types';
import {mergeShape,collapseShapes} from './partialShapes';
export interface Supports {readonly inputs:readonly (readonly SchemaShape[])[]}
/** Enumerate bounded width supports for equality, not nominal assignments. @param a First domain. @param b Second domain. @returns Matching projections. */
export function equalitySupports(a:readonly SchemaShape[],b:readonly SchemaShape[]):Supports {
  const merged:SchemaShape[]=[];
  for(const x of a) for(const y of b) {const value=mergeShape(x,y);if(value) merged.push(value);}
  const result=collapseShapes(merged);return {inputs:[result,result]};
}
/** Retain transpose projections supported by both independently constrained domains. @param input Operand. @param output Result domain. @returns Supported shapes. */
export function transposeSupports(input:readonly SchemaShape[],output:readonly SchemaShape[]):Supports {
  const a:SchemaShape[]=[],b:SchemaShape[]=[];
  for(const x of input) if(x.columns.length===2) for(const y of output) {
    const merged=mergeShape({columns:[...x.columns].reverse()},y);
    if(merged) {a.push({columns:[...merged.columns].reverse()});b.push(merged);}
  }
  return {inputs:[collapseShapes(a),collapseShapes(b)]};
}
/** Project one product support into its exact input positions. @param a Left shape. @param b Right shape. @param out Candidate result. @returns Three projections or null. */
function productShape(a:SchemaShape,b:SchemaShape,out:SchemaShape):readonly SchemaShape[]|null {
  const joined=mergeShape({columns:[...a.columns,...b.columns]},out);
  if(!joined||joined.columns.length>8) return null;
  return [{columns:joined.columns.slice(0,a.columns.length)},{columns:joined.columns.slice(a.columns.length)},joined];
}
/** Project one nominal join support, preserving nonempty bounded output. @param a Left shape. @param b Right shape. @param out Candidate result. @returns Three projections or null. */
function joinShape(a:SchemaShape,b:SchemaShape,out:SchemaShape):readonly SchemaShape[]|null {
  const left=a.columns.at(-1)!,right=b.columns[0];
  if(left!==null&&right!==null&&left!==right) return null;
  const endpoint=left??right,joined=mergeShape({columns:[...a.columns.slice(0,-1),...b.columns.slice(1)]},out);
  if(!joined||joined.columns.length<1||joined.columns.length>8) return null;
  const split=a.columns.length-1;
  return [{columns:[...joined.columns.slice(0,split),endpoint]},{columns:[endpoint,...joined.columns.slice(split)]},joined];
}
/** Enumerate at most8x8x8 width supports for a fixed product/join equation. @param kind Operator. @param a Left. @param b Right. @param out Result domain. @returns Canonical projections. */
export function compositionSupports(kind:'product'|'join',a:readonly SchemaShape[],b:readonly SchemaShape[],out:readonly SchemaShape[]):Supports {
  const supports:SchemaShape[][]=[[],[],[]];
  for(const x of a) for(const y of b) for(const z of out) {
    const projection=kind==='product'?productShape(x,y,z):joinShape(x,y,z);
    if(projection) for(let index=0;index<projection.length;index++) supports[index].push(projection[index]);
  }
  return {inputs:supports.map(collapseShapes)};
}
