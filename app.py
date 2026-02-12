from flask import Flask, request, jsonify, render_template
import os
import mimetypes
import time
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from mutagen.mp3 import MP3, EasyMP3
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_file_details(file_path):
    try:
        file_stats = os.stat(file_path)
        return {
            "Size": file_stats.st_size,
            "Created": time.ctime(file_stats.st_ctime),
            "Modified": time.ctime(file_stats.st_mtime),
            "Accessed": time.ctime(file_stats.st_atime),
            "Permissions": oct(file_stats.st_mode),
            "Owner UID": file_stats.st_uid,
            "Group GID": file_stats.st_gid,
        }
    except Exception as e:
        return f"Error getting file details: {e}"

def get_file_hashes(file_path):
    try:
        hashes = {}
        with open(file_path, "rb") as f:
            data = f.read()
            hashes["MD5"] = hashlib.md5(data).hexdigest()
            hashes["SHA-1"] = hashlib.sha1(data).hexdigest()
            hashes["SHA-256"] = hashlib.sha256(data).hexdigest()
        return hashes
    except Exception as e:
        return f"Error calculating file hashes: {e}"

def get_image_metadata(file_path):
    try:
        image = Image.open(file_path)
        exif_data = image._getexif()
        metadata = {}
        if exif_data:
            for tag, value in exif_data.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for gps_tag in value:
                        sub_decoded = GPSTAGS.get(gps_tag, gps_tag)
                        gps_data[sub_decoded] = value[gps_tag]
                    metadata[decoded] = gps_data
                else:
                    metadata[decoded] = value
        metadata["Resolution"] = image.size
        return metadata if metadata else "No EXIF metadata found."
    except Exception as e:
        return f"Error extracting image metadata: {e}"

def get_video_metadata(file_path):
    try:
        parser = createParser(file_path)
        if not parser:
            return "Unable to parse file."
        metadata = extractMetadata(parser)
        return metadata.exportDictionary() if metadata else "No metadata found."
    except Exception as e:
        return f"Error extracting video metadata: {e}"

def get_document_metadata(file_path):
    try:
        metadata = {}
        with open(file_path, "rb") as f:
            pdf = PdfReader(f)
            info = pdf.metadata
            metadata = {
                "Title": info.title,
                "Author": info.author,
                "Creation Date": info.creation_date,
                "Modification Date": info.mod_date,
                "Page Count": len(pdf.pages)
            }
        return metadata
    except Exception as e:
        return f"Error extracting document metadata: {e}"

def get_mp3_metadata(file_path):
    try:
        audio = MP3(file_path)
        easy_audio = EasyMP3(file_path)
        return {
            "Bitrate": audio.info.bitrate,
            "Length": audio.info.length,
            "Sample Rate": audio.info.sample_rate,
            "Artist": easy_audio.get("artist", ["Unknown"])[0],
            "Album": easy_audio.get("album", ["Unknown"])[0],
            "Title": easy_audio.get("title", ["Unknown"])[0],
            "Track Number": easy_audio.get("tracknumber", ["Unknown"])[0],
            "Genre": easy_audio.get("genre", ["Unknown"])[0],
            "Year": easy_audio.get("date", ["Unknown"])[0]
        }
    except Exception as e:
        return f"Error extracting MP3 metadata: {e}"

def extract_metadata(file_path):
    if not os.path.exists(file_path):
        return "File does not exist."
    
    metadata = {}
    metadata["File Details"] = get_file_details(file_path)
    metadata["File Hashes"] = get_file_hashes(file_path)
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        metadata["Type"] = "Unknown file type."
    elif mime_type.startswith("image"):
        metadata["Image Metadata"] = get_image_metadata(file_path)
    elif mime_type.startswith("video"):
        metadata["Video Metadata"] = get_video_metadata(file_path)
    elif mime_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        metadata["Document Metadata"] = get_document_metadata(file_path)
    elif mime_type == "audio/mpeg":
        metadata["MP3 Metadata"] = get_mp3_metadata(file_path)
    else:
        metadata["Type"] = "Unsupported file type."
    
    return metadata

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Extract metadata from the uploaded file
    result = extract_metadata(file_path)
    
    # Optionally remove the file after processing
    os.remove(file_path)
    
    return jsonify(result)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
