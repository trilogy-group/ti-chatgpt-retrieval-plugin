from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import requests
import time
import json

SHEETS_FILE_ID="1gg8_Ojhxcwq38Q0akEJYrd4MkEVujwX83alWBx4iK-Y"
APPROACH_TITLE="Basic Refine"
PRODUCT_TITLE="EYK"
SHEET_NAME="EYK"
REFINE_PROMPT="""
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
INITIAL_PROMPT="""
    "Context information is below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "Answer questions given the context information and not prior knowledge\n"
    "Prioritize keeping the answer consise.\n"
    "Do not add explanations about your answer unlessly explicitly asked to do so in the question.\n"
    "If the context isn't useful, return nothing'\n"
    "answer the question: {question}\n"
"""

Questions = [
    {
        "category": "Incorporating timeline (i.e) the ability to fetch earliest docs, latest docs etc.", 
        "questions": [
            "What are the most important technical decisions EYK has taken over the years, which of them brought the most business value?",
            "What were the key approaches that were curated to reduce private cluster cost on EYK in 2022? Are there any new approaches that have been added recently?"
        ]
    },
    {
        "category": "Prevent losing any information while aggregating data from multiple documents",
        "questions": [
            "What are the core databases that are required to run the basic EYK infrastructure? Name all of them.",
            "What is the functionality of harbour master? Mention all of them.",
            "What is the role of hephy router in EYK?",
            "What does EYK deliver over AWS EKS? How does it differ from EKS?",
            "What is the role of deis controller in EYK?",
            "Does EYK have a default horizontal pod autoscaler?"
        ]
    },
    {
        "category": "Recognising named entities.",
        "questions": [
            "Name all Subject Matter Experts(SME) for EYK.",
            "What all entities are stored in harbour master database in EYK?",
            "What all does EYK controller store on EYK controller database? Mention all entities.",
            "What is organisation entity in EYK context?",
            "What entities does hephy database bucket store for EYK?",
            "What component of EYK is called on executing 'git push eyk' command?"
        ]
    },
    {
        "category": "Formulating answers with information spread across a large number of documents",
        "questions": [
            "How can EYK handle isolation for resources used by different customers in a multi-tenant setup?`",
            "How can we lower private cluster costs for EYK?",
            "What are the projects that have utilised hephy workflow or deis workflow?",
            "How can you perform a release of EYK on a new environment?",
            "What are all the components that EYK is comprised of? Briefly explain the importance of each component.",
            "How can we create app specific resources on EYK?",
            "What is the problem that EYK solves?",
            "What is the role of cluster overprovisioners in EYK?"
        ]
    },
    {
        "category" : "Answering 'document retrieval' questions with a list of (possibly) all the documents relevant to the given question",
        "questions": [
            "What is the job of Port authority in EYK, pull out all documents that talk about it?",
            "Explain the working of hephy builder, pull out all documents that talk about it.",
            "Mention all documents that talk about the working of deis router on EYK."
        ]
    },
    {
        "category": "Questions on where previously made decisions were overturned",
        "questions": [
            "Why was the decision to decrease resources allocated to overprovisoners made? When was the decision first mentioned?",
            "Why was the decision to not use spot instances for EYK nodes made? Was that ever overturned, if yes, why?"
        ]
    }
]

# create google sheets api service using service user credentials
credentials = service_account.Credentials.from_service_account_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
service = build('sheets', 'v4', credentials=credentials)

"""
Function that iterates through questions, for each category, sends all the questions to localhost:8000/query endpoint as a post request
From the response, extracts the answer fields. 
For each received answer appends a row to the google sheet with the following information
Question, Product, Category, Approach, Answer, Time
"""
def write_to_sheet():
    for category in Questions[1:]:
        for question in category["questions"]:
            print(question)
            # send request to localhost:8000/query endpoint
            start = time.time()
            response = requests.post(
                "http://localhost:8000/full-query", json={"queries": [{"query": question, "top_k": 5}]}, headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoiQWRtaW4iLCJJc3N1ZXIiOiJJc3N1ZXIiLCJVc2VybmFtZSI6Imt1c2hhbCIsImV4cCI6MTY4MDE3MjczMSwiaWF0IjoxNjgwMTcyNzMxfQ.ED-HOUmhhCm2bjpJvYZXJw65zULvGaDotS3gJmMNcHo"}
            )
            end = time.time()

            # extract answer field from response
            query_results = response.json()["results"]
            for query_result in query_results:
                semantic_search_sources = []
                for result in query_result["results"]:
                    semantic_search_sources.append(result['metadata']['originalFileSource'])
                answer = query_result['answer']
                sources = query_result['sources']
                question = query_result['query']
                append_row(question, answer, category["category"], semantic_search_sources, sources, end - start)
            # append_row(question, answer, category["category"], end - start)

def append_row(question, answer, category, sematic_search_sources, sources, time):
    # append row to google sheet
    values = [
        [
            question,
            PRODUCT_TITLE,
            category,
            APPROACH_TITLE,
            answer, 
            time,
            INITIAL_PROMPT,
            REFINE_PROMPT,
            "\n".join(sematic_search_sources), 
            "\n".join(sources)
        ]
    ]
    body = {
        'values': values
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=SHEETS_FILE_ID, range="Sheet1!A1",
        valueInputOption="USER_ENTERED", body=body).execute()
    
write_to_sheet()