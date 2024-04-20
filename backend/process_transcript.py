import json
import pprint
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import openai
from typing import List

uri = "mongodb+srv://pgarg4:TE8HRkPMv18iBj64@cluster0.7y0k8ar.mongodb.net" 
embedding_model_string = 'nomic-ai/nomic-embed-text-v1.5'
video_id = 1
client = MongoClient(uri, server_api=ServerApi('1'))
fw_client = openai.OpenAI(
  api_key="et9MwRyCcuEHGK5JQqTHKIgWAZEaYwB5GAbnlA0RkF8ZAaZT", 
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

def store_embeddings(chunks):
    db = client['ygpt']
    collection = db['ygpt_data']

    for i, chunk in enumerate(chunks):
#        print('\n'+f"Chunk {i+1}:")
#        pprint.pprint(chunk)
        embedding_output = generate_embeddings(chunk, embedding_model_string)
        document = {
	    "video_id":1,
            "text": chunk,
            "embedding": embedding_output
        }
        collection.insert_one(document)
#        print(f"Embedding size is: {str(len(sample_output))}")
#        print(sample_output)

def main():
    file_path = 'transcript.json'
    
    transcript = load_transcript(file_path)
    
    chunks = merge_captions(transcript)

    store_embeddings(chunks)

if __name__ == "__main__":
    main()
