import logging


log = logging.getLogger("__name__")


OPTIONAL_PAGE_NUMBER_SP = (
    "State in brackets after each sentence or paragraph from which page in the text the information used to "
    + "generate the answer came. Format: (word 'page' in the same language as rest of output: number or numbers)."
)


def show_pages(system_prompt: str, show_pages_checkbox: bool) -> str:
    """
    Add an additional string to the system prompt to instruct model to include page name in outputs.
    """
    if show_pages_checkbox == "True":  # request can be used only inside the function
        log.debug(system_prompt + OPTIONAL_PAGE_NUMBER_SP)
        return system_prompt + OPTIONAL_PAGE_NUMBER_SP
    else:
        log.debug(system_prompt)
        return system_prompt
