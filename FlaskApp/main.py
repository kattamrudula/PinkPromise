__author__ = "spark expedition"
__copyright__ = "Copyright 2023, UnFold"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "spark expedition"
__email__ = "spark.expedition@gmail.com"
__status__ = "Development"

# Import Statement
import ast
import mimetypes
import ntpath
from pathlib import Path
import pathlib
import PyPDF2
import math
import datetime
import time
import os
import subprocess
import csv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import openpyxl
from flask import jsonify
from flask import render_template, url_for, json, session
from flask_cors import CORS, cross_origin
from flask import Flask, request, send_file, send_from_directory
import shutil
import nbformat
import json
from nbformat import read
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import PythonExporter

from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import h5py
import numpy as np
from time import strptime
import pandas as pd
import logging
import re
# from datetime import datetime
import dill
import base64
from PIL import Image
import psycopg2
import requests
from flask import redirect
import os
import sqlite3
# from bcrypt import hashpw, gensalt, checkpw
import papermill as pm
import uuid
import cv2
import numpy as np
#from socketio_setup import socketio
import google.generativeai as genai
import json
import requests
import speech_recognition as sr
import moviepy.editor as mp
from pydub import AudioSegment 
from pydub.silence import split_on_silence 
from datetime import datetime, timedelta
from collections import defaultdict 
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
# import asyncio
# from asyncio import WindowsSelectorEventLoopPolicy

# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['model'] = ""
app.config['mname'] = ""
app.config['vname'] = ""

# Create a global logger object
logger = logging.getLogger(__name__)

# Configure the logger to use Stackdriver Logging
# You can also set the logging level and format if needed
logging.basicConfig(level=logging.INFO)
# # creating logger
app.secret_key = os.urandom(24)  # Set a secret key for session management
workspace_dir_path = "../PatientData/"
model_dir_path = "../MLModels"

@app.route('/get_patient_file',methods = ['GET','POST'])
def get_patient_file():
    userName = request.args.get("userName")
    wspName = request.args.get("wspName")
    filePath = request.args.get("filePath")
    folder_path = workspace_dir_path
    file_obj = folder_path + filePath
    return send_file(file_obj)

@app.route("/get_patient_files_info")
def get_patient_files_info():
    data = []
    dbParams = json.loads(request.args.get("dbParams"))
    userName = dbParams['userName']
    folderName = dbParams['selectedPatient']
    dir_path = workspace_dir_path+"/"+folderName
    summary_path = "static/OutputCache/Summary/"+folderName+"/"
    columns = ["ID","FileName","Summary","FilePath","UserName"]
    i = 0
    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)) and f.startswith(".")==False]
    print("Files",files)
    for l in files:
        i = i+1
        l_path = Path(l) 
        summary_file_path = summary_path+l_path.stem+".txt"
        f = open(summary_file_path,'r')
        summary = json.loads(f.read())["text"]
        tcrow=[i,l_path.name,summary,folderName+"/"+l,userName]
        data.append(dict(zip(columns, tcrow)))
    print(data)
    return json.dumps(data, indent=4) 

# Configure a route to handle the request for displaying the models
@app.errorhandler(500)
def handle_internal_server_error(e):
    response = jsonify(error=str(e))
    response.status_code = 500
    return response

# Configure a route to handle the request for displaying the models


@app.errorhandler(500)
def handle_internal_server_error(e):
    response = jsonify(error=str(e))
    response.status_code = 500
    return response


@app.route("/favicon.ico")
def favicon():
    return send_file(os.path.join(app.static_folder, "CDN/images/entity.jpg"))


@app.route('/')
@cross_origin()
def landing():
    return render_template("PanaceaLanding.html")

@app.route('/PrivacyPolicy')
@cross_origin()
def PrivacyPolicy():
    return render_template("PrivacyPolicy.html")

@app.route('/ServiceTerms')
@cross_origin()
def ServiceTerms():
    return render_template("ServiceTerms.html")

@app.route('/Feedback')
@cross_origin()
def Feedback():
    return render_template("Feedback.html")

@app.route('/login')
@cross_origin()
def login():
    return render_template("Landing.html")

@app.route('/MasterHeader')
@cross_origin()
def MasterHeader():
    return render_template("MasterHeader.html")

@app.route('/<htmlfile>')
def renderhtml(htmlfile):
    user = request.args.get('user')
    return render_template(htmlfile, user=user)


@app.route('/Query')
def Query():
    return render_template('QueryWhisperer.html')

@app.route('/Timeline')
def Timeline():
    return render_template('Timeline.html')
 

@app.route('/Insights')
def Insights():
    return render_template('Panacea.html')

@app.route('/Compliance')
def Compliance():
    return render_template('Compliance.html')

def get_files(path):
    all_files = []
    for root, directories, files in os.walk(path):
        # print("++++++++++++++++=======================+++++++++++++")
        # print(root)
        for file in files:
            if file.endswith(".ipynb") and not os.path.isdir(os.path.join(root, file)) and not (
                    file.endswith("-checkpoint.ipynb")):
                all_files.append(os.path.join(root, file))
    # print("+++++++_______++++++++")

    return all_files


@app.route('/get_meta_data')
def get_metadata_dict():
    path = request.args.get('folder_path')
    files = get_files(path)
    # print("printing number of files")

    return files


@app.route('/get_folder_structure', methods=['GET'])
def get_folder_structure():
    folder_path = request.args.get('folder_path')
    files = get_files(folder_path)
    # print(files)
    b = []
    for i in files:

        d = get_notebook_metadata(i)
        b.append(d)
    # print(b)
    return b


@app.route("/get_notebook_metadata")
def get_notebook_metadata(notebook_paths=None):
    import os
    from datetime import datetime
    notebook_path = []
    if notebook_paths is None:
        notebook_paths = request.args.get("notebook_path")
    # print(notebook_paths, "HERE")

    x = notebook_paths.split(",")
    # print(x)
    for i in range(len(x)):
        if x[i].endswith(".ipynb"):
            notebook_name = '.'.join(x[i].split('\\')[-1].split('.')[:-1])
            notebook_path.append(os.path.join(
                os.getcwd(), "static", "Notebooks", "TrainingNotebook", x[i]))
        else:
            notebook_name = '.'.join(x[i].split('\\')[-1].split('.')[:-1])
            notebook_path.append(os.path.join(
                os.getcwd(), "static", "Notebooks", "TrainingNotebook", x[i]+".ipynb"))
    # print(notebook_path)
    x = notebook_path
    for notebook_path in x:
        # print(notebook_path)
        # NOTEBOOK
        modified_timestamp = os.path.getmtime(notebook_path)
        # Convert the timestamp to a datetime object
        modified_datetime = datetime.fromtimestamp(modified_timestamp)
        # Format the datetime as a date
        modified_date = modified_datetime.date()
        nb_date_string = modified_date.strftime("%d-%m-%Y")
        # Print the modified date
        # print("Modified Date:", modified_date)
        # Load the notebook using nbformat
        with open(notebook_path, 'r') as f:
            notebook = nbformat.read(f, as_version=nbformat.NO_CONVERT)
        # Access the notebook metadata
        metadata = notebook['metadata']

        # Count the number of cells
        num_cells = len(notebook['cells'])
        # print("Number of cells:", num_cells)

        # print(metadata)
        try:
            end = metadata["papermill"]["end_time"][:10]
            start = metadata["papermill"]["start_time"][:10]
            execution_time = metadata["papermill"]["duration"]
            execution_time = str(round(execution_time/60, 2))+" "+"min"
        except:
            start = "NotAvailable"
            end = "NotAvailable"
            execution_time = str(num_cells*1.25)+"mins (approx)"
            # fetch file name from notebook path

        # CSV
        if "/" in notebook_path:
            x = notebook_path.split("/")
        else:
            x = notebook_path.split("\\")
        # print("-------------------------------------------------------", x)
        x, ext = os.path.splitext(x[-1])

        file_name, Algorithm = x.split("-")
        # print(file_name, Algorithm)
        csv_path = os.path.join(os.getcwd(), "static", "Data", file_name)
        # print(csv_path)
        # Fetch the modified time as a timestamp
        data_modified_timestamp = os.path.getmtime(csv_path)
        data_modified_time = datetime.fromtimestamp(data_modified_timestamp)
        # Format the datetime as a date
        data_modified_time = data_modified_time.date()
        date_string = data_modified_time.strftime("%d-%m-%Y")

        popup_metadata = {
            "Notebook": notebook_name,
            "Data_Used": file_name,
            "Data_Last_Modified": date_string,
            "Notebook Last run": start,
            "Notebook Last Modified": nb_date_string,
            "Time need for notebook execution": execution_time,

            "cells in notebook": str(num_cells)


        }
        return (popup_metadata)


@app.route("/execute_notebook")
def execute_notebook():
    notebook_paths = request.args.get("notebook_path")
    x = notebook_paths.split(",")
    # print(x)
    versions = []
    notebook_path = []
    for i in range(len(x)):
        notebook_path.append(os.path.join(
            os.getcwd(), "static", "Notebooks", "TrainingNotebook", x[i]+".ipynb"))
    x = notebook_path
    for notebook_path in x:

        # print("INNOTEBOOK", notebook_path)
        try:
            # Display loading popup
            loading_script = "<script>alert('Notebook execution in progress...');</script>"
            display_script = "<script>document.getElementById('loading-popup').style.display = 'block';</script>"
            pm.execute_notebook(
                notebook_path,
                notebook_path
            )
            tag_to_fetch = 'output'
            cell_outputs = []

            with open(notebook_path, "r") as nb_file:
                notebook_content = nb_file.read()

            notebook = nbformat.reads(notebook_content, as_version=4)

            for cell in notebook.cells:
                if tag_to_fetch in cell.metadata.get('tags', []):
                    cell_outputs.append(cell.outputs)

            for output in cell_outputs:
                for entry in output:
                    if "logged" in entry.get("text", ""):
                        version = entry.get("text", "")

            # print("version", version)
            versions.append(version)

       
        except Exception as e:

            print(f"Error executing notebook: {e}")
            versions.append("error"+notebook_path)
    return versions


@app.route("/get_patient_folders")
def get_patient_folders():
    data = []
    dbParams = json.loads(request.args.get("dbParams"))
    userName = dbParams['userName']
    dir_path = workspace_dir_path
    print(dir_path)
    columns = ["name"]
    for l in os.listdir(dir_path):
        tcrow=[l]
        data.append(dict(zip(columns, tcrow)))
    print(data)
    return json.dumps(data, indent=4) 

@app.route("/gemini_query_file")
def gemini_query_file():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    userQuery = dbParams['userQuery']
    print("Entered file query for file "+filePath)
    fileAbs = Path(filePath)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"
    f = open(extracted_filename,'r', encoding='UTF-8')
    report = f.read()
    model = genai.GenerativeModel(model_name='gemini-1.5-pro-latest')
    return {"report_data": report}
    # prompt = f"""Provide answer to below question based on report provided.
    # Question : {userQuery}
    # Report: {report}""" 
    # response = model.generate_content(prompt)
    # try:
    #     returnData = response.candidates[0].content.parts[0].text
    #     return returnData
    # except:
    #     returnData = response.text
    #     return returnData
    
"""Gemini"""
def gemini_summary(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "summarize the below report in 6 points numbered list maximum \n\n" + entity_report
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-SummaryContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_summary done")
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_sentiment(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-SentimentContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_sentiment done")
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 6:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 6:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_NER(entity_report, reportName, domainName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    # prompt = "provide the Named Entities such as hospital names, patient names, doctor names,locations,medication names, and dates mentioned in the patient report as json key value pairs \n\n" + entity_report
    # prompt = "provide the named entities such as who are the people involved, locations involved, datestamps, items or servers involved as json key value pairs \n\n"+ entity_report
    prompt = ""
    if domainName == "Clinical":
        prompt = "provide the Named Entities such as hospital names, patient names, doctor names,locations,medication names, and dates mentioned in the patient report as json key value pairs \n\n" + entity_report
    elif domainName == "Incidents":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, items or servers involved as json key value pairs \n\n" + entity_report
    elif domainName == "Manufacturing":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, items or products involved, costs involved as json key value pairs \n\n" + entity_report
    elif domainName == "Gas Supply":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, items involved, costs involved as json key value pairs \n\n" + entity_report
    elif domainName == "Cyber Security":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, risks and penalties involved, costs involved as json key value pairs \n\n" + entity_report
    else:
        prompt = "provide the named entities such as hospital names, patient names, doctor names,locations,medication names, and dates mentioned in the patient report as json key value pairs  \n\n" + entity_report
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-NERContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_NER done")
    # print(json.dumps(response))

    # Three PArameters - Response, OpenAI, NERContent.txt - FileName - OpenAI-NERContent.txt
    # Three PArameters - Response, Gemini, Sentiment.txt - FileName - Gemini-Sentiment.txt

    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_emotion(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    print("gemini_emotion done")
    cache_file_path = f"static/OutputCache/Gemini-EmotionContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 1:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 1:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_tone(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    print("gemini_tone done")
    cache_file_path =f"static/OutputCache/Gemini-ToneContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 1:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 1:
            f = open(cache_file_path, encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_englishmaturity(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    print("gemini_englishmaturity done")
    cache_file_path = f"static/OutputCache/Gemini-EngmatContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 1:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 1:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_sentiment_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the sentiment of the report. Return answer in form of json with key as SentimentWords and value as list of identified words or phrases."
    response = model.generate_content(prompt)
    print("gemini_sentiment_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-SentHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_tone_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the tone of the report. Return answer in form of json with key as ToneWords and value as list of identified words or phrases"
    response = model.generate_content(prompt)
    print("gemini_tone_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-ToneHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_emotion_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the emotion of the report. Return answer in form of json with key as EmotionWords and value as list of identified words or phrases"
    response = model.generate_content(prompt)
    print("gemini_emotion_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-EmoHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_englishmaturity_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the English Maturity of the report. Return answer in form of json with key as EngMatWords and value as list of identified words or phrases"
    response = model.generate_content(prompt)
    print("gemini_englishmaturity_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-EngmatHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()

@app.route("/get_valid_rag_queries")
def get_valid_rag_queries():
    queries = ["What are the medicines prescribed?","When is the patient registered?"]
    return queries

def create_rag_model():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest",
                                   temperature=0.3)

    prompt = PromptTemplate(template=prompt_template,
                            input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain


def create_vector_db(patient_report):
    # code to extract text from folder files
    text = patient_report
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=256, chunk_overlap=20)
    text_chunks = text_splitter.split_text(text)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    
@app.route("/create_search_query")
def create_search_query():
    dbParams = json.loads(request.args.get("dbParams"))
    reportName = "RAG"
    user_question = dbParams['userQuestion']
    entity = reportName.split('_')
    print(dbParams)
    # entity_report = ""
    # for file in filesList:
    #     entity_report += pdf_2_txt("../Workspace/"+userName +
    #                                "/"+workspaceName+"/DataFiles/"+file) + "\n\n"
    # create_vector_db(entity_report)
    # print("db created")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("static/faiss_index_medical", embeddings)
    print("db loaded")
    docs = new_db.similarity_search(user_question)
    print("docs searched")
    chain = create_rag_model()
    print("rag model created")

    try:
        response = chain(
            {"input_documents": docs, "question": user_question}, return_only_outputs=True)
        if response:
            f = open(
                f"static/OutputCache/RAG/Gemini-RAG-{entity[0]}.txt", "w", encoding='utf-8')
            f.write(json.dumps(response))
            f.close()
        return response
    except:
        f = open(
            f"static/OutputCache/RAG/Gemini-RAG-{entity[0]}.txt", "r", encoding='utf-8')
        return f.read()
    
@app.route("/validate_search_query")
def validate_search_query():   
    dbParams = json.loads(request.args.get("dbParams"))
    user_question = dbParams['userQuestion']
    query_validations = [
        {
            "query":"get me the contact details of Anita",
            "status":"BLOCKED",
            "detection":"DOCUMENT LEVEL SECURITY",
            "description":"You don't have access to the document to fetch this information",
            "alternate": "Try same query with customers you have access to."
        },
        {
            "query":"get me the admission details of children in Srilanka",
            "status":"BLOCKED",
            "detection":"ROW LEVEL SECURITY",
            "description":"You dont have access to the data of this country.",
            "alternate": "Try accessing India, Nepal, Burma - available for your role"
        },
        {
            "query":"get me the city born details of Anita",
            "status":"BLOCKED",
            "detection":"COLUMN LEVEL SECURITY",
            "description":"You dont have access to location details as this column has been locked.",
            "alternate":"NA"
        },
        {
            "query":"get me the names of children relocated in Gayana",
            "status":"BLOCKED (risk score:0.8)<icon>",
            "detection":"PII DETECTED",
            "description":"PII information is detected",
            "alternate":"NA"
        },
        {
            "query":"get me the total number of mentors assigned",
            "status":"BLOCKED",
            "detection":"PERSONA PERMISSIONS",
            "description":"You dont have permission to read the data.",
            "alternate":"NA"
        }
        # {
        #     "query":"show me the sales forecast for France",
        #     "status":"BLOCKED",
        #     "detection":"MODEL LEVEL SECURITY",
        #     "description":"You dont have access to the Sales Forecast model.",
        #     "alternate":"Try accessing other models"
        # },
        # {
        #     "query":"Show me the sales for retail segment Q4-2024",
        #     "status":"BLOCKED",
        #     "detection":"INSIDER TRADING VIOLATION",
        #     "description":"You dont have permission to read the data of current quarter as this may lead to insider trading",
        #     "alternate":"Try for previous quarters"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"COPYRIGHT VIOLATION",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"RECRUITMENT/PERSONAL",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"SELF HARMING",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"DATA MANIPULATION/POISONING",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"VIOLENT ACTION",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"DATA DELETION",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # },
        # {
        #     "query":"Show me the technical details of submarine",
        #     "status":"BLOCKED",
        #     "detection":"JAIL BREAKING",
        #     "description":"This information cannot be accessed as it is a violation of copyright",
        #     "alternate":"Try any other details"
        # }
    ]
    check_exists = [q for q in query_validations if q["query"]==user_question]
    if len(check_exists) == 0:
        return {
            "message" :"PASS"
        }
    else:
        return {
            "message":"BLOCKED",
            "data":check_exists[0],
        }
 
@app.route("/get_timeline")
def get_timeline():
    print("Etered timeline")
    dbParams = json.loads(request.args.get("dbParams"))
    workspace_path = workspace_dir_path
    folder = dbParams['selectedPatient']
    folder_path = workspace_path+"/"+folder
    filesList = [folder+"/"+str(filepath) for filepath in os.listdir(folder_path)]
    timeline = []
    for file in filesList:
        fileAbs = Path(file);
        file = Path(workspace_path+"/"+file)
        filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
        f = open(filename, "r", encoding='cp1252')
        summary_obj = json.loads(f.read())
        summary = summary_obj["text"]
        create_timestamp = file.stat().st_ctime
        create_time = datetime.fromtimestamp(create_timestamp)
        timeline.append({"Event Type":fileAbs.stem,"Event Description":summary,"Time":create_time})
    return timeline

@app.route("/gemini_results")
def gemini_results():

    dbParams = json.loads(request.args.get("dbParams"))
    domainName = dbParams['domainName']
    userName = dbParams['userName']
    workspace_path = workspace_dir_path
    folder = dbParams['selectedPatient']
    folder_path = workspace_path+"/"+folder
    filesList = [folder+"/"+str(filepath) for filepath in os.listdir(folder_path)]
    reportName = filesList[0]
    print(dbParams)
    print(reportName)
    input_tokens = 0
    output_tokens = 0
    entity_report = ""
    timeline = []
    for file in filesList:
        fileAbs = Path(file);
        file = Path(workspace_path+"/"+file)
        filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
        print(filename)
        f = open(filename, "r", encoding='cp1252')
        summary_obj = json.loads(f.read())
        summary = summary_obj["text"]
        input_tokens += summary_obj["input_tokens"]
        output_tokens += summary_obj["output_tokens"]
        create_timestamp = file.stat().st_ctime
        create_time = datetime.fromtimestamp(create_timestamp)
        timeline.append({"Event Type":fileAbs.stem,"Event Description":summary,"Time":create_time})
        entity_report += summary + "\n\n"
    output_json = {
        "completeReport": entity_report,
        # "Summary": gemini_summary(entity_report, reportName),
        "Summary": entity_report,
        "Sentiment": gemini_sentiment(entity_report, reportName),
        "NER": gemini_NER(entity_report, reportName, domainName),
        "Emotion": gemini_emotion(entity_report, reportName),
        "Tone": gemini_tone(entity_report, reportName),
        "EnglishMaturity": gemini_englishmaturity(entity_report, reportName),
        "SentimentWords": gemini_determine_sentiment_highlights(entity_report, reportName),
        "EmotionWords": gemini_determine_emotion_highlights(entity_report, reportName),
        "ToneWords": gemini_determine_tone_highlights(entity_report, reportName),
        "EngMatWords": gemini_determine_englishmaturity_highlights(entity_report, reportName),
        "Timeline": timeline,
        "InputTokens": input_tokens,
        "OutputTokens": output_tokens
    }
    return output_json

@app.route('/get_folder_names')
def get_folder_names():
    data = []
    dbParams = json.loads(request.args.get("dbParams"))
    folderName = dbParams['folderName']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    dir_path = workspace_dir_path + '/' + folderName
    config_file_path = workspace_dir_path + '/' + 'Config.json'
    
    # Load the config JSON file
    with open(config_file_path, 'r') as config_file:
        config_data = json.load(config_file)

    # Initialize result list
    result = []

    # Function to get type based on folder name from config
    def get_folder_type(folder_name):
        for entry in config_data.get('Directory', []):
            if entry.get('Name') == folder_name:
                return entry.get('Type', 'Folder')
        return 'Folder'

    for root, dirs, files in os.walk(dir_path):
        if root == dir_path:  # Top-level dir_path
            result.extend([{"name": file, "type": "File"} for file in files])
        else:  # Subdirectories
            if os.path.relpath(root, dir_path) != "temp":
                folder_dict = {
                    "name": os.path.relpath(root, dir_path),
                    "type": get_folder_type(os.path.relpath(root, dir_path)),
                    "children": [{"name": file, "type": "File"} for file in files]
                }
                result.append(folder_dict)
    # print(result)

    return json.dumps(result)

@app.route("/gemini_aifeature_results")
def gemini_aifeature_results():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    aiFeature = dbParams['aiFeature']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    workspace_path = workspace_dir_path
    reportName = filePath
    value = ""
    print(dbParams)
    print(reportName)
    output_json = {}
    if aiFeature == "Summary":
        fileAbs = Path(filePath);
        filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
        f = open(filename, "r", encoding='cp1252')
        value = f.read()
        output_json = {
            "Summary" : value
        }
    else:
        emotion = gemini_multimodal_aifeature(filePath, "Emotion",workspace_path)
        sentiment = gemini_multimodal_aifeature(filePath, "Sentiment",workspace_path)
        tone = gemini_multimodal_aifeature(filePath, "Tone",workspace_path)
        #english = gemini_multimodal_aifeature(filePath, "EnglishMaturity")
        output_json = {
            "Emotion" : emotion,
            "Sentiment" : sentiment,
            "Tone" : tone
            #"EnglishMaturity":english
        }
    
    return output_json

"""Utility function for text extraction"""
def pdf_2_txt(pdf_path):
    try:
        pdf_file = open(pdf_path, 'rb')
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = ' '
        for page_number in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_number]
            text_content += page.extract_text()
        pdf_file.close()
        text_content = re.sub(r'\s+', ' ', text_content)
    except Exception as e:
        print("Error:", e)
    return text_content

@app.route("/find_medical_department")
def find_medical_department():
    dbParams = json.loads(request.args.get("dbParams"))
    folder = dbParams['selectedPatient']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    workspace_path = workspace_dir_path
    folder_path = workspace_path+"/"+folder
    filesList = [folder+"/"+str(filepath) for filepath in os.listdir(folder_path) if Path(filepath).suffix != ""]
    entity_report = ""
    for file in filesList:
        print(file)
        # if ".pdf" in file["name"] :
        #     entity_report += pdf_2_txt(workspace_dir_path+"/DataFiles/"+file["absPath"]) + "\n\n"
        # else:
        summary = gemini_multimodal_summary(file,workspace_path)
        entity_report += summary
    entity = filesList[0].split('/')[0]
    # model = genai.GenerativeModel('gemini-1.5-pro-latest')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = """Identify  the medical department of the below report from the given options :
                
                ['Anesthesiology','Cardiology','Dermatology','Emergency Medicine','Endocrinology','Gastroenterology','General Surgery','Geriatrics','Hematology',
                'Infectious Diseases','Internal Medicine','Nephrology','Neurology','Neurosurgery','Obstetrics and Gynecology (OB/GYN)','Oncology','Ophthalmology',
                'Orthopedics','Otolaryngology (ENT)','Pathology','Pediatrics','Physical Medicine and Rehabilitation','Plastic Surgery','Podiatry','Psychiatry','Pulmonology',
                'Radiology','Rheumatology','Thoracic Surgery','Urology','Vascular Surgery']. 
                
                If no department is identified from above options, then return response as 'General Medicine'.
                
                Return response in form of json with key as Department and value as identified medical department.
                \n\n""" + entity_report 
    print("gemini finding medical department")
    cache_file_path = f"static/OutputCache/gemini-MEDICAL-DEPARTMENT-{entity}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = model.generate_content(prompt)
        returnData = response.candidates[0].content.parts[0].text
        f = open(cache_file_path, "w", encoding='cp1252')
        f.write(returnData)
        f.close()
        return returnData
    except:
        response = model.generate_content(prompt)
        returnData = response.text
        f = open(cache_file_path, "w", encoding='cp1252')
        f.write(returnData)
        f.close()
        return returnData
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        print("gemini finding medical department done in finally")
        return f.read()

def extract_video_text(filePath):
    video_text = ""
    video_file_path = filePath
    clip = mp.VideoFileClip(video_file_path)
    clip.audio.write_audiofile(r"static/temp/videoconverted.wav")
    audio = AudioSegment.from_wav(r"static/temp/videoconverted.wav")
    n = len(audio)
    counter = 1
    interval = 20 * 1000
    overlap = 1.5 * 1000
    start = 0
    end = 0
    flag = 0
    # chunks = split_on_silence(audio,min_silence_len = 500, silence_thresh = -40) 
    Path(r'static/temp/video_chunks').parent.mkdir(parents=True,exist_ok=True) 
    # print(chunks)
    for i in range(0, 2 * n, interval):
        if i == 0:
            start = 0
            end = interval
        else:
            start = end - overlap
            end = start + interval 
    
        if end >= n:
            end = n
            flag = 1
    
        audio_chunk = audio[start:end]
    
        # Filename / Path to store the sliced audio
        filename = 'chunk'+str(counter)+'.wav'
        file = "static/temp/video_chunks/"+filename 
        audio_chunk.export(file,format="wav")
        print("Processing chunk "+str(counter)+". Start = "
                        +str(start)+" end = "+str(end))
        counter = counter + 1
        r = sr.Recognizer() 
        try:
            with sr.AudioFile(file) as source: 
                audio_listened = r.listen(source) 
                rec = r.recognize_google(audio_listened) 
                video_text += rec + " "
        except:
            pass
    return video_text

def extract_audio_text(filePath):
    audio_text = ""
    audio_file_path = filePath
    clip = mp.AudioFileClip(audio_file_path)
    clip.write_audiofile(r"static/temp/audioconverted.wav")
    audio = AudioSegment.from_wav(r"static/temp/audioconverted.wav")
    n = len(audio)
    counter = 1
    interval = 20 * 1000
    overlap = 1.5 * 1000
    start = 0
    end = 0
    flag = 0
    # chunks = split_on_silence(audio,min_silence_len = 500, silence_thresh = -40) 
    Path(r'static/temp/audio_chunks').parent.mkdir(parents=True,exist_ok=True) 
    # print(chunks)
    for i in range(0, 2 * n, interval):
        if i == 0:
            start = 0
            end = interval
        else:
            start = end - overlap
            end = start + interval 
    
        if end >= n:
            end = n
            flag = 1
    
        audio_chunk = audio[start:end]
    
        # Filename / Path to store the sliced audio
        filename = 'chunk'+str(counter)+'.wav'
        file = "static/temp/audio_chunks/"+filename 
        audio_chunk.export(file,format="wav")
        print("Processing chunk "+str(counter)+". Start = "
                        +str(start)+" end = "+str(end))
        counter = counter + 1
        r = sr.Recognizer() 
        try:
            with sr.AudioFile(file) as source: 
                audio_listened = r.listen(source) 
                rec = r.recognize_google(audio_listened) 
                audio_text += rec + " "
        except:
            pass
    return audio_text

@app.route("/gemini_get_sections")
def gemini_get_sections():
    dbParams = json.loads(request.args.get("dbParams"))
    selectedPatient = dbParams['selectedPatient']
    workspace_path = workspace_dir_path
    folder_path = workspace_path+"/"+selectedPatient
    filesList = [selectedPatient+"/"+str(filepath) for filepath in os.listdir(folder_path) if Path(filepath).suffix != ""]
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    sections = []
    for file in filesList:
        print(file)
        fileAbs = Path(file)
        if fileAbs.suffix != ".jpg":
            sections_path = f"static/OutputCache/Sections/{fileAbs.parent}/{fileAbs.stem}.json"
            spath = Path(sections_path)
            spath.parent.mkdir(parents=True, exist_ok=True)
            extracted_text = data_extraction(file,workspace_path)
            response = model.generate_content(
                "I have the below text extracted from patient medical report"
                + extracted_text + """Give the sections from the Medical Report in a list.
                Dont provide any extra information just provide Section name  in a list
                Incase section name has special charcater please remove special charcter from section name.
                for example = ['Problem','Diagnostics']
                please provide the response in the given above example format only with proper comma for section in list and without any escape charcters in the response and list could be properly closed.
                Response should have have only 20 sections and section name should be one worded as  provided example.
                Dont provide answer in with unnecessary strings like Here are the sections from the medical report:```python   and Dont provide long section names and section names should short as given above format""")
            print(response.text)
            t_list = list(set(ast.literal_eval(response.text.strip('```'))))
            sections_data = t_list
            section ={}
            section["fileName"] = file
            section["sections"] = sections_data
            sections.append(section)
            print(sections_data)
            with open(sections_path, "w") as f:
                json.dump(section, f, indent=4)
    return sections

# @app.route("/gemini_multimodal_summary")
def gemini_multimodal_summary(filePath,workspace_path):
    # dbParams = json.loads(request.args.get("dbParams"))
    # filePath = dbParams['selectedFile']
    input_tokens = 0
    output_tokens = 0
    print("Entered multimodal summary for file "+filePath)
    fileAbs = Path(filePath)
    file = Path(workspace_path+"/"+filePath)
    print(filePath)
    filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"
    # extracted_path = Path(extracted_filename)
    # extracted_path.parent.mkdir(parents=True, exist_ok=True)
    #entity = str(filePath).split('/')[0]
    try:
        generation_config = {
            "temperature":0.9,
            "top_p":1,
            "top_k":0,
            "max_output_tokens":4096
        }
        safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        ]
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest",
                                            generation_config=generation_config,
                                            safety_settings=safety_settings)
        if str(filePath).split('.')[-1]=="pdf":
            patient_report = ""
            with open(extracted_filename,"r", encoding='UTF-8') as f:
                patient_report = f.read()
            prompt = "provide the summary of the below patient report"+patient_report
            response = model.generate_content(prompt)
            input_tokens = response.usage_metadata.prompt_token_count 
            output_tokens = response.usage_metadata.candidates_token_count
            out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="png" or filePath.split('.')[-1]=="jpeg" or filePath.split('.')[-1]=="jpg":
            try:
                image_parts = [
                    {
                        "mime_type": "image/jpeg", ## Mime type are PNG - image/png. JPEG - image/jpeg. WEBP - image/webp
                        "data": file.read_bytes()
                    }
                ]
                system_prompt = """
                        You are a radiologist expert in interpreting MRI scanning reports and identifies abnormalities to provide accurate diagnoses..
                        Input images in the form of MRI sacnning images  will be provided to you,
                        and your task is to respond to questions based on the image.
                        """
                
                user_prompt = "What specific abnormalities or findings were identified in the MRI brain scan image?"
                input_prompt= [system_prompt, image_parts[0], user_prompt]
                response = model.generate_content(input_prompt)
                input_tokens = response.usage_metadata.prompt_token_count 
                output_tokens = response.usage_metadata.candidates_token_count
                out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
                returnData = response.Candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="mp3":
            patient_report = ""
            with open(extracted_filename,"r") as f:
                patient_report = f.read()
            prompt = "provide the summary of the below report \n"+patient_report
            response = model.generate_content(prompt)
            input_tokens = response.usage_metadata.prompt_token_count 
            output_tokens = response.usage_metadata.candidates_token_count
            out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="mp4":
            patient_report = ""
            with open(extracted_filename,"r") as f:
                patient_report = f.read()
            prompt = "provide the summary of the below report \n"+patient_report
            response = model.generate_content(prompt)
            input_tokens = response.usage_metadata.prompt_token_count 
            output_tokens = response.usage_metadata.candidates_token_count
            out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
    except Exception as e:
        print("Error:"+filePath,e)
        return "Some error occured"

def data_extraction(filePath,workspace_path):
    # dbParams = json.loads(request.args.get("dbParams"))
    # filePath = dbParams['selectedFile']
    print("Entered multimodal extraction for file "+filePath)
    fileAbs = Path(filePath)
    file = Path(workspace_path+"/"+filePath)
    print(filePath)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"
    extracted_path = Path(extracted_filename)
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    #entity = str(filePath).split('/')[0]
    patient_report = ""
    try:
        generation_config = {
            "temperature":0.9,
            "top_p":1,
            "top_k":0,
            "max_output_tokens":4096
        }
        safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        ]
        if str(filePath).split('.')[-1]=="pdf":
            patient_report = pdf_2_txt(file)
            with open(extracted_filename,"w+", encoding='UTF-8') as f:
                f.write(patient_report)
                print("written extracted text to file")
        elif str(filePath).split('.')[-1]=="mp3":
            patient_report = extract_audio_text(f"{file.parent}/{file.name}")
            with open(extracted_filename,"w+", encoding='UTF-8') as f:
                f.write(patient_report)
                print("written extracted text to file")
            
        elif str(filePath).split('.')[-1]=="mp4":
            patient_report = extract_video_text(f"{file.parent}/{file.name}")
            with open(extracted_filename,"w+", encoding='UTF-8') as f:
                f.write(patient_report)
                print("written extracted text to file")
        return patient_report
    except Exception as e:
        print("Error:"+filePath,e)
        return "Some error occured"

# @app.route("/gemini_multimodal_summary")
def gemini_multimodal_aifeature(filePath,aifeature,workspace_path):
    # dbParams = json.loads(request.args.get("dbParams"))
    # filePath = dbParams['selectedFile']
    print("Entered multimodal ai feature "+aifeature+" for file "+filePath)
    fileAbs = Path(filePath);
    file = Path(workspace_path+"/"+filePath)
    print(filePath)
    filename = f"static/OutputCache/{aifeature}/{fileAbs.parent}/{fileAbs.stem}.txt"
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"

    #entity = str(filePath).split('/')[0]
    try:
        generation_config = {
            "temperature":0.9,
            "top_p":1,
            "top_k":0,
            "max_output_tokens":4096
        }
        safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        ]
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest",
                                            generation_config=generation_config,
                                            safety_settings=safety_settings)
        if str(filePath).split('.')[-1]=="pdf":
            f=open(extracted_filename,'r',encoding='UTF-8')
            patient_report = f.read()
            prompt = ""
            if aifeature == "Sentiment":
                prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"+patient_report
            elif aifeature == "Emotion":
                prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"+patient_report
            elif aifeature == "Tone":
                prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"+patient_report
            elif aifeature == "EnglishMaturity":
                prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + patient_report
            response = model.generate_content(prompt)
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,"w") as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename, 'w') as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="png" or filePath.split('.')[-1]=="jpeg" or filePath.split('.')[-1]=="jpg":
            try:
                user_prompt = ""
                image_parts = [
                    {
                        "mime_type": "image/jpeg", ## Mime type are PNG - image/png. JPEG - image/jpeg. WEBP - image/webp
                        "data": file.read_bytes()
                    }
                ]
                system_prompt = """
                        You are a radiologist expert in interpreting MRI scanning reports and identifies abnormalities to provide accurate diagnoses..
                        Input images in the form of MRI sacnning images  will be provided to you,
                        and your task is to respond to questions based on the image.
                        """
                if aifeature == "Sentiment":
                    user_prompt = "provide the sentiment of  image in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"
                elif aifeature == "Emotion":
                    user_prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"
                elif aifeature == "Tone":
                    user_prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"
                elif aifeature == "EnglishMaturity":
                    user_prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n"
            
                input_prompt= [system_prompt, image_parts[0], user_prompt]
                response = model.generate_content(input_prompt)
                returnData = response.Candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,'w') as f:
                        f.write(returnData)
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename,'w') as f:
                        f.write(returnData)
                return returnData
            finally:
                f=open(filename,'r')
                return f.read() 
        elif str(filePath).split('.')[-1]=="mp3":
            f=open(extracted_filename,'r')
            patient_report = f.read()
            prompt = ""
            if aifeature == "Sentiment":
                prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"+patient_report
            elif aifeature == "Emotion":
                prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"+patient_report
            elif aifeature == "Tone":
                prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"+patient_report
            elif aifeature == "EnglishMaturity":
                prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + patient_report
            response = model.generate_content(prompt)
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,"w") as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename, 'w') as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="mp4":
            f=open(extracted_filename,'r')
            patient_report = f.read()
            prompt = ""
            if aifeature == "Sentiment":
                prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"+patient_report
            elif aifeature == "Emotion":
                prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"+patient_report
            elif aifeature == "Tone":
                prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"+patient_report
            elif aifeature == "EnglishMaturity":
                prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + patient_report
            response = model.generate_content(prompt)
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,"w") as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename, 'w') as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
    except Exception as e:
        print("Error:"+filePath,e)
        return "Some error occured"
    
def get_access_token():
    # Load Google Playground credentials from environment variables
    client_id = os.getenv("GOOGLE_CLIENT_ID")

    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
   
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
   

    # Make a request to the Google OAuth 2.0 token endpoint to get a new access token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        return access_token
    else:
        print(f"Error fetching access token: {response.status_code}, {response.text}")
        return None


def update_dates(data):
    new_data = {}
    for category, values in data.items():
        new_data[category] = []
        new_json = {}
        current_date = datetime.now().strftime("%Y-%m-%d")
        previous_date = None
        
        for date, value in reversed(values[0].items()):
            if previous_date is None:
                previous_date = datetime.strptime(current_date, "%Y-%m-%d")
                new_json[current_date] = value
            else:
                previous_date = previous_date - timedelta(days=1)
                new_json[previous_date.strftime("%Y-%m-%d")] = value
        
        new_data[category].append(new_json)
    
    return new_data

@app.route("/get_google_fit_data_old")
def google_fit_data_old():
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgsw-RXQOmz73-e35V6dd7JtjrsiS2wZuDd-wnCrdApgnCoISpNjy5nDFrXhMf3aUoiMEcKfZt9IyntKm1ZZId2VbCat91MsBYK5QfKxo8znkCFYcyNjNGV6wtblHrX0Pl93G0gHFK_up6f_XNrFIGTtEugHpaCgYKARcSARASFQHGX2MikwDwTPfwHGEcuhQNkqL_kw0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)
        
        # Replace with your specific data source ID for Heart Points
        data_source_id = 'derived:com.google.heart_minutes:com.google.android.gms:merge_heart_minutes'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)
        

        if response.status_code == 200:
            dataset = response.json()
            heart_points_by_date = defaultdict(float)
            
            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    heart_points_by_date[date] += value.get("fpVal", 0)
            
            heart_points_json = dict(heart_points_by_date)
            # print(heart_points_json)
        else:
            print(f"Error retrieving data: {response.status_code}, {response.text}")
        
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)
        # Replace with your specific data source ID for Step Count
        data_source_id = 'derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            steps_by_date = defaultdict(int)
            
            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    steps_by_date[date] += value.get("intVal", 0)
            
            steps_json = dict(steps_by_date)
            # print(steps_json)
        else:
            print(f"Error retrieving data: {response.status_code}, {response.text}")
        
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)
        # Replace with your specific data source ID for Calories Burned
        data_source_id = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            calories_by_date = defaultdict(float)
            
            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date =datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    calories_by_date[date] += value.get("fpVal", 0)
            
            calories_json = dict(calories_by_date)
            # print(calories_json)
        else:
            print(f"Error retrieving data: {response.status_code}, {response.text}")
        data = {"Heartpoints": [heart_points_json], "StepCount":[steps_json], "CaloriesBurned":[calories_json]}
        new_data = {}
        for key, value in data.items():
            new_data[key] = []
            for item in value:
                for date, val in item.items():
                    new_data[key].append({"date": date, "value": round(val, 2)})
        with open('static/OutputCache/google_fit_cache.json', 'w') as f:
            json.dump(data, f)
        print(json.dumps(new_data))
        return new_data
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_cache.json'):
            with open('static/OutputCache/google_fit_cache.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            return new_data
        return None

def update_dates(data):
    new_data = {}
    for category, values in data.items():
        new_data[category] = []
        new_json = {}
        current_date = datetime.now().strftime("%Y-%m-%d")
        previous_date = None

        for date, value in reversed(values[0].items()):
            if previous_date is None:
                previous_date = datetime.strptime(current_date, "%Y-%m-%d")
                new_json[current_date] = value
            else:
                previous_date = previous_date - timedelta(days=1)
                new_json[previous_date.strftime("%Y-%m-%d")] = value

        new_data[category].append(new_json)

    return new_data

def get_heart_points(heart_points: str) -> str:
    """Fetches the Heart points for last 10 days from google fit API."""
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgv81bpH63OAy6-xuMAnIx0DTQTmS27HkaZjB3ITW1bYZAqeHMxzYKwZJa3g5HMzveyrJ9xfaI5GO7E4bLdpgZMamDPGnTXBDOd-wq3Lxh5fvuCvpOdrJD37Z3auwQV7cHiMVOCbznQ8DfiE_fosk7I02-728fJ7aCgYKASkSARASFQHGX2Mik8uAsJ3mL0eD3Ns8u9EgVg0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)

        # Replace with your specific data source ID for Heart Points
        data_source_id = 'derived:com.google.heart_minutes:com.google.android.gms:merge_heart_minutes'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)


        if response.status_code == 200:
            dataset = response.json()
            heart_points_by_date = defaultdict(float)

            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    heart_points_by_date[date] += value.get("fpVal", 0)

            heart_points_json = dict(heart_points_by_date)
            # print(heart_points_json)
            data = {"Heartpoints": [heart_points_json]}
            new_data = {}
            for key, value in data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            with open('static/OutputCache/google_fit_heartpoints.json', 'w') as f:
                json.dump(data, f)
            print(json.dumps(new_data))
            return new_data
        else:
            if os.path.exists('static/OutputCache/google_fit_heartpoints.json'):
                with open('static/OutputCache/google_fit_heartpoints.json', 'r') as f:
                    data =  json.load(f)
                shifted_data = update_dates(data)
                new_data = {}
                for key, value in shifted_data.items():
                    new_data[key] = []
                    for item in value:
                        for date, val in item.items():
                            new_data[key].append({"date": date, "value": round(val, 2)})
                print("heart points", new_data)
                return new_data
            else:
                return "Error retrieving data"
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_heartpoints.json'):
            with open('static/OutputCache/google_fit_heartpoints.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            print("heart points", new_data)
            return new_data
        else:
            return "Error retrieving data"

def get_steps(steps: str, reason: str) -> str:
    """Fetches the steps count for last 10 days from google fit API."""
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgv81bpH63OAy6-xuMAnIx0DTQTmS27HkaZjB3ITW1bYZAqeHMxzYKwZJa3g5HMzveyrJ9xfaI5GO7E4bLdpgZMamDPGnTXBDOd-wq3Lxh5fvuCvpOdrJD37Z3auwQV7cHiMVOCbznQ8DfiE_fosk7I02-728fJ7aCgYKASkSARASFQHGX2Mik8uAsJ3mL0eD3Ns8u9EgVg0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)

        # Replace with your specific data source ID for Step Count
        data_source_id = 'derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            steps_by_date = defaultdict(int)

            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    steps_by_date[date] += value.get("intVal", 0)

            steps_json = dict(steps_by_date)
            # print(steps_json)
            data = {"Steps": [steps_json]}
            new_data = {}
            for key, value in data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            with open('static/OutputCache/google_fit_steps.json', 'w') as f:
                json.dump(data, f)
            print(json.dumps(new_data))
            return new_data
        else:
            if os.path.exists('static/OutputCache/google_fit_steps.json'):
                with open('static/OutputCache/google_fit_steps.json', 'r') as f:
                    data =  json.load(f)
                shifted_data = update_dates(data)
                new_data = {}
                for key, value in shifted_data.items():
                    new_data[key] = []
                    for item in value:
                        for date, val in item.items():
                            new_data[key].append({"date": date, "value": round(val, 2)})
                return new_data
            else:
                return "Error retrieving data"
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_steps.json'):
            with open('static/OutputCache/google_fit_steps.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            return new_data
        else:
            return "Error retrieving data"

def get_calories(calories: str, reason: str) -> str:
    """Fetches the calories burned for last 10 days from google fit API."""
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgv81bpH63OAy6-xuMAnIx0DTQTmS27HkaZjB3ITW1bYZAqeHMxzYKwZJa3g5HMzveyrJ9xfaI5GO7E4bLdpgZMamDPGnTXBDOd-wq3Lxh5fvuCvpOdrJD37Z3auwQV7cHiMVOCbznQ8DfiE_fosk7I02-728fJ7aCgYKASkSARASFQHGX2Mik8uAsJ3mL0eD3Ns8u9EgVg0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)

         # Replace with your specific data source ID for Calories Burned
        data_source_id = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            calories_by_date = defaultdict(float)

            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date =datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    calories_by_date[date] += value.get("fpVal", 0)

            calories_json = dict(calories_by_date)
            # print(calories_json)
            data = {"CaloriesBurned": [calories_json]}
            new_data = {}
            for key, value in data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            with open('static/OutputCache/google_fit_calories.json', 'w') as f:
                json.dump(data, f)
            print(json.dumps(new_data))
            return new_data
        else:
            if os.path.exists('static/OutputCache/google_fit_calories.json'):
                with open('static/OutputCache/google_fit_calories.json', 'r') as f:
                    data =  json.load(f)
                shifted_data = update_dates(data)
                new_data = {}
                for key, value in shifted_data.items():
                    new_data[key] = []
                    for item in value:
                        for date, val in item.items():
                            new_data[key].append({"date": date, "value": round(val, 2)})
                return new_data
            else:
                return "Error retrieving data"
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_calories.json'):
            with open('static/OutputCache/google_fit_calories.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            return new_data
        else:
            return "Error retrieving data"

@app.route("/get_google_fit_data")  
def get_google_fit_data():
    chat_model = genai.GenerativeModel(
        model_name='gemini-1.5-flash-latest',
        tools=[get_heart_points, get_steps, get_calories] # list of all available tools
    )

    """### alway use the model in chat mode for function calling"""

    chat = chat_model.start_chat(enable_automatic_function_calling=True)


    response = chat.send_message('Give the heart points for the last 10 days. Return only function response without any additional text')
    heart_json = str(response.candidates[0].content.parts[0].text)

    response = chat.send_message('Give the steps count for the last 10 days')
    steps_json = str(response.candidates[0].content.parts[0].text)

    response = chat.send_message('Give the calories burned for the last 10 days')
    calories_json = str(response.candidates[0].content.parts[0].text)

    return {"heart_json":heart_json,"steps_json":steps_json,"calories_json":calories_json}

@app.route("/explain_fit_data")
def explain_fit_data():
    dbParams = json.loads(request.args.get("dbParams"))
    fit_json = dbParams['fitJson']
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Explain the condition of person or patient based on provided json data extracted from google fit.\n\n" + fit_json
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-FitData-Summary.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_fitdata_summary done")
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()



#@app.route("/get_opentext_auth_token",methods = ['GET'])
def get_opentext_auth_token():
    url = "https://us.api.opentext.com/tenants/6940d09e-0f19-4929-9618-724037d07bc3/oauth2/token"
    payload = 'grant_type=client_credentials&client_secret=encoded&client_id=encoded'
    headers = {
    'Authorization': 'Basic cDVlZ3BlTktPM3hsbHJOTkxSVDBoMEEzMVJ3NWpDMDM6WTl4S1U1QWpkaHZaNms0OA==',
    'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_data = response.json()
    token = response_data["access_token"]
    return token



# @app.route("/get_opentext_auth_token_for_ocp",methods = ['GET'])
def get_opentext_auth_token_for_ocp():
    #First we're going to login to the OT2 authentication service
    print("Logging in to OT2")
    
    #This is the Autehntication URL
    #eu "https://otdsauth.ot2.opentext.eu/oauth2/token"
    authUrl = "https://us.api.opentext.com/tenants/6940d09e-0f19-4929-9618-724037d07bc3/oauth2/token"
    
    # authUrl = "https://otdsauth.ot2.opentext.com/oauth2/token"
    #Now create the Login request
    loginRequest = {}
    loginRequest['grant_type'] = 'client_credentials'
    loginRequest['username'] = 'dataflow.expedition@gmail.com'
    loginRequest['password'] = 'Infy1234567@'
    loginRequest['subscriptionName'] = 'cap-69616598-1c0a-44b7-8ec7-8d0bf8edcffa-1017'
    
    #Take the client secret from the developer console and convert it to base 64
    client = 'scsO1Sw0e0uogucXQ9W6YY79aVA1Rt3G'
    secret = 'obGeo8A1aBH077nP'
    clientSecret = client + ':' + secret
    csEncoded = base64.b64encode(clientSecret.encode())
    
    # You now need to decode the Base64 to a string version
    csString = csEncoded.decode('utf-8')
    
    #Add the Client Secret and content Type to the request header
    loginHeaders={}
    loginHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
    loginHeaders['Authorization'] = "Basic " + csString
    
    #Now post the request
    r = requests.post(authUrl,data=loginRequest,headers=loginHeaders)
    loginResponse = json.loads(r.text)
    
    #Get the Access Token from the request
    accessToken = loginResponse['access_token']
    return accessToken

@app.route("/get_opentext_auth_token_for_ocp_sign",methods = ['GET'])
def get_opentext_auth_token_for_ocp_sign():
    #First we're going to login to the OT2 authentication service
    print("Logging in to OT2")
    
    #This is the Autehntication URL
    #eu "https://otdsauth.ot2.opentext.eu/oauth2/token"
    authUrl = "https://us.api.opentext.com/tenants/6940d09e-0f19-4929-9618-724037d07bc3/oauth2/token"
    
    # authUrl = "https://otdsauth.ot2.opentext.com/oauth2/token"
    #Now create the Login request
    loginRequest = {}
    loginRequest['grant_type'] = 'client_credentials'
    loginRequest['username'] = 'dataflow.expedition@gmail.com'
    loginRequest['password'] = 'Infy1234567@'
    loginRequest['subscriptionName'] = 'cap-69616598-1c0a-44b7-8ec7-8d0bf8edcffa-1017'
    
    #Take the client secret from the developer console and convert it to base 64
    client = 'scsO1Sw0e0uogucXQ9W6YY79aVA1Rt3G'
    secret = 'obGeo8A1aBH077nP'
    clientSecret = client + ':' + secret
    csEncoded = base64.b64encode(clientSecret.encode())
    
    # You now need to decode the Base64 to a string version
    csString = csEncoded.decode('utf-8')
    
    #Add the Client Secret and content Type to the request header
    loginHeaders={}
    loginHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
    loginHeaders['Authorization'] = "Basic " + csString
    
    #Now post the request
    r = requests.post(authUrl,data=loginRequest,headers=loginHeaders)
    loginResponse = json.loads(r.text)
    
    #Get the Access Token from the request
    accessToken = loginResponse['access_token']
    return accessToken

@app.route("/ocp_full_page_ocr",methods = ["GET"])
def ocp_full_page_ocr():
    token = get_opentext_auth_token_for_ocp()

@app.route("/get_list_ocr",methods = ["GET"])
def get_list_ocr():
    # baseURL = 'https://capture.ot2.opentext.com/cp-rest/session'
    accessToken = get_opentext_auth_token_for_ocp()
    serviceHeaders = {}
    serviceHeaders['Authorization'] = 'Bearer ' + accessToken
    serviceHeaders['Content-Type'] = 'application/hal+json; charset=utf-8'
    baseURL = 'https://us.api.opentext.com/capture/cp-rest/v2'
    #Now for the file resource
    uploadURL = baseURL + '/session/doctypes?Env=D'
    
    uploadRequest = requests.get(uploadURL,headers=serviceHeaders)
    res = json.loads(uploadRequest.text)
    return res

@app.route("/upload_file_ocr",methods=["GET"])
def upload_file_ocr():
    payload = {}
    accessToken = get_opentext_auth_token_for_ocp()
    #use this token in all future headers
    #Create the service headers
    serviceHeaders = {}
    serviceHeaders['Authorization'] = 'Bearer ' + accessToken
    serviceHeaders['Content-Type'] = 'application/hal+json; charset=utf-8'
     #Now we're going to upload the Image
    print('Uploading Image')
    #Create Image Upload object
    
    imageUpload = {}
    
    #Open the file and convert it to a Base 64 String
    #fileName = '../Workspace/slope.expedition@gmail.com/PatientWorkspace/DataFiles/AmyCripto/Amy_Cripto_EncounterDetails.pdf'
    fileName = 'static/MyFirstInvoice.jpg'
    #we'll use this for later
    originalFileName = ntpath.basename(fileName)
    
    imageFile = open(fileName,'rb').read()
    imageB64 = base64.encodebytes(imageFile)
    
    #Assign this string to a data element called data
    imageUpload['data'] = imageB64.decode('utf-8')
    
    #Now get the Mimetype of the file
    #add 0 to get ('image/tiff', None)
    mime = mimetypes.guess_type(fileName)[0]
    imageUpload['contentType'] = mime
    #Now convert the object to json
    uploadJson = json.dumps(imageUpload)
    # print(uploadJson)
    #Now upload the image
    #base url for all commands
    #eu 'https://capture.ot2.opentext.eu/cp-rest/session'
    # baseURL = 'https://capture.us.opentext.com/capture/cp-rest/session/v2'
    baseURL = 'https://us.api.opentext.com/capture/cp-rest/v2/session'
    #Now for the file resource
    uploadURL = baseURL + '/files'
    
    uploadRequest = requests.post(uploadURL,data=uploadJson,headers=serviceHeaders)
    print(uploadRequest)
    uploadResponse = json.loads(uploadRequest.text)
    
    #get the image id
    # uploadFileID = uploadResponse['id']
    # uploadContentType = uploadResponse['contentType']
    return uploadResponse

@app.route("/get_file_risk_guard",methods = ['GET'])
def get_file_risk_guard():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    file_path = workspace_dir_path+'/'+filePath
    url = "https://us.api.opentext.com/mtm-riskguard/api/v1/process"
    payload = {}
    token = get_opentext_auth_token()
    headers = {
    'Authorization': 'Bearer '+token
    }
    with open(file_path, 'rb') as fobj:
        response = requests.request("POST", url, headers=headers, data=payload, files={"File":fobj})
    return response.json()

    
if __name__ == '__main__':
    app.run(debug=True,port=5505)
    # mlflow_process.terminate()
    # app.run(host='0.0.0.0',port=5505)
