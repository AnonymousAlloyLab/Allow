import {expect,test} from 'vitest';
import {dragEndNotice,type Gesture} from './gesture';

/** Keep a completed drop notice and explain unfinished gestures. @returns Nothing. */
function finishFeedback():void {
  const gesture:Gesture={kind:'node',nonce:'nonce',snapshot:'snapshot',source:'node'};
  expect(dragEndNotice(null,null)).toBeNull();
  expect(dragEndNotice(gesture,{kind:'incompatible',message:'Expected formula.'})).toBe('Expected formula. Draft unchanged.');
  expect(dragEndNotice(gesture,{kind:'unresolved',message:'Unresolved.'})).toContain('canceled');
  expect(dragEndNotice(gesture,null)).toContain('draft unchanged');
}
test('drag completion reports rejection or cancellation without overwriting a committed drop',finishFeedback);
