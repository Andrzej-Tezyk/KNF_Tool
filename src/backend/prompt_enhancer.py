import json
import logging
from typing import Any
from pathlib import Path

log = logging.getLogger("__name__")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
print(CONFIG_PATH)
with open(CONFIG_PATH) as file:
    config = json.load(file)


def enhance_prompt(prompt: str, model: Any) -> Any:
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

    enhanced_prompt = model.generate_content(instructions_and_prompt)
    log.debug("User prompt sent to enchancer.")
    log.debug(f"Enhanced prompt: \n {enhanced_prompt}")

    return enhanced_prompt.candidates[0].content.parts[0].text
