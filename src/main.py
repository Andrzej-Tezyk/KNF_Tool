from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from backend.text_extraction import process_pdfs

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_text():
    try:
        prompt = request.form['input']
        
        # a generator function to stream results back
        def generate_results():
            pdfs_to_process = process_pdfs(prompt)
            
            for result in pdfs_to_process:
                yield ("<div><p><strong>Podsumowanie dla</strong>:" 
                + f"<em>{result['pdf_name']}</em><br>{result['content']}<br><br></p></div>")

        return Response(generate_results(), mimetype='text/html')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
