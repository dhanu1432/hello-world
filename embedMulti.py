import openai
import json
import time
import numpy as np
from tqdm import tqdm
import os

from dotenv import load_dotenv

load_dotenv()  

api_key = os.getenv("OPENAI_API_KEY")
print("api_key: " + api_key)
client = openai.OpenAI(api_key=api_key)

# Load data from data.json
with open("data.json", "r") as f:
    queries = json.load(f)

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

output_data = []

for q in tqdm(queries):
    try:
        embedding = get_embedding(q["text"])
        output_data.append({
            "embedding": embedding.tolist(),
            "label": q["label"]
        })
        time.sleep(0.5)  # Optional: rate limit control
    except Exception as e:
        print(f"Error embedding '{q['text']}': {e}")

# Save to output file
with open("labeled_embeddings.json", "w") as f:
    json.dump(output_data, f)