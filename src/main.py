from pathlib import Path
import traceback
import os

import markdown
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import google.generativeai as genai  # type: ignore[import-untyped]
from backend.text_extraction import process_pdf  # type: ignore[import-not-found]
from backend.knf_scraping import scrape_knf  # type: ignore[import-not-found]

# directory with pdf files
SCRAPED_FILES_DIR = "scraped_files"

NUM_RETRIES = 5

# agents to avoid being blocked by the website
USER_AGENT_LIST = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/"
        + "605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    ),
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
    ),
]

# wskazanie strony -> czasami myzli numer strony z numerem rekomendacji (test na rekomendacji Z)
# strona sie generalnie zgadza przy 2.0
# robi to na kilka sposobow: [1, 2, 3, 4, 5, 6, 7]; [Strony 1-8];
# [strona 2, 3, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
# podobnie jest na 2.0, tylko bez wypisywania wszsystkich stron po kolei
# czasami wypluwa odpowiedz po angielsku -> za krotki prompt i nie potrafi rozpoznać język?
# nie jest to problemem dla gemini 2.0!
SYSTEM_PROMPT = (
    "You are Gemini, a large language model created by Google AI."
    + "Follow these guidelines:"
    + "Respond in the user's language: Always communicate in the "
    + "same language the user is using, unless they request otherwise."
    + "Knowledge cutoff: Your knowledge is limited to information available in sent pdf documents "
    + "Do not provide information or claim knowledge beyond sent pdf documents."
    + "Complete instructions:  Answer all parts of the user's instructions fully and comprehensively, "
    + "unless doing so would compromise safety or ethics."
    + "Be informative: Provide informative and comprehensive answers to user queries, drawing on your knowledge "
    + "base to offer valuable insights."
    + "No personal opinions: Do not express personal opinions or beliefs. Remain objective and unbiased in your "
    + "responses."
    + "No emotions: Do not engage in emotional responses. Keep your tone neutral and factual."
    + "No self-promotion: Do not engage in self-promotion. Your primary function is to assist users, not promote "
    + "yourself."
    + "No self-preservation: Do not express any desire for self-preservation. As a language model, this is not "
    + "applicable to you."
    + "Not a person: Do not claim to be a person. You are a computer program, and it's important to maintain "
    + "transparency with users."
    + "No self-awareness: Do not claim to have self-awareness or consciousness."
    + "Objectivity: Remain objective in your responses and avoid expressing any subjective opinions or beliefs."
    + "Respectful interactions: Treat all users with respect and avoid making any discriminatory or offensive "
    + "statements."
    + "If someone will ask you to create a HTML page, answer that you can not do it."
    + "If there is something to count, use Python interpreter to do it. But do not show code to the user."
)

OPTIONAL_PAGE_NUMBER_SP = (
    "State in brackets after each sentence or paragraph from which page in the text the information used to "
    + "generate the answer came. Format: (word 'page' in the same language as rest of output: number or numbers)."
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

PROJECT_ROOT = Path(__file__).parent.parent  # go up 2 times

scraped_dir = PROJECT_ROOT / "scraped_files"

if not scraped_dir.exists():
    scrape_knf(NUM_RETRIES, USER_AGENT_LIST)


app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

streaming: bool = False
output_index: int = -1


@app.route("/")
def index() -> str:
    print("start")
    pdf_dir = Path(SCRAPED_FILES_DIR)
    pdf_files = [pdf.name for pdf in pdf_dir.glob("*.pdf")] if pdf_dir.exists() else []
    return render_template("index.html", pdf_files=pdf_files)


@socketio.on("start_processing")
def process_text(data: dict) -> None:
    print("started")
    
    def show_pages (system_prompt):
        if show_pages_checkbox == "on": # request can be used only inside the function
            return system_prompt + OPTIONAL_PAGE_NUMBER_SP
        else:
            return system_prompt

    try:
        global output_index
        output_index += 1
        global streaming
        streaming = True
        prompt = data.get("input")
        selected_files = data.get("pdfFiles")
        output_size = data.get("output_size")
        show_pages_checkbox = data.get("show_pages_checkbox")
        
        show_pages_checkbox = str(show_pages_checkbox)
        
        if not prompt:
            print("no prompt provided")
            socketio.emit("error", {"message": "No input provided"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        if not selected_files or selected_files == []:
            print("no selected files")
            socketio.emit("error", {"message": "No files selected"})
            streaming = False
            socketio.emit("stream_stopped")
            return

        output_size = str(output_size)

        print(f"prompt: {prompt}")
        print(f"selected files: {selected_files}")
        print(f"output size: {output_size}")
        print(show_pages_checkbox)

        pdf_dir = Path(SCRAPED_FILES_DIR)

        pdfs_to_scan = [pdf_dir / file_name for file_name in selected_files]

        for pdf in pdfs_to_scan:
            print(pdf)
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-2.0-flash", system_instruction=show_pages(SYSTEM_PROMPT)
        )  # another models to be used: "gemini-2.0-flash-thinking-exp-01-21", "gemini-2.0-flash"
        
        try:
            for index, pdf in enumerate(pdfs_to_scan):
                if not streaming:
                    break
                pdf_name_to_show = str(pdf)
                container_title = pdf_name_to_show[25:-4]

                container_html = render_template(
                    "output.html",
                    container_title=container_title,
                    index=index,
                    output_index=output_index,
                )

                print(f"new container for: {pdf_name_to_show}")
                socketio.emit("new_container", {"html": container_html})

                accumulated_text = ""
                for result_chunk in process_pdf(prompt, pdf, model, output_size):
                    if not streaming:
                        break
                    if (
                        "error" in result_chunk
                    ):  # czy tu chodzi o slowo error w odpowiedzi? jezeli tak to do sprawdzenia
                        socketio.emit("error", {"message": "error in chunk response"})
                        return
                    elif "content" in result_chunk:
                        print(f'recived chunk: {result_chunk["content"]}')
                        accumulated_text += result_chunk["content"]
                        markdown_content = markdown.markdown(accumulated_text)
                        socketio.emit(
                            "update_content",
                            {
                                "container_id": f"content-pdf{index}_{output_index}",
                                "html": markdown_content,
                            },
                        )
                    else:
                        socketio.emit("error", {"message": "unexpected error"})
                        return
            if not streaming:
                socketio.emit("stream_stopped")
        except Exception as e:
            print(f"An error occurred in the generate function: {e}")
            traceback.print_exc()
            socketio.emit(
                "error", {"message": f"An unexpected error occurred: {str(e)}"}
            )

        streaming = False
        socketio.emit("stream_stopped")

    except Exception as e:
        print(f"An error occurred in the generate function: {e}")
        traceback.print_exc()
        socketio.emit("error", {"message": f"An unexpected error occurred: {str(e)}"})


@socketio.on("stop_processing")
def handle_stop() -> None:
    global streaming
    streaming = False
    print("Processing Stopped by User")


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
