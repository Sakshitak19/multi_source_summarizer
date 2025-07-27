from flask import Flask, render_template, request, send_file
import pytesseract
from PIL import Image
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize, RegexpTokenizer
import heapq
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re
from urllib.parse import urlparse
import os

# Initialize NLTK data (important for PythonAnywhere)
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# Configure Tesseract path (different for PythonAnywhere)
if not os.name == 'nt':  # Not Windows (for PythonAnywhere)
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

def preprocess_text(text):
    """Clean and preprocess text for better summarization"""
    if not text:
        return ""
    # Remove special characters and extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'[^\w\s.,;:!?]', '', text)  # Keep basic punctuation
    return text.strip()

def get_key_phrases(text, num_phrases=5):
    """Extract key phrases from text"""
    if not text:
        return []
    
    tokenizer = RegexpTokenizer(r'\w+')
    words = tokenizer.tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    
    # Filter out stopwords and short words
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Create frequency distribution
    freq_dist = nltk.FreqDist(filtered_words)
    
    # Get most common phrases (2-3 word combinations)
    bigrams = list(nltk.ngrams(filtered_words, 2))
    trigrams = list(nltk.ngrams(filtered_words, 3))
    
    phrases = []
    for ngram in bigrams + trigrams:
        phrase = ' '.join(ngram)
        if phrase in text.lower():
            phrases.append(phrase)
    
    # Get most frequent phrases
    phrase_freq = nltk.FreqDist(phrases)
    return [phrase[0] for phrase in phrase_freq.most_common(num_phrases)]

def simplify_language(text):
    """Simplify complex language for better readability"""
    if not text:
        return ""
    
    replacements = {
        "however": "but",
        "therefore": "so",
        "nevertheless": "still",
        "consequently": "so",
        "furthermore": "also",
        "moreover": "also",
        "thus": "so",
        "hence": "so",
        "although": "though",
        "utilize": "use"
    }
    for word, replacement in replacements.items():
        text = re.sub(r'\b' + word + r'\b', replacement, text, flags=re.IGNORECASE)
    return text

def generate_structured_summary(text):
    """Generate a well-structured summary with key points"""
    if not text:
        return "No text provided for summarization.", []
    
    text = preprocess_text(text)
    
    if len(text.split()) < 20:
        return "The content is too short to generate a meaningful summary.", []
    
    # Get key phrases
    key_phrases = get_key_phrases(text)
    
    # Tokenize sentences
    sentences = sent_tokenize(text)
    
    # Score sentences based on key phrases and position
    sentence_scores = {}
    for i, sent in enumerate(sentences):
        score = 0
        # Higher score for sentences containing key phrases
        for phrase in key_phrases:
            if phrase in sent.lower():
                score += 2
        # Higher score for first/last sentences
        if i < 3 or i > len(sentences) - 3:
            score += 1
        # Higher score for medium-length sentences
        if 15 <= len(sent.split()) <= 30:
            score += 1
        sentence_scores[sent] = score
    
    # Get top 5-7 most important sentences
    summary_sentences = heapq.nlargest(
        min(7, len(sentences)), 
        sentence_scores, 
        key=sentence_scores.get
    )
    
    # Simplify language
    summary_sentences = [simplify_language(sent) for sent in summary_sentences]
    
    # Organize into structured format
    overview = ' '.join(summary_sentences[:2])
    key_points = summary_sentences[2:-1] if len(summary_sentences) > 3 else summary_sentences[1:]
    conclusion = summary_sentences[-1] if len(summary_sentences) > 1 else ""
    
    # Format for HTML display
    structured_summary = {
        'overview': overview,
        'key_points': key_points,
        'conclusion': conclusion,
        'key_phrases': key_phrases[:10]  # Limit to 10 key phrases
    }
    
    return structured_summary

def generate_plain_summary(text):
    """Generate plain text summary for download"""
    if not text:
        return "No text provided for summarization.", []
    
    structured = generate_structured_summary(text)
    if isinstance(structured, str):
        return structured, []
    
    plain_text = "DOCUMENT SUMMARY\n\n"
    plain_text += "OVERVIEW:\n" + structured['overview'] + "\n\n"
    plain_text += "KEY POINTS:\n- " + "\n- ".join(structured['key_points']) + "\n\n"
    if structured['conclusion']:
        plain_text += "CONCLUSION:\n" + structured['conclusion'] + "\n\n"
    plain_text += "KEY TERMS: " + ", ".join(structured['key_phrases'])
    
    return plain_text, structured['key_phrases']

def extract_main_content(soup):
    """Extract main content from webpage using heuristics"""
    if not soup:
        return ""
    
    # Try common content containers first
    for tag in ['article', 'main']:
        element = soup.find(tag)
        if element:
            return element.get_text()
    
    # Try common class names
    for class_name in ['content', 'post-content', 'article-body']:
        element = soup.find(class_=class_name)
        if element:
            return element.get_text()
    
    # Fallback to paragraph content
    paragraphs = soup.find_all('p')
    content = '\n'.join(p.get_text() for p in paragraphs if len(p.get_text()) > 40)
    
    # If still too short, try divs with high text density
    if len(content.split()) < 100:
        all_divs = soup.find_all('div')
        for div in all_divs:
            text = div.get_text()
            if len(text.split()) > 100:
                return text
    
    return content

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/summarize_text', methods=['POST', 'GET'])
def summarize_text():
    if request.method == 'POST':
        text = request.form.get('text', '')
        summary, keywords = generate_plain_summary(text)
        return render_template('summarize_text.html', summary=summary, keywords=keywords)
    return render_template('summarize_text.html')

@app.route('/summarize_pdf', methods=['POST', 'GET'])
def summarize_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('summarize_pdf.html', error="No file uploaded")
            
        file = request.files['pdf_file']
        if file.filename == '':
            return render_template('summarize_pdf.html', error="No file selected")
            
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            if not text.strip():
                return render_template('summarize_pdf.html', error="No text could be extracted from PDF")
            
            structured_summary = generate_structured_summary(text)
            plain_summary, keywords = generate_plain_summary(text)
            
            return render_template(
                'summarize_pdf.html',
                summary=structured_summary,
                keywords=keywords,
                plain_summary=plain_summary
            )
        except Exception as e:
            return render_template('summarize_pdf.html', error=f"Error processing PDF: {str(e)}")
    return render_template('summarize_pdf.html')

@app.route('/summarize_image', methods=['POST', 'GET'])
def summarize_image():
    if request.method == 'POST':
        if 'image_file' not in request.files:
            return render_template('summarize_image.html', error="No file uploaded")
            
        image = request.files['image_file']
        if image.filename == '':
            return render_template('summarize_image.html', error="No file selected")
            
        try:
            img = Image.open(image)
            text = pytesseract.image_to_string(img)
            
            if not text.strip():
                return render_template('summarize_image.html', error="No text could be extracted from image")
                
            summary, keywords = generate_plain_summary(text)
            return render_template('summarize_image.html', summary=summary, keywords=keywords)
        except Exception as e:
            return render_template('summarize_image.html', error=f"Error processing image: {str(e)}")
    return render_template('summarize_image.html')

@app.route('/summarize_url', methods=['POST', 'GET'])
def summarize_url():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url:
            return render_template('summarize_url.html', error="Please enter a URL")
            
        try:
            # Validate URL format
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError("Invalid URL format")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()  # Raise exception for bad status codes
            
            soup = BeautifulSoup(res.text, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            
            # Extract main content
            text = extract_main_content(soup)
            
            if not text.strip():
                return render_template('summarize_url.html', error="No main content could be extracted from the page")
            
            # Generate concise one-paragraph summary
            structured = generate_structured_summary(text)
            if isinstance(structured, str):
                summary = structured
            else:
                # Combine overview and key points into one paragraph
                summary = structured['overview'] + " " + " ".join(structured['key_points'])
                if structured['conclusion']:
                    summary += " " + structured['conclusion']
                
                # Simplify further and limit to 5-7 sentences
                sentences = sent_tokenize(summary)
                summary = ' '.join(sentences[:7])
                summary = simplify_language(summary)
            
            keywords = get_key_phrases(text)
            
            return render_template(
                'summarize_url.html',
                summary=summary,
                keywords=keywords,
                title=title,
                url=url
            )
        except Exception as e:
            return render_template('summarize_url.html', error=f"Error processing URL: {str(e)}")
    return render_template('summarize_url.html')

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    title = request.form.get('title', 'Document Summary')
    summary = request.form.get('summary', '')
    keywords = request.form.get('keywords', '')

    if not summary:
        return "No summary data to download."

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, title)

    # Summary content
    c.setFont("Helvetica", 12)
    text_object = c.beginText(40, height - 80)
    text_object.setLeading(15)
    
    # Split summary into lines and add to PDF
    for line in summary.split('\n'):
        if line.startswith(('OVERVIEW:', 'KEY POINTS:', 'CONCLUSION:', 'KEY TERMS:')):
            c.setFont("Helvetica-Bold", 12)
            text_object.textLine(line)
            c.setFont("Helvetica", 12)
        elif line.startswith('- '):
            text_object.textLine(line)
        else:
            text_object.textLine(line)

    # Add keywords if available
    if keywords:
        text_object.textLine("\nKeywords: " + keywords)

    c.drawText(text_object)
    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="document_summary.pdf",
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False for production
