import json
import logging
import os
from typing import Any

import google.generativeai as genai


log = logging.getLogger("__name__")


with open("config/config.json") as file:
    config = json.load(file)




GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")




def enhance_prompt(prompt: str, model: Any) -> str:
    """Enhances the given prompt by adding context and instructions.

    This function takes a user-provided prompt and enhances it by adding context
    and instructions to improve the quality of the generated response.

    Args:
        prompt (str): The original user-provided prompt.

    Returns:
        str: The enhanced prompt with additional context and instructions.
    """


    instructions = config["prompt_enhancer"]

    instructions_and_prompt = f"{instructions}\n\nUser Prompt: {prompt}"

    enchaced_prompt = model.generate_content(instructions_and_prompt)
    log.debug("User prompt sent to enchancer.")

    return enchaced_prompt.candidates[0].content.parts[0].text


test = enhance_prompt("Czy ten dokument zawiera informacje na temat zarządznia ryzkiem kredytowym?", model)
print(test)