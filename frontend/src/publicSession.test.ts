import {afterEach,expect,test,vi} from 'vitest';
import {createSession,resumeSession,endSession,readToken,writeToken} from './publicSession';
const TOKEN='a'.repeat(43);
/** Remove isolated browser stubs. @returns Nothing. */
function cleanup():void {vi.unstubAllGlobals();}
afterEach(cleanup);
/** Enroll using only the fixed JSON request and validate returned capability. @returns Completion. */
async function enrollment():Promise<void> {
  const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({token:TOKEN,expiresAt:'2030-01-01T00:00:00Z',lifetimeSeconds:1800}),{status:201}));
  vi.stubGlobal('fetch',fetcher);const session=await createSession();expect(session.token).toBe(TOKEN);
  expect(fetcher.mock.calls[0][0]).toBe('/api/public/workspaces');expect(fetcher.mock.calls[0][1]).toMatchObject({method:'POST',body:'{}',credentials:'omit'});
}
/** Keep transient failures distinct from expired authority and support explicit end. @returns Completion. */
async function recovery():Promise<void> {
  const fetcher=vi.fn().mockResolvedValueOnce(new Response('{}',{status:401})).mockResolvedValueOnce(new Response('{}',{status:503})).mockResolvedValueOnce(new Response(null,{status:204}));
  vi.stubGlobal('fetch',fetcher);expect(await resumeSession(TOKEN)).toBeNull();await expect(resumeSession(TOKEN)).rejects.toThrow('unavailable');await expect(endSession(TOKEN)).resolves.toBeUndefined();
}
/** Avoid alternate persistence when tab storage is unavailable. @returns Nothing. */
function storageFailure():void {
  const storage={getItem:vi.fn(denied),setItem:vi.fn(denied),removeItem:vi.fn(denied)};vi.stubGlobal('sessionStorage',storage);
  expect(readToken()).toBe('');expect(writeToken(TOKEN)).toBe(false);
}
/** Simulate a blocked browser storage API. @returns Never returns. @throws Error storage denial. */
function denied():never {throw new Error('blocked');}
test('enrollment sends closed request and returns checked authority',enrollment);
test('expiration, availability and end remain distinct',recovery);
test('storage failure does not write other storage',storageFailure);
