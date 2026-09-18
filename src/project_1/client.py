from openai import OpenAI
from .config import MODEL_NAME

client = OpenAI()

def call_model(instructions:str, user_input:str) -> str:
    '''Send request to model and return output text'''
    response = client.responses.create(
        model = MODEL_NAME,
        instructions = instructions,
        input = user_input,
    )
    
    return response.output_text.strip()
    