import streamlit as st
from fastapi import FastAPI, Query, Path, HTTPException, Body
import uvicorn
from pydantic import BaseModel
from pipeline_refined import is_url_in_database,store_url,finding_kb, chatbot_query
import mysql.connector

class Upload(BaseModel):
    urls : list[str]
    
def upload_urls(input_data: Upload):
    urls=input_data.urls

# Store the URLs in the SQL database
try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="user@123"
    )
    cursor = mydb.cursor()
    cursor.execute("USE vectordb")
    
    cursor = mydb.cursor(buffered=True)

    sql = "INSERT INTO information (url_list) VALUES (%s)"
    
    
    for url in urls:
            if not is_url_in_database(cursor, url):
                store_url(cursor, url)
                mydb.commit()  # Commit the transaction


except Exception as e:
    print(f"Error storing URLs in SQL database: {e}")
    raise HTTPException(status_code=500, detail=str(e))

# Reflect the URLs in the `vectodb` database
try:
    finding_kb(urls)
except Exception as e:
    print(f"Error reflecting URLs in `vectodb` database: {e}")
    raise HTTPException(status_code=500, detail=str(e))  


def user_question(query: str):
    try:
        response = chatbot_query(query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
st.title("Knowledge Base App")

# Upload the URLs
upload_form = st.form(key="upload_urls")
upload_urls_data = Upload()
upload_form.add_input(key="urls", label="URLs to Add", type="text", value="")
submit_button = upload_form.form_submit_button(label="Upload URLs")

if submit_button:
    upload_urls(upload_urls_data)

# Answer the user's question
query_form = st.form(key="user_question")
query_data = Query()
query_form.add_input(key="query", label="Query", type="text", value="")
submit_button = query_form.form_submit_button(label="Answer")

if submit_button:
    response = user_question(query_data.query)
    st.write(response) 

