from flask import Flask, jsonify, request
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import json
import groq
from groq import Groq
import os
from dotenv import load_dotenv
load_dotenv('.env')
print(os.getenv('API_KEY'))
client = Groq(api_key=os.getenv('API_KEY'))

app = Flask(__name__)
CORS(app)

def get_llm_answer(context:str, user_query:str):
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

  # search postgres database
  # if video_id found -> return instant 200 response

  try:
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi','en'])
  except:
    transcript = "No subtitles found!"
  
  json_formatted = json.dumps(transcript, indent=2)

  with open('transcript.json', 'w', encoding='utf-8') as json_file:
      json_file.write(json_formatted)

  # Next steps:
  # transcript.json -> merge various lines and create chunks
  # convert created chunks -> vector embeddings
  # vector embeddings -> Vector DB

  #todo: Change the response to something else
  return jsonify({'transcript': transcript})


@app.route('/get_response', methods=['POST'])
def get_response():
  data = request.json
  user_query = data.get('user_query')
  video_id = data.get('video_id')

  # Next steps
  # user_query -> vector embedding -> search Vector DB
  # return context from vector DB

  # hardcoding context here, this should come from vector db
  context = "okay, so let's talk about our very vast solar system. Jupyter is the largest planet in our solar system."
  llm_output = get_llm_answer(context, user_query)
  return jsonify({'llm_output': llm_output})


@app.route("/")
def helloWorld():
  return "Hello, hackers! Backend working"
