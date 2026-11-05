import {useEffect,useMemo,useState} from 'react';
import type {Controller} from '../controller';
import {identity} from './transactions';
import {AssistantSession,INITIAL} from './session';
import type {AssistantState} from './types';
/** Create one private assistant owner for the current bearer. @param controller Current controller. @param notify React publisher. @returns Owner. */
function owner(controller:Controller,notify:(state:AssistantState)=>void):AssistantSession {return new AssistantSession(controller,notify);}
/** Initialize and retire owned requests with the mounted authority. @param session Assistant owner. @returns Cleanup. */
function lifetime(session:AssistantSession):()=>void {void session.initialize();return session.dispose.bind(session);}
/** Observe exact current content identity. @param session Assistant owner. @returns Nothing. */
function observe(session:AssistantSession):void {session.observe();}
/** Bind the independent assistant surface to current workbench state. @param controller Workbench controller. @param online Session liveness. @returns Assistant owner and presentation. */
export function useAssistant(controller:Controller,online:boolean):{session:AssistantSession;view:AssistantState} {
  const [view,set]=useState<AssistantState>(INITIAL),session=useMemo(owner.bind(null,controller,set),[controller.token]);
  session.connect(controller,online);
  useEffect(lifetime.bind(null,session),[session]);
  useEffect(observe.bind(null,session),[session,online,identity(controller.current.current.document)]);
  return {session,view};
}
