interface ObserverDetails {readonly droppedEntriesCount?:number}
interface ResourceRecord {readonly path:string;readonly start:number;readonly duration:number;readonly responseStatus:number|string}
const LIMIT=4096;

/** Capture browser resource entries continuously without touching application fetch behavior. */
export class ResourceCapture {
  private readonly entries:PerformanceResourceTiming[]=[];
  private observer:PerformanceObserver|null=null;
  private bufferFull=false;
  private overflow=false;
  private dropped=0;
  private droppedFieldObserved=false;
  private supported=false;
  private statusFieldSupported=false;
  /** Start before app setup and request already buffered entries. */
  constructor() {
    this.statusFieldSupported=typeof PerformanceResourceTiming!=='undefined'&&'responseStatus' in PerformanceResourceTiming.prototype;
    this.supported=typeof PerformanceObserver!=='undefined'&&PerformanceObserver.supportedEntryTypes.includes('resource');
    if(!this.supported) return;
    performance.addEventListener('resourcetimingbufferfull',this.full.bind(this));
    performance.setResourceTimingBufferSize(LIMIT);
    try {
      this.observer=new PerformanceObserver(this.capture.bind(this));
      this.observer.observe({type:'resource',buffered:true});
    } catch {this.supported=false;this.observer=null;}
  }
  /** Mark the browser resource timing buffer overflow. @returns Nothing. */
  private full():void {this.bufferFull=true;}
  /** Retain bounded entries and browser-reported observer drops. @param list Delivered entries. @param observer Owning observer. @param details Browser callback metadata. @returns Nothing. */
  private capture(list:PerformanceObserverEntryList,observer:PerformanceObserver,details?:ObserverDetails):void {
    void observer;
    if(typeof details?.droppedEntriesCount==='number') {this.droppedFieldObserved=true;this.dropped+=details.droppedEntriesCount;}
    for(const entry of list.getEntries()) {
      if(this.entries.length>=LIMIT) {this.overflow=true;continue;}
      this.entries.push(entry as PerformanceResourceTiming);
    }
  }
  /** Drain queued observer records outside timing callbacks. @returns Nothing. */
  private drain():void {
    for(const entry of this.observer?.takeRecords()??[]) {
      if(this.entries.length>=LIMIT) {this.overflow=true;continue;}
      this.entries.push(entry as PerformanceResourceTiming);
    }
  }
  /** Return currently delivered resource records, redacted outside timed event callbacks. @returns Redacted entries. */
  records():ResourceRecord[] {this.drain();return this.entries.map(redact);}
  /** Report whether complete, supported and bounded resource evidence exists. @returns Coverage metadata. */
  coverage():{complete:boolean;[key:string]:unknown} {
    this.drain();const unknown=this.entries.filter(unknownStatus).length;
    return {supported:this.supported,statusFieldSupported:this.statusFieldSupported,droppedFieldObserved:this.droppedFieldObserved,
      browserBufferFull:this.bufferFull,observerOverflow:this.overflow,droppedEntries:this.dropped,unknownStatusCount:unknown,entryCount:this.entries.length,limit:LIMIT,
      complete:this.supported&&this.statusFieldSupported&&this.droppedFieldObserved&&!this.bufferFull&&!this.overflow&&this.dropped===0&&unknown===0};
  }
  /** Find observed validation requests after the final dispatch. @param after Monotonic dispatch time. @returns Matching redacted entries. */
  validations(after:number):ResourceRecord[] {return this.records().filter(isFinalValidation.bind(null,after));}
}
/** Redact resource paths and treat unavailable or zero status as unknown. @param entry Browser resource. @returns Safe evidence. */
function redact(entry:PerformanceResourceTiming):ResourceRecord {
  const path=new URL(entry.name,location.href).pathname.replace(/\/documents\/[^/]+/,'/documents/[redacted]');
  return {path,start:entry.startTime,duration:entry.duration,responseStatus:entry.responseStatus>0?entry.responseStatus:'UNKNOWN_OR_ERROR'};
}
/** Detect missing or zero HTTP status. @param entry Browser resource. @returns Whether status is unknown. */
function unknownStatus(entry:PerformanceResourceTiming):boolean {return !(entry.responseStatus>0);}
/** Match a final generation validation after dispatch. @param after Dispatch timestamp. @param entry Redacted resource. @returns Whether candidate. */
function isFinalValidation(after:number,entry:ResourceRecord):boolean {return entry.path.endsWith('/validate')&&entry.start>=after;}

/** Start capture at test entry module initialization, before application mounting. */
export const resourceCapture=new ResourceCapture();
