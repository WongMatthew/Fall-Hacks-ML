from fastapi import FastAPI, File, UploadFile, status
import os
from dotenv import load_dotenv
import requests
import nltk
nltk.download('punkt')
import math
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

app = FastAPI()

@app.get('/')
async def home():
    return {'response': 'success'}

# Receive video file from client and get the file extension using fastapi
@app.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)):
    # Get the filename of the file
    filename = file.filename
    # Get the extension of the file
    _ , extension = filename.split('.')
    # Write the file
    with open(f"file.{extension}" , "wb") as f:
        f.write(file.file.read())

    #Upload the video or audio to assembly ai
    file = upload_file(open(f"file.{extension}" , "rb"))
    # Remove the file
    os.remove(f"file.{extension}")
    #Get the response from assembly ai
    response = get_text(file[0], file[1])
    # Initialize a counter to keep track of the number of requests made to assembly ai
    index = 0
    #Check if response was not ready
    while response["status"] != 'completed':
        # Increment the counter and get the updated response
        index += 1
        response = get_text(file[0], file[1])

    print(f"Requests to assemblyAI: {index} times done")

    # Add the summarized text to the response
    response.update({'summerize': summerize(response['text'])})

    return response

def summerize(original_text):
    '''
    Summarize the given text using the LexRank algorithm

    --Params--
    original_text: The text to summerize
    Return Value: sentences
    sentences : The summerized text
    '''
    # Split the text into a list of words
    text_list = original_text.split()

    # Get the number of words in the text
    num_words = len(text_list)

    # Calculate the number of sentences to include in the summary
    count = math.ceil(num_words/70)

    # Parse the text using the PlaintextParser and Tokenizer
    my_parser = PlaintextParser.from_string(original_text,Tokenizer('english'))

    # Create a LexRankSummarizer object
    lex_rank_summarizer = LexRankSummarizer()
    # Summarize the text using the LexRank algorithm
    lexrank_summary = lex_rank_summarizer(my_parser.document,sentences_count=count)

    # Concatenate the summary sentences into a single string
    sentences = ''
    for sentence in lexrank_summary:
        sentences = sentences + str(sentence)
    return sentences

def upload_file(fileObj):
    '''
    Upload a file to AssemblyAI and get the transcribe id and API key

    Parameter:
    fileObj: The File Object to transcribe
    Return Value:
    token : The API key
    transcribe_id: The ID of the file which is being transcribed
    '''
    # Load the API key from the .env file
    load_dotenv()
    token = os.getenv('API_TOKEN')
    # Get the URL of the file
    file_url = get_url(token, fileObj)
    # Get the transcribe ID of the file
    transcribe_id = get_transcribe_id(token,file_url)
    return token,transcribe_id

def get_text(token, transcribe_id):
    '''
    Get the text from the file

    --Params--
    token: The API key
    transcribe_id: The ID of the file which is being
     Return Value: result
     result : The response object
    ''' 
    # Get the response from the API
    endpoint= f'https://api.assemblyai.com/v2/transcript/{transcribe_id}'
    headers = {'authorization': token}
    result = requests.get(endpoint, headers=headers).json()
    return result

def get_transcribe_id(token,url):
    '''
    Get the transcribe id of the file

    --Params--
    token: The API key
    url : Url to uploaded file
    Return Value: id
    id : The transcribe id of the file
    '''
    # Set the endpoint, json and headers
    endpoint = 'https://api.assemblyai.com/v2/transcript'
    json = {'audio_url': url}
    headers = {'authorization': token, 'content-type': 'application/json'}
    # Make the POST request
    response = requests.post(endpoint, json=json, headers=headers)
    # Get the transcribe id from response
    transcribe_id = response.json()['id']
    print('Made request and file is currently queued')
    return transcribe_id

def get_url(token,data):
    '''
    Get the url of the file

    --Params--
    token: The API key
    data : The File Object to upload
    Return Value: url
    url : Url to uploaded file
    '''
    # Set the endpoint, json and headers
    headers = {'authorization': token}
    response = requests.post('https://api.assemblyai.com/v2/upload',
    headers=headers,
    data=data)
    # Get the URL of the uploaded file from the response
    url = response.json()['upload_url']
    print('Uploaded File and got temporary URL to file')
    return url