import type {DraftModule,DraftNode,Expression,Id,Parameter} from './types';
import {emptyModule,freshId,UNARY,BINARY,QUANT} from './model';
export const TAGS:readonly Expression['tag'][]=['signature_ref','field_ref','variable_ref','predicate_call',...UNARY,...BINARY,...QUANT];
/** Build owned constructor fixtures independently from runtime construction. */
export class Fixture {
  private readonly nodes:DraftNode[]=[];
  private readonly a=freshId();
  private readonly b=freshId();
  private readonly field=freshId();
  private readonly wide=freshId();
  private readonly predicate=freshId();
  private readonly parameter:Parameter={tag:'parameter',id:freshId(),name:'parameter',columns:[]};
  /** Build a scoped declaration environment. */
  constructor() {this.parameter={...this.parameter,columns:[this.a]};}
  /** Append an independently assembled node. @param node Constructor. @returns Identity. */
  private add(node:DraftNode):Id {this.nodes.push(node);return node.id;}
  /** Build a nominal signature reference. @param target Exact signature. @returns Expression ID. */
  private ref(target:Id=this.a):Id {return this.add({tag:'signature_ref',id:freshId(),targetId:target});}
  /** Build a formula subtree with owned leaves. @returns Formula expression ID. */
  private formula():Id {return this.add({tag:'some_test',id:freshId(),operandId:this.ref()});}
  /** Assemble a unary tag with a valid or known-invalid operand. @param tag Constructor. @param invalid Denial fixture. @returns Root. */
  private unary(tag:Expression['tag'],invalid:boolean):Id {
    const id=freshId();
    if(tag==='transpose') return this.add({tag,id,operandId:invalid?this.ref():this.add({tag:'field_ref',id:freshId(),targetId:this.field})});
    const operandId=tag==='not'?(invalid?this.ref():this.formula()):(invalid?this.formula():this.ref());
    return this.add({tag:tag as 'not'|'some_test'|'no_test'|'one_test'|'lone_test',id,operandId});
  }
  /** Assemble binary tags with exact nominal acceptance and denials. @param tag Constructor. @param invalid Denial fixture. @returns Root. */
  private binary(tag:Expression['tag'],invalid:boolean):Id {
    let leftId:Id,rightId:Id;
    if(['and','or','implies','iff'].includes(tag)) {leftId=invalid?this.ref():this.formula();rightId=this.formula();}
    else if(tag==='join') {leftId=this.add({tag:'field_ref',id:freshId(),targetId:this.field});rightId=this.ref(invalid?this.a:this.b);}
    else if(tag==='product'&&invalid) {leftId=this.add({tag:'field_ref',id:freshId(),targetId:this.wide});rightId=this.ref();}
    else {leftId=this.ref();rightId=this.ref(invalid?this.b:this.a);}
    return this.add({tag:tag as 'and',id:freshId(),leftId,rightId});
  }
  /** Assemble the requested closed expression family. @param tag Constructor. @param invalid Denial fixture. @returns Root. */
  private expression(tag:Expression['tag'],invalid:boolean):Id {
    if(tag==='signature_ref') return this.ref(invalid?'missing':this.a);
    if(tag==='field_ref') return this.add({tag,id:freshId(),targetId:invalid?'missing':this.field});
    if(tag==='variable_ref') return this.add({tag,id:freshId(),targetId:invalid?'missing':this.parameter.id});
    if(tag==='predicate_call') return this.add({tag,id:freshId(),predicateId:this.predicate,arguments:invalid?[]:[this.ref()]});
    if(tag==='all_quant'||tag==='some_quant') {
      const binder={id:freshId(),name:'local',signatureId:invalid?'missing':this.a};
      const reference=this.add({tag:'variable_ref',id:freshId(),targetId:binder.id});
      const bodyId=this.add({tag:'some_test',id:freshId(),operandId:reference});
      return this.add({tag,id:freshId(),binder,bodyId});
    }
    if((UNARY as readonly string[]).includes(tag)) return this.unary(tag,invalid);
    return this.binary(tag,invalid);
  }
  /** Build a complete module with a separately owned callee and selected constructor. @param tag Constructor. @param invalid Denial fixture. @returns Finite whole-module fixture. */
  build(tag:Expression['tag'],invalid=false):DraftModule {
    let bodyId=this.expression(tag,invalid);
    if(['signature_ref','field_ref','variable_ref','transpose','union','intersection','difference','join','product'].includes(tag)) bodyId=this.add({tag:'some_test',id:freshId(),operandId:bodyId});
    const calledBody=this.formula();
    return {...emptyModule(),signatures:[{tag:'signature',id:this.a,name:'A',multiplicity:'set'},{tag:'signature',id:this.b,name:'B',multiplicity:'set'}],fields:[{tag:'field',id:this.field,name:'field',ownerSignatureId:this.a,rangeColumns:[this.b],multiplicity:'set'},{tag:'field',id:this.wide,name:'wide',ownerSignatureId:this.a,rangeColumns:[this.a,this.a,this.a,this.a,this.a,this.a,this.a],multiplicity:'set'}],predicates:[{tag:'predicate',id:freshId(),name:'main',parameters:[this.parameter],bodyId},{tag:'predicate',id:this.predicate,name:'callee',parameters:[{...this.parameter,id:freshId(),name:'argument'}],bodyId:calledBody}],nodes:[...this.nodes]};
  }
}
