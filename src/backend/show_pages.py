OPTIONAL_PAGE_NUMBER_SP = (
    "State in brackets after each sentence or paragraph from which page in the text the information used to "
    + "generate the answer came. Format: (word 'page' in the same language as rest of output: number or numbers)."
)


def show_pages(system_prompt: str, show_pages_checkbox: bool) -> str:
    if show_pages_checkbox == "True":  # request can be used only inside the function
        print(system_prompt + OPTIONAL_PAGE_NUMBER_SP)
        return system_prompt + OPTIONAL_PAGE_NUMBER_SP
    else:
        print(system_prompt)
        return system_prompt
