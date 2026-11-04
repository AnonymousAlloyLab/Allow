/* Minimal built-in runtime declarations for this test, whose project does not install @types/node. */
declare module 'node:crypto' {
  interface FixtureHash {
    /** Add exact benchmark input bytes. @param bytes Text or byte input. @returns Same digest builder. */
    update(bytes:string|Uint8Array):FixtureHash;
    /** Finish the fixture digest. @param encoding Required hex encoding. @returns Lowercase SHA256 text. */
    digest(encoding:'hex'):string;
  }
  /** Construct a SHA256 digest builder. @param algorithm Required hash algorithm. @returns Streaming digest. */
  export function createHash(algorithm:'sha256'):FixtureHash;
}
declare module 'node:fs' {
  /** Read exact source bytes for evidence hashing. @param path Existing file path. @returns Byte buffer. */
  export function readFileSync(path:string):Uint8Array;
  /** Read explicit UTF8 system metadata or contracts. @param path Existing file path. @param encoding UTF8 decoding. @returns Decoded file contents. */
  export function readFileSync(path:string,encoding:'utf8'):string;
  /** Persist generated JSON evidence. @param path Output path. @param data Exact UTF8 text. @returns Nothing. */
  export function writeFileSync(path:string,data:string):void;
}
declare module 'node:os' {
  /** Inventory exposed processors. @returns CPU model records. */
  export function cpus():readonly {readonly model:string}[];
  /** Read exposed system memory. @returns Reported bytes. */
  export function totalmem():number;
  /** Read operating system family. @returns Runtime platform. */
  export function platform():string;
  /** Read kernel release. @returns Release text. */
  export function release():string;
  /** Read native runtime architecture. @returns Architecture text. */
  export function arch():string;
  /** Read reference machine name. @returns Host identifier. */
  export function hostname():string;
}
declare module 'node:path' {
  /** Resolve the test file directory. @param path Absolute source path. @returns Parent directory. */
  export function dirname(path:string):string;
  /** Resolve fixed workspace-relative artifact paths. @param paths Path components. @returns Absolute path. */
  export function resolve(...paths:string[]):string;
}
declare module 'node:url' {
  /** Decode the local test module URL. @param url Module URL. @returns Filesystem path. */
  export function fileURLToPath(url:string):string;
}
declare module 'node:perf_hooks' {
  export const performance:Performance;
}
