import os
import sys
import time
import json
import hashlib
import platform
from datetime import datetime

# --- Optional libraries (install via pip if necessary) ---
try:
    import PyPDF2  # For PDF metadata extraction
except ImportError:
    PyPDF2 = None

try:
    import docx    # For DOCX metadata extraction
except ImportError:
    docx = None

try:
    from PIL import Image, ExifTags  # For image metadata extraction
except ImportError:
    Image = None

try:
    from mutagen import File as MutagenFile  # For audio/video metadata
except ImportError:
    MutagenFile = None

try:
    from bs4 import BeautifulSoup  # For HTML metadata extraction
except ImportError:
    BeautifulSoup = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    print("Error: reportlab library is required for PDF report generation. Install it via pip.")
    sys.exit(1)

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    # If colorama isn't installed, define dummy variables.
    class Dummy:
        RESET_ALL = ""
    class ForeDummy:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = ""
    init = lambda **kwargs: None
    Fore = ForeDummy()
    Style = Dummy()

# Try to import tabulate. If not available, fallback to a simple implementation.
try:
    from tabulate import tabulate
except ImportError:
    def tabulate(rows, headers):
        header_line = " | ".join(headers)
        sep = "-" * len(header_line)
        row_lines = "\n".join(" | ".join(row) for row in rows)
        return header_line + "\n" + sep + "\n" + row_lines

# -------------------------------
# Helper Functions for Table Formatting and Cleaning Output
# -------------------------------
def format_value(val):
    """Format a value to a string and remove curly brackets if any."""
    if isinstance(val, dict):
        # Create a multi-line string with each key-value pair (without { }).
        return "\n".join(f"{k}: {v}" for k, v in val.items())
    elif isinstance(val, list):
        return ", ".join(str(v) for v in val)
    else:
        return str(val).replace("{", "").replace("}", "")

def print_table(data, title=""):
    """Convert a dictionary to a 2-column table and print with a title."""
    if title:
        print(Fore.CYAN + Style.BRIGHT + f"\n--- {title} ---")
    if not data:
        print(Fore.RED + "No data found.")
        return
    rows = [[str(key), format_value(val)] for key, val in data.items()]
    table_str = tabulate(rows, headers=["Field", "Value"])
    # Print the table in green.
    print(Fore.GREEN + table_str)

# -------------------------------
# 1. Banner and User Input
# -------------------------------
banner = r"""
 ___      ___   _______  ___________   __       _______       __  ___________  __    __    _______   _______      
|"  \    /"  | /"     "|("     _   ") /""\     /" _   "|     /""\("     _   ")/" |  | "\  /"     "| /"      \     
 \   \  //   |(: ______) )__/  \\__/ /    \   (: ( \___)    /    \)__/  \\__/(:  (__)  :)(: ______)|:        |    
 /\\  \/.    | \/    |      \\_ /   /' /\  \   \/ \        /' /\  \  \\_ /    \/      \/  \/    |  |_____/   )    
|: \.        | // ___)_     |.  |  //  __'  \  //  \ ___  //  __'  \ |.  |    //  __  \\  // ___)_  //      /     
|.  \    /:  |(:      "|    \:  | /   /  \\  \(:   _(  _|/   /  \\  \\:  |   (:  (  )  :)(:      "||:  __   \     
|___|\__/|___| \_______)     \__|(___/    \___)\_______)(___/    \___)\__|    \__|  |__/  \_______)|__|  \___)    
"""
print(Fore.CYAN + Style.BRIGHT + banner)
time.sleep(5)

user_input = input(Fore.YELLOW + "Enter the path to the file (you can include quotes): ").strip()
if (user_input.startswith('"') and user_input.endswith('"')) or \
   (user_input.startswith("'") and user_input.endswith("'")):
    user_input = user_input[1:-1]

if not os.path.exists(user_input):
    print(Fore.RED + "Error: The file does not exist.")
    sys.exit(1)

# -------------------------------
# 2. Basic File Information Retrieval
# -------------------------------
def get_file_info(filepath):
    info = {}
    info['File Name'] = os.path.basename(filepath)
    info['File Path'] = os.path.abspath(filepath)
    info['Size (bytes)'] = os.path.getsize(filepath)
    info['File Type'] = os.path.splitext(filepath)[1]
    stat = os.stat(filepath)
    info['Creation Date'] = datetime.fromtimestamp(stat.st_ctime).isoformat()
    info['Last Modified Date'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    info['Last Accessed Date'] = datetime.fromtimestamp(stat.st_atime).isoformat()
    return info

file_info = get_file_info(user_input)
print_table(file_info, "Basic File Information")
time.sleep(2)

# -------------------------------
# 3. Conditional Metadata Extraction Based on File Type
# -------------------------------
extension = os.path.splitext(user_input)[1].lower()
extra_metadata = {}

if extension in [".pdf", ".docx"]:
    # Document Metadata Extraction
    def extract_pdf_metadata(filepath):
        metadata = {}
        if PyPDF2 is None:
            metadata["Error"] = "PyPDF2 not installed."
            return metadata
        try:
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                doc_info = reader.metadata
                if doc_info:
                    metadata = {key[1:]: value for key, value in doc_info.items()}
        except Exception as e:
            metadata["Error"] = str(e)
        return metadata

    def extract_docx_metadata(filepath):
        metadata = {}
        if docx is None:
            metadata["Error"] = "python-docx not installed."
            return metadata
        try:
            document = docx.Document(filepath)
            props = document.core_properties
            metadata = {
                "Author": props.author,
                "Title": props.title,
                "Subject": props.subject,
                "Keywords": props.keywords,
                "Software": getattr(props, 'creator', 'N/A'),
                "Revision": props.revision
            }
        except Exception as e:
            metadata["Error"] = str(e)
        return metadata

    if extension == ".pdf":
        extra_metadata = extract_pdf_metadata(user_input)
    elif extension == ".docx":
        extra_metadata = extract_docx_metadata(user_input)
    
    print_table(extra_metadata, "Document Metadata")

elif extension in [".jpg", ".jpeg", ".png"]:
    # Image Metadata Extraction
    def extract_image_metadata(filepath):
        metadata = {}
        if Image is None:
            metadata["Error"] = "Pillow not installed."
            return metadata
        try:
            img = Image.open(filepath)
            metadata["Dimensions"] = f"Width: {img.width}, Height: {img.height}"
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                for tag, value in exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    exif_data[decoded] = value
                metadata["EXIF"] = exif_data
            else:
                metadata["EXIF"] = "No EXIF data found."
        except Exception as e:
            metadata["Error"] = str(e)
        return metadata

    extra_metadata = extract_image_metadata(user_input)
    print_table(extra_metadata, "Image Metadata")

elif extension in [".mp3", ".mp4", ".mkv", ".wav"]:
    # Audio/Video Metadata Extraction
    def extract_av_metadata(filepath):
        metadata = {}
        if MutagenFile is None:
            metadata["Error"] = "mutagen not installed."
            return metadata
        try:
            media = MutagenFile(filepath)
            if media is None:
                return {"Error": "Unsupported format or no metadata found."}
            if hasattr(media, 'info'):
                info = media.info
                metadata["Duration"] = getattr(info, "length", "N/A")
                metadata["Bitrate"] = getattr(info, "bitrate", "N/A")
                metadata["Frame Rate"] = getattr(info, "framerate", "N/A")
                metadata["Resolution"] = getattr(info, "resolution", "N/A")
            if media.tags:
                metadata["Tags"] = dict(media.tags)
        except Exception as e:
            metadata["Error"] = str(e)
        return metadata

    extra_metadata = extract_av_metadata(user_input)
    print_table(extra_metadata, "Audio/Video Metadata")

elif extension in [".html", ".htm"]:
    # Web File Metadata Extraction
    def extract_html_metadata(filepath):
        metadata = {}
        if BeautifulSoup is None:
            metadata["Error"] = "beautifulsoup4 not installed."
            return metadata
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, "html.parser")
            meta_tags = soup.find_all("meta")
            meta_info = {}
            for tag in meta_tags:
                if tag.get("name"):
                    meta_info[tag.get("name")] = tag.get("content")
            metadata["Meta Tags"] = meta_info
            title = soup.find("title")
            metadata["Title"] = title.string if title else "N/A"
            generator = soup.find("meta", attrs={"name": "generator"})
            metadata["Generator"] = generator.get("content") if generator else "N/A"
        except Exception as e:
            metadata["Error"] = str(e)
        return metadata

    extra_metadata = extract_html_metadata(user_input)
    print_table(extra_metadata, "Web File Metadata")

else:
    print(Fore.RED + "\nNo additional metadata extraction available for the file type.")

time.sleep(2)

# -------------------------------
# 4. File Hash Generation (MD5, SHA1, SHA256)
# -------------------------------
def generate_hashes(filepath):
    result = {"MD5": None, "SHA1": None, "SHA256": None}
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        result["MD5"] = hashlib.md5(data).hexdigest()
        result["SHA1"] = hashlib.sha1(data).hexdigest()
        result["SHA256"] = hashlib.sha256(data).hexdigest()
    except Exception as e:
        result["Error"] = str(e)
    return result

hashes = generate_hashes(user_input)
print_table(hashes, "File Hashes")
time.sleep(2)

# -------------------------------
# 5. Final Report and PDF Report Generation
# -------------------------------
report_data = {
    "File Information": file_info,
    "Extra Metadata": extra_metadata,
    "Hashes": hashes
}
report_text = json.dumps(report_data, indent=4, default=str)

report_filename = os.path.join(os.path.dirname(os.path.abspath(user_input)), "metadata_report.pdf")
c = canvas.Canvas(report_filename, pagesize=letter)
width, height = letter

c.setFont("Helvetica-Bold", 16)
c.drawString(50, height - 50, "Metadata Extraction Report")
c.setFont("Helvetica", 10)
lines = report_text.split("\n")
y = height - 80
for line in lines:
    # Remove curly brackets from the string before printing.
    line = line.replace("{", "").replace("}", "")
    c.drawString(40, y, line)
    y -= 12
    if y < 40:
        c.showPage()
        c.setFont("Helvetica", 10)
        y = height - 50
c.save()

print(Fore.MAGENTA + "\n--- Final PDF Report ---")
print(Fore.CYAN + f"The report has been saved to:\n{report_filename}")
print(Fore.YELLOW + "\n[Note] Forensic or OSINT integration can utilize these metadata details for tracing file origin and activity timeline.")
