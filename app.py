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

@app.route('/rotate/pdf', methods=['POST'])
def rotate_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']
    angle = request.form.get('angle', '90')

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    try:
        angle = int(angle)
        if angle not in (90, 180, 270):
            return jsonify({"error": "El ángulo debe ser 90, 180 o 270"}), 400
    except ValueError:
        return jsonify({"error": "Ángulo inválido"}), 400

    tmp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_output = None

    try:
        import fitz

        file.save(tmp_input.name)
        tmp_input.close()

        doc = fitz.open(tmp_input.name)

        for page in doc:
            new_rotation = (page.rotation + angle) % 360
            page.set_rotation(new_rotation)

        tmp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        doc.save(tmp_output)
        doc.close()

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name='rotado.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(tmp_input.name):
            os.remove(tmp_input.name)
        if tmp_output and os.path.exists(tmp_output):
            os.remove(tmp_output)

@app.route('/convert/image-to-pdf', methods=['POST'])
def image_to_pdf():
    files = request.files.getlist('files')

    if len(files) < 1:
        return jsonify({"error": "Debes subir al menos 1 imagen"}), 400

    allowed_ext = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

    for f in files:
        if f.filename == '' or not f.filename.lower().endswith(allowed_ext):
            return jsonify({"error": f"{f.filename} no es una imagen válida (usa JPG, PNG, WEBP o BMP)"}), 400

    tmp_paths = []
    tmp_output = None

    try:
        import fitz

        doc = fitz.open()

        for f in files:
            ext = os.path.splitext(f.filename)[1]
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            f.save(tmp.name)
            tmp.close()
            tmp_paths.append(tmp.name)

            img_doc = fitz.open(tmp.name)
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()

            img_pdf = fitz.open("pdf", pdf_bytes)
            doc.insert_pdf(img_pdf)
            img_pdf.close()

        tmp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        doc.save(tmp_output)
        doc.close()

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name='imagenes_convertidas.pdf',
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

@app.route('/numerate/pdf', methods=['POST'])
def numerate_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']
    position = request.form.get('position', 'bottom-center')

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    tmp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_output = None

    try:
        import fitz

        file.save(tmp_input.name)
        tmp_input.close()

        doc = fitz.open(tmp_input.name)
        total = doc.page_count

        for i, page in enumerate(doc):
            rect = page.rect
            text = f"{i + 1} / {total}"
            fontsize = 10
            margin = 25

            if position == 'bottom-center':
                point = fitz.Point(rect.width / 2 - 15, rect.height - margin)
            elif position == 'bottom-right':
                point = fitz.Point(rect.width - 60, rect.height - margin)
            elif position == 'bottom-left':
                point = fitz.Point(margin, rect.height - margin)
            else:
                point = fitz.Point(rect.width / 2 - 15, rect.height - margin)

            page.insert_text(point, text, fontsize=fontsize, color=(0.3, 0.3, 0.3))

        tmp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        doc.save(tmp_output)
        doc.close()

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name='numerado.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(tmp_input.name):
            os.remove(tmp_input.name)
        if tmp_output and os.path.exists(tmp_output):
            os.remove(tmp_output)

@app.route('/delete-pages/pdf', methods=['POST'])
def delete_pages_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']
    pages_str = request.form.get('pages', '')

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    if not pages_str.strip():
        return jsonify({"error": "Debes indicar qué páginas eliminar (ej: 1,3,5)"}), 400

    tmp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_output = None

    try:
        import fitz

        file.save(tmp_input.name)
        tmp_input.close()

        doc = fitz.open(tmp_input.name)
        total = doc.page_count

        try:
            pages_to_delete = sorted(set(
                int(p.strip()) - 1 for p in pages_str.split(',') if p.strip()
            ), reverse=True)
        except ValueError:
            doc.close()
            return jsonify({"error": "Formato de páginas inválido, usa números separados por coma (ej: 1,3,5)"}), 400

        for p in pages_to_delete:
            if p < 0 or p >= total:
                doc.close()
                return jsonify({"error": f"La página {p + 1} no existe en este documento ({total} páginas en total)"}), 400

        if len(pages_to_delete) >= total:
            doc.close()
            return jsonify({"error": "No puedes eliminar todas las páginas del documento"}), 400

        for p in pages_to_delete:
            doc.delete_page(p)

        tmp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        doc.save(tmp_output)
        doc.close()

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name='sin_paginas.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(tmp_input.name):
            os.remove(tmp_input.name)
        if tmp_output and os.path.exists(tmp_output):
            os.remove(tmp_output)

@app.route('/convert/pdf-to-jpg', methods=['POST'])
def pdf_to_jpg():
    if 'file' not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files['file']

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400

    tmp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_output = None
    img_paths = []

    try:
        import fitz
        import zipfile

        file.save(tmp_input.name)
        tmp_input.close()

        doc = fitz.open(tmp_input.name)
        base_name = os.path.splitext(file.filename)[0]
        zoom = 2  # ~144 DPI para buena calidad
        matrix = fitz.Matrix(zoom, zoom)

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            img_path = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False).name
            pix.save(img_path)
            img_paths.append((img_path, f"{base_name}_pagina_{i + 1}.jpg"))

        doc.close()

        if len(img_paths) == 1:
            return send_file(
                img_paths[0][0],
                as_attachment=True,
                download_name=img_paths[0][1],
                mimetype='image/jpeg'
            )

        tmp_output = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name
        with zipfile.ZipFile(tmp_output, 'w') as zipf:
            for path, name in img_paths:
                zipf.write(path, arcname=name)

        return send_file(
            tmp_output,
            as_attachment=True,
            download_name=f'{base_name}_imagenes.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(tmp_input.name):
            os.remove(tmp_input.name)
        for path, _ in img_paths:
            if os.path.exists(path):
                os.remove(path)
        if tmp_output and os.path.exists(tmp_output):
            os.remove(tmp_output)

@app.route('/convert/heic-to-jpg', methods=['POST'])
def heic_to_jpg():
    files = request.files.getlist('files')

    if len(files) < 1:
        return jsonify({"error": "Debes subir al menos 1 imagen HEIC"}), 400

    for f in files:
        if f.filename == '' or not f.filename.lower().endswith(('.heic', '.heif')):
            return jsonify({"error": f"{f.filename} no es un archivo HEIC/HEIF válido"}), 400

    tmp_paths = []
    out_paths = []
    tmp_zip = None

    try:
        import pillow_heif
        import zipfile

        pillow_heif.register_heif_opener()
        from PIL import Image

        for f in files:
            ext = os.path.splitext(f.filename)[1]
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            f.save(tmp.name)
            tmp.close()
            tmp_paths.append(tmp.name)

            img = Image.open(tmp.name).convert('RGB')
            out_path = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False).name
            img.save(out_path, 'JPEG', quality=90)

            base_name = os.path.splitext(f.filename)[0]
            out_paths.append((out_path, f"{base_name}.jpg"))

        if len(out_paths) == 1:
            return send_file(
                out_paths[0][0],
                as_attachment=True,
                download_name=out_paths[0][1],
                mimetype='image/jpeg'
            )

        tmp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name
        with zipfile.ZipFile(tmp_zip, 'w') as zipf:
            for path, name in out_paths:
                zipf.write(path, arcname=name)

        return send_file(
            tmp_zip,
            as_attachment=True,
            download_name='imagenes_convertidas.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        for path in tmp_paths:
            if os.path.exists(path):
                os.remove(path)
        for path, _ in out_paths:
            if os.path.exists(path):
                os.remove(path)
        if tmp_zip and os.path.exists(tmp_zip):
            os.remove(tmp_zip)

if __name__ == '__main__':
    app.run(debug=False)