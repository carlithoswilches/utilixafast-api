from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter
import tempfile
import os

app = Flask(__name__)
CORS(app)  # Permite que tu WordPress se comunique con la API

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

if __name__ == '__main__':
    app.run(debug=False)