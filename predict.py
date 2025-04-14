import torch
import torch.nn as nn
import numpy as np
import openai
import os
from dotenv import load_dotenv

# ------------------------------
# Load API Key
# ------------------------------
load_dotenv()  
api_key = os.getenv("OPENAI_API_KEY")
print("api_key: " + api_key)
client = openai.OpenAI(api_key=api_key)
# ------------------------------
# GRU Classifier
# ------------------------------
class GRUClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim=64):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 2)

    def forward(self, x):
        x = x.unsqueeze(1)
        _, h = self.gru(x)
        logits = self.fc(h.squeeze(0))
        return logits

# ------------------------------
# Embedding Function
# ------------------------------
def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

# ------------------------------
# Prediction
# ------------------------------
def predict(model, embedding):
    x = torch.tensor(embedding, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        output = model(x)
        pred = torch.argmax(output, dim=1).item()
        return "yes" if pred == 1 else "no"

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    user_input = input("Enter user input: ")
    embedding = get_embedding(user_input)

    input_dim = len(embedding)
    model = GRUClassifier(input_dim)
    model.load_state_dict(torch.load("gru_classifier.pt", map_location=torch.device('cpu')))
    model.eval()

    prediction = predict(model, embedding)
    print(f"Prediction: {prediction}")