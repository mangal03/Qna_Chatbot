import os
from dotenv import dotenv_values
from langchain.document_loaders import WebBaseLoader, TextLoader,PyPDFLoader
from langchain.schema import Document
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import AzureChatOpenAI
from langchain.utilities import TextRequestsWrapper
from bs4 import BeautifulSoup
from langchain.chains import LLMChain
from PyPDF2 import PdfFileReader
import re
import io
import mysql.connector
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

config = dotenv_values(".env")
config["BASE"]
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_BASE"] = config["BASE"]
os.environ["OPENAI_API_KEY"] = config["OPENAI_API_KEY"]
os.environ["OPENAI_API_VERSION"] = config["API_VERSION"]

def is_url_in_database(cursor, url):
    # Check if the URL exists in the database
    sql_select = "SELECT url_list FROM information WHERE url_list = %s"
    cursor.execute(sql_select, (url,))
    result = cursor.fetchone()
    return result is not None

def store_url(cursor, url):
    # Store the URL in the database
    sql_insert = "INSERT INTO information (url_list) VALUES (%s)"
    cursor.execute(sql_insert, (url,))

def finding_kb(urls, is_pdf=False):
    if os.path.exists("store.txt"):
        os.remove("store.txt")
    print("debug")  
    requests = TextRequestsWrapper()
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="user@123"
        )
        cursor = mydb.cursor()
        
        cursor.execute("USE vectordb")
        
        cursor = mydb.cursor(buffered=True)

        for url in urls:
                if not is_url_in_database(cursor, url):
                # URL is not in the database, store it
                    store_url(cursor, url)
                    mydb.commit()  # Commit the transaction

            # Retrieve the response (you need to implement this function)
                response = chatbot_query(url)
                if response is not None:
                    return response
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        mydb.close()


        
        if is_pdf == False:
            
            a=''
            for url in urls:
                html_doc=requests.get(url)
                soup = BeautifulSoup(html_doc,'html.parser')
                a = soup.text
                a = re.sub(r'\n+', '\n', a)
                a = a + "\n\n"
                print("text-----",a)

                with open('store.txt', 'a', encoding='utf-8') as file:
                    file.write(a)
        if is_pdf:
            print("entered in pdf")
            extracted_text = []
            for pdf_url in urls:
                try:
                # Read and extract text from the PDF
                    pdf_reader = PyPDFLoader(pdf_url)
                    pages = pdf_reader.load()
                    text = ""
                    for page_num in range(len(pages)):
                        text += pages[page_num].page_content + "\n\n"
                        extracted_text.append(text)
                except Exception as e:
                    return {"status":(f"Error processing {pdf_url}: {str(e)}")} 

        # Combine all extracted text into a single string
            all_text = "\n".join(extracted_text) 
            print("all text printed",all_text)  
            with open("store.txt", "a", encoding="utf-8") as output_file:
                output_file.write(all_text)

            return{"message":"Extracted content stored in store.txt", "status":"success"}
    
    text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=0
                )
    text_loader= TextLoader("store.txt",encoding="utf-8")
    pages = text_loader.load() 
    chunks = text_splitter.split_documents(pages)
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", deployment="text-embedding-ada-002" )       
    print("completed")   # debugging line
    query ="test question"
    db = Chroma.from_documents(chunks, embeddings,persist_directory="./chroma_db")
    docs = db.similarity_search(query, k=2)
    print(docs[0].page_content)
         

def chatbot_query(query):
    llm = AzureChatOpenAI(
        deployment_name = "LionoGpt35",
        model_name = "gpt-3.5-turbo",
        openai_api_base="https://lobopenaisandbox.openai.azure.com/",
        openai_api_version ="2023-03-15-preview",
        temperature=0
    )
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", deployment="text-embedding-ada-002" ) 
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    docs = db.similarity_search(query)
    print(docs[0].page_content)
    
    prompt_template = """ User's question is text. Give answer to user's message from my knowledge base only.
    {context}
    Question: {question}
    If the answer to the question is not available in memory , answer it as , no data found """
    
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context","question"])
    chain_type_kwargs = {"prompt": PROMPT}
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=db.as_retriever(), chain_type_kwargs=chain_type_kwargs)

    response =  qa.run(query)

    print(response)
    return response
    
    
    
    
    