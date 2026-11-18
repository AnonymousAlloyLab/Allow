import {useEffect,useRef,useState,type FormEvent} from 'react';
import {accessApi,captchaMessage,newNonce} from './protocol';
interface Challenge {id:string;expiresAt:number}
/** Render the isolated manual-review intake without loading workspace code. @returns Request page. */
export function AccessRequest(){
  const [enabled,setEnabled]=useState(false),[siteKey,setSiteKey]=useState(''),[nonce,setNonce]=useState(newNonce),[token,setToken]=useState('');
  const [message,setMessage]=useState('Checking request availability…'),[busy,setBusy]=useState(false),[challenge,setChallenge]=useState<Challenge|null>(null),[requestId,setRequestId]=useState('');
  const frame=useRef<HTMLIFrameElement>(null),generation=useRef(0),locked=useRef(false);
  /** Give the opaque child public initialization only. @returns Nothing. */
  function initialize():void {frame.current?.contentWindow?.postMessage({kind:'initialize',nonce,siteKey},'*');}
  /** Retire all provider state after an attempt or reset. @returns Nothing. */
  function resetCaptcha():void {setToken('');setNonce(newNonce());}
  /** Start a new immutable request and invalidate pending responses. @returns Nothing. */
  function restart():void {generation.current++;locked.current=false;setBusy(false);setChallenge(null);setRequestId('');setMessage('');resetCaptcha();}
  /** Submit the validated form snapshot once, then lock its fields. @param event Form event. @returns Completion. */
  async function submit(event:FormEvent<HTMLFormElement>):Promise<void> {
    event.preventDefault();if(locked.current||!enabled||!token)return;const form=event.currentTarget;if(!form.reportValidity())return;
    const fields=new FormData(form),owner=++generation.current;locked.current=true;setBusy(true);setMessage('Sending your verification code…');
    try {const data=await accessApi('challenge',{name:formValue(fields,'name'),email:formValue(fields,'email'),organization:formValue(fields,'organization'),purpose:formValue(fields,'purpose'),acknowledged:fields.get('acknowledged')==='on',captchaToken:token});
      if(owner!==generation.current)return;if(data.status!=='CODE_SENT'||typeof data.challenge!=='string'||typeof data.expiresAt!=='number')throw new Error('Invalid service response.');
      setChallenge({id:data.challenge,expiresAt:data.expiresAt});setMessage('Check your email for an eight-digit code. Your request details are now locked.');
    }catch(error){if(owner===generation.current)setMessage(error instanceof Error?error.message:'Request unavailable.');}finally{if(owner===generation.current){locked.current=false;setBusy(false);resetCaptcha();}}
  }
  /** Verify only the bound challenge, never editable applicant fields. @param event Form event. @returns Completion. */
  async function verify(event:FormEvent<HTMLFormElement>):Promise<void> {
    event.preventDefault();if(locked.current||!challenge)return;const form=event.currentTarget;if(!form.reportValidity())return;
    const code=new FormData(form).get('code'),owner=++generation.current;locked.current=true;setBusy(true);setMessage('Verifying your email…');
    try {const data=await accessApi('verify',{challenge:challenge.id,code});if(owner!==generation.current)return;
      if(data.status!=='REQUESTED'||typeof data.requestId!=='string')throw new Error('Invalid service response.');setRequestId(data.requestId);setChallenge(null);setMessage('Your request is pending manual review. Email verification does not grant AI access.');
    }catch(error){if(owner===generation.current)setMessage(error instanceof Error?error.message:'Verification unavailable.');}finally{if(owner===generation.current){locked.current=false;setBusy(false);}}
  }
  useEffect(configure.bind(null,setEnabled,setSiteKey,setMessage,generation),[]);useEffect(listen.bind(null,frame,nonce,setToken,setMessage),[nonce]);
  return <main className="request-shell"><header><a className="wordmark" href="/">Allow <span>/ AI access</span></a><span className="review-label">MANUAL REVIEW</span></header><div className="request-layout"><aside><p className="eyebrow">A little context first</p><h1>Bring AI into your reasoning workflow.</h1><p>Tell us what you want to explore. Verify your email, and an operator will review your request.</p><ol><li>Share your intended use</li><li>Verify your email address</li><li>Wait for manual review</li></ol><p className="fine">Submitting a request does not enable AI, issue an access token, or change your workspace permissions.</p></aside><section className="request-card" aria-label="AI access request"><p className="step">{requestId?'REQUEST RECEIVED':challenge?'02 / VERIFY EMAIL':'01 / YOUR REQUEST'}</p><h2>{requestId?'Thank you for the context.':challenge?'One quick email check.':'Request AI access'}</h2><p role="status" aria-live="polite" className="notice">{message}</p>{requestId?<p className="receipt">Reference: <code>{requestId}</code></p>:challenge?<form onSubmit={verify}><label>Email verification code<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{8}" minLength={8} maxLength={8} required disabled={busy}/></label><p className="fine">Eight digits · expires {new Date(challenge.expiresAt).toLocaleTimeString()} · up to five attempts</p><button disabled={busy} type="submit">{busy?'Verifying…':'Verify and submit request'}</button><button className="secondary" disabled={busy} onClick={restart} type="button">Start over with new details</button></form>:<RequestForm disabled={!enabled||busy} busy={busy} token={token} submit={submit} frame={frame} nonce={nonce} siteKey={siteKey} initialize={initialize}/>}</section></div><footer>Human review. Explicit approval. Access stays in your control.</footer></main>;
}
interface FormProps {disabled:boolean;busy:boolean;token:string;submit:(event:FormEvent<HTMLFormElement>)=>Promise<void>;frame:React.RefObject<HTMLIFrameElement|null>;nonce:string;siteKey:string;initialize:()=>void}
/** Render browser validation and the isolated captcha surface. @param props Current intake state. @returns Applicant fields. */
function RequestForm(props:FormProps){return <form onSubmit={props.submit}><fieldset disabled={props.disabled}><div className="field-pair"><label>Name<input name="name" autoComplete="name" required maxLength={100}/></label><label>Organization <span>(optional)</span><input name="organization" autoComplete="organization" maxLength={160}/></label></div><label>Email address<input name="email" type="email" autoComplete="email" required maxLength={254}/></label><label>What would you use AI for?<textarea name="purpose" minLength={20} maxLength={2000} required rows={4} placeholder="Describe your workflow and the help you are looking for."/></label><p className="fine">20–2,000 characters. Line breaks and tabs become spaces. Please avoid sensitive information.</p><label className="acknowledgement"><input name="acknowledged" type="checkbox" required/><span>I understand this is a request for manual review and does not grant AI access.</span></label></fieldset>{props.siteKey&&!props.disabled&&<iframe key={props.nonce} ref={props.frame} title="Security check" src="/request-ai-access/captcha.html" sandbox="allow-scripts" referrerPolicy="no-referrer" onLoad={props.initialize}/>}<p className="fine">Security check by Google reCAPTCHA (space below is reserved for image challenges): <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Privacy</a> · <a href="https://policies.google.com/terms" target="_blank" rel="noopener noreferrer">Terms</a>.</p><button disabled={props.disabled||!props.token} type="submit">{props.busy?'Sending code…':'Send verification code'}<span aria-hidden="true"> ↗</span></button><p className="fine">We will email a verification code. Details are submitted for review only after you verify.</p></form>;}

  /** Load public configuration with response ownership. @param setEnabled Enablement consumer. @param setSiteKey Public key consumer. @param setMessage Status consumer. @param generation Response owner. @returns Cleanup. */
  function configure(setEnabled:(value:boolean)=>void,setSiteKey:(value:string)=>void,setMessage:(value:string)=>void,generation:React.RefObject<number>):()=>void {let live=true;void accessApi('config').then(loaded).catch(unavailable);return cleanup;
    /** Accept only the closed public configuration. @param data Response. @returns Nothing. */
    function loaded(data:Record<string,unknown>):void {if(!live)return;if(data.enabled===false&&Object.keys(data).join(',')==='enabled'){setMessage('Requests are not open yet. Email verification settings are pending.');return;}if(Object.keys(data).sort().join(',')!=='enabled,siteKey'||typeof data.enabled!=='boolean'||typeof data.siteKey!=='string'||!/^([A-Za-z0-9_-]{1,256})?$/.test(data.siteKey))return unavailable();setEnabled(data.enabled);setSiteKey(data.siteKey);setMessage(data.enabled?'':'Requests are not open yet. Email verification settings are pending.');}
    /** Explain disabled intake without suggesting submission succeeded. @returns Nothing. */
    function unavailable():void {if(live)setMessage('Request intake is unavailable. Please return later.');}
    /** Retire configuration response ownership. @returns Nothing. */
    function cleanup():void {live=false;generation.current++;}
  }
  /** Own one iframe conversation. @param frame Child reference. @param nonce Conversation identifier. @param setToken Token consumer. @param setMessage Status consumer. @returns Cleanup. */
  function listen(frame:React.RefObject<HTMLIFrameElement|null>,nonce:string,setToken:(value:string)=>void,setMessage:(value:string)=>void):()=>void {window.addEventListener('message',receive);return cleanup;
    /** Check opaque source, nonce and closed schema before accepting a token. @param event Child event. @returns Nothing. */
    function receive(event:MessageEvent):void {const data=captchaMessage(event,frame.current?.contentWindow??null,nonce);if(!data)return;setToken(data.kind==='token'?data.token!:'');if(data.kind==='error')setMessage('The security check is unavailable. Please try again later.');}
    /** Remove the retired conversation listener. @returns Nothing. */
    function cleanup():void {window.removeEventListener('message',receive);}
  }

/** Normalize user whitespace without truncation; reject remaining controls. @param fields Form snapshot. @param name Field name. @returns Normalized text. @throws Error Invalid control characters. */
function formValue(fields:FormData,name:string):string {const value=String(fields.get(name)??'').replace(/[\r\n\t]/g,' ');if(/[\u0000-\u001f\u007f]/.test(value))throw new Error('Please remove control characters from your details.');return value;}
