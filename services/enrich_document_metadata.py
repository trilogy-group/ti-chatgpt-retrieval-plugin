from models.models import Document
from typing import Dict, List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.schema import Document as LangchainDocument
from langchain.chat_models import ChatOpenAI
import json


def cleanup_list(lst):
    cleaned_lst = []
    for item in lst:
        item = item.strip()
        if item.startswith('{'):
            cleaned_lst.append(json.loads(item))
    return cleaned_lst

def merge_json(json_list):
    print("json_list: ", json_list)
    json_list = cleanup_list(json_list)
    result = {}
    for json_data in json_list:
        for key in json_data:
            if key not in result:
                result[key] = []
            result[key].extend(json_data[key])
    return result

def remove_duplicates(json_obj):
    json_obj['people'] = list(set(json_obj['people']))
    json_obj['technologies'] = list(set(json_obj['technologies']))
    json_obj['organizations'] = list(set(json_obj['organizations']))
    return json_obj

def extract_metadata_using_llm(text: str):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200) # TODO: increase chunk_size
    chunks = text_splitter.split_text(text)

    model_name = "gpt-3.5-turbo"
    chain_type = "map_reduce"

    docs = []

    for chunk in chunks:
        docs.append(LangchainDocument(page_content=chunk))
    
    query = """Given a document from a user, try to extract the following metadata:
            - people = [List of string containing people names that are being mentioned in the document]
            - technologies = [List of string containing technologies that are being talked about in the document]
            - organizations = [List of string containing organization names that are being mentioned in the document]
            Respond with a JSON containing the extracted metadata in key value pairs. If you don't find a metadata field, specify it as an empty array but keep all keys in the output, dont create any key or value of your own.
            Output json format: """ + """people: [List[str]], technologies: [List[str]], organizations: [List[str]]"""
    
    question_prompt_template = """Use the following portion of a long document to extract the entities mentioned in the question.
    {context}
    Question: {question}
    Output json format: """ + """people: [List[str]], technologies: [List[str]], organizations: [List[str]]"""
    QUESTION_PROMPT = PromptTemplate(
        template=question_prompt_template, input_variables=["context", "question"]
    )

    combine_prompt_template = """Given the following extracted metadata json of a long document and a question, create a final json aggregating all the information together. 
    Dont miss any information(key or value) for the final output. Don't try to make up an answer.
    QUESTION: {question}
    =========
    {summaries}
    =========
    Aggregated json:"""

    COMBINE_PROMPT = PromptTemplate(
        template=combine_prompt_template, input_variables=["summaries", "question"]
    )
    
    chain = load_qa_chain(OpenAI(temperature=0, model_name=model_name), chain_type=chain_type, return_map_steps=False,
                        question_prompt=QUESTION_PROMPT, combine_prompt=COMBINE_PROMPT)
    extracted_metadata = chain({"input_documents": docs, "question": query}, return_only_outputs=True)

    '''
    refine_prompt_template = (
    "The original question is as follows: {question}\n"
    "We have provided an existing answer: {existing_answer}\n"
    "We have the opportunity to extend the key values list in existing json"
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_str}\n"
    "------------\n"
    "Given the new context, extend people, technologies, organizations array in the original answer to better "
    "answer the question. "
    "If the context isn't useful just return the existing json, dont add anything to the answer. Dont explain what you did just return the final json output."
    )
    refine_prompt = PromptTemplate(
        input_variables=["question", "existing_answer", "context_str"],
        template=refine_prompt_template,
    )


    initial_qa_template = (
        "Context information is below. \n"
        "---------------------\n"
        "{context_str}"
        "\n---------------------\n"
        "Given the context information and not prior knowledge, "
        "answer the question: {question}\nYour json answer should be strictly follow this format: " + """people: [List[str]], technologies: [List[str]], organizations: [List[str]] \n"""
    )
    initial_qa_prompt = PromptTemplate(
        input_variables=["context_str", "question"], template=initial_qa_template
    )
    chain = load_qa_chain(OpenAI(temperature=0, model_name=model_name), chain_type=chain_type, return_refine_steps=True,
                        question_prompt=initial_qa_prompt, refine_prompt=refine_prompt)
    extracted_metadata = chain({"input_documents": docs, "question": query}, return_only_outputs=True)
    '''
    # open the file in write mode and write the text
    extracted_metadata = merge_json(extracted_metadata.get('intermediate_steps', []))
    extracted_metadata = remove_duplicates(extracted_metadata)

    with open("/Users/rakshitbhatt/Documents/projects-cn/ti-group/ti-chatgpt-retrieval-plugin/services/extracted_metadata_results_2.txt", "a") as file:
        output = 'model_name: ' + model_name + '\n' + 'chain_type: ' + chain_type + '\n'
        output += 'extracted metadata: ' + str(extracted_metadata) + '\n'
        file.write(output)

    print("extracted_metadata: ", extracted_metadata)
    return extracted_metadata



def enrich_metadata(doc: Document):
    additional_metadata = extract_metadata_using_llm(doc.text)
    doc.metadata.people.append(additional_metadata.get('people', []))
    doc.metadata.technologies.append(additional_metadata.get('technologies', []))
    doc.metadata.organizations.append(additional_metadata.get('organizations', []))
    doc.metadata.productsInvolved.append(additional_metadata.get('productsInvolved', []))
    # print("Final metadata: ", doc.metadata)
    


def enrich_document_metadata(documents: List[Document]):
    for doc in documents:
        enrich_metadata(doc)
