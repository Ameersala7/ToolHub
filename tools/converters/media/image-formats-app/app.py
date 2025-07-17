from flask import Flask, request, send_file, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
from PIL import Image
import subprocess
import zipfile
import io

app = Flask(__name__, static_folder='.', static_url_path='/')

UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'files' not in request.files or 'outputFormat' not in request.form:
        return 'Missing file(s) or format', 400

    # Clear previous uploads
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))
    for f in os.listdir(TEMP_FOLDER):
        os.remove(os.path.join(TEMP_FOLDER, f))

    files = request.files.getlist('files')
    output_format = request.form['outputFormat'].lower()
    output_files = []

    raster_exts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp',
                   'ppm', 'pgm', 'pbm', 'pnm', 'pam']
    vector_exts = ['svg', 'eps', 'pdf', 'ai', 'emf', 'wmf', 'cgm']
    force_convert_exts = ['pgm', 'pbm', 'pnm', 'pam'] + vector_exts

    for file in files:
        filename = secure_filename(file.filename)
        input_path = os.path.join(TEMP_FOLDER, filename)
        file.save(input_path)

        name, ext = os.path.splitext(filename)
        output_filename = f'{name}_converted.{output_format}'
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        ext = ext.lower().lstrip('.')

        try:
            if output_format in force_convert_exts:
                subprocess.run(['convert', input_path, output_path], check=True)
            else:
                img = Image.open(input_path).convert('RGB')
                img.save(output_path, output_format.upper())
            output_files.append(output_filename)
        except Exception as e:
            print(f"Error converting {filename}: {e}")
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

    if not output_files:
        return "No files converted successfully.", 500

    return jsonify({"status": "success", "files": output_files})

@app.route('/download-all', methods=['GET'])
def download_all():
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                zipf.write(file_path, arcname=filename)
    zip_stream.seek(0)
    return send_file(zip_stream, mimetype='application/zip', as_attachment=True, download_name='converted_files.zip')

if __name__ == '__main__':
    app.run(debug=True)
