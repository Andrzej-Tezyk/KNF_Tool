import typing
import threading
from pathlib import Path
import traceback
import os
import json

import markdown
from flask import Flask, request, render_template, Response, stream_with_context
import google.generativeai as genai  # type: ignore[import-untyped]
from backend.text_extraction import process_pdf  # type: ignore[import-not-found]
from flask_socketio import SocketIO, emit

# directory with pdf files
SCRAPED_FILES_DIR = "scraped_files"

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
)

OPTIONAL_PAGE_NUMBER_SP = (
    "State in brackets after each sentence or paragraph from which page in the text the information used to "
    + "generate the answer came. Format: (page in the same language as rest of output: number or numbers)."
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
"""
def show_pages (system_prompt):
    if request.form.get("show-pages") == "on": # request can be used only inside the function
        return system_prompt + OPTIONAL_PAGE_NUMBER_SP
    else:
        return system_prompt
"""
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    "gemini-1.5-flash", system_instruction=SYSTEM_PROMPT
)  # another models to be used: "gemini-1.5-flash", "gemini-1.5-flash-8b",
# "gemini-2.0-flash-thinking-exp-01-21", "gemini-2.0-flash-exp"


app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

stop_flag = threading.Event()


@app.route("/")
def index() -> str:
    print('start')
    pdf_dir = Path(SCRAPED_FILES_DIR)
    pdf_files = [pdf.name for pdf in pdf_dir.glob("*.pdf")] if pdf_dir.exists() else []
    return render_template("index.html", pdf_files=pdf_files)

@socketio.on('start_processing')
def process_text(data):# -> Response:
    try:
        prompt = data.get('input')
        selected_files = data.get('pdfFiles')
        if not prompt:
            print(f"no prompt provided")
            socketio.emit('error', {'message': 'No input provided'})
            return
        
        if not selected_files or selected_files == []:
            print(f"no selected files")
            socketio.emit('error', {'message': 'No selectedd files'})
            return

        stop_flag.clear()  # reset stop flag

        output_size = int(request.form.get("output_size", 5))  # control output size

        # get selected files from the form
        #selected_files = request.form.getlist("selected_files")
        if not selected_files:
            print(f"no selected files")
            socketio.emit('error', {'message': 'No selected files'})
            return 

        # get the directory of PDFs and filter only the selected files
        pdf_dir = Path(SCRAPED_FILES_DIR)
        # result: Path("scraped_files/example.pdf") -> when used with Path object
        pdfs_to_scan = [pdf_dir / file_name for file_name in selected_files]
        #pdfs_to_scan = list(pdf_dir.glob("*.pdf"))
        for pdf in pdfs_to_scan:
            print(pdf)

        #def generate() -> typing.Generator:
        try:
            for index, pdf in enumerate(pdfs_to_scan):
                # if stop_flag.is_set():  # check stop flag
                #     yield "<div><p><strong>Processing stopped. Partial results displayed.</strong></p></div>"
                #     break

                # if not pdf.exists():
                #     yield f"<div><p><strong>Error:</strong> File {pdf.name} not found.</p></div>"
                #    continue

                pdf_name_to_show = str(pdf)

                container_html = f"""
                    <div class="output-content">
                        <div class="output-header">Result for:&nbsp <em>{pdf_name_to_show}</em>
                            <button class="output-button">
                                <span class="arrow-icon">➤</span>
                            </button>
                        </div>
                        <div class="markdown-body"
                        id="content-pdf{index}">
                        </div>
                    </div>\n\n
                    """
                print(f'new container for: {pdf_name_to_show}') 
                socketio.emit('new_container', {'html': container_html})
                
                accumulated_text = ""
                for result_chunk in process_pdf(prompt, pdf, model, output_size):
                    if "error" in result_chunk:
                        socketio.emit('error', {'message': 'error in chunk response'})
                        return 
                    elif "content" in result_chunk:
                        print(f'recived chunk: {result_chunk["content"]}') 
                        accumulated_text += result_chunk['content']
                        markdown_content = markdown.markdown(accumulated_text)
                        socketio.emit('update_content', {
                            'container_id': f'content-pdf{index}',
                            'html': markdown_content
                            })

                # if "error" in result:
                #     yield f"<div><p><strong>Error:</strong> {result['error']}</p></div>"
                # elif "content" in result:
                #     markdown_content = markdown.markdown(result["content"])
                #     yield f"""
                #     <div class="output-content">
                #         <div class="output-header">Result for:&nbsp <em>{pdf_name_to_show}</em>
                #             <button class="output-button">
                #                 <span class="arrow-icon">➤</span>
                #             </button>
                #         </div>
                #         <div class="markdown-body">{markdown_content}</div>
                #     </div>\n\n
                #     """
                    else:
                        socketio.emit('error', {'message': 'unexpected error'})
                        return 

        except Exception as e:
            print(f"An error occurred in the generate function: {e}")
            traceback.print_exc()
            socketio.emit('error', {'message': f'An unexpected error occurred: {str(e)}'})

        #return Response(stream_with_context(generate()), content_type="text/html")

    except Exception as e:
        print(f"An error occurred in the generate function: {e}")
        traceback.print_exc()
        socketio.emit('error', {'message': f'An unexpected error occurred: {str(e)}'})

# @app.route("/clear_output", methods=["GET"])  # CHANGE THE ENTIRE #OUTPUT
# def clear_output() -> str:
#     return "<div id='output' class='markdown-body'></div>"


# @app.route("/stop_processing", methods=["GET"])
# def stop_processing() -> str:
#     stop_flag.set()  # set flag to true
#     print("Stop processing triggered!")
#     return "<div></div>"  # <p><strong>Processing stopped. Displaying partial results...</strong></p>


if __name__ == "__main__":
    socketio.run(app, debug=True)
