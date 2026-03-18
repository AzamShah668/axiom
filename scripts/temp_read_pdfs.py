import sys
import os

try:
    import pypdf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    import pypdf

def extract_pdf(pdf_path, txt_path):
    print(f"Extracting {pdf_path} to {txt_path}...")
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ''
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + '\n'
            
            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            with open(txt_path, 'w', encoding='utf-8') as out:
                out.write(text)
        print(f"Successfully extracted {pdf_path}")
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")

btech_pdf = r"d:\notebook lm\syllabus\BTech_Syllabus_detailed.pdf"
mbbs_pdf = r"d:\notebook lm\syllabus\Syllabus - MBBS.pdf"
btech_txt = r"d:\notebook lm\data\btech_extracted.txt"
mbbs_txt = r"d:\notebook lm\data\mbbs_extracted.txt"

extract_pdf(btech_pdf, btech_txt)
extract_pdf(mbbs_pdf, mbbs_txt)
