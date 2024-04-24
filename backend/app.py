import certifi
from flask import Flask, jsonify, request
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import json
import groq
from groq import Groq
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import openai
from typing import List
import sqlite3

load_dotenv('.env')
client = Groq(api_key=os.getenv('API_KEY'))

app = Flask(__name__)
CORS(app)

ca = certifi.where()


uri = "{YOUR MONGO DB DB CLUSTER NAME}"
embedding_model_string = 'nomic-ai/nomic-embed-text-v1.5'
mongo_client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=ca)

fw_client = openai.OpenAI(
    api_key="{YOUR API KEY}",
    base_url="https://api.fireworks.ai/inference/v1"
)

def generate_embeddings(input_texts: str, model_api_string: str, prefix="") -> List[float]:
    if prefix:
        input_texts = [prefix + text for text in input_texts]
    return fw_client.embeddings.create(
        input=input_texts,
        model=model_api_string,
    ).data[0].embedding

def load_transcript(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def merge_captions(transcript, max_words=50):
    chunks = []
    current_chunk = []
    current_words = 0
    last_end_time = 0

    for caption in transcript:
        start_time = caption['start']
        duration = caption['duration']
        end_time = start_time + duration
        words = caption['text'].split()

        if (start_time < last_end_time + 2) and (current_words + len(words) <= max_words):
            current_chunk.append(caption['text'])
            current_words += len(words)
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [caption['text']]
            current_words = len(words)

        last_end_time = end_time

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def store_embeddings(chunks, video_id):
    db = mongo_client['ygpt']
    collection = db['ygpt_data']

    for i, chunk in enumerate(chunks):
        embedding_output = generate_embeddings(chunk, embedding_model_string)
        document = {
            "video_id": video_id,
            "text": chunk,
            "embedding": embedding_output
        }
        collection.insert_one(document)

def get_llm_answer(context: str, user_query: str):
    try:
        completion = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {
                    "role": "user",
                    "content": f"Answer the question based only on the following context:\n{context}\n\nQuestion:\n{user_query}"
                },
            ],
            temperature=0,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )

        return completion.choices[0].message.content
    except groq.APIConnectionError as e:
        print(e)
        return "500: GROQ Internal server error"
    except groq.RateLimitError as e:
        print(e)
        return "429: GROQ Rate Limit Reached"
    except groq.APIStatusError as e:
        print(e)
        return e
    except Exception as e:
        print(e)
        return e


@app.route("/load", methods=['POST'])
def load():
    data = request.json
    video_id = data.get('video_id')

    conn = sqlite3.connect('videos.db')
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS videos
                 (video_id text PRIMARY KEY)''')

    # Check if video_id is already in the database
    c.execute("SELECT 1 FROM videos WHERE video_id=?", (video_id,))
    if c.fetchone():
        # Video ID found, return instant 200 response
        return jsonify({'message': 'Video ID already processed'}), 200


    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except:
        transcript = "No subtitles found!"
        return jsonify({'message': transcript})

    json_formatted = json.dumps(transcript, indent=2)

    with open('transcript.json', 'w', encoding='utf-8') as json_file:
        json_file.write(json_formatted)

    transcript_data = load_transcript('transcript.json')
    chunks = merge_captions(transcript_data)
    store_embeddings(chunks, video_id)

    # Add video ID to SQLite database
    c.execute("INSERT INTO videos (video_id) VALUES (?)", (video_id,))
    conn.commit()

    return jsonify({'message': 'Transcript loaded and embeddings stored successfully'})


@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.json
    user_query = data.get('user_query')
    video_id = data.get('video_id')

    query_embedding = generate_embeddings(user_query, embedding_model_string)

    top_k = 5
    search_results = search_relevant_chunks(video_id, query_embedding, top_k)
    print(search_results)

    chunk_texts = extract_chunk_texts(search_results)
    context = form_context(chunk_texts)
    print(context)

    llm_output = get_llm_answer(context, user_query)
    return jsonify({'llm_output': llm_output})


@app.route("/")
def helloWorld():
    return "Hello, hackers! Backend working"


def search_relevant_chunks(video_id, query_embedding, top_k):
    db = mongo_client['ygpt']
    collection = db['ygpt_data']

    pipeline = [
        {
            '$vectorSearch': {
                'index': 'vector_index',
                'path': 'embedding',
                'queryVector': query_embedding,
                'numCandidates': 200,
                'limit': top_k
            }
        },
        {
            '$match': {
                'video_id': video_id
            }
        },
        {
            '$project': {
                '_id': 0,
                'text': 1,
                'score': {
                    '$meta': 'vectorSearchScore'
                }
            }
        }
    ]

    results = collection.aggregate(pipeline)
    print(results)

    return list(results)


def extract_chunk_texts(search_results):
    chunk_texts = [result['text'] for result in search_results]
    return chunk_texts


def form_context(chunk_texts):
    context = ' '.join(chunk_texts)
    print(context)
    return context
