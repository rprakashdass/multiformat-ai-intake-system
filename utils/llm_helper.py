# utils/llm_helper.py
import sys
import os
import google.generativeai as genai
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.config import settings

# Configure the Gemini API client
genai.configure(api_key=settings.GOOGLE_API_KEY)

def get_gemini_model(model_name: str):
    """
    Returns a configured Gemini generative model.
    """
    return genai.GenerativeModel(model_name=model_name)

def  generate_output_from_prompt(
    prompt: str,
    model_name: str = "gemini-2.0-flash",
    temperature: float = 0.3,
    max_output_tokens: int = 2048
) -> str:
    """
    Generates text using the specified Gemini model.
    """
    model = get_gemini_model(model_name)
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json"
    }
    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return response.text
    except Exception as e:
        print(f"Error generating text: {e}")
        return ""

if __name__ == "__main__":
    # Testing the LLM 
    print("Testing Gemini LLM helper...")
    test_prompt = "What is Agentic AI?"
    response =  generate_output_from_prompt(test_prompt)
    print(f"Response: {response}")