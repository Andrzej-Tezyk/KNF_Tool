from backend.text_extraction import extract_text_from_pdf, process_pdfs
from flask import Flask, request, jsonify, render_template, Response
import time

app = Flask(__name__)

@app.route("/")
def index():
    # Serve the HTML page
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_text():
    try:
        # Get the input text from the textarea in the HTML
        prompt = request.form['input']
        
        # Create a generator function to stream results back
        def generate_results():
            # Process PDFs and yield results for each PDF as it is processed
            pdfs_to_process = process_pdfs(prompt)  # Modify this to process PDFs iteratively
            
            for result in pdfs_to_process:
                yield f"<div><p>{result}<br><br><br></p></div>"  # This will wrap each result in a <div> tag for easy styling
                time.sleep(1)  # To simulate the delay for each document being processed (optional)

        # Return the streamed response
        return Response(generate_results(), content_type='text/html;charset=utf-8')

    except Exception as e:
        # If an error occurs, return a JSON response with the error message
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True)

