/** Install the captcha-only classic bridge in an HTTP-sandboxed document. @returns Nothing. */
(function captchaBridge(){
  'use strict';
  let nonce='',siteKey='',widget=null,ready=false;
  /** Send only a bounded captcha result to the exact embedding parent. @param kind Message variant. @param token Optional provider token. @returns Nothing. */
  function send(kind,token){const data={kind:kind,nonce:nonce};if(kind==='token')data.token=token;parent.postMessage(data,location.origin);}
  /** Forward only bounded successful provider tokens. @param token Provider token. @returns Nothing. */
  function solved(token){if(typeof token==='string'&&token.length>0&&token.length<=4096)send('token',token);else send('error');}
  /** Retire a stale provider token. @returns Nothing. */
  function expired(){send('expired');}
  /** Report an inert generic provider failure. @returns Nothing. */
  function failed(){send('error');}
  /** Render after both verified initialization and provider readiness. @returns Nothing. */
  function render(){if(!ready||!siteKey)return;if(widget!==null){grecaptcha.reset(widget);return;}widget=grecaptcha.render('captcha',{sitekey:siteKey,size:'compact',callback:solved,'expired-callback':expired,'error-callback':failed});}
  /** Complete the provider load callback. @returns Nothing. */
  function loaded(){ready=true;render();}
  /** Receive no applicant data, only a checked public key and fresh nonce. @param event Parent message. @returns Nothing. */
  function initialize(event){
    if(event.source!==parent||event.origin!==location.origin)return;
    const data=event.data;if(!data||typeof data!=='object'||Array.isArray(data)||Object.keys(data).sort().join(',')!=='kind,nonce,siteKey')return;
    if(data.kind!=='initialize'||typeof data.nonce!=='string'||!/^[0-9a-f]{64}$/.test(data.nonce)||typeof data.siteKey!=='string'||!/^[A-Za-z0-9_-]{1,256}$/.test(data.siteKey))return;
    if(nonce===data.nonce)return;nonce=data.nonce;siteKey=data.siteKey;
    if(!document.getElementById('provider')){const script=document.createElement('script');script.id='provider';script.src='https://www.google.com/recaptcha/api.js?onload=allowCaptchaLoaded&render=explicit';script.async=true;script.defer=true;script.onerror=failed;document.head.appendChild(script);}else render();
  }
  window.allowCaptchaLoaded=loaded;window.addEventListener('message',initialize);
})();
