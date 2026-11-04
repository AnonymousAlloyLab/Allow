var W8=Object.defineProperty;var F8=(r,d,f)=>d in r?W8(r,d,{enumerable:!0,configurable:!0,writable:!0,value:f}):r[d]=f;var n0=(r,d,f)=>F8(r,typeof d!="symbol"?d+"":d,f);(function(){const d=document.createElement("link").relList;if(d&&d.supports&&d.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))u(s);new MutationObserver(s=>{for(const c of s)if(c.type==="childList")for(const v of c.addedNodes)v.tagName==="LINK"&&v.rel==="modulepreload"&&u(v)}).observe(document,{childList:!0,subtree:!0});function f(s){const c={};return s.integrity&&(c.integrity=s.integrity),s.referrerPolicy&&(c.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?c.credentials="include":s.crossOrigin==="anonymous"?c.credentials="omit":c.credentials="same-origin",c}function u(s){if(s.ep)return;s.ep=!0;const c=f(s);fetch(s.href,c)}})();var Pi={exports:{}},Va={};/**
 * @license React
 * react-jsx-runtime.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Tc;function P8(){if(Tc)return Va;Tc=1;var r=Symbol.for("react.transitional.element"),d=Symbol.for("react.fragment");function f(u,s,c){var v=null;if(c!==void 0&&(v=""+c),s.key!==void 0&&(v=""+s.key),"key"in s){c={};for(var p in s)p!=="key"&&(c[p]=s[p])}else c=s;return s=c.ref,{$$typeof:r,type:u,key:v,ref:s!==void 0?s:null,props:c}}return Va.Fragment=d,Va.jsx=f,Va.jsxs=f,Va}var jc;function ng(){return jc||(jc=1,Pi.exports=P8()),Pi.exports}var I=ng(),nf={exports:{}},Ka={},ef={exports:{}},tf={};/**
 * @license React
 * scheduler.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Oc;function eg(){return Oc||(Oc=1,(function(r){function d(O,M){var L=O.length;O.push(M);n:for(;0<L;){var s0=L-1>>>1,I0=O[s0];if(0<s(I0,M))O[s0]=M,O[L]=I0,L=s0;else break n}}function f(O){return O.length===0?null:O[0]}function u(O){if(O.length===0)return null;var M=O[0],L=O.pop();if(L!==M){O[0]=L;n:for(var s0=0,I0=O.length,y=I0>>>1;s0<y;){var C=2*(s0+1)-1,R=O[C],H=C+1,X=O[H];if(0>s(R,L))H<I0&&0>s(X,R)?(O[s0]=X,O[H]=L,s0=H):(O[s0]=R,O[C]=L,s0=C);else if(H<I0&&0>s(X,L))O[s0]=X,O[H]=L,s0=H;else break n}}return M}function s(O,M){var L=O.sortIndex-M.sortIndex;return L!==0?L:O.id-M.id}if(r.unstable_now=void 0,typeof performance=="object"&&typeof performance.now=="function"){var c=performance;r.unstable_now=function(){return c.now()}}else{var v=Date,p=v.now();r.unstable_now=function(){return v.now()-p}}var A=[],S=[],N=1,U=null,Y=3,u0=!1,y0=!1,T0=!1,Q0=!1,C0=typeof setTimeout=="function"?setTimeout:null,jn=typeof clearTimeout=="function"?clearTimeout:null,Y0=typeof setImmediate<"u"?setImmediate:null;function mn(O){for(var M=f(S);M!==null;){if(M.callback===null)u(S);else if(M.startTime<=O)u(S),M.sortIndex=M.expirationTime,d(A,M);else break;M=f(S)}}function Nn(O){if(T0=!1,mn(O),!y0)if(f(A)!==null)y0=!0,K0||(K0=!0,k0());else{var M=f(S);M!==null&&On(Nn,M.startTime-O)}}var K0=!1,F=-1,J0=5,Mn=-1;function ft(){return Q0?!0:!(r.unstable_now()-Mn<J0)}function Un(){if(Q0=!1,K0){var O=r.unstable_now();Mn=O;var M=!0;try{n:{y0=!1,T0&&(T0=!1,jn(F),F=-1),u0=!0;var L=Y;try{e:{for(mn(O),U=f(A);U!==null&&!(U.expirationTime>O&&ft());){var s0=U.callback;if(typeof s0=="function"){U.callback=null,Y=U.priorityLevel;var I0=s0(U.expirationTime<=O);if(O=r.unstable_now(),typeof I0=="function"){U.callback=I0,mn(O),M=!0;break e}U===f(A)&&u(A),mn(O)}else u(A);U=f(A)}if(U!==null)M=!0;else{var y=f(S);y!==null&&On(Nn,y.startTime-O),M=!1}}break n}finally{U=null,Y=L,u0=!1}M=void 0}}finally{M?k0():K0=!1}}}var k0;if(typeof Y0=="function")k0=function(){Y0(Un)};else if(typeof MessageChannel<"u"){var we=new MessageChannel,Yn=we.port2;we.port1.onmessage=Un,k0=function(){Yn.postMessage(null)}}else k0=function(){C0(Un,0)};function On(O,M){F=C0(function(){O(r.unstable_now())},M)}r.unstable_IdlePriority=5,r.unstable_ImmediatePriority=1,r.unstable_LowPriority=4,r.unstable_NormalPriority=3,r.unstable_Profiling=null,r.unstable_UserBlockingPriority=2,r.unstable_cancelCallback=function(O){O.callback=null},r.unstable_forceFrameRate=function(O){0>O||125<O?console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"):J0=0<O?Math.floor(1e3/O):5},r.unstable_getCurrentPriorityLevel=function(){return Y},r.unstable_next=function(O){switch(Y){case 1:case 2:case 3:var M=3;break;default:M=Y}var L=Y;Y=M;try{return O()}finally{Y=L}},r.unstable_requestPaint=function(){Q0=!0},r.unstable_runWithPriority=function(O,M){switch(O){case 1:case 2:case 3:case 4:case 5:break;default:O=3}var L=Y;Y=O;try{return M()}finally{Y=L}},r.unstable_scheduleCallback=function(O,M,L){var s0=r.unstable_now();switch(typeof L=="object"&&L!==null?(L=L.delay,L=typeof L=="number"&&0<L?s0+L:s0):L=s0,O){case 1:var I0=-1;break;case 2:I0=250;break;case 5:I0=1073741823;break;case 4:I0=1e4;break;default:I0=5e3}return I0=L+I0,O={id:N++,callback:M,priorityLevel:O,startTime:L,expirationTime:I0,sortIndex:-1},L>s0?(O.sortIndex=L,d(S,O),f(A)===null&&O===f(S)&&(T0?(jn(F),F=-1):T0=!0,On(Nn,L-s0))):(O.sortIndex=I0,d(A,O),y0||u0||(y0=!0,K0||(K0=!0,k0()))),O},r.unstable_shouldYield=ft,r.unstable_wrapCallback=function(O){var M=Y;return function(){var L=Y;Y=M;try{return O.apply(this,arguments)}finally{Y=L}}}})(tf)),tf}var zc;function tg(){return zc||(zc=1,ef.exports=eg()),ef.exports}var af={exports:{}},Q={};/**
 * @license React
 * react.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Dc;function ag(){if(Dc)return Q;Dc=1;var r=Symbol.for("react.transitional.element"),d=Symbol.for("react.portal"),f=Symbol.for("react.fragment"),u=Symbol.for("react.strict_mode"),s=Symbol.for("react.profiler"),c=Symbol.for("react.consumer"),v=Symbol.for("react.context"),p=Symbol.for("react.forward_ref"),A=Symbol.for("react.suspense"),S=Symbol.for("react.memo"),N=Symbol.for("react.lazy"),U=Symbol.for("react.activity"),Y=Symbol.iterator;function u0(y){return y===null||typeof y!="object"?null:(y=Y&&y[Y]||y["@@iterator"],typeof y=="function"?y:null)}var y0={isMounted:function(){return!1},enqueueForceUpdate:function(){},enqueueReplaceState:function(){},enqueueSetState:function(){}},T0=Object.assign,Q0={};function C0(y,C,R){this.props=y,this.context=C,this.refs=Q0,this.updater=R||y0}C0.prototype.isReactComponent={},C0.prototype.setState=function(y,C){if(typeof y!="object"&&typeof y!="function"&&y!=null)throw Error("takes an object of state variables to update or a function which returns an object of state variables.");this.updater.enqueueSetState(this,y,C,"setState")},C0.prototype.forceUpdate=function(y){this.updater.enqueueForceUpdate(this,y,"forceUpdate")};function jn(){}jn.prototype=C0.prototype;function Y0(y,C,R){this.props=y,this.context=C,this.refs=Q0,this.updater=R||y0}var mn=Y0.prototype=new jn;mn.constructor=Y0,T0(mn,C0.prototype),mn.isPureReactComponent=!0;var Nn=Array.isArray;function K0(){}var F={H:null,A:null,T:null,S:null},J0=Object.prototype.hasOwnProperty;function Mn(y,C,R){var H=R.ref;return{$$typeof:r,type:y,key:C,ref:H!==void 0?H:null,props:R}}function ft(y,C){return Mn(y.type,C,y.props)}function Un(y){return typeof y=="object"&&y!==null&&y.$$typeof===r}function k0(y){var C={"=":"=0",":":"=2"};return"$"+y.replace(/[=:]/g,function(R){return C[R]})}var we=/\/+/g;function Yn(y,C){return typeof y=="object"&&y!==null&&y.key!=null?k0(""+y.key):C.toString(36)}function On(y){switch(y.status){case"fulfilled":return y.value;case"rejected":throw y.reason;default:switch(typeof y.status=="string"?y.then(K0,K0):(y.status="pending",y.then(function(C){y.status==="pending"&&(y.status="fulfilled",y.value=C)},function(C){y.status==="pending"&&(y.status="rejected",y.reason=C)})),y.status){case"fulfilled":return y.value;case"rejected":throw y.reason}}throw y}function O(y,C,R,H,X){var K=typeof y;(K==="undefined"||K==="boolean")&&(y=null);var d0=!1;if(y===null)d0=!0;else switch(K){case"bigint":case"string":case"number":d0=!0;break;case"object":switch(y.$$typeof){case r:case d:d0=!0;break;case N:return d0=y._init,O(d0(y._payload),C,R,H,X)}}if(d0)return X=X(y),d0=H===""?"."+Yn(y,0):H,Nn(X)?(R="",d0!=null&&(R=d0.replace(we,"$&/")+"/"),O(X,C,R,"",function(Pt){return Pt})):X!=null&&(Un(X)&&(X=ft(X,R+(X.key==null||y&&y.key===X.key?"":(""+X.key).replace(we,"$&/")+"/")+d0)),C.push(X)),1;d0=0;var X0=H===""?".":H+":";if(Nn(y))for(var x0=0;x0<y.length;x0++)H=y[x0],K=X0+Yn(H,x0),d0+=O(H,C,R,K,X);else if(x0=u0(y),typeof x0=="function")for(y=x0.call(y),x0=0;!(H=y.next()).done;)H=H.value,K=X0+Yn(H,x0++),d0+=O(H,C,R,K,X);else if(K==="object"){if(typeof y.then=="function")return O(On(y),C,R,H,X);throw C=String(y),Error("Objects are not valid as a React child (found: "+(C==="[object Object]"?"object with keys {"+Object.keys(y).join(", ")+"}":C)+"). If you meant to render a collection of children, use an array instead.")}return d0}function M(y,C,R){if(y==null)return y;var H=[],X=0;return O(y,H,"","",function(K){return C.call(R,K,X++)}),H}function L(y){if(y._status===-1){var C=y._result;C=C(),C.then(function(R){(y._status===0||y._status===-1)&&(y._status=1,y._result=R)},function(R){(y._status===0||y._status===-1)&&(y._status=2,y._result=R)}),y._status===-1&&(y._status=0,y._result=C)}if(y._status===1)return y._result.default;throw y._result}var s0=typeof reportError=="function"?reportError:function(y){if(typeof window=="object"&&typeof window.ErrorEvent=="function"){var C=new window.ErrorEvent("error",{bubbles:!0,cancelable:!0,message:typeof y=="object"&&y!==null&&typeof y.message=="string"?String(y.message):String(y),error:y});if(!window.dispatchEvent(C))return}else if(typeof process=="object"&&typeof process.emit=="function"){process.emit("uncaughtException",y);return}console.error(y)},I0={map:M,forEach:function(y,C,R){M(y,function(){C.apply(this,arguments)},R)},count:function(y){var C=0;return M(y,function(){C++}),C},toArray:function(y){return M(y,function(C){return C})||[]},only:function(y){if(!Un(y))throw Error("React.Children.only expected to receive a single React element child.");return y}};return Q.Activity=U,Q.Children=I0,Q.Component=C0,Q.Fragment=f,Q.Profiler=s,Q.PureComponent=Y0,Q.StrictMode=u,Q.Suspense=A,Q.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE=F,Q.__COMPILER_RUNTIME={__proto__:null,c:function(y){return F.H.useMemoCache(y)}},Q.cache=function(y){return function(){return y.apply(null,arguments)}},Q.cacheSignal=function(){return null},Q.cloneElement=function(y,C,R){if(y==null)throw Error("The argument must be a React element, but you passed "+y+".");var H=T0({},y.props),X=y.key;if(C!=null)for(K in C.key!==void 0&&(X=""+C.key),C)!J0.call(C,K)||K==="key"||K==="__self"||K==="__source"||K==="ref"&&C.ref===void 0||(H[K]=C[K]);var K=arguments.length-2;if(K===1)H.children=R;else if(1<K){for(var d0=Array(K),X0=0;X0<K;X0++)d0[X0]=arguments[X0+2];H.children=d0}return Mn(y.type,X,H)},Q.createContext=function(y){return y={$$typeof:v,_currentValue:y,_currentValue2:y,_threadCount:0,Provider:null,Consumer:null},y.Provider=y,y.Consumer={$$typeof:c,_context:y},y},Q.createElement=function(y,C,R){var H,X={},K=null;if(C!=null)for(H in C.key!==void 0&&(K=""+C.key),C)J0.call(C,H)&&H!=="key"&&H!=="__self"&&H!=="__source"&&(X[H]=C[H]);var d0=arguments.length-2;if(d0===1)X.children=R;else if(1<d0){for(var X0=Array(d0),x0=0;x0<d0;x0++)X0[x0]=arguments[x0+2];X.children=X0}if(y&&y.defaultProps)for(H in d0=y.defaultProps,d0)X[H]===void 0&&(X[H]=d0[H]);return Mn(y,K,X)},Q.createRef=function(){return{current:null}},Q.forwardRef=function(y){return{$$typeof:p,render:y}},Q.isValidElement=Un,Q.lazy=function(y){return{$$typeof:N,_payload:{_status:-1,_result:y},_init:L}},Q.memo=function(y,C){return{$$typeof:S,type:y,compare:C===void 0?null:C}},Q.startTransition=function(y){var C=F.T,R={};F.T=R;try{var H=y(),X=F.S;X!==null&&X(R,H),typeof H=="object"&&H!==null&&typeof H.then=="function"&&H.then(K0,s0)}catch(K){s0(K)}finally{C!==null&&R.types!==null&&(C.types=R.types),F.T=C}},Q.unstable_useCacheRefresh=function(){return F.H.useCacheRefresh()},Q.use=function(y){return F.H.use(y)},Q.useActionState=function(y,C,R){return F.H.useActionState(y,C,R)},Q.useCallback=function(y,C){return F.H.useCallback(y,C)},Q.useContext=function(y){return F.H.useContext(y)},Q.useDebugValue=function(){},Q.useDeferredValue=function(y,C){return F.H.useDeferredValue(y,C)},Q.useEffect=function(y,C){return F.H.useEffect(y,C)},Q.useEffectEvent=function(y){return F.H.useEffectEvent(y)},Q.useId=function(){return F.H.useId()},Q.useImperativeHandle=function(y,C,R){return F.H.useImperativeHandle(y,C,R)},Q.useInsertionEffect=function(y,C){return F.H.useInsertionEffect(y,C)},Q.useLayoutEffect=function(y,C){return F.H.useLayoutEffect(y,C)},Q.useMemo=function(y,C){return F.H.useMemo(y,C)},Q.useOptimistic=function(y,C){return F.H.useOptimistic(y,C)},Q.useReducer=function(y,C,R){return F.H.useReducer(y,C,R)},Q.useRef=function(y){return F.H.useRef(y)},Q.useState=function(y){return F.H.useState(y)},Q.useSyncExternalStore=function(y,C,R){return F.H.useSyncExternalStore(y,C,R)},Q.useTransition=function(){return F.H.useTransition()},Q.version="19.2.9",Q}var Cc;function If(){return Cc||(Cc=1,af.exports=ag()),af.exports}var rf={exports:{}},G0={};/**
 * @license React
 * react-dom.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Nc;function rg(){if(Nc)return G0;Nc=1;var r=If();function d(A){var S="https://react.dev/errors/"+A;if(1<arguments.length){S+="?args[]="+encodeURIComponent(arguments[1]);for(var N=2;N<arguments.length;N++)S+="&args[]="+encodeURIComponent(arguments[N])}return"Minified React error #"+A+"; visit "+S+" for the full message or use the non-minified dev environment for full errors and additional helpful warnings."}function f(){}var u={d:{f,r:function(){throw Error(d(522))},D:f,C:f,L:f,m:f,X:f,S:f,M:f},p:0,findDOMNode:null},s=Symbol.for("react.portal");function c(A,S,N){var U=3<arguments.length&&arguments[3]!==void 0?arguments[3]:null;return{$$typeof:s,key:U==null?null:""+U,children:A,containerInfo:S,implementation:N}}var v=r.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;function p(A,S){if(A==="font")return"";if(typeof S=="string")return S==="use-credentials"?S:""}return G0.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE=u,G0.createPortal=function(A,S){var N=2<arguments.length&&arguments[2]!==void 0?arguments[2]:null;if(!S||S.nodeType!==1&&S.nodeType!==9&&S.nodeType!==11)throw Error(d(299));return c(A,S,null,N)},G0.flushSync=function(A){var S=v.T,N=u.p;try{if(v.T=null,u.p=2,A)return A()}finally{v.T=S,u.p=N,u.d.f()}},G0.preconnect=function(A,S){typeof A=="string"&&(S?(S=S.crossOrigin,S=typeof S=="string"?S==="use-credentials"?S:"":void 0):S=null,u.d.C(A,S))},G0.prefetchDNS=function(A){typeof A=="string"&&u.d.D(A)},G0.preinit=function(A,S){if(typeof A=="string"&&S&&typeof S.as=="string"){var N=S.as,U=p(N,S.crossOrigin),Y=typeof S.integrity=="string"?S.integrity:void 0,u0=typeof S.fetchPriority=="string"?S.fetchPriority:void 0;N==="style"?u.d.S(A,typeof S.precedence=="string"?S.precedence:void 0,{crossOrigin:U,integrity:Y,fetchPriority:u0}):N==="script"&&u.d.X(A,{crossOrigin:U,integrity:Y,fetchPriority:u0,nonce:typeof S.nonce=="string"?S.nonce:void 0})}},G0.preinitModule=function(A,S){if(typeof A=="string")if(typeof S=="object"&&S!==null){if(S.as==null||S.as==="script"){var N=p(S.as,S.crossOrigin);u.d.M(A,{crossOrigin:N,integrity:typeof S.integrity=="string"?S.integrity:void 0,nonce:typeof S.nonce=="string"?S.nonce:void 0})}}else S==null&&u.d.M(A)},G0.preload=function(A,S){if(typeof A=="string"&&typeof S=="object"&&S!==null&&typeof S.as=="string"){var N=S.as,U=p(N,S.crossOrigin);u.d.L(A,N,{crossOrigin:U,integrity:typeof S.integrity=="string"?S.integrity:void 0,nonce:typeof S.nonce=="string"?S.nonce:void 0,type:typeof S.type=="string"?S.type:void 0,fetchPriority:typeof S.fetchPriority=="string"?S.fetchPriority:void 0,referrerPolicy:typeof S.referrerPolicy=="string"?S.referrerPolicy:void 0,imageSrcSet:typeof S.imageSrcSet=="string"?S.imageSrcSet:void 0,imageSizes:typeof S.imageSizes=="string"?S.imageSizes:void 0,media:typeof S.media=="string"?S.media:void 0})}},G0.preloadModule=function(A,S){if(typeof A=="string")if(S){var N=p(S.as,S.crossOrigin);u.d.m(A,{as:typeof S.as=="string"&&S.as!=="script"?S.as:void 0,crossOrigin:N,integrity:typeof S.integrity=="string"?S.integrity:void 0})}else u.d.m(A)},G0.requestFormReset=function(A){u.d.r(A)},G0.unstable_batchedUpdates=function(A,S){return A(S)},G0.useFormState=function(A,S,N){return v.H.useFormState(A,S,N)},G0.useFormStatus=function(){return v.H.useHostTransitionStatus()},G0.version="19.2.9",G0}var Mc;function dg(){if(Mc)return rf.exports;Mc=1;function r(){if(!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__>"u"||typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE!="function"))try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(r)}catch(d){console.error(d)}}return r(),rf.exports=rg(),rf.exports}/**
 * @license React
 * react-dom-client.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Uc;function lg(){if(Uc)return Ka;Uc=1;var r=tg(),d=If(),f=dg();function u(n){var e="https://react.dev/errors/"+n;if(1<arguments.length){e+="?args[]="+encodeURIComponent(arguments[1]);for(var t=2;t<arguments.length;t++)e+="&args[]="+encodeURIComponent(arguments[t])}return"Minified React error #"+n+"; visit "+e+" for the full message or use the non-minified dev environment for full errors and additional helpful warnings."}function s(n){return!(!n||n.nodeType!==1&&n.nodeType!==9&&n.nodeType!==11)}function c(n){var e=n,t=n;if(n.alternate)for(;e.return;)e=e.return;else{n=e;do e=n,(e.flags&4098)!==0&&(t=e.return),n=e.return;while(n)}return e.tag===3?t:null}function v(n){if(n.tag===13){var e=n.memoizedState;if(e===null&&(n=n.alternate,n!==null&&(e=n.memoizedState)),e!==null)return e.dehydrated}return null}function p(n){if(n.tag===31){var e=n.memoizedState;if(e===null&&(n=n.alternate,n!==null&&(e=n.memoizedState)),e!==null)return e.dehydrated}return null}function A(n){if(c(n)!==n)throw Error(u(188))}function S(n){var e=n.alternate;if(!e){if(e=c(n),e===null)throw Error(u(188));return e!==n?null:n}for(var t=n,a=e;;){var l=t.return;if(l===null)break;var i=l.alternate;if(i===null){if(a=l.return,a!==null){t=a;continue}break}if(l.child===i.child){for(i=l.child;i;){if(i===t)return A(l),n;if(i===a)return A(l),e;i=i.sibling}throw Error(u(188))}if(t.return!==a.return)t=l,a=i;else{for(var o=!1,g=l.child;g;){if(g===t){o=!0,t=l,a=i;break}if(g===a){o=!0,a=l,t=i;break}g=g.sibling}if(!o){for(g=i.child;g;){if(g===t){o=!0,t=i,a=l;break}if(g===a){o=!0,a=i,t=l;break}g=g.sibling}if(!o)throw Error(u(189))}}if(t.alternate!==a)throw Error(u(190))}if(t.tag!==3)throw Error(u(188));return t.stateNode.current===t?n:e}function N(n){var e=n.tag;if(e===5||e===26||e===27||e===6)return n;for(n=n.child;n!==null;){if(e=N(n),e!==null)return e;n=n.sibling}return null}var U=Object.assign,Y=Symbol.for("react.element"),u0=Symbol.for("react.transitional.element"),y0=Symbol.for("react.portal"),T0=Symbol.for("react.fragment"),Q0=Symbol.for("react.strict_mode"),C0=Symbol.for("react.profiler"),jn=Symbol.for("react.consumer"),Y0=Symbol.for("react.context"),mn=Symbol.for("react.forward_ref"),Nn=Symbol.for("react.suspense"),K0=Symbol.for("react.suspense_list"),F=Symbol.for("react.memo"),J0=Symbol.for("react.lazy"),Mn=Symbol.for("react.activity"),ft=Symbol.for("react.memo_cache_sentinel"),Un=Symbol.iterator;function k0(n){return n===null||typeof n!="object"?null:(n=Un&&n[Un]||n["@@iterator"],typeof n=="function"?n:null)}var we=Symbol.for("react.client.reference");function Yn(n){if(n==null)return null;if(typeof n=="function")return n.$$typeof===we?null:n.displayName||n.name||null;if(typeof n=="string")return n;switch(n){case T0:return"Fragment";case C0:return"Profiler";case Q0:return"StrictMode";case Nn:return"Suspense";case K0:return"SuspenseList";case Mn:return"Activity"}if(typeof n=="object")switch(n.$$typeof){case y0:return"Portal";case Y0:return n.displayName||"Context";case jn:return(n._context.displayName||"Context")+".Consumer";case mn:var e=n.render;return n=n.displayName,n||(n=e.displayName||e.name||"",n=n!==""?"ForwardRef("+n+")":"ForwardRef"),n;case F:return e=n.displayName||null,e!==null?e:Yn(n.type)||"Memo";case J0:e=n._payload,n=n._init;try{return Yn(n(e))}catch{}}return null}var On=Array.isArray,O=d.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE,M=f.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE,L={pending:!1,data:null,method:null,action:null},s0=[],I0=-1;function y(n){return{current:n}}function C(n){0>I0||(n.current=s0[I0],s0[I0]=null,I0--)}function R(n,e){I0++,s0[I0]=n.current,n.current=e}var H=y(null),X=y(null),K=y(null),d0=y(null);function X0(n,e){switch(R(K,e),R(X,n),R(H,null),e.nodeType){case 9:case 11:n=(n=e.documentElement)&&(n=n.namespaceURI)?ko(n):0;break;default:if(n=e.tagName,e=e.namespaceURI)e=ko(e),n=$o(e,n);else switch(n){case"svg":n=1;break;case"math":n=2;break;default:n=0}}C(H),R(H,n)}function x0(){C(H),C(X),C(K)}function Pt(n){n.memoizedState!==null&&R(d0,n);var e=H.current,t=$o(e,n.type);e!==t&&(R(X,n),R(H,t))}function rr(n){X.current===n&&(C(H),C(X)),d0.current===n&&(C(d0),La._currentValue=L)}var Rd,Af;function qe(n){if(Rd===void 0)try{throw Error()}catch(t){var e=t.stack.trim().match(/\n( *(at )?)/);Rd=e&&e[1]||"",Af=-1<t.stack.indexOf(`
    at`)?" (<anonymous>)":-1<t.stack.indexOf("@")?"@unknown:0:0":""}return`
`+Rd+n+Af}var Bd=!1;function Hd(n,e){if(!n||Bd)return"";Bd=!0;var t=Error.prepareStackTrace;Error.prepareStackTrace=void 0;try{var a={DetermineComponentFrameRoot:function(){try{if(e){var D=function(){throw Error()};if(Object.defineProperty(D.prototype,"props",{set:function(){throw Error()}}),typeof Reflect=="object"&&Reflect.construct){try{Reflect.construct(D,[])}catch(T){var E=T}Reflect.construct(n,[],D)}else{try{D.call()}catch(T){E=T}n.call(D.prototype)}}else{try{throw Error()}catch(T){E=T}(D=n())&&typeof D.catch=="function"&&D.catch(function(){})}}catch(T){if(T&&E&&typeof T.stack=="string")return[T.stack,E.stack]}return[null,null]}};a.DetermineComponentFrameRoot.displayName="DetermineComponentFrameRoot";var l=Object.getOwnPropertyDescriptor(a.DetermineComponentFrameRoot,"name");l&&l.configurable&&Object.defineProperty(a.DetermineComponentFrameRoot,"name",{value:"DetermineComponentFrameRoot"});var i=a.DetermineComponentFrameRoot(),o=i[0],g=i[1];if(o&&g){var m=o.split(`
`),x=g.split(`
`);for(l=a=0;a<m.length&&!m[a].includes("DetermineComponentFrameRoot");)a++;for(;l<x.length&&!x[l].includes("DetermineComponentFrameRoot");)l++;if(a===m.length||l===x.length)for(a=m.length-1,l=x.length-1;1<=a&&0<=l&&m[a]!==x[l];)l--;for(;1<=a&&0<=l;a--,l--)if(m[a]!==x[l]){if(a!==1||l!==1)do if(a--,l--,0>l||m[a]!==x[l]){var j=`
`+m[a].replace(" at new "," at ");return n.displayName&&j.includes("<anonymous>")&&(j=j.replace("<anonymous>",n.displayName)),j}while(1<=a&&0<=l);break}}}finally{Bd=!1,Error.prepareStackTrace=t}return(t=n?n.displayName||n.name:"")?qe(t):""}function O4(n,e){switch(n.tag){case 26:case 27:case 5:return qe(n.type);case 16:return qe("Lazy");case 13:return n.child!==e&&e!==null?qe("Suspense Fallback"):qe("Suspense");case 19:return qe("SuspenseList");case 0:case 15:return Hd(n.type,!1);case 11:return Hd(n.type.render,!1);case 1:return Hd(n.type,!0);case 31:return qe("Activity");default:return""}}function Ef(n){try{var e="",t=null;do e+=O4(n,t),t=n,n=n.return;while(n);return e}catch(a){return`
Error generating stack: `+a.message+`
`+a.stack}}var wd=Object.prototype.hasOwnProperty,qd=r.unstable_scheduleCallback,Yd=r.unstable_cancelCallback,z4=r.unstable_shouldYield,D4=r.unstable_requestPaint,dn=r.unstable_now,C4=r.unstable_getCurrentPriorityLevel,Tf=r.unstable_ImmediatePriority,jf=r.unstable_UserBlockingPriority,dr=r.unstable_NormalPriority,N4=r.unstable_LowPriority,Of=r.unstable_IdlePriority,M4=r.log,U4=r.unstable_setDisableYieldValue,na=null,ln=null;function le(n){if(typeof M4=="function"&&U4(n),ln&&typeof ln.setStrictMode=="function")try{ln.setStrictMode(na,n)}catch{}}var fn=Math.clz32?Math.clz32:H4,R4=Math.log,B4=Math.LN2;function H4(n){return n>>>=0,n===0?32:31-(R4(n)/B4|0)|0}var lr=256,ir=262144,fr=4194304;function Ye(n){var e=n&42;if(e!==0)return e;switch(n&-n){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;case 16:return 16;case 32:return 32;case 64:return 64;case 128:return 128;case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:return n&261888;case 262144:case 524288:case 1048576:case 2097152:return n&3932160;case 4194304:case 8388608:case 16777216:case 33554432:return n&62914560;case 67108864:return 67108864;case 134217728:return 134217728;case 268435456:return 268435456;case 536870912:return 536870912;case 1073741824:return 0;default:return n}}function ur(n,e,t){var a=n.pendingLanes;if(a===0)return 0;var l=0,i=n.suspendedLanes,o=n.pingedLanes;n=n.warmLanes;var g=a&134217727;return g!==0?(a=g&~i,a!==0?l=Ye(a):(o&=g,o!==0?l=Ye(o):t||(t=g&~n,t!==0&&(l=Ye(t))))):(g=a&~i,g!==0?l=Ye(g):o!==0?l=Ye(o):t||(t=a&~n,t!==0&&(l=Ye(t)))),l===0?0:e!==0&&e!==l&&(e&i)===0&&(i=l&-l,t=e&-e,i>=t||i===32&&(t&4194048)!==0)?e:l}function ea(n,e){return(n.pendingLanes&~(n.suspendedLanes&~n.pingedLanes)&e)===0}function w4(n,e){switch(n){case 1:case 2:case 4:case 8:case 64:return e+250;case 16:case 32:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return e+5e3;case 4194304:case 8388608:case 16777216:case 33554432:return-1;case 67108864:case 134217728:case 268435456:case 536870912:case 1073741824:return-1;default:return-1}}function zf(){var n=fr;return fr<<=1,(fr&62914560)===0&&(fr=4194304),n}function Gd(n){for(var e=[],t=0;31>t;t++)e.push(n);return e}function ta(n,e){n.pendingLanes|=e,e!==268435456&&(n.suspendedLanes=0,n.pingedLanes=0,n.warmLanes=0)}function q4(n,e,t,a,l,i){var o=n.pendingLanes;n.pendingLanes=t,n.suspendedLanes=0,n.pingedLanes=0,n.warmLanes=0,n.expiredLanes&=t,n.entangledLanes&=t,n.errorRecoveryDisabledLanes&=t,n.shellSuspendCounter=0;var g=n.entanglements,m=n.expirationTimes,x=n.hiddenUpdates;for(t=o&~t;0<t;){var j=31-fn(t),D=1<<j;g[j]=0,m[j]=-1;var E=x[j];if(E!==null)for(x[j]=null,j=0;j<E.length;j++){var T=E[j];T!==null&&(T.lane&=-536870913)}t&=~D}a!==0&&Df(n,a,0),i!==0&&l===0&&n.tag!==0&&(n.suspendedLanes|=i&~(o&~e))}function Df(n,e,t){n.pendingLanes|=e,n.suspendedLanes&=~e;var a=31-fn(e);n.entangledLanes|=e,n.entanglements[a]=n.entanglements[a]|1073741824|t&261930}function Cf(n,e){var t=n.entangledLanes|=e;for(n=n.entanglements;t;){var a=31-fn(t),l=1<<a;l&e|n[a]&e&&(n[a]|=e),t&=~l}}function Nf(n,e){var t=e&-e;return t=(t&42)!==0?1:Ld(t),(t&(n.suspendedLanes|e))!==0?0:t}function Ld(n){switch(n){case 2:n=1;break;case 8:n=4;break;case 32:n=16;break;case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:case 4194304:case 8388608:case 16777216:case 33554432:n=128;break;case 268435456:n=134217728;break;default:n=0}return n}function Qd(n){return n&=-n,2<n?8<n?(n&134217727)!==0?32:268435456:8:2}function Mf(){var n=M.p;return n!==0?n:(n=window.event,n===void 0?32:pc(n.type))}function Uf(n,e){var t=M.p;try{return M.p=n,e()}finally{M.p=t}}var ie=Math.random().toString(36).slice(2),R0="__reactFiber$"+ie,$0="__reactProps$"+ie,ut="__reactContainer$"+ie,Xd="__reactEvents$"+ie,Y4="__reactListeners$"+ie,G4="__reactHandles$"+ie,Rf="__reactResources$"+ie,aa="__reactMarker$"+ie;function Zd(n){delete n[R0],delete n[$0],delete n[Xd],delete n[Y4],delete n[G4]}function st(n){var e=n[R0];if(e)return e;for(var t=n.parentNode;t;){if(e=t[ut]||t[R0]){if(t=e.alternate,e.child!==null||t!==null&&t.child!==null)for(n=ac(n);n!==null;){if(t=n[R0])return t;n=ac(n)}return e}n=t,t=n.parentNode}return null}function ot(n){if(n=n[R0]||n[ut]){var e=n.tag;if(e===5||e===6||e===13||e===31||e===26||e===27||e===3)return n}return null}function ra(n){var e=n.tag;if(e===5||e===26||e===27||e===6)return n.stateNode;throw Error(u(33))}function ct(n){var e=n[Rf];return e||(e=n[Rf]={hoistableStyles:new Map,hoistableScripts:new Map}),e}function M0(n){n[aa]=!0}var Bf=new Set,Hf={};function Ge(n,e){gt(n,e),gt(n+"Capture",e)}function gt(n,e){for(Hf[n]=e,n=0;n<e.length;n++)Bf.add(e[n])}var L4=RegExp("^[:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD][:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD\\-.0-9\\u00B7\\u0300-\\u036F\\u203F-\\u2040]*$"),wf={},qf={};function Q4(n){return wd.call(qf,n)?!0:wd.call(wf,n)?!1:L4.test(n)?qf[n]=!0:(wf[n]=!0,!1)}function sr(n,e,t){if(Q4(e))if(t===null)n.removeAttribute(e);else{switch(typeof t){case"undefined":case"function":case"symbol":n.removeAttribute(e);return;case"boolean":var a=e.toLowerCase().slice(0,5);if(a!=="data-"&&a!=="aria-"){n.removeAttribute(e);return}}n.setAttribute(e,""+t)}}function or(n,e,t){if(t===null)n.removeAttribute(e);else{switch(typeof t){case"undefined":case"function":case"symbol":case"boolean":n.removeAttribute(e);return}n.setAttribute(e,""+t)}}function Gn(n,e,t,a){if(a===null)n.removeAttribute(t);else{switch(typeof a){case"undefined":case"function":case"symbol":case"boolean":n.removeAttribute(t);return}n.setAttributeNS(e,t,""+a)}}function hn(n){switch(typeof n){case"bigint":case"boolean":case"number":case"string":case"undefined":return n;case"object":return n;default:return""}}function Yf(n){var e=n.type;return(n=n.nodeName)&&n.toLowerCase()==="input"&&(e==="checkbox"||e==="radio")}function X4(n,e,t){var a=Object.getOwnPropertyDescriptor(n.constructor.prototype,e);if(!n.hasOwnProperty(e)&&typeof a<"u"&&typeof a.get=="function"&&typeof a.set=="function"){var l=a.get,i=a.set;return Object.defineProperty(n,e,{configurable:!0,get:function(){return l.call(this)},set:function(o){t=""+o,i.call(this,o)}}),Object.defineProperty(n,e,{enumerable:a.enumerable}),{getValue:function(){return t},setValue:function(o){t=""+o},stopTracking:function(){n._valueTracker=null,delete n[e]}}}}function Vd(n){if(!n._valueTracker){var e=Yf(n)?"checked":"value";n._valueTracker=X4(n,e,""+n[e])}}function Gf(n){if(!n)return!1;var e=n._valueTracker;if(!e)return!0;var t=e.getValue(),a="";return n&&(a=Yf(n)?n.checked?"true":"false":n.value),n=a,n!==t?(e.setValue(n),!0):!1}function cr(n){if(n=n||(typeof document<"u"?document:void 0),typeof n>"u")return null;try{return n.activeElement||n.body}catch{return n.body}}var Z4=/[\n"\\]/g;function yn(n){return n.replace(Z4,function(e){return"\\"+e.charCodeAt(0).toString(16)+" "})}function Kd(n,e,t,a,l,i,o,g){n.name="",o!=null&&typeof o!="function"&&typeof o!="symbol"&&typeof o!="boolean"?n.type=o:n.removeAttribute("type"),e!=null?o==="number"?(e===0&&n.value===""||n.value!=e)&&(n.value=""+hn(e)):n.value!==""+hn(e)&&(n.value=""+hn(e)):o!=="submit"&&o!=="reset"||n.removeAttribute("value"),e!=null?Jd(n,o,hn(e)):t!=null?Jd(n,o,hn(t)):a!=null&&n.removeAttribute("value"),l==null&&i!=null&&(n.defaultChecked=!!i),l!=null&&(n.checked=l&&typeof l!="function"&&typeof l!="symbol"),g!=null&&typeof g!="function"&&typeof g!="symbol"&&typeof g!="boolean"?n.name=""+hn(g):n.removeAttribute("name")}function Lf(n,e,t,a,l,i,o,g){if(i!=null&&typeof i!="function"&&typeof i!="symbol"&&typeof i!="boolean"&&(n.type=i),e!=null||t!=null){if(!(i!=="submit"&&i!=="reset"||e!=null)){Vd(n);return}t=t!=null?""+hn(t):"",e=e!=null?""+hn(e):t,g||e===n.value||(n.value=e),n.defaultValue=e}a=a??l,a=typeof a!="function"&&typeof a!="symbol"&&!!a,n.checked=g?n.checked:!!a,n.defaultChecked=!!a,o!=null&&typeof o!="function"&&typeof o!="symbol"&&typeof o!="boolean"&&(n.name=o),Vd(n)}function Jd(n,e,t){e==="number"&&cr(n.ownerDocument)===n||n.defaultValue===""+t||(n.defaultValue=""+t)}function It(n,e,t,a){if(n=n.options,e){e={};for(var l=0;l<t.length;l++)e["$"+t[l]]=!0;for(t=0;t<n.length;t++)l=e.hasOwnProperty("$"+n[t].value),n[t].selected!==l&&(n[t].selected=l),l&&a&&(n[t].defaultSelected=!0)}else{for(t=""+hn(t),e=null,l=0;l<n.length;l++){if(n[l].value===t){n[l].selected=!0,a&&(n[l].defaultSelected=!0);return}e!==null||n[l].disabled||(e=n[l])}e!==null&&(e.selected=!0)}}function Qf(n,e,t){if(e!=null&&(e=""+hn(e),e!==n.value&&(n.value=e),t==null)){n.defaultValue!==e&&(n.defaultValue=e);return}n.defaultValue=t!=null?""+hn(t):""}function Xf(n,e,t,a){if(e==null){if(a!=null){if(t!=null)throw Error(u(92));if(On(a)){if(1<a.length)throw Error(u(93));a=a[0]}t=a}t==null&&(t=""),e=t}t=hn(e),n.defaultValue=t,a=n.textContent,a===t&&a!==""&&a!==null&&(n.value=a),Vd(n)}function vt(n,e){if(e){var t=n.firstChild;if(t&&t===n.lastChild&&t.nodeType===3){t.nodeValue=e;return}}n.textContent=e}var V4=new Set("animationIterationCount aspectRatio borderImageOutset borderImageSlice borderImageWidth boxFlex boxFlexGroup boxOrdinalGroup columnCount columns flex flexGrow flexPositive flexShrink flexNegative flexOrder gridArea gridRow gridRowEnd gridRowSpan gridRowStart gridColumn gridColumnEnd gridColumnSpan gridColumnStart fontWeight lineClamp lineHeight opacity order orphans scale tabSize widows zIndex zoom fillOpacity floodOpacity stopOpacity strokeDasharray strokeDashoffset strokeMiterlimit strokeOpacity strokeWidth MozAnimationIterationCount MozBoxFlex MozBoxFlexGroup MozLineClamp msAnimationIterationCount msFlex msZoom msFlexGrow msFlexNegative msFlexOrder msFlexPositive msFlexShrink msGridColumn msGridColumnSpan msGridRow msGridRowSpan WebkitAnimationIterationCount WebkitBoxFlex WebKitBoxFlexGroup WebkitBoxOrdinalGroup WebkitColumnCount WebkitColumns WebkitFlex WebkitFlexGrow WebkitFlexPositive WebkitFlexShrink WebkitLineClamp".split(" "));function Zf(n,e,t){var a=e.indexOf("--")===0;t==null||typeof t=="boolean"||t===""?a?n.setProperty(e,""):e==="float"?n.cssFloat="":n[e]="":a?n.setProperty(e,t):typeof t!="number"||t===0||V4.has(e)?e==="float"?n.cssFloat=t:n[e]=(""+t).trim():n[e]=t+"px"}function Vf(n,e,t){if(e!=null&&typeof e!="object")throw Error(u(62));if(n=n.style,t!=null){for(var a in t)!t.hasOwnProperty(a)||e!=null&&e.hasOwnProperty(a)||(a.indexOf("--")===0?n.setProperty(a,""):a==="float"?n.cssFloat="":n[a]="");for(var l in e)a=e[l],e.hasOwnProperty(l)&&t[l]!==a&&Zf(n,l,a)}else for(var i in e)e.hasOwnProperty(i)&&Zf(n,i,e[i])}function kd(n){if(n.indexOf("-")===-1)return!1;switch(n){case"annotation-xml":case"color-profile":case"font-face":case"font-face-src":case"font-face-uri":case"font-face-format":case"font-face-name":case"missing-glyph":return!1;default:return!0}}var K4=new Map([["acceptCharset","accept-charset"],["htmlFor","for"],["httpEquiv","http-equiv"],["crossOrigin","crossorigin"],["accentHeight","accent-height"],["alignmentBaseline","alignment-baseline"],["arabicForm","arabic-form"],["baselineShift","baseline-shift"],["capHeight","cap-height"],["clipPath","clip-path"],["clipRule","clip-rule"],["colorInterpolation","color-interpolation"],["colorInterpolationFilters","color-interpolation-filters"],["colorProfile","color-profile"],["colorRendering","color-rendering"],["dominantBaseline","dominant-baseline"],["enableBackground","enable-background"],["fillOpacity","fill-opacity"],["fillRule","fill-rule"],["floodColor","flood-color"],["floodOpacity","flood-opacity"],["fontFamily","font-family"],["fontSize","font-size"],["fontSizeAdjust","font-size-adjust"],["fontStretch","font-stretch"],["fontStyle","font-style"],["fontVariant","font-variant"],["fontWeight","font-weight"],["glyphName","glyph-name"],["glyphOrientationHorizontal","glyph-orientation-horizontal"],["glyphOrientationVertical","glyph-orientation-vertical"],["horizAdvX","horiz-adv-x"],["horizOriginX","horiz-origin-x"],["imageRendering","image-rendering"],["letterSpacing","letter-spacing"],["lightingColor","lighting-color"],["markerEnd","marker-end"],["markerMid","marker-mid"],["markerStart","marker-start"],["overlinePosition","overline-position"],["overlineThickness","overline-thickness"],["paintOrder","paint-order"],["panose-1","panose-1"],["pointerEvents","pointer-events"],["renderingIntent","rendering-intent"],["shapeRendering","shape-rendering"],["stopColor","stop-color"],["stopOpacity","stop-opacity"],["strikethroughPosition","strikethrough-position"],["strikethroughThickness","strikethrough-thickness"],["strokeDasharray","stroke-dasharray"],["strokeDashoffset","stroke-dashoffset"],["strokeLinecap","stroke-linecap"],["strokeLinejoin","stroke-linejoin"],["strokeMiterlimit","stroke-miterlimit"],["strokeOpacity","stroke-opacity"],["strokeWidth","stroke-width"],["textAnchor","text-anchor"],["textDecoration","text-decoration"],["textRendering","text-rendering"],["transformOrigin","transform-origin"],["underlinePosition","underline-position"],["underlineThickness","underline-thickness"],["unicodeBidi","unicode-bidi"],["unicodeRange","unicode-range"],["unitsPerEm","units-per-em"],["vAlphabetic","v-alphabetic"],["vHanging","v-hanging"],["vIdeographic","v-ideographic"],["vMathematical","v-mathematical"],["vectorEffect","vector-effect"],["vertAdvY","vert-adv-y"],["vertOriginX","vert-origin-x"],["vertOriginY","vert-origin-y"],["wordSpacing","word-spacing"],["writingMode","writing-mode"],["xmlnsXlink","xmlns:xlink"],["xHeight","x-height"]]),J4=/^[\u0000-\u001F ]*j[\r\n\t]*a[\r\n\t]*v[\r\n\t]*a[\r\n\t]*s[\r\n\t]*c[\r\n\t]*r[\r\n\t]*i[\r\n\t]*p[\r\n\t]*t[\r\n\t]*:/i;function gr(n){return J4.test(""+n)?"javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')":n}function Ln(){}var $d=null;function Wd(n){return n=n.target||n.srcElement||window,n.correspondingUseElement&&(n=n.correspondingUseElement),n.nodeType===3?n.parentNode:n}var mt=null,ht=null;function Kf(n){var e=ot(n);if(e&&(n=e.stateNode)){var t=n[$0]||null;n:switch(n=e.stateNode,e.type){case"input":if(Kd(n,t.value,t.defaultValue,t.defaultValue,t.checked,t.defaultChecked,t.type,t.name),e=t.name,t.type==="radio"&&e!=null){for(t=n;t.parentNode;)t=t.parentNode;for(t=t.querySelectorAll('input[name="'+yn(""+e)+'"][type="radio"]'),e=0;e<t.length;e++){var a=t[e];if(a!==n&&a.form===n.form){var l=a[$0]||null;if(!l)throw Error(u(90));Kd(a,l.value,l.defaultValue,l.defaultValue,l.checked,l.defaultChecked,l.type,l.name)}}for(e=0;e<t.length;e++)a=t[e],a.form===n.form&&Gf(a)}break n;case"textarea":Qf(n,t.value,t.defaultValue);break n;case"select":e=t.value,e!=null&&It(n,!!t.multiple,e,!1)}}}var Fd=!1;function Jf(n,e,t){if(Fd)return n(e,t);Fd=!0;try{var a=n(e);return a}finally{if(Fd=!1,(mt!==null||ht!==null)&&(nd(),mt&&(e=mt,n=ht,ht=mt=null,Kf(e),n)))for(e=0;e<n.length;e++)Kf(n[e])}}function da(n,e){var t=n.stateNode;if(t===null)return null;var a=t[$0]||null;if(a===null)return null;t=a[e];n:switch(e){case"onClick":case"onClickCapture":case"onDoubleClick":case"onDoubleClickCapture":case"onMouseDown":case"onMouseDownCapture":case"onMouseMove":case"onMouseMoveCapture":case"onMouseUp":case"onMouseUpCapture":case"onMouseEnter":(a=!a.disabled)||(n=n.type,a=!(n==="button"||n==="input"||n==="select"||n==="textarea")),n=!a;break n;default:n=!1}if(n)return null;if(t&&typeof t!="function")throw Error(u(231,e,typeof t));return t}var Qn=!(typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"),Pd=!1;if(Qn)try{var la={};Object.defineProperty(la,"passive",{get:function(){Pd=!0}}),window.addEventListener("test",la,la),window.removeEventListener("test",la,la)}catch{Pd=!1}var fe=null,nl=null,Ir=null;function kf(){if(Ir)return Ir;var n,e=nl,t=e.length,a,l="value"in fe?fe.value:fe.textContent,i=l.length;for(n=0;n<t&&e[n]===l[n];n++);var o=t-n;for(a=1;a<=o&&e[t-a]===l[i-a];a++);return Ir=l.slice(n,1<a?1-a:void 0)}function vr(n){var e=n.keyCode;return"charCode"in n?(n=n.charCode,n===0&&e===13&&(n=13)):n=e,n===10&&(n=13),32<=n||n===13?n:0}function mr(){return!0}function $f(){return!1}function W0(n){function e(t,a,l,i,o){this._reactName=t,this._targetInst=l,this.type=a,this.nativeEvent=i,this.target=o,this.currentTarget=null;for(var g in n)n.hasOwnProperty(g)&&(t=n[g],this[g]=t?t(i):i[g]);return this.isDefaultPrevented=(i.defaultPrevented!=null?i.defaultPrevented:i.returnValue===!1)?mr:$f,this.isPropagationStopped=$f,this}return U(e.prototype,{preventDefault:function(){this.defaultPrevented=!0;var t=this.nativeEvent;t&&(t.preventDefault?t.preventDefault():typeof t.returnValue!="unknown"&&(t.returnValue=!1),this.isDefaultPrevented=mr)},stopPropagation:function(){var t=this.nativeEvent;t&&(t.stopPropagation?t.stopPropagation():typeof t.cancelBubble!="unknown"&&(t.cancelBubble=!0),this.isPropagationStopped=mr)},persist:function(){},isPersistent:mr}),e}var Le={eventPhase:0,bubbles:0,cancelable:0,timeStamp:function(n){return n.timeStamp||Date.now()},defaultPrevented:0,isTrusted:0},hr=W0(Le),ia=U({},Le,{view:0,detail:0}),k4=W0(ia),el,tl,fa,yr=U({},ia,{screenX:0,screenY:0,clientX:0,clientY:0,pageX:0,pageY:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,getModifierState:rl,button:0,buttons:0,relatedTarget:function(n){return n.relatedTarget===void 0?n.fromElement===n.srcElement?n.toElement:n.fromElement:n.relatedTarget},movementX:function(n){return"movementX"in n?n.movementX:(n!==fa&&(fa&&n.type==="mousemove"?(el=n.screenX-fa.screenX,tl=n.screenY-fa.screenY):tl=el=0,fa=n),el)},movementY:function(n){return"movementY"in n?n.movementY:tl}}),Wf=W0(yr),$4=U({},yr,{dataTransfer:0}),W4=W0($4),F4=U({},ia,{relatedTarget:0}),al=W0(F4),P4=U({},Le,{animationName:0,elapsedTime:0,pseudoElement:0}),n1=W0(P4),e1=U({},Le,{clipboardData:function(n){return"clipboardData"in n?n.clipboardData:window.clipboardData}}),t1=W0(e1),a1=U({},Le,{data:0}),Ff=W0(a1),r1={Esc:"Escape",Spacebar:" ",Left:"ArrowLeft",Up:"ArrowUp",Right:"ArrowRight",Down:"ArrowDown",Del:"Delete",Win:"OS",Menu:"ContextMenu",Apps:"ContextMenu",Scroll:"ScrollLock",MozPrintableKey:"Unidentified"},d1={8:"Backspace",9:"Tab",12:"Clear",13:"Enter",16:"Shift",17:"Control",18:"Alt",19:"Pause",20:"CapsLock",27:"Escape",32:" ",33:"PageUp",34:"PageDown",35:"End",36:"Home",37:"ArrowLeft",38:"ArrowUp",39:"ArrowRight",40:"ArrowDown",45:"Insert",46:"Delete",112:"F1",113:"F2",114:"F3",115:"F4",116:"F5",117:"F6",118:"F7",119:"F8",120:"F9",121:"F10",122:"F11",123:"F12",144:"NumLock",145:"ScrollLock",224:"Meta"},l1={Alt:"altKey",Control:"ctrlKey",Meta:"metaKey",Shift:"shiftKey"};function i1(n){var e=this.nativeEvent;return e.getModifierState?e.getModifierState(n):(n=l1[n])?!!e[n]:!1}function rl(){return i1}var f1=U({},ia,{key:function(n){if(n.key){var e=r1[n.key]||n.key;if(e!=="Unidentified")return e}return n.type==="keypress"?(n=vr(n),n===13?"Enter":String.fromCharCode(n)):n.type==="keydown"||n.type==="keyup"?d1[n.keyCode]||"Unidentified":""},code:0,location:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,repeat:0,locale:0,getModifierState:rl,charCode:function(n){return n.type==="keypress"?vr(n):0},keyCode:function(n){return n.type==="keydown"||n.type==="keyup"?n.keyCode:0},which:function(n){return n.type==="keypress"?vr(n):n.type==="keydown"||n.type==="keyup"?n.keyCode:0}}),u1=W0(f1),s1=U({},yr,{pointerId:0,width:0,height:0,pressure:0,tangentialPressure:0,tiltX:0,tiltY:0,twist:0,pointerType:0,isPrimary:0}),Pf=W0(s1),o1=U({},ia,{touches:0,targetTouches:0,changedTouches:0,altKey:0,metaKey:0,ctrlKey:0,shiftKey:0,getModifierState:rl}),c1=W0(o1),g1=U({},Le,{propertyName:0,elapsedTime:0,pseudoElement:0}),I1=W0(g1),v1=U({},yr,{deltaX:function(n){return"deltaX"in n?n.deltaX:"wheelDeltaX"in n?-n.wheelDeltaX:0},deltaY:function(n){return"deltaY"in n?n.deltaY:"wheelDeltaY"in n?-n.wheelDeltaY:"wheelDelta"in n?-n.wheelDelta:0},deltaZ:0,deltaMode:0}),m1=W0(v1),h1=U({},Le,{newState:0,oldState:0}),y1=W0(h1),p1=[9,13,27,32],dl=Qn&&"CompositionEvent"in window,ua=null;Qn&&"documentMode"in document&&(ua=document.documentMode);var b1=Qn&&"TextEvent"in window&&!ua,nu=Qn&&(!dl||ua&&8<ua&&11>=ua),eu=" ",tu=!1;function au(n,e){switch(n){case"keyup":return p1.indexOf(e.keyCode)!==-1;case"keydown":return e.keyCode!==229;case"keypress":case"mousedown":case"focusout":return!0;default:return!1}}function ru(n){return n=n.detail,typeof n=="object"&&"data"in n?n.data:null}var yt=!1;function S1(n,e){switch(n){case"compositionend":return ru(e);case"keypress":return e.which!==32?null:(tu=!0,eu);case"textInput":return n=e.data,n===eu&&tu?null:n;default:return null}}function _1(n,e){if(yt)return n==="compositionend"||!dl&&au(n,e)?(n=kf(),Ir=nl=fe=null,yt=!1,n):null;switch(n){case"paste":return null;case"keypress":if(!(e.ctrlKey||e.altKey||e.metaKey)||e.ctrlKey&&e.altKey){if(e.char&&1<e.char.length)return e.char;if(e.which)return String.fromCharCode(e.which)}return null;case"compositionend":return nu&&e.locale!=="ko"?null:e.data;default:return null}}var x1={color:!0,date:!0,datetime:!0,"datetime-local":!0,email:!0,month:!0,number:!0,password:!0,range:!0,search:!0,tel:!0,text:!0,time:!0,url:!0,week:!0};function du(n){var e=n&&n.nodeName&&n.nodeName.toLowerCase();return e==="input"?!!x1[n.type]:e==="textarea"}function lu(n,e,t,a){mt?ht?ht.push(a):ht=[a]:mt=a,e=id(e,"onChange"),0<e.length&&(t=new hr("onChange","change",null,t,a),n.push({event:t,listeners:e}))}var sa=null,oa=null;function A1(n){Qo(n,0)}function pr(n){var e=ra(n);if(Gf(e))return n}function iu(n,e){if(n==="change")return e}var fu=!1;if(Qn){var ll;if(Qn){var il="oninput"in document;if(!il){var uu=document.createElement("div");uu.setAttribute("oninput","return;"),il=typeof uu.oninput=="function"}ll=il}else ll=!1;fu=ll&&(!document.documentMode||9<document.documentMode)}function su(){sa&&(sa.detachEvent("onpropertychange",ou),oa=sa=null)}function ou(n){if(n.propertyName==="value"&&pr(oa)){var e=[];lu(e,oa,n,Wd(n)),Jf(A1,e)}}function E1(n,e,t){n==="focusin"?(su(),sa=e,oa=t,sa.attachEvent("onpropertychange",ou)):n==="focusout"&&su()}function T1(n){if(n==="selectionchange"||n==="keyup"||n==="keydown")return pr(oa)}function j1(n,e){if(n==="click")return pr(e)}function O1(n,e){if(n==="input"||n==="change")return pr(e)}function z1(n,e){return n===e&&(n!==0||1/n===1/e)||n!==n&&e!==e}var un=typeof Object.is=="function"?Object.is:z1;function ca(n,e){if(un(n,e))return!0;if(typeof n!="object"||n===null||typeof e!="object"||e===null)return!1;var t=Object.keys(n),a=Object.keys(e);if(t.length!==a.length)return!1;for(a=0;a<t.length;a++){var l=t[a];if(!wd.call(e,l)||!un(n[l],e[l]))return!1}return!0}function cu(n){for(;n&&n.firstChild;)n=n.firstChild;return n}function gu(n,e){var t=cu(n);n=0;for(var a;t;){if(t.nodeType===3){if(a=n+t.textContent.length,n<=e&&a>=e)return{node:t,offset:e-n};n=a}n:{for(;t;){if(t.nextSibling){t=t.nextSibling;break n}t=t.parentNode}t=void 0}t=cu(t)}}function Iu(n,e){return n&&e?n===e?!0:n&&n.nodeType===3?!1:e&&e.nodeType===3?Iu(n,e.parentNode):"contains"in n?n.contains(e):n.compareDocumentPosition?!!(n.compareDocumentPosition(e)&16):!1:!1}function vu(n){n=n!=null&&n.ownerDocument!=null&&n.ownerDocument.defaultView!=null?n.ownerDocument.defaultView:window;for(var e=cr(n.document);e instanceof n.HTMLIFrameElement;){try{var t=typeof e.contentWindow.location.href=="string"}catch{t=!1}if(t)n=e.contentWindow;else break;e=cr(n.document)}return e}function fl(n){var e=n&&n.nodeName&&n.nodeName.toLowerCase();return e&&(e==="input"&&(n.type==="text"||n.type==="search"||n.type==="tel"||n.type==="url"||n.type==="password")||e==="textarea"||n.contentEditable==="true")}var D1=Qn&&"documentMode"in document&&11>=document.documentMode,pt=null,ul=null,ga=null,sl=!1;function mu(n,e,t){var a=t.window===t?t.document:t.nodeType===9?t:t.ownerDocument;sl||pt==null||pt!==cr(a)||(a=pt,"selectionStart"in a&&fl(a)?a={start:a.selectionStart,end:a.selectionEnd}:(a=(a.ownerDocument&&a.ownerDocument.defaultView||window).getSelection(),a={anchorNode:a.anchorNode,anchorOffset:a.anchorOffset,focusNode:a.focusNode,focusOffset:a.focusOffset}),ga&&ca(ga,a)||(ga=a,a=id(ul,"onSelect"),0<a.length&&(e=new hr("onSelect","select",null,e,t),n.push({event:e,listeners:a}),e.target=pt)))}function Qe(n,e){var t={};return t[n.toLowerCase()]=e.toLowerCase(),t["Webkit"+n]="webkit"+e,t["Moz"+n]="moz"+e,t}var bt={animationend:Qe("Animation","AnimationEnd"),animationiteration:Qe("Animation","AnimationIteration"),animationstart:Qe("Animation","AnimationStart"),transitionrun:Qe("Transition","TransitionRun"),transitionstart:Qe("Transition","TransitionStart"),transitioncancel:Qe("Transition","TransitionCancel"),transitionend:Qe("Transition","TransitionEnd")},ol={},hu={};Qn&&(hu=document.createElement("div").style,"AnimationEvent"in window||(delete bt.animationend.animation,delete bt.animationiteration.animation,delete bt.animationstart.animation),"TransitionEvent"in window||delete bt.transitionend.transition);function Xe(n){if(ol[n])return ol[n];if(!bt[n])return n;var e=bt[n],t;for(t in e)if(e.hasOwnProperty(t)&&t in hu)return ol[n]=e[t];return n}var yu=Xe("animationend"),pu=Xe("animationiteration"),bu=Xe("animationstart"),C1=Xe("transitionrun"),N1=Xe("transitionstart"),M1=Xe("transitioncancel"),Su=Xe("transitionend"),_u=new Map,cl="abort auxClick beforeToggle cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");cl.push("scrollEnd");function zn(n,e){_u.set(n,e),Ge(e,[n])}var br=typeof reportError=="function"?reportError:function(n){if(typeof window=="object"&&typeof window.ErrorEvent=="function"){var e=new window.ErrorEvent("error",{bubbles:!0,cancelable:!0,message:typeof n=="object"&&n!==null&&typeof n.message=="string"?String(n.message):String(n),error:n});if(!window.dispatchEvent(e))return}else if(typeof process=="object"&&typeof process.emit=="function"){process.emit("uncaughtException",n);return}console.error(n)},pn=[],St=0,gl=0;function Sr(){for(var n=St,e=gl=St=0;e<n;){var t=pn[e];pn[e++]=null;var a=pn[e];pn[e++]=null;var l=pn[e];pn[e++]=null;var i=pn[e];if(pn[e++]=null,a!==null&&l!==null){var o=a.pending;o===null?l.next=l:(l.next=o.next,o.next=l),a.pending=l}i!==0&&xu(t,l,i)}}function _r(n,e,t,a){pn[St++]=n,pn[St++]=e,pn[St++]=t,pn[St++]=a,gl|=a,n.lanes|=a,n=n.alternate,n!==null&&(n.lanes|=a)}function Il(n,e,t,a){return _r(n,e,t,a),xr(n)}function Ze(n,e){return _r(n,null,null,e),xr(n)}function xu(n,e,t){n.lanes|=t;var a=n.alternate;a!==null&&(a.lanes|=t);for(var l=!1,i=n.return;i!==null;)i.childLanes|=t,a=i.alternate,a!==null&&(a.childLanes|=t),i.tag===22&&(n=i.stateNode,n===null||n._visibility&1||(l=!0)),n=i,i=i.return;return n.tag===3?(i=n.stateNode,l&&e!==null&&(l=31-fn(t),n=i.hiddenUpdates,a=n[l],a===null?n[l]=[e]:a.push(e),e.lane=t|536870912),i):null}function xr(n){if(50<Ra)throw Ra=0,xi=null,Error(u(185));for(var e=n.return;e!==null;)n=e,e=n.return;return n.tag===3?n.stateNode:null}var _t={};function U1(n,e,t,a){this.tag=n,this.key=t,this.sibling=this.child=this.return=this.stateNode=this.type=this.elementType=null,this.index=0,this.refCleanup=this.ref=null,this.pendingProps=e,this.dependencies=this.memoizedState=this.updateQueue=this.memoizedProps=null,this.mode=a,this.subtreeFlags=this.flags=0,this.deletions=null,this.childLanes=this.lanes=0,this.alternate=null}function sn(n,e,t,a){return new U1(n,e,t,a)}function vl(n){return n=n.prototype,!(!n||!n.isReactComponent)}function Xn(n,e){var t=n.alternate;return t===null?(t=sn(n.tag,e,n.key,n.mode),t.elementType=n.elementType,t.type=n.type,t.stateNode=n.stateNode,t.alternate=n,n.alternate=t):(t.pendingProps=e,t.type=n.type,t.flags=0,t.subtreeFlags=0,t.deletions=null),t.flags=n.flags&65011712,t.childLanes=n.childLanes,t.lanes=n.lanes,t.child=n.child,t.memoizedProps=n.memoizedProps,t.memoizedState=n.memoizedState,t.updateQueue=n.updateQueue,e=n.dependencies,t.dependencies=e===null?null:{lanes:e.lanes,firstContext:e.firstContext},t.sibling=n.sibling,t.index=n.index,t.ref=n.ref,t.refCleanup=n.refCleanup,t}function Au(n,e){n.flags&=65011714;var t=n.alternate;return t===null?(n.childLanes=0,n.lanes=e,n.child=null,n.subtreeFlags=0,n.memoizedProps=null,n.memoizedState=null,n.updateQueue=null,n.dependencies=null,n.stateNode=null):(n.childLanes=t.childLanes,n.lanes=t.lanes,n.child=t.child,n.subtreeFlags=0,n.deletions=null,n.memoizedProps=t.memoizedProps,n.memoizedState=t.memoizedState,n.updateQueue=t.updateQueue,n.type=t.type,e=t.dependencies,n.dependencies=e===null?null:{lanes:e.lanes,firstContext:e.firstContext}),n}function Ar(n,e,t,a,l,i){var o=0;if(a=n,typeof n=="function")vl(n)&&(o=1);else if(typeof n=="string")o=q8(n,t,H.current)?26:n==="html"||n==="head"||n==="body"?27:5;else n:switch(n){case Mn:return n=sn(31,t,e,l),n.elementType=Mn,n.lanes=i,n;case T0:return Ve(t.children,l,i,e);case Q0:o=8,l|=24;break;case C0:return n=sn(12,t,e,l|2),n.elementType=C0,n.lanes=i,n;case Nn:return n=sn(13,t,e,l),n.elementType=Nn,n.lanes=i,n;case K0:return n=sn(19,t,e,l),n.elementType=K0,n.lanes=i,n;default:if(typeof n=="object"&&n!==null)switch(n.$$typeof){case Y0:o=10;break n;case jn:o=9;break n;case mn:o=11;break n;case F:o=14;break n;case J0:o=16,a=null;break n}o=29,t=Error(u(130,n===null?"null":typeof n,"")),a=null}return e=sn(o,t,e,l),e.elementType=n,e.type=a,e.lanes=i,e}function Ve(n,e,t,a){return n=sn(7,n,a,e),n.lanes=t,n}function ml(n,e,t){return n=sn(6,n,null,e),n.lanes=t,n}function Eu(n){var e=sn(18,null,null,0);return e.stateNode=n,e}function hl(n,e,t){return e=sn(4,n.children!==null?n.children:[],n.key,e),e.lanes=t,e.stateNode={containerInfo:n.containerInfo,pendingChildren:null,implementation:n.implementation},e}var Tu=new WeakMap;function bn(n,e){if(typeof n=="object"&&n!==null){var t=Tu.get(n);return t!==void 0?t:(e={value:n,source:e,stack:Ef(e)},Tu.set(n,e),e)}return{value:n,source:e,stack:Ef(e)}}var xt=[],At=0,Er=null,Ia=0,Sn=[],_n=0,ue=null,Rn=1,Bn="";function Zn(n,e){xt[At++]=Ia,xt[At++]=Er,Er=n,Ia=e}function ju(n,e,t){Sn[_n++]=Rn,Sn[_n++]=Bn,Sn[_n++]=ue,ue=n;var a=Rn;n=Bn;var l=32-fn(a)-1;a&=~(1<<l),t+=1;var i=32-fn(e)+l;if(30<i){var o=l-l%5;i=(a&(1<<o)-1).toString(32),a>>=o,l-=o,Rn=1<<32-fn(e)+l|t<<l|a,Bn=i+n}else Rn=1<<i|t<<l|a,Bn=n}function yl(n){n.return!==null&&(Zn(n,1),ju(n,1,0))}function pl(n){for(;n===Er;)Er=xt[--At],xt[At]=null,Ia=xt[--At],xt[At]=null;for(;n===ue;)ue=Sn[--_n],Sn[_n]=null,Bn=Sn[--_n],Sn[_n]=null,Rn=Sn[--_n],Sn[_n]=null}function Ou(n,e){Sn[_n++]=Rn,Sn[_n++]=Bn,Sn[_n++]=ue,Rn=e.id,Bn=e.overflow,ue=n}var B0=null,m0=null,P=!1,se=null,xn=!1,bl=Error(u(519));function oe(n){var e=Error(u(418,1<arguments.length&&arguments[1]!==void 0&&arguments[1]?"text":"HTML",""));throw va(bn(e,n)),bl}function zu(n){var e=n.stateNode,t=n.type,a=n.memoizedProps;switch(e[R0]=n,e[$0]=a,t){case"dialog":k("cancel",e),k("close",e);break;case"iframe":case"object":case"embed":k("load",e);break;case"video":case"audio":for(t=0;t<Ha.length;t++)k(Ha[t],e);break;case"source":k("error",e);break;case"img":case"image":case"link":k("error",e),k("load",e);break;case"details":k("toggle",e);break;case"input":k("invalid",e),Lf(e,a.value,a.defaultValue,a.checked,a.defaultChecked,a.type,a.name,!0);break;case"select":k("invalid",e);break;case"textarea":k("invalid",e),Xf(e,a.value,a.defaultValue,a.children)}t=a.children,typeof t!="string"&&typeof t!="number"&&typeof t!="bigint"||e.textContent===""+t||a.suppressHydrationWarning===!0||Ko(e.textContent,t)?(a.popover!=null&&(k("beforetoggle",e),k("toggle",e)),a.onScroll!=null&&k("scroll",e),a.onScrollEnd!=null&&k("scrollend",e),a.onClick!=null&&(e.onclick=Ln),e=!0):e=!1,e||oe(n,!0)}function Du(n){for(B0=n.return;B0;)switch(B0.tag){case 5:case 31:case 13:xn=!1;return;case 27:case 3:xn=!0;return;default:B0=B0.return}}function Et(n){if(n!==B0)return!1;if(!P)return Du(n),P=!0,!1;var e=n.tag,t;if((t=e!==3&&e!==27)&&((t=e===5)&&(t=n.type,t=!(t!=="form"&&t!=="button")||wi(n.type,n.memoizedProps)),t=!t),t&&m0&&oe(n),Du(n),e===13){if(n=n.memoizedState,n=n!==null?n.dehydrated:null,!n)throw Error(u(317));m0=tc(n)}else if(e===31){if(n=n.memoizedState,n=n!==null?n.dehydrated:null,!n)throw Error(u(317));m0=tc(n)}else e===27?(e=m0,Ee(n.type)?(n=Qi,Qi=null,m0=n):m0=e):m0=B0?En(n.stateNode.nextSibling):null;return!0}function Ke(){m0=B0=null,P=!1}function Sl(){var n=se;return n!==null&&(en===null?en=n:en.push.apply(en,n),se=null),n}function va(n){se===null?se=[n]:se.push(n)}var _l=y(null),Je=null,Vn=null;function ce(n,e,t){R(_l,e._currentValue),e._currentValue=t}function Kn(n){n._currentValue=_l.current,C(_l)}function xl(n,e,t){for(;n!==null;){var a=n.alternate;if((n.childLanes&e)!==e?(n.childLanes|=e,a!==null&&(a.childLanes|=e)):a!==null&&(a.childLanes&e)!==e&&(a.childLanes|=e),n===t)break;n=n.return}}function Al(n,e,t,a){var l=n.child;for(l!==null&&(l.return=n);l!==null;){var i=l.dependencies;if(i!==null){var o=l.child;i=i.firstContext;n:for(;i!==null;){var g=i;i=l;for(var m=0;m<e.length;m++)if(g.context===e[m]){i.lanes|=t,g=i.alternate,g!==null&&(g.lanes|=t),xl(i.return,t,n),a||(o=null);break n}i=g.next}}else if(l.tag===18){if(o=l.return,o===null)throw Error(u(341));o.lanes|=t,i=o.alternate,i!==null&&(i.lanes|=t),xl(o,t,n),o=null}else o=l.child;if(o!==null)o.return=l;else for(o=l;o!==null;){if(o===n){o=null;break}if(l=o.sibling,l!==null){l.return=o.return,o=l;break}o=o.return}l=o}}function Tt(n,e,t,a){n=null;for(var l=e,i=!1;l!==null;){if(!i){if((l.flags&524288)!==0)i=!0;else if((l.flags&262144)!==0)break}if(l.tag===10){var o=l.alternate;if(o===null)throw Error(u(387));if(o=o.memoizedProps,o!==null){var g=l.type;un(l.pendingProps.value,o.value)||(n!==null?n.push(g):n=[g])}}else if(l===d0.current){if(o=l.alternate,o===null)throw Error(u(387));o.memoizedState.memoizedState!==l.memoizedState.memoizedState&&(n!==null?n.push(La):n=[La])}l=l.return}n!==null&&Al(e,n,t,a),e.flags|=262144}function Tr(n){for(n=n.firstContext;n!==null;){if(!un(n.context._currentValue,n.memoizedValue))return!0;n=n.next}return!1}function ke(n){Je=n,Vn=null,n=n.dependencies,n!==null&&(n.firstContext=null)}function H0(n){return Cu(Je,n)}function jr(n,e){return Je===null&&ke(n),Cu(n,e)}function Cu(n,e){var t=e._currentValue;if(e={context:e,memoizedValue:t,next:null},Vn===null){if(n===null)throw Error(u(308));Vn=e,n.dependencies={lanes:0,firstContext:e},n.flags|=524288}else Vn=Vn.next=e;return t}var R1=typeof AbortController<"u"?AbortController:function(){var n=[],e=this.signal={aborted:!1,addEventListener:function(t,a){n.push(a)}};this.abort=function(){e.aborted=!0,n.forEach(function(t){return t()})}},B1=r.unstable_scheduleCallback,H1=r.unstable_NormalPriority,j0={$$typeof:Y0,Consumer:null,Provider:null,_currentValue:null,_currentValue2:null,_threadCount:0};function El(){return{controller:new R1,data:new Map,refCount:0}}function ma(n){n.refCount--,n.refCount===0&&B1(H1,function(){n.controller.abort()})}var ha=null,Tl=0,jt=0,Ot=null;function w1(n,e){if(ha===null){var t=ha=[];Tl=0,jt=zi(),Ot={status:"pending",value:void 0,then:function(a){t.push(a)}}}return Tl++,e.then(Nu,Nu),e}function Nu(){if(--Tl===0&&ha!==null){Ot!==null&&(Ot.status="fulfilled");var n=ha;ha=null,jt=0,Ot=null;for(var e=0;e<n.length;e++)(0,n[e])()}}function q1(n,e){var t=[],a={status:"pending",value:null,reason:null,then:function(l){t.push(l)}};return n.then(function(){a.status="fulfilled",a.value=e;for(var l=0;l<t.length;l++)(0,t[l])(e)},function(l){for(a.status="rejected",a.reason=l,l=0;l<t.length;l++)(0,t[l])(void 0)}),a}var Mu=O.S;O.S=function(n,e){ho=dn(),typeof e=="object"&&e!==null&&typeof e.then=="function"&&w1(n,e),Mu!==null&&Mu(n,e)};var $e=y(null);function jl(){var n=$e.current;return n!==null?n:v0.pooledCache}function Or(n,e){e===null?R($e,$e.current):R($e,e.pool)}function Uu(){var n=jl();return n===null?null:{parent:j0._currentValue,pool:n}}var zt=Error(u(460)),Ol=Error(u(474)),zr=Error(u(542)),Dr={then:function(){}};function Ru(n){return n=n.status,n==="fulfilled"||n==="rejected"}function Bu(n,e,t){switch(t=n[t],t===void 0?n.push(e):t!==e&&(e.then(Ln,Ln),e=t),e.status){case"fulfilled":return e.value;case"rejected":throw n=e.reason,wu(n),n;default:if(typeof e.status=="string")e.then(Ln,Ln);else{if(n=v0,n!==null&&100<n.shellSuspendCounter)throw Error(u(482));n=e,n.status="pending",n.then(function(a){if(e.status==="pending"){var l=e;l.status="fulfilled",l.value=a}},function(a){if(e.status==="pending"){var l=e;l.status="rejected",l.reason=a}})}switch(e.status){case"fulfilled":return e.value;case"rejected":throw n=e.reason,wu(n),n}throw Fe=e,zt}}function We(n){try{var e=n._init;return e(n._payload)}catch(t){throw t!==null&&typeof t=="object"&&typeof t.then=="function"?(Fe=t,zt):t}}var Fe=null;function Hu(){if(Fe===null)throw Error(u(459));var n=Fe;return Fe=null,n}function wu(n){if(n===zt||n===zr)throw Error(u(483))}var Dt=null,ya=0;function Cr(n){var e=ya;return ya+=1,Dt===null&&(Dt=[]),Bu(Dt,n,e)}function pa(n,e){e=e.props.ref,n.ref=e!==void 0?e:null}function Nr(n,e){throw e.$$typeof===Y?Error(u(525)):(n=Object.prototype.toString.call(e),Error(u(31,n==="[object Object]"?"object with keys {"+Object.keys(e).join(", ")+"}":n)))}function qu(n){function e(b,h){if(n){var _=b.deletions;_===null?(b.deletions=[h],b.flags|=16):_.push(h)}}function t(b,h){if(!n)return null;for(;h!==null;)e(b,h),h=h.sibling;return null}function a(b){for(var h=new Map;b!==null;)b.key!==null?h.set(b.key,b):h.set(b.index,b),b=b.sibling;return h}function l(b,h){return b=Xn(b,h),b.index=0,b.sibling=null,b}function i(b,h,_){return b.index=_,n?(_=b.alternate,_!==null?(_=_.index,_<h?(b.flags|=67108866,h):_):(b.flags|=67108866,h)):(b.flags|=1048576,h)}function o(b){return n&&b.alternate===null&&(b.flags|=67108866),b}function g(b,h,_,z){return h===null||h.tag!==6?(h=ml(_,b.mode,z),h.return=b,h):(h=l(h,_),h.return=b,h)}function m(b,h,_,z){var q=_.type;return q===T0?j(b,h,_.props.children,z,_.key):h!==null&&(h.elementType===q||typeof q=="object"&&q!==null&&q.$$typeof===J0&&We(q)===h.type)?(h=l(h,_.props),pa(h,_),h.return=b,h):(h=Ar(_.type,_.key,_.props,null,b.mode,z),pa(h,_),h.return=b,h)}function x(b,h,_,z){return h===null||h.tag!==4||h.stateNode.containerInfo!==_.containerInfo||h.stateNode.implementation!==_.implementation?(h=hl(_,b.mode,z),h.return=b,h):(h=l(h,_.children||[]),h.return=b,h)}function j(b,h,_,z,q){return h===null||h.tag!==7?(h=Ve(_,b.mode,z,q),h.return=b,h):(h=l(h,_),h.return=b,h)}function D(b,h,_){if(typeof h=="string"&&h!==""||typeof h=="number"||typeof h=="bigint")return h=ml(""+h,b.mode,_),h.return=b,h;if(typeof h=="object"&&h!==null){switch(h.$$typeof){case u0:return _=Ar(h.type,h.key,h.props,null,b.mode,_),pa(_,h),_.return=b,_;case y0:return h=hl(h,b.mode,_),h.return=b,h;case J0:return h=We(h),D(b,h,_)}if(On(h)||k0(h))return h=Ve(h,b.mode,_,null),h.return=b,h;if(typeof h.then=="function")return D(b,Cr(h),_);if(h.$$typeof===Y0)return D(b,jr(b,h),_);Nr(b,h)}return null}function E(b,h,_,z){var q=h!==null?h.key:null;if(typeof _=="string"&&_!==""||typeof _=="number"||typeof _=="bigint")return q!==null?null:g(b,h,""+_,z);if(typeof _=="object"&&_!==null){switch(_.$$typeof){case u0:return _.key===q?m(b,h,_,z):null;case y0:return _.key===q?x(b,h,_,z):null;case J0:return _=We(_),E(b,h,_,z)}if(On(_)||k0(_))return q!==null?null:j(b,h,_,z,null);if(typeof _.then=="function")return E(b,h,Cr(_),z);if(_.$$typeof===Y0)return E(b,h,jr(b,_),z);Nr(b,_)}return null}function T(b,h,_,z,q){if(typeof z=="string"&&z!==""||typeof z=="number"||typeof z=="bigint")return b=b.get(_)||null,g(h,b,""+z,q);if(typeof z=="object"&&z!==null){switch(z.$$typeof){case u0:return b=b.get(z.key===null?_:z.key)||null,m(h,b,z,q);case y0:return b=b.get(z.key===null?_:z.key)||null,x(h,b,z,q);case J0:return z=We(z),T(b,h,_,z,q)}if(On(z)||k0(z))return b=b.get(_)||null,j(h,b,z,q,null);if(typeof z.then=="function")return T(b,h,_,Cr(z),q);if(z.$$typeof===Y0)return T(b,h,_,jr(h,z),q);Nr(h,z)}return null}function B(b,h,_,z){for(var q=null,t0=null,w=h,V=h=0,W=null;w!==null&&V<_.length;V++){w.index>V?(W=w,w=null):W=w.sibling;var a0=E(b,w,_[V],z);if(a0===null){w===null&&(w=W);break}n&&w&&a0.alternate===null&&e(b,w),h=i(a0,h,V),t0===null?q=a0:t0.sibling=a0,t0=a0,w=W}if(V===_.length)return t(b,w),P&&Zn(b,V),q;if(w===null){for(;V<_.length;V++)w=D(b,_[V],z),w!==null&&(h=i(w,h,V),t0===null?q=w:t0.sibling=w,t0=w);return P&&Zn(b,V),q}for(w=a(w);V<_.length;V++)W=T(w,b,V,_[V],z),W!==null&&(n&&W.alternate!==null&&w.delete(W.key===null?V:W.key),h=i(W,h,V),t0===null?q=W:t0.sibling=W,t0=W);return n&&w.forEach(function(De){return e(b,De)}),P&&Zn(b,V),q}function G(b,h,_,z){if(_==null)throw Error(u(151));for(var q=null,t0=null,w=h,V=h=0,W=null,a0=_.next();w!==null&&!a0.done;V++,a0=_.next()){w.index>V?(W=w,w=null):W=w.sibling;var De=E(b,w,a0.value,z);if(De===null){w===null&&(w=W);break}n&&w&&De.alternate===null&&e(b,w),h=i(De,h,V),t0===null?q=De:t0.sibling=De,t0=De,w=W}if(a0.done)return t(b,w),P&&Zn(b,V),q;if(w===null){for(;!a0.done;V++,a0=_.next())a0=D(b,a0.value,z),a0!==null&&(h=i(a0,h,V),t0===null?q=a0:t0.sibling=a0,t0=a0);return P&&Zn(b,V),q}for(w=a(w);!a0.done;V++,a0=_.next())a0=T(w,b,V,a0.value,z),a0!==null&&(n&&a0.alternate!==null&&w.delete(a0.key===null?V:a0.key),h=i(a0,h,V),t0===null?q=a0:t0.sibling=a0,t0=a0);return n&&w.forEach(function($8){return e(b,$8)}),P&&Zn(b,V),q}function g0(b,h,_,z){if(typeof _=="object"&&_!==null&&_.type===T0&&_.key===null&&(_=_.props.children),typeof _=="object"&&_!==null){switch(_.$$typeof){case u0:n:{for(var q=_.key;h!==null;){if(h.key===q){if(q=_.type,q===T0){if(h.tag===7){t(b,h.sibling),z=l(h,_.props.children),z.return=b,b=z;break n}}else if(h.elementType===q||typeof q=="object"&&q!==null&&q.$$typeof===J0&&We(q)===h.type){t(b,h.sibling),z=l(h,_.props),pa(z,_),z.return=b,b=z;break n}t(b,h);break}else e(b,h);h=h.sibling}_.type===T0?(z=Ve(_.props.children,b.mode,z,_.key),z.return=b,b=z):(z=Ar(_.type,_.key,_.props,null,b.mode,z),pa(z,_),z.return=b,b=z)}return o(b);case y0:n:{for(q=_.key;h!==null;){if(h.key===q)if(h.tag===4&&h.stateNode.containerInfo===_.containerInfo&&h.stateNode.implementation===_.implementation){t(b,h.sibling),z=l(h,_.children||[]),z.return=b,b=z;break n}else{t(b,h);break}else e(b,h);h=h.sibling}z=hl(_,b.mode,z),z.return=b,b=z}return o(b);case J0:return _=We(_),g0(b,h,_,z)}if(On(_))return B(b,h,_,z);if(k0(_)){if(q=k0(_),typeof q!="function")throw Error(u(150));return _=q.call(_),G(b,h,_,z)}if(typeof _.then=="function")return g0(b,h,Cr(_),z);if(_.$$typeof===Y0)return g0(b,h,jr(b,_),z);Nr(b,_)}return typeof _=="string"&&_!==""||typeof _=="number"||typeof _=="bigint"?(_=""+_,h!==null&&h.tag===6?(t(b,h.sibling),z=l(h,_),z.return=b,b=z):(t(b,h),z=ml(_,b.mode,z),z.return=b,b=z),o(b)):t(b,h)}return function(b,h,_,z){try{ya=0;var q=g0(b,h,_,z);return Dt=null,q}catch(w){if(w===zt||w===zr)throw w;var t0=sn(29,w,null,b.mode);return t0.lanes=z,t0.return=b,t0}finally{}}}var Pe=qu(!0),Yu=qu(!1),ge=!1;function zl(n){n.updateQueue={baseState:n.memoizedState,firstBaseUpdate:null,lastBaseUpdate:null,shared:{pending:null,lanes:0,hiddenCallbacks:null},callbacks:null}}function Dl(n,e){n=n.updateQueue,e.updateQueue===n&&(e.updateQueue={baseState:n.baseState,firstBaseUpdate:n.firstBaseUpdate,lastBaseUpdate:n.lastBaseUpdate,shared:n.shared,callbacks:null})}function Ie(n){return{lane:n,tag:0,payload:null,callback:null,next:null}}function ve(n,e,t){var a=n.updateQueue;if(a===null)return null;if(a=a.shared,(r0&2)!==0){var l=a.pending;return l===null?e.next=e:(e.next=l.next,l.next=e),a.pending=e,e=xr(n),xu(n,null,t),e}return _r(n,a,e,t),xr(n)}function ba(n,e,t){if(e=e.updateQueue,e!==null&&(e=e.shared,(t&4194048)!==0)){var a=e.lanes;a&=n.pendingLanes,t|=a,e.lanes=t,Cf(n,t)}}function Cl(n,e){var t=n.updateQueue,a=n.alternate;if(a!==null&&(a=a.updateQueue,t===a)){var l=null,i=null;if(t=t.firstBaseUpdate,t!==null){do{var o={lane:t.lane,tag:t.tag,payload:t.payload,callback:null,next:null};i===null?l=i=o:i=i.next=o,t=t.next}while(t!==null);i===null?l=i=e:i=i.next=e}else l=i=e;t={baseState:a.baseState,firstBaseUpdate:l,lastBaseUpdate:i,shared:a.shared,callbacks:a.callbacks},n.updateQueue=t;return}n=t.lastBaseUpdate,n===null?t.firstBaseUpdate=e:n.next=e,t.lastBaseUpdate=e}var Nl=!1;function Sa(){if(Nl){var n=Ot;if(n!==null)throw n}}function _a(n,e,t,a){Nl=!1;var l=n.updateQueue;ge=!1;var i=l.firstBaseUpdate,o=l.lastBaseUpdate,g=l.shared.pending;if(g!==null){l.shared.pending=null;var m=g,x=m.next;m.next=null,o===null?i=x:o.next=x,o=m;var j=n.alternate;j!==null&&(j=j.updateQueue,g=j.lastBaseUpdate,g!==o&&(g===null?j.firstBaseUpdate=x:g.next=x,j.lastBaseUpdate=m))}if(i!==null){var D=l.baseState;o=0,j=x=m=null,g=i;do{var E=g.lane&-536870913,T=E!==g.lane;if(T?($&E)===E:(a&E)===E){E!==0&&E===jt&&(Nl=!0),j!==null&&(j=j.next={lane:0,tag:g.tag,payload:g.payload,callback:null,next:null});n:{var B=n,G=g;E=e;var g0=t;switch(G.tag){case 1:if(B=G.payload,typeof B=="function"){D=B.call(g0,D,E);break n}D=B;break n;case 3:B.flags=B.flags&-65537|128;case 0:if(B=G.payload,E=typeof B=="function"?B.call(g0,D,E):B,E==null)break n;D=U({},D,E);break n;case 2:ge=!0}}E=g.callback,E!==null&&(n.flags|=64,T&&(n.flags|=8192),T=l.callbacks,T===null?l.callbacks=[E]:T.push(E))}else T={lane:E,tag:g.tag,payload:g.payload,callback:g.callback,next:null},j===null?(x=j=T,m=D):j=j.next=T,o|=E;if(g=g.next,g===null){if(g=l.shared.pending,g===null)break;T=g,g=T.next,T.next=null,l.lastBaseUpdate=T,l.shared.pending=null}}while(!0);j===null&&(m=D),l.baseState=m,l.firstBaseUpdate=x,l.lastBaseUpdate=j,i===null&&(l.shared.lanes=0),be|=o,n.lanes=o,n.memoizedState=D}}function Gu(n,e){if(typeof n!="function")throw Error(u(191,n));n.call(e)}function Lu(n,e){var t=n.callbacks;if(t!==null)for(n.callbacks=null,n=0;n<t.length;n++)Gu(t[n],e)}var Ct=y(null),Mr=y(0);function Qu(n,e){n=te,R(Mr,n),R(Ct,e),te=n|e.baseLanes}function Ml(){R(Mr,te),R(Ct,Ct.current)}function Ul(){te=Mr.current,C(Ct),C(Mr)}var on=y(null),An=null;function me(n){var e=n.alternate;R(A0,A0.current&1),R(on,n),An===null&&(e===null||Ct.current!==null||e.memoizedState!==null)&&(An=n)}function Rl(n){R(A0,A0.current),R(on,n),An===null&&(An=n)}function Xu(n){n.tag===22?(R(A0,A0.current),R(on,n),An===null&&(An=n)):he()}function he(){R(A0,A0.current),R(on,on.current)}function cn(n){C(on),An===n&&(An=null),C(A0)}var A0=y(0);function Ur(n){for(var e=n;e!==null;){if(e.tag===13){var t=e.memoizedState;if(t!==null&&(t=t.dehydrated,t===null||Gi(t)||Li(t)))return e}else if(e.tag===19&&(e.memoizedProps.revealOrder==="forwards"||e.memoizedProps.revealOrder==="backwards"||e.memoizedProps.revealOrder==="unstable_legacy-backwards"||e.memoizedProps.revealOrder==="together")){if((e.flags&128)!==0)return e}else if(e.child!==null){e.child.return=e,e=e.child;continue}if(e===n)break;for(;e.sibling===null;){if(e.return===null||e.return===n)return null;e=e.return}e.sibling.return=e.return,e=e.sibling}return null}var Jn=0,Z=null,o0=null,O0=null,Rr=!1,Nt=!1,nt=!1,Br=0,xa=0,Mt=null,Y1=0;function b0(){throw Error(u(321))}function Bl(n,e){if(e===null)return!1;for(var t=0;t<e.length&&t<n.length;t++)if(!un(n[t],e[t]))return!1;return!0}function Hl(n,e,t,a,l,i){return Jn=i,Z=e,e.memoizedState=null,e.updateQueue=null,e.lanes=0,O.H=n===null||n.memoizedState===null?js:Fl,nt=!1,i=t(a,l),nt=!1,Nt&&(i=Vu(e,t,a,l)),Zu(n),i}function Zu(n){O.H=Ta;var e=o0!==null&&o0.next!==null;if(Jn=0,O0=o0=Z=null,Rr=!1,xa=0,Mt=null,e)throw Error(u(300));n===null||z0||(n=n.dependencies,n!==null&&Tr(n)&&(z0=!0))}function Vu(n,e,t,a){Z=n;var l=0;do{if(Nt&&(Mt=null),xa=0,Nt=!1,25<=l)throw Error(u(301));if(l+=1,O0=o0=null,n.updateQueue!=null){var i=n.updateQueue;i.lastEffect=null,i.events=null,i.stores=null,i.memoCache!=null&&(i.memoCache.index=0)}O.H=Os,i=e(t,a)}while(Nt);return i}function G1(){var n=O.H,e=n.useState()[0];return e=typeof e.then=="function"?Aa(e):e,n=n.useState()[0],(o0!==null?o0.memoizedState:null)!==n&&(Z.flags|=1024),e}function wl(){var n=Br!==0;return Br=0,n}function ql(n,e,t){e.updateQueue=n.updateQueue,e.flags&=-2053,n.lanes&=~t}function Yl(n){if(Rr){for(n=n.memoizedState;n!==null;){var e=n.queue;e!==null&&(e.pending=null),n=n.next}Rr=!1}Jn=0,O0=o0=Z=null,Nt=!1,xa=Br=0,Mt=null}function Z0(){var n={memoizedState:null,baseState:null,baseQueue:null,queue:null,next:null};return O0===null?Z.memoizedState=O0=n:O0=O0.next=n,O0}function E0(){if(o0===null){var n=Z.alternate;n=n!==null?n.memoizedState:null}else n=o0.next;var e=O0===null?Z.memoizedState:O0.next;if(e!==null)O0=e,o0=n;else{if(n===null)throw Z.alternate===null?Error(u(467)):Error(u(310));o0=n,n={memoizedState:o0.memoizedState,baseState:o0.baseState,baseQueue:o0.baseQueue,queue:o0.queue,next:null},O0===null?Z.memoizedState=O0=n:O0=O0.next=n}return O0}function Hr(){return{lastEffect:null,events:null,stores:null,memoCache:null}}function Aa(n){var e=xa;return xa+=1,Mt===null&&(Mt=[]),n=Bu(Mt,n,e),e=Z,(O0===null?e.memoizedState:O0.next)===null&&(e=e.alternate,O.H=e===null||e.memoizedState===null?js:Fl),n}function wr(n){if(n!==null&&typeof n=="object"){if(typeof n.then=="function")return Aa(n);if(n.$$typeof===Y0)return H0(n)}throw Error(u(438,String(n)))}function Gl(n){var e=null,t=Z.updateQueue;if(t!==null&&(e=t.memoCache),e==null){var a=Z.alternate;a!==null&&(a=a.updateQueue,a!==null&&(a=a.memoCache,a!=null&&(e={data:a.data.map(function(l){return l.slice()}),index:0})))}if(e==null&&(e={data:[],index:0}),t===null&&(t=Hr(),Z.updateQueue=t),t.memoCache=e,t=e.data[e.index],t===void 0)for(t=e.data[e.index]=Array(n),a=0;a<n;a++)t[a]=ft;return e.index++,t}function kn(n,e){return typeof e=="function"?e(n):e}function qr(n){var e=E0();return Ll(e,o0,n)}function Ll(n,e,t){var a=n.queue;if(a===null)throw Error(u(311));a.lastRenderedReducer=t;var l=n.baseQueue,i=a.pending;if(i!==null){if(l!==null){var o=l.next;l.next=i.next,i.next=o}e.baseQueue=l=i,a.pending=null}if(i=n.baseState,l===null)n.memoizedState=i;else{e=l.next;var g=o=null,m=null,x=e,j=!1;do{var D=x.lane&-536870913;if(D!==x.lane?($&D)===D:(Jn&D)===D){var E=x.revertLane;if(E===0)m!==null&&(m=m.next={lane:0,revertLane:0,gesture:null,action:x.action,hasEagerState:x.hasEagerState,eagerState:x.eagerState,next:null}),D===jt&&(j=!0);else if((Jn&E)===E){x=x.next,E===jt&&(j=!0);continue}else D={lane:0,revertLane:x.revertLane,gesture:null,action:x.action,hasEagerState:x.hasEagerState,eagerState:x.eagerState,next:null},m===null?(g=m=D,o=i):m=m.next=D,Z.lanes|=E,be|=E;D=x.action,nt&&t(i,D),i=x.hasEagerState?x.eagerState:t(i,D)}else E={lane:D,revertLane:x.revertLane,gesture:x.gesture,action:x.action,hasEagerState:x.hasEagerState,eagerState:x.eagerState,next:null},m===null?(g=m=E,o=i):m=m.next=E,Z.lanes|=D,be|=D;x=x.next}while(x!==null&&x!==e);if(m===null?o=i:m.next=g,!un(i,n.memoizedState)&&(z0=!0,j&&(t=Ot,t!==null)))throw t;n.memoizedState=i,n.baseState=o,n.baseQueue=m,a.lastRenderedState=i}return l===null&&(a.lanes=0),[n.memoizedState,a.dispatch]}function Ql(n){var e=E0(),t=e.queue;if(t===null)throw Error(u(311));t.lastRenderedReducer=n;var a=t.dispatch,l=t.pending,i=e.memoizedState;if(l!==null){t.pending=null;var o=l=l.next;do i=n(i,o.action),o=o.next;while(o!==l);un(i,e.memoizedState)||(z0=!0),e.memoizedState=i,e.baseQueue===null&&(e.baseState=i),t.lastRenderedState=i}return[i,a]}function Ku(n,e,t){var a=Z,l=E0(),i=P;if(i){if(t===void 0)throw Error(u(407));t=t()}else t=e();var o=!un((o0||l).memoizedState,t);if(o&&(l.memoizedState=t,z0=!0),l=l.queue,Vl($u.bind(null,a,l,n),[n]),l.getSnapshot!==e||o||O0!==null&&O0.memoizedState.tag&1){if(a.flags|=2048,Ut(9,{destroy:void 0},ku.bind(null,a,l,t,e),null),v0===null)throw Error(u(349));i||(Jn&127)!==0||Ju(a,e,t)}return t}function Ju(n,e,t){n.flags|=16384,n={getSnapshot:e,value:t},e=Z.updateQueue,e===null?(e=Hr(),Z.updateQueue=e,e.stores=[n]):(t=e.stores,t===null?e.stores=[n]:t.push(n))}function ku(n,e,t,a){e.value=t,e.getSnapshot=a,Wu(e)&&Fu(n)}function $u(n,e,t){return t(function(){Wu(e)&&Fu(n)})}function Wu(n){var e=n.getSnapshot;n=n.value;try{var t=e();return!un(n,t)}catch{return!0}}function Fu(n){var e=Ze(n,2);e!==null&&tn(e,n,2)}function Xl(n){var e=Z0();if(typeof n=="function"){var t=n;if(n=t(),nt){le(!0);try{t()}finally{le(!1)}}}return e.memoizedState=e.baseState=n,e.queue={pending:null,lanes:0,dispatch:null,lastRenderedReducer:kn,lastRenderedState:n},e}function Pu(n,e,t,a){return n.baseState=t,Ll(n,o0,typeof a=="function"?a:kn)}function L1(n,e,t,a,l){if(Lr(n))throw Error(u(485));if(n=e.action,n!==null){var i={payload:l,action:n,next:null,isTransition:!0,status:"pending",value:null,reason:null,listeners:[],then:function(o){i.listeners.push(o)}};O.T!==null?t(!0):i.isTransition=!1,a(i),t=e.pending,t===null?(i.next=e.pending=i,ns(e,i)):(i.next=t.next,e.pending=t.next=i)}}function ns(n,e){var t=e.action,a=e.payload,l=n.state;if(e.isTransition){var i=O.T,o={};O.T=o;try{var g=t(l,a),m=O.S;m!==null&&m(o,g),es(n,e,g)}catch(x){Zl(n,e,x)}finally{i!==null&&o.types!==null&&(i.types=o.types),O.T=i}}else try{i=t(l,a),es(n,e,i)}catch(x){Zl(n,e,x)}}function es(n,e,t){t!==null&&typeof t=="object"&&typeof t.then=="function"?t.then(function(a){ts(n,e,a)},function(a){return Zl(n,e,a)}):ts(n,e,t)}function ts(n,e,t){e.status="fulfilled",e.value=t,as(e),n.state=t,e=n.pending,e!==null&&(t=e.next,t===e?n.pending=null:(t=t.next,e.next=t,ns(n,t)))}function Zl(n,e,t){var a=n.pending;if(n.pending=null,a!==null){a=a.next;do e.status="rejected",e.reason=t,as(e),e=e.next;while(e!==a)}n.action=null}function as(n){n=n.listeners;for(var e=0;e<n.length;e++)(0,n[e])()}function rs(n,e){return e}function ds(n,e){if(P){var t=v0.formState;if(t!==null){n:{var a=Z;if(P){if(m0){e:{for(var l=m0,i=xn;l.nodeType!==8;){if(!i){l=null;break e}if(l=En(l.nextSibling),l===null){l=null;break e}}i=l.data,l=i==="F!"||i==="F"?l:null}if(l){m0=En(l.nextSibling),a=l.data==="F!";break n}}oe(a)}a=!1}a&&(e=t[0])}}return t=Z0(),t.memoizedState=t.baseState=e,a={pending:null,lanes:0,dispatch:null,lastRenderedReducer:rs,lastRenderedState:e},t.queue=a,t=As.bind(null,Z,a),a.dispatch=t,a=Xl(!1),i=Wl.bind(null,Z,!1,a.queue),a=Z0(),l={state:e,dispatch:null,action:n,pending:null},a.queue=l,t=L1.bind(null,Z,l,i,t),l.dispatch=t,a.memoizedState=n,[e,t,!1]}function ls(n){var e=E0();return is(e,o0,n)}function is(n,e,t){if(e=Ll(n,e,rs)[0],n=qr(kn)[0],typeof e=="object"&&e!==null&&typeof e.then=="function")try{var a=Aa(e)}catch(o){throw o===zt?zr:o}else a=e;e=E0();var l=e.queue,i=l.dispatch;return t!==e.memoizedState&&(Z.flags|=2048,Ut(9,{destroy:void 0},Q1.bind(null,l,t),null)),[a,i,n]}function Q1(n,e){n.action=e}function fs(n){var e=E0(),t=o0;if(t!==null)return is(e,t,n);E0(),e=e.memoizedState,t=E0();var a=t.queue.dispatch;return t.memoizedState=n,[e,a,!1]}function Ut(n,e,t,a){return n={tag:n,create:t,deps:a,inst:e,next:null},e=Z.updateQueue,e===null&&(e=Hr(),Z.updateQueue=e),t=e.lastEffect,t===null?e.lastEffect=n.next=n:(a=t.next,t.next=n,n.next=a,e.lastEffect=n),n}function us(){return E0().memoizedState}function Yr(n,e,t,a){var l=Z0();Z.flags|=n,l.memoizedState=Ut(1|e,{destroy:void 0},t,a===void 0?null:a)}function Gr(n,e,t,a){var l=E0();a=a===void 0?null:a;var i=l.memoizedState.inst;o0!==null&&a!==null&&Bl(a,o0.memoizedState.deps)?l.memoizedState=Ut(e,i,t,a):(Z.flags|=n,l.memoizedState=Ut(1|e,i,t,a))}function ss(n,e){Yr(8390656,8,n,e)}function Vl(n,e){Gr(2048,8,n,e)}function X1(n){Z.flags|=4;var e=Z.updateQueue;if(e===null)e=Hr(),Z.updateQueue=e,e.events=[n];else{var t=e.events;t===null?e.events=[n]:t.push(n)}}function os(n){var e=E0().memoizedState;return X1({ref:e,nextImpl:n}),function(){if((r0&2)!==0)throw Error(u(440));return e.impl.apply(void 0,arguments)}}function cs(n,e){return Gr(4,2,n,e)}function gs(n,e){return Gr(4,4,n,e)}function Is(n,e){if(typeof e=="function"){n=n();var t=e(n);return function(){typeof t=="function"?t():e(null)}}if(e!=null)return n=n(),e.current=n,function(){e.current=null}}function vs(n,e,t){t=t!=null?t.concat([n]):null,Gr(4,4,Is.bind(null,e,n),t)}function Kl(){}function ms(n,e){var t=E0();e=e===void 0?null:e;var a=t.memoizedState;return e!==null&&Bl(e,a[1])?a[0]:(t.memoizedState=[n,e],n)}function hs(n,e){var t=E0();e=e===void 0?null:e;var a=t.memoizedState;if(e!==null&&Bl(e,a[1]))return a[0];if(a=n(),nt){le(!0);try{n()}finally{le(!1)}}return t.memoizedState=[a,e],a}function Jl(n,e,t){return t===void 0||(Jn&1073741824)!==0&&($&261930)===0?n.memoizedState=e:(n.memoizedState=t,n=po(),Z.lanes|=n,be|=n,t)}function ys(n,e,t,a){return un(t,e)?t:Ct.current!==null?(n=Jl(n,t,a),un(n,e)||(z0=!0),n):(Jn&42)===0||(Jn&1073741824)!==0&&($&261930)===0?(z0=!0,n.memoizedState=t):(n=po(),Z.lanes|=n,be|=n,e)}function ps(n,e,t,a,l){var i=M.p;M.p=i!==0&&8>i?i:8;var o=O.T,g={};O.T=g,Wl(n,!1,e,t);try{var m=l(),x=O.S;if(x!==null&&x(g,m),m!==null&&typeof m=="object"&&typeof m.then=="function"){var j=q1(m,a);Ea(n,e,j,vn(n))}else Ea(n,e,a,vn(n))}catch(D){Ea(n,e,{then:function(){},status:"rejected",reason:D},vn())}finally{M.p=i,o!==null&&g.types!==null&&(o.types=g.types),O.T=o}}function Z1(){}function kl(n,e,t,a){if(n.tag!==5)throw Error(u(476));var l=bs(n).queue;ps(n,l,e,L,t===null?Z1:function(){return Ss(n),t(a)})}function bs(n){var e=n.memoizedState;if(e!==null)return e;e={memoizedState:L,baseState:L,baseQueue:null,queue:{pending:null,lanes:0,dispatch:null,lastRenderedReducer:kn,lastRenderedState:L},next:null};var t={};return e.next={memoizedState:t,baseState:t,baseQueue:null,queue:{pending:null,lanes:0,dispatch:null,lastRenderedReducer:kn,lastRenderedState:t},next:null},n.memoizedState=e,n=n.alternate,n!==null&&(n.memoizedState=e),e}function Ss(n){var e=bs(n);e.next===null&&(e=n.alternate.memoizedState),Ea(n,e.next.queue,{},vn())}function $l(){return H0(La)}function _s(){return E0().memoizedState}function xs(){return E0().memoizedState}function V1(n){for(var e=n.return;e!==null;){switch(e.tag){case 24:case 3:var t=vn();n=Ie(t);var a=ve(e,n,t);a!==null&&(tn(a,e,t),ba(a,e,t)),e={cache:El()},n.payload=e;return}e=e.return}}function K1(n,e,t){var a=vn();t={lane:a,revertLane:0,gesture:null,action:t,hasEagerState:!1,eagerState:null,next:null},Lr(n)?Es(e,t):(t=Il(n,e,t,a),t!==null&&(tn(t,n,a),Ts(t,e,a)))}function As(n,e,t){var a=vn();Ea(n,e,t,a)}function Ea(n,e,t,a){var l={lane:a,revertLane:0,gesture:null,action:t,hasEagerState:!1,eagerState:null,next:null};if(Lr(n))Es(e,l);else{var i=n.alternate;if(n.lanes===0&&(i===null||i.lanes===0)&&(i=e.lastRenderedReducer,i!==null))try{var o=e.lastRenderedState,g=i(o,t);if(l.hasEagerState=!0,l.eagerState=g,un(g,o))return _r(n,e,l,0),v0===null&&Sr(),!1}catch{}finally{}if(t=Il(n,e,l,a),t!==null)return tn(t,n,a),Ts(t,e,a),!0}return!1}function Wl(n,e,t,a){if(a={lane:2,revertLane:zi(),gesture:null,action:a,hasEagerState:!1,eagerState:null,next:null},Lr(n)){if(e)throw Error(u(479))}else e=Il(n,t,a,2),e!==null&&tn(e,n,2)}function Lr(n){var e=n.alternate;return n===Z||e!==null&&e===Z}function Es(n,e){Nt=Rr=!0;var t=n.pending;t===null?e.next=e:(e.next=t.next,t.next=e),n.pending=e}function Ts(n,e,t){if((t&4194048)!==0){var a=e.lanes;a&=n.pendingLanes,t|=a,e.lanes=t,Cf(n,t)}}var Ta={readContext:H0,use:wr,useCallback:b0,useContext:b0,useEffect:b0,useImperativeHandle:b0,useLayoutEffect:b0,useInsertionEffect:b0,useMemo:b0,useReducer:b0,useRef:b0,useState:b0,useDebugValue:b0,useDeferredValue:b0,useTransition:b0,useSyncExternalStore:b0,useId:b0,useHostTransitionStatus:b0,useFormState:b0,useActionState:b0,useOptimistic:b0,useMemoCache:b0,useCacheRefresh:b0};Ta.useEffectEvent=b0;var js={readContext:H0,use:wr,useCallback:function(n,e){return Z0().memoizedState=[n,e===void 0?null:e],n},useContext:H0,useEffect:ss,useImperativeHandle:function(n,e,t){t=t!=null?t.concat([n]):null,Yr(4194308,4,Is.bind(null,e,n),t)},useLayoutEffect:function(n,e){return Yr(4194308,4,n,e)},useInsertionEffect:function(n,e){Yr(4,2,n,e)},useMemo:function(n,e){var t=Z0();e=e===void 0?null:e;var a=n();if(nt){le(!0);try{n()}finally{le(!1)}}return t.memoizedState=[a,e],a},useReducer:function(n,e,t){var a=Z0();if(t!==void 0){var l=t(e);if(nt){le(!0);try{t(e)}finally{le(!1)}}}else l=e;return a.memoizedState=a.baseState=l,n={pending:null,lanes:0,dispatch:null,lastRenderedReducer:n,lastRenderedState:l},a.queue=n,n=n.dispatch=K1.bind(null,Z,n),[a.memoizedState,n]},useRef:function(n){var e=Z0();return n={current:n},e.memoizedState=n},useState:function(n){n=Xl(n);var e=n.queue,t=As.bind(null,Z,e);return e.dispatch=t,[n.memoizedState,t]},useDebugValue:Kl,useDeferredValue:function(n,e){var t=Z0();return Jl(t,n,e)},useTransition:function(){var n=Xl(!1);return n=ps.bind(null,Z,n.queue,!0,!1),Z0().memoizedState=n,[!1,n]},useSyncExternalStore:function(n,e,t){var a=Z,l=Z0();if(P){if(t===void 0)throw Error(u(407));t=t()}else{if(t=e(),v0===null)throw Error(u(349));($&127)!==0||Ju(a,e,t)}l.memoizedState=t;var i={value:t,getSnapshot:e};return l.queue=i,ss($u.bind(null,a,i,n),[n]),a.flags|=2048,Ut(9,{destroy:void 0},ku.bind(null,a,i,t,e),null),t},useId:function(){var n=Z0(),e=v0.identifierPrefix;if(P){var t=Bn,a=Rn;t=(a&~(1<<32-fn(a)-1)).toString(32)+t,e="_"+e+"R_"+t,t=Br++,0<t&&(e+="H"+t.toString(32)),e+="_"}else t=Y1++,e="_"+e+"r_"+t.toString(32)+"_";return n.memoizedState=e},useHostTransitionStatus:$l,useFormState:ds,useActionState:ds,useOptimistic:function(n){var e=Z0();e.memoizedState=e.baseState=n;var t={pending:null,lanes:0,dispatch:null,lastRenderedReducer:null,lastRenderedState:null};return e.queue=t,e=Wl.bind(null,Z,!0,t),t.dispatch=e,[n,e]},useMemoCache:Gl,useCacheRefresh:function(){return Z0().memoizedState=V1.bind(null,Z)},useEffectEvent:function(n){var e=Z0(),t={impl:n};return e.memoizedState=t,function(){if((r0&2)!==0)throw Error(u(440));return t.impl.apply(void 0,arguments)}}},Fl={readContext:H0,use:wr,useCallback:ms,useContext:H0,useEffect:Vl,useImperativeHandle:vs,useInsertionEffect:cs,useLayoutEffect:gs,useMemo:hs,useReducer:qr,useRef:us,useState:function(){return qr(kn)},useDebugValue:Kl,useDeferredValue:function(n,e){var t=E0();return ys(t,o0.memoizedState,n,e)},useTransition:function(){var n=qr(kn)[0],e=E0().memoizedState;return[typeof n=="boolean"?n:Aa(n),e]},useSyncExternalStore:Ku,useId:_s,useHostTransitionStatus:$l,useFormState:ls,useActionState:ls,useOptimistic:function(n,e){var t=E0();return Pu(t,o0,n,e)},useMemoCache:Gl,useCacheRefresh:xs};Fl.useEffectEvent=os;var Os={readContext:H0,use:wr,useCallback:ms,useContext:H0,useEffect:Vl,useImperativeHandle:vs,useInsertionEffect:cs,useLayoutEffect:gs,useMemo:hs,useReducer:Ql,useRef:us,useState:function(){return Ql(kn)},useDebugValue:Kl,useDeferredValue:function(n,e){var t=E0();return o0===null?Jl(t,n,e):ys(t,o0.memoizedState,n,e)},useTransition:function(){var n=Ql(kn)[0],e=E0().memoizedState;return[typeof n=="boolean"?n:Aa(n),e]},useSyncExternalStore:Ku,useId:_s,useHostTransitionStatus:$l,useFormState:fs,useActionState:fs,useOptimistic:function(n,e){var t=E0();return o0!==null?Pu(t,o0,n,e):(t.baseState=n,[n,t.queue.dispatch])},useMemoCache:Gl,useCacheRefresh:xs};Os.useEffectEvent=os;function Pl(n,e,t,a){e=n.memoizedState,t=t(a,e),t=t==null?e:U({},e,t),n.memoizedState=t,n.lanes===0&&(n.updateQueue.baseState=t)}var ni={enqueueSetState:function(n,e,t){n=n._reactInternals;var a=vn(),l=Ie(a);l.payload=e,t!=null&&(l.callback=t),e=ve(n,l,a),e!==null&&(tn(e,n,a),ba(e,n,a))},enqueueReplaceState:function(n,e,t){n=n._reactInternals;var a=vn(),l=Ie(a);l.tag=1,l.payload=e,t!=null&&(l.callback=t),e=ve(n,l,a),e!==null&&(tn(e,n,a),ba(e,n,a))},enqueueForceUpdate:function(n,e){n=n._reactInternals;var t=vn(),a=Ie(t);a.tag=2,e!=null&&(a.callback=e),e=ve(n,a,t),e!==null&&(tn(e,n,t),ba(e,n,t))}};function zs(n,e,t,a,l,i,o){return n=n.stateNode,typeof n.shouldComponentUpdate=="function"?n.shouldComponentUpdate(a,i,o):e.prototype&&e.prototype.isPureReactComponent?!ca(t,a)||!ca(l,i):!0}function Ds(n,e,t,a){n=e.state,typeof e.componentWillReceiveProps=="function"&&e.componentWillReceiveProps(t,a),typeof e.UNSAFE_componentWillReceiveProps=="function"&&e.UNSAFE_componentWillReceiveProps(t,a),e.state!==n&&ni.enqueueReplaceState(e,e.state,null)}function et(n,e){var t=e;if("ref"in e){t={};for(var a in e)a!=="ref"&&(t[a]=e[a])}if(n=n.defaultProps){t===e&&(t=U({},t));for(var l in n)t[l]===void 0&&(t[l]=n[l])}return t}function Cs(n){br(n)}function Ns(n){console.error(n)}function Ms(n){br(n)}function Qr(n,e){try{var t=n.onUncaughtError;t(e.value,{componentStack:e.stack})}catch(a){setTimeout(function(){throw a})}}function Us(n,e,t){try{var a=n.onCaughtError;a(t.value,{componentStack:t.stack,errorBoundary:e.tag===1?e.stateNode:null})}catch(l){setTimeout(function(){throw l})}}function ei(n,e,t){return t=Ie(t),t.tag=3,t.payload={element:null},t.callback=function(){Qr(n,e)},t}function Rs(n){return n=Ie(n),n.tag=3,n}function Bs(n,e,t,a){var l=t.type.getDerivedStateFromError;if(typeof l=="function"){var i=a.value;n.payload=function(){return l(i)},n.callback=function(){Us(e,t,a)}}var o=t.stateNode;o!==null&&typeof o.componentDidCatch=="function"&&(n.callback=function(){Us(e,t,a),typeof l!="function"&&(Se===null?Se=new Set([this]):Se.add(this));var g=a.stack;this.componentDidCatch(a.value,{componentStack:g!==null?g:""})})}function J1(n,e,t,a,l){if(t.flags|=32768,a!==null&&typeof a=="object"&&typeof a.then=="function"){if(e=t.alternate,e!==null&&Tt(e,t,l,!0),t=on.current,t!==null){switch(t.tag){case 31:case 13:return An===null?ed():t.alternate===null&&S0===0&&(S0=3),t.flags&=-257,t.flags|=65536,t.lanes=l,a===Dr?t.flags|=16384:(e=t.updateQueue,e===null?t.updateQueue=new Set([a]):e.add(a),Ti(n,a,l)),!1;case 22:return t.flags|=65536,a===Dr?t.flags|=16384:(e=t.updateQueue,e===null?(e={transitions:null,markerInstances:null,retryQueue:new Set([a])},t.updateQueue=e):(t=e.retryQueue,t===null?e.retryQueue=new Set([a]):t.add(a)),Ti(n,a,l)),!1}throw Error(u(435,t.tag))}return Ti(n,a,l),ed(),!1}if(P)return e=on.current,e!==null?((e.flags&65536)===0&&(e.flags|=256),e.flags|=65536,e.lanes=l,a!==bl&&(n=Error(u(422),{cause:a}),va(bn(n,t)))):(a!==bl&&(e=Error(u(423),{cause:a}),va(bn(e,t))),n=n.current.alternate,n.flags|=65536,l&=-l,n.lanes|=l,a=bn(a,t),l=ei(n.stateNode,a,l),Cl(n,l),S0!==4&&(S0=2)),!1;var i=Error(u(520),{cause:a});if(i=bn(i,t),Ua===null?Ua=[i]:Ua.push(i),S0!==4&&(S0=2),e===null)return!0;a=bn(a,t),t=e;do{switch(t.tag){case 3:return t.flags|=65536,n=l&-l,t.lanes|=n,n=ei(t.stateNode,a,n),Cl(t,n),!1;case 1:if(e=t.type,i=t.stateNode,(t.flags&128)===0&&(typeof e.getDerivedStateFromError=="function"||i!==null&&typeof i.componentDidCatch=="function"&&(Se===null||!Se.has(i))))return t.flags|=65536,l&=-l,t.lanes|=l,l=Rs(l),Bs(l,n,t,a),Cl(t,l),!1}t=t.return}while(t!==null);return!1}var ti=Error(u(461)),z0=!1;function w0(n,e,t,a){e.child=n===null?Yu(e,null,t,a):Pe(e,n.child,t,a)}function Hs(n,e,t,a,l){t=t.render;var i=e.ref;if("ref"in a){var o={};for(var g in a)g!=="ref"&&(o[g]=a[g])}else o=a;return ke(e),a=Hl(n,e,t,o,i,l),g=wl(),n!==null&&!z0?(ql(n,e,l),$n(n,e,l)):(P&&g&&yl(e),e.flags|=1,w0(n,e,a,l),e.child)}function ws(n,e,t,a,l){if(n===null){var i=t.type;return typeof i=="function"&&!vl(i)&&i.defaultProps===void 0&&t.compare===null?(e.tag=15,e.type=i,qs(n,e,i,a,l)):(n=Ar(t.type,null,a,e,e.mode,l),n.ref=e.ref,n.return=e,e.child=n)}if(i=n.child,!si(n,l)){var o=i.memoizedProps;if(t=t.compare,t=t!==null?t:ca,t(o,a)&&n.ref===e.ref)return $n(n,e,l)}return e.flags|=1,n=Xn(i,a),n.ref=e.ref,n.return=e,e.child=n}function qs(n,e,t,a,l){if(n!==null){var i=n.memoizedProps;if(ca(i,a)&&n.ref===e.ref)if(z0=!1,e.pendingProps=a=i,si(n,l))(n.flags&131072)!==0&&(z0=!0);else return e.lanes=n.lanes,$n(n,e,l)}return ai(n,e,t,a,l)}function Ys(n,e,t,a){var l=a.children,i=n!==null?n.memoizedState:null;if(n===null&&e.stateNode===null&&(e.stateNode={_visibility:1,_pendingMarkers:null,_retryCache:null,_transitions:null}),a.mode==="hidden"){if((e.flags&128)!==0){if(i=i!==null?i.baseLanes|t:t,n!==null){for(a=e.child=n.child,l=0;a!==null;)l=l|a.lanes|a.childLanes,a=a.sibling;a=l&~i}else a=0,e.child=null;return Gs(n,e,i,t,a)}if((t&536870912)!==0)e.memoizedState={baseLanes:0,cachePool:null},n!==null&&Or(e,i!==null?i.cachePool:null),i!==null?Qu(e,i):Ml(),Xu(e);else return a=e.lanes=536870912,Gs(n,e,i!==null?i.baseLanes|t:t,t,a)}else i!==null?(Or(e,i.cachePool),Qu(e,i),he(),e.memoizedState=null):(n!==null&&Or(e,null),Ml(),he());return w0(n,e,l,t),e.child}function ja(n,e){return n!==null&&n.tag===22||e.stateNode!==null||(e.stateNode={_visibility:1,_pendingMarkers:null,_retryCache:null,_transitions:null}),e.sibling}function Gs(n,e,t,a,l){var i=jl();return i=i===null?null:{parent:j0._currentValue,pool:i},e.memoizedState={baseLanes:t,cachePool:i},n!==null&&Or(e,null),Ml(),Xu(e),n!==null&&Tt(n,e,a,!0),e.childLanes=l,null}function Xr(n,e){return e=Vr({mode:e.mode,children:e.children},n.mode),e.ref=n.ref,n.child=e,e.return=n,e}function Ls(n,e,t){return Pe(e,n.child,null,t),n=Xr(e,e.pendingProps),n.flags|=2,cn(e),e.memoizedState=null,n}function k1(n,e,t){var a=e.pendingProps,l=(e.flags&128)!==0;if(e.flags&=-129,n===null){if(P){if(a.mode==="hidden")return n=Xr(e,a),e.lanes=536870912,ja(null,n);if(Rl(e),(n=m0)?(n=ec(n,xn),n=n!==null&&n.data==="&"?n:null,n!==null&&(e.memoizedState={dehydrated:n,treeContext:ue!==null?{id:Rn,overflow:Bn}:null,retryLane:536870912,hydrationErrors:null},t=Eu(n),t.return=e,e.child=t,B0=e,m0=null)):n=null,n===null)throw oe(e);return e.lanes=536870912,null}return Xr(e,a)}var i=n.memoizedState;if(i!==null){var o=i.dehydrated;if(Rl(e),l)if(e.flags&256)e.flags&=-257,e=Ls(n,e,t);else if(e.memoizedState!==null)e.child=n.child,e.flags|=128,e=null;else throw Error(u(558));else if(z0||Tt(n,e,t,!1),l=(t&n.childLanes)!==0,z0||l){if(a=v0,a!==null&&(o=Nf(a,t),o!==0&&o!==i.retryLane))throw i.retryLane=o,Ze(n,o),tn(a,n,o),ti;ed(),e=Ls(n,e,t)}else n=i.treeContext,m0=En(o.nextSibling),B0=e,P=!0,se=null,xn=!1,n!==null&&Ou(e,n),e=Xr(e,a),e.flags|=4096;return e}return n=Xn(n.child,{mode:a.mode,children:a.children}),n.ref=e.ref,e.child=n,n.return=e,n}function Zr(n,e){var t=e.ref;if(t===null)n!==null&&n.ref!==null&&(e.flags|=4194816);else{if(typeof t!="function"&&typeof t!="object")throw Error(u(284));(n===null||n.ref!==t)&&(e.flags|=4194816)}}function ai(n,e,t,a,l){return ke(e),t=Hl(n,e,t,a,void 0,l),a=wl(),n!==null&&!z0?(ql(n,e,l),$n(n,e,l)):(P&&a&&yl(e),e.flags|=1,w0(n,e,t,l),e.child)}function Qs(n,e,t,a,l,i){return ke(e),e.updateQueue=null,t=Vu(e,a,t,l),Zu(n),a=wl(),n!==null&&!z0?(ql(n,e,i),$n(n,e,i)):(P&&a&&yl(e),e.flags|=1,w0(n,e,t,i),e.child)}function Xs(n,e,t,a,l){if(ke(e),e.stateNode===null){var i=_t,o=t.contextType;typeof o=="object"&&o!==null&&(i=H0(o)),i=new t(a,i),e.memoizedState=i.state!==null&&i.state!==void 0?i.state:null,i.updater=ni,e.stateNode=i,i._reactInternals=e,i=e.stateNode,i.props=a,i.state=e.memoizedState,i.refs={},zl(e),o=t.contextType,i.context=typeof o=="object"&&o!==null?H0(o):_t,i.state=e.memoizedState,o=t.getDerivedStateFromProps,typeof o=="function"&&(Pl(e,t,o,a),i.state=e.memoizedState),typeof t.getDerivedStateFromProps=="function"||typeof i.getSnapshotBeforeUpdate=="function"||typeof i.UNSAFE_componentWillMount!="function"&&typeof i.componentWillMount!="function"||(o=i.state,typeof i.componentWillMount=="function"&&i.componentWillMount(),typeof i.UNSAFE_componentWillMount=="function"&&i.UNSAFE_componentWillMount(),o!==i.state&&ni.enqueueReplaceState(i,i.state,null),_a(e,a,i,l),Sa(),i.state=e.memoizedState),typeof i.componentDidMount=="function"&&(e.flags|=4194308),a=!0}else if(n===null){i=e.stateNode;var g=e.memoizedProps,m=et(t,g);i.props=m;var x=i.context,j=t.contextType;o=_t,typeof j=="object"&&j!==null&&(o=H0(j));var D=t.getDerivedStateFromProps;j=typeof D=="function"||typeof i.getSnapshotBeforeUpdate=="function",g=e.pendingProps!==g,j||typeof i.UNSAFE_componentWillReceiveProps!="function"&&typeof i.componentWillReceiveProps!="function"||(g||x!==o)&&Ds(e,i,a,o),ge=!1;var E=e.memoizedState;i.state=E,_a(e,a,i,l),Sa(),x=e.memoizedState,g||E!==x||ge?(typeof D=="function"&&(Pl(e,t,D,a),x=e.memoizedState),(m=ge||zs(e,t,m,a,E,x,o))?(j||typeof i.UNSAFE_componentWillMount!="function"&&typeof i.componentWillMount!="function"||(typeof i.componentWillMount=="function"&&i.componentWillMount(),typeof i.UNSAFE_componentWillMount=="function"&&i.UNSAFE_componentWillMount()),typeof i.componentDidMount=="function"&&(e.flags|=4194308)):(typeof i.componentDidMount=="function"&&(e.flags|=4194308),e.memoizedProps=a,e.memoizedState=x),i.props=a,i.state=x,i.context=o,a=m):(typeof i.componentDidMount=="function"&&(e.flags|=4194308),a=!1)}else{i=e.stateNode,Dl(n,e),o=e.memoizedProps,j=et(t,o),i.props=j,D=e.pendingProps,E=i.context,x=t.contextType,m=_t,typeof x=="object"&&x!==null&&(m=H0(x)),g=t.getDerivedStateFromProps,(x=typeof g=="function"||typeof i.getSnapshotBeforeUpdate=="function")||typeof i.UNSAFE_componentWillReceiveProps!="function"&&typeof i.componentWillReceiveProps!="function"||(o!==D||E!==m)&&Ds(e,i,a,m),ge=!1,E=e.memoizedState,i.state=E,_a(e,a,i,l),Sa();var T=e.memoizedState;o!==D||E!==T||ge||n!==null&&n.dependencies!==null&&Tr(n.dependencies)?(typeof g=="function"&&(Pl(e,t,g,a),T=e.memoizedState),(j=ge||zs(e,t,j,a,E,T,m)||n!==null&&n.dependencies!==null&&Tr(n.dependencies))?(x||typeof i.UNSAFE_componentWillUpdate!="function"&&typeof i.componentWillUpdate!="function"||(typeof i.componentWillUpdate=="function"&&i.componentWillUpdate(a,T,m),typeof i.UNSAFE_componentWillUpdate=="function"&&i.UNSAFE_componentWillUpdate(a,T,m)),typeof i.componentDidUpdate=="function"&&(e.flags|=4),typeof i.getSnapshotBeforeUpdate=="function"&&(e.flags|=1024)):(typeof i.componentDidUpdate!="function"||o===n.memoizedProps&&E===n.memoizedState||(e.flags|=4),typeof i.getSnapshotBeforeUpdate!="function"||o===n.memoizedProps&&E===n.memoizedState||(e.flags|=1024),e.memoizedProps=a,e.memoizedState=T),i.props=a,i.state=T,i.context=m,a=j):(typeof i.componentDidUpdate!="function"||o===n.memoizedProps&&E===n.memoizedState||(e.flags|=4),typeof i.getSnapshotBeforeUpdate!="function"||o===n.memoizedProps&&E===n.memoizedState||(e.flags|=1024),a=!1)}return i=a,Zr(n,e),a=(e.flags&128)!==0,i||a?(i=e.stateNode,t=a&&typeof t.getDerivedStateFromError!="function"?null:i.render(),e.flags|=1,n!==null&&a?(e.child=Pe(e,n.child,null,l),e.child=Pe(e,null,t,l)):w0(n,e,t,l),e.memoizedState=i.state,n=e.child):n=$n(n,e,l),n}function Zs(n,e,t,a){return Ke(),e.flags|=256,w0(n,e,t,a),e.child}var ri={dehydrated:null,treeContext:null,retryLane:0,hydrationErrors:null};function di(n){return{baseLanes:n,cachePool:Uu()}}function li(n,e,t){return n=n!==null?n.childLanes&~t:0,e&&(n|=In),n}function Vs(n,e,t){var a=e.pendingProps,l=!1,i=(e.flags&128)!==0,o;if((o=i)||(o=n!==null&&n.memoizedState===null?!1:(A0.current&2)!==0),o&&(l=!0,e.flags&=-129),o=(e.flags&32)!==0,e.flags&=-33,n===null){if(P){if(l?me(e):he(),(n=m0)?(n=ec(n,xn),n=n!==null&&n.data!=="&"?n:null,n!==null&&(e.memoizedState={dehydrated:n,treeContext:ue!==null?{id:Rn,overflow:Bn}:null,retryLane:536870912,hydrationErrors:null},t=Eu(n),t.return=e,e.child=t,B0=e,m0=null)):n=null,n===null)throw oe(e);return Li(n)?e.lanes=32:e.lanes=536870912,null}var g=a.children;return a=a.fallback,l?(he(),l=e.mode,g=Vr({mode:"hidden",children:g},l),a=Ve(a,l,t,null),g.return=e,a.return=e,g.sibling=a,e.child=g,a=e.child,a.memoizedState=di(t),a.childLanes=li(n,o,t),e.memoizedState=ri,ja(null,a)):(me(e),ii(e,g))}var m=n.memoizedState;if(m!==null&&(g=m.dehydrated,g!==null)){if(i)e.flags&256?(me(e),e.flags&=-257,e=fi(n,e,t)):e.memoizedState!==null?(he(),e.child=n.child,e.flags|=128,e=null):(he(),g=a.fallback,l=e.mode,a=Vr({mode:"visible",children:a.children},l),g=Ve(g,l,t,null),g.flags|=2,a.return=e,g.return=e,a.sibling=g,e.child=a,Pe(e,n.child,null,t),a=e.child,a.memoizedState=di(t),a.childLanes=li(n,o,t),e.memoizedState=ri,e=ja(null,a));else if(me(e),Li(g)){if(o=g.nextSibling&&g.nextSibling.dataset,o)var x=o.dgst;o=x,a=Error(u(419)),a.stack="",a.digest=o,va({value:a,source:null,stack:null}),e=fi(n,e,t)}else if(z0||Tt(n,e,t,!1),o=(t&n.childLanes)!==0,z0||o){if(o=v0,o!==null&&(a=Nf(o,t),a!==0&&a!==m.retryLane))throw m.retryLane=a,Ze(n,a),tn(o,n,a),ti;Gi(g)||ed(),e=fi(n,e,t)}else Gi(g)?(e.flags|=192,e.child=n.child,e=null):(n=m.treeContext,m0=En(g.nextSibling),B0=e,P=!0,se=null,xn=!1,n!==null&&Ou(e,n),e=ii(e,a.children),e.flags|=4096);return e}return l?(he(),g=a.fallback,l=e.mode,m=n.child,x=m.sibling,a=Xn(m,{mode:"hidden",children:a.children}),a.subtreeFlags=m.subtreeFlags&65011712,x!==null?g=Xn(x,g):(g=Ve(g,l,t,null),g.flags|=2),g.return=e,a.return=e,a.sibling=g,e.child=a,ja(null,a),a=e.child,g=n.child.memoizedState,g===null?g=di(t):(l=g.cachePool,l!==null?(m=j0._currentValue,l=l.parent!==m?{parent:m,pool:m}:l):l=Uu(),g={baseLanes:g.baseLanes|t,cachePool:l}),a.memoizedState=g,a.childLanes=li(n,o,t),e.memoizedState=ri,ja(n.child,a)):(me(e),t=n.child,n=t.sibling,t=Xn(t,{mode:"visible",children:a.children}),t.return=e,t.sibling=null,n!==null&&(o=e.deletions,o===null?(e.deletions=[n],e.flags|=16):o.push(n)),e.child=t,e.memoizedState=null,t)}function ii(n,e){return e=Vr({mode:"visible",children:e},n.mode),e.return=n,n.child=e}function Vr(n,e){return n=sn(22,n,null,e),n.lanes=0,n}function fi(n,e,t){return Pe(e,n.child,null,t),n=ii(e,e.pendingProps.children),n.flags|=2,e.memoizedState=null,n}function Ks(n,e,t){n.lanes|=e;var a=n.alternate;a!==null&&(a.lanes|=e),xl(n.return,e,t)}function ui(n,e,t,a,l,i){var o=n.memoizedState;o===null?n.memoizedState={isBackwards:e,rendering:null,renderingStartTime:0,last:a,tail:t,tailMode:l,treeForkCount:i}:(o.isBackwards=e,o.rendering=null,o.renderingStartTime=0,o.last=a,o.tail=t,o.tailMode=l,o.treeForkCount=i)}function Js(n,e,t){var a=e.pendingProps,l=a.revealOrder,i=a.tail;a=a.children;var o=A0.current,g=(o&2)!==0;if(g?(o=o&1|2,e.flags|=128):o&=1,R(A0,o),w0(n,e,a,t),a=P?Ia:0,!g&&n!==null&&(n.flags&128)!==0)n:for(n=e.child;n!==null;){if(n.tag===13)n.memoizedState!==null&&Ks(n,t,e);else if(n.tag===19)Ks(n,t,e);else if(n.child!==null){n.child.return=n,n=n.child;continue}if(n===e)break n;for(;n.sibling===null;){if(n.return===null||n.return===e)break n;n=n.return}n.sibling.return=n.return,n=n.sibling}switch(l){case"forwards":for(t=e.child,l=null;t!==null;)n=t.alternate,n!==null&&Ur(n)===null&&(l=t),t=t.sibling;t=l,t===null?(l=e.child,e.child=null):(l=t.sibling,t.sibling=null),ui(e,!1,l,t,i,a);break;case"backwards":case"unstable_legacy-backwards":for(t=null,l=e.child,e.child=null;l!==null;){if(n=l.alternate,n!==null&&Ur(n)===null){e.child=l;break}n=l.sibling,l.sibling=t,t=l,l=n}ui(e,!0,t,null,i,a);break;case"together":ui(e,!1,null,null,void 0,a);break;default:e.memoizedState=null}return e.child}function $n(n,e,t){if(n!==null&&(e.dependencies=n.dependencies),be|=e.lanes,(t&e.childLanes)===0)if(n!==null){if(Tt(n,e,t,!1),(t&e.childLanes)===0)return null}else return null;if(n!==null&&e.child!==n.child)throw Error(u(153));if(e.child!==null){for(n=e.child,t=Xn(n,n.pendingProps),e.child=t,t.return=e;n.sibling!==null;)n=n.sibling,t=t.sibling=Xn(n,n.pendingProps),t.return=e;t.sibling=null}return e.child}function si(n,e){return(n.lanes&e)!==0?!0:(n=n.dependencies,!!(n!==null&&Tr(n)))}function $1(n,e,t){switch(e.tag){case 3:X0(e,e.stateNode.containerInfo),ce(e,j0,n.memoizedState.cache),Ke();break;case 27:case 5:Pt(e);break;case 4:X0(e,e.stateNode.containerInfo);break;case 10:ce(e,e.type,e.memoizedProps.value);break;case 31:if(e.memoizedState!==null)return e.flags|=128,Rl(e),null;break;case 13:var a=e.memoizedState;if(a!==null)return a.dehydrated!==null?(me(e),e.flags|=128,null):(t&e.child.childLanes)!==0?Vs(n,e,t):(me(e),n=$n(n,e,t),n!==null?n.sibling:null);me(e);break;case 19:var l=(n.flags&128)!==0;if(a=(t&e.childLanes)!==0,a||(Tt(n,e,t,!1),a=(t&e.childLanes)!==0),l){if(a)return Js(n,e,t);e.flags|=128}if(l=e.memoizedState,l!==null&&(l.rendering=null,l.tail=null,l.lastEffect=null),R(A0,A0.current),a)break;return null;case 22:return e.lanes=0,Ys(n,e,t,e.pendingProps);case 24:ce(e,j0,n.memoizedState.cache)}return $n(n,e,t)}function ks(n,e,t){if(n!==null)if(n.memoizedProps!==e.pendingProps)z0=!0;else{if(!si(n,t)&&(e.flags&128)===0)return z0=!1,$1(n,e,t);z0=(n.flags&131072)!==0}else z0=!1,P&&(e.flags&1048576)!==0&&ju(e,Ia,e.index);switch(e.lanes=0,e.tag){case 16:n:{var a=e.pendingProps;if(n=We(e.elementType),e.type=n,typeof n=="function")vl(n)?(a=et(n,a),e.tag=1,e=Xs(null,e,n,a,t)):(e.tag=0,e=ai(null,e,n,a,t));else{if(n!=null){var l=n.$$typeof;if(l===mn){e.tag=11,e=Hs(null,e,n,a,t);break n}else if(l===F){e.tag=14,e=ws(null,e,n,a,t);break n}}throw e=Yn(n)||n,Error(u(306,e,""))}}return e;case 0:return ai(n,e,e.type,e.pendingProps,t);case 1:return a=e.type,l=et(a,e.pendingProps),Xs(n,e,a,l,t);case 3:n:{if(X0(e,e.stateNode.containerInfo),n===null)throw Error(u(387));a=e.pendingProps;var i=e.memoizedState;l=i.element,Dl(n,e),_a(e,a,null,t);var o=e.memoizedState;if(a=o.cache,ce(e,j0,a),a!==i.cache&&Al(e,[j0],t,!0),Sa(),a=o.element,i.isDehydrated)if(i={element:a,isDehydrated:!1,cache:o.cache},e.updateQueue.baseState=i,e.memoizedState=i,e.flags&256){e=Zs(n,e,a,t);break n}else if(a!==l){l=bn(Error(u(424)),e),va(l),e=Zs(n,e,a,t);break n}else{switch(n=e.stateNode.containerInfo,n.nodeType){case 9:n=n.body;break;default:n=n.nodeName==="HTML"?n.ownerDocument.body:n}for(m0=En(n.firstChild),B0=e,P=!0,se=null,xn=!0,t=Yu(e,null,a,t),e.child=t;t;)t.flags=t.flags&-3|4096,t=t.sibling}else{if(Ke(),a===l){e=$n(n,e,t);break n}w0(n,e,a,t)}e=e.child}return e;case 26:return Zr(n,e),n===null?(t=ic(e.type,null,e.pendingProps,null))?e.memoizedState=t:P||(t=e.type,n=e.pendingProps,a=fd(K.current).createElement(t),a[R0]=e,a[$0]=n,q0(a,t,n),M0(a),e.stateNode=a):e.memoizedState=ic(e.type,n.memoizedProps,e.pendingProps,n.memoizedState),null;case 27:return Pt(e),n===null&&P&&(a=e.stateNode=rc(e.type,e.pendingProps,K.current),B0=e,xn=!0,l=m0,Ee(e.type)?(Qi=l,m0=En(a.firstChild)):m0=l),w0(n,e,e.pendingProps.children,t),Zr(n,e),n===null&&(e.flags|=4194304),e.child;case 5:return n===null&&P&&((l=a=m0)&&(a=T8(a,e.type,e.pendingProps,xn),a!==null?(e.stateNode=a,B0=e,m0=En(a.firstChild),xn=!1,l=!0):l=!1),l||oe(e)),Pt(e),l=e.type,i=e.pendingProps,o=n!==null?n.memoizedProps:null,a=i.children,wi(l,i)?a=null:o!==null&&wi(l,o)&&(e.flags|=32),e.memoizedState!==null&&(l=Hl(n,e,G1,null,null,t),La._currentValue=l),Zr(n,e),w0(n,e,a,t),e.child;case 6:return n===null&&P&&((n=t=m0)&&(t=j8(t,e.pendingProps,xn),t!==null?(e.stateNode=t,B0=e,m0=null,n=!0):n=!1),n||oe(e)),null;case 13:return Vs(n,e,t);case 4:return X0(e,e.stateNode.containerInfo),a=e.pendingProps,n===null?e.child=Pe(e,null,a,t):w0(n,e,a,t),e.child;case 11:return Hs(n,e,e.type,e.pendingProps,t);case 7:return w0(n,e,e.pendingProps,t),e.child;case 8:return w0(n,e,e.pendingProps.children,t),e.child;case 12:return w0(n,e,e.pendingProps.children,t),e.child;case 10:return a=e.pendingProps,ce(e,e.type,a.value),w0(n,e,a.children,t),e.child;case 9:return l=e.type._context,a=e.pendingProps.children,ke(e),l=H0(l),a=a(l),e.flags|=1,w0(n,e,a,t),e.child;case 14:return ws(n,e,e.type,e.pendingProps,t);case 15:return qs(n,e,e.type,e.pendingProps,t);case 19:return Js(n,e,t);case 31:return k1(n,e,t);case 22:return Ys(n,e,t,e.pendingProps);case 24:return ke(e),a=H0(j0),n===null?(l=jl(),l===null&&(l=v0,i=El(),l.pooledCache=i,i.refCount++,i!==null&&(l.pooledCacheLanes|=t),l=i),e.memoizedState={parent:a,cache:l},zl(e),ce(e,j0,l)):((n.lanes&t)!==0&&(Dl(n,e),_a(e,null,null,t),Sa()),l=n.memoizedState,i=e.memoizedState,l.parent!==a?(l={parent:a,cache:a},e.memoizedState=l,e.lanes===0&&(e.memoizedState=e.updateQueue.baseState=l),ce(e,j0,a)):(a=i.cache,ce(e,j0,a),a!==l.cache&&Al(e,[j0],t,!0))),w0(n,e,e.pendingProps.children,t),e.child;case 29:throw e.pendingProps}throw Error(u(156,e.tag))}function Wn(n){n.flags|=4}function oi(n,e,t,a,l){if((e=(n.mode&32)!==0)&&(e=!1),e){if(n.flags|=16777216,(l&335544128)===l)if(n.stateNode.complete)n.flags|=8192;else if(xo())n.flags|=8192;else throw Fe=Dr,Ol}else n.flags&=-16777217}function $s(n,e){if(e.type!=="stylesheet"||(e.state.loading&4)!==0)n.flags&=-16777217;else if(n.flags|=16777216,!cc(e))if(xo())n.flags|=8192;else throw Fe=Dr,Ol}function Kr(n,e){e!==null&&(n.flags|=4),n.flags&16384&&(e=n.tag!==22?zf():536870912,n.lanes|=e,wt|=e)}function Oa(n,e){if(!P)switch(n.tailMode){case"hidden":e=n.tail;for(var t=null;e!==null;)e.alternate!==null&&(t=e),e=e.sibling;t===null?n.tail=null:t.sibling=null;break;case"collapsed":t=n.tail;for(var a=null;t!==null;)t.alternate!==null&&(a=t),t=t.sibling;a===null?e||n.tail===null?n.tail=null:n.tail.sibling=null:a.sibling=null}}function h0(n){var e=n.alternate!==null&&n.alternate.child===n.child,t=0,a=0;if(e)for(var l=n.child;l!==null;)t|=l.lanes|l.childLanes,a|=l.subtreeFlags&65011712,a|=l.flags&65011712,l.return=n,l=l.sibling;else for(l=n.child;l!==null;)t|=l.lanes|l.childLanes,a|=l.subtreeFlags,a|=l.flags,l.return=n,l=l.sibling;return n.subtreeFlags|=a,n.childLanes=t,e}function W1(n,e,t){var a=e.pendingProps;switch(pl(e),e.tag){case 16:case 15:case 0:case 11:case 7:case 8:case 12:case 9:case 14:return h0(e),null;case 1:return h0(e),null;case 3:return t=e.stateNode,a=null,n!==null&&(a=n.memoizedState.cache),e.memoizedState.cache!==a&&(e.flags|=2048),Kn(j0),x0(),t.pendingContext&&(t.context=t.pendingContext,t.pendingContext=null),(n===null||n.child===null)&&(Et(e)?Wn(e):n===null||n.memoizedState.isDehydrated&&(e.flags&256)===0||(e.flags|=1024,Sl())),h0(e),null;case 26:var l=e.type,i=e.memoizedState;return n===null?(Wn(e),i!==null?(h0(e),$s(e,i)):(h0(e),oi(e,l,null,a,t))):i?i!==n.memoizedState?(Wn(e),h0(e),$s(e,i)):(h0(e),e.flags&=-16777217):(n=n.memoizedProps,n!==a&&Wn(e),h0(e),oi(e,l,n,a,t)),null;case 27:if(rr(e),t=K.current,l=e.type,n!==null&&e.stateNode!=null)n.memoizedProps!==a&&Wn(e);else{if(!a){if(e.stateNode===null)throw Error(u(166));return h0(e),null}n=H.current,Et(e)?zu(e):(n=rc(l,a,t),e.stateNode=n,Wn(e))}return h0(e),null;case 5:if(rr(e),l=e.type,n!==null&&e.stateNode!=null)n.memoizedProps!==a&&Wn(e);else{if(!a){if(e.stateNode===null)throw Error(u(166));return h0(e),null}if(i=H.current,Et(e))zu(e);else{var o=fd(K.current);switch(i){case 1:i=o.createElementNS("http://www.w3.org/2000/svg",l);break;case 2:i=o.createElementNS("http://www.w3.org/1998/Math/MathML",l);break;default:switch(l){case"svg":i=o.createElementNS("http://www.w3.org/2000/svg",l);break;case"math":i=o.createElementNS("http://www.w3.org/1998/Math/MathML",l);break;case"script":i=o.createElement("div"),i.innerHTML="<script><\/script>",i=i.removeChild(i.firstChild);break;case"select":i=typeof a.is=="string"?o.createElement("select",{is:a.is}):o.createElement("select"),a.multiple?i.multiple=!0:a.size&&(i.size=a.size);break;default:i=typeof a.is=="string"?o.createElement(l,{is:a.is}):o.createElement(l)}}i[R0]=e,i[$0]=a;n:for(o=e.child;o!==null;){if(o.tag===5||o.tag===6)i.appendChild(o.stateNode);else if(o.tag!==4&&o.tag!==27&&o.child!==null){o.child.return=o,o=o.child;continue}if(o===e)break n;for(;o.sibling===null;){if(o.return===null||o.return===e)break n;o=o.return}o.sibling.return=o.return,o=o.sibling}e.stateNode=i;n:switch(q0(i,l,a),l){case"button":case"input":case"select":case"textarea":a=!!a.autoFocus;break n;case"img":a=!0;break n;default:a=!1}a&&Wn(e)}}return h0(e),oi(e,e.type,n===null?null:n.memoizedProps,e.pendingProps,t),null;case 6:if(n&&e.stateNode!=null)n.memoizedProps!==a&&Wn(e);else{if(typeof a!="string"&&e.stateNode===null)throw Error(u(166));if(n=K.current,Et(e)){if(n=e.stateNode,t=e.memoizedProps,a=null,l=B0,l!==null)switch(l.tag){case 27:case 5:a=l.memoizedProps}n[R0]=e,n=!!(n.nodeValue===t||a!==null&&a.suppressHydrationWarning===!0||Ko(n.nodeValue,t)),n||oe(e,!0)}else n=fd(n).createTextNode(a),n[R0]=e,e.stateNode=n}return h0(e),null;case 31:if(t=e.memoizedState,n===null||n.memoizedState!==null){if(a=Et(e),t!==null){if(n===null){if(!a)throw Error(u(318));if(n=e.memoizedState,n=n!==null?n.dehydrated:null,!n)throw Error(u(557));n[R0]=e}else Ke(),(e.flags&128)===0&&(e.memoizedState=null),e.flags|=4;h0(e),n=!1}else t=Sl(),n!==null&&n.memoizedState!==null&&(n.memoizedState.hydrationErrors=t),n=!0;if(!n)return e.flags&256?(cn(e),e):(cn(e),null);if((e.flags&128)!==0)throw Error(u(558))}return h0(e),null;case 13:if(a=e.memoizedState,n===null||n.memoizedState!==null&&n.memoizedState.dehydrated!==null){if(l=Et(e),a!==null&&a.dehydrated!==null){if(n===null){if(!l)throw Error(u(318));if(l=e.memoizedState,l=l!==null?l.dehydrated:null,!l)throw Error(u(317));l[R0]=e}else Ke(),(e.flags&128)===0&&(e.memoizedState=null),e.flags|=4;h0(e),l=!1}else l=Sl(),n!==null&&n.memoizedState!==null&&(n.memoizedState.hydrationErrors=l),l=!0;if(!l)return e.flags&256?(cn(e),e):(cn(e),null)}return cn(e),(e.flags&128)!==0?(e.lanes=t,e):(t=a!==null,n=n!==null&&n.memoizedState!==null,t&&(a=e.child,l=null,a.alternate!==null&&a.alternate.memoizedState!==null&&a.alternate.memoizedState.cachePool!==null&&(l=a.alternate.memoizedState.cachePool.pool),i=null,a.memoizedState!==null&&a.memoizedState.cachePool!==null&&(i=a.memoizedState.cachePool.pool),i!==l&&(a.flags|=2048)),t!==n&&t&&(e.child.flags|=8192),Kr(e,e.updateQueue),h0(e),null);case 4:return x0(),n===null&&Mi(e.stateNode.containerInfo),h0(e),null;case 10:return Kn(e.type),h0(e),null;case 19:if(C(A0),a=e.memoizedState,a===null)return h0(e),null;if(l=(e.flags&128)!==0,i=a.rendering,i===null)if(l)Oa(a,!1);else{if(S0!==0||n!==null&&(n.flags&128)!==0)for(n=e.child;n!==null;){if(i=Ur(n),i!==null){for(e.flags|=128,Oa(a,!1),n=i.updateQueue,e.updateQueue=n,Kr(e,n),e.subtreeFlags=0,n=t,t=e.child;t!==null;)Au(t,n),t=t.sibling;return R(A0,A0.current&1|2),P&&Zn(e,a.treeForkCount),e.child}n=n.sibling}a.tail!==null&&dn()>Fr&&(e.flags|=128,l=!0,Oa(a,!1),e.lanes=4194304)}else{if(!l)if(n=Ur(i),n!==null){if(e.flags|=128,l=!0,n=n.updateQueue,e.updateQueue=n,Kr(e,n),Oa(a,!0),a.tail===null&&a.tailMode==="hidden"&&!i.alternate&&!P)return h0(e),null}else 2*dn()-a.renderingStartTime>Fr&&t!==536870912&&(e.flags|=128,l=!0,Oa(a,!1),e.lanes=4194304);a.isBackwards?(i.sibling=e.child,e.child=i):(n=a.last,n!==null?n.sibling=i:e.child=i,a.last=i)}return a.tail!==null?(n=a.tail,a.rendering=n,a.tail=n.sibling,a.renderingStartTime=dn(),n.sibling=null,t=A0.current,R(A0,l?t&1|2:t&1),P&&Zn(e,a.treeForkCount),n):(h0(e),null);case 22:case 23:return cn(e),Ul(),a=e.memoizedState!==null,n!==null?n.memoizedState!==null!==a&&(e.flags|=8192):a&&(e.flags|=8192),a?(t&536870912)!==0&&(e.flags&128)===0&&(h0(e),e.subtreeFlags&6&&(e.flags|=8192)):h0(e),t=e.updateQueue,t!==null&&Kr(e,t.retryQueue),t=null,n!==null&&n.memoizedState!==null&&n.memoizedState.cachePool!==null&&(t=n.memoizedState.cachePool.pool),a=null,e.memoizedState!==null&&e.memoizedState.cachePool!==null&&(a=e.memoizedState.cachePool.pool),a!==t&&(e.flags|=2048),n!==null&&C($e),null;case 24:return t=null,n!==null&&(t=n.memoizedState.cache),e.memoizedState.cache!==t&&(e.flags|=2048),Kn(j0),h0(e),null;case 25:return null;case 30:return null}throw Error(u(156,e.tag))}function F1(n,e){switch(pl(e),e.tag){case 1:return n=e.flags,n&65536?(e.flags=n&-65537|128,e):null;case 3:return Kn(j0),x0(),n=e.flags,(n&65536)!==0&&(n&128)===0?(e.flags=n&-65537|128,e):null;case 26:case 27:case 5:return rr(e),null;case 31:if(e.memoizedState!==null){if(cn(e),e.alternate===null)throw Error(u(340));Ke()}return n=e.flags,n&65536?(e.flags=n&-65537|128,e):null;case 13:if(cn(e),n=e.memoizedState,n!==null&&n.dehydrated!==null){if(e.alternate===null)throw Error(u(340));Ke()}return n=e.flags,n&65536?(e.flags=n&-65537|128,e):null;case 19:return C(A0),null;case 4:return x0(),null;case 10:return Kn(e.type),null;case 22:case 23:return cn(e),Ul(),n!==null&&C($e),n=e.flags,n&65536?(e.flags=n&-65537|128,e):null;case 24:return Kn(j0),null;case 25:return null;default:return null}}function Ws(n,e){switch(pl(e),e.tag){case 3:Kn(j0),x0();break;case 26:case 27:case 5:rr(e);break;case 4:x0();break;case 31:e.memoizedState!==null&&cn(e);break;case 13:cn(e);break;case 19:C(A0);break;case 10:Kn(e.type);break;case 22:case 23:cn(e),Ul(),n!==null&&C($e);break;case 24:Kn(j0)}}function za(n,e){try{var t=e.updateQueue,a=t!==null?t.lastEffect:null;if(a!==null){var l=a.next;t=l;do{if((t.tag&n)===n){a=void 0;var i=t.create,o=t.inst;a=i(),o.destroy=a}t=t.next}while(t!==l)}}catch(g){f0(e,e.return,g)}}function ye(n,e,t){try{var a=e.updateQueue,l=a!==null?a.lastEffect:null;if(l!==null){var i=l.next;a=i;do{if((a.tag&n)===n){var o=a.inst,g=o.destroy;if(g!==void 0){o.destroy=void 0,l=e;var m=t,x=g;try{x()}catch(j){f0(l,m,j)}}}a=a.next}while(a!==i)}}catch(j){f0(e,e.return,j)}}function Fs(n){var e=n.updateQueue;if(e!==null){var t=n.stateNode;try{Lu(e,t)}catch(a){f0(n,n.return,a)}}}function Ps(n,e,t){t.props=et(n.type,n.memoizedProps),t.state=n.memoizedState;try{t.componentWillUnmount()}catch(a){f0(n,e,a)}}function Da(n,e){try{var t=n.ref;if(t!==null){switch(n.tag){case 26:case 27:case 5:var a=n.stateNode;break;case 30:a=n.stateNode;break;default:a=n.stateNode}typeof t=="function"?n.refCleanup=t(a):t.current=a}}catch(l){f0(n,e,l)}}function Hn(n,e){var t=n.ref,a=n.refCleanup;if(t!==null)if(typeof a=="function")try{a()}catch(l){f0(n,e,l)}finally{n.refCleanup=null,n=n.alternate,n!=null&&(n.refCleanup=null)}else if(typeof t=="function")try{t(null)}catch(l){f0(n,e,l)}else t.current=null}function no(n){var e=n.type,t=n.memoizedProps,a=n.stateNode;try{n:switch(e){case"button":case"input":case"select":case"textarea":t.autoFocus&&a.focus();break n;case"img":t.src?a.src=t.src:t.srcSet&&(a.srcset=t.srcSet)}}catch(l){f0(n,n.return,l)}}function ci(n,e,t){try{var a=n.stateNode;b8(a,n.type,t,e),a[$0]=e}catch(l){f0(n,n.return,l)}}function eo(n){return n.tag===5||n.tag===3||n.tag===26||n.tag===27&&Ee(n.type)||n.tag===4}function gi(n){n:for(;;){for(;n.sibling===null;){if(n.return===null||eo(n.return))return null;n=n.return}for(n.sibling.return=n.return,n=n.sibling;n.tag!==5&&n.tag!==6&&n.tag!==18;){if(n.tag===27&&Ee(n.type)||n.flags&2||n.child===null||n.tag===4)continue n;n.child.return=n,n=n.child}if(!(n.flags&2))return n.stateNode}}function Ii(n,e,t){var a=n.tag;if(a===5||a===6)n=n.stateNode,e?(t.nodeType===9?t.body:t.nodeName==="HTML"?t.ownerDocument.body:t).insertBefore(n,e):(e=t.nodeType===9?t.body:t.nodeName==="HTML"?t.ownerDocument.body:t,e.appendChild(n),t=t._reactRootContainer,t!=null||e.onclick!==null||(e.onclick=Ln));else if(a!==4&&(a===27&&Ee(n.type)&&(t=n.stateNode,e=null),n=n.child,n!==null))for(Ii(n,e,t),n=n.sibling;n!==null;)Ii(n,e,t),n=n.sibling}function Jr(n,e,t){var a=n.tag;if(a===5||a===6)n=n.stateNode,e?t.insertBefore(n,e):t.appendChild(n);else if(a!==4&&(a===27&&Ee(n.type)&&(t=n.stateNode),n=n.child,n!==null))for(Jr(n,e,t),n=n.sibling;n!==null;)Jr(n,e,t),n=n.sibling}function to(n){var e=n.stateNode,t=n.memoizedProps;try{for(var a=n.type,l=e.attributes;l.length;)e.removeAttributeNode(l[0]);q0(e,a,t),e[R0]=n,e[$0]=t}catch(i){f0(n,n.return,i)}}var Fn=!1,D0=!1,vi=!1,ao=typeof WeakSet=="function"?WeakSet:Set,U0=null;function P1(n,e){if(n=n.containerInfo,Bi=vd,n=vu(n),fl(n)){if("selectionStart"in n)var t={start:n.selectionStart,end:n.selectionEnd};else n:{t=(t=n.ownerDocument)&&t.defaultView||window;var a=t.getSelection&&t.getSelection();if(a&&a.rangeCount!==0){t=a.anchorNode;var l=a.anchorOffset,i=a.focusNode;a=a.focusOffset;try{t.nodeType,i.nodeType}catch{t=null;break n}var o=0,g=-1,m=-1,x=0,j=0,D=n,E=null;e:for(;;){for(var T;D!==t||l!==0&&D.nodeType!==3||(g=o+l),D!==i||a!==0&&D.nodeType!==3||(m=o+a),D.nodeType===3&&(o+=D.nodeValue.length),(T=D.firstChild)!==null;)E=D,D=T;for(;;){if(D===n)break e;if(E===t&&++x===l&&(g=o),E===i&&++j===a&&(m=o),(T=D.nextSibling)!==null)break;D=E,E=D.parentNode}D=T}t=g===-1||m===-1?null:{start:g,end:m}}else t=null}t=t||{start:0,end:0}}else t=null;for(Hi={focusedElem:n,selectionRange:t},vd=!1,U0=e;U0!==null;)if(e=U0,n=e.child,(e.subtreeFlags&1028)!==0&&n!==null)n.return=e,U0=n;else for(;U0!==null;){switch(e=U0,i=e.alternate,n=e.flags,e.tag){case 0:if((n&4)!==0&&(n=e.updateQueue,n=n!==null?n.events:null,n!==null))for(t=0;t<n.length;t++)l=n[t],l.ref.impl=l.nextImpl;break;case 11:case 15:break;case 1:if((n&1024)!==0&&i!==null){n=void 0,t=e,l=i.memoizedProps,i=i.memoizedState,a=t.stateNode;try{var B=et(t.type,l);n=a.getSnapshotBeforeUpdate(B,i),a.__reactInternalSnapshotBeforeUpdate=n}catch(G){f0(t,t.return,G)}}break;case 3:if((n&1024)!==0){if(n=e.stateNode.containerInfo,t=n.nodeType,t===9)Yi(n);else if(t===1)switch(n.nodeName){case"HEAD":case"HTML":case"BODY":Yi(n);break;default:n.textContent=""}}break;case 5:case 26:case 27:case 6:case 4:case 17:break;default:if((n&1024)!==0)throw Error(u(163))}if(n=e.sibling,n!==null){n.return=e.return,U0=n;break}U0=e.return}}function ro(n,e,t){var a=t.flags;switch(t.tag){case 0:case 11:case 15:ne(n,t),a&4&&za(5,t);break;case 1:if(ne(n,t),a&4)if(n=t.stateNode,e===null)try{n.componentDidMount()}catch(o){f0(t,t.return,o)}else{var l=et(t.type,e.memoizedProps);e=e.memoizedState;try{n.componentDidUpdate(l,e,n.__reactInternalSnapshotBeforeUpdate)}catch(o){f0(t,t.return,o)}}a&64&&Fs(t),a&512&&Da(t,t.return);break;case 3:if(ne(n,t),a&64&&(n=t.updateQueue,n!==null)){if(e=null,t.child!==null)switch(t.child.tag){case 27:case 5:e=t.child.stateNode;break;case 1:e=t.child.stateNode}try{Lu(n,e)}catch(o){f0(t,t.return,o)}}break;case 27:e===null&&a&4&&to(t);case 26:case 5:ne(n,t),e===null&&a&4&&no(t),a&512&&Da(t,t.return);break;case 12:ne(n,t);break;case 31:ne(n,t),a&4&&fo(n,t);break;case 13:ne(n,t),a&4&&uo(n,t),a&64&&(n=t.memoizedState,n!==null&&(n=n.dehydrated,n!==null&&(t=f8.bind(null,t),O8(n,t))));break;case 22:if(a=t.memoizedState!==null||Fn,!a){e=e!==null&&e.memoizedState!==null||D0,l=Fn;var i=D0;Fn=a,(D0=e)&&!i?ee(n,t,(t.subtreeFlags&8772)!==0):ne(n,t),Fn=l,D0=i}break;case 30:break;default:ne(n,t)}}function lo(n){var e=n.alternate;e!==null&&(n.alternate=null,lo(e)),n.child=null,n.deletions=null,n.sibling=null,n.tag===5&&(e=n.stateNode,e!==null&&Zd(e)),n.stateNode=null,n.return=null,n.dependencies=null,n.memoizedProps=null,n.memoizedState=null,n.pendingProps=null,n.stateNode=null,n.updateQueue=null}var p0=null,F0=!1;function Pn(n,e,t){for(t=t.child;t!==null;)io(n,e,t),t=t.sibling}function io(n,e,t){if(ln&&typeof ln.onCommitFiberUnmount=="function")try{ln.onCommitFiberUnmount(na,t)}catch{}switch(t.tag){case 26:D0||Hn(t,e),Pn(n,e,t),t.memoizedState?t.memoizedState.count--:t.stateNode&&(t=t.stateNode,t.parentNode.removeChild(t));break;case 27:D0||Hn(t,e);var a=p0,l=F0;Ee(t.type)&&(p0=t.stateNode,F0=!1),Pn(n,e,t),qa(t.stateNode),p0=a,F0=l;break;case 5:D0||Hn(t,e);case 6:if(a=p0,l=F0,p0=null,Pn(n,e,t),p0=a,F0=l,p0!==null)if(F0)try{(p0.nodeType===9?p0.body:p0.nodeName==="HTML"?p0.ownerDocument.body:p0).removeChild(t.stateNode)}catch(i){f0(t,e,i)}else try{p0.removeChild(t.stateNode)}catch(i){f0(t,e,i)}break;case 18:p0!==null&&(F0?(n=p0,Po(n.nodeType===9?n.body:n.nodeName==="HTML"?n.ownerDocument.body:n,t.stateNode),Vt(n)):Po(p0,t.stateNode));break;case 4:a=p0,l=F0,p0=t.stateNode.containerInfo,F0=!0,Pn(n,e,t),p0=a,F0=l;break;case 0:case 11:case 14:case 15:ye(2,t,e),D0||ye(4,t,e),Pn(n,e,t);break;case 1:D0||(Hn(t,e),a=t.stateNode,typeof a.componentWillUnmount=="function"&&Ps(t,e,a)),Pn(n,e,t);break;case 21:Pn(n,e,t);break;case 22:D0=(a=D0)||t.memoizedState!==null,Pn(n,e,t),D0=a;break;default:Pn(n,e,t)}}function fo(n,e){if(e.memoizedState===null&&(n=e.alternate,n!==null&&(n=n.memoizedState,n!==null))){n=n.dehydrated;try{Vt(n)}catch(t){f0(e,e.return,t)}}}function uo(n,e){if(e.memoizedState===null&&(n=e.alternate,n!==null&&(n=n.memoizedState,n!==null&&(n=n.dehydrated,n!==null))))try{Vt(n)}catch(t){f0(e,e.return,t)}}function n8(n){switch(n.tag){case 31:case 13:case 19:var e=n.stateNode;return e===null&&(e=n.stateNode=new ao),e;case 22:return n=n.stateNode,e=n._retryCache,e===null&&(e=n._retryCache=new ao),e;default:throw Error(u(435,n.tag))}}function kr(n,e){var t=n8(n);e.forEach(function(a){if(!t.has(a)){t.add(a);var l=u8.bind(null,n,a);a.then(l,l)}})}function P0(n,e){var t=e.deletions;if(t!==null)for(var a=0;a<t.length;a++){var l=t[a],i=n,o=e,g=o;n:for(;g!==null;){switch(g.tag){case 27:if(Ee(g.type)){p0=g.stateNode,F0=!1;break n}break;case 5:p0=g.stateNode,F0=!1;break n;case 3:case 4:p0=g.stateNode.containerInfo,F0=!0;break n}g=g.return}if(p0===null)throw Error(u(160));io(i,o,l),p0=null,F0=!1,i=l.alternate,i!==null&&(i.return=null),l.return=null}if(e.subtreeFlags&13886)for(e=e.child;e!==null;)so(e,n),e=e.sibling}var Dn=null;function so(n,e){var t=n.alternate,a=n.flags;switch(n.tag){case 0:case 11:case 14:case 15:P0(e,n),nn(n),a&4&&(ye(3,n,n.return),za(3,n),ye(5,n,n.return));break;case 1:P0(e,n),nn(n),a&512&&(D0||t===null||Hn(t,t.return)),a&64&&Fn&&(n=n.updateQueue,n!==null&&(a=n.callbacks,a!==null&&(t=n.shared.hiddenCallbacks,n.shared.hiddenCallbacks=t===null?a:t.concat(a))));break;case 26:var l=Dn;if(P0(e,n),nn(n),a&512&&(D0||t===null||Hn(t,t.return)),a&4){var i=t!==null?t.memoizedState:null;if(a=n.memoizedState,t===null)if(a===null)if(n.stateNode===null){n:{a=n.type,t=n.memoizedProps,l=l.ownerDocument||l;e:switch(a){case"title":i=l.getElementsByTagName("title")[0],(!i||i[aa]||i[R0]||i.namespaceURI==="http://www.w3.org/2000/svg"||i.hasAttribute("itemprop"))&&(i=l.createElement(a),l.head.insertBefore(i,l.querySelector("head > title"))),q0(i,a,t),i[R0]=n,M0(i),a=i;break n;case"link":var o=sc("link","href",l).get(a+(t.href||""));if(o){for(var g=0;g<o.length;g++)if(i=o[g],i.getAttribute("href")===(t.href==null||t.href===""?null:t.href)&&i.getAttribute("rel")===(t.rel==null?null:t.rel)&&i.getAttribute("title")===(t.title==null?null:t.title)&&i.getAttribute("crossorigin")===(t.crossOrigin==null?null:t.crossOrigin)){o.splice(g,1);break e}}i=l.createElement(a),q0(i,a,t),l.head.appendChild(i);break;case"meta":if(o=sc("meta","content",l).get(a+(t.content||""))){for(g=0;g<o.length;g++)if(i=o[g],i.getAttribute("content")===(t.content==null?null:""+t.content)&&i.getAttribute("name")===(t.name==null?null:t.name)&&i.getAttribute("property")===(t.property==null?null:t.property)&&i.getAttribute("http-equiv")===(t.httpEquiv==null?null:t.httpEquiv)&&i.getAttribute("charset")===(t.charSet==null?null:t.charSet)){o.splice(g,1);break e}}i=l.createElement(a),q0(i,a,t),l.head.appendChild(i);break;default:throw Error(u(468,a))}i[R0]=n,M0(i),a=i}n.stateNode=a}else oc(l,n.type,n.stateNode);else n.stateNode=uc(l,a,n.memoizedProps);else i!==a?(i===null?t.stateNode!==null&&(t=t.stateNode,t.parentNode.removeChild(t)):i.count--,a===null?oc(l,n.type,n.stateNode):uc(l,a,n.memoizedProps)):a===null&&n.stateNode!==null&&ci(n,n.memoizedProps,t.memoizedProps)}break;case 27:P0(e,n),nn(n),a&512&&(D0||t===null||Hn(t,t.return)),t!==null&&a&4&&ci(n,n.memoizedProps,t.memoizedProps);break;case 5:if(P0(e,n),nn(n),a&512&&(D0||t===null||Hn(t,t.return)),n.flags&32){l=n.stateNode;try{vt(l,"")}catch(B){f0(n,n.return,B)}}a&4&&n.stateNode!=null&&(l=n.memoizedProps,ci(n,l,t!==null?t.memoizedProps:l)),a&1024&&(vi=!0);break;case 6:if(P0(e,n),nn(n),a&4){if(n.stateNode===null)throw Error(u(162));a=n.memoizedProps,t=n.stateNode;try{t.nodeValue=a}catch(B){f0(n,n.return,B)}}break;case 3:if(od=null,l=Dn,Dn=ud(e.containerInfo),P0(e,n),Dn=l,nn(n),a&4&&t!==null&&t.memoizedState.isDehydrated)try{Vt(e.containerInfo)}catch(B){f0(n,n.return,B)}vi&&(vi=!1,oo(n));break;case 4:a=Dn,Dn=ud(n.stateNode.containerInfo),P0(e,n),nn(n),Dn=a;break;case 12:P0(e,n),nn(n);break;case 31:P0(e,n),nn(n),a&4&&(a=n.updateQueue,a!==null&&(n.updateQueue=null,kr(n,a)));break;case 13:P0(e,n),nn(n),n.child.flags&8192&&n.memoizedState!==null!=(t!==null&&t.memoizedState!==null)&&(Wr=dn()),a&4&&(a=n.updateQueue,a!==null&&(n.updateQueue=null,kr(n,a)));break;case 22:l=n.memoizedState!==null;var m=t!==null&&t.memoizedState!==null,x=Fn,j=D0;if(Fn=x||l,D0=j||m,P0(e,n),D0=j,Fn=x,nn(n),a&8192)n:for(e=n.stateNode,e._visibility=l?e._visibility&-2:e._visibility|1,l&&(t===null||m||Fn||D0||tt(n)),t=null,e=n;;){if(e.tag===5||e.tag===26){if(t===null){m=t=e;try{if(i=m.stateNode,l)o=i.style,typeof o.setProperty=="function"?o.setProperty("display","none","important"):o.display="none";else{g=m.stateNode;var D=m.memoizedProps.style,E=D!=null&&D.hasOwnProperty("display")?D.display:null;g.style.display=E==null||typeof E=="boolean"?"":(""+E).trim()}}catch(B){f0(m,m.return,B)}}}else if(e.tag===6){if(t===null){m=e;try{m.stateNode.nodeValue=l?"":m.memoizedProps}catch(B){f0(m,m.return,B)}}}else if(e.tag===18){if(t===null){m=e;try{var T=m.stateNode;l?nc(T,!0):nc(m.stateNode,!1)}catch(B){f0(m,m.return,B)}}}else if((e.tag!==22&&e.tag!==23||e.memoizedState===null||e===n)&&e.child!==null){e.child.return=e,e=e.child;continue}if(e===n)break n;for(;e.sibling===null;){if(e.return===null||e.return===n)break n;t===e&&(t=null),e=e.return}t===e&&(t=null),e.sibling.return=e.return,e=e.sibling}a&4&&(a=n.updateQueue,a!==null&&(t=a.retryQueue,t!==null&&(a.retryQueue=null,kr(n,t))));break;case 19:P0(e,n),nn(n),a&4&&(a=n.updateQueue,a!==null&&(n.updateQueue=null,kr(n,a)));break;case 30:break;case 21:break;default:P0(e,n),nn(n)}}function nn(n){var e=n.flags;if(e&2){try{for(var t,a=n.return;a!==null;){if(eo(a)){t=a;break}a=a.return}if(t==null)throw Error(u(160));switch(t.tag){case 27:var l=t.stateNode,i=gi(n);Jr(n,i,l);break;case 5:var o=t.stateNode;t.flags&32&&(vt(o,""),t.flags&=-33);var g=gi(n);Jr(n,g,o);break;case 3:case 4:var m=t.stateNode.containerInfo,x=gi(n);Ii(n,x,m);break;default:throw Error(u(161))}}catch(j){f0(n,n.return,j)}n.flags&=-3}e&4096&&(n.flags&=-4097)}function oo(n){if(n.subtreeFlags&1024)for(n=n.child;n!==null;){var e=n;oo(e),e.tag===5&&e.flags&1024&&e.stateNode.reset(),n=n.sibling}}function ne(n,e){if(e.subtreeFlags&8772)for(e=e.child;e!==null;)ro(n,e.alternate,e),e=e.sibling}function tt(n){for(n=n.child;n!==null;){var e=n;switch(e.tag){case 0:case 11:case 14:case 15:ye(4,e,e.return),tt(e);break;case 1:Hn(e,e.return);var t=e.stateNode;typeof t.componentWillUnmount=="function"&&Ps(e,e.return,t),tt(e);break;case 27:qa(e.stateNode);case 26:case 5:Hn(e,e.return),tt(e);break;case 22:e.memoizedState===null&&tt(e);break;case 30:tt(e);break;default:tt(e)}n=n.sibling}}function ee(n,e,t){for(t=t&&(e.subtreeFlags&8772)!==0,e=e.child;e!==null;){var a=e.alternate,l=n,i=e,o=i.flags;switch(i.tag){case 0:case 11:case 15:ee(l,i,t),za(4,i);break;case 1:if(ee(l,i,t),a=i,l=a.stateNode,typeof l.componentDidMount=="function")try{l.componentDidMount()}catch(x){f0(a,a.return,x)}if(a=i,l=a.updateQueue,l!==null){var g=a.stateNode;try{var m=l.shared.hiddenCallbacks;if(m!==null)for(l.shared.hiddenCallbacks=null,l=0;l<m.length;l++)Gu(m[l],g)}catch(x){f0(a,a.return,x)}}t&&o&64&&Fs(i),Da(i,i.return);break;case 27:to(i);case 26:case 5:ee(l,i,t),t&&a===null&&o&4&&no(i),Da(i,i.return);break;case 12:ee(l,i,t);break;case 31:ee(l,i,t),t&&o&4&&fo(l,i);break;case 13:ee(l,i,t),t&&o&4&&uo(l,i);break;case 22:i.memoizedState===null&&ee(l,i,t),Da(i,i.return);break;case 30:break;default:ee(l,i,t)}e=e.sibling}}function mi(n,e){var t=null;n!==null&&n.memoizedState!==null&&n.memoizedState.cachePool!==null&&(t=n.memoizedState.cachePool.pool),n=null,e.memoizedState!==null&&e.memoizedState.cachePool!==null&&(n=e.memoizedState.cachePool.pool),n!==t&&(n!=null&&n.refCount++,t!=null&&ma(t))}function hi(n,e){n=null,e.alternate!==null&&(n=e.alternate.memoizedState.cache),e=e.memoizedState.cache,e!==n&&(e.refCount++,n!=null&&ma(n))}function Cn(n,e,t,a){if(e.subtreeFlags&10256)for(e=e.child;e!==null;)co(n,e,t,a),e=e.sibling}function co(n,e,t,a){var l=e.flags;switch(e.tag){case 0:case 11:case 15:Cn(n,e,t,a),l&2048&&za(9,e);break;case 1:Cn(n,e,t,a);break;case 3:Cn(n,e,t,a),l&2048&&(n=null,e.alternate!==null&&(n=e.alternate.memoizedState.cache),e=e.memoizedState.cache,e!==n&&(e.refCount++,n!=null&&ma(n)));break;case 12:if(l&2048){Cn(n,e,t,a),n=e.stateNode;try{var i=e.memoizedProps,o=i.id,g=i.onPostCommit;typeof g=="function"&&g(o,e.alternate===null?"mount":"update",n.passiveEffectDuration,-0)}catch(m){f0(e,e.return,m)}}else Cn(n,e,t,a);break;case 31:Cn(n,e,t,a);break;case 13:Cn(n,e,t,a);break;case 23:break;case 22:i=e.stateNode,o=e.alternate,e.memoizedState!==null?i._visibility&2?Cn(n,e,t,a):Ca(n,e):i._visibility&2?Cn(n,e,t,a):(i._visibility|=2,Rt(n,e,t,a,(e.subtreeFlags&10256)!==0||!1)),l&2048&&mi(o,e);break;case 24:Cn(n,e,t,a),l&2048&&hi(e.alternate,e);break;default:Cn(n,e,t,a)}}function Rt(n,e,t,a,l){for(l=l&&((e.subtreeFlags&10256)!==0||!1),e=e.child;e!==null;){var i=n,o=e,g=t,m=a,x=o.flags;switch(o.tag){case 0:case 11:case 15:Rt(i,o,g,m,l),za(8,o);break;case 23:break;case 22:var j=o.stateNode;o.memoizedState!==null?j._visibility&2?Rt(i,o,g,m,l):Ca(i,o):(j._visibility|=2,Rt(i,o,g,m,l)),l&&x&2048&&mi(o.alternate,o);break;case 24:Rt(i,o,g,m,l),l&&x&2048&&hi(o.alternate,o);break;default:Rt(i,o,g,m,l)}e=e.sibling}}function Ca(n,e){if(e.subtreeFlags&10256)for(e=e.child;e!==null;){var t=n,a=e,l=a.flags;switch(a.tag){case 22:Ca(t,a),l&2048&&mi(a.alternate,a);break;case 24:Ca(t,a),l&2048&&hi(a.alternate,a);break;default:Ca(t,a)}e=e.sibling}}var Na=8192;function Bt(n,e,t){if(n.subtreeFlags&Na)for(n=n.child;n!==null;)go(n,e,t),n=n.sibling}function go(n,e,t){switch(n.tag){case 26:Bt(n,e,t),n.flags&Na&&n.memoizedState!==null&&Y8(t,Dn,n.memoizedState,n.memoizedProps);break;case 5:Bt(n,e,t);break;case 3:case 4:var a=Dn;Dn=ud(n.stateNode.containerInfo),Bt(n,e,t),Dn=a;break;case 22:n.memoizedState===null&&(a=n.alternate,a!==null&&a.memoizedState!==null?(a=Na,Na=16777216,Bt(n,e,t),Na=a):Bt(n,e,t));break;default:Bt(n,e,t)}}function Io(n){var e=n.alternate;if(e!==null&&(n=e.child,n!==null)){e.child=null;do e=n.sibling,n.sibling=null,n=e;while(n!==null)}}function Ma(n){var e=n.deletions;if((n.flags&16)!==0){if(e!==null)for(var t=0;t<e.length;t++){var a=e[t];U0=a,mo(a,n)}Io(n)}if(n.subtreeFlags&10256)for(n=n.child;n!==null;)vo(n),n=n.sibling}function vo(n){switch(n.tag){case 0:case 11:case 15:Ma(n),n.flags&2048&&ye(9,n,n.return);break;case 3:Ma(n);break;case 12:Ma(n);break;case 22:var e=n.stateNode;n.memoizedState!==null&&e._visibility&2&&(n.return===null||n.return.tag!==13)?(e._visibility&=-3,$r(n)):Ma(n);break;default:Ma(n)}}function $r(n){var e=n.deletions;if((n.flags&16)!==0){if(e!==null)for(var t=0;t<e.length;t++){var a=e[t];U0=a,mo(a,n)}Io(n)}for(n=n.child;n!==null;){switch(e=n,e.tag){case 0:case 11:case 15:ye(8,e,e.return),$r(e);break;case 22:t=e.stateNode,t._visibility&2&&(t._visibility&=-3,$r(e));break;default:$r(e)}n=n.sibling}}function mo(n,e){for(;U0!==null;){var t=U0;switch(t.tag){case 0:case 11:case 15:ye(8,t,e);break;case 23:case 22:if(t.memoizedState!==null&&t.memoizedState.cachePool!==null){var a=t.memoizedState.cachePool.pool;a!=null&&a.refCount++}break;case 24:ma(t.memoizedState.cache)}if(a=t.child,a!==null)a.return=t,U0=a;else n:for(t=n;U0!==null;){a=U0;var l=a.sibling,i=a.return;if(lo(a),a===t){U0=null;break n}if(l!==null){l.return=i,U0=l;break n}U0=i}}}var e8={getCacheForType:function(n){var e=H0(j0),t=e.data.get(n);return t===void 0&&(t=n(),e.data.set(n,t)),t},cacheSignal:function(){return H0(j0).controller.signal}},t8=typeof WeakMap=="function"?WeakMap:Map,r0=0,v0=null,J=null,$=0,i0=0,gn=null,pe=!1,Ht=!1,yi=!1,te=0,S0=0,be=0,at=0,pi=0,In=0,wt=0,Ua=null,en=null,bi=!1,Wr=0,ho=0,Fr=1/0,Pr=null,Se=null,N0=0,_e=null,qt=null,ae=0,Si=0,_i=null,yo=null,Ra=0,xi=null;function vn(){return(r0&2)!==0&&$!==0?$&-$:O.T!==null?zi():Mf()}function po(){if(In===0)if(($&536870912)===0||P){var n=ir;ir<<=1,(ir&3932160)===0&&(ir=262144),In=n}else In=536870912;return n=on.current,n!==null&&(n.flags|=32),In}function tn(n,e,t){(n===v0&&(i0===2||i0===9)||n.cancelPendingCommit!==null)&&(Yt(n,0),xe(n,$,In,!1)),ta(n,t),((r0&2)===0||n!==v0)&&(n===v0&&((r0&2)===0&&(at|=t),S0===4&&xe(n,$,In,!1)),wn(n))}function bo(n,e,t){if((r0&6)!==0)throw Error(u(327));var a=!t&&(e&127)===0&&(e&n.expiredLanes)===0||ea(n,e),l=a?d8(n,e):Ei(n,e,!0),i=a;do{if(l===0){Ht&&!a&&xe(n,e,0,!1);break}else{if(t=n.current.alternate,i&&!a8(t)){l=Ei(n,e,!1),i=!1;continue}if(l===2){if(i=e,n.errorRecoveryDisabledLanes&i)var o=0;else o=n.pendingLanes&-536870913,o=o!==0?o:o&536870912?536870912:0;if(o!==0){e=o;n:{var g=n;l=Ua;var m=g.current.memoizedState.isDehydrated;if(m&&(Yt(g,o).flags|=256),o=Ei(g,o,!1),o!==2){if(yi&&!m){g.errorRecoveryDisabledLanes|=i,at|=i,l=4;break n}i=en,en=l,i!==null&&(en===null?en=i:en.push.apply(en,i))}l=o}if(i=!1,l!==2)continue}}if(l===1){Yt(n,0),xe(n,e,0,!0);break}n:{switch(a=n,i=l,i){case 0:case 1:throw Error(u(345));case 4:if((e&4194048)!==e)break;case 6:xe(a,e,In,!pe);break n;case 2:en=null;break;case 3:case 5:break;default:throw Error(u(329))}if((e&62914560)===e&&(l=Wr+300-dn(),10<l)){if(xe(a,e,In,!pe),ur(a,0,!0)!==0)break n;ae=e,a.timeoutHandle=Wo(So.bind(null,a,t,en,Pr,bi,e,In,at,wt,pe,i,"Throttled",-0,0),l);break n}So(a,t,en,Pr,bi,e,In,at,wt,pe,i,null,-0,0)}}break}while(!0);wn(n)}function So(n,e,t,a,l,i,o,g,m,x,j,D,E,T){if(n.timeoutHandle=-1,D=e.subtreeFlags,D&8192||(D&16785408)===16785408){D={stylesheets:null,count:0,imgCount:0,imgBytes:0,suspenseyImages:[],waitingForImages:!0,waitingForViewTransition:!1,unsuspend:Ln},go(e,i,D);var B=(i&62914560)===i?Wr-dn():(i&4194048)===i?ho-dn():0;if(B=G8(D,B),B!==null){ae=i,n.cancelPendingCommit=B(zo.bind(null,n,e,i,t,a,l,o,g,m,j,D,null,E,T)),xe(n,i,o,!x);return}}zo(n,e,i,t,a,l,o,g,m)}function a8(n){for(var e=n;;){var t=e.tag;if((t===0||t===11||t===15)&&e.flags&16384&&(t=e.updateQueue,t!==null&&(t=t.stores,t!==null)))for(var a=0;a<t.length;a++){var l=t[a],i=l.getSnapshot;l=l.value;try{if(!un(i(),l))return!1}catch{return!1}}if(t=e.child,e.subtreeFlags&16384&&t!==null)t.return=e,e=t;else{if(e===n)break;for(;e.sibling===null;){if(e.return===null||e.return===n)return!0;e=e.return}e.sibling.return=e.return,e=e.sibling}}return!0}function xe(n,e,t,a){e&=~pi,e&=~at,n.suspendedLanes|=e,n.pingedLanes&=~e,a&&(n.warmLanes|=e),a=n.expirationTimes;for(var l=e;0<l;){var i=31-fn(l),o=1<<i;a[i]=-1,l&=~o}t!==0&&Df(n,t,e)}function nd(){return(r0&6)===0?(Ba(0),!1):!0}function Ai(){if(J!==null){if(i0===0)var n=J.return;else n=J,Vn=Je=null,Yl(n),Dt=null,ya=0,n=J;for(;n!==null;)Ws(n.alternate,n),n=n.return;J=null}}function Yt(n,e){var t=n.timeoutHandle;t!==-1&&(n.timeoutHandle=-1,x8(t)),t=n.cancelPendingCommit,t!==null&&(n.cancelPendingCommit=null,t()),ae=0,Ai(),v0=n,J=t=Xn(n.current,null),$=e,i0=0,gn=null,pe=!1,Ht=ea(n,e),yi=!1,wt=In=pi=at=be=S0=0,en=Ua=null,bi=!1,(e&8)!==0&&(e|=e&32);var a=n.entangledLanes;if(a!==0)for(n=n.entanglements,a&=e;0<a;){var l=31-fn(a),i=1<<l;e|=n[l],a&=~i}return te=e,Sr(),t}function _o(n,e){Z=null,O.H=Ta,e===zt||e===zr?(e=Hu(),i0=3):e===Ol?(e=Hu(),i0=4):i0=e===ti?8:e!==null&&typeof e=="object"&&typeof e.then=="function"?6:1,gn=e,J===null&&(S0=1,Qr(n,bn(e,n.current)))}function xo(){var n=on.current;return n===null?!0:($&4194048)===$?An===null:($&62914560)===$||($&536870912)!==0?n===An:!1}function Ao(){var n=O.H;return O.H=Ta,n===null?Ta:n}function Eo(){var n=O.A;return O.A=e8,n}function ed(){S0=4,pe||($&4194048)!==$&&on.current!==null||(Ht=!0),(be&134217727)===0&&(at&134217727)===0||v0===null||xe(v0,$,In,!1)}function Ei(n,e,t){var a=r0;r0|=2;var l=Ao(),i=Eo();(v0!==n||$!==e)&&(Pr=null,Yt(n,e)),e=!1;var o=S0;n:do try{if(i0!==0&&J!==null){var g=J,m=gn;switch(i0){case 8:Ai(),o=6;break n;case 3:case 2:case 9:case 6:on.current===null&&(e=!0);var x=i0;if(i0=0,gn=null,Gt(n,g,m,x),t&&Ht){o=0;break n}break;default:x=i0,i0=0,gn=null,Gt(n,g,m,x)}}r8(),o=S0;break}catch(j){_o(n,j)}while(!0);return e&&n.shellSuspendCounter++,Vn=Je=null,r0=a,O.H=l,O.A=i,J===null&&(v0=null,$=0,Sr()),o}function r8(){for(;J!==null;)To(J)}function d8(n,e){var t=r0;r0|=2;var a=Ao(),l=Eo();v0!==n||$!==e?(Pr=null,Fr=dn()+500,Yt(n,e)):Ht=ea(n,e);n:do try{if(i0!==0&&J!==null){e=J;var i=gn;e:switch(i0){case 1:i0=0,gn=null,Gt(n,e,i,1);break;case 2:case 9:if(Ru(i)){i0=0,gn=null,jo(e);break}e=function(){i0!==2&&i0!==9||v0!==n||(i0=7),wn(n)},i.then(e,e);break n;case 3:i0=7;break n;case 4:i0=5;break n;case 7:Ru(i)?(i0=0,gn=null,jo(e)):(i0=0,gn=null,Gt(n,e,i,7));break;case 5:var o=null;switch(J.tag){case 26:o=J.memoizedState;case 5:case 27:var g=J;if(o?cc(o):g.stateNode.complete){i0=0,gn=null;var m=g.sibling;if(m!==null)J=m;else{var x=g.return;x!==null?(J=x,td(x)):J=null}break e}}i0=0,gn=null,Gt(n,e,i,5);break;case 6:i0=0,gn=null,Gt(n,e,i,6);break;case 8:Ai(),S0=6;break n;default:throw Error(u(462))}}l8();break}catch(j){_o(n,j)}while(!0);return Vn=Je=null,O.H=a,O.A=l,r0=t,J!==null?0:(v0=null,$=0,Sr(),S0)}function l8(){for(;J!==null&&!z4();)To(J)}function To(n){var e=ks(n.alternate,n,te);n.memoizedProps=n.pendingProps,e===null?td(n):J=e}function jo(n){var e=n,t=e.alternate;switch(e.tag){case 15:case 0:e=Qs(t,e,e.pendingProps,e.type,void 0,$);break;case 11:e=Qs(t,e,e.pendingProps,e.type.render,e.ref,$);break;case 5:Yl(e);default:Ws(t,e),e=J=Au(e,te),e=ks(t,e,te)}n.memoizedProps=n.pendingProps,e===null?td(n):J=e}function Gt(n,e,t,a){Vn=Je=null,Yl(e),Dt=null,ya=0;var l=e.return;try{if(J1(n,l,e,t,$)){S0=1,Qr(n,bn(t,n.current)),J=null;return}}catch(i){if(l!==null)throw J=l,i;S0=1,Qr(n,bn(t,n.current)),J=null;return}e.flags&32768?(P||a===1?n=!0:Ht||($&536870912)!==0?n=!1:(pe=n=!0,(a===2||a===9||a===3||a===6)&&(a=on.current,a!==null&&a.tag===13&&(a.flags|=16384))),Oo(e,n)):td(e)}function td(n){var e=n;do{if((e.flags&32768)!==0){Oo(e,pe);return}n=e.return;var t=W1(e.alternate,e,te);if(t!==null){J=t;return}if(e=e.sibling,e!==null){J=e;return}J=e=n}while(e!==null);S0===0&&(S0=5)}function Oo(n,e){do{var t=F1(n.alternate,n);if(t!==null){t.flags&=32767,J=t;return}if(t=n.return,t!==null&&(t.flags|=32768,t.subtreeFlags=0,t.deletions=null),!e&&(n=n.sibling,n!==null)){J=n;return}J=n=t}while(n!==null);S0=6,J=null}function zo(n,e,t,a,l,i,o,g,m){n.cancelPendingCommit=null;do ad();while(N0!==0);if((r0&6)!==0)throw Error(u(327));if(e!==null){if(e===n.current)throw Error(u(177));if(i=e.lanes|e.childLanes,i|=gl,q4(n,t,i,o,g,m),n===v0&&(J=v0=null,$=0),qt=e,_e=n,ae=t,Si=i,_i=l,yo=a,(e.subtreeFlags&10256)!==0||(e.flags&10256)!==0?(n.callbackNode=null,n.callbackPriority=0,s8(dr,function(){return Uo(),null})):(n.callbackNode=null,n.callbackPriority=0),a=(e.flags&13878)!==0,(e.subtreeFlags&13878)!==0||a){a=O.T,O.T=null,l=M.p,M.p=2,o=r0,r0|=4;try{P1(n,e,t)}finally{r0=o,M.p=l,O.T=a}}N0=1,Do(),Co(),No()}}function Do(){if(N0===1){N0=0;var n=_e,e=qt,t=(e.flags&13878)!==0;if((e.subtreeFlags&13878)!==0||t){t=O.T,O.T=null;var a=M.p;M.p=2;var l=r0;r0|=4;try{so(e,n);var i=Hi,o=vu(n.containerInfo),g=i.focusedElem,m=i.selectionRange;if(o!==g&&g&&g.ownerDocument&&Iu(g.ownerDocument.documentElement,g)){if(m!==null&&fl(g)){var x=m.start,j=m.end;if(j===void 0&&(j=x),"selectionStart"in g)g.selectionStart=x,g.selectionEnd=Math.min(j,g.value.length);else{var D=g.ownerDocument||document,E=D&&D.defaultView||window;if(E.getSelection){var T=E.getSelection(),B=g.textContent.length,G=Math.min(m.start,B),g0=m.end===void 0?G:Math.min(m.end,B);!T.extend&&G>g0&&(o=g0,g0=G,G=o);var b=gu(g,G),h=gu(g,g0);if(b&&h&&(T.rangeCount!==1||T.anchorNode!==b.node||T.anchorOffset!==b.offset||T.focusNode!==h.node||T.focusOffset!==h.offset)){var _=D.createRange();_.setStart(b.node,b.offset),T.removeAllRanges(),G>g0?(T.addRange(_),T.extend(h.node,h.offset)):(_.setEnd(h.node,h.offset),T.addRange(_))}}}}for(D=[],T=g;T=T.parentNode;)T.nodeType===1&&D.push({element:T,left:T.scrollLeft,top:T.scrollTop});for(typeof g.focus=="function"&&g.focus(),g=0;g<D.length;g++){var z=D[g];z.element.scrollLeft=z.left,z.element.scrollTop=z.top}}vd=!!Bi,Hi=Bi=null}finally{r0=l,M.p=a,O.T=t}}n.current=e,N0=2}}function Co(){if(N0===2){N0=0;var n=_e,e=qt,t=(e.flags&8772)!==0;if((e.subtreeFlags&8772)!==0||t){t=O.T,O.T=null;var a=M.p;M.p=2;var l=r0;r0|=4;try{ro(n,e.alternate,e)}finally{r0=l,M.p=a,O.T=t}}N0=3}}function No(){if(N0===4||N0===3){N0=0,D4();var n=_e,e=qt,t=ae,a=yo;(e.subtreeFlags&10256)!==0||(e.flags&10256)!==0?N0=5:(N0=0,qt=_e=null,Mo(n,n.pendingLanes));var l=n.pendingLanes;if(l===0&&(Se=null),Qd(t),e=e.stateNode,ln&&typeof ln.onCommitFiberRoot=="function")try{ln.onCommitFiberRoot(na,e,void 0,(e.current.flags&128)===128)}catch{}if(a!==null){e=O.T,l=M.p,M.p=2,O.T=null;try{for(var i=n.onRecoverableError,o=0;o<a.length;o++){var g=a[o];i(g.value,{componentStack:g.stack})}}finally{O.T=e,M.p=l}}(ae&3)!==0&&ad(),wn(n),l=n.pendingLanes,(t&261930)!==0&&(l&42)!==0?n===xi?Ra++:(Ra=0,xi=n):Ra=0,Ba(0)}}function Mo(n,e){(n.pooledCacheLanes&=e)===0&&(e=n.pooledCache,e!=null&&(n.pooledCache=null,ma(e)))}function ad(){return Do(),Co(),No(),Uo()}function Uo(){if(N0!==5)return!1;var n=_e,e=Si;Si=0;var t=Qd(ae),a=O.T,l=M.p;try{M.p=32>t?32:t,O.T=null,t=_i,_i=null;var i=_e,o=ae;if(N0=0,qt=_e=null,ae=0,(r0&6)!==0)throw Error(u(331));var g=r0;if(r0|=4,vo(i.current),co(i,i.current,o,t),r0=g,Ba(0,!1),ln&&typeof ln.onPostCommitFiberRoot=="function")try{ln.onPostCommitFiberRoot(na,i)}catch{}return!0}finally{M.p=l,O.T=a,Mo(n,e)}}function Ro(n,e,t){e=bn(t,e),e=ei(n.stateNode,e,2),n=ve(n,e,2),n!==null&&(ta(n,2),wn(n))}function f0(n,e,t){if(n.tag===3)Ro(n,n,t);else for(;e!==null;){if(e.tag===3){Ro(e,n,t);break}else if(e.tag===1){var a=e.stateNode;if(typeof e.type.getDerivedStateFromError=="function"||typeof a.componentDidCatch=="function"&&(Se===null||!Se.has(a))){n=bn(t,n),t=Rs(2),a=ve(e,t,2),a!==null&&(Bs(t,a,e,n),ta(a,2),wn(a));break}}e=e.return}}function Ti(n,e,t){var a=n.pingCache;if(a===null){a=n.pingCache=new t8;var l=new Set;a.set(e,l)}else l=a.get(e),l===void 0&&(l=new Set,a.set(e,l));l.has(t)||(yi=!0,l.add(t),n=i8.bind(null,n,e,t),e.then(n,n))}function i8(n,e,t){var a=n.pingCache;a!==null&&a.delete(e),n.pingedLanes|=n.suspendedLanes&t,n.warmLanes&=~t,v0===n&&($&t)===t&&(S0===4||S0===3&&($&62914560)===$&&300>dn()-Wr?(r0&2)===0&&Yt(n,0):pi|=t,wt===$&&(wt=0)),wn(n)}function Bo(n,e){e===0&&(e=zf()),n=Ze(n,e),n!==null&&(ta(n,e),wn(n))}function f8(n){var e=n.memoizedState,t=0;e!==null&&(t=e.retryLane),Bo(n,t)}function u8(n,e){var t=0;switch(n.tag){case 31:case 13:var a=n.stateNode,l=n.memoizedState;l!==null&&(t=l.retryLane);break;case 19:a=n.stateNode;break;case 22:a=n.stateNode._retryCache;break;default:throw Error(u(314))}a!==null&&a.delete(e),Bo(n,t)}function s8(n,e){return qd(n,e)}var rd=null,Lt=null,ji=!1,dd=!1,Oi=!1,Ae=0;function wn(n){n!==Lt&&n.next===null&&(Lt===null?rd=Lt=n:Lt=Lt.next=n),dd=!0,ji||(ji=!0,c8())}function Ba(n,e){if(!Oi&&dd){Oi=!0;do for(var t=!1,a=rd;a!==null;){if(n!==0){var l=a.pendingLanes;if(l===0)var i=0;else{var o=a.suspendedLanes,g=a.pingedLanes;i=(1<<31-fn(42|n)+1)-1,i&=l&~(o&~g),i=i&201326741?i&201326741|1:i?i|2:0}i!==0&&(t=!0,Yo(a,i))}else i=$,i=ur(a,a===v0?i:0,a.cancelPendingCommit!==null||a.timeoutHandle!==-1),(i&3)===0||ea(a,i)||(t=!0,Yo(a,i));a=a.next}while(t);Oi=!1}}function o8(){Ho()}function Ho(){dd=ji=!1;var n=0;Ae!==0&&_8()&&(n=Ae);for(var e=dn(),t=null,a=rd;a!==null;){var l=a.next,i=wo(a,e);i===0?(a.next=null,t===null?rd=l:t.next=l,l===null&&(Lt=t)):(t=a,(n!==0||(i&3)!==0)&&(dd=!0)),a=l}N0!==0&&N0!==5||Ba(n),Ae!==0&&(Ae=0)}function wo(n,e){for(var t=n.suspendedLanes,a=n.pingedLanes,l=n.expirationTimes,i=n.pendingLanes&-62914561;0<i;){var o=31-fn(i),g=1<<o,m=l[o];m===-1?((g&t)===0||(g&a)!==0)&&(l[o]=w4(g,e)):m<=e&&(n.expiredLanes|=g),i&=~g}if(e=v0,t=$,t=ur(n,n===e?t:0,n.cancelPendingCommit!==null||n.timeoutHandle!==-1),a=n.callbackNode,t===0||n===e&&(i0===2||i0===9)||n.cancelPendingCommit!==null)return a!==null&&a!==null&&Yd(a),n.callbackNode=null,n.callbackPriority=0;if((t&3)===0||ea(n,t)){if(e=t&-t,e===n.callbackPriority)return e;switch(a!==null&&Yd(a),Qd(t)){case 2:case 8:t=jf;break;case 32:t=dr;break;case 268435456:t=Of;break;default:t=dr}return a=qo.bind(null,n),t=qd(t,a),n.callbackPriority=e,n.callbackNode=t,e}return a!==null&&a!==null&&Yd(a),n.callbackPriority=2,n.callbackNode=null,2}function qo(n,e){if(N0!==0&&N0!==5)return n.callbackNode=null,n.callbackPriority=0,null;var t=n.callbackNode;if(ad()&&n.callbackNode!==t)return null;var a=$;return a=ur(n,n===v0?a:0,n.cancelPendingCommit!==null||n.timeoutHandle!==-1),a===0?null:(bo(n,a,e),wo(n,dn()),n.callbackNode!=null&&n.callbackNode===t?qo.bind(null,n):null)}function Yo(n,e){if(ad())return null;bo(n,e,!0)}function c8(){A8(function(){(r0&6)!==0?qd(Tf,o8):Ho()})}function zi(){if(Ae===0){var n=jt;n===0&&(n=lr,lr<<=1,(lr&261888)===0&&(lr=256)),Ae=n}return Ae}function Go(n){return n==null||typeof n=="symbol"||typeof n=="boolean"?null:typeof n=="function"?n:gr(""+n)}function Lo(n,e){var t=e.ownerDocument.createElement("input");return t.name=e.name,t.value=e.value,n.id&&t.setAttribute("form",n.id),e.parentNode.insertBefore(t,e),n=new FormData(n),t.parentNode.removeChild(t),n}function g8(n,e,t,a,l){if(e==="submit"&&t&&t.stateNode===l){var i=Go((l[$0]||null).action),o=a.submitter;o&&(e=(e=o[$0]||null)?Go(e.formAction):o.getAttribute("formAction"),e!==null&&(i=e,o=null));var g=new hr("action","action",null,a,l);n.push({event:g,listeners:[{instance:null,listener:function(){if(a.defaultPrevented){if(Ae!==0){var m=o?Lo(l,o):new FormData(l);kl(t,{pending:!0,data:m,method:l.method,action:i},null,m)}}else typeof i=="function"&&(g.preventDefault(),m=o?Lo(l,o):new FormData(l),kl(t,{pending:!0,data:m,method:l.method,action:i},i,m))},currentTarget:l}]})}}for(var Di=0;Di<cl.length;Di++){var Ci=cl[Di],I8=Ci.toLowerCase(),v8=Ci[0].toUpperCase()+Ci.slice(1);zn(I8,"on"+v8)}zn(yu,"onAnimationEnd"),zn(pu,"onAnimationIteration"),zn(bu,"onAnimationStart"),zn("dblclick","onDoubleClick"),zn("focusin","onFocus"),zn("focusout","onBlur"),zn(C1,"onTransitionRun"),zn(N1,"onTransitionStart"),zn(M1,"onTransitionCancel"),zn(Su,"onTransitionEnd"),gt("onMouseEnter",["mouseout","mouseover"]),gt("onMouseLeave",["mouseout","mouseover"]),gt("onPointerEnter",["pointerout","pointerover"]),gt("onPointerLeave",["pointerout","pointerover"]),Ge("onChange","change click focusin focusout input keydown keyup selectionchange".split(" ")),Ge("onSelect","focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")),Ge("onBeforeInput",["compositionend","keypress","textInput","paste"]),Ge("onCompositionEnd","compositionend focusout keydown keypress keyup mousedown".split(" ")),Ge("onCompositionStart","compositionstart focusout keydown keypress keyup mousedown".split(" ")),Ge("onCompositionUpdate","compositionupdate focusout keydown keypress keyup mousedown".split(" "));var Ha="abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "),m8=new Set("beforetoggle cancel close invalid load scroll scrollend toggle".split(" ").concat(Ha));function Qo(n,e){e=(e&4)!==0;for(var t=0;t<n.length;t++){var a=n[t],l=a.event;a=a.listeners;n:{var i=void 0;if(e)for(var o=a.length-1;0<=o;o--){var g=a[o],m=g.instance,x=g.currentTarget;if(g=g.listener,m!==i&&l.isPropagationStopped())break n;i=g,l.currentTarget=x;try{i(l)}catch(j){br(j)}l.currentTarget=null,i=m}else for(o=0;o<a.length;o++){if(g=a[o],m=g.instance,x=g.currentTarget,g=g.listener,m!==i&&l.isPropagationStopped())break n;i=g,l.currentTarget=x;try{i(l)}catch(j){br(j)}l.currentTarget=null,i=m}}}}function k(n,e){var t=e[Xd];t===void 0&&(t=e[Xd]=new Set);var a=n+"__bubble";t.has(a)||(Xo(e,n,2,!1),t.add(a))}function Ni(n,e,t){var a=0;e&&(a|=4),Xo(t,n,a,e)}var ld="_reactListening"+Math.random().toString(36).slice(2);function Mi(n){if(!n[ld]){n[ld]=!0,Bf.forEach(function(t){t!=="selectionchange"&&(m8.has(t)||Ni(t,!1,n),Ni(t,!0,n))});var e=n.nodeType===9?n:n.ownerDocument;e===null||e[ld]||(e[ld]=!0,Ni("selectionchange",!1,e))}}function Xo(n,e,t,a){switch(pc(e)){case 2:var l=X8;break;case 8:l=Z8;break;default:l=Ji}t=l.bind(null,e,t,n),l=void 0,!Pd||e!=="touchstart"&&e!=="touchmove"&&e!=="wheel"||(l=!0),a?l!==void 0?n.addEventListener(e,t,{capture:!0,passive:l}):n.addEventListener(e,t,!0):l!==void 0?n.addEventListener(e,t,{passive:l}):n.addEventListener(e,t,!1)}function Ui(n,e,t,a,l){var i=a;if((e&1)===0&&(e&2)===0&&a!==null)n:for(;;){if(a===null)return;var o=a.tag;if(o===3||o===4){var g=a.stateNode.containerInfo;if(g===l)break;if(o===4)for(o=a.return;o!==null;){var m=o.tag;if((m===3||m===4)&&o.stateNode.containerInfo===l)return;o=o.return}for(;g!==null;){if(o=st(g),o===null)return;if(m=o.tag,m===5||m===6||m===26||m===27){a=i=o;continue n}g=g.parentNode}}a=a.return}Jf(function(){var x=i,j=Wd(t),D=[];n:{var E=_u.get(n);if(E!==void 0){var T=hr,B=n;switch(n){case"keypress":if(vr(t)===0)break n;case"keydown":case"keyup":T=u1;break;case"focusin":B="focus",T=al;break;case"focusout":B="blur",T=al;break;case"beforeblur":case"afterblur":T=al;break;case"click":if(t.button===2)break n;case"auxclick":case"dblclick":case"mousedown":case"mousemove":case"mouseup":case"mouseout":case"mouseover":case"contextmenu":T=Wf;break;case"drag":case"dragend":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"dragstart":case"drop":T=W4;break;case"touchcancel":case"touchend":case"touchmove":case"touchstart":T=c1;break;case yu:case pu:case bu:T=n1;break;case Su:T=I1;break;case"scroll":case"scrollend":T=k4;break;case"wheel":T=m1;break;case"copy":case"cut":case"paste":T=t1;break;case"gotpointercapture":case"lostpointercapture":case"pointercancel":case"pointerdown":case"pointermove":case"pointerout":case"pointerover":case"pointerup":T=Pf;break;case"toggle":case"beforetoggle":T=y1}var G=(e&4)!==0,g0=!G&&(n==="scroll"||n==="scrollend"),b=G?E!==null?E+"Capture":null:E;G=[];for(var h=x,_;h!==null;){var z=h;if(_=z.stateNode,z=z.tag,z!==5&&z!==26&&z!==27||_===null||b===null||(z=da(h,b),z!=null&&G.push(wa(h,z,_))),g0)break;h=h.return}0<G.length&&(E=new T(E,B,null,t,j),D.push({event:E,listeners:G}))}}if((e&7)===0){n:{if(E=n==="mouseover"||n==="pointerover",T=n==="mouseout"||n==="pointerout",E&&t!==$d&&(B=t.relatedTarget||t.fromElement)&&(st(B)||B[ut]))break n;if((T||E)&&(E=j.window===j?j:(E=j.ownerDocument)?E.defaultView||E.parentWindow:window,T?(B=t.relatedTarget||t.toElement,T=x,B=B?st(B):null,B!==null&&(g0=c(B),G=B.tag,B!==g0||G!==5&&G!==27&&G!==6)&&(B=null)):(T=null,B=x),T!==B)){if(G=Wf,z="onMouseLeave",b="onMouseEnter",h="mouse",(n==="pointerout"||n==="pointerover")&&(G=Pf,z="onPointerLeave",b="onPointerEnter",h="pointer"),g0=T==null?E:ra(T),_=B==null?E:ra(B),E=new G(z,h+"leave",T,t,j),E.target=g0,E.relatedTarget=_,z=null,st(j)===x&&(G=new G(b,h+"enter",B,t,j),G.target=_,G.relatedTarget=g0,z=G),g0=z,T&&B)e:{for(G=h8,b=T,h=B,_=0,z=b;z;z=G(z))_++;z=0;for(var q=h;q;q=G(q))z++;for(;0<_-z;)b=G(b),_--;for(;0<z-_;)h=G(h),z--;for(;_--;){if(b===h||h!==null&&b===h.alternate){G=b;break e}b=G(b),h=G(h)}G=null}else G=null;T!==null&&Zo(D,E,T,G,!1),B!==null&&g0!==null&&Zo(D,g0,B,G,!0)}}n:{if(E=x?ra(x):window,T=E.nodeName&&E.nodeName.toLowerCase(),T==="select"||T==="input"&&E.type==="file")var t0=iu;else if(du(E))if(fu)t0=O1;else{t0=T1;var w=E1}else T=E.nodeName,!T||T.toLowerCase()!=="input"||E.type!=="checkbox"&&E.type!=="radio"?x&&kd(x.elementType)&&(t0=iu):t0=j1;if(t0&&(t0=t0(n,x))){lu(D,t0,t,j);break n}w&&w(n,E,x),n==="focusout"&&x&&E.type==="number"&&x.memoizedProps.value!=null&&Jd(E,"number",E.value)}switch(w=x?ra(x):window,n){case"focusin":(du(w)||w.contentEditable==="true")&&(pt=w,ul=x,ga=null);break;case"focusout":ga=ul=pt=null;break;case"mousedown":sl=!0;break;case"contextmenu":case"mouseup":case"dragend":sl=!1,mu(D,t,j);break;case"selectionchange":if(D1)break;case"keydown":case"keyup":mu(D,t,j)}var V;if(dl)n:{switch(n){case"compositionstart":var W="onCompositionStart";break n;case"compositionend":W="onCompositionEnd";break n;case"compositionupdate":W="onCompositionUpdate";break n}W=void 0}else yt?au(n,t)&&(W="onCompositionEnd"):n==="keydown"&&t.keyCode===229&&(W="onCompositionStart");W&&(nu&&t.locale!=="ko"&&(yt||W!=="onCompositionStart"?W==="onCompositionEnd"&&yt&&(V=kf()):(fe=j,nl="value"in fe?fe.value:fe.textContent,yt=!0)),w=id(x,W),0<w.length&&(W=new Ff(W,n,null,t,j),D.push({event:W,listeners:w}),V?W.data=V:(V=ru(t),V!==null&&(W.data=V)))),(V=b1?S1(n,t):_1(n,t))&&(W=id(x,"onBeforeInput"),0<W.length&&(w=new Ff("onBeforeInput","beforeinput",null,t,j),D.push({event:w,listeners:W}),w.data=V)),g8(D,n,x,t,j)}Qo(D,e)})}function wa(n,e,t){return{instance:n,listener:e,currentTarget:t}}function id(n,e){for(var t=e+"Capture",a=[];n!==null;){var l=n,i=l.stateNode;if(l=l.tag,l!==5&&l!==26&&l!==27||i===null||(l=da(n,t),l!=null&&a.unshift(wa(n,l,i)),l=da(n,e),l!=null&&a.push(wa(n,l,i))),n.tag===3)return a;n=n.return}return[]}function h8(n){if(n===null)return null;do n=n.return;while(n&&n.tag!==5&&n.tag!==27);return n||null}function Zo(n,e,t,a,l){for(var i=e._reactName,o=[];t!==null&&t!==a;){var g=t,m=g.alternate,x=g.stateNode;if(g=g.tag,m!==null&&m===a)break;g!==5&&g!==26&&g!==27||x===null||(m=x,l?(x=da(t,i),x!=null&&o.unshift(wa(t,x,m))):l||(x=da(t,i),x!=null&&o.push(wa(t,x,m)))),t=t.return}o.length!==0&&n.push({event:e,listeners:o})}var y8=/\r\n?/g,p8=/\u0000|\uFFFD/g;function Vo(n){return(typeof n=="string"?n:""+n).replace(y8,`
`).replace(p8,"")}function Ko(n,e){return e=Vo(e),Vo(n)===e}function c0(n,e,t,a,l,i){switch(t){case"children":typeof a=="string"?e==="body"||e==="textarea"&&a===""||vt(n,a):(typeof a=="number"||typeof a=="bigint")&&e!=="body"&&vt(n,""+a);break;case"className":or(n,"class",a);break;case"tabIndex":or(n,"tabindex",a);break;case"dir":case"role":case"viewBox":case"width":case"height":or(n,t,a);break;case"style":Vf(n,a,i);break;case"data":if(e!=="object"){or(n,"data",a);break}case"src":case"href":if(a===""&&(e!=="a"||t!=="href")){n.removeAttribute(t);break}if(a==null||typeof a=="function"||typeof a=="symbol"||typeof a=="boolean"){n.removeAttribute(t);break}a=gr(""+a),n.setAttribute(t,a);break;case"action":case"formAction":if(typeof a=="function"){n.setAttribute(t,"javascript:throw new Error('A React form was unexpectedly submitted. If you called form.submit() manually, consider using form.requestSubmit() instead. If you\\'re trying to use event.stopPropagation() in a submit event handler, consider also calling event.preventDefault().')");break}else typeof i=="function"&&(t==="formAction"?(e!=="input"&&c0(n,e,"name",l.name,l,null),c0(n,e,"formEncType",l.formEncType,l,null),c0(n,e,"formMethod",l.formMethod,l,null),c0(n,e,"formTarget",l.formTarget,l,null)):(c0(n,e,"encType",l.encType,l,null),c0(n,e,"method",l.method,l,null),c0(n,e,"target",l.target,l,null)));if(a==null||typeof a=="symbol"||typeof a=="boolean"){n.removeAttribute(t);break}a=gr(""+a),n.setAttribute(t,a);break;case"onClick":a!=null&&(n.onclick=Ln);break;case"onScroll":a!=null&&k("scroll",n);break;case"onScrollEnd":a!=null&&k("scrollend",n);break;case"dangerouslySetInnerHTML":if(a!=null){if(typeof a!="object"||!("__html"in a))throw Error(u(61));if(t=a.__html,t!=null){if(l.children!=null)throw Error(u(60));n.innerHTML=t}}break;case"multiple":n.multiple=a&&typeof a!="function"&&typeof a!="symbol";break;case"muted":n.muted=a&&typeof a!="function"&&typeof a!="symbol";break;case"suppressContentEditableWarning":case"suppressHydrationWarning":case"defaultValue":case"defaultChecked":case"innerHTML":case"ref":break;case"autoFocus":break;case"xlinkHref":if(a==null||typeof a=="function"||typeof a=="boolean"||typeof a=="symbol"){n.removeAttribute("xlink:href");break}t=gr(""+a),n.setAttributeNS("http://www.w3.org/1999/xlink","xlink:href",t);break;case"contentEditable":case"spellCheck":case"draggable":case"value":case"autoReverse":case"externalResourcesRequired":case"focusable":case"preserveAlpha":a!=null&&typeof a!="function"&&typeof a!="symbol"?n.setAttribute(t,""+a):n.removeAttribute(t);break;case"inert":case"allowFullScreen":case"async":case"autoPlay":case"controls":case"default":case"defer":case"disabled":case"disablePictureInPicture":case"disableRemotePlayback":case"formNoValidate":case"hidden":case"loop":case"noModule":case"noValidate":case"open":case"playsInline":case"readOnly":case"required":case"reversed":case"scoped":case"seamless":case"itemScope":a&&typeof a!="function"&&typeof a!="symbol"?n.setAttribute(t,""):n.removeAttribute(t);break;case"capture":case"download":a===!0?n.setAttribute(t,""):a!==!1&&a!=null&&typeof a!="function"&&typeof a!="symbol"?n.setAttribute(t,a):n.removeAttribute(t);break;case"cols":case"rows":case"size":case"span":a!=null&&typeof a!="function"&&typeof a!="symbol"&&!isNaN(a)&&1<=a?n.setAttribute(t,a):n.removeAttribute(t);break;case"rowSpan":case"start":a==null||typeof a=="function"||typeof a=="symbol"||isNaN(a)?n.removeAttribute(t):n.setAttribute(t,a);break;case"popover":k("beforetoggle",n),k("toggle",n),sr(n,"popover",a);break;case"xlinkActuate":Gn(n,"http://www.w3.org/1999/xlink","xlink:actuate",a);break;case"xlinkArcrole":Gn(n,"http://www.w3.org/1999/xlink","xlink:arcrole",a);break;case"xlinkRole":Gn(n,"http://www.w3.org/1999/xlink","xlink:role",a);break;case"xlinkShow":Gn(n,"http://www.w3.org/1999/xlink","xlink:show",a);break;case"xlinkTitle":Gn(n,"http://www.w3.org/1999/xlink","xlink:title",a);break;case"xlinkType":Gn(n,"http://www.w3.org/1999/xlink","xlink:type",a);break;case"xmlBase":Gn(n,"http://www.w3.org/XML/1998/namespace","xml:base",a);break;case"xmlLang":Gn(n,"http://www.w3.org/XML/1998/namespace","xml:lang",a);break;case"xmlSpace":Gn(n,"http://www.w3.org/XML/1998/namespace","xml:space",a);break;case"is":sr(n,"is",a);break;case"innerText":case"textContent":break;default:(!(2<t.length)||t[0]!=="o"&&t[0]!=="O"||t[1]!=="n"&&t[1]!=="N")&&(t=K4.get(t)||t,sr(n,t,a))}}function Ri(n,e,t,a,l,i){switch(t){case"style":Vf(n,a,i);break;case"dangerouslySetInnerHTML":if(a!=null){if(typeof a!="object"||!("__html"in a))throw Error(u(61));if(t=a.__html,t!=null){if(l.children!=null)throw Error(u(60));n.innerHTML=t}}break;case"children":typeof a=="string"?vt(n,a):(typeof a=="number"||typeof a=="bigint")&&vt(n,""+a);break;case"onScroll":a!=null&&k("scroll",n);break;case"onScrollEnd":a!=null&&k("scrollend",n);break;case"onClick":a!=null&&(n.onclick=Ln);break;case"suppressContentEditableWarning":case"suppressHydrationWarning":case"innerHTML":case"ref":break;case"innerText":case"textContent":break;default:if(!Hf.hasOwnProperty(t))n:{if(t[0]==="o"&&t[1]==="n"&&(l=t.endsWith("Capture"),e=t.slice(2,l?t.length-7:void 0),i=n[$0]||null,i=i!=null?i[t]:null,typeof i=="function"&&n.removeEventListener(e,i,l),typeof a=="function")){typeof i!="function"&&i!==null&&(t in n?n[t]=null:n.hasAttribute(t)&&n.removeAttribute(t)),n.addEventListener(e,a,l);break n}t in n?n[t]=a:a===!0?n.setAttribute(t,""):sr(n,t,a)}}}function q0(n,e,t){switch(e){case"div":case"span":case"svg":case"path":case"a":case"g":case"p":case"li":break;case"img":k("error",n),k("load",n);var a=!1,l=!1,i;for(i in t)if(t.hasOwnProperty(i)){var o=t[i];if(o!=null)switch(i){case"src":a=!0;break;case"srcSet":l=!0;break;case"children":case"dangerouslySetInnerHTML":throw Error(u(137,e));default:c0(n,e,i,o,t,null)}}l&&c0(n,e,"srcSet",t.srcSet,t,null),a&&c0(n,e,"src",t.src,t,null);return;case"input":k("invalid",n);var g=i=o=l=null,m=null,x=null;for(a in t)if(t.hasOwnProperty(a)){var j=t[a];if(j!=null)switch(a){case"name":l=j;break;case"type":o=j;break;case"checked":m=j;break;case"defaultChecked":x=j;break;case"value":i=j;break;case"defaultValue":g=j;break;case"children":case"dangerouslySetInnerHTML":if(j!=null)throw Error(u(137,e));break;default:c0(n,e,a,j,t,null)}}Lf(n,i,g,m,x,o,l,!1);return;case"select":k("invalid",n),a=o=i=null;for(l in t)if(t.hasOwnProperty(l)&&(g=t[l],g!=null))switch(l){case"value":i=g;break;case"defaultValue":o=g;break;case"multiple":a=g;default:c0(n,e,l,g,t,null)}e=i,t=o,n.multiple=!!a,e!=null?It(n,!!a,e,!1):t!=null&&It(n,!!a,t,!0);return;case"textarea":k("invalid",n),i=l=a=null;for(o in t)if(t.hasOwnProperty(o)&&(g=t[o],g!=null))switch(o){case"value":a=g;break;case"defaultValue":l=g;break;case"children":i=g;break;case"dangerouslySetInnerHTML":if(g!=null)throw Error(u(91));break;default:c0(n,e,o,g,t,null)}Xf(n,a,l,i);return;case"option":for(m in t)if(t.hasOwnProperty(m)&&(a=t[m],a!=null))switch(m){case"selected":n.selected=a&&typeof a!="function"&&typeof a!="symbol";break;default:c0(n,e,m,a,t,null)}return;case"dialog":k("beforetoggle",n),k("toggle",n),k("cancel",n),k("close",n);break;case"iframe":case"object":k("load",n);break;case"video":case"audio":for(a=0;a<Ha.length;a++)k(Ha[a],n);break;case"image":k("error",n),k("load",n);break;case"details":k("toggle",n);break;case"embed":case"source":case"link":k("error",n),k("load",n);case"area":case"base":case"br":case"col":case"hr":case"keygen":case"meta":case"param":case"track":case"wbr":case"menuitem":for(x in t)if(t.hasOwnProperty(x)&&(a=t[x],a!=null))switch(x){case"children":case"dangerouslySetInnerHTML":throw Error(u(137,e));default:c0(n,e,x,a,t,null)}return;default:if(kd(e)){for(j in t)t.hasOwnProperty(j)&&(a=t[j],a!==void 0&&Ri(n,e,j,a,t,void 0));return}}for(g in t)t.hasOwnProperty(g)&&(a=t[g],a!=null&&c0(n,e,g,a,t,null))}function b8(n,e,t,a){switch(e){case"div":case"span":case"svg":case"path":case"a":case"g":case"p":case"li":break;case"input":var l=null,i=null,o=null,g=null,m=null,x=null,j=null;for(T in t){var D=t[T];if(t.hasOwnProperty(T)&&D!=null)switch(T){case"checked":break;case"value":break;case"defaultValue":m=D;default:a.hasOwnProperty(T)||c0(n,e,T,null,a,D)}}for(var E in a){var T=a[E];if(D=t[E],a.hasOwnProperty(E)&&(T!=null||D!=null))switch(E){case"type":i=T;break;case"name":l=T;break;case"checked":x=T;break;case"defaultChecked":j=T;break;case"value":o=T;break;case"defaultValue":g=T;break;case"children":case"dangerouslySetInnerHTML":if(T!=null)throw Error(u(137,e));break;default:T!==D&&c0(n,e,E,T,a,D)}}Kd(n,o,g,m,x,j,i,l);return;case"select":T=o=g=E=null;for(i in t)if(m=t[i],t.hasOwnProperty(i)&&m!=null)switch(i){case"value":break;case"multiple":T=m;default:a.hasOwnProperty(i)||c0(n,e,i,null,a,m)}for(l in a)if(i=a[l],m=t[l],a.hasOwnProperty(l)&&(i!=null||m!=null))switch(l){case"value":E=i;break;case"defaultValue":g=i;break;case"multiple":o=i;default:i!==m&&c0(n,e,l,i,a,m)}e=g,t=o,a=T,E!=null?It(n,!!t,E,!1):!!a!=!!t&&(e!=null?It(n,!!t,e,!0):It(n,!!t,t?[]:"",!1));return;case"textarea":T=E=null;for(g in t)if(l=t[g],t.hasOwnProperty(g)&&l!=null&&!a.hasOwnProperty(g))switch(g){case"value":break;case"children":break;default:c0(n,e,g,null,a,l)}for(o in a)if(l=a[o],i=t[o],a.hasOwnProperty(o)&&(l!=null||i!=null))switch(o){case"value":E=l;break;case"defaultValue":T=l;break;case"children":break;case"dangerouslySetInnerHTML":if(l!=null)throw Error(u(91));break;default:l!==i&&c0(n,e,o,l,a,i)}Qf(n,E,T);return;case"option":for(var B in t)if(E=t[B],t.hasOwnProperty(B)&&E!=null&&!a.hasOwnProperty(B))switch(B){case"selected":n.selected=!1;break;default:c0(n,e,B,null,a,E)}for(m in a)if(E=a[m],T=t[m],a.hasOwnProperty(m)&&E!==T&&(E!=null||T!=null))switch(m){case"selected":n.selected=E&&typeof E!="function"&&typeof E!="symbol";break;default:c0(n,e,m,E,a,T)}return;case"img":case"link":case"area":case"base":case"br":case"col":case"embed":case"hr":case"keygen":case"meta":case"param":case"source":case"track":case"wbr":case"menuitem":for(var G in t)E=t[G],t.hasOwnProperty(G)&&E!=null&&!a.hasOwnProperty(G)&&c0(n,e,G,null,a,E);for(x in a)if(E=a[x],T=t[x],a.hasOwnProperty(x)&&E!==T&&(E!=null||T!=null))switch(x){case"children":case"dangerouslySetInnerHTML":if(E!=null)throw Error(u(137,e));break;default:c0(n,e,x,E,a,T)}return;default:if(kd(e)){for(var g0 in t)E=t[g0],t.hasOwnProperty(g0)&&E!==void 0&&!a.hasOwnProperty(g0)&&Ri(n,e,g0,void 0,a,E);for(j in a)E=a[j],T=t[j],!a.hasOwnProperty(j)||E===T||E===void 0&&T===void 0||Ri(n,e,j,E,a,T);return}}for(var b in t)E=t[b],t.hasOwnProperty(b)&&E!=null&&!a.hasOwnProperty(b)&&c0(n,e,b,null,a,E);for(D in a)E=a[D],T=t[D],!a.hasOwnProperty(D)||E===T||E==null&&T==null||c0(n,e,D,E,a,T)}function Jo(n){switch(n){case"css":case"script":case"font":case"img":case"image":case"input":case"link":return!0;default:return!1}}function S8(){if(typeof performance.getEntriesByType=="function"){for(var n=0,e=0,t=performance.getEntriesByType("resource"),a=0;a<t.length;a++){var l=t[a],i=l.transferSize,o=l.initiatorType,g=l.duration;if(i&&g&&Jo(o)){for(o=0,g=l.responseEnd,a+=1;a<t.length;a++){var m=t[a],x=m.startTime;if(x>g)break;var j=m.transferSize,D=m.initiatorType;j&&Jo(D)&&(m=m.responseEnd,o+=j*(m<g?1:(g-x)/(m-x)))}if(--a,e+=8*(i+o)/(l.duration/1e3),n++,10<n)break}}if(0<n)return e/n/1e6}return navigator.connection&&(n=navigator.connection.downlink,typeof n=="number")?n:5}var Bi=null,Hi=null;function fd(n){return n.nodeType===9?n:n.ownerDocument}function ko(n){switch(n){case"http://www.w3.org/2000/svg":return 1;case"http://www.w3.org/1998/Math/MathML":return 2;default:return 0}}function $o(n,e){if(n===0)switch(e){case"svg":return 1;case"math":return 2;default:return 0}return n===1&&e==="foreignObject"?0:n}function wi(n,e){return n==="textarea"||n==="noscript"||typeof e.children=="string"||typeof e.children=="number"||typeof e.children=="bigint"||typeof e.dangerouslySetInnerHTML=="object"&&e.dangerouslySetInnerHTML!==null&&e.dangerouslySetInnerHTML.__html!=null}var qi=null;function _8(){var n=window.event;return n&&n.type==="popstate"?n===qi?!1:(qi=n,!0):(qi=null,!1)}var Wo=typeof setTimeout=="function"?setTimeout:void 0,x8=typeof clearTimeout=="function"?clearTimeout:void 0,Fo=typeof Promise=="function"?Promise:void 0,A8=typeof queueMicrotask=="function"?queueMicrotask:typeof Fo<"u"?function(n){return Fo.resolve(null).then(n).catch(E8)}:Wo;function E8(n){setTimeout(function(){throw n})}function Ee(n){return n==="head"}function Po(n,e){var t=e,a=0;do{var l=t.nextSibling;if(n.removeChild(t),l&&l.nodeType===8)if(t=l.data,t==="/$"||t==="/&"){if(a===0){n.removeChild(l),Vt(e);return}a--}else if(t==="$"||t==="$?"||t==="$~"||t==="$!"||t==="&")a++;else if(t==="html")qa(n.ownerDocument.documentElement);else if(t==="head"){t=n.ownerDocument.head,qa(t);for(var i=t.firstChild;i;){var o=i.nextSibling,g=i.nodeName;i[aa]||g==="SCRIPT"||g==="STYLE"||g==="LINK"&&i.rel.toLowerCase()==="stylesheet"||t.removeChild(i),i=o}}else t==="body"&&qa(n.ownerDocument.body);t=l}while(t);Vt(e)}function nc(n,e){var t=n;n=0;do{var a=t.nextSibling;if(t.nodeType===1?e?(t._stashedDisplay=t.style.display,t.style.display="none"):(t.style.display=t._stashedDisplay||"",t.getAttribute("style")===""&&t.removeAttribute("style")):t.nodeType===3&&(e?(t._stashedText=t.nodeValue,t.nodeValue=""):t.nodeValue=t._stashedText||""),a&&a.nodeType===8)if(t=a.data,t==="/$"){if(n===0)break;n--}else t!=="$"&&t!=="$?"&&t!=="$~"&&t!=="$!"||n++;t=a}while(t)}function Yi(n){var e=n.firstChild;for(e&&e.nodeType===10&&(e=e.nextSibling);e;){var t=e;switch(e=e.nextSibling,t.nodeName){case"HTML":case"HEAD":case"BODY":Yi(t),Zd(t);continue;case"SCRIPT":case"STYLE":continue;case"LINK":if(t.rel.toLowerCase()==="stylesheet")continue}n.removeChild(t)}}function T8(n,e,t,a){for(;n.nodeType===1;){var l=t;if(n.nodeName.toLowerCase()!==e.toLowerCase()){if(!a&&(n.nodeName!=="INPUT"||n.type!=="hidden"))break}else if(a){if(!n[aa])switch(e){case"meta":if(!n.hasAttribute("itemprop"))break;return n;case"link":if(i=n.getAttribute("rel"),i==="stylesheet"&&n.hasAttribute("data-precedence"))break;if(i!==l.rel||n.getAttribute("href")!==(l.href==null||l.href===""?null:l.href)||n.getAttribute("crossorigin")!==(l.crossOrigin==null?null:l.crossOrigin)||n.getAttribute("title")!==(l.title==null?null:l.title))break;return n;case"style":if(n.hasAttribute("data-precedence"))break;return n;case"script":if(i=n.getAttribute("src"),(i!==(l.src==null?null:l.src)||n.getAttribute("type")!==(l.type==null?null:l.type)||n.getAttribute("crossorigin")!==(l.crossOrigin==null?null:l.crossOrigin))&&i&&n.hasAttribute("async")&&!n.hasAttribute("itemprop"))break;return n;default:return n}}else if(e==="input"&&n.type==="hidden"){var i=l.name==null?null:""+l.name;if(l.type==="hidden"&&n.getAttribute("name")===i)return n}else return n;if(n=En(n.nextSibling),n===null)break}return null}function j8(n,e,t){if(e==="")return null;for(;n.nodeType!==3;)if((n.nodeType!==1||n.nodeName!=="INPUT"||n.type!=="hidden")&&!t||(n=En(n.nextSibling),n===null))return null;return n}function ec(n,e){for(;n.nodeType!==8;)if((n.nodeType!==1||n.nodeName!=="INPUT"||n.type!=="hidden")&&!e||(n=En(n.nextSibling),n===null))return null;return n}function Gi(n){return n.data==="$?"||n.data==="$~"}function Li(n){return n.data==="$!"||n.data==="$?"&&n.ownerDocument.readyState!=="loading"}function O8(n,e){var t=n.ownerDocument;if(n.data==="$~")n._reactRetry=e;else if(n.data!=="$?"||t.readyState!=="loading")e();else{var a=function(){e(),t.removeEventListener("DOMContentLoaded",a)};t.addEventListener("DOMContentLoaded",a),n._reactRetry=a}}function En(n){for(;n!=null;n=n.nextSibling){var e=n.nodeType;if(e===1||e===3)break;if(e===8){if(e=n.data,e==="$"||e==="$!"||e==="$?"||e==="$~"||e==="&"||e==="F!"||e==="F")break;if(e==="/$"||e==="/&")return null}}return n}var Qi=null;function tc(n){n=n.nextSibling;for(var e=0;n;){if(n.nodeType===8){var t=n.data;if(t==="/$"||t==="/&"){if(e===0)return En(n.nextSibling);e--}else t!=="$"&&t!=="$!"&&t!=="$?"&&t!=="$~"&&t!=="&"||e++}n=n.nextSibling}return null}function ac(n){n=n.previousSibling;for(var e=0;n;){if(n.nodeType===8){var t=n.data;if(t==="$"||t==="$!"||t==="$?"||t==="$~"||t==="&"){if(e===0)return n;e--}else t!=="/$"&&t!=="/&"||e++}n=n.previousSibling}return null}function rc(n,e,t){switch(e=fd(t),n){case"html":if(n=e.documentElement,!n)throw Error(u(452));return n;case"head":if(n=e.head,!n)throw Error(u(453));return n;case"body":if(n=e.body,!n)throw Error(u(454));return n;default:throw Error(u(451))}}function qa(n){for(var e=n.attributes;e.length;)n.removeAttributeNode(e[0]);Zd(n)}var Tn=new Map,dc=new Set;function ud(n){return typeof n.getRootNode=="function"?n.getRootNode():n.nodeType===9?n:n.ownerDocument}var re=M.d;M.d={f:z8,r:D8,D:C8,C:N8,L:M8,m:U8,X:B8,S:R8,M:H8};function z8(){var n=re.f(),e=nd();return n||e}function D8(n){var e=ot(n);e!==null&&e.tag===5&&e.type==="form"?Ss(e):re.r(n)}var Qt=typeof document>"u"?null:document;function lc(n,e,t){var a=Qt;if(a&&typeof e=="string"&&e){var l=yn(e);l='link[rel="'+n+'"][href="'+l+'"]',typeof t=="string"&&(l+='[crossorigin="'+t+'"]'),dc.has(l)||(dc.add(l),n={rel:n,crossOrigin:t,href:e},a.querySelector(l)===null&&(e=a.createElement("link"),q0(e,"link",n),M0(e),a.head.appendChild(e)))}}function C8(n){re.D(n),lc("dns-prefetch",n,null)}function N8(n,e){re.C(n,e),lc("preconnect",n,e)}function M8(n,e,t){re.L(n,e,t);var a=Qt;if(a&&n&&e){var l='link[rel="preload"][as="'+yn(e)+'"]';e==="image"&&t&&t.imageSrcSet?(l+='[imagesrcset="'+yn(t.imageSrcSet)+'"]',typeof t.imageSizes=="string"&&(l+='[imagesizes="'+yn(t.imageSizes)+'"]')):l+='[href="'+yn(n)+'"]';var i=l;switch(e){case"style":i=Xt(n);break;case"script":i=Zt(n)}Tn.has(i)||(n=U({rel:"preload",href:e==="image"&&t&&t.imageSrcSet?void 0:n,as:e},t),Tn.set(i,n),a.querySelector(l)!==null||e==="style"&&a.querySelector(Ya(i))||e==="script"&&a.querySelector(Ga(i))||(e=a.createElement("link"),q0(e,"link",n),M0(e),a.head.appendChild(e)))}}function U8(n,e){re.m(n,e);var t=Qt;if(t&&n){var a=e&&typeof e.as=="string"?e.as:"script",l='link[rel="modulepreload"][as="'+yn(a)+'"][href="'+yn(n)+'"]',i=l;switch(a){case"audioworklet":case"paintworklet":case"serviceworker":case"sharedworker":case"worker":case"script":i=Zt(n)}if(!Tn.has(i)&&(n=U({rel:"modulepreload",href:n},e),Tn.set(i,n),t.querySelector(l)===null)){switch(a){case"audioworklet":case"paintworklet":case"serviceworker":case"sharedworker":case"worker":case"script":if(t.querySelector(Ga(i)))return}a=t.createElement("link"),q0(a,"link",n),M0(a),t.head.appendChild(a)}}}function R8(n,e,t){re.S(n,e,t);var a=Qt;if(a&&n){var l=ct(a).hoistableStyles,i=Xt(n);e=e||"default";var o=l.get(i);if(!o){var g={loading:0,preload:null};if(o=a.querySelector(Ya(i)))g.loading=5;else{n=U({rel:"stylesheet",href:n,"data-precedence":e},t),(t=Tn.get(i))&&Xi(n,t);var m=o=a.createElement("link");M0(m),q0(m,"link",n),m._p=new Promise(function(x,j){m.onload=x,m.onerror=j}),m.addEventListener("load",function(){g.loading|=1}),m.addEventListener("error",function(){g.loading|=2}),g.loading|=4,sd(o,e,a)}o={type:"stylesheet",instance:o,count:1,state:g},l.set(i,o)}}}function B8(n,e){re.X(n,e);var t=Qt;if(t&&n){var a=ct(t).hoistableScripts,l=Zt(n),i=a.get(l);i||(i=t.querySelector(Ga(l)),i||(n=U({src:n,async:!0},e),(e=Tn.get(l))&&Zi(n,e),i=t.createElement("script"),M0(i),q0(i,"link",n),t.head.appendChild(i)),i={type:"script",instance:i,count:1,state:null},a.set(l,i))}}function H8(n,e){re.M(n,e);var t=Qt;if(t&&n){var a=ct(t).hoistableScripts,l=Zt(n),i=a.get(l);i||(i=t.querySelector(Ga(l)),i||(n=U({src:n,async:!0,type:"module"},e),(e=Tn.get(l))&&Zi(n,e),i=t.createElement("script"),M0(i),q0(i,"link",n),t.head.appendChild(i)),i={type:"script",instance:i,count:1,state:null},a.set(l,i))}}function ic(n,e,t,a){var l=(l=K.current)?ud(l):null;if(!l)throw Error(u(446));switch(n){case"meta":case"title":return null;case"style":return typeof t.precedence=="string"&&typeof t.href=="string"?(e=Xt(t.href),t=ct(l).hoistableStyles,a=t.get(e),a||(a={type:"style",instance:null,count:0,state:null},t.set(e,a)),a):{type:"void",instance:null,count:0,state:null};case"link":if(t.rel==="stylesheet"&&typeof t.href=="string"&&typeof t.precedence=="string"){n=Xt(t.href);var i=ct(l).hoistableStyles,o=i.get(n);if(o||(l=l.ownerDocument||l,o={type:"stylesheet",instance:null,count:0,state:{loading:0,preload:null}},i.set(n,o),(i=l.querySelector(Ya(n)))&&!i._p&&(o.instance=i,o.state.loading=5),Tn.has(n)||(t={rel:"preload",as:"style",href:t.href,crossOrigin:t.crossOrigin,integrity:t.integrity,media:t.media,hrefLang:t.hrefLang,referrerPolicy:t.referrerPolicy},Tn.set(n,t),i||w8(l,n,t,o.state))),e&&a===null)throw Error(u(528,""));return o}if(e&&a!==null)throw Error(u(529,""));return null;case"script":return e=t.async,t=t.src,typeof t=="string"&&e&&typeof e!="function"&&typeof e!="symbol"?(e=Zt(t),t=ct(l).hoistableScripts,a=t.get(e),a||(a={type:"script",instance:null,count:0,state:null},t.set(e,a)),a):{type:"void",instance:null,count:0,state:null};default:throw Error(u(444,n))}}function Xt(n){return'href="'+yn(n)+'"'}function Ya(n){return'link[rel="stylesheet"]['+n+"]"}function fc(n){return U({},n,{"data-precedence":n.precedence,precedence:null})}function w8(n,e,t,a){n.querySelector('link[rel="preload"][as="style"]['+e+"]")?a.loading=1:(e=n.createElement("link"),a.preload=e,e.addEventListener("load",function(){return a.loading|=1}),e.addEventListener("error",function(){return a.loading|=2}),q0(e,"link",t),M0(e),n.head.appendChild(e))}function Zt(n){return'[src="'+yn(n)+'"]'}function Ga(n){return"script[async]"+n}function uc(n,e,t){if(e.count++,e.instance===null)switch(e.type){case"style":var a=n.querySelector('style[data-href~="'+yn(t.href)+'"]');if(a)return e.instance=a,M0(a),a;var l=U({},t,{"data-href":t.href,"data-precedence":t.precedence,href:null,precedence:null});return a=(n.ownerDocument||n).createElement("style"),M0(a),q0(a,"style",l),sd(a,t.precedence,n),e.instance=a;case"stylesheet":l=Xt(t.href);var i=n.querySelector(Ya(l));if(i)return e.state.loading|=4,e.instance=i,M0(i),i;a=fc(t),(l=Tn.get(l))&&Xi(a,l),i=(n.ownerDocument||n).createElement("link"),M0(i);var o=i;return o._p=new Promise(function(g,m){o.onload=g,o.onerror=m}),q0(i,"link",a),e.state.loading|=4,sd(i,t.precedence,n),e.instance=i;case"script":return i=Zt(t.src),(l=n.querySelector(Ga(i)))?(e.instance=l,M0(l),l):(a=t,(l=Tn.get(i))&&(a=U({},t),Zi(a,l)),n=n.ownerDocument||n,l=n.createElement("script"),M0(l),q0(l,"link",a),n.head.appendChild(l),e.instance=l);case"void":return null;default:throw Error(u(443,e.type))}else e.type==="stylesheet"&&(e.state.loading&4)===0&&(a=e.instance,e.state.loading|=4,sd(a,t.precedence,n));return e.instance}function sd(n,e,t){for(var a=t.querySelectorAll('link[rel="stylesheet"][data-precedence],style[data-precedence]'),l=a.length?a[a.length-1]:null,i=l,o=0;o<a.length;o++){var g=a[o];if(g.dataset.precedence===e)i=g;else if(i!==l)break}i?i.parentNode.insertBefore(n,i.nextSibling):(e=t.nodeType===9?t.head:t,e.insertBefore(n,e.firstChild))}function Xi(n,e){n.crossOrigin==null&&(n.crossOrigin=e.crossOrigin),n.referrerPolicy==null&&(n.referrerPolicy=e.referrerPolicy),n.title==null&&(n.title=e.title)}function Zi(n,e){n.crossOrigin==null&&(n.crossOrigin=e.crossOrigin),n.referrerPolicy==null&&(n.referrerPolicy=e.referrerPolicy),n.integrity==null&&(n.integrity=e.integrity)}var od=null;function sc(n,e,t){if(od===null){var a=new Map,l=od=new Map;l.set(t,a)}else l=od,a=l.get(t),a||(a=new Map,l.set(t,a));if(a.has(n))return a;for(a.set(n,null),t=t.getElementsByTagName(n),l=0;l<t.length;l++){var i=t[l];if(!(i[aa]||i[R0]||n==="link"&&i.getAttribute("rel")==="stylesheet")&&i.namespaceURI!=="http://www.w3.org/2000/svg"){var o=i.getAttribute(e)||"";o=n+o;var g=a.get(o);g?g.push(i):a.set(o,[i])}}return a}function oc(n,e,t){n=n.ownerDocument||n,n.head.insertBefore(t,e==="title"?n.querySelector("head > title"):null)}function q8(n,e,t){if(t===1||e.itemProp!=null)return!1;switch(n){case"meta":case"title":return!0;case"style":if(typeof e.precedence!="string"||typeof e.href!="string"||e.href==="")break;return!0;case"link":if(typeof e.rel!="string"||typeof e.href!="string"||e.href===""||e.onLoad||e.onError)break;switch(e.rel){case"stylesheet":return n=e.disabled,typeof e.precedence=="string"&&n==null;default:return!0}case"script":if(e.async&&typeof e.async!="function"&&typeof e.async!="symbol"&&!e.onLoad&&!e.onError&&e.src&&typeof e.src=="string")return!0}return!1}function cc(n){return!(n.type==="stylesheet"&&(n.state.loading&3)===0)}function Y8(n,e,t,a){if(t.type==="stylesheet"&&(typeof a.media!="string"||matchMedia(a.media).matches!==!1)&&(t.state.loading&4)===0){if(t.instance===null){var l=Xt(a.href),i=e.querySelector(Ya(l));if(i){e=i._p,e!==null&&typeof e=="object"&&typeof e.then=="function"&&(n.count++,n=cd.bind(n),e.then(n,n)),t.state.loading|=4,t.instance=i,M0(i);return}i=e.ownerDocument||e,a=fc(a),(l=Tn.get(l))&&Xi(a,l),i=i.createElement("link"),M0(i);var o=i;o._p=new Promise(function(g,m){o.onload=g,o.onerror=m}),q0(i,"link",a),t.instance=i}n.stylesheets===null&&(n.stylesheets=new Map),n.stylesheets.set(t,e),(e=t.state.preload)&&(t.state.loading&3)===0&&(n.count++,t=cd.bind(n),e.addEventListener("load",t),e.addEventListener("error",t))}}var Vi=0;function G8(n,e){return n.stylesheets&&n.count===0&&Id(n,n.stylesheets),0<n.count||0<n.imgCount?function(t){var a=setTimeout(function(){if(n.stylesheets&&Id(n,n.stylesheets),n.unsuspend){var i=n.unsuspend;n.unsuspend=null,i()}},6e4+e);0<n.imgBytes&&Vi===0&&(Vi=62500*S8());var l=setTimeout(function(){if(n.waitingForImages=!1,n.count===0&&(n.stylesheets&&Id(n,n.stylesheets),n.unsuspend)){var i=n.unsuspend;n.unsuspend=null,i()}},(n.imgBytes>Vi?50:800)+e);return n.unsuspend=t,function(){n.unsuspend=null,clearTimeout(a),clearTimeout(l)}}:null}function cd(){if(this.count--,this.count===0&&(this.imgCount===0||!this.waitingForImages)){if(this.stylesheets)Id(this,this.stylesheets);else if(this.unsuspend){var n=this.unsuspend;this.unsuspend=null,n()}}}var gd=null;function Id(n,e){n.stylesheets=null,n.unsuspend!==null&&(n.count++,gd=new Map,e.forEach(L8,n),gd=null,cd.call(n))}function L8(n,e){if(!(e.state.loading&4)){var t=gd.get(n);if(t)var a=t.get(null);else{t=new Map,gd.set(n,t);for(var l=n.querySelectorAll("link[data-precedence],style[data-precedence]"),i=0;i<l.length;i++){var o=l[i];(o.nodeName==="LINK"||o.getAttribute("media")!=="not all")&&(t.set(o.dataset.precedence,o),a=o)}a&&t.set(null,a)}l=e.instance,o=l.getAttribute("data-precedence"),i=t.get(o)||a,i===a&&t.set(null,l),t.set(o,l),this.count++,a=cd.bind(this),l.addEventListener("load",a),l.addEventListener("error",a),i?i.parentNode.insertBefore(l,i.nextSibling):(n=n.nodeType===9?n.head:n,n.insertBefore(l,n.firstChild)),e.state.loading|=4}}var La={$$typeof:Y0,Provider:null,Consumer:null,_currentValue:L,_currentValue2:L,_threadCount:0};function Q8(n,e,t,a,l,i,o,g,m){this.tag=1,this.containerInfo=n,this.pingCache=this.current=this.pendingChildren=null,this.timeoutHandle=-1,this.callbackNode=this.next=this.pendingContext=this.context=this.cancelPendingCommit=null,this.callbackPriority=0,this.expirationTimes=Gd(-1),this.entangledLanes=this.shellSuspendCounter=this.errorRecoveryDisabledLanes=this.expiredLanes=this.warmLanes=this.pingedLanes=this.suspendedLanes=this.pendingLanes=0,this.entanglements=Gd(0),this.hiddenUpdates=Gd(null),this.identifierPrefix=a,this.onUncaughtError=l,this.onCaughtError=i,this.onRecoverableError=o,this.pooledCache=null,this.pooledCacheLanes=0,this.formState=m,this.incompleteTransitions=new Map}function gc(n,e,t,a,l,i,o,g,m,x,j,D){return n=new Q8(n,e,t,o,m,x,j,D,g),e=1,i===!0&&(e|=24),i=sn(3,null,null,e),n.current=i,i.stateNode=n,e=El(),e.refCount++,n.pooledCache=e,e.refCount++,i.memoizedState={element:a,isDehydrated:t,cache:e},zl(i),n}function Ic(n){return n?(n=_t,n):_t}function vc(n,e,t,a,l,i){l=Ic(l),a.context===null?a.context=l:a.pendingContext=l,a=Ie(e),a.payload={element:t},i=i===void 0?null:i,i!==null&&(a.callback=i),t=ve(n,a,e),t!==null&&(tn(t,n,e),ba(t,n,e))}function mc(n,e){if(n=n.memoizedState,n!==null&&n.dehydrated!==null){var t=n.retryLane;n.retryLane=t!==0&&t<e?t:e}}function Ki(n,e){mc(n,e),(n=n.alternate)&&mc(n,e)}function hc(n){if(n.tag===13||n.tag===31){var e=Ze(n,67108864);e!==null&&tn(e,n,67108864),Ki(n,67108864)}}function yc(n){if(n.tag===13||n.tag===31){var e=vn();e=Ld(e);var t=Ze(n,e);t!==null&&tn(t,n,e),Ki(n,e)}}var vd=!0;function X8(n,e,t,a){var l=O.T;O.T=null;var i=M.p;try{M.p=2,Ji(n,e,t,a)}finally{M.p=i,O.T=l}}function Z8(n,e,t,a){var l=O.T;O.T=null;var i=M.p;try{M.p=8,Ji(n,e,t,a)}finally{M.p=i,O.T=l}}function Ji(n,e,t,a){if(vd){var l=ki(a);if(l===null)Ui(n,e,a,md,t),bc(n,a);else if(K8(l,n,e,t,a))a.stopPropagation();else if(bc(n,a),e&4&&-1<V8.indexOf(n)){for(;l!==null;){var i=ot(l);if(i!==null)switch(i.tag){case 3:if(i=i.stateNode,i.current.memoizedState.isDehydrated){var o=Ye(i.pendingLanes);if(o!==0){var g=i;for(g.pendingLanes|=2,g.entangledLanes|=2;o;){var m=1<<31-fn(o);g.entanglements[1]|=m,o&=~m}wn(i),(r0&6)===0&&(Fr=dn()+500,Ba(0))}}break;case 31:case 13:g=Ze(i,2),g!==null&&tn(g,i,2),nd(),Ki(i,2)}if(i=ki(a),i===null&&Ui(n,e,a,md,t),i===l)break;l=i}l!==null&&a.stopPropagation()}else Ui(n,e,a,null,t)}}function ki(n){return n=Wd(n),$i(n)}var md=null;function $i(n){if(md=null,n=st(n),n!==null){var e=c(n);if(e===null)n=null;else{var t=e.tag;if(t===13){if(n=v(e),n!==null)return n;n=null}else if(t===31){if(n=p(e),n!==null)return n;n=null}else if(t===3){if(e.stateNode.current.memoizedState.isDehydrated)return e.tag===3?e.stateNode.containerInfo:null;n=null}else e!==n&&(n=null)}}return md=n,null}function pc(n){switch(n){case"beforetoggle":case"cancel":case"click":case"close":case"contextmenu":case"copy":case"cut":case"auxclick":case"dblclick":case"dragend":case"dragstart":case"drop":case"focusin":case"focusout":case"input":case"invalid":case"keydown":case"keypress":case"keyup":case"mousedown":case"mouseup":case"paste":case"pause":case"play":case"pointercancel":case"pointerdown":case"pointerup":case"ratechange":case"reset":case"resize":case"seeked":case"submit":case"toggle":case"touchcancel":case"touchend":case"touchstart":case"volumechange":case"change":case"selectionchange":case"textInput":case"compositionstart":case"compositionend":case"compositionupdate":case"beforeblur":case"afterblur":case"beforeinput":case"blur":case"fullscreenchange":case"focus":case"hashchange":case"popstate":case"select":case"selectstart":return 2;case"drag":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"mousemove":case"mouseout":case"mouseover":case"pointermove":case"pointerout":case"pointerover":case"scroll":case"touchmove":case"wheel":case"mouseenter":case"mouseleave":case"pointerenter":case"pointerleave":return 8;case"message":switch(C4()){case Tf:return 2;case jf:return 8;case dr:case N4:return 32;case Of:return 268435456;default:return 32}default:return 32}}var Wi=!1,Te=null,je=null,Oe=null,Qa=new Map,Xa=new Map,ze=[],V8="mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset".split(" ");function bc(n,e){switch(n){case"focusin":case"focusout":Te=null;break;case"dragenter":case"dragleave":je=null;break;case"mouseover":case"mouseout":Oe=null;break;case"pointerover":case"pointerout":Qa.delete(e.pointerId);break;case"gotpointercapture":case"lostpointercapture":Xa.delete(e.pointerId)}}function Za(n,e,t,a,l,i){return n===null||n.nativeEvent!==i?(n={blockedOn:e,domEventName:t,eventSystemFlags:a,nativeEvent:i,targetContainers:[l]},e!==null&&(e=ot(e),e!==null&&hc(e)),n):(n.eventSystemFlags|=a,e=n.targetContainers,l!==null&&e.indexOf(l)===-1&&e.push(l),n)}function K8(n,e,t,a,l){switch(e){case"focusin":return Te=Za(Te,n,e,t,a,l),!0;case"dragenter":return je=Za(je,n,e,t,a,l),!0;case"mouseover":return Oe=Za(Oe,n,e,t,a,l),!0;case"pointerover":var i=l.pointerId;return Qa.set(i,Za(Qa.get(i)||null,n,e,t,a,l)),!0;case"gotpointercapture":return i=l.pointerId,Xa.set(i,Za(Xa.get(i)||null,n,e,t,a,l)),!0}return!1}function Sc(n){var e=st(n.target);if(e!==null){var t=c(e);if(t!==null){if(e=t.tag,e===13){if(e=v(t),e!==null){n.blockedOn=e,Uf(n.priority,function(){yc(t)});return}}else if(e===31){if(e=p(t),e!==null){n.blockedOn=e,Uf(n.priority,function(){yc(t)});return}}else if(e===3&&t.stateNode.current.memoizedState.isDehydrated){n.blockedOn=t.tag===3?t.stateNode.containerInfo:null;return}}}n.blockedOn=null}function hd(n){if(n.blockedOn!==null)return!1;for(var e=n.targetContainers;0<e.length;){var t=ki(n.nativeEvent);if(t===null){t=n.nativeEvent;var a=new t.constructor(t.type,t);$d=a,t.target.dispatchEvent(a),$d=null}else return e=ot(t),e!==null&&hc(e),n.blockedOn=t,!1;e.shift()}return!0}function _c(n,e,t){hd(n)&&t.delete(e)}function J8(){Wi=!1,Te!==null&&hd(Te)&&(Te=null),je!==null&&hd(je)&&(je=null),Oe!==null&&hd(Oe)&&(Oe=null),Qa.forEach(_c),Xa.forEach(_c)}function yd(n,e){n.blockedOn===e&&(n.blockedOn=null,Wi||(Wi=!0,r.unstable_scheduleCallback(r.unstable_NormalPriority,J8)))}var pd=null;function xc(n){pd!==n&&(pd=n,r.unstable_scheduleCallback(r.unstable_NormalPriority,function(){pd===n&&(pd=null);for(var e=0;e<n.length;e+=3){var t=n[e],a=n[e+1],l=n[e+2];if(typeof a!="function"){if($i(a||t)===null)continue;break}var i=ot(t);i!==null&&(n.splice(e,3),e-=3,kl(i,{pending:!0,data:l,method:t.method,action:a},a,l))}}))}function Vt(n){function e(m){return yd(m,n)}Te!==null&&yd(Te,n),je!==null&&yd(je,n),Oe!==null&&yd(Oe,n),Qa.forEach(e),Xa.forEach(e);for(var t=0;t<ze.length;t++){var a=ze[t];a.blockedOn===n&&(a.blockedOn=null)}for(;0<ze.length&&(t=ze[0],t.blockedOn===null);)Sc(t),t.blockedOn===null&&ze.shift();if(t=(n.ownerDocument||n).$$reactFormReplay,t!=null)for(a=0;a<t.length;a+=3){var l=t[a],i=t[a+1],o=l[$0]||null;if(typeof i=="function")o||xc(t);else if(o){var g=null;if(i&&i.hasAttribute("formAction")){if(l=i,o=i[$0]||null)g=o.formAction;else if($i(l)!==null)continue}else g=o.action;typeof g=="function"?t[a+1]=g:(t.splice(a,3),a-=3),xc(t)}}}function Ac(){function n(i){i.canIntercept&&i.info==="react-transition"&&i.intercept({handler:function(){return new Promise(function(o){return l=o})},focusReset:"manual",scroll:"manual"})}function e(){l!==null&&(l(),l=null),a||setTimeout(t,20)}function t(){if(!a&&!navigation.transition){var i=navigation.currentEntry;i&&i.url!=null&&navigation.navigate(i.url,{state:i.getState(),info:"react-transition",history:"replace"})}}if(typeof navigation=="object"){var a=!1,l=null;return navigation.addEventListener("navigate",n),navigation.addEventListener("navigatesuccess",e),navigation.addEventListener("navigateerror",e),setTimeout(t,100),function(){a=!0,navigation.removeEventListener("navigate",n),navigation.removeEventListener("navigatesuccess",e),navigation.removeEventListener("navigateerror",e),l!==null&&(l(),l=null)}}}function Fi(n){this._internalRoot=n}bd.prototype.render=Fi.prototype.render=function(n){var e=this._internalRoot;if(e===null)throw Error(u(409));var t=e.current,a=vn();vc(t,a,n,e,null,null)},bd.prototype.unmount=Fi.prototype.unmount=function(){var n=this._internalRoot;if(n!==null){this._internalRoot=null;var e=n.containerInfo;vc(n.current,2,null,n,null,null),nd(),e[ut]=null}};function bd(n){this._internalRoot=n}bd.prototype.unstable_scheduleHydration=function(n){if(n){var e=Mf();n={blockedOn:null,target:n,priority:e};for(var t=0;t<ze.length&&e!==0&&e<ze[t].priority;t++);ze.splice(t,0,n),t===0&&Sc(n)}};var Ec=d.version;if(Ec!=="19.2.9")throw Error(u(527,Ec,"19.2.9"));M.findDOMNode=function(n){var e=n._reactInternals;if(e===void 0)throw typeof n.render=="function"?Error(u(188)):(n=Object.keys(n).join(","),Error(u(268,n)));return n=S(e),n=n!==null?N(n):null,n=n===null?null:n.stateNode,n};var k8={bundleType:0,version:"19.2.9",rendererPackageName:"react-dom",currentDispatcherRef:O,reconcilerVersion:"19.2.9"};if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<"u"){var Sd=__REACT_DEVTOOLS_GLOBAL_HOOK__;if(!Sd.isDisabled&&Sd.supportsFiber)try{na=Sd.inject(k8),ln=Sd}catch{}}return Ka.createRoot=function(n,e){if(!s(n))throw Error(u(299));var t=!1,a="",l=Cs,i=Ns,o=Ms;return e!=null&&(e.unstable_strictMode===!0&&(t=!0),e.identifierPrefix!==void 0&&(a=e.identifierPrefix),e.onUncaughtError!==void 0&&(l=e.onUncaughtError),e.onCaughtError!==void 0&&(i=e.onCaughtError),e.onRecoverableError!==void 0&&(o=e.onRecoverableError)),e=gc(n,1,!1,null,null,t,a,null,l,i,o,Ac),n[ut]=e.current,Mi(n),new Fi(e)},Ka.hydrateRoot=function(n,e,t){if(!s(n))throw Error(u(299));var a=!1,l="",i=Cs,o=Ns,g=Ms,m=null;return t!=null&&(t.unstable_strictMode===!0&&(a=!0),t.identifierPrefix!==void 0&&(l=t.identifierPrefix),t.onUncaughtError!==void 0&&(i=t.onUncaughtError),t.onCaughtError!==void 0&&(o=t.onCaughtError),t.onRecoverableError!==void 0&&(g=t.onRecoverableError),t.formState!==void 0&&(m=t.formState)),e=gc(n,1,!0,e,t??null,a,l,m,i,o,g,Ac),e.context=Ic(null),t=e.current,a=vn(),a=Ld(a),l=Ie(a),l.callback=null,ve(t,l,a),t=a,e.current.lanes=t,ta(e,t),wn(e),n[ut]=e.current,Mi(n),new bd(e)},Ka.version="19.2.9",Ka}var Rc;function ig(){if(Rc)return nf.exports;Rc=1;function r(){if(!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__>"u"||typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE!="function"))try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(r)}catch(d){console.error(d)}}return r(),nf.exports=lg(),nf.exports}var fg=ig(),l0=If();let dt=null,Ad=null,ug=0;function sg(r,d,f){dt={mount:r,controller:d,view:f,sequence:++ug},Ad==null||Ad(dt)}function og(r){(dt==null?void 0:dt.mount)===r&&(dt=null)}function rn(){return dt}function Jt(r){Ad=r}function cg(r,d){const f=l0.useRef({});function u(){sg(f.current,r,d)}function s(){function c(){og(f.current)}return c}l0.useLayoutEffect(u),l0.useLayoutEffect(s,[])}function gg(r){return/^[A-Za-z][A-Za-z0-9_]*$/.test(r)&&!Ig.has(r)}const Ig=new Set(["sig","one","lone","some","no","all","fact","pred","run","check","and","or","not","implies","univ","none","Int","abstract","as","assert","but","check","disj","else","enum","exactly","expect","extends","for","fun","iden","iff","in","let","module","open","private","seq","set","sum","this","var","always","eventually","after","before","until","releases","historically","once","since","triggered"]);function vg(r){let d=-1;for(const f of r.fields){let u=-1;for(let s=0;s<r.signatures.length;s++)r.signatures[s].id===f.ownerSignatureId&&(u=s);if(u<0||u<d)return!1;d=u}return!0}function Xc(r,d){const f=[],u=new Set;for(const s of r.signatures){u.add(s.id);for(const c of d)c.ownerSignatureId===s.id&&f.push(c)}for(const s of d)u.has(s.ownerSignatureId)||f.push(s);return f}function mg(r,d){let f=d.fields.length>r.fields.length;for(const u of d.fields)for(const s of r.fields)u.id===s.id&&u.ownerSignatureId!==s.ownerSignatureId&&(f=!0);return f?"Draft field insertion/reassignment grouped by signature order; within-owner order retained. Accepted history unchanged.":null}function Bc(){const r=[];for(let d=1;d<=8;d++)r.push({columns:Array(d).fill(null)});return r}function df(r){return r.kind==="formula"?{sort:"formula",shapes:[]}:{sort:"relation",shapes:[{columns:r.columns}]}}function Kt(r){const d=[r.sort];for(const f of r.shapes)d.push(JSON.stringify(f.columns));return d}function Zc(r,d,f){const{ownerId:u,role:s,rule:c,expected:v,actual:p,relatedIds:A}=r;return{key:JSON.stringify([u,s,c,v,p,A]),identity:r,nodeId:d,message:f}}function nr(r,d){if(r.columns.length!==d.columns.length)return null;const f=[];for(let u=0;u<r.columns.length;u++){const s=r.columns[u],c=d.columns[u];if(s!==null&&c!==null&&s!==c)return null;f.push(s??c)}return{columns:f}}function ka(r){const d=[];for(let f=1;f<=8;f++){const u=[];for(const c of r)c.columns.length===f&&u.push(c);if(!u.length)continue;const s=[];for(let c=0;c<f;c++){let v=u[0].columns[c];for(const p of u)p.columns[c]!==v&&(v=null);s.push(v)}d.push({columns:s})}return d}function hg(r,d){const f=[];for(const u of r)for(const s of d){const c=nr(u,s);c&&f.push(c)}return ka(f)}function yg(r,d){return JSON.stringify(r)===JSON.stringify(d)}function Vc(r,d){const f="arguments"in r?"argument":"bodyId"in r?"body":"operandId"in r?"operand":d===0?"left":"right";return{ownerId:r.id,role:f,...f==="argument"?{index:d}:{}}}function pg(r){if(r.nodes.length>512)return!1;const d=new Map,f=new Set;for(const s of r.nodes)d.set(s.id,s);if(d.size!==r.nodes.length)return!1;const u=[];for(const s of[...r.predicates,...r.facts,...r.assertions])u.push({id:s.bodyId,depth:0});for(;u.length;){const s=u.pop(),c=d.get(s.id);if(!c||f.has(s.id)||s.depth>=32)return!1;f.add(s.id);for(const v of Be(c))u.push({id:v,depth:s.depth+1})}return f.size===r.nodes.length}function Me(r,d){const f=d.expected==="relation"?"relation":d.expected?[d.expected.kind,...d.expected.kind==="relation"?d.expected.columns:[]]:null,u=JSON.stringify([d.ownerId,d.role,d.rule,d.ids,f,d.widths,d.relatedIds]);r.set(u,{...d,key:u})}function bg(r,d,f){const u=Be(d);for(let s=0;s<u.length;s++){const c=Vc(d,s);let v="relation";if(("binder"in d||d.tag==="not"||["and","or","implies","iff"].includes(d.tag))&&(v={kind:"formula"}),d.tag==="predicate_call"){let p;for(const A of r.predicates)A.id===d.predicateId&&(p=A.parameters[s]);if(!p)continue;v={kind:"relation",columns:p.columns}}Me(f,{ownerId:d.id,role:c.role+(c.index===void 0?"":`:${c.index}`),rule:"expect",ids:[u[s]],expected:v,...d.tag==="transpose"?{widths:[2]}:{},...d.tag==="predicate_call"?{relatedIds:[d.predicateId]}:{}})}}function Sg(r,d){if(r.tag==="transpose"&&Me(d,{ownerId:r.id,role:"operand",rule:"transpose",ids:[r.operandId,r.id]}),!("leftId"in r))return;const f=[r.leftId,r.rightId];["equal","subset","union","intersection","difference"].includes(r.tag)&&Me(d,{ownerId:r.id,role:"operands",rule:"equal",ids:f}),["union","intersection","difference"].includes(r.tag)&&Me(d,{ownerId:r.id,role:"result",rule:"equal",ids:[r.id,r.leftId]}),(r.tag==="product"||r.tag==="join")&&Me(d,{ownerId:r.id,role:"result",rule:r.tag,ids:[r.leftId,r.rightId,r.id]})}function _g(r,d){const f=new Map,u=new Map;for(const s of[...r.predicates,...r.facts,...r.assertions])u.set(s.bodyId,{ownerId:s.id,role:"body"}),Me(f,{ownerId:s.id,role:"body",rule:"expect",ids:[s.bodyId],expected:{kind:"formula"}});for(const s of r.nodes){let c=0;for(const v of Be(s))u.set(v,Vc(s,c++));bg(r,s,f),Sg(s,f)}for(const s of r.nodes)if(s.tag==="hole"&&s.expected){const c=u.get(s.id);c&&Me(f,{ownerId:c.ownerId,role:`${c.role}:${c.index??""}:explicit`,rule:"expect",ids:[s.id],expected:s.expected})}for(const s of d)for(const[c,v]of u)v.ownerId===s.slot.ownerId&&v.role===s.slot.role&&v.index===s.slot.index&&Me(f,{ownerId:v.ownerId,role:`${v.role}:${v.index??""}:explicit`,rule:"expect",ids:[c],expected:s.expected});return{equations:[...f.values()].sort(Ag),slots:u,valid:pg(r)}}function xg(r,d){if(r.tag==="hole")return"unknown";const f=d.types.get(r.id);return f?f.kind:["signature_ref","field_ref","variable_ref","transpose","union","intersection","difference","join","product"].includes(r.tag)?"relation":"formula"}function Ag(r,d){return r.key.localeCompare(d.key)}function Eg(r,d){const f=[];for(const s of r)for(const c of d){const v=nr(s,c);v&&f.push(v)}const u=ka(f);return{inputs:[u,u]}}function Tg(r,d){const f=[],u=[];for(const s of r)if(s.columns.length===2)for(const c of d){const v=nr({columns:[...s.columns].reverse()},c);v&&(f.push({columns:[...v.columns].reverse()}),u.push(v))}return{inputs:[ka(f),ka(u)]}}function jg(r,d,f){const u=nr({columns:[...r.columns,...d.columns]},f);return!u||u.columns.length>8?null:[{columns:u.columns.slice(0,r.columns.length)},{columns:u.columns.slice(r.columns.length)},u]}function Og(r,d,f){const u=r.columns.at(-1),s=d.columns[0];if(u!==null&&s!==null&&u!==s)return null;const c=u??s,v=nr({columns:[...r.columns.slice(0,-1),...d.columns.slice(1)]},f);if(!v||v.columns.length<1||v.columns.length>8)return null;const p=r.columns.length-1;return[{columns:[...v.columns.slice(0,p),c]},{columns:[c,...v.columns.slice(p)]},v]}function zg(r,d,f,u){const s=[[],[],[]];for(const c of d)for(const v of f)for(const p of u){const A=r==="product"?jg(c,v,p):Og(c,v,p);if(A)for(let S=0;S<A.length;S++)s[S].push(A[S])}return{inputs:s.map(ka)}}function Dg(r){if(!r||r.sort!=="relation"||r.shapes.length!==1)return null;const d=[];for(const f of r.shapes[0].columns){if(f===null)return null;d.push(f)}return d}function Cg(r,d,f,u){var v;if(d.rule==="expect")return d.expected==="relation"?((v=d.widths)==null?void 0:v.length)===1?`relation width ${d.widths[0]}`:"nonempty relation schema":$a(r,d.expected);if(d.rule==="product")return"relation: concatenated result width≤8";if(d.rule==="join")return"relation: left-last = right-first; result nonempty, width≤8";if(d.rule==="transpose")return"binary relation [A → B]";let s;for(const p of d.ids)if(p!==f){s=p;break}const c=Dg(s?u.get(s):void 0);return c?$a(r,{kind:"relation",columns:c}):"relation matching resolved sibling schema"}function Ng(r,d,f,u){var U;const s=[],c=[];for(const Y of d.equations)Y.ids.includes(u)&&(s.push(Y),Y.rule==="expect"&&Y.ids[0]===u&&c.push(Y));const v=c[0],p=(v==null?void 0:v.expected)!=="relation"&&((U=v==null?void 0:v.expected)==null?void 0:U.kind)==="formula"?"formula":"relation";let A=null,S=p==="relation"?[1,2,3,4,5,6,7,8]:[];for(const Y of c){const u0=Y.expected;u0&&u0!=="relation"&&u0.kind==="relation"&&(A=u0.columns),Y.widths&&(S=Y.widths)}const N=new Set;for(const Y of s)N.add(Cg(r,Y,u,f));return{slot:d.slots.get(u),sort:p,exact:A,widths:S,descriptions:N.size?[...N]:[p]}}function Mg(r,d,f){const u=new Map;for(const s of d.slots.keys())u.set(s,Ng(r,d,f,s));return u}const Ja={columnVariables:4096,equations:32768,violations:65536,worklistPops:262144,refinements:262144};class Ug{constructor(d,f,u,s){n0(this,"facts",new Map);n0(this,"violations",new Map);n0(this,"dependencies",new Map);n0(this,"pending",[]);n0(this,"queued",new Set);n0(this,"counters",{columnVariables:0,equations:0,violations:0,worklistPops:0,refinements:0});n0(this,"failure",null);n0(this,"graph");this.module=d,this.limits=s,u.length>s.equations?(this.failure={code:"ANALYSIS_RESOURCE_LIMIT",counter:"equations",limit:s.equations},this.graph={equations:[],slots:new Map,valid:!0}):this.graph=_g(d,u);for(const c of d.nodes){const v=xg(c,f),p=f.types.get(c.id);this.facts.set(c.id,p?df(p):{sort:v,shapes:v==="relation"?Bc():[]})}}count(d,f=1){return this.counters[d]+=f,this.counters[d]>this.limits[d]&&(this.failure={code:"ANALYSIS_RESOURCE_LIMIT",counter:d,limit:this.limits[d]}),!this.failure}enqueue(d){this.queued.has(d)||(this.queued.add(d),this.pending.push(d))}refine(d,f){const u=this.facts.get(d);if(!(!u||yg(u,f)||this.failure)&&this.count("refinements")){this.facts.set(d,f);for(const s of this.dependencies.get(d)??[])this.enqueue(s)}}reject(d,f,u,s){const c=Zc({ownerId:d.ownerId,role:d.role,rule:d.rule,expected:f,actual:u,relatedIds:d.relatedIds??[]},d.ids[0],s);this.violations.has(c.key)||!this.count("violations")||this.violations.set(c.key,c)}validExpected(d,f){const u=d.expected;if(!u||u==="relation"||u.kind==="formula")return!0;const s=new Set;for(const v of this.module.signatures)s.add(v.id);let c=u.columns.length>=1&&u.columns.length<=8;for(const v of u.columns)s.has(v)||(c=!1);return!c&&f&&this.reject(d,["declared-schema-width1..8"],Kt(df(u)),"Invalid nominal destination schema."),c}expectation(d,f){const u=d.ids[0],s=this.facts.get(u);if(!this.validExpected(d,f))return;const c=d.expected==="relation"?{sort:"relation",shapes:Bc()}:df(d.expected),v=[];for(const S of c.shapes)(!d.widths||d.widths.includes(S.columns.length))&&v.push(S);const p={...c,shapes:v};if(s.sort!=="unknown"&&s.sort!==p.sort){f&&this.reject(d,Kt(p),Kt(s),`Expected ${p.sort}; actual ${s.sort}.`);return}const A=s.sort==="unknown"?p.shapes:hg(s.shapes,p.shapes);if(p.sort==="relation"&&!A.length){f&&this.reject(d,Kt(p),Kt(s),"Ordered nominal schema or relation width constraint mismatch.");return}f||this.refine(u,{sort:p.sort,shapes:A})}relation(d,f){const u=[];for(const p of d.ids){const A=this.facts.get(p);if(A.sort!=="relation")return;u.push(A)}const s=[];for(const p of u)s.push(p.shapes);const c=d.rule==="equal"?Eg(s[0],s[1]):d.rule==="transpose"?Tg(s[0],s[1]):zg(d.rule,s[0],s[1],s[2]);let v=!0;for(const p of c.inputs)p.length||(v=!1);if(!v){const p=[];for(const A of u)p.push(...Kt(A));f&&this.reject(d,[d.rule],p,`Known ${d.rule} nominal schema, endpoint or width contradiction.`);return}if(!f)for(let p=0;p<c.inputs.length;p++)this.refine(d.ids[p],{sort:"relation",shapes:c.inputs[p]})}apply(d,f){d.rule==="expect"?this.expectation(d,f):this.relation(d,f)}initialize(){if(this.failure)return!1;if(!this.graph.valid)return this.failure={code:"ANALYSIS_INVALID_GRAPH"},!1;if(!this.count("columnVariables",this.module.nodes.length*8)||!this.count("equations",this.graph.equations.length))return!1;let d=0;for(const f of this.graph.equations){for(const u of f.ids){const s=this.dependencies.get(u)??new Set;s.add(d),this.dependencies.set(u,s)}this.enqueue(d++)}return!0}run(){if(this.initialize()){let d=0;for(;d<this.pending.length&&!this.failure;){const f=this.pending[d++];if(this.queued.delete(f),!this.count("worklistPops"))break;this.apply(this.graph.equations[f],!1)}if(!this.failure){for(const f of this.graph.equations)if(this.apply(f,!0),this.failure)break}}return{facts:this.facts,destinations:Mg(this.module,this.graph,this.facts),violations:this.violations,resourceFailure:this.failure}}}function Rg(r,d,f,u=Ja){const s={...Ja};for(const c of Object.keys(s)){const v=u[c];s[c]=Number.isNaN(v)?0:Math.max(0,Math.floor(Math.min(Ja[c],v)))}return new Ug(r,d,f,s).run()}function Bg(r,d){if(r.identity.rule!=="exact-11"||r.nodeId!==d.nodeId)return!1;const f=r.identity.expected,u=f[0]==="formula"?["formula"]:["relation",JSON.stringify(f.slice(1))];return JSON.stringify(u)===JSON.stringify(d.identity.expected)}function Hg(r,d){if(Bg(r,d))return!0;if(r.identity.ownerId!==d.identity.ownerId||d.identity.role.endsWith(":explicit"))return!1;const f=r.identity.rule,u=d.identity.rule;return u==="expect"?["exact-19","exact-20","exact-21","exact-22","exact-23"].includes(f):u==="equal"?f==="exact-25":u==="transpose"?f==="exact-21":u==="join"?f==="exact-24"||f==="exact-26":u==="product"&&f==="exact-26"}function wg(r,d,f){for(const u of f.values()){let s=!1;for(const c of d.values())if(Hg(c,u)){s=!0;break}if(!s)for(const c of r)c.nodeId===u.nodeId&&c.message===u.message&&(s=!0);s||uf(r,u.nodeId,u.message)}}class qg{constructor(d,f=[],u){n0(this,"module");n0(this,"index");n0(this,"diagnostics",[]);n0(this,"types",new Map);n0(this,"scopes",new Map);n0(this,"owned",new Set);n0(this,"ids",new Set);n0(this,"names",new Set);n0(this,"complete",!0);n0(this,"violations",new Map);this.obligations=f,this.limits=u,this.module=d,this.index=He(d)}check(){this.declarations(),vg(this.module)||this.error("module","Fields must be grouped by signature owner order; submitted order is not normalized.","exact-01",[],this.fieldOrderFacts());for(const d of this.module.predicates)this.expect(d.bodyId,d.parameters,an,0);for(const d of[...this.module.facts,...this.module.assertions])this.expect(d.bodyId,[],an,0);for(const d of this.module.nodes)this.owned.has(d.id)||this.error(d.id,"Unreachable expression.","exact-02");return this.dependencies(),this.commands(),this.finish()}error(d,f,u,s=[],c=[]){uf(this.diagnostics,d,f);const v=Zc({ownerId:d,role:"node",rule:u,expected:s,actual:c,relatedIds:[]},d,f);this.violations.set(v.key,v)}finish(){var c;const d={diagnostics:this.diagnostics,types:this.types,scopes:this.scopes,complete:this.complete&&this.diagnostics.length===0},f=Rg(this.module,d,this.obligations,this.limits);wg(this.diagnostics,this.violations,f.violations);for(const[v,p]of f.violations)this.violations.set(v,p);const u=Math.min(Ja.violations,((c=this.limits)==null?void 0:c.violations)??Ja.violations),s=f.resourceFailure??(this.violations.size>u?{code:"ANALYSIS_RESOURCE_LIMIT",counter:"violations",limit:u}:null);return s&&uf(this.diagnostics,"module",s.code),{...d,...f,violations:this.violations,resourceFailure:s,complete:d.complete&&this.violations.size===0&&!s}}identity(d,f){this.ids.has(d)&&this.error(d,"Duplicate identity.","exact-03"),this.ids.add(d),f!==void 0&&((!gg(f)||f.length>64||f.startsWith("allow_"))&&this.error(d,"Invalid or reserved name.","exact-04",[],[f]),this.names.has(f)&&this.error(d,"Names must be globally unique.","exact-05",[],[f]),this.names.add(f))}declarations(){const d=this.module,f=[...d.signatures,...d.fields,...d.predicates,...d.facts,...d.assertions,...d.commands];(f.length>128||d.nodes.length>512)&&this.error("module","Declaration/node budget exceeded.","exact-06",["128","512"],[String(f.length),String(d.nodes.length)]);for(const u of f)this.identity(u.id,"name"in u?u.name:void 0);for(const u of d.nodes)this.identity(u.id),"binder"in u&&this.identity(u.binder.id,u.binder.name);for(const u of d.fields)_d(d,[u.ownerSignatureId,...u.rangeColumns])||this.error(u.id,"Field owner/range must be declared; full width 1..8.","exact-07",[],[u.ownerSignatureId,...u.rangeColumns]),u.rangeColumns.length>1&&u.multiplicity!=="set"&&this.error(u.id,"Tuple range permits set multiplicity only.","exact-08",[],[u.multiplicity,...u.rangeColumns]);for(const u of d.predicates){u.parameters.length>16&&this.error(u.id,"At most16 parameters.","exact-09",["16"],[String(u.parameters.length)]);for(const s of u.parameters)this.identity(s.id,s.name),_d(d,s.columns)||this.error(s.id,"Parameter requires declared nonempty nominal schema.","exact-10",[],s.columns)}}expect(d,f,u,s){const c=this.visit(d,f,s);return c&&!ff(c,u)&&this.error(d,`Expected ${this.describe(u)}; actual ${this.describe(c)}.`,"exact-11",[u.kind,...u.kind==="relation"?u.columns:[]],[c.kind,...c.kind==="relation"?c.columns:[]]),c}describe(d){return d.kind==="formula"?"formula":`relation [${d.columns.join(", ")}]`}visit(d,f,u){if(u>=32)return this.error(d,"Depth limit32 exceeded.","exact-12"),null;if(this.owned.has(d))return this.error(d,"Shared child or cycle.","exact-13"),null;this.owned.add(d),this.scopes.set(d,f);const s=this.index.get(d);if(!s)return this.error(d,"Dangling child.","exact-14"),null;if(s.tag==="hole")return this.complete=!1,null;const c=this.infer(s,f,u);return c&&this.types.set(d,c),c}infer(d,f,u){if("targetId"in d)return this.reference(d,f);if(d.tag==="predicate_call")return this.call(d,f,u);if("binder"in d){const s={tag:"parameter",id:d.binder.id,name:d.binder.name,columns:[d.binder.signatureId]};return _d(this.module,s.columns)||this.error(d.id,"Unknown quantifier signature.","exact-15",[],[d.binder.signatureId]),this.expect(d.bodyId,[...f,s],an,u+1),an}return"operandId"in d?this.unary(d,f,u):this.binary(d,f,u)}reference(d,f){var s;let u;if(d.tag==="signature_ref")for(const c of this.module.signatures)c.id===d.targetId&&(u=[c.id]);if(d.tag==="field_ref")for(const c of this.module.fields)c.id===d.targetId&&(u=[c.ownerSignatureId,...c.rangeColumns]);return d.tag==="variable_ref"&&(u=(s=Gg(f,d.targetId))==null?void 0:s.columns),u?{kind:"relation",columns:u}:(this.error(d.id,"Unknown declaration or out-of-scope binder.","exact-16",[],[d.targetId,...d.tag==="variable_ref"?this.scopeFacts(f):[]]),null)}call(d,f,u){let s;for(const c of this.module.predicates)c.id===d.predicateId&&(s=c.parameters);s||this.error(d.id,"Unknown predicate.","exact-17",[],[d.predicateId]),s&&s.length!==d.arguments.length&&this.error(d.id,"Predicate argument count mismatch.","exact-18",[d.predicateId,String(s.length)],[d.predicateId,String(d.arguments.length)]);for(let c=0;c<d.arguments.length;c++){const v=s==null?void 0:s[c];v?this.expect(d.arguments[c],f,{kind:"relation",columns:v.columns},u+1):this.visit(d.arguments[c],f,u+1)}return an}unary(d,f,u){const s=this.visit(d.operandId,f,u+1);return s?d.tag==="not"?(s.kind!=="formula"&&this.error(d.id,"not requires formula.","exact-19"),an):s.kind!=="relation"?(this.error(d.id,"Expected nonempty relation schema.","exact-20"),null):d.tag==="transpose"?s.columns.length!==2?(this.error(d.id,"Transpose requires exactly2 columns.","exact-21",["2"],[String(s.columns.length)]),null):{kind:"relation",columns:[s.columns[1],s.columns[0]]}:an:null}binary(d,f,u){const s=this.visit(d.leftId,f,u+1),c=this.visit(d.rightId,f,u+1);return["and","or","implies","iff"].includes(d.tag)?((s&&s.kind!=="formula"||c&&c.kind!=="formula")&&this.error(d.id,"Boolean operands require formulas.","exact-22"),an):s&&s.kind!=="relation"||c&&c.kind!=="relation"?(this.error(d.id,"Operands require relations.","exact-23"),null):!s||!c||s.kind!=="relation"||c.kind!=="relation"?null:d.tag==="product"?this.resultSchema(d.id,[...s.columns,...c.columns]):d.tag==="join"?s.columns.at(-1)!==c.columns[0]?(this.error(d.id,"Join nominal endpoint mismatch.","exact-24",[s.columns.at(-1)],[c.columns[0]]),null):this.resultSchema(d.id,[...s.columns.slice(0,-1),...c.columns.slice(1)]):(ff(s,c)||this.error(d.id,"Ordered nominal schemas must be identical.","exact-25",s.columns,c.columns),d.tag==="equal"||d.tag==="subset"?an:s)}resultSchema(d,f){return _d(this.module,f)?{kind:"relation",columns:f}:(this.error(d,"Result schema must be nonempty and width<=8.","exact-26",["width1..8","declared-columns"],f),null)}fieldOrderFacts(){const d=[];for(const f of this.module.fields)d.push(f.id,f.ownerSignatureId);return d}scopeFacts(d){const f=[];for(const u of d)f.push(u.id,...u.columns);return f}cycleFacts(d,f){const u=[];for(const[s,c]of d)for(const v of c){const p=s===f||this.reaches(d,f,s,new Set),A=v===f||this.reaches(d,v,f,new Set);p&&A&&u.push(JSON.stringify([s,v]))}return u.sort()}commands(){for(const d of this.module.commands){let f=!1;for(const u of this.module.predicates)d.tag==="run"&&d.targetId===u.id&&u.parameters.length===0&&(f=!0);for(const u of this.module.assertions)d.tag==="check"&&d.targetId===u.id&&(f=!0);f||this.error(d.id,"run needs nullary predicate; check needs assertion.","exact-27",[],[d.tag,d.targetId]),(d.uniformScope<1||d.uniformScope>5||!Number.isInteger(d.uniformScope)||d.bitwidth!==4||d.maxseq!==3)&&this.error(d.id,"Invalid bounded command options.","exact-28",[],[String(d.uniformScope),String(d.bitwidth),String(d.maxseq)])}}dependencies(){const d=new Map;for(const f of this.module.predicates){const u=new Set;for(const s of this.collect(f.bodyId)){const c=this.index.get(s);(c==null?void 0:c.tag)==="predicate_call"&&u.add(c.predicateId)}d.set(f.id,u)}for(const f of this.module.predicates)this.reaches(d,f.id,f.id,new Set)&&this.error(f.id,"Recursive predicate dependency.","exact-29",[],this.cycleFacts(d,f.id))}collect(d){const f=new Set,u=[d];for(;u.length;){const s=u.pop();if(f.has(s))continue;f.add(s);const c=this.index.get(s);c&&u.push(...Be(c))}return f}reaches(d,f,u,s){if(s.has(f))return!1;s.add(f);for(const c of d.get(f)??[])if(c===u||this.reaches(d,c,u,s))return!0;return!1}}const vf=["not","some_test","no_test","one_test","lone_test","transpose"],Kc=["and","or","implies","iff","equal","subset","union","intersection","difference","join","product"],Jc=["all_quant","some_quant"],an={kind:"formula"};function it(){return`draft:${crypto.randomUUID()}`}function kc(){return{version:1,signatures:[],fields:[],predicates:[],facts:[],assertions:[],commands:[],nodes:[]}}function Be(r){return"operandId"in r?[r.operandId]:"leftId"in r?[r.leftId,r.rightId]:"bodyId"in r?[r.bodyId]:"arguments"in r?r.arguments:[]}function ff(r,d){return!!r&&!!d&&r.kind===d.kind&&(r.kind==="formula"||d.kind==="relation"&&Yg(r.columns,d.columns))}function Yg(r,d){if(r.length!==d.length)return!1;for(let f=0;f<r.length;f++)if(r[f]!==d[f])return!1;return!0}function He(r){const d=new Map;for(const f of r.nodes)d.set(f.id,f);return d}function Wt(r,d){const f=He(r),u=new Set,s=[d];for(;s.length;){const c=s.pop();if(u.has(c))continue;u.add(c);const v=f.get(c);v&&s.push(...Be(v))}return u}function $a(r,d){if(!d)return"unresolved relation constraint";if(d.kind==="formula")return"formula";const f=[];for(const u of d.columns){let s=u;for(const c of r.signatures)c.id===u&&(s=c.name);f.push(s)}return f.join(" → ")}function _d(r,d){if(d.length<1||d.length>8)return!1;const f=new Set;for(const u of r.signatures)f.add(u.id);for(const u of d)if(!f.has(u))return!1;return!0}function Gg(r,d){for(const f of r)if(f.id===d)return f}function uf(r,d,f){r.length<64&&r.push({nodeId:d,message:f})}function Wa(r,d=[],f){return new qg(r,d,f).check()}const qn="/api/v1/documents";function Dd(r){const d=JSON.stringify(r);if(new TextEncoder().encode(d).length>262144)throw new Error("Document request exceeds262144 UTF8 bytes.");return d}function $c(r){for(let d=0;d<r.length;d++){const f=r.charCodeAt(d);if(f>=55296&&f<=56319){const u=r.charCodeAt(++d);if(!(u>=56320&&u<=57343))return!1}else if(f>=56320&&f<=57343)return!1}return!0}async function lf(r){if(!$c(r))throw new Error("Unpaired UTF16 surrogate.");const d=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(r)),f=[];for(const u of new Uint8Array(d))f.push(u.toString(16).padStart(2,"0"));return f.join("")}async function er(r,d,f,u){const s=await fetch(d,{method:f===void 0?"GET":"POST",body:f,signal:u,headers:{Authorization:`Bearer ${r}`,"Content-Type":"application/json"}}),c=await s.json();if(!c||typeof c!="object"||!("protocol"in c)||c.protocol!==1||!("status"in c)||!("data"in c))throw new Error(`Unavailable document protocol (${s.status}); retry exact pending request.`);return c}function Lg(r){return er(r,qn)}function Wc(r,d,f){const u=f===void 0?"":`?revision=${f}`;return er(r,`${qn}/${encodeURIComponent(d)}${u}`)}function Qg(r,d,f,u,s){const c=crypto.randomUUID();return{route:`${qn}/${encodeURIComponent(r)}/commit`,method:"POST",key:c,body:Dd({idempotencyKey:c,expectedRevision:f,candidate:d}),draftId:u,epoch:s}}function Xg(r,d,f,u,s,c){const v=crypto.randomUUID(),p=Dd({idempotencyKey:v,expectedRevision:d,targetRevision:f,direction:u});return{route:`${qn}/${encodeURIComponent(r)}/history-copy`,method:"POST",key:v,body:p,draftId:s,epoch:c}}function Zg(r,d){return er(r,d.route,d.body)}function Vg(r,d,f,u){return er(r,`${qn}/${encodeURIComponent(d)}/validate`,f,u)}function Fc(r){const d=new Map;for(const f of[...r.predicates,...r.facts,...r.assertions])d.set(f.bodyId,{ownerId:f.id,role:"body"});for(const f of r.nodes)if("operandId"in f&&d.set(f.operandId,{ownerId:f.id,role:"operand"}),"leftId"in f&&(d.set(f.leftId,{ownerId:f.id,role:"left"}),d.set(f.rightId,{ownerId:f.id,role:"right"})),"bodyId"in f&&d.set(f.bodyId,{ownerId:f.id,role:"body"}),"arguments"in f)for(let u=0;u<f.arguments.length;u++)d.set(f.arguments[u],{ownerId:f.id,role:"argument",index:u});return d}function jd(r){return JSON.stringify([r.ownerId,r.role,r.index??null])}function Kg(r,d){for(const f of r)if(jd(f.slot)===jd(d.slot)&&ff(f.expected,d.expected))return r;return[...r,d]}function sf(r,d,f){const u=Fc(r).get(d);if(!u)return f;for(const s of r.nodes)if(s.id===d&&s.tag==="hole"&&s.expected)return Kg(f,{slot:u,expected:s.expected});return f}function tr(r,d){const f=new Set,u=[];for(const s of Fc(r).values())f.add(jd(s));for(const s of d)f.has(jd(s.slot))&&u.push(s);return u.length===d.length?d:u}function Jg(r,d){if(r.kind==="formula")return r;const f=[];for(const u of r.columns)f.push(d.get(u)??u);return{kind:"relation",columns:f}}function Pc(r,d){const f=[];for(const u of r)f.push({slot:{...u.slot,ownerId:d.get(u.slot.ownerId)??u.slot.ownerId},expected:Jg(u.expected,d)});return f}function kg(r,d,f,u){const s=Wt(r,d),c=[];for(const v of f)s.has(v.slot.ownerId)&&c.push(v);return[...f,...Pc(c,u)]}function of(r,d,f){for(const u of r.obligationHistory)if(u.documentId===d&&u.revision===f)return u.obligations;return[]}function n4(r,d,f){return{...r,pendingObligations:{key:d.key,obligations:f}}}function $g(r,d,f){const u=r.pendingObligations;if((u==null?void 0:u.key)!==d.key)return r;const s=new Map(Object.entries(f.idRemapping)),c=f.artifact.module,v=c?tr(c,Pc(u.obligations,s)):[],p=[];for(const A of r.obligationHistory)(A.documentId!==f.documentId||A.revision!==f.revision)&&p.push(A);return v.length&&p.push({documentId:f.documentId,revision:f.revision,obligations:v}),{...r,obligationHistory:p,pendingObligations:null}}function e4(){return{slotObligations:[],obligationHistory:[],pendingObligations:null,accepted:null,draftId:crypto.randomUUID(),epoch:0,contentGeneration:0,baseRevision:0,module:kc(),source:"",mode:"BLOCK_SUPPORTED",selected:null,dirty:!1,copies:[],clipboard:null,validation:null,validationBody:null,preview:null,historicalPreview:null,pending:null,rejectionDiagnostics:[],notice:"Create or open a model.",historyCursor:null}}function Ue(r,d){return{...r,selected:d,epoch:r.epoch+1,validation:null,validationBody:null,historicalPreview:r.preview??r.historicalPreview,preview:null,rejectionDiagnostics:[]}}function t4(r,d,f=r.selected,u=r.copies,s=tr(d,r.slotObligations)){return{...Ue(r,f),module:d,copies:u,slotObligations:s,mode:"BLOCK_SUPPORTED",contentGeneration:r.contentGeneration+1,dirty:!0,clipboard:null}}function Wg(r,d){return{...Ue(r,r.selected),source:d,mode:"SOURCE",dirty:!0,contentGeneration:r.contentGeneration+1,clipboard:null}}function a4(r,d){var u;if(((u=r.accepted)==null?void 0:u.documentId)===d.documentId&&d.headRevision<r.accepted.headRevision)return{...r,notice:"Ignored an older server head response."};const f=d.artifact.module??kc();return{...e4(),obligationHistory:r.obligationHistory,slotObligations:tr(f,of(r,d.documentId,d.revision)),accepted:d,draftId:crypto.randomUUID(),epoch:r.epoch+1,contentGeneration:r.contentGeneration+1,baseRevision:d.headRevision,module:f,source:d.artifact.source,mode:d.artifact.module?"BLOCK_SUPPORTED":"SOURCE",notice:of(r,d.documentId,d.revision).length?"Model opened with retained in-tab constraints.":"Model opened; no explicit constraint provenance is retained for this version in this tab.",historyCursor:d.revision}}function Cd(r){var f;if(r.mode==="SOURCE"){if(!$c(r.source)||new TextEncoder().encode(r.source).length>32768)throw new Error("Source must be strict Unicode and at most32768 UTF8 bytes.");return{mode:"SOURCE",source:r.source}}const d=Wa(r.module,r.slotObligations);if(!d.complete)throw new Error(((f=d.diagnostics[0])==null?void 0:f.message)??"Fill every unresolved hole before validating or saving.");return{mode:"BLOCK_SUPPORTED",module:r.module,presentationCopies:r.copies}}function Fg(r,d,f,u){return r.validationBody!==d||u.requestHash!==f||u.draftId!==r.draftId||u.draftEpoch!==r.epoch||u.baseRevision!==r.baseRevision?r:{...r,validation:u,preview:u.proposedSource,notice:"Draft checked. Your saved version is unchanged."}}function Pg(r,d,f){var A,S,N;if(f.status!=="COMMITTED")return{...r,pendingObligations:Hc(f.status)?r.pendingObligations:null,rejectionDiagnostics:"diagnostics"in f.data?f.data.diagnostics:[],pending:Hc(f.status)?d:null,notice:`${f.status}: draft retained; accepted state unchanged or awaiting recovery.`};if(!("artifact"in f.data))return{...r,notice:"Invalid success envelope; exact pending bytes retained for recovery."};const u=f.data,s=((A=r.accepted)==null?void 0:A.headRevision)??-1;if(u.revision<s)return{...r,pending:null,pendingObligations:((S=r.pendingObligations)==null?void 0:S.key)===d.key?null:r.pendingObligations,notice:"Historical receipt recovered; refresh current head."};const c=$g(r,d,u),v=d.route.endsWith("/history-copy")&&!((N=r.pendingObligations)!=null&&N.obligations.length)?"Saved this version; explicit constraint provenance was unavailable for the restored version in this tab.":"Saved this version.",p={documentId:u.documentId,revision:u.revision,headRevision:u.revision,artifact:u.artifact,provenance:u.provenance};return r.draftId===d.draftId&&r.epoch===d.epoch?{...a4(c,p),historyCursor:d.route.endsWith("/history-copy")?r.historyCursor:u.revision,pending:null,notice:v}:{...c,accepted:p,pending:null,validation:null,preview:null,notice:"Server commit recorded; newer draft preserved. Rebase explicitly before saving."}}function Hc(r){return["UNKNOWN_COMMIT_OUTCOME","IN_PROGRESS","UNAVAILABLE"].includes(r)}function nI(r){var f;const d=r.clipboard;return!!d&&d.documentId===((f=r.accepted)==null?void 0:f.documentId)&&d.baseRevision===r.baseRevision&&d.draftId===r.draftId&&d.contentGeneration===r.contentGeneration}function Ne(r=null){return{tag:"hole",id:it(),expected:r}}function eI(r,d,f,u="variable"){const s=it();if(r==="signature_ref"||r==="field_ref"||r==="variable_ref")return[{tag:r,id:s,targetId:d}];if(r==="predicate_call"){const A=[];for(const N of f.predicates)if(N.id===d)for(const U of N.parameters)A.push(Ne({kind:"relation",columns:U.columns}));const S=[];for(const N of A)S.push(N.id);return[{tag:r,id:s,predicateId:d,arguments:S},...A]}if(r==="all_quant"||r==="some_quant"){const A=Ne(an);return[{tag:r,id:s,binder:{id:it(),name:u,signatureId:d},bodyId:A.id},A]}if(vf.includes(r)){const A=Ne(r==="not"?an:null);return[{tag:r,id:s,operandId:A.id},A]}const c=["and","or","implies","iff"].includes(r),v=Ne(c?an:null),p=Ne(c?an:null);return[{tag:r,id:s,leftId:v.id,rightId:p.id},v,p]}function tI(r,d,f){if("operandId"in r)return{...r,operandId:r.operandId===d?f:r.operandId};if("leftId"in r)return{...r,leftId:r.leftId===d?f:r.leftId,rightId:r.rightId===d?f:r.rightId};if("bodyId"in r)return{...r,bodyId:r.bodyId===d?f:r.bodyId};if("arguments"in r){const u=[];for(const s of r.arguments)u.push(s===d?f:s);return{...r,arguments:u}}return r}function cf(r,d,f){const u=Wt(r,d),s=f[0].id,c=[];for(const S of r.nodes)u.has(S.id)||c.push(tI(S,d,s));c.push(...f);const v=[];for(const S of r.predicates)v.push({...S,bodyId:S.bodyId===d?s:S.bodyId});const p=[];for(const S of r.facts)p.push({...S,bodyId:S.bodyId===d?s:S.bodyId});const A=[];for(const S of r.assertions)A.push({...S,bodyId:S.bodyId===d?s:S.bodyId});return{...r,nodes:c,predicates:v,facts:p,assertions:A}}function r4(r,d,f,u){const s=sf(r,d,u),c=cf(r,d,f);return{module:c,slotObligations:tr(c,s)}}function mf(r,d,f=[],u=f,s){const c=Wa(r,f,s),v=Wa(d,u,s),p=c.resourceFailure??v.resourceFailure;if(p)return`${p.code}: Draft constraint analysis did not complete; edit rejected.`;for(const[A,S]of v.violations)if(!c.violations.has(A))return S.message;return null}function Ce(r,d){return d.get(r)??r}function aI(r,d){const f=Ce(r.id,d);if("targetId"in r)return{...r,id:f,targetId:Ce(r.targetId,d)};if("binder"in r)return{...r,id:f,binder:{...r.binder,id:Ce(r.binder.id,d),name:`${r.binder.name.slice(0,48)}_${f.slice(-8)}`},bodyId:Ce(r.bodyId,d)};if("operandId"in r)return{...r,id:f,operandId:Ce(r.operandId,d)};if("leftId"in r)return{...r,id:f,leftId:Ce(r.leftId,d),rightId:Ce(r.rightId,d)};if("arguments"in r){const u=[];for(const s of r.arguments)u.push(Ce(s,d));return{...r,id:f,arguments:u}}return{...r,id:f}}function rI(r,d){const f=Wt(r,d),u=He(r),s=new Map,c=new Map,v=[];for(const p of f){s.set(p,it()),c.set(p,s.get(p));const A=u.get(p);A&&"binder"in A&&s.set(A.binder.id,it())}for(const p of f){const A=u.get(p);A&&v.push(aI(A,s))}return{nodes:v,remap:s,expressionMap:c}}function dI(r,d){const f=[...r];for(const[u,s]of d){let c=u.startsWith("server:")?u:null;for(const v of r)v.targetNodeId===u&&(c=v.sourceNodeId);c&&f.push({sourceNodeId:c,targetNodeId:s})}return f}function Nd(r,d){const f=new Set;for(const s of d.nodes)f.add(s.id);const u=[];for(const s of r)f.has(s.targetNodeId)&&u.push(s);return u}function d4(r,d,f,u,s=[]){const c={module:r,copies:u,selected:f,slotObligations:s};if(Wt(r,d.nodeId).has(f))return{...c,error:"Cannot paste into the source or its descendant."};const v=He(r);if(!v.has(f)||!v.has(d.nodeId))return{...c,error:"Clipboard source/destination is unavailable."};let p=r,A,S=u,N=sf(r,f,s);if(d.cut){const y0=[];for(const T0 of Wt(r,d.nodeId)){const Q0=v.get(T0);Q0&&y0.push(Q0)}A=y0,p=cf(r,d.nodeId,[Ne()]),N=sf(r,d.nodeId,N)}else{const y0=rI(r,d.nodeId);A=y0.nodes,S=dI(u,y0.expressionMap),N=kg(r,d.nodeId,N,y0.remap)}const U=cf(p,f,A),Y=tr(U,N),u0=mf(r,U,s,Y);return u0?{...c,error:u0}:{module:U,copies:Nd(S,U),selected:A[0].id,slotObligations:Y,error:null}}function lI(r,d){const f=new Map;for(const[u,s]of d.destinations){const c=[...s.descriptions];s.exact&&c.unshift($a(r,{kind:"relation",columns:s.exact})),f.set(u,c.length?c.join("; "):s.sort)}return f}function hf(r,d){r.current.current=d,r.set(d)}function _0(r,d){hf(r,{...r.current.current,document:d})}function L0(r,d){_0(r,{...r.current.current.document,notice:d})}async function Od(r){try{const d=await Lg(r.token);d.data.documents?hf(r,{...r.current.current,documents:d.data.documents}):L0(r,d.status)}catch(d){L0(r,Ft(d))}}function Ft(r){return r instanceof Error?r.message:"Request unavailable; accepted commit outcome may require recovery."}async function l4(r,d){const f=Ue(r.current.current.document,null);_0(r,f);try{const u=await Wc(r.token,d);if(r.current.current.document.epoch!==f.epoch)return;u.data.artifact?_0(r,a4(r.current.current.document,u.data)):L0(r,u.status)}catch(u){L0(r,Ft(u))}}async function iI(r,d){const f=r.current.current.document;if(f.pending){L0(r,"Recover the pending request before creating another document.");return}const u=crypto.randomUUID(),s={route:qn,method:"POST",body:JSON.stringify({idempotencyKey:u,title:d}),key:u,draftId:f.draftId,epoch:f.epoch};_0(r,{...f,pending:s,notice:"Creating document; exact request retained."}),await Md(r,s)}async function Md(r,d){try{const f=await Zg(r.token,d),u=r.current.current.document;if(u.pending&&u.pending.key!==d.key||d.route!==qn&&u.accepted&&!d.route.includes(`/${encodeURIComponent(u.accepted.documentId)}/`))return;if(d.route===qn&&"documentId"in f.data&&f.data.documentId){_0(r,{...r.current.current.document,pending:null}),await Od(r),await l4(r,f.data.documentId);return}_0(r,Pg(r.current.current.document,d,f)),f.status==="COMMITTED"&&await Od(r)}catch(f){L0(r,`${Ft(f)} Exact pending bytes retained; use Retry.`)}}async function fI(r){const d=r.current.current.document;if(d.accepted){if(d.pending){L0(r,"Retry/recover the existing request first.");return}try{const f=Qg(d.accepted.documentId,Cd(d),d.baseRevision,d.draftId,d.epoch),u=n4(d,f,d.mode==="BLOCK_SUPPORTED"?d.slotObligations:[]);_0(r,{...u,pending:f,notice:"Saving candidate; acceptance awaits server commit receipt."}),await Md(r,f)}catch(f){L0(r,Ft(f))}}}async function uI(r,d){const f=r.current.current.document;if(f.accepted)try{const u=Dd({draftId:f.draftId,draftEpoch:f.epoch,baseRevision:f.baseRevision,candidate:Cd(f)});_0(r,{...f,validationBody:u,notice:"Validating advisory draft…"});const s=await lf(u),c=await Vg(r.token,f.accepted.documentId,u,d);if(d!=null&&d.aborted)return;if(!c.data||typeof c.data.requestHash!="string"){r.current.current.document.epoch===f.epoch&&L0(r,c.status);return}if(c.data.proposedSource!==null&&await lf(c.data.proposedSource)!==c.data.proposedSourceHash)throw new Error("Server projection hash mismatch.");if(f.mode==="SOURCE"&&c.data.sourceHash!==await lf(f.source))throw new Error("Source validation identity mismatch.");d!=null&&d.aborted||_0(r,Fg(r.current.current.document,u,s,c.data))}catch(u){!(d!=null&&d.aborted)&&r.current.current.document.epoch===f.epoch&&L0(r,Ft(u))}}function i4(r,d){_0(r,Ue(r.current.current.document,d))}function yf(r,d){const f=r.current.current.document,u=t4(f,d,f.selected,Nd(f.copies,d));_0(r,{...u,notice:mg(f.module,d)??"Declaration draft changed; dependencies rechecked before acceptance."})}function sI(r,d){_0(r,Wg(r.current.current.document,d))}function Ud(r,d,f,u){if(f.error){_0(r,{...d,notice:f.error});return}const s={...t4(d,f.module,f.selected,f.copies,f.slotObligations),notice:u};_0(r,s),hI(r,s,f.selected)}function oI(r,d,f,u,s){const c=r.current.current.document,v=eI(d,f,c.module,u),p=r4(c.module,s,v,c.slotObligations),A=mf(c.module,p.module,c.slotObligations,p.slotObligations);Ud(r,c,{...p,copies:Nd(c.copies,p.module),selected:v[0].id,error:A},"Inserted draft block; server acceptance pending.")}function f4(r,d,f){return r.accepted?{documentId:r.accepted.documentId,baseRevision:r.baseRevision,draftId:r.draftId,contentGeneration:r.contentGeneration,nodeId:d,cut:f}:null}function cI(r,d){const f=r.current.current.document,u=f.selected?f4(f,f.selected,d):null;u&&_0(r,{...f,clipboard:u,notice:`${d?"Cut":"Copied"} subtree. Select a destination then Paste.`})}function gI(r){const d=r.current.current.document;if(!nI(d)||!d.clipboard||!d.selected){L0(r,"Clipboard stale or missing. Copy/Cut current content again.");return}const f=d4(d.module,d.clipboard,d.selected,d.copies,d.slotObligations);Ud(r,d,f,"Draft paste completed; scope and nominal schemas rechecked.")}function II(r,d,f,u){const s=r.current.current.document,c=f4(s,d,!u);if(!c||!He(s.module).has(d)){_0(r,{...s,notice:"Foreign or stale dragged source."});return}const v=d4(s.module,c,f,s.copies,s.slotObligations);Ud(r,s,v,"Draft drop completed; scope and nominal schemas rechecked.")}function vI(r){const d=r.current.current.document;if(!d.selected)return;const f=Ne(),u=r4(d.module,d.selected,[f],d.slotObligations),s=mf(d.module,u.module,d.slotObligations,u.slotObligations);Ud(r,d,{...u,copies:Nd(d.copies,u.module),selected:f.id,error:s},"Deleted draft subtree; comments become visible orphans on block commit.")}function mI(r,d,f){var u;r.current.current.document===d&&((u=document.getElementById(`block-${f}`))==null||u.focus())}function hI(r,d,f){window.setTimeout(mI.bind(null,r,d,f),0)}async function u4(r,d,f){const u=r.current.current.document;if(!(!u.accepted||!Number.isSafeInteger(d)||d<0)){_0(r,Ue(u,u.selected));try{const s=await Wc(r.token,u.accepted.documentId,d);s.data.artifact?hf(r,{...r.current.current,target:d,direction:f,history:s.data}):L0(r,s.status)}catch(s){L0(r,Ft(s))}}}async function yI(r){const d=r.current.current,f=d.document,u=d.history;if(!u||!f.accepted||f.pending)return;if(u.documentId!==f.accepted.documentId){L0(r,"Historical target belongs to a different document.");return}const s=Xg(f.accepted.documentId,f.accepted.headRevision,u.revision,d.direction,f.draftId,f.epoch),c=of(f,u.documentId,u.revision),v=n4(f,s,c),p=c.length?"Appending historical content with retained in-tab constraints.":"Appending historical content; explicit constraint provenance is unavailable for this version in this tab.";_0(r,{...v,pending:s,historyCursor:u.revision,notice:p}),await Md(r,s)}function pI(r){const d=r.current.current.document;_0(r,{...d,clipboard:null,notice:"Pending clipboard interaction cancelled."})}function rt(r,d){const f=[];for(const u of r)f.push(u.id===d.id?d:u);return f}function bI(r,d){switch(d.tag){case"signature":return{...r,signatures:rt(r.signatures,d)};case"field":return{...r,fields:Xc(r,rt(r.fields,d))};case"predicate":return{...r,predicates:rt(r.predicates,d)};case"fact":return{...r,facts:rt(r.facts,d)};case"assertion":return{...r,assertions:rt(r.assertions,d)};default:return{...r,commands:rt(r.commands,d)}}}function SI(r,d){const f="bodyId"in d?Wt(r,d.bodyId):new Set,u=[],s=[],c=[],v=[],p=[],A=[],S=[];for(const N of r.nodes)f.has(N.id)||u.push(N);for(const N of r.signatures)N.id!==d.id&&s.push(N);for(const N of r.fields)N.id!==d.id&&c.push(N);for(const N of r.predicates)N.id!==d.id&&v.push(N);for(const N of r.facts)N.id!==d.id&&p.push(N);for(const N of r.assertions)N.id!==d.id&&A.push(N);for(const N of r.commands)N.id!==d.id&&S.push(N);return{...r,signatures:s,fields:c,predicates:v,facts:p,assertions:A,commands:S,nodes:u}}function _I(r,d){var p;const f=it(),u=`${d}_${f.slice(-8).replaceAll("-","")}`,s=((p=r.signatures[0])==null?void 0:p.id)??"";if(d==="signature")return{...r,signatures:[...r.signatures,{tag:d,id:f,name:u,multiplicity:"set"}]};if(d==="field")return{...r,fields:Xc(r,[...r.fields,{tag:d,id:f,name:u,ownerSignatureId:s,rangeColumns:[s],multiplicity:"set"}])};if(d==="run"||d==="check")return{...r,commands:[...r.commands,{tag:d,id:f,targetId:"",uniformScope:3,bitwidth:4,maxseq:3}]};const c=Ne(an),v=[...r.nodes,c];return d==="predicate"?{...r,nodes:v,predicates:[...r.predicates,{tag:d,id:f,name:u,parameters:[],bodyId:c.id}]}:d==="fact"?{...r,nodes:v,facts:[...r.facts,{tag:d,id:f,name:u,bodyId:c.id}]}:{...r,nodes:v,assertions:[...r.assertions,{tag:d,id:f,name:u,bodyId:c.id}]}}function xI(r,d){const f=it(),u={tag:"parameter",id:f,name:`param_${f.slice(-8)}`,columns:[d]};return{...r,parameters:[...r.parameters,u]}}function s4(r,d){r(d.target.value)}function ar(r){return I.jsxs("label",{children:[r.label,I.jsx("input",{value:r.value,onChange:s4.bind(null,r.onChange)})]})}function de(r){const d=[];for(const f of r.options)d.push(I.jsx("option",{value:f.id,children:f.label},f.id));return I.jsxs("label",{children:[r.label,I.jsxs("select",{value:r.value,onChange:s4.bind(null,r.onChange),children:[I.jsx("option",{value:"",children:"Choose explicitly"}),d]})]})}function o4(r){const d=[];for(const f of r.signatures)d.push({id:f.id,label:f.name});return d}function wc(r){function d(u){["set","one","lone","some"].includes(u)&&r.onChange(u)}const f=[];for(const u of["set","one","lone","some"])f.push({id:u,label:u});return I.jsx(de,{label:"Multiplicity",value:r.value,options:f,onChange:d})}function c4(r){function d(c,v){const p=[...r.columns];p[c]=v,r.onChange(p)}function f(){r.onChange([...r.columns,""])}function u(){r.onChange(r.columns.slice(0,-1))}const s=[];for(let c=0;c<r.columns.length;c++)s.push(I.jsx(de,{label:`Column ${c+1}`,value:r.columns[c],options:o4(r.module),onChange:d.bind(null,c)},c));return I.jsxs("fieldset",{children:[I.jsx("legend",{children:"Ordered nominal schema (set-valued)"}),s,I.jsx("button",{type:"button",disabled:r.columns.length>=8,onClick:f,children:"Add column"}),I.jsx("button",{type:"button",disabled:r.columns.length<=1,onClick:u,children:"Remove last column"})]})}function AI(r){function d(s){r.onChange(_I(r.module,s))}const f=[],u=[];for(const s of["signature","field","predicate","fact","assertion","run","check"])f.push(I.jsxs("button",{onClick:d.bind(null,s),children:["Add ",s]},s));for(const s of[...r.module.signatures,...r.module.fields,...r.module.predicates,...r.module.facts,...r.module.assertions,...r.module.commands])u.push(I.jsx(EI,{...r,item:s},s.id));return I.jsxs("section",{"aria-label":"Declaration editors",children:[I.jsx("h2",{children:"Declarations"}),I.jsx("div",{className:"document-actions",children:f}),u]})}function EI(r){function d(c){r.onChange(bI(r.module,c))}function f(c){"name"in r.item&&d({...r.item,name:c})}function u(){r.onChange(SI(r.module,r.item))}const s=r.item;return I.jsxs("fieldset",{children:[I.jsx("legend",{children:s.tag}),"name"in s&&I.jsx(ar,{label:"Name",value:s.name,onChange:f}),I.jsx(TI,{...r,update:d}),"bodyId"in s&&I.jsxs("button",{onClick:r.onSelect.bind(null,s.bodyId),children:["Select ",s.tag," body"]}),I.jsxs("button",{onClick:u,children:["Delete ",s.tag]}),I.jsxs("details",{children:[I.jsx("summary",{children:"Declaration identity"}),I.jsx("small",{children:s.id})]})]})}function TI(r){const d=r.item;function f(c){(d.tag==="signature"||d.tag==="field")&&r.update({...d,multiplicity:c})}function u(c){d.tag==="field"&&r.update({...d,ownerSignatureId:c})}function s(c){d.tag==="field"&&r.update({...d,rangeColumns:c})}return d.tag==="signature"?I.jsx(wc,{value:d.multiplicity,onChange:f}):d.tag==="field"?I.jsxs(I.Fragment,{children:[I.jsx(de,{label:"Owner signature",value:d.ownerSignatureId,options:o4(r.module),onChange:u}),I.jsx(c4,{module:r.module,columns:d.rangeColumns,onChange:s}),I.jsx(wc,{value:d.multiplicity,onChange:f})]}):d.tag==="predicate"?I.jsx(jI,{module:r.module,predicate:d,onChange:r.update}):d.tag==="run"||d.tag==="check"?I.jsx(zI,{item:d,module:r.module,onChange:r.update}):null}function jI(r){function d(){var c;r.onChange(xI(r.predicate,((c=r.module.signatures[0])==null?void 0:c.id)??""))}function f(c){r.onChange({...r.predicate,parameters:rt(r.predicate.parameters,c)})}function u(c){const v=[];for(const p of r.predicate.parameters)p.id!==c&&v.push(p);r.onChange({...r.predicate,parameters:v})}const s=[];for(const c of r.predicate.parameters)s.push(I.jsx(OI,{module:r.module,parameter:c,onChange:f,onDelete:u.bind(null,c.id)},c.id));return I.jsxs("fieldset",{children:[I.jsx("legend",{children:"Ordered set-valued parameters"}),s,I.jsx("button",{disabled:r.predicate.parameters.length>=16,onClick:d,children:"Add parameter"})]})}function OI(r){function d(u){r.onChange({...r.parameter,name:u})}function f(u){r.onChange({...r.parameter,columns:u})}return I.jsxs("fieldset",{children:[I.jsx("legend",{children:"Parameter"}),I.jsx(ar,{label:"Parameter name",value:r.parameter.name,onChange:d}),I.jsx(c4,{module:r.module,columns:r.parameter.columns,onChange:f}),I.jsx("button",{onClick:r.onDelete,children:"Delete parameter"})]})}function zI(r){function d(c){r.onChange({...r.item,targetId:c})}function f(c){r.onChange({...r.item,uniformScope:Number(c)})}const u=[],s=[];if(r.item.tag==="run")for(const c of r.module.predicates)c.parameters.length===0&&u.push({id:c.id,label:c.name});else for(const c of r.module.assertions)u.push({id:c.id,label:c.name});for(let c=1;c<=5;c++)s.push({id:String(c),label:String(c)});return I.jsxs(I.Fragment,{children:[I.jsx(de,{label:"Command target",value:r.item.targetId,options:u,onChange:d}),I.jsx(de,{label:"Uniform scope",value:String(r.item.uniformScope),options:s,onChange:f}),I.jsx("p",{children:"Bitwidth4 · maxseq3"})]})}function DI(r){const[d,f]=l0.useState(""),[u,s]=l0.useState("variable"),c=Wa(r.module,r.slotObligations),v=lI(r.module,c),p=He(r.module);function A(N){r.selected?r.onInsert(N,d,u,r.selected):r.onNotice("Select a body or child slot first.")}function S(N,U){U.preventDefault(),U.stopPropagation();const Y=U.dataTransfer.getData("text/plain");if(Y.startsWith("node:")){YI(r,Y.slice(5),N,U.ctrlKey||U.metaKey);return}["signature_ref","field_ref","variable_ref","predicate_call",...vf,...Kc,...Jc].includes(Y)?r.onInsert(Y,d,u,N):r.onNotice("Unsupported drag payload.")}return I.jsxs("section",{"aria-label":"Typed block editor",className:"document-blocks",onKeyDown:CI.bind(null,r),children:[I.jsx("h2",{children:"Typed blocks"}),I.jsx(RI,{constraints:v,module:r.module,selected:r.selected,checked:c,target:d,name:u,onTarget:f,onName:s,onInsert:A}),I.jsx(NI,{...r}),I.jsx(BI,{...r,constraints:v,index:p,checked:c,onDrop:S})]})}function CI(r,d){const f=d.target;if(["INPUT","TEXTAREA","SELECT"].includes(f.tagName)||f.isContentEditable)return;const u=d.ctrlKey||d.metaKey,s=d.key.toLowerCase();u&&["c","x","v"].includes(s)?(d.preventDefault(),s==="v"?r.onPaste():r.onClipboard(s==="x")):d.key==="Delete"?(d.preventDefault(),r.onDelete()):d.key==="Escape"&&r.onCancel()}function NI(r){return I.jsxs("div",{className:"document-actions",children:[I.jsx("button",{disabled:!r.selected,onClick:r.onClipboard.bind(null,!1),children:"Copy (Ctrl/Cmd+C)"}),I.jsx("button",{disabled:!r.selected,onClick:r.onClipboard.bind(null,!0),children:"Cut (Ctrl/Cmd+X)"}),I.jsx("button",{onClick:r.onPaste,children:"Paste (Ctrl/Cmd+V)"}),I.jsx("button",{disabled:!r.selected,onClick:r.onDelete,children:"Delete selected"}),I.jsx("p",{children:"Drag an existing block to move; Ctrl/Cmd-drag copies. Selection preserves clipboard content identity."})]})}function MI(r){const d=[];for(const f of r.module.signatures)d.push({id:f.id,label:`Signature ${f.name}`});for(const f of r.module.fields)d.push({id:f.id,label:`Field ${f.name}`});for(const f of r.module.predicates)d.push({id:f.id,label:`Predicate ${f.name}`});for(const f of r.checked.scopes.get(r.selected??"")??[])d.push({id:f.id,label:`In-scope variable ${f.name}`});return d}function UI(r,d){d.dataTransfer.setData("text/plain",r)}function RI(r){const d=[],f=["signature_ref","field_ref","variable_ref","predicate_call",...vf,...Kc,...Jc];for(const s of f)d.push(I.jsx("button",{draggable:!0,onDragStart:UI.bind(null,s),onClick:r.onInsert.bind(null,s),"data-operator":s,children:GI(s)},s));const u=[];for(const s of r.checked.scopes.get(r.selected??"")??[])u.push(I.jsxs("li",{children:[s.name,": ",$a(r.module,{kind:"relation",columns:s.columns})]},s.id));return I.jsxs("fieldset",{children:[I.jsx("legend",{children:"Complete expression palette"}),I.jsx(de,{label:"Declaration or in-scope variable",value:r.target,options:MI(r),onChange:r.onTarget}),I.jsx(ar,{label:"Quantifier variable name",value:r.name,onChange:r.onName}),I.jsxs("p",{children:["Expected destination: ",r.selected?r.constraints.get(r.selected)??"unresolved constraint":"select a declaration body"]}),I.jsx("ul",{"aria-label":"In-scope variables",children:u}),I.jsx("div",{className:"document-actions",children:d})]})}function BI(r){const d=[];for(const f of[...r.module.predicates,...r.module.facts,...r.module.assertions])d.push(I.jsxs("div",{children:[I.jsxs("h3",{children:[f.tag," ",f.name]}),I.jsx(g4,{...r,id:f.bodyId,depth:0})]},f.id));return I.jsx("div",{"aria-label":"Owned expression forest",children:d.length?d:I.jsx("p",{children:"Add a predicate, fact or assertion to create a formula root."})})}function HI(r){r.preventDefault(),r.stopPropagation()}function wI(r,d,f){f.stopPropagation(),f.dataTransfer.setData("text/plain",`node:${JSON.stringify({nodeId:r,snapshot:d})}`)}function qI(r,d,f){const u=f.types.get(d),s=f.facts.get(d);if(u)return $a(r,u);if((s==null?void 0:s.sort)==="formula")return"formula";if((s==null?void 0:s.sort)==="relation"){const c=new Set;for(const v of s.shapes)c.add(v.columns.length);return c.size===1?`relation; width ${[...c][0]}, nominal schema unresolved`:"relation; nominal schema unresolved"}return"unresolved constraint"}function g4(r){const d=r.index.get(r.id),f=[],u=[];if(!d||r.depth>=32)return I.jsx("p",{role:"alert",children:"Missing node or depth limit."});for(const v of Be(d))f.push(I.jsx(g4,{...r,id:v,depth:r.depth+1},v));for(const v of r.checked.diagnostics)v.nodeId===d.id&&u.push(I.jsx("li",{children:v.message},v.message));const s=`constraint-${d.id}`,c=d.tag==="hole"?"Unresolved hole":d.tag.replaceAll("_"," ");return I.jsxs("div",{className:"document-branch",children:[I.jsxs("button",{id:`block-${d.id}`,draggable:d.tag!=="hole",onDragStart:wI.bind(null,d.id,r.snapshot),onDragOver:HI,onDrop:r.onDrop.bind(null,d.id),onClick:r.onSelect.bind(null,d.id),"aria-pressed":r.selected===d.id,"aria-describedby":s,children:[c," · ",qI(r.module,d.id,r.checked)]}),I.jsxs("p",{id:s,children:["Expected: ",r.constraints.get(d.id)??"unresolved constraint"]}),u.length>0&&I.jsx("ul",{children:u}),I.jsx("div",{className:"document-children",children:f})]})}function YI(r,d,f,u){try{const s=JSON.parse(d);if(s&&typeof s=="object"&&"nodeId"in s&&typeof s.nodeId=="string"&&"snapshot"in s&&s.snapshot===r.snapshot){r.onDropNode(s.nodeId,f,u);return}}catch{r.onNotice("Malformed dragged source.");return}r.onNotice("Stale or foreign dragged source; draft unchanged.")}function GI(r){return{signature_ref:"Signature",field_ref:"Field",variable_ref:"Variable",predicate_call:"Call predicate",some_test:"Some tuples",no_test:"No tuples",one_test:"Exactly one tuple",lone_test:"At most one tuple",all_quant:"For every variable",some_quant:"For some variable",equal:"Equals",subset:"Subset",implies:"Implies",iff:"If and only if"}[r]??r.charAt(0).toUpperCase()+r.slice(1)}function $t(r){return JSON.stringify(r,null,2)??"Unavailable"}function I4(r){return`Root ${r.rootPath.length?r.rootPath.join("."):"0"}`}function LI(r){return r==="CHECKED"?"Equivalence certificate checked":r==="FAILED"?"Certificate check failed":"Equivalence certificate unavailable"}function QI(r){return{SATURATED:"Saturated within supported rules",NODE_LIMIT:"Node budget reached",ITERATION_LIMIT:"Iteration budget reached",MATCH_LIMIT:"Match budget reached",UNION_LIMIT:"Union budget reached",PROOF_LIMIT:"Proof budget reached",TIME_LIMIT:"Time budget reached",INPUT_LIMIT:"Input budget reached",OUTPUT_LIMIT:"Output budget reached",ERROR:"Optimization unavailable"}[r]??"Search termination unavailable"}function XI(r){return r==="SATURATED"?"No further work was found in this finite rule profile. This is not a complete normal form for Alloy.":"Search is incomplete. A checked extraction remains equivalent under the supported rule profile."}function ZI(r){return I.jsxs("li",{children:[I.jsxs("strong",{children:["Class ",r.id]}),": ",r.nodes.map(v4).join(", ")||"No displayed nodes"]},r.id)}function v4(r){return r.op}function VI(r,d){const f=d%3*176+14,u=Math.floor(d/3)*110+20;return I.jsxs("g",{transform:`translate(${f},${u})`,children:[I.jsx("rect",{width:"146",height:"52",rx:"7"}),I.jsxs("text",{x:"9",y:"19",children:["Class ",r.id]}),I.jsx("text",{x:"9",y:"37",className:"graph-ops",children:r.nodes.map(v4).join(" · ").slice(0,18)})]},r.id)}function qc(r,d){const f=r.findIndex(KI.bind(null,d));return f<0?void 0:{x:f%3*176+87,y:Math.floor(f/3)*110+46}}function KI(r,d){return d.id===r}function JI(r,d,f,u){const s=qc(r,f.from),c=qc(r,f.to);if(!s||!c)return null;const v=f.from===f.to,p=25+f.position%3*9,A=v?`M ${s.x+58} ${s.y} C ${s.x+100} ${s.y-58}, ${s.x-20} ${s.y-58}, ${s.x} ${s.y-27}`:`M ${s.x} ${s.y+26} Q ${(s.x+c.x)/2+p} ${(s.y+c.y)/2+38}, ${c.x} ${c.y+29}`;return I.jsxs("g",{className:"graph-edge",children:[I.jsx("path",{d:A,markerEnd:`url(#${d})`}),I.jsx("text",{x:v?s.x+76:(s.x+c.x)/2+p/2,y:v?s.y-30:(s.y+c.y)/2+48,children:f.position+1})]},`${f.from}:${f.to}:${f.position}:${u}`)}function kI(r,d){return I.jsxs("li",{children:["Class ",r.from," → class ",r.to," · child ",r.position+1]},`${r.from}:${r.to}:${r.position}:${d}`)}function $I(r){const d=new Set,f=[];for(const u of r.preview.edges??[]){const s=`${u.from}:${u.to}:${u.position}`;d.has(s)||(d.add(s),f.push(u))}return f}function WI(r){const d=`arrow-${l0.useId().replace(/:/g,"")}`,f=r.island.preview.classes??[],u=$I(r.island),s=Math.max(110,Math.ceil(f.length/3)*110+30);return I.jsxs("details",{children:[I.jsxs("summary",{children:["Graph preview · ",f.length," displayed classes"]}),f.length>0?I.jsxs(I.Fragment,{children:[I.jsx("div",{className:"egraph-scroll",children:I.jsxs("svg",{className:"egraph-svg",viewBox:`0 0 540 ${s}`,role:"img","aria-label":"Anonymous e-class membership and directed child dependencies",children:[I.jsx("title",{children:"Arrows connect parent classes to child classes; numbers are child positions"}),I.jsx("defs",{children:I.jsx("marker",{id:d,viewBox:"0 0 10 10",refX:"9",refY:"5",markerWidth:"6",markerHeight:"6",orient:"auto-start-reverse",children:I.jsx("path",{d:"M 0 0 L 10 5 L 0 10 z"})})}),u.map(JI.bind(null,f,d)),f.map(VI)]})}),I.jsx("ol",{className:"graph-text",children:f.map(ZI)}),I.jsxs("details",{children:[I.jsxs("summary",{children:["Directed child dependencies · ",u.length]}),I.jsx("ul",{className:"graph-text",children:u.map(kI)}),!u.length&&I.jsx("p",{children:"No child dependencies are displayed."})]})]}):I.jsx("p",{children:"No graph preview is available."}),r.island.preview.truncated&&I.jsx("p",{children:"Graph preview is truncated; search termination is reported separately."}),I.jsx("p",{children:"Arrows point from parent to child class. Numbers identify ordered child positions; cards group equivalent nodes."}),I.jsxs("details",{children:[I.jsx("summary",{children:"Complete displayed graph data"}),I.jsx("pre",{children:$t(r.island.preview)})]})]})}function FI(r){return I.jsxs("div",{children:[I.jsx("dt",{children:r[0]}),I.jsx("dd",{children:r[1]})]},r[0])}function PI(r){const d=r.island,f=d.certificate?`data:application/json;charset=utf-8,${encodeURIComponent($t(d.certificate))}`:null;return I.jsxs("details",{children:[I.jsx("summary",{children:"Proof details"}),I.jsx("p",{children:"Local replay checks concrete endpoints and supported rules. The running JVM and parser are not verified by Lean."}),I.jsx("pre",{children:$t(d.proofSummary)}),f&&I.jsxs(I.Fragment,{children:[I.jsx("a",{className:"certificate-download",href:f,download:`allow-proof-${d.rootPath.join("-")||"0"}.json`,children:"Download anonymous certificate"}),I.jsxs("details",{children:[I.jsx("summary",{children:"Inspect certificate"}),I.jsx("pre",{children:$t(d.certificate)})]})]})]})}function nv(r){const d=r.island,f=d.certificateStatus==="CHECKED"&&d.input!==null&&d.extracted!==null;return I.jsxs("section",{className:"egraph-island","aria-label":I4(d),children:[I.jsxs("div",{className:"egraph-badges",children:[I.jsx("span",{className:f?"evidence checked":"evidence",children:LI(f?"CHECKED":d.certificateStatus==="CHECKED"?"UNAVAILABLE":d.certificateStatus)}),I.jsx("span",{className:"termination",children:QI(d.stopReason)})]}),I.jsx("p",{children:f?XI(d.stopReason):"No checked extracted-equivalence result is available for this root."}),f&&I.jsxs(I.Fragment,{children:[I.jsxs("div",{className:"extraction-cost",children:[I.jsx("span",{children:"Tree cost"}),I.jsxs("strong",{children:[d.inputCost," → ",d.extractedCost]}),I.jsx("small",{children:"Unit cost per node occurrence"})]}),I.jsxs("details",{open:!0,children:[I.jsx("summary",{children:"Anonymous extracted term"}),I.jsx("pre",{children:$t(d.extracted)})]}),I.jsxs("details",{children:[I.jsx("summary",{children:"Anonymous input term"}),I.jsx("pre",{children:$t(d.input)})]})]}),I.jsx("dl",{className:"graph-statistics",children:Object.entries(d.stats).map(FI)}),I.jsx(WI,{island:d}),I.jsx(PI,{island:d})]})}function ev(r,d){return I.jsxs("option",{value:d,children:[I4(r)," · ",r.certificateStatus]},`${d}:${r.rootPath.join(".")}`)}function tv(r){const[d,f]=l0.useState(0),u=l0.useId(),s=r.value,c=s.islands[d]??s.islands[0];function v(p){f(Number(p.target.value))}return I.jsxs("section",{className:"egraph-panel","aria-label":"Anonymous equality optimization",children:[I.jsxs("div",{className:"egraph-heading",children:[I.jsx("h4",{children:"Equality optimization"}),I.jsx("span",{children:"READ ONLY"})]}),I.jsx("p",{children:"Anonymous views of supported expression roots. Original Alloy source and its bounded analysis remain unchanged. Different extracted terms do not prove inequivalence."}),I.jsxs("p",{className:"egraph-status",children:[s.islands.length," root",s.islands.length===1?"":"s"," · Module status: ",s.status]}),s.truncated&&I.jsx("p",{className:"egraph-warning",children:"Module output is truncated; not every root is represented. This does not establish complete optimization."}),c?I.jsxs(I.Fragment,{children:[I.jsx("label",{htmlFor:u,children:"Expression root"}),I.jsx("select",{id:u,value:Math.min(d,s.islands.length-1),onChange:v,children:s.islands.map(ev)}),I.jsx(nv,{island:c})]}):I.jsx("p",{children:"No optimization islands are available. No extracted equivalence is claimed."}),I.jsxs("details",{children:[I.jsx("summary",{children:"Optimization profile"}),I.jsx("p",{children:s.profile}),I.jsxs("p",{children:["Rule registry digest: ",s.rulesetDigest]}),I.jsx("p",{children:"Digests identify artifacts; digest equality alone is not an equivalence proof."})]})]})}function av(r,d){return r==="SAT"&&d==="check"?"Counterexample found":r==="SAT"&&d==="run"?"Instance found":r==="UNSAT"&&d==="check"?"No counterexample within bounds":r==="UNSAT"&&d==="run"?"No instance within bounds":r==="SAT"?"Satisfiable within bounds":r==="UNSAT"?"Unsatisfiable within bounds":{QUEUED:"Queued",RUNNING:"Running",VALIDATED:"Source validated",INVALID:"Invalid source",UNSUPPORTED:"Unsupported",UNKNOWN:"Inconclusive",ERROR:"Analysis error",TIMEOUT:"Time limit reached",CANCELLED:"Cancelled"}[r]}function rv(r){return r.memberships.length?`${r.id} (${r.memberships.join(", ")})`:r.id}function dv(r){return I.jsx("li",{children:rv(r)},r.id)}function lv(r){return r.join(" → ")}function iv(r){const d=r.tuples.slice(0,8).map(lv).join(", "),f=r.tuples.length>8?`, +${r.tuples.length-8} more`:"";return I.jsxs("li",{children:[I.jsx("strong",{children:r.name})," ",I.jsxs("span",{children:["(",r.arity,")"]}),I.jsxs("div",{children:[d||"∅",f]})]},r.name)}function fv(r,d){return I.jsxs("section",{className:"witness-state",children:[I.jsxs("h4",{children:["State ",d+1]}),r.atoms.length>0&&I.jsxs(I.Fragment,{children:[I.jsx("span",{className:"result-caption",children:"ATOMS"}),I.jsx("ul",{children:r.atoms.slice(0,12).map(dv)}),r.atoms.length>12&&I.jsxs("small",{children:["+",r.atoms.length-12," more atoms"]})]}),r.relations.length>0&&I.jsxs(I.Fragment,{children:[I.jsx("span",{className:"result-caption",children:"RELATIONS"}),I.jsx("ul",{children:r.relations.slice(0,12).map(iv)}),r.relations.length>12&&I.jsxs("small",{children:["+",r.relations.length-12," more relations"]})]})]},d)}function uv(r){const d=r.witness;return I.jsxs("div",{className:"witness",children:[I.jsx("h4",{children:"Witness"}),I.jsxs("p",{children:[d.traceLength," state",d.traceLength===1?"":"s",d.loopState>=0?` · loop at state ${d.loopState+1}`:""]}),d.states.slice(0,3).map(fv),d.states.length>3&&I.jsxs("small",{children:["+",d.states.length-3," more displayed states"]}),d.truncated&&I.jsx("p",{children:"Witness display is truncated."}),I.jsxs("details",{children:[I.jsx("summary",{children:"Witness provenance"}),I.jsxs("p",{children:["Full instance hash: ",d.fullInstanceHash]})]})]})}function sv(r){const d=r.canonical;return I.jsxs("details",{className:"canonical-details",children:[I.jsx("summary",{children:"Anonymous structural profile"}),I.jsxs("p",{children:["Status: ",d.status]}),d.sha256&&I.jsxs("p",{children:["SHA-256: ",d.sha256]}),d.features&&I.jsxs("p",{children:["Feature dimensions: ",d.features.length]}),d.payload&&I.jsx("pre",{children:d.payload}),I.jsx("p",{children:"Structural representation for retrieval; it is not an equivalence proof."})]})}function ov(r){var f;const d=r.job;return I.jsxs("div",{className:"results",children:[I.jsxs("div",{className:"results-heading",children:[I.jsx("h3",{children:"ANALYSIS"}),I.jsx("span",{children:(d==null?void 0:d.status)??"READY"})]}),d&&I.jsx("p",{className:"result-label",children:av(d.status,d.commandKind)}),I.jsx("p",{"aria-live":"polite",children:r.notice}),(d==null?void 0:d.message)&&I.jsx("p",{children:d.message}),(d==null?void 0:d.witness)&&I.jsx(uv,{witness:d.witness}),(d==null?void 0:d.canonical)&&I.jsx(sv,{canonical:d.canonical}),((f=d==null?void 0:d.canonical)==null?void 0:f.egraph)&&I.jsx(tv,{value:d.canonical.egraph},`${d.jobId}:${d.sourceHash}:${d.revision}:${d.epoch}`),I.jsx("p",{className:"disclaimer",children:"Results are bounded by the selected Alloy command. A lack of counterexamples is not an unbounded proof."})]})}function zd(r,d){if(r===d)return!0;if(!r||!d||typeof r!="object"||typeof d!="object"||Array.isArray(r)!==Array.isArray(d))return!1;const f=Object.keys(r).sort(),u=Object.keys(d).sort();if(f.length!==u.length)return!1;for(let s=0;s<f.length;s++)if(f[s]!==u[s]||!zd(r[f[s]],d[u[s]]))return!1;return!0}function gf(r,d){const f=r.accepted;if(!f||r.dirty||r.source!==f.artifact.source||f.headRevision!==f.revision)return null;for(const u of f.artifact.analysisDescriptors)if(u.commandKey===d&&u.artifactId===f.artifact.artifactId&&u.sourceHash===f.artifact.sourceHash&&u.policyVersion===f.artifact.policyVersion)return{accepted:f,descriptor:u,draftId:r.draftId,epoch:r.epoch,contentGeneration:r.contentGeneration};return null}function pf(r,d){if(!d)return!1;const f=r.accepted,u=d.accepted;return r.draftId===d.draftId&&r.epoch===d.epoch&&r.contentGeneration===d.contentGeneration&&f.documentId===u.documentId&&f.revision===u.revision&&f.artifact.artifactId===u.artifact.artifactId&&f.artifact.source===u.artifact.source&&f.artifact.sourceHash===u.artifact.sourceHash&&f.artifact.policyVersion===u.artifact.policyVersion&&f.artifact.dependencyHash===u.artifact.dependencyHash&&r.descriptor.commandKey===d.descriptor.commandKey&&zd(r.descriptor.options,d.descriptor.options)}function m4(r,d,f){if(!(r!=null&&r.job)||!r.acceptedAnalysisKey)return!1;const u=r.acceptedAnalysisKey,s=d.accepted,c=s.artifact,v=r.job;return u.documentId===s.documentId&&u.acceptedRevision===s.revision&&u.draftEpoch===d.epoch&&u.artifactId===c.artifactId&&u.sourceHash===c.sourceHash&&u.policyVersion===c.policyVersion&&u.dependencyHash===c.dependencyHash&&u.commandKey===d.descriptor.commandKey&&zd(u.options,d.descriptor.options)&&typeof u.jobAnalysisKey=="string"&&u.jobAnalysisKey.length>0&&v.jobId===r.jobId&&v.sourceHash===u.sourceHash&&v.revision===u.acceptedRevision&&v.epoch===u.draftEpoch&&v.analysisKey===u.jobAnalysisKey&&(!f||zd(u,f))}function cv(r,d,f){return r.historical!==!0&&pf(d,f)&&m4(r,d)}function Yc(r){return r.status!=="QUEUED"&&r.status!=="RUNNING"}function gv(r){r.abort("deadline")}async function h4(r,d,f){return r.transport?r.transport(d,f,r.controller.signal):er(r.token,d,f,r.controller.signal)}function y4(r,d,f){return r.controller.signal.aborted?!1:!m4(d,r.snapshot,f)||d.historical===!0||!pf(r.snapshot,r.current())?(r.emit({kind:"historical",data:null,notice:"This analysis belongs to an earlier model or command. Run the current model for a current result."}),!1):(r.emit({kind:"current",data:d,notice:Yc(d.job)?"Analysis finished within the selected bounds.":"Analyzing the saved model…"}),!Yc(d.job))}async function Iv(r,d){var f;for(let u=0;u<60;u++){if(await hv(r.controller.signal),!pf(r.snapshot,r.current()))return;const s=`${qn}/${encodeURIComponent(r.snapshot.accepted.documentId)}/analysis/${encodeURIComponent(d.jobId)}`,c=await h4(r,s);if(c.status!=="OK"||typeof((f=c.data)==null?void 0:f.historical)!="boolean")throw new Error("Analysis result is unavailable.");if(!y4(r,c.data,d.acceptedAnalysisKey))return}r.emit({kind:"timeout",data:null,notice:"Stopped waiting for analysis. You can run the saved model again."})}async function vv(r){const d=setTimeout(gv.bind(null,r.controller),15e3),f=r.snapshot;try{const u=Dd({acceptedRevision:f.accepted.revision,commandKey:f.descriptor.commandKey,draftEpoch:f.epoch,exactSourceHash:f.accepted.artifact.sourceHash}),s=await h4(r,`${qn}/${encodeURIComponent(f.accepted.documentId)}/analyze`,u);if(s.status!=="SUBMITTED")throw new Error("Analysis could not be started.");y4(r,s.data)&&await Iv(r,s.data)}catch(u){r.controller.signal.reason==="deadline"?r.emit({kind:"timeout",data:null,notice:"Stopped waiting after15 seconds. The saved model is unchanged."}):r.controller.signal.aborted||r.emit({kind:"unavailable",data:null,notice:u instanceof Error?u.message:"Analysis unavailable."})}finally{clearTimeout(d)}}function mv(r,d,f){function u(){r.removeEventListener("abort",s),d()}function s(){clearTimeout(c),r.removeEventListener("abort",s),f(new DOMException("Analysis wait aborted","AbortError"))}const c=setTimeout(u,250);if(r.aborted){s();return}r.addEventListener("abort",s,{once:!0})}function hv(r){return new Promise(mv.bind(null,r))}function bf(r){var d;(d=r.current)==null||d.abort("view changed"),r.current=null}function yv(r){return bf.bind(null,r)}function pv(r){bf(r.active);const d=gf(r.controller.current.current.document,r.command.current);if(!d)return;const f=d,u=new AbortController;r.active.current=u;function s(){return gf(r.controller.current.current.document,r.command.current)}function c(v){r.active.current===u&&r.setOutcome({snapshot:f,event:v})}r.setOutcome({snapshot:f,event:{kind:"waiting",data:null,notice:"Starting analysis…"}}),vv({token:r.controller.token,snapshot:f,controller:u,current:s,emit:c})}function bv(r){var y0,T0,Q0;const[d,f]=l0.useState(""),[u,s]=l0.useState(null),c=l0.useRef(null),v=l0.useRef(d),p=r.view.document,A=[];v.current=d;for(const C0 of((y0=p.accepted)==null?void 0:y0.artifact.analysisDescriptors)??[])A.push({id:C0.commandKey,label:C0.label});l0.useEffect(yv.bind(null,c),[p.draftId,p.epoch,p.contentGeneration,(T0=p.accepted)==null?void 0:T0.artifact.artifactId,(Q0=p.accepted)==null?void 0:Q0.documentId,p.dirty,d]);const S={controller:r.controller,command:v,active:c,setOutcome:s};function N(C0){bf(c),v.current=C0,f(C0);const jn=r.controller.current.current.document;_0(r.controller,Ue(jn,jn.selected))}const U=gf(p,d),Y=u==null?void 0:u.event.data,u0=!!Y&&!!u&&cv(Y,u.snapshot,U);return I.jsxs("fieldset",{className:"document-analysis",children:[I.jsx("legend",{children:"Explore this model"}),I.jsx(de,{label:"Command",value:d,options:A,onChange:N}),I.jsx("button",{disabled:!U,onClick:pv.bind(null,S),children:"Run analysis"}),u0&&Y?I.jsx(ov,{job:Y.job,notice:u.event.notice}):I.jsx(Sv,{outcome:u,dirty:p.dirty})]})}function Sv(r){return r.dirty?I.jsx("p",{children:"Save your changes before analyzing this model."}):r.outcome?r.outcome.event.kind==="current"||r.outcome.event.kind==="historical"?I.jsx("p",{children:"Historical analysis: the model, command or selection changed. Run again for a current result."}):I.jsx("p",{role:"status",children:r.outcome.event.notice}):I.jsx("p",{children:"Select a command to look for an instance or counterexample."})}function _v(r){const[d,f]=l0.useState("Untitled model"),[u,s]=l0.useState(""),c=[];for(const S of r.view.documents)c.push({id:S.documentId,label:S.title});function v(){iI(r.controller,d)}function p(){u&&l4(r.controller,u)}function A(){Od(r.controller)}return I.jsxs("section",{"aria-label":"Documents",className:"document-navigation",children:[I.jsx(ar,{label:"New model name",value:d,onChange:f}),I.jsx("button",{disabled:!!r.view.document.pending,onClick:v,children:"Create model"}),I.jsx(de,{label:"Your models",value:u,options:c,onChange:s}),I.jsx("button",{disabled:!u||!!r.view.document.pending,onClick:p,children:r.view.document.dirty?"Open and discard unsaved changes":"Open model"}),I.jsx("button",{onClick:A,children:"Refresh"})]})}function xv(r){const d=r.view.document;let f=!0;try{Cd(d)}catch{f=!1}function u(){fI(r.controller)}function s(){d.pending&&Md(r.controller,d.pending)}return I.jsxs("section",{"aria-label":"Draft acceptance",className:"document-savebar",children:[I.jsx("strong",{children:d.dirty?"Unsaved changes":"Saved version"}),I.jsx("button",{disabled:!f||!d.accepted,onClick:r.onValidate,children:"Check model"}),I.jsx("button",{disabled:!f||!d.accepted||!!d.pending,onClick:u,children:"Save version"}),d.pending&&I.jsxs(I.Fragment,{children:[I.jsx("span",{children:"Waiting for save confirmation."}),I.jsx("button",{onClick:s,children:"Recover save"})]}),I.jsxs("details",{children:[I.jsx("summary",{children:"Save details"}),I.jsxs("p",{children:["Draft mode: ",d.mode,"; based on version ",d.baseRevision,"."]}),d.pending&&I.jsxs("p",{children:["Pending request: ",d.pending.key,". Recovery resends identical bytes; a network error does not establish rollback."]}),I.jsx("p",{children:"Pending model data stays in this tab. After restarting your browser, inspect the saved model and version history before resubmitting changes."})]})]})}function Av(r){var S;const[d,f]=l0.useState("0"),[u,s]=l0.useState("UNDO");function c(){u4(r.controller,Number(d),u==="REDO"?"REDO":"UNDO")}function v(){yI(r.controller)}const p=r.view.history,A=r.view.document;return I.jsxs("details",{className:"document-history",children:[I.jsx("summary",{children:"Version history and provenance"}),I.jsxs("p",{children:["Saved version ",((S=A.accepted)==null?void 0:S.headRevision)??"none",". Undo/Redo creates a new version; earlier versions remain unchanged."]}),I.jsx(ar,{label:"Version to restore",value:d,onChange:f}),I.jsx(de,{label:"Direction",value:u,options:[{id:"UNDO",label:"Undo"},{id:"REDO",label:"Redo"}],onChange:s}),I.jsx("button",{disabled:!A.accepted,onClick:c,children:"Preview Undo/Redo target"}),p&&I.jsxs(I.Fragment,{children:[I.jsxs("p",{children:["Target version ",p.revision]}),I.jsx("pre",{children:p.artifact.source}),I.jsx("button",{disabled:!!A.pending,onClick:v,children:A.dirty?"Replace unsaved changes with this version":"Restore as a new version"}),I.jsxs("p",{children:["Artifact ",p.artifact.artifactId,"; navigation cursor ",A.historyCursor??"none","."]})]})]})}function Ev(r){var v;const d=r.view.document,f=d.mode==="SOURCE"?d.source:d.preview??d.historicalPreview??d.source;function u(p){sI(r.controller,p.target.value)}function s(){const p=r.controller.current.current.document;_0(r.controller,Ue(p,p.selected))}function c(){_0(r.controller,{...Ue(d,d.selected),mode:"BLOCK_SUPPORTED",dirty:!0,contentGeneration:d.contentGeneration+1,clipboard:null,notice:"Block editing resumed. Check and save when ready."})}return I.jsxs("section",{"aria-label":"Source and accepted artifact",className:"document-source",children:[I.jsx("h2",{children:"Alloy source"}),I.jsx("p",{children:d.mode==="SOURCE"?"Editing source directly.":d.preview?"Live block preview.":d.dirty?"Previous source preview; complete blocks are checked automatically.":"Source for the saved model."}),I.jsxs("label",{children:["Source",I.jsx("textarea",{id:"document-source-draft",value:f,onChange:u,onSelect:s,spellCheck:!1})]}),d.mode==="SOURCE"&&I.jsx("button",{disabled:!((v=d.accepted)!=null&&v.artifact.module),onClick:c,children:"Resume block editing"}),I.jsx(bv,{controller:r.controller,view:r.view}),I.jsx(Tv,{controller:r.controller,view:r.view})]})}function Tv(r){const d=r.view.document,f=d.accepted,u=[];if(!f)return null;function s(c){var A;const v=r.controller.current.current.document,p=(A=v.accepted)==null?void 0:A.artifact;if(!p||v.dirty||v.epoch!==d.epoch||v.source!==p.source||p.artifactId!==f.artifact.artifactId){L0(r.controller,"This location belongs to an earlier version.");return}for(const S of p.occurrences)if(S.occurrenceId===c){const N=document.getElementById("document-source-draft");N==null||N.focus(),N==null||N.setSelectionRange(S.startUtf16,S.endUtf16);return}}for(const c of f.artifact.occurrences)u.push(I.jsxs("button",{disabled:d.dirty,onClick:s.bind(null,c.occurrenceId),children:[c.role," ",c.startUtf16,"–",c.endUtf16]},c.occurrenceId));return I.jsxs("details",{children:[I.jsxs("summary",{children:["Saved source and provenance · version ",f.revision]}),I.jsx("p",{children:f.artifact.mode==="TEXT_ONLY"?"Text-only model":"Block-supported model"}),I.jsx("pre",{children:f.artifact.source}),I.jsx("div",{"aria-label":"Accepted occurrence locations",children:u}),I.jsxs("p",{children:["Artifact ",f.artifact.artifactId,"; policy ",f.artifact.policyVersion,"; source hash ",f.artifact.sourceHash,"."]}),I.jsxs("details",{children:[I.jsx("summary",{children:"Comments and orphan notices"}),I.jsx("pre",{children:JSON.stringify(f.artifact.trivia,null,2)})]})]})}function jv(r,d){var u;const f=d.target;if(!(["INPUT","TEXTAREA","SELECT"].includes(f.tagName)||f.isContentEditable||!f.closest(".document-blocks"))&&(d.ctrlKey||d.metaKey)&&d.key.toLowerCase()==="z"){d.preventDefault();const s=r.current.current.document,c=s.historyCursor??((u=s.accepted)==null?void 0:u.headRevision)??0;u4(r,Math.max(0,c+(d.shiftKey?1:-1)),d.shiftKey?"REDO":"UNDO")}}class Ov{constructor(){n0(this,"latest",null);n0(this,"active",null);n0(this,"activeKey",null);n0(this,"attempted",null);n0(this,"timer",null);n0(this,"disposed",!1)}request(d,f=!1){this.disposed||d.key===this.activeKey||!f&&d.key===this.attempted||(this.latest=d,this.timer&&clearTimeout(this.timer),this.active||(this.timer=setTimeout(this.begin.bind(this),f?0:350)))}clearPending(){this.latest=null,this.timer&&clearTimeout(this.timer),this.timer=null}dispose(){var d;this.disposed=!0,this.clearPending(),(d=this.active)==null||d.abort("view closed")}begin(){if(this.timer=null,this.disposed||this.active||!this.latest)return;const d=this.latest,f=new AbortController;this.latest=null,this.active=f,this.activeKey=d.key,this.attempted=d.key,this.execute(d,f)}async execute(d,f){const u=setTimeout(this.abort.bind(this,f),15e3);try{await d.run(f.signal)}catch{}finally{clearTimeout(u),this.active=null,this.activeKey=null,!this.disposed&&this.latest&&(this.timer=setTimeout(this.begin.bind(this),350))}}abort(d){d.abort("advisory deadline")}}function p4(r){var d;return JSON.stringify([(d=r.accepted)==null?void 0:d.documentId,r.draftId,r.contentGeneration,r.baseRevision,r.mode])}async function zv(r,d,f){f.aborted||p4(r.current.current.document)!==d||await uI(r,f)}function Gc(r,d,f=!1){const u=r.current.current.document;if(!u.accepted||!f&&!u.dirty){d.clearPending();return}try{Cd(u)}catch{d.clearPending();return}const s=p4(u);d.request({key:s,run:zv.bind(null,r,s)},f)}function Dv(){return new Ov}function Cv(r){return r.dispose.bind(r)}function Nv(r,d){var u;const f=l0.useMemo(Dv,[r.token]);return l0.useEffect(Cv.bind(null,f),[f]),l0.useEffect(Gc.bind(null,r,f,!1),[f,d.draftId,d.contentGeneration,d.baseRevision,d.mode,(u=d.accepted)==null?void 0:u.documentId]),Gc.bind(null,r,f,!0)}function Mv(r){const[d,f]=l0.useState({document:e4(),documents:[],target:0,history:null,direction:"UNDO"}),u=l0.useRef(d),s={token:r,current:u,set:f};function c(){Od(s)}return l0.useEffect(c,[r]),{view:d,controller:s}}function Uv(r){const{view:d,controller:f}=Mv(r.token);return cg(f,d),I.jsxs("main",{className:"document-workbench",onKeyDown:jv.bind(null,f),children:[I.jsxs("header",{children:[I.jsx("h1",{children:"Allow"}),I.jsx("p",{children:"Build an Alloy model with blocks, edit its source, and explore examples."})]}),I.jsx("p",{role:"status","aria-live":"polite",children:d.document.notice}),I.jsx(_v,{controller:f,view:d}),d.document.accepted&&I.jsx(Rv,{controller:f,view:d})]})}function Rv(r){var v;const{controller:d,view:f}=r,u=f.document,s=[],c=Nv(d,u);for(const p of Wa(u.module,u.slotObligations).diagnostics)s.push(I.jsx("li",{children:p.message},`${p.nodeId}:${p.message}`));for(const p of[...u.rejectionDiagnostics,...((v=u.validation)==null?void 0:v.diagnostics)??[]])s.push(I.jsx("li",{children:p.message},`server:${p.nodeId}:${p.message}`));return I.jsxs(I.Fragment,{children:[I.jsx(xv,{controller:d,view:f,onValidate:c}),I.jsxs("div",{className:"document-layout",children:[I.jsx(AI,{module:u.module,onChange:yf.bind(null,d),onSelect:i4.bind(null,d)}),I.jsx(Bv,{controller:d,view:f}),I.jsx(Ev,{controller:d,view:f})]}),I.jsxs("section",{"aria-label":"Draft diagnostics",children:[I.jsx("h2",{children:"Specific diagnostics"}),I.jsx("ul",{children:s})]}),I.jsx(Av,{controller:d,view:f})]})}function Bv(r){var s;const{controller:d,view:f}=r,u=f.document;return I.jsx(DI,{snapshot:JSON.stringify([(s=u.accepted)==null?void 0:s.documentId,u.baseRevision,u.draftId,u.contentGeneration]),module:u.module,slotObligations:u.slotObligations,selected:u.selected,onSelect:i4.bind(null,d),onInsert:oI.bind(null,d),onClipboard:cI.bind(null,d),onPaste:gI.bind(null,d),onDelete:vI.bind(null,d),onCancel:pI.bind(null,d),onDropNode:II.bind(null,d),onNotice:L0.bind(null,d)})}function Fa(r){if(r===null||typeof r!="object"||Array.isArray(r))throw new Error("Invalid corpus response.");return r}function V0(r){if(typeof r!="number"||!Number.isFinite(r))throw new Error("Invalid corpus measurement.");return r}function lt(r){if(typeof r!="string")throw new Error("Invalid corpus metadata.");return r}async function Sf(r,d,f){const u=await fetch(`/api/corpus/${d}`,{method:f?"POST":"GET",headers:{Authorization:`Bearer ${r}`,...f?{"Content-Type":"application/json"}:{}},...f?{body:JSON.stringify(f)}:{}});if(!u.ok)throw new Error(u.status===503?"Start the local corpus service to browse its records.":"Corpus request failed.");const s=Fa(await u.json());if(s.protocol!==1||s.status!=="OK")throw new Error("The corpus is unavailable or quarantined.");return Fa(s.data)}async function Hv(r){const d=await Sf(r,"status");return{records:V0(d.records),full:V0(d.full),vectors:V0(d.vectors),revoked:V0(d.revoked),journal_sequence:V0(d.journal_sequence)}}function wv(r){const d=Fa(r);return{id:lt(d.id),family:lt(d.family),split:lt(d.split),n:V0(d.n),status:lt(d.status)}}async function qv(r){const d=await Sf(r,"records");if(!Array.isArray(d.records))throw new Error("Invalid corpus record list.");return d.records.map(wv)}function Yv(r){const d=Fa(r);if(typeof d.contextCompatible!="boolean")throw new Error("Invalid corpus compatibility status.");return{recordId:lt(d.recordId),family:lt(d.family),score:V0(d.score),canonicalSimilarity:V0(d.canonicalSimilarity),predicateCosine:V0(d.predicateCosine),sharedPositive:V0(d.sharedPositive),sharedNegative:V0(d.sharedNegative),contextCompatible:d.contextCompatible,positiveCount:V0(d.positiveCount),negativeCount:V0(d.negativeCount)}}function Gv(r,d){const f=Fa(r);if(f.queryRecordId!==d||!Array.isArray(f.results)||!Array.isArray(f.weights)||typeof f.exact!="boolean")throw new Error("Corpus query identity changed.");return{queryRecordId:d,modelId:lt(f.modelId),exact:f.exact,candidateCount:V0(f.candidateCount),weights:f.weights.map(V0),results:f.results.map(Yv)}}async function Lv(r,d){return Gv(await Sf(r,"search",{recordId:d,limit:5}),d)}function Qv(){const[r,d]=l0.useState(null),[f,u]=l0.useState([]),[s,c]=l0.useState(""),[v,p]=l0.useState(null),[A,S]=l0.useState("Browse locally stored predicates and their example pools."),[N,U]=l0.useState(!1),Y=l0.useRef(0);return{status:r,setStatus:d,records:f,setRecords:u,selected:s,setSelected:c,result:v,setResult:p,notice:A,setNotice:S,busy:N,setBusy:U,generation:Y}}function b4(r){return r.generation.current+=1,r.setResult(null),r.setBusy(!0),r.generation.current}async function Xv(r,d){var u;const f=b4(r);r.setNotice("Reading the local corpus…");try{const[s,c]=await Promise.all([Hv(d),qv(d)]);if(f!==r.generation.current)return;r.setStatus(s),r.setRecords(c),r.setSelected(((u=c[0])==null?void 0:u.id)??""),r.setNotice(c.length?"Choose a stored predicate to retrieve related candidates.":"No eligible embedded records yet.")}catch(s){f===r.generation.current&&r.setNotice(s instanceof Error?s.message:"Corpus unavailable.")}finally{f===r.generation.current&&r.setBusy(!1)}}function Zv(r,d){r.generation.current+=1,r.setSelected(d.target.value),r.setResult(null),r.setBusy(!1)}async function Vv(r,d){const f=b4(r);r.setNotice("Ranking candidates from the local corpus…");try{const u=await Lv(d,r.selected);if(f!==r.generation.current)return;r.setResult(u),r.setNotice("Candidate ranking ready. Similarity does not establish equivalence.")}catch(u){f===r.generation.current&&r.setNotice(u instanceof Error?u.message:"Retrieval failed.")}finally{f===r.generation.current&&r.setBusy(!1)}}function Kv(r){return I.jsxs("option",{value:r.id,children:[r.id.slice(0,12)," · ",r.family," · ",r.n,"+ / ",r.n,"−"]},r.id)}function Jv(r){return I.jsxs("li",{className:"corpus-hit",children:[I.jsxs("div",{children:[I.jsx("strong",{children:r.recordId.slice(0,12)}),I.jsx("span",{className:"corpus-score",children:r.score.toFixed(3)})]}),I.jsxs("p",{children:[r.family," · ",r.positiveCount," examples / ",r.negativeCount," counterexamples"]}),I.jsxs("dl",{children:[I.jsxs("div",{children:[I.jsx("dt",{children:"Hierarchy similarity"}),I.jsx("dd",{children:r.canonicalSimilarity.toFixed(3)})]}),I.jsxs("div",{children:[I.jsx("dt",{children:"Shared examples"}),I.jsx("dd",{children:r.sharedPositive.toFixed(3)})]}),I.jsxs("div",{children:[I.jsx("dt",{children:"Shared counterexamples"}),I.jsx("dd",{children:r.sharedNegative.toFixed(3)})]})]}),I.jsx("small",{children:r.contextCompatible?"Matching environment and bounds":"Different environment or bounds · overlap credit is zero"})]},r.recordId)}function kv(r){const d=r.result;return d?I.jsxs("div",{className:"corpus-results",children:[I.jsxs("p",{children:[d.exact?"Exact ranking":"Approximate candidates"," · ",d.candidateCount," eligible candidates · weights ",d.weights.join(" / ")]}),I.jsx("p",{className:"hint",children:"Retrieval candidates only. Matching samples and high similarity do not prove equivalence."}),I.jsx("ol",{children:d.results.map(Jv)}),I.jsxs("details",{children:[I.jsx("summary",{children:"Embedding profile and query identity"}),I.jsx("p",{children:"3072 dimensions · context / predicate / examples / counterexamples"}),I.jsx("code",{children:d.modelId}),I.jsxs("p",{children:["Query: ",I.jsx("code",{children:d.queryRecordId})]})]})]}):null}function $v(r){const d=Qv();return I.jsxs("section",{className:"panel corpus","aria-labelledby":"corpus-title",children:[I.jsxs("div",{className:"panel-title",children:[I.jsxs("div",{children:[I.jsx("span",{className:"panel-index",children:"04"}),I.jsx("h2",{id:"corpus-title",children:"Predicate corpus"})]}),I.jsx("span",{children:"LOCAL RETRIEVAL"})]}),I.jsx("p",{children:"Explore anonymous predicates with checked e-graph representatives and both witness polarities."}),I.jsxs("div",{className:"corpus-controls",children:[I.jsx("button",{className:"secondary",disabled:d.busy,onClick:Xv.bind(null,d,r.token),children:"Load corpus"}),I.jsx("label",{htmlFor:"corpus-record",children:"Query predicate"}),I.jsxs("select",{id:"corpus-record",value:d.selected,onChange:Zv.bind(null,d),disabled:!d.records.length,children:[!d.records.length&&I.jsx("option",{value:"",children:"Load eligible records"}),d.records.map(Kv)]}),I.jsx("button",{className:"primary",disabled:d.busy||!d.selected,onClick:Vv.bind(null,d,r.token),children:"Find related predicates"})]}),d.status&&I.jsxs("p",{className:"corpus-counts",children:[d.status.full," full pools · ",d.status.vectors," embeddings · ",d.status.revoked," revoked records"]}),I.jsx("p",{role:"status","aria-live":"polite",children:d.notice}),I.jsx(kv,{result:d.result})]})}function Wv(r){return I.jsxs("div",{className:"allow-app",children:[I.jsxs("nav",{className:"allow-navigation","aria-label":"Workspace sections",children:[I.jsx("a",{href:"#editor",children:"Editor"}),I.jsx("a",{href:"#predicate-library",children:"Predicate library"}),I.jsx("span",{children:"Local workspace"})]}),I.jsx("div",{id:"editor",children:I.jsx(Uv,{token:r.token})}),I.jsx("aside",{id:"predicate-library",className:"allow-library","aria-label":"Private predicate retrieval",children:I.jsx($v,{token:r.token})})]})}function Fv(){const r=new URLSearchParams(window.location.hash.slice(1)).get("token")??"";return history.replaceState(null,"",window.location.pathname+window.location.search),r}const Lc=`{
  "module": {
    "version": 1,
    "signatures": [
      {
        "tag": "signature",
        "id": "server:00000000-0000-4000-8000-000000001000",
        "name": "A",
        "multiplicity": "set"
      },
      {
        "tag": "signature",
        "id": "server:00000000-0000-4000-8000-000000001001",
        "name": "B",
        "multiplicity": "set"
      }
    ],
    "fields": [],
    "predicates": [
      {
        "tag": "predicate",
        "id": "server:00000000-0000-4000-8000-000000001002",
        "name": "model",
        "parameters": [],
        "bodyId": "draft:00000000-0000-4000-8000-0000000001f4"
      }
    ],
    "facts": [],
    "assertions": [],
    "commands": [
      {
        "tag": "run",
        "id": "server:00000000-0000-4000-8000-000000001003",
        "targetId": "server:00000000-0000-4000-8000-000000001002",
        "uniformScope": 3,
        "bitwidth": 4,
        "maxseq": 3
      }
    ],
    "nodes": [
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000001",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000002",
        "operandId": "draft:00000000-0000-4000-8000-000000000001"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000003",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000004",
        "operandId": "draft:00000000-0000-4000-8000-000000000003"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000005",
        "leftId": "draft:00000000-0000-4000-8000-000000000002",
        "rightId": "draft:00000000-0000-4000-8000-000000000004"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000006",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000007",
        "operandId": "draft:00000000-0000-4000-8000-000000000006"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000008",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000009",
        "operandId": "draft:00000000-0000-4000-8000-000000000008"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000000a",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000000b",
        "operandId": "draft:00000000-0000-4000-8000-00000000000a"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000000c",
        "leftId": "draft:00000000-0000-4000-8000-000000000009",
        "rightId": "draft:00000000-0000-4000-8000-00000000000b"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000000d",
        "leftId": "draft:00000000-0000-4000-8000-000000000007",
        "rightId": "draft:00000000-0000-4000-8000-00000000000c"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000000e",
        "leftId": "draft:00000000-0000-4000-8000-000000000005",
        "rightId": "draft:00000000-0000-4000-8000-00000000000d"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000000f",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000010",
        "operandId": "draft:00000000-0000-4000-8000-00000000000f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000011",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000012",
        "operandId": "draft:00000000-0000-4000-8000-000000000011"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000013",
        "leftId": "draft:00000000-0000-4000-8000-000000000010",
        "rightId": "draft:00000000-0000-4000-8000-000000000012"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000014",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000015",
        "operandId": "draft:00000000-0000-4000-8000-000000000014"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000016",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000017",
        "operandId": "draft:00000000-0000-4000-8000-000000000016"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000018",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000019",
        "operandId": "draft:00000000-0000-4000-8000-000000000018"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000001a",
        "leftId": "draft:00000000-0000-4000-8000-000000000017",
        "rightId": "draft:00000000-0000-4000-8000-000000000019"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000001b",
        "leftId": "draft:00000000-0000-4000-8000-000000000015",
        "rightId": "draft:00000000-0000-4000-8000-00000000001a"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000001c",
        "leftId": "draft:00000000-0000-4000-8000-000000000013",
        "rightId": "draft:00000000-0000-4000-8000-00000000001b"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000001d",
        "leftId": "draft:00000000-0000-4000-8000-00000000000e",
        "rightId": "draft:00000000-0000-4000-8000-00000000001c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000001e",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000001f",
        "operandId": "draft:00000000-0000-4000-8000-00000000001e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000020",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000021",
        "operandId": "draft:00000000-0000-4000-8000-000000000020"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000022",
        "leftId": "draft:00000000-0000-4000-8000-00000000001f",
        "rightId": "draft:00000000-0000-4000-8000-000000000021"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000023",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000024",
        "operandId": "draft:00000000-0000-4000-8000-000000000023"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000025",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000026",
        "operandId": "draft:00000000-0000-4000-8000-000000000025"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000027",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000028",
        "operandId": "draft:00000000-0000-4000-8000-000000000027"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000029",
        "leftId": "draft:00000000-0000-4000-8000-000000000026",
        "rightId": "draft:00000000-0000-4000-8000-000000000028"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000002a",
        "leftId": "draft:00000000-0000-4000-8000-000000000024",
        "rightId": "draft:00000000-0000-4000-8000-000000000029"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000002b",
        "leftId": "draft:00000000-0000-4000-8000-000000000022",
        "rightId": "draft:00000000-0000-4000-8000-00000000002a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000002c",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000002d",
        "operandId": "draft:00000000-0000-4000-8000-00000000002c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000002e",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000002f",
        "operandId": "draft:00000000-0000-4000-8000-00000000002e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000030",
        "leftId": "draft:00000000-0000-4000-8000-00000000002d",
        "rightId": "draft:00000000-0000-4000-8000-00000000002f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000031",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000032",
        "operandId": "draft:00000000-0000-4000-8000-000000000031"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000033",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000034",
        "operandId": "draft:00000000-0000-4000-8000-000000000033"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000035",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000036",
        "operandId": "draft:00000000-0000-4000-8000-000000000035"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000037",
        "leftId": "draft:00000000-0000-4000-8000-000000000034",
        "rightId": "draft:00000000-0000-4000-8000-000000000036"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000038",
        "leftId": "draft:00000000-0000-4000-8000-000000000032",
        "rightId": "draft:00000000-0000-4000-8000-000000000037"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000039",
        "leftId": "draft:00000000-0000-4000-8000-000000000030",
        "rightId": "draft:00000000-0000-4000-8000-000000000038"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000003a",
        "leftId": "draft:00000000-0000-4000-8000-00000000002b",
        "rightId": "draft:00000000-0000-4000-8000-000000000039"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000003b",
        "leftId": "draft:00000000-0000-4000-8000-00000000001d",
        "rightId": "draft:00000000-0000-4000-8000-00000000003a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000003c",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000003d",
        "operandId": "draft:00000000-0000-4000-8000-00000000003c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000003e",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000003f",
        "operandId": "draft:00000000-0000-4000-8000-00000000003e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000040",
        "leftId": "draft:00000000-0000-4000-8000-00000000003d",
        "rightId": "draft:00000000-0000-4000-8000-00000000003f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000041",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000042",
        "operandId": "draft:00000000-0000-4000-8000-000000000041"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000043",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000044",
        "operandId": "draft:00000000-0000-4000-8000-000000000043"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000045",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000046",
        "operandId": "draft:00000000-0000-4000-8000-000000000045"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000047",
        "leftId": "draft:00000000-0000-4000-8000-000000000044",
        "rightId": "draft:00000000-0000-4000-8000-000000000046"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000048",
        "leftId": "draft:00000000-0000-4000-8000-000000000042",
        "rightId": "draft:00000000-0000-4000-8000-000000000047"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000049",
        "leftId": "draft:00000000-0000-4000-8000-000000000040",
        "rightId": "draft:00000000-0000-4000-8000-000000000048"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000004a",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000004b",
        "operandId": "draft:00000000-0000-4000-8000-00000000004a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000004c",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000004d",
        "operandId": "draft:00000000-0000-4000-8000-00000000004c"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000004e",
        "leftId": "draft:00000000-0000-4000-8000-00000000004b",
        "rightId": "draft:00000000-0000-4000-8000-00000000004d"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000004f",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000050",
        "operandId": "draft:00000000-0000-4000-8000-00000000004f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000051",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000052",
        "operandId": "draft:00000000-0000-4000-8000-000000000051"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000053",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000054",
        "operandId": "draft:00000000-0000-4000-8000-000000000053"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000055",
        "leftId": "draft:00000000-0000-4000-8000-000000000052",
        "rightId": "draft:00000000-0000-4000-8000-000000000054"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000056",
        "leftId": "draft:00000000-0000-4000-8000-000000000050",
        "rightId": "draft:00000000-0000-4000-8000-000000000055"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000057",
        "leftId": "draft:00000000-0000-4000-8000-00000000004e",
        "rightId": "draft:00000000-0000-4000-8000-000000000056"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000058",
        "leftId": "draft:00000000-0000-4000-8000-000000000049",
        "rightId": "draft:00000000-0000-4000-8000-000000000057"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000059",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000005a",
        "operandId": "draft:00000000-0000-4000-8000-000000000059"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000005b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000005c",
        "operandId": "draft:00000000-0000-4000-8000-00000000005b"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000005d",
        "leftId": "draft:00000000-0000-4000-8000-00000000005a",
        "rightId": "draft:00000000-0000-4000-8000-00000000005c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000005e",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000005f",
        "operandId": "draft:00000000-0000-4000-8000-00000000005e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000060",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000061",
        "operandId": "draft:00000000-0000-4000-8000-000000000060"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000062",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000063",
        "operandId": "draft:00000000-0000-4000-8000-000000000062"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000064",
        "leftId": "draft:00000000-0000-4000-8000-000000000061",
        "rightId": "draft:00000000-0000-4000-8000-000000000063"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000065",
        "leftId": "draft:00000000-0000-4000-8000-00000000005f",
        "rightId": "draft:00000000-0000-4000-8000-000000000064"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000066",
        "leftId": "draft:00000000-0000-4000-8000-00000000005d",
        "rightId": "draft:00000000-0000-4000-8000-000000000065"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000067",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000068",
        "operandId": "draft:00000000-0000-4000-8000-000000000067"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000069",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000006a",
        "operandId": "draft:00000000-0000-4000-8000-000000000069"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000006b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000006c",
        "operandId": "draft:00000000-0000-4000-8000-00000000006b"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000006d",
        "leftId": "draft:00000000-0000-4000-8000-00000000006a",
        "rightId": "draft:00000000-0000-4000-8000-00000000006c"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000006e",
        "leftId": "draft:00000000-0000-4000-8000-000000000068",
        "rightId": "draft:00000000-0000-4000-8000-00000000006d"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000006f",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000070",
        "operandId": "draft:00000000-0000-4000-8000-00000000006f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000071",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000072",
        "operandId": "draft:00000000-0000-4000-8000-000000000071"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000073",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000074",
        "operandId": "draft:00000000-0000-4000-8000-000000000073"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000075",
        "leftId": "draft:00000000-0000-4000-8000-000000000072",
        "rightId": "draft:00000000-0000-4000-8000-000000000074"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000076",
        "leftId": "draft:00000000-0000-4000-8000-000000000070",
        "rightId": "draft:00000000-0000-4000-8000-000000000075"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000077",
        "leftId": "draft:00000000-0000-4000-8000-00000000006e",
        "rightId": "draft:00000000-0000-4000-8000-000000000076"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000078",
        "leftId": "draft:00000000-0000-4000-8000-000000000066",
        "rightId": "draft:00000000-0000-4000-8000-000000000077"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000079",
        "leftId": "draft:00000000-0000-4000-8000-000000000058",
        "rightId": "draft:00000000-0000-4000-8000-000000000078"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000007a",
        "leftId": "draft:00000000-0000-4000-8000-00000000003b",
        "rightId": "draft:00000000-0000-4000-8000-000000000079"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000007b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000007c",
        "operandId": "draft:00000000-0000-4000-8000-00000000007b"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000007d",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000007e",
        "operandId": "draft:00000000-0000-4000-8000-00000000007d"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000007f",
        "leftId": "draft:00000000-0000-4000-8000-00000000007c",
        "rightId": "draft:00000000-0000-4000-8000-00000000007e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000080",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000081",
        "operandId": "draft:00000000-0000-4000-8000-000000000080"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000082",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000083",
        "operandId": "draft:00000000-0000-4000-8000-000000000082"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000084",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000085",
        "operandId": "draft:00000000-0000-4000-8000-000000000084"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000086",
        "leftId": "draft:00000000-0000-4000-8000-000000000083",
        "rightId": "draft:00000000-0000-4000-8000-000000000085"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000087",
        "leftId": "draft:00000000-0000-4000-8000-000000000081",
        "rightId": "draft:00000000-0000-4000-8000-000000000086"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000088",
        "leftId": "draft:00000000-0000-4000-8000-00000000007f",
        "rightId": "draft:00000000-0000-4000-8000-000000000087"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000089",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000008a",
        "operandId": "draft:00000000-0000-4000-8000-000000000089"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000008b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000008c",
        "operandId": "draft:00000000-0000-4000-8000-00000000008b"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000008d",
        "leftId": "draft:00000000-0000-4000-8000-00000000008a",
        "rightId": "draft:00000000-0000-4000-8000-00000000008c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000008e",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000008f",
        "operandId": "draft:00000000-0000-4000-8000-00000000008e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000090",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000091",
        "operandId": "draft:00000000-0000-4000-8000-000000000090"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000092",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000093",
        "operandId": "draft:00000000-0000-4000-8000-000000000092"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000094",
        "leftId": "draft:00000000-0000-4000-8000-000000000091",
        "rightId": "draft:00000000-0000-4000-8000-000000000093"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000095",
        "leftId": "draft:00000000-0000-4000-8000-00000000008f",
        "rightId": "draft:00000000-0000-4000-8000-000000000094"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000096",
        "leftId": "draft:00000000-0000-4000-8000-00000000008d",
        "rightId": "draft:00000000-0000-4000-8000-000000000095"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000097",
        "leftId": "draft:00000000-0000-4000-8000-000000000088",
        "rightId": "draft:00000000-0000-4000-8000-000000000096"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000098",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000099",
        "operandId": "draft:00000000-0000-4000-8000-000000000098"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000009a",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000009b",
        "operandId": "draft:00000000-0000-4000-8000-00000000009a"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000009c",
        "leftId": "draft:00000000-0000-4000-8000-000000000099",
        "rightId": "draft:00000000-0000-4000-8000-00000000009b"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000009d",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000009e",
        "operandId": "draft:00000000-0000-4000-8000-00000000009d"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000009f",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000a0",
        "operandId": "draft:00000000-0000-4000-8000-00000000009f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000a1",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000a2",
        "operandId": "draft:00000000-0000-4000-8000-0000000000a1"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000a3",
        "leftId": "draft:00000000-0000-4000-8000-0000000000a0",
        "rightId": "draft:00000000-0000-4000-8000-0000000000a2"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000a4",
        "leftId": "draft:00000000-0000-4000-8000-00000000009e",
        "rightId": "draft:00000000-0000-4000-8000-0000000000a3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000a5",
        "leftId": "draft:00000000-0000-4000-8000-00000000009c",
        "rightId": "draft:00000000-0000-4000-8000-0000000000a4"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000a6",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000a7",
        "operandId": "draft:00000000-0000-4000-8000-0000000000a6"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000a8",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000a9",
        "operandId": "draft:00000000-0000-4000-8000-0000000000a8"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000aa",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000ab",
        "operandId": "draft:00000000-0000-4000-8000-0000000000aa"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000ac",
        "leftId": "draft:00000000-0000-4000-8000-0000000000a9",
        "rightId": "draft:00000000-0000-4000-8000-0000000000ab"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000ad",
        "leftId": "draft:00000000-0000-4000-8000-0000000000a7",
        "rightId": "draft:00000000-0000-4000-8000-0000000000ac"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000ae",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000af",
        "operandId": "draft:00000000-0000-4000-8000-0000000000ae"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000b0",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000b1",
        "operandId": "draft:00000000-0000-4000-8000-0000000000b0"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000b2",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000b3",
        "operandId": "draft:00000000-0000-4000-8000-0000000000b2"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000b4",
        "leftId": "draft:00000000-0000-4000-8000-0000000000b1",
        "rightId": "draft:00000000-0000-4000-8000-0000000000b3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000b5",
        "leftId": "draft:00000000-0000-4000-8000-0000000000af",
        "rightId": "draft:00000000-0000-4000-8000-0000000000b4"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000b6",
        "leftId": "draft:00000000-0000-4000-8000-0000000000ad",
        "rightId": "draft:00000000-0000-4000-8000-0000000000b5"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000b7",
        "leftId": "draft:00000000-0000-4000-8000-0000000000a5",
        "rightId": "draft:00000000-0000-4000-8000-0000000000b6"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000b8",
        "leftId": "draft:00000000-0000-4000-8000-000000000097",
        "rightId": "draft:00000000-0000-4000-8000-0000000000b7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000b9",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000ba",
        "operandId": "draft:00000000-0000-4000-8000-0000000000b9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000bb",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000bc",
        "operandId": "draft:00000000-0000-4000-8000-0000000000bb"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000bd",
        "leftId": "draft:00000000-0000-4000-8000-0000000000ba",
        "rightId": "draft:00000000-0000-4000-8000-0000000000bc"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000be",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000bf",
        "operandId": "draft:00000000-0000-4000-8000-0000000000be"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000c0",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000c1",
        "operandId": "draft:00000000-0000-4000-8000-0000000000c0"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000c2",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000c3",
        "operandId": "draft:00000000-0000-4000-8000-0000000000c2"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000c4",
        "leftId": "draft:00000000-0000-4000-8000-0000000000c1",
        "rightId": "draft:00000000-0000-4000-8000-0000000000c3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000c5",
        "leftId": "draft:00000000-0000-4000-8000-0000000000bf",
        "rightId": "draft:00000000-0000-4000-8000-0000000000c4"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000c6",
        "leftId": "draft:00000000-0000-4000-8000-0000000000bd",
        "rightId": "draft:00000000-0000-4000-8000-0000000000c5"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000c7",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000c8",
        "operandId": "draft:00000000-0000-4000-8000-0000000000c7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000c9",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000ca",
        "operandId": "draft:00000000-0000-4000-8000-0000000000c9"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000cb",
        "leftId": "draft:00000000-0000-4000-8000-0000000000c8",
        "rightId": "draft:00000000-0000-4000-8000-0000000000ca"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000cc",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000cd",
        "operandId": "draft:00000000-0000-4000-8000-0000000000cc"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000ce",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000cf",
        "operandId": "draft:00000000-0000-4000-8000-0000000000ce"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000d0",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000d1",
        "operandId": "draft:00000000-0000-4000-8000-0000000000d0"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000d2",
        "leftId": "draft:00000000-0000-4000-8000-0000000000cf",
        "rightId": "draft:00000000-0000-4000-8000-0000000000d1"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000d3",
        "leftId": "draft:00000000-0000-4000-8000-0000000000cd",
        "rightId": "draft:00000000-0000-4000-8000-0000000000d2"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000d4",
        "leftId": "draft:00000000-0000-4000-8000-0000000000cb",
        "rightId": "draft:00000000-0000-4000-8000-0000000000d3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000d5",
        "leftId": "draft:00000000-0000-4000-8000-0000000000c6",
        "rightId": "draft:00000000-0000-4000-8000-0000000000d4"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000d6",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000d7",
        "operandId": "draft:00000000-0000-4000-8000-0000000000d6"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000d8",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000d9",
        "operandId": "draft:00000000-0000-4000-8000-0000000000d8"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000da",
        "leftId": "draft:00000000-0000-4000-8000-0000000000d7",
        "rightId": "draft:00000000-0000-4000-8000-0000000000d9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000db",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000dc",
        "operandId": "draft:00000000-0000-4000-8000-0000000000db"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000dd",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000de",
        "operandId": "draft:00000000-0000-4000-8000-0000000000dd"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000df",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000e0",
        "operandId": "draft:00000000-0000-4000-8000-0000000000df"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000e1",
        "leftId": "draft:00000000-0000-4000-8000-0000000000de",
        "rightId": "draft:00000000-0000-4000-8000-0000000000e0"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000e2",
        "leftId": "draft:00000000-0000-4000-8000-0000000000dc",
        "rightId": "draft:00000000-0000-4000-8000-0000000000e1"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000e3",
        "leftId": "draft:00000000-0000-4000-8000-0000000000da",
        "rightId": "draft:00000000-0000-4000-8000-0000000000e2"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000e4",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000e5",
        "operandId": "draft:00000000-0000-4000-8000-0000000000e4"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000e6",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000e7",
        "operandId": "draft:00000000-0000-4000-8000-0000000000e6"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000e8",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000e9",
        "operandId": "draft:00000000-0000-4000-8000-0000000000e8"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000ea",
        "leftId": "draft:00000000-0000-4000-8000-0000000000e7",
        "rightId": "draft:00000000-0000-4000-8000-0000000000e9"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000eb",
        "leftId": "draft:00000000-0000-4000-8000-0000000000e5",
        "rightId": "draft:00000000-0000-4000-8000-0000000000ea"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000ec",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000ed",
        "operandId": "draft:00000000-0000-4000-8000-0000000000ec"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000ee",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000ef",
        "operandId": "draft:00000000-0000-4000-8000-0000000000ee"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000f0",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000f1",
        "operandId": "draft:00000000-0000-4000-8000-0000000000f0"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f2",
        "leftId": "draft:00000000-0000-4000-8000-0000000000ef",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f1"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f3",
        "leftId": "draft:00000000-0000-4000-8000-0000000000ed",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f2"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f4",
        "leftId": "draft:00000000-0000-4000-8000-0000000000eb",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f5",
        "leftId": "draft:00000000-0000-4000-8000-0000000000e3",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f4"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f6",
        "leftId": "draft:00000000-0000-4000-8000-0000000000d5",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f5"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f7",
        "leftId": "draft:00000000-0000-4000-8000-0000000000b8",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f6"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000f8",
        "leftId": "draft:00000000-0000-4000-8000-00000000007a",
        "rightId": "draft:00000000-0000-4000-8000-0000000000f7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000f9",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000fa",
        "operandId": "draft:00000000-0000-4000-8000-0000000000f9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000fb",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000fc",
        "operandId": "draft:00000000-0000-4000-8000-0000000000fb"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000000fd",
        "leftId": "draft:00000000-0000-4000-8000-0000000000fa",
        "rightId": "draft:00000000-0000-4000-8000-0000000000fc"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000000fe",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000000ff",
        "operandId": "draft:00000000-0000-4000-8000-0000000000fe"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000100",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000101",
        "operandId": "draft:00000000-0000-4000-8000-000000000100"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000102",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000103",
        "operandId": "draft:00000000-0000-4000-8000-000000000102"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000104",
        "leftId": "draft:00000000-0000-4000-8000-000000000101",
        "rightId": "draft:00000000-0000-4000-8000-000000000103"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000105",
        "leftId": "draft:00000000-0000-4000-8000-0000000000ff",
        "rightId": "draft:00000000-0000-4000-8000-000000000104"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000106",
        "leftId": "draft:00000000-0000-4000-8000-0000000000fd",
        "rightId": "draft:00000000-0000-4000-8000-000000000105"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000107",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000108",
        "operandId": "draft:00000000-0000-4000-8000-000000000107"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000109",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000010a",
        "operandId": "draft:00000000-0000-4000-8000-000000000109"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000010b",
        "leftId": "draft:00000000-0000-4000-8000-000000000108",
        "rightId": "draft:00000000-0000-4000-8000-00000000010a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000010c",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000010d",
        "operandId": "draft:00000000-0000-4000-8000-00000000010c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000010e",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000010f",
        "operandId": "draft:00000000-0000-4000-8000-00000000010e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000110",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000111",
        "operandId": "draft:00000000-0000-4000-8000-000000000110"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000112",
        "leftId": "draft:00000000-0000-4000-8000-00000000010f",
        "rightId": "draft:00000000-0000-4000-8000-000000000111"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000113",
        "leftId": "draft:00000000-0000-4000-8000-00000000010d",
        "rightId": "draft:00000000-0000-4000-8000-000000000112"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000114",
        "leftId": "draft:00000000-0000-4000-8000-00000000010b",
        "rightId": "draft:00000000-0000-4000-8000-000000000113"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000115",
        "leftId": "draft:00000000-0000-4000-8000-000000000106",
        "rightId": "draft:00000000-0000-4000-8000-000000000114"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000116",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000117",
        "operandId": "draft:00000000-0000-4000-8000-000000000116"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000118",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000119",
        "operandId": "draft:00000000-0000-4000-8000-000000000118"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000011a",
        "leftId": "draft:00000000-0000-4000-8000-000000000117",
        "rightId": "draft:00000000-0000-4000-8000-000000000119"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000011b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000011c",
        "operandId": "draft:00000000-0000-4000-8000-00000000011b"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000011d",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000011e",
        "operandId": "draft:00000000-0000-4000-8000-00000000011d"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000011f",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000120",
        "operandId": "draft:00000000-0000-4000-8000-00000000011f"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000121",
        "leftId": "draft:00000000-0000-4000-8000-00000000011e",
        "rightId": "draft:00000000-0000-4000-8000-000000000120"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000122",
        "leftId": "draft:00000000-0000-4000-8000-00000000011c",
        "rightId": "draft:00000000-0000-4000-8000-000000000121"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000123",
        "leftId": "draft:00000000-0000-4000-8000-00000000011a",
        "rightId": "draft:00000000-0000-4000-8000-000000000122"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000124",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000125",
        "operandId": "draft:00000000-0000-4000-8000-000000000124"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000126",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000127",
        "operandId": "draft:00000000-0000-4000-8000-000000000126"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000128",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000129",
        "operandId": "draft:00000000-0000-4000-8000-000000000128"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000012a",
        "leftId": "draft:00000000-0000-4000-8000-000000000127",
        "rightId": "draft:00000000-0000-4000-8000-000000000129"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000012b",
        "leftId": "draft:00000000-0000-4000-8000-000000000125",
        "rightId": "draft:00000000-0000-4000-8000-00000000012a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000012c",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000012d",
        "operandId": "draft:00000000-0000-4000-8000-00000000012c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000012e",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000012f",
        "operandId": "draft:00000000-0000-4000-8000-00000000012e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000130",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000131",
        "operandId": "draft:00000000-0000-4000-8000-000000000130"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000132",
        "leftId": "draft:00000000-0000-4000-8000-00000000012f",
        "rightId": "draft:00000000-0000-4000-8000-000000000131"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000133",
        "leftId": "draft:00000000-0000-4000-8000-00000000012d",
        "rightId": "draft:00000000-0000-4000-8000-000000000132"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000134",
        "leftId": "draft:00000000-0000-4000-8000-00000000012b",
        "rightId": "draft:00000000-0000-4000-8000-000000000133"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000135",
        "leftId": "draft:00000000-0000-4000-8000-000000000123",
        "rightId": "draft:00000000-0000-4000-8000-000000000134"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000136",
        "leftId": "draft:00000000-0000-4000-8000-000000000115",
        "rightId": "draft:00000000-0000-4000-8000-000000000135"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000137",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000138",
        "operandId": "draft:00000000-0000-4000-8000-000000000137"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000139",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000013a",
        "operandId": "draft:00000000-0000-4000-8000-000000000139"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000013b",
        "leftId": "draft:00000000-0000-4000-8000-000000000138",
        "rightId": "draft:00000000-0000-4000-8000-00000000013a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000013c",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000013d",
        "operandId": "draft:00000000-0000-4000-8000-00000000013c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000013e",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000013f",
        "operandId": "draft:00000000-0000-4000-8000-00000000013e"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000140",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000141",
        "operandId": "draft:00000000-0000-4000-8000-000000000140"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000142",
        "leftId": "draft:00000000-0000-4000-8000-00000000013f",
        "rightId": "draft:00000000-0000-4000-8000-000000000141"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000143",
        "leftId": "draft:00000000-0000-4000-8000-00000000013d",
        "rightId": "draft:00000000-0000-4000-8000-000000000142"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000144",
        "leftId": "draft:00000000-0000-4000-8000-00000000013b",
        "rightId": "draft:00000000-0000-4000-8000-000000000143"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000145",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000146",
        "operandId": "draft:00000000-0000-4000-8000-000000000145"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000147",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000148",
        "operandId": "draft:00000000-0000-4000-8000-000000000147"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000149",
        "leftId": "draft:00000000-0000-4000-8000-000000000146",
        "rightId": "draft:00000000-0000-4000-8000-000000000148"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000014a",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000014b",
        "operandId": "draft:00000000-0000-4000-8000-00000000014a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000014c",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000014d",
        "operandId": "draft:00000000-0000-4000-8000-00000000014c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000014e",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000014f",
        "operandId": "draft:00000000-0000-4000-8000-00000000014e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000150",
        "leftId": "draft:00000000-0000-4000-8000-00000000014d",
        "rightId": "draft:00000000-0000-4000-8000-00000000014f"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000151",
        "leftId": "draft:00000000-0000-4000-8000-00000000014b",
        "rightId": "draft:00000000-0000-4000-8000-000000000150"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000152",
        "leftId": "draft:00000000-0000-4000-8000-000000000149",
        "rightId": "draft:00000000-0000-4000-8000-000000000151"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000153",
        "leftId": "draft:00000000-0000-4000-8000-000000000144",
        "rightId": "draft:00000000-0000-4000-8000-000000000152"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000154",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000155",
        "operandId": "draft:00000000-0000-4000-8000-000000000154"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000156",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000157",
        "operandId": "draft:00000000-0000-4000-8000-000000000156"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000158",
        "leftId": "draft:00000000-0000-4000-8000-000000000155",
        "rightId": "draft:00000000-0000-4000-8000-000000000157"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000159",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000015a",
        "operandId": "draft:00000000-0000-4000-8000-000000000159"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000015b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000015c",
        "operandId": "draft:00000000-0000-4000-8000-00000000015b"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000015d",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000015e",
        "operandId": "draft:00000000-0000-4000-8000-00000000015d"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000015f",
        "leftId": "draft:00000000-0000-4000-8000-00000000015c",
        "rightId": "draft:00000000-0000-4000-8000-00000000015e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000160",
        "leftId": "draft:00000000-0000-4000-8000-00000000015a",
        "rightId": "draft:00000000-0000-4000-8000-00000000015f"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000161",
        "leftId": "draft:00000000-0000-4000-8000-000000000158",
        "rightId": "draft:00000000-0000-4000-8000-000000000160"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000162",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000163",
        "operandId": "draft:00000000-0000-4000-8000-000000000162"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000164",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000165",
        "operandId": "draft:00000000-0000-4000-8000-000000000164"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000166",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000167",
        "operandId": "draft:00000000-0000-4000-8000-000000000166"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000168",
        "leftId": "draft:00000000-0000-4000-8000-000000000165",
        "rightId": "draft:00000000-0000-4000-8000-000000000167"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000169",
        "leftId": "draft:00000000-0000-4000-8000-000000000163",
        "rightId": "draft:00000000-0000-4000-8000-000000000168"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000016a",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000016b",
        "operandId": "draft:00000000-0000-4000-8000-00000000016a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000016c",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000016d",
        "operandId": "draft:00000000-0000-4000-8000-00000000016c"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000016e",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000016f",
        "operandId": "draft:00000000-0000-4000-8000-00000000016e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000170",
        "leftId": "draft:00000000-0000-4000-8000-00000000016d",
        "rightId": "draft:00000000-0000-4000-8000-00000000016f"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000171",
        "leftId": "draft:00000000-0000-4000-8000-00000000016b",
        "rightId": "draft:00000000-0000-4000-8000-000000000170"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000172",
        "leftId": "draft:00000000-0000-4000-8000-000000000169",
        "rightId": "draft:00000000-0000-4000-8000-000000000171"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000173",
        "leftId": "draft:00000000-0000-4000-8000-000000000161",
        "rightId": "draft:00000000-0000-4000-8000-000000000172"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000174",
        "leftId": "draft:00000000-0000-4000-8000-000000000153",
        "rightId": "draft:00000000-0000-4000-8000-000000000173"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000175",
        "leftId": "draft:00000000-0000-4000-8000-000000000136",
        "rightId": "draft:00000000-0000-4000-8000-000000000174"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000176",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000177",
        "operandId": "draft:00000000-0000-4000-8000-000000000176"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000178",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000179",
        "operandId": "draft:00000000-0000-4000-8000-000000000178"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000017a",
        "leftId": "draft:00000000-0000-4000-8000-000000000177",
        "rightId": "draft:00000000-0000-4000-8000-000000000179"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000017b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000017c",
        "operandId": "draft:00000000-0000-4000-8000-00000000017b"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000017d",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000017e",
        "operandId": "draft:00000000-0000-4000-8000-00000000017d"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000017f",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000180",
        "operandId": "draft:00000000-0000-4000-8000-00000000017f"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000181",
        "leftId": "draft:00000000-0000-4000-8000-00000000017e",
        "rightId": "draft:00000000-0000-4000-8000-000000000180"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000182",
        "leftId": "draft:00000000-0000-4000-8000-00000000017c",
        "rightId": "draft:00000000-0000-4000-8000-000000000181"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000183",
        "leftId": "draft:00000000-0000-4000-8000-00000000017a",
        "rightId": "draft:00000000-0000-4000-8000-000000000182"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000184",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000185",
        "operandId": "draft:00000000-0000-4000-8000-000000000184"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000186",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000187",
        "operandId": "draft:00000000-0000-4000-8000-000000000186"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000188",
        "leftId": "draft:00000000-0000-4000-8000-000000000185",
        "rightId": "draft:00000000-0000-4000-8000-000000000187"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000189",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000018a",
        "operandId": "draft:00000000-0000-4000-8000-000000000189"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000018b",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000018c",
        "operandId": "draft:00000000-0000-4000-8000-00000000018b"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000018d",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000018e",
        "operandId": "draft:00000000-0000-4000-8000-00000000018d"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000018f",
        "leftId": "draft:00000000-0000-4000-8000-00000000018c",
        "rightId": "draft:00000000-0000-4000-8000-00000000018e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000190",
        "leftId": "draft:00000000-0000-4000-8000-00000000018a",
        "rightId": "draft:00000000-0000-4000-8000-00000000018f"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000191",
        "leftId": "draft:00000000-0000-4000-8000-000000000188",
        "rightId": "draft:00000000-0000-4000-8000-000000000190"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000192",
        "leftId": "draft:00000000-0000-4000-8000-000000000183",
        "rightId": "draft:00000000-0000-4000-8000-000000000191"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000193",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000194",
        "operandId": "draft:00000000-0000-4000-8000-000000000193"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000195",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000196",
        "operandId": "draft:00000000-0000-4000-8000-000000000195"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-000000000197",
        "leftId": "draft:00000000-0000-4000-8000-000000000194",
        "rightId": "draft:00000000-0000-4000-8000-000000000196"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-000000000198",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-000000000199",
        "operandId": "draft:00000000-0000-4000-8000-000000000198"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000019a",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000019b",
        "operandId": "draft:00000000-0000-4000-8000-00000000019a"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-00000000019c",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-00000000019d",
        "operandId": "draft:00000000-0000-4000-8000-00000000019c"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000019e",
        "leftId": "draft:00000000-0000-4000-8000-00000000019b",
        "rightId": "draft:00000000-0000-4000-8000-00000000019d"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-00000000019f",
        "leftId": "draft:00000000-0000-4000-8000-000000000199",
        "rightId": "draft:00000000-0000-4000-8000-00000000019e"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001a0",
        "leftId": "draft:00000000-0000-4000-8000-000000000197",
        "rightId": "draft:00000000-0000-4000-8000-00000000019f"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001a1",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001a2",
        "operandId": "draft:00000000-0000-4000-8000-0000000001a1"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001a3",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001a4",
        "operandId": "draft:00000000-0000-4000-8000-0000000001a3"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001a5",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001a6",
        "operandId": "draft:00000000-0000-4000-8000-0000000001a5"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001a7",
        "leftId": "draft:00000000-0000-4000-8000-0000000001a4",
        "rightId": "draft:00000000-0000-4000-8000-0000000001a6"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001a8",
        "leftId": "draft:00000000-0000-4000-8000-0000000001a2",
        "rightId": "draft:00000000-0000-4000-8000-0000000001a7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001a9",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001aa",
        "operandId": "draft:00000000-0000-4000-8000-0000000001a9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001ab",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001ac",
        "operandId": "draft:00000000-0000-4000-8000-0000000001ab"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001ad",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001ae",
        "operandId": "draft:00000000-0000-4000-8000-0000000001ad"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001af",
        "leftId": "draft:00000000-0000-4000-8000-0000000001ac",
        "rightId": "draft:00000000-0000-4000-8000-0000000001ae"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001b0",
        "leftId": "draft:00000000-0000-4000-8000-0000000001aa",
        "rightId": "draft:00000000-0000-4000-8000-0000000001af"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001b1",
        "leftId": "draft:00000000-0000-4000-8000-0000000001a8",
        "rightId": "draft:00000000-0000-4000-8000-0000000001b0"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001b2",
        "leftId": "draft:00000000-0000-4000-8000-0000000001a0",
        "rightId": "draft:00000000-0000-4000-8000-0000000001b1"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001b3",
        "leftId": "draft:00000000-0000-4000-8000-000000000192",
        "rightId": "draft:00000000-0000-4000-8000-0000000001b2"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001b4",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001b5",
        "operandId": "draft:00000000-0000-4000-8000-0000000001b4"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001b6",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001b7",
        "operandId": "draft:00000000-0000-4000-8000-0000000001b6"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001b8",
        "leftId": "draft:00000000-0000-4000-8000-0000000001b5",
        "rightId": "draft:00000000-0000-4000-8000-0000000001b7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001b9",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001ba",
        "operandId": "draft:00000000-0000-4000-8000-0000000001b9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001bb",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001bc",
        "operandId": "draft:00000000-0000-4000-8000-0000000001bb"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001bd",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001be",
        "operandId": "draft:00000000-0000-4000-8000-0000000001bd"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001bf",
        "leftId": "draft:00000000-0000-4000-8000-0000000001bc",
        "rightId": "draft:00000000-0000-4000-8000-0000000001be"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001c0",
        "leftId": "draft:00000000-0000-4000-8000-0000000001ba",
        "rightId": "draft:00000000-0000-4000-8000-0000000001bf"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001c1",
        "leftId": "draft:00000000-0000-4000-8000-0000000001b8",
        "rightId": "draft:00000000-0000-4000-8000-0000000001c0"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001c2",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001c3",
        "operandId": "draft:00000000-0000-4000-8000-0000000001c2"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001c4",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001c5",
        "operandId": "draft:00000000-0000-4000-8000-0000000001c4"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001c6",
        "leftId": "draft:00000000-0000-4000-8000-0000000001c3",
        "rightId": "draft:00000000-0000-4000-8000-0000000001c5"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001c7",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001c8",
        "operandId": "draft:00000000-0000-4000-8000-0000000001c7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001c9",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001ca",
        "operandId": "draft:00000000-0000-4000-8000-0000000001c9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001cb",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001cc",
        "operandId": "draft:00000000-0000-4000-8000-0000000001cb"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001cd",
        "leftId": "draft:00000000-0000-4000-8000-0000000001ca",
        "rightId": "draft:00000000-0000-4000-8000-0000000001cc"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001ce",
        "leftId": "draft:00000000-0000-4000-8000-0000000001c8",
        "rightId": "draft:00000000-0000-4000-8000-0000000001cd"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001cf",
        "leftId": "draft:00000000-0000-4000-8000-0000000001c6",
        "rightId": "draft:00000000-0000-4000-8000-0000000001ce"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001d0",
        "leftId": "draft:00000000-0000-4000-8000-0000000001c1",
        "rightId": "draft:00000000-0000-4000-8000-0000000001cf"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001d1",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001d2",
        "operandId": "draft:00000000-0000-4000-8000-0000000001d1"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001d3",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001d4",
        "operandId": "draft:00000000-0000-4000-8000-0000000001d3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001d5",
        "leftId": "draft:00000000-0000-4000-8000-0000000001d2",
        "rightId": "draft:00000000-0000-4000-8000-0000000001d4"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001d6",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001d7",
        "operandId": "draft:00000000-0000-4000-8000-0000000001d6"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001d8",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001d9",
        "operandId": "draft:00000000-0000-4000-8000-0000000001d8"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001da",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001db",
        "operandId": "draft:00000000-0000-4000-8000-0000000001da"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001dc",
        "leftId": "draft:00000000-0000-4000-8000-0000000001d9",
        "rightId": "draft:00000000-0000-4000-8000-0000000001db"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001dd",
        "leftId": "draft:00000000-0000-4000-8000-0000000001d7",
        "rightId": "draft:00000000-0000-4000-8000-0000000001dc"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001de",
        "leftId": "draft:00000000-0000-4000-8000-0000000001d5",
        "rightId": "draft:00000000-0000-4000-8000-0000000001dd"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001df",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001e0",
        "operandId": "draft:00000000-0000-4000-8000-0000000001df"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001e1",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001e2",
        "operandId": "draft:00000000-0000-4000-8000-0000000001e1"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001e3",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001e4",
        "operandId": "draft:00000000-0000-4000-8000-0000000001e3"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001e5",
        "leftId": "draft:00000000-0000-4000-8000-0000000001e2",
        "rightId": "draft:00000000-0000-4000-8000-0000000001e4"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001e6",
        "leftId": "draft:00000000-0000-4000-8000-0000000001e0",
        "rightId": "draft:00000000-0000-4000-8000-0000000001e5"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001e7",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001e8",
        "operandId": "draft:00000000-0000-4000-8000-0000000001e7"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001e9",
        "targetId": "server:00000000-0000-4000-8000-000000001001"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001ea",
        "operandId": "draft:00000000-0000-4000-8000-0000000001e9"
      },
      {
        "tag": "signature_ref",
        "id": "draft:00000000-0000-4000-8000-0000000001eb",
        "targetId": "server:00000000-0000-4000-8000-000000001000"
      },
      {
        "tag": "some_test",
        "id": "draft:00000000-0000-4000-8000-0000000001ec",
        "operandId": "draft:00000000-0000-4000-8000-0000000001eb"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001ed",
        "leftId": "draft:00000000-0000-4000-8000-0000000001ea",
        "rightId": "draft:00000000-0000-4000-8000-0000000001ec"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001ee",
        "leftId": "draft:00000000-0000-4000-8000-0000000001e8",
        "rightId": "draft:00000000-0000-4000-8000-0000000001ed"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001ef",
        "leftId": "draft:00000000-0000-4000-8000-0000000001e6",
        "rightId": "draft:00000000-0000-4000-8000-0000000001ee"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001f0",
        "leftId": "draft:00000000-0000-4000-8000-0000000001de",
        "rightId": "draft:00000000-0000-4000-8000-0000000001ef"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001f1",
        "leftId": "draft:00000000-0000-4000-8000-0000000001d0",
        "rightId": "draft:00000000-0000-4000-8000-0000000001f0"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001f2",
        "leftId": "draft:00000000-0000-4000-8000-0000000001b3",
        "rightId": "draft:00000000-0000-4000-8000-0000000001f1"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001f3",
        "leftId": "draft:00000000-0000-4000-8000-000000000175",
        "rightId": "draft:00000000-0000-4000-8000-0000000001f2"
      },
      {
        "tag": "and",
        "id": "draft:00000000-0000-4000-8000-0000000001f4",
        "leftId": "draft:00000000-0000-4000-8000-0000000000f8",
        "rightId": "draft:00000000-0000-4000-8000-0000000001f3"
      }
    ]
  },
  "source": "sig A {}\\nsig B {}\\npred model { ((((((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and (some A)) and ((some B) and ((some A) and (some B))))) and ((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and (some A)) and ((some B) and ((some A) and (some B)))))) and (((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and (some A)) and ((some B) and ((some A) and (some B))))) and ((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and ((some A) and (some B))) and ((some A) and ((some B) and (some A))))))) and ((((((some B) and (some A)) and ((some B) and ((some A) and (some B)))) and (((some A) and (some B)) and ((some A) and ((some B) and (some A))))) and ((((some B) and (some A)) and ((some B) and ((some A) and (some B)))) and (((some A) and ((some B) and (some A))) and ((some B) and ((some A) and (some B)))))) and (((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and (some A)) and ((some B) and ((some A) and (some B))))) and ((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and ((some A) and (some B))) and ((some A) and ((some B) and (some A)))))))) and (((((((some B) and (some A)) and ((some B) and ((some A) and (some B)))) and (((some A) and (some B)) and ((some A) and ((some B) and (some A))))) and ((((some B) and (some A)) and ((some B) and ((some A) and (some B)))) and (((some A) and ((some B) and (some A))) and ((some B) and ((some A) and (some B)))))) and (((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and (some A)) and ((some B) and ((some A) and (some B))))) and ((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and ((some A) and (some B))) and ((some A) and ((some B) and (some A))))))) and ((((((some B) and (some A)) and ((some B) and ((some A) and (some B)))) and (((some A) and (some B)) and ((some A) and ((some B) and (some A))))) and ((((some B) and (some A)) and ((some B) and ((some A) and (some B)))) and (((some A) and ((some B) and (some A))) and ((some B) and ((some A) and (some B)))))) and (((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and (some A)) and ((some B) and ((some A) and (some B))))) and ((((some A) and (some B)) and ((some A) and ((some B) and (some A)))) and (((some B) and ((some A) and (some B))) and ((some A) and ((some B) and (some A))))))))) }\\nrun model for 3 but 4 Int, 3 seq\\n",
  "references": [
    "draft:00000000-0000-4000-8000-000000000001",
    "draft:00000000-0000-4000-8000-000000000003",
    "draft:00000000-0000-4000-8000-000000000006",
    "draft:00000000-0000-4000-8000-000000000008",
    "draft:00000000-0000-4000-8000-00000000000a",
    "draft:00000000-0000-4000-8000-00000000000f",
    "draft:00000000-0000-4000-8000-000000000011",
    "draft:00000000-0000-4000-8000-000000000014",
    "draft:00000000-0000-4000-8000-000000000016",
    "draft:00000000-0000-4000-8000-000000000018",
    "draft:00000000-0000-4000-8000-00000000001e",
    "draft:00000000-0000-4000-8000-000000000020",
    "draft:00000000-0000-4000-8000-000000000023",
    "draft:00000000-0000-4000-8000-000000000025",
    "draft:00000000-0000-4000-8000-000000000027",
    "draft:00000000-0000-4000-8000-00000000002c",
    "draft:00000000-0000-4000-8000-00000000002e",
    "draft:00000000-0000-4000-8000-000000000031",
    "draft:00000000-0000-4000-8000-000000000033",
    "draft:00000000-0000-4000-8000-000000000035",
    "draft:00000000-0000-4000-8000-00000000003c",
    "draft:00000000-0000-4000-8000-00000000003e",
    "draft:00000000-0000-4000-8000-000000000041",
    "draft:00000000-0000-4000-8000-000000000043",
    "draft:00000000-0000-4000-8000-000000000045",
    "draft:00000000-0000-4000-8000-00000000004a",
    "draft:00000000-0000-4000-8000-00000000004c",
    "draft:00000000-0000-4000-8000-00000000004f",
    "draft:00000000-0000-4000-8000-000000000051",
    "draft:00000000-0000-4000-8000-000000000053",
    "draft:00000000-0000-4000-8000-000000000059",
    "draft:00000000-0000-4000-8000-00000000005b",
    "draft:00000000-0000-4000-8000-00000000005e",
    "draft:00000000-0000-4000-8000-000000000060",
    "draft:00000000-0000-4000-8000-000000000062",
    "draft:00000000-0000-4000-8000-000000000067",
    "draft:00000000-0000-4000-8000-000000000069",
    "draft:00000000-0000-4000-8000-00000000006b",
    "draft:00000000-0000-4000-8000-00000000006f",
    "draft:00000000-0000-4000-8000-000000000071",
    "draft:00000000-0000-4000-8000-000000000073",
    "draft:00000000-0000-4000-8000-00000000007b",
    "draft:00000000-0000-4000-8000-00000000007d",
    "draft:00000000-0000-4000-8000-000000000080",
    "draft:00000000-0000-4000-8000-000000000082",
    "draft:00000000-0000-4000-8000-000000000084",
    "draft:00000000-0000-4000-8000-000000000089",
    "draft:00000000-0000-4000-8000-00000000008b",
    "draft:00000000-0000-4000-8000-00000000008e",
    "draft:00000000-0000-4000-8000-000000000090",
    "draft:00000000-0000-4000-8000-000000000092",
    "draft:00000000-0000-4000-8000-000000000098",
    "draft:00000000-0000-4000-8000-00000000009a",
    "draft:00000000-0000-4000-8000-00000000009d",
    "draft:00000000-0000-4000-8000-00000000009f",
    "draft:00000000-0000-4000-8000-0000000000a1",
    "draft:00000000-0000-4000-8000-0000000000a6",
    "draft:00000000-0000-4000-8000-0000000000a8",
    "draft:00000000-0000-4000-8000-0000000000aa",
    "draft:00000000-0000-4000-8000-0000000000ae",
    "draft:00000000-0000-4000-8000-0000000000b0",
    "draft:00000000-0000-4000-8000-0000000000b2",
    "draft:00000000-0000-4000-8000-0000000000b9",
    "draft:00000000-0000-4000-8000-0000000000bb",
    "draft:00000000-0000-4000-8000-0000000000be",
    "draft:00000000-0000-4000-8000-0000000000c0",
    "draft:00000000-0000-4000-8000-0000000000c2",
    "draft:00000000-0000-4000-8000-0000000000c7",
    "draft:00000000-0000-4000-8000-0000000000c9",
    "draft:00000000-0000-4000-8000-0000000000cc",
    "draft:00000000-0000-4000-8000-0000000000ce",
    "draft:00000000-0000-4000-8000-0000000000d0",
    "draft:00000000-0000-4000-8000-0000000000d6",
    "draft:00000000-0000-4000-8000-0000000000d8",
    "draft:00000000-0000-4000-8000-0000000000db",
    "draft:00000000-0000-4000-8000-0000000000dd",
    "draft:00000000-0000-4000-8000-0000000000df",
    "draft:00000000-0000-4000-8000-0000000000e4",
    "draft:00000000-0000-4000-8000-0000000000e6",
    "draft:00000000-0000-4000-8000-0000000000e8",
    "draft:00000000-0000-4000-8000-0000000000ec",
    "draft:00000000-0000-4000-8000-0000000000ee",
    "draft:00000000-0000-4000-8000-0000000000f0",
    "draft:00000000-0000-4000-8000-0000000000f9",
    "draft:00000000-0000-4000-8000-0000000000fb",
    "draft:00000000-0000-4000-8000-0000000000fe",
    "draft:00000000-0000-4000-8000-000000000100",
    "draft:00000000-0000-4000-8000-000000000102",
    "draft:00000000-0000-4000-8000-000000000107",
    "draft:00000000-0000-4000-8000-000000000109",
    "draft:00000000-0000-4000-8000-00000000010c",
    "draft:00000000-0000-4000-8000-00000000010e",
    "draft:00000000-0000-4000-8000-000000000110",
    "draft:00000000-0000-4000-8000-000000000116",
    "draft:00000000-0000-4000-8000-000000000118",
    "draft:00000000-0000-4000-8000-00000000011b",
    "draft:00000000-0000-4000-8000-00000000011d",
    "draft:00000000-0000-4000-8000-00000000011f",
    "draft:00000000-0000-4000-8000-000000000124",
    "draft:00000000-0000-4000-8000-000000000126",
    "draft:00000000-0000-4000-8000-000000000128",
    "draft:00000000-0000-4000-8000-00000000012c",
    "draft:00000000-0000-4000-8000-00000000012e",
    "draft:00000000-0000-4000-8000-000000000130",
    "draft:00000000-0000-4000-8000-000000000137",
    "draft:00000000-0000-4000-8000-000000000139",
    "draft:00000000-0000-4000-8000-00000000013c",
    "draft:00000000-0000-4000-8000-00000000013e",
    "draft:00000000-0000-4000-8000-000000000140",
    "draft:00000000-0000-4000-8000-000000000145",
    "draft:00000000-0000-4000-8000-000000000147",
    "draft:00000000-0000-4000-8000-00000000014a",
    "draft:00000000-0000-4000-8000-00000000014c",
    "draft:00000000-0000-4000-8000-00000000014e",
    "draft:00000000-0000-4000-8000-000000000154",
    "draft:00000000-0000-4000-8000-000000000156",
    "draft:00000000-0000-4000-8000-000000000159",
    "draft:00000000-0000-4000-8000-00000000015b",
    "draft:00000000-0000-4000-8000-00000000015d",
    "draft:00000000-0000-4000-8000-000000000162",
    "draft:00000000-0000-4000-8000-000000000164",
    "draft:00000000-0000-4000-8000-000000000166",
    "draft:00000000-0000-4000-8000-00000000016a",
    "draft:00000000-0000-4000-8000-00000000016c",
    "draft:00000000-0000-4000-8000-00000000016e",
    "draft:00000000-0000-4000-8000-000000000176",
    "draft:00000000-0000-4000-8000-000000000178",
    "draft:00000000-0000-4000-8000-00000000017b",
    "draft:00000000-0000-4000-8000-00000000017d",
    "draft:00000000-0000-4000-8000-00000000017f",
    "draft:00000000-0000-4000-8000-000000000184",
    "draft:00000000-0000-4000-8000-000000000186",
    "draft:00000000-0000-4000-8000-000000000189",
    "draft:00000000-0000-4000-8000-00000000018b",
    "draft:00000000-0000-4000-8000-00000000018d",
    "draft:00000000-0000-4000-8000-000000000193",
    "draft:00000000-0000-4000-8000-000000000195",
    "draft:00000000-0000-4000-8000-000000000198",
    "draft:00000000-0000-4000-8000-00000000019a",
    "draft:00000000-0000-4000-8000-00000000019c",
    "draft:00000000-0000-4000-8000-0000000001a1",
    "draft:00000000-0000-4000-8000-0000000001a3",
    "draft:00000000-0000-4000-8000-0000000001a5",
    "draft:00000000-0000-4000-8000-0000000001a9",
    "draft:00000000-0000-4000-8000-0000000001ab",
    "draft:00000000-0000-4000-8000-0000000001ad",
    "draft:00000000-0000-4000-8000-0000000001b4",
    "draft:00000000-0000-4000-8000-0000000001b6",
    "draft:00000000-0000-4000-8000-0000000001b9",
    "draft:00000000-0000-4000-8000-0000000001bb",
    "draft:00000000-0000-4000-8000-0000000001bd",
    "draft:00000000-0000-4000-8000-0000000001c2",
    "draft:00000000-0000-4000-8000-0000000001c4",
    "draft:00000000-0000-4000-8000-0000000001c7",
    "draft:00000000-0000-4000-8000-0000000001c9",
    "draft:00000000-0000-4000-8000-0000000001cb",
    "draft:00000000-0000-4000-8000-0000000001d1",
    "draft:00000000-0000-4000-8000-0000000001d3",
    "draft:00000000-0000-4000-8000-0000000001d6",
    "draft:00000000-0000-4000-8000-0000000001d8",
    "draft:00000000-0000-4000-8000-0000000001da",
    "draft:00000000-0000-4000-8000-0000000001df",
    "draft:00000000-0000-4000-8000-0000000001e1",
    "draft:00000000-0000-4000-8000-0000000001e3",
    "draft:00000000-0000-4000-8000-0000000001e7",
    "draft:00000000-0000-4000-8000-0000000001e9",
    "draft:00000000-0000-4000-8000-0000000001eb"
  ],
  "edits": [
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000162",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000bb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000128",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000198",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000014",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000082",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ee",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001cb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000126",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000195",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000011",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000080",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ec",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000045",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000124",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000193",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000159",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000043",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000156",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000041",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ae",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000008",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000073",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000154",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000aa",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000189",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000006",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000071",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000df",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bd",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000118",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000186",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000003",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000dd",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000035",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000116",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000184",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000162",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000bb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000128",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000198",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000014",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000082",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ee",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001cb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000126",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000195",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000011",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000080",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ec",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000045",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000124",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000193",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000159",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000043",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000156",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000041",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ae",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000008",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000073",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000154",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000aa",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000189",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000006",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000071",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bd",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000118",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000186",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000003",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000dd",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000035",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000116",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000184",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000162",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000bb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000128",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000198",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000014",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000082",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ee",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001cb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000126",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000195",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000011",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000080",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ec",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000045",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000124",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000193",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000159",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000043",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000156",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000041",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ae",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000008",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000073",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000154",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000aa",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000189",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000006",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000071",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000df",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bd",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000118",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000186",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000003",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000dd",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000035",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000116",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000184",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000162",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000bb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000128",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000198",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000014",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000082",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ee",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001cb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000126",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000195",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000011",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000080",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ec",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000045",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000124",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000193",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000159",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000043",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000156",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000041",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ae",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000008",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000073",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000154",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000aa",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000189",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000006",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000071",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bd",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000118",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000186",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000003",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000dd",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000035",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000116",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000184",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000162",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000bb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000128",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000198",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000014",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000082",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ee",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001cb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000126",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000195",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000011",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000080",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ec",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000045",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000124",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000193",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000159",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000043",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000156",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000041",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ae",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000008",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000073",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000154",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000aa",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000189",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000006",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000071",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000df",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bd",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000118",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000186",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000003",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000dd",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000035",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000116",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000184",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000162",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000bb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000128",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000198",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000014",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000082",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ee",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001cb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000126",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000195",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000011",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000080",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ec",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000015b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000045",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000124",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000193",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000159",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000043",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000b0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000000a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000007b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000156",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c4",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000041",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ae",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000018b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000008",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000073",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000e4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000154",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000aa",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000011b",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000189",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000006",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000071",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bd",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000003c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a8",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000118",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000186",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000003",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000dd",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001bb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000035",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000116",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000184",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000001",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000006b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000db",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000014a",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000033",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000a1",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000110",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001eb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000069",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000147",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b6",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000031",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009f",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017d",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000067",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000145",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001b4",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009d",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000010c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000017b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e7",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000062",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000d0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000140",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ad",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000002c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000009a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000109",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000178",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000060",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000ce",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013e",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001ab",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000027",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000098",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000107",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000176",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001e1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000cc",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000013c",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000025",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000092",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000102",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001df",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000005b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c9",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000139",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a5",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000023",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000090",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000100",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001da",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000059",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c7",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000137",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000020",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fe",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000016a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d8",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000053",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c2",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000130",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001a1",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000001e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000008b",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000fb",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000166",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d6",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000051",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000c0",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012e",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000018",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000089",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f9",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000164",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000001d3",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000004f",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000be",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000012c",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-00000000019a",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000016",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-000000000084",
      "targetId": "server:00000000-0000-4000-8000-000000001000"
    },
    {
      "nodeId": "draft:00000000-0000-4000-8000-0000000000f0",
      "targetId": "server:00000000-0000-4000-8000-000000001001"
    }
  ]
}
`,xd=4096;class Pv{constructor(){n0(this,"entries",[]);n0(this,"observer",null);n0(this,"bufferFull",!1);n0(this,"overflow",!1);n0(this,"dropped",0);n0(this,"droppedFieldObserved",!1);n0(this,"supported",!1);n0(this,"statusFieldSupported",!1);if(this.statusFieldSupported=typeof PerformanceResourceTiming<"u"&&"responseStatus"in PerformanceResourceTiming.prototype,this.supported=typeof PerformanceObserver<"u"&&PerformanceObserver.supportedEntryTypes.includes("resource"),!!this.supported){performance.addEventListener("resourcetimingbufferfull",this.full.bind(this)),performance.setResourceTimingBufferSize(xd);try{this.observer=new PerformanceObserver(this.capture.bind(this)),this.observer.observe({type:"resource",buffered:!0})}catch{this.supported=!1,this.observer=null}}}full(){this.bufferFull=!0}capture(d,f,u){typeof(u==null?void 0:u.droppedEntriesCount)=="number"&&(this.droppedFieldObserved=!0,this.dropped+=u.droppedEntriesCount);for(const s of d.getEntries()){if(this.entries.length>=xd){this.overflow=!0;continue}this.entries.push(s)}}drain(){var d;for(const f of((d=this.observer)==null?void 0:d.takeRecords())??[]){if(this.entries.length>=xd){this.overflow=!0;continue}this.entries.push(f)}}records(){return this.drain(),this.entries.map(nm)}coverage(){this.drain();const d=this.entries.filter(em).length;return{supported:this.supported,statusFieldSupported:this.statusFieldSupported,droppedFieldObserved:this.droppedFieldObserved,browserBufferFull:this.bufferFull,observerOverflow:this.overflow,droppedEntries:this.dropped,unknownStatusCount:d,entryCount:this.entries.length,limit:xd,complete:this.supported&&this.statusFieldSupported&&this.droppedFieldObserved&&!this.bufferFull&&!this.overflow&&this.dropped===0&&d===0}}validations(d){return this.records().filter(tm.bind(null,d))}}function nm(r){return{path:new URL(r.name,location.href).pathname.replace(/\/documents\/[^/]+/,"/documents/[redacted]"),start:r.startTime,duration:r.duration,responseStatus:r.responseStatus>0?r.responseStatus:"UNKNOWN_OR_ERROR"}}function em(r){return!(r.responseStatus>0)}function tm(r,d){return d.path.endsWith("/validate")&&d.start>=r}const Ed=new Pv;function Pa(r){const d=r.view.document,f=d.accepted;return{documentId:(f==null?void 0:f.documentId)??null,acceptedRevision:(f==null?void 0:f.revision)??null,headRevision:(f==null?void 0:f.headRevision)??null,baseRevision:d.baseRevision,draftId:d.draftId,draftEpoch:d.epoch,contentGeneration:d.contentGeneration,commitSequence:r.sequence}}function am(){const r=navigator.deviceMemory;return{browser:navigator.userAgent,hardwareConcurrency:navigator.hardwareConcurrency,deviceMemoryGiB:r??"unavailable",viewport:[innerWidth,innerHeight],devicePixelRatio,screen:[screen.width,screen.height],screenColorDepth:screen.colorDepth,visibility:document.visibilityState,clock:"performance.now",workerStartup:"excluded",physicalDisplayRefresh:"unknown"}}function rm(){function r(d,f){const u=[];function s(){f(new Error("Refresh sampling timed out."))}const c=window.setTimeout(s,1e4);function v(p){if(u.push(p),u.length<13){requestAnimationFrame(v);return}clearTimeout(c);const A=[];for(let S=1;S<u.length;S++)A.push(u[S]-u[S-1]);d(A)}requestAnimationFrame(v)}return new Promise(r)}function dm(r,d){var s,c;const f=r.view.document,u=d.view.document;if(r.mount!==d.mount||r.controller.token!==d.controller.token||((s=f.accepted)==null?void 0:s.documentId)!==((c=u.accepted)==null?void 0:c.documentId)||f.draftId!==u.draftId||f.baseRevision!==u.baseRevision||f.epoch!==u.epoch||f.contentGeneration!==u.contentGeneration||!f.validationBody)return!1;try{const v=JSON.parse(f.validationBody);if(!v||typeof v!="object")return!1;const p=v;return p.draftId===u.draftId&&p.draftEpoch===u.epoch&&p.baseRevision===u.baseRevision}catch{return!1}}async function lm(r,d){var s;const f=performance.now()+1e4;for(;performance.now()<f;){const c=Ed.validations(r).at(-1),v=rn();if(c&&v&&dm(v,d)&&v.view.document.notice!=="Validating advisory draft…"){const p=v.view.document;return{status:c.responseStatus==="UNKNOWN_OR_ERROR"?"UNKNOWN_OR_ERROR":"SETTLED_OBSERVED",resource:c,notice:p.notice,validationPresent:!!p.validation,diagnostics:((s=p.validation)==null?void 0:s.diagnostics)??[],rejectionDiagnostics:p.rejectionDiagnostics,identity:Pa(v)}}await im()}const u=rn();return{status:"NOT_SETTLED_WITHIN_10_SECONDS",notice:(u==null?void 0:u.view.document.notice)??"workbench unmounted",identity:u?Pa(u):null}}function im(){function r(d){window.setTimeout(d,100)}return new Promise(r)}const S4="947ed5002b097cd25e780afddfca5a3db9721c42b839fad4925b488af996089c",_4="server:00000000-0000-4000-8000-000000001000",x4="server:00000000-0000-4000-8000-000000001001",A4=1e4;function e0(r,d){if(!r)throw new Error(d)}async function Td(r){const d=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(r));return Array.from(new Uint8Array(d),fm).join("")}function fm(r){return r.toString(16).padStart(2,"0")}function _f(r){const d=r.view.document;return e0(d.accepted,"Open an accepted document first."),{mount:r.mount,token:r.controller.token,document:d.accepted.documentId,base:d.baseRevision,draft:d.draftId,generation:d.contentGeneration}}function Re(r,d){e0(r&&document.visibilityState==="visible","Unmount or visibility loss.");const f=_f(r);e0(f.mount===d.mount&&f.token===d.token&&f.document===d.document&&f.base===d.base&&f.draft===d.draft&&f.generation===d.generation,"Identity or generation changed.")}function E4(r,d){let f=0,u=xf;function s(v,p){u=p;function A(){Jt(null),p(new Error("Commit timeout."))}f=window.setTimeout(A,A4);function S(N){try{e0(N.sequence>d,"Stale commit."),Re(N,r),clearTimeout(f),Jt(null),v()}catch(U){clearTimeout(f),Jt(null),p(U)}}Jt(S)}function c(){clearTimeout(f),Jt(null),u(new Error("Dispatch failed."))}return{promise:new Promise(s),cancel:c}}function um(r){function d(f,u){function s(){u(new Error("Frame timeout."))}const c=window.setTimeout(s,A4);function v(){try{Re(rn(),r);const A=performance.now();clearTimeout(c),f(A)}catch(A){clearTimeout(c),u(A)}}function p(){try{Re(rn(),r),requestAnimationFrame(v)}catch(A){clearTimeout(c),u(A)}}requestAnimationFrame(p)}return new Promise(d)}function sm(r,d){let f=0;function u(c){return c.id!==d.nodeId?c:(e0(c.tag==="signature_ref"&&c.targetId!==d.targetId,"Unexpected pre-edit target."),f++,{...c,targetId:d.targetId})}const s=r.nodes.map(u);return e0(f===1,"Missing or duplicate edited reference."),{...r,nodes:s}}function T4(r){return r.id}function om(r){return r.id===_4&&r.name==="A"}function cm(r){return r.id===x4&&r.name==="B"}function gm(r){const d=r.module,f=He(d),u=new Set(d.nodes.map(T4));e0(u.size===500&&d.nodes.length===500&&r.edits.length===1100,"Fixture count mismatch."),e0(new TextEncoder().encode(r.source).length===2565,"Fixture source size mismatch."),e0(d.signatures.some(om)&&d.signatures.some(cm),"Fixture declaration mismatch.");function s(c){const v=f.get(c);return e0(v,"Missing fixture node."),1+Math.max(0,...Be(v).map(s))}for(const c of d.predicates)e0(s(c.bodyId)<=32,"Fixture depth exceeded.")}function Im(r){return`block-${r.id}`}function vm(r){return r.id}function Qc(r,d){const f=document.querySelector('[aria-label="Owned expression forest"]');e0(f,"Missing owned forest.");const u=Array.from(f.querySelectorAll('button[id^="block-"]')),s=new Set(r.nodes.map(Im));function c(S){return s.has(S.id)}function v(S){return S.id===`block-${d.nodeId}`}e0(u.length===500&&new Set(u.map(vm)).size===500&&u.every(c),"Rendered node set mismatch."),e0(!f.querySelector('[role="alert"]'),"Missing-node or depth alert.");const p=u.find(v),A=d.targetId===_4?"A":d.targetId===x4?"B":"";e0(A&&(p==null?void 0:p.textContent)===`signature ref · ${A}`,"Edited target DOM mismatch.")}function xf(r){}async function mm(r,d){var Y;const f=rn();e0(f,"Workbench not mounted."),e0(f.view.document.module===r,"Prior committed candidate changed.");function u(u0){return u0.id===d.nodeId}const s=r.nodes.find(u);e0((s==null?void 0:s.tag)==="signature_ref","Missing prior target."),Qc(r,{nodeId:d.nodeId,targetId:s.targetId});const c=_f(f),v=sm(r,d),p={...c,generation:c.generation+1},A=E4(p,f.sequence);A.promise.catch(xf);const S=performance.now();try{yf(f.controller,v)}catch(u0){throw A.cancel(),u0}await A.promise;const U=await um(p)-S;return Re(rn(),p),e0(((Y=rn())==null?void 0:Y.view.document.module)===v,"Committed candidate mismatch."),Qc(v,d),{module:v,elapsed:U,dispatch:S}}function hm(r,d){return r-d}function ym(r){return Number.isFinite(r)&&r>=0}function pm(r){const d=[...r].sort(hm);return e0(d.length===1e3&&d.every(ym),"Invalid sample vector."),{p50:d[499],p95:d[949],p99:d[989],classification:d[949]<50?"PASS":"FAIL"}}async function bm(r){const d=He(r.module);function f(s){const c=d.get(s);return e0(c,"Missing fixture node."),1+Math.max(0,...Be(c).map(f))}let u=0;for(const s of r.module.predicates)u=Math.max(u,f(s.bodyId));return{fileSha256:S4,sourceSha256:await Td(r.source),sourceUtf8Bytes:new TextEncoder().encode(r.source).length,editSequenceSha256:await Td(JSON.stringify(r.edits)),nodeIdsSha256:await Td(JSON.stringify(r.module.nodes.map(T4))),expressionNodes:r.module.nodes.length,maximumDepth:u,warmupEvents:100,measuredEvents:1e3}}function Sm(){return{status:"INCOMPLETE",samples:[],warmupSamples:[],visibility:[],cold:"NOT_CONDUCTED",environment:am(),resources:[],limitation:"Pinned server-prefixed fixture declaration IDs may be foreign to the accepted document; preview is not authoritative acceptance.",continuityChecks:0,startedUtc:new Date().toISOString(),errors:[]}}async function _m(r,d){const f=rn();e0(f&&f.view.document.accepted,"Open an accepted document first."),e0(!f.view.document.pending&&!f.view.document.validationBody&&!f.view.document.dirty,"Start with a clean accepted document and no pending operation.");const u=_f(f);Re(f,u),d.initialIdentity=Pa(f);const s=E4({...u,generation:u.generation+1},f.sequence);s.promise.catch(xf);try{yf(f.controller,r.module)}catch(v){throw s.cancel(),v}await s.promise;const c=rn();return e0(c,"Workbench unmounted during setup."),d.fixtureIdentity=Pa(c),{...u,generation:u.generation+1}}async function xm(r,d,f,u){let s=r.module;for(let v=0;v<r.edits.length;v++){Re(rn(),{...d,generation:d.generation+v});const p=await mm(s,r.edits[v]);s=p.module,Re(rn(),{...d,generation:d.generation+v+1}),f.continuityChecks++,v<100?f.warmupSamples.push(p.elapsed):f.samples.push(p.elapsed),v===r.edits.length-1&&(f.finalDispatchMs=p.dispatch),e0(f.visibility.length===0,"Visibility transition during benchmark."),u.textContent=`Benchmark ${v+1}/1100`}const c=rn();e0(c,"Workbench unmounted at end."),f.finalIdentity=Pa(c)}async function Am(){const r=document.getElementById("benchmark-status");e0(r,"Missing status.");const d=Sm();function f(){d.visibility.push(`${performance.now()}:${document.visibilityState}`)}function u(){d.errors.push("window error")}function s(){d.errors.push("unhandled rejection")}document.addEventListener("visibilitychange",f),window.addEventListener("error",u),window.addEventListener("unhandledrejection",s);try{e0(await Td(Lc)===S4,"Fixture hash mismatch.");const c=JSON.parse(Lc);gm(c),d.fixture=await bm(c),d.refreshIntervalsMs=await rm();const v=await _m(c,d);await xm(c,v,d,r),d.statistics=pm(d.samples);const p=rn();e0(p&&d.finalDispatchMs!==void 0,"Missing final identity or dispatch boundary.");const A=await lm(d.finalDispatchMs,p);d.advisory=A;const S=Ed.coverage();d.resourceCoverage=S,e0(S.complete,"Resource coverage incomplete or unknown."),Re(rn(),{...v,generation:v.generation+1100}),e0(A.status==="SETTLED_OBSERVED","Advisory outcome not observed within deadline."),e0(d.errors.length===0,"Browser runtime error observed."),e0(d.visibility.length===0,"Visibility transition during evidence capture."),d.status="COMPLETE"}catch(c){d.reason=c instanceof Error?c.message:String(c)}finally{Jt(null),document.removeEventListener("visibilitychange",f),window.removeEventListener("error",u),window.removeEventListener("unhandledrejection",s),d.resources=Ed.records();const c=Ed.coverage();d.resourceCoverage=c,c.complete||(d.status="INCOMPLETE",d.reason="Resource coverage incomplete or unknown."),r.textContent=JSON.stringify(d,null,2)}}const Em=Fv(),j4=document.getElementById("root"),kt=document.getElementById("benchmark-start");if(!j4||!(kt instanceof HTMLButtonElement))throw new Error("Missing benchmark root or control.");fg.createRoot(j4).render(I.jsx(Wv,{token:Em}));async function Tm(){if(!(!(kt instanceof HTMLButtonElement)||kt.disabled)){kt.disabled=!0;try{await Am()}finally{kt.disabled=!1}}}kt.addEventListener("click",Tm);
