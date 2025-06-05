import json
import logging
import google.generativeai as genai

# For file routing
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

from config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Gemini API Configuration
genai.configure(api_key=settings.GOOGLE_API_KEY)
logger.info("Google Generative AI configured.")

def get_gemini_model(model_name: str):
    """
    Returns a configured Gemini generative model instance.
    """
    try:
        model = genai.GenerativeModel(model_name=model_name)
        logger.debug(f"Gemini model '{model_name}' retrieved successfully.")
        return model
    except Exception as e:
        logger.error(f"Failed to retrieve Gemini model '{model_name}': {e}")
        raise

def generate_output_from_prompt(
    formatted_prompt: str,
    model_name: str = "gemini-2.0-flash",
    temperature: float = 0.3,
    max_output_tokens: int = 2048
) -> str:
    """
    Generates text using the specified Gemini model.
    The prompt should be pre-formatted with any required input data.

    Returns:
        str: The generated text response, or a JSON string with an error message.
    """
    try:
        model = get_gemini_model(model_name)
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": "application/json"
        }

        logger.info(f"Attempting to generate content using model '{model_name}'...")
        logger.debug(f"Prompt: {formatted_prompt[:200]}...")

        response = model.generate_content(
            formatted_prompt,
            generation_config=generation_config
        )
        logger.info("Content generation successful.")
        return response.text
    except Exception as e:
        logger.error(f"Error generating text from LLM with model '{model_name}': {e}")
        return json.dumps({"error": f"LLM generation failed: {e}", "raw_prompt_snippet": formatted_prompt[:200]})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info(" Testing Gemini LLM helper locally ")

    test_json_prompt = """
    You are an AI assistant. Provide a JSON object with a single key "answer" and its value being a concise answer to "What is Agentic AI?".
    """
    logger.info("\n Test 1: Successful JSON Generation ")
    response_json = generate_output_from_prompt(test_json_prompt, model_name="gemini-1.5-flash-latest")
    logger.info(f"Raw Response (expecting JSON): {response_json}")
    try:
        parsed_response = json.loads(response_json)
        logger.info(f"Parsed JSON:\n{json.dumps(parsed_response, indent=2)}")
    except json.JSONDecodeError:
        logger.error("Response was not valid JSON.")

    logger.info("\n Test 2: Error Case (e.g., non-existent model name) ")
    error_response = generate_output_from_prompt("This prompt should fail.", model_name="non-existent-model")
    logger.error(f"Error Response (expected JSON error): {error_response}")
    try:
        parsed_error_response = json.loads(error_response)
        logger.info(f"Parsed Error JSON:\n{json.dumps(parsed_error_response, indent=2)}")
    except json.JSONDecodeError:
        logger.critical("Error response itself was not valid JSON.")

    logger.info("\n LLM Helper Testing Complete ")