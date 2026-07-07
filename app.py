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

@app.route('/merge/pdf', methods=['POST'])
def merge_pdfs():
    files = request.files.getlist('files')

    if len(files) < 2:
        return jsonify({"error": "Debes subir al menos 2 archivos PDF"}), 400

    for f in files:
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            return jsonify({"error": f"{f.filename} no es un PDF válido"}), 400

    tmp_paths = []
    tmp_output = None

    try:
        import fitz

        merged = fitz.open()

        for f in files:
            tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            f.save(tmp.name)
            tmp.close()
            tmp_paths.append(tmp.name)

            with fitz.open(tmp.name) as part:
                merged.insert_pdf(part)

        tmp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        merged.save(tmp_output)
        merged.close()

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name='documento_unido.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        for path in tmp_paths:
            if os.path.exists(path):
                os.remove(path)
        if tmp_output and os.path.exists(tmp_output):
            os.remove(tmp_output)

@app.route('/split/pdf', methods=['POST'])
def split_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    tmp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_zip = None
    page_paths = []

    try:
        import fitz
        import zipfile

        file.save(tmp_input.name)
        tmp_input.close()

        doc = fitz.open(tmp_input.name)

        if doc.page_count < 2:
            doc.close()
            return jsonify({"error": "El PDF debe tener al menos 2 páginas para dividirlo"}), 400

        base_name = os.path.splitext(file.filename)[0]

        for i in range(doc.page_count):
            single = fitz.open()
            single.insert_pdf(doc, from_page=i, to_page=i)
            page_path = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
            single.save(page_path)
            single.close()
            page_paths.append((page_path, f"{base_name}_pagina_{i + 1}.pdf"))

        doc.close()

        tmp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name
        with zipfile.ZipFile(tmp_zip, 'w') as zipf:
            for path, name in page_paths:
                zipf.write(path, arcname=name)

        return send_file(
            tmp_zip,
            as_attachment=True,
            download_name=f'{base_name}_paginas.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(tmp_input.name):
            os.remove(tmp_input.name)
        for path, _ in page_paths:
            if os.path.exists(path):
                os.remove(path)
        if tmp_zip and os.path.exists(tmp_zip):
            os.remove(tmp_zip)

if __name__ == '__main__':
    app.run(debug=False)