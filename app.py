from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter
import tempfile
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "API funcionando correctamente"})

@app.route('/convert/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']

    if file.filename == '' or not file.filename.endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    # Crear archivos temporales
    tmp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_docx = tmp_pdf.name.replace('.pdf', '.docx')

    try:
        file.save(tmp_pdf.name)
        tmp_pdf.close()

        # Conversión
        cv = Converter(tmp_pdf.name)
        cv.convert(tmp_docx)
        cv.close()

        return send_file(
            tmp_docx,
            as_attachment=True,
            download_name='convertido.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Limpiar archivos temporales
        if os.path.exists(tmp_pdf.name):
            os.remove(tmp_pdf.name)

@app.route('/compress/pdf', methods=['POST'])
def compress_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']

    if file.filename == '' or not file.filename.endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    tmp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_output = tmp_input.name.replace('.pdf', '_comprimido.pdf')

    try:
        file.save(tmp_input.name)
        tmp_input.close()

        # Comprimir con PyMuPDF
        import fitz
        doc = fitz.open(tmp_input.name)
        doc.save(tmp_output, garbage=4, deflate=True, clean=True)
        doc.close()

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name='comprimido.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(tmp_input.name):
            os.remove(tmp_input.name)

if __name__ == '__main__':
    app.run(debug=False)