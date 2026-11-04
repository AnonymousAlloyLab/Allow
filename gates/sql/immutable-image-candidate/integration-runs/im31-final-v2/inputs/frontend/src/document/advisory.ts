/** One content generation's diagnostic-only operation. */
export interface AdvisoryTask {
  readonly key:string;
  /** Run exact draft validation without committing. @param signal Lifetime/deadline cancellation. @returns Completion. */
  readonly run:(signal:AbortSignal)=>Promise<void>;
}
/** Debounce latest content, serialize validation and never retry unchanged availability failures. */
export class AdvisoryValidator {
  private latest:AdvisoryTask|null=null;
  private active:AbortController|null=null;
  private activeKey:string|null=null;
  private attempted:string|null=null;
  private timer:ReturnType<typeof setTimeout>|null=null;
  private disposed=false;
  /** Queue latest content or an explicit manual request. @param task Complete candidate. @param manual Immediate intentional validation. @returns Nothing. */
  request(task:AdvisoryTask,manual=false):void {
    if(this.disposed||task.key===this.activeKey||(!manual&&task.key===this.attempted)) return;
    this.latest=task;
    if(this.timer) clearTimeout(this.timer);
    if(!this.active) this.timer=setTimeout(this.begin.bind(this),manual?0:350);
  }
  /** Remove queued work when the latest draft becomes incomplete. @returns Nothing. */
  clearPending():void {this.latest=null;if(this.timer) clearTimeout(this.timer);this.timer=null;}
  /** End owned waits on unmount/authority change. @returns Nothing. */
  dispose():void {this.disposed=true;this.clearPending();this.active?.abort('view closed');}
  /** Start at most one request and charge its content generation once. @returns Nothing. */
  private begin():void {
    this.timer=null;
    if(this.disposed||this.active||!this.latest) return;
    const task=this.latest,controller=new AbortController();
    this.latest=null;this.active=controller;this.activeKey=task.key;this.attempted=task.key;
    void this.execute(task,controller);
  }
  /** Bound an advisory HTTP operation and settle its pending successor. @param task Frozen diagnostic operation. @param controller Session lifetime. @returns Completion. */
  private async execute(task:AdvisoryTask,controller:AbortController):Promise<void> {
    const timeout=setTimeout(this.abort.bind(this,controller),15000);
    try {await task.run(controller.signal);} catch { /* Availability never automatically retries unchanged input. */ }
    finally {
      clearTimeout(timeout);this.active=null;this.activeKey=null;
      if(!this.disposed&&this.latest) this.timer=setTimeout(this.begin.bind(this),350);
    }
  }
  /** Abort only the advisory client wait after its bounded deadline. @param controller Current operation. @returns Nothing. */
  private abort(controller:AbortController):void {controller.abort('advisory deadline');}
}
