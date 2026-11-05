import {useState} from 'react';
import type {ChangeEvent} from 'react';
import type {Controller} from '../controller';
import type {AssistantState,Kind} from './types';
import type {AssistantSession} from './session';
import {useAssistant} from './useAssistant';
/** Render optional private assistance inside the document editor. @param props Controller and live session. @returns Assistant panel or hidden OFF surface. */
export function AssistantPanel(props:{controller:Controller;online:boolean}) {
  const {session,view}=useAssistant(props.controller,props.online),[intent,setIntent]=useState(''),[kind,setKind]=useState<Kind>('SOURCE_EDIT');
  /** Update explicitly reviewed intent. @param event Text input. @returns Nothing. */
  function changeIntent(event:ChangeEvent<HTMLTextAreaElement>):void {setIntent(event.target.value);}
  /** Select one bounded feature. @param event Select input. @returns Nothing. */
  function changeKind(event:ChangeEvent<HTMLSelectElement>):void {setKind(event.target.value==='EXPLANATION'?'EXPLANATION':'SOURCE_EDIT');}
  /** Prepare without provider disclosure. @returns Nothing. */
  function prepare():void {void session.prepare(kind,intent);}
  if(!view.config||view.config.mode==='OFF') return null;
  return <section className="document-assistant" aria-label="Model assistant"><h2>Model assistant</h2>
    <p>{view.config.mode==='FIXTURE'?'Deterministic fixture mode · no provider call.':'Private AI pilot · suggestions require review.'} Complete supported models only; no library retrieval.</p>
    <fieldset disabled={!props.online||view.busy}><label>Feature<select value={kind} onChange={changeKind}><option value="SOURCE_EDIT">Propose source edit</option><option value="EXPLANATION">Explain model</option></select></label>
      <label>Intent<textarea value={intent} onChange={changeIntent} maxLength={4096}/></label><button disabled={!intent.trim()||!!view.job&&['CREATING','AWAITING_DISCLOSURE','GENERATING','VERIFYING'].includes(view.job.status)} onClick={prepare}>Prepare payload</button></fieldset>
    <p role="status" aria-live="polite">{view.notice} {view.job?.status} {view.job?.code}</p>
    <AssistantReview view={view} session={session} online={props.online}/>
    {view.undo&&<button onClick={session.undo.bind(session)}>Undo AI edit</button>}
  </section>;
}
/** Render exact escaped disclosure and independently checked source review. @param props Assistant state and owner. @returns Review controls. */
export function AssistantReview(props:{view:AssistantState;session:AssistantSession;online:boolean}) {
  const {view,session}=props,job=view.job;if(!job) return null;
  return <div><p>Attempt {job.attempt} · expires {job.expiresAt}</p>
    {job.status==='AWAITING_DISCLOSURE'&&<><h3>Review exact provider payload</h3><p>Endpoint: https://api.openai.com/v1/responses · Model: {job.model} · Terms: {job.termsVersion}</p>
      <p>Names and comments are omitted from model context. Your intent can contain personal information. Structural anonymization does not guarantee confidentiality. Provider retention and training terms are governed by the reviewed operator terms above.</p>
      <pre tabIndex={0} aria-label="Exact provider payload">{job.payload}</pre><p>Payload SHA-256: {job.payloadHash}</p><button disabled={!props.online||view.busy} onClick={session.send.bind(session)}>Send this exact payload</button></>}
    {job.proposal&&<><h3>AI suggestion</h3><p>{job.proposal.explanation}</p><p>Validation projection: {job.proposal.projection}. Source checking is not proof of intended behavior.</p>
      {job.status==='REVIEW_READY'&&<><p>Applying the reprinted source omits comments. Undo AI edit restores your complete previous local draft.</p><SourceComparison view={view}/><button disabled={!props.online||view.busy} onClick={session.apply.bind(session)}>Apply to draft</button><p>Apply does not save. Use Save version separately.</p></>}
    </>}
    {['CREATING','AWAITING_DISCLOSURE','GENERATING','VERIFYING','REVIEW_READY','SUGGESTION'].includes(job.status)&&<button disabled={!props.online} onClick={session.cancel.bind(session)}>Cancel assistant request</button>}
  </div>;
}
/** Display exact source difference without executing or interpreting provider markup. @param props Current proposal and captured draft. @returns Before/after text. */
function SourceComparison(props:{view:AssistantState}) {
  const proposal=props.view.job?.proposal;
  return <div className="assistant-source-comparison"><div><h4>Before</h4><pre>{props.view.job?.beforeSource??'Exact source projection unavailable.'}</pre></div><div><h4>Proposed source</h4><pre>{proposal?.source}</pre></div></div>;
}
