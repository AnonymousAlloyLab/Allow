"""Actual LangGraph retrieval node, with no generation or remote tracing."""
import os
from typing import TypedDict

class RetrievalState(TypedDict, total=False):
    record_id: str
    limit: int
    documents: list
    envelope: dict

def build_graph(repository):
    if any(os.environ.get(k,'').lower() in ('1','true') for k in ('LANGCHAIN_TRACING','LANGCHAIN_TRACING_V2','LANGSMITH_TRACING','LANGSMITH_TRACING_V2')):
        raise ValueError('external_tracing_forbidden')
    from langgraph.graph import StateGraph, START, END
    from langchain_core.documents import Document
    from .ranking import search
    from .common import canonical
    def retrieve(state):
        envelope=search(repository,state['record_id'],state.get('limit',10))
        docs=[]
        for item in envelope['results']:
            metadata={k:v for k,v in item.items() if k!='structuredContent'}
            content=item.get('structuredContent',{'contentUnavailable':True,'reason':item.get('contentReason')})
            docs.append(Document(page_content=canonical(content),metadata=metadata))
        return {'documents':docs,'envelope':envelope}
    graph=StateGraph(RetrievalState)
    graph.add_node('retrieve',retrieve)
    graph.add_edge(START,'retrieve');graph.add_edge('retrieve',END)
    return graph.compile()
