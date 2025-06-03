import os
import PyPDF2
import fitz # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import numpy as np
import cv2
from pdf2image import convert_from_path

def extract_text_from_pdf(pdf_path, verbose=True):
    """
    Function to extract text from a PDF file using multiple methods.
    Returns text as soon as one method succeeds.

    Args:
        pdf_path (str): Path to the PDF file
        verbose (bool): Whether to print progress information

    Returns:
        tuple: (method_name, extracted_text) if successful, (None, None) if all methods fail
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist.")
        return None, None

    if verbose:
        print(f"Attempting to extract text from {pdf_path}")

    # Method 1: PyPDF2
    try:
        if verbose:
            print("Trying PyPDF2...")

        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"

            if text.strip():
                if verbose:
                    print("PyPDF2 extraction successful.")
                return "PyPDF2", text
            elif verbose:
                print("PyPDF2 extraction yielded no text.")
    except Exception as e:
        if verbose:
            print(f"PyPDF2 extraction failed: {str(e)}")

    # Method 2: PyMuPDF (fitz)
    try:
        if verbose:
            print("Trying PyMuPDF...")

        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text() + "\n\n"
        doc.close()

        if text.strip():
            if verbose:
                print("PyMuPDF extraction successful.")
            return "PyMuPDF", text
        elif verbose:
            print("PyMuPDF extraction yielded no text.")
    except Exception as e:
        if verbose:
            print(f"PyMuPDF extraction failed: {str(e)}")

    # Method 3: pdfplumber
    try:
        if verbose:
            print("Trying pdfplumber...")

        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n\n"

        if text.strip():
            if verbose:
                print("pdfplumber extraction successful.")
            return "pdfplumber", text
        elif verbose:
            print("pdfplumber extraction yielded no text.")
    except Exception as e:
        if verbose:
            print(f"pdfplumber extraction failed: {str(e)}")

    # Method 4: OCR using pytesseract (last resort)
    try:
        if verbose:
            print("All standard methods failed. Attempting OCR...")

        # Convert PDF pages to images
        images = convert_from_path(pdf_path)
        text = ""

        for i, image in enumerate(images):
            if verbose:
                print(f"Processing page {i+1} with OCR...")

            # Process the image before OCR to improve results
            img_np = np.array(image)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            pil_img = Image.fromarray(binary)

            # Extract text using pytesseract
            page_text = pytesseract.image_to_string(pil_img)
            text += page_text + "\n\n"

        if text.strip():
            if verbose:
                print("OCR extraction successful.")
            return "OCR", text
        elif verbose:
            print("OCR extraction yielded no text.")
    except Exception as e:
        if verbose:
            print(f"OCR extraction failed: {str(e)}")

    if verbose:
        print("All extraction methods failed.")
    return None, None

