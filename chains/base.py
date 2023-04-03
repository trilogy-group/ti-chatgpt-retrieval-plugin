from typing import List, Tuple

from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.docstore.document import Document
from langchain.llms.openai import OpenAI
from langchain import PromptTemplate


from models.models import DocumentChunkWithScore, QueryResult, AggregatedQueryResult

refine_template = """
    "The original question is as follows: {question}\n"
    "We have provided an existing answer: {existing_answer}\n"
    "We have the opportunity to refine the existing answer"
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_str}\n"
    "------------\n"
    "Given the new context, refine the original answer.\n"
    "If the context isn't useful, return the original answer.\n"
    "Do not add explanations about your answer unlessly explicitly asked to do so in the question.\n"
    "Answer the question.\n"
"""
refine_prompt = PromptTemplate(template=refine_template, input_variables=["question", "existing_answer", "context_str"])

initial_qa_template = (
    "Context information is below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "Answer questions given the context information and not prior knowledge\n"
    "Prioritize keeping the answer consise.\n"
    "Do not add explanations about your answer unlessly explicitly asked to do so in the question.\n"
    "If the context isn't useful, return nothing'\n"
    "answer the question: {question}\n"
)
initial_qa_prompt = PromptTemplate(template=initial_qa_template, input_variables=["context_str", "question"])

chain = load_qa_with_sources_chain(
    llm=OpenAI(temperature=0.2), chain_type="refine", question_prompt=initial_qa_prompt, refine_prompt=refine_prompt # type: ignore
)

async def aggregate(results: List[QueryResult]):
    agg_results: List[AggregatedQueryResult] = []
    for result in results:
        answer, sources = await aggregate_query_result(result)
        agg_result = AggregatedQueryResult(answer=answer, sources=sources, results=result.results, query=result.query)
        agg_results.append(agg_result)
    return agg_results
    
async def aggregate_query_result(queryResult: QueryResult):
    """
    Converts results to Langchain documents
    Runs the documents through qa with sources chain with refine type and returns the results
    Parameters
    ----------
    results : List[DocumentChunkWithScore]
        _description_
    """
    documents = []
    for result in queryResult.results:
        metadata = result.metadata.dict()
        metadata["source"] = result.metadata.originalFileSource
        documents.append(Document(page_content=result.text, metadata=metadata))
    res = await chain.acombine_docs(docs=documents, question=queryResult.query)
    sources: List[str] = res[1]['sources']
    answer: str = res[0]
    return answer, sources

