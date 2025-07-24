from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pytesseract
from PIL import Image
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import heapq
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Download NLTK resources
nltk.download('punkt')
nltk.download('stopwords')

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

# Helper: Paragraph summary
def summarize_paragraph(para):
    stop_words = set(stopwords.words("english"))
    words = word_tokenize(para.lower())
    word_frequencies = {}

    for word in words:
        if word.isalpha() and word not in stop_words:
            word_frequencies[word] = word_frequencies.get(word, 0) + 1

    sentences = sent_tokenize(para)
    sentence_scores = {}
    for sent in sentences:
        for word in word_tokenize(sent.lower()):
            if word in word_frequencies:
                if len(sent.split(' ')) < 30:
                    sentence_scores[sent] = sentence_scores.get(sent, 0) + word_frequencies[word]

    summary_length = min(2, len(sentences))
    summary_sentences = heapq.nlargest(summary_length, sentence_scores, key=sentence_scores.get)
    summary = ' '.join(summary_sentences)
    important_words = sorted(word_frequencies, key=word_frequencies.get, reverse=True)[:5]

    return summary, important_words

# Final summary
def generate_summary(text):
    if not text or len(text.split()) < 10:
        return text, []

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    all_summary = []
    all_keywords = []

    for para in paragraphs:
        summary, keywords = summarize_paragraph(para)
        all_summary.append(summary)
        all_keywords.extend(keywords)

    final_summary = '\n'.join(all_summary)
    unique_keywords = list(set(all_keywords))[:10]

    return final_summary, unique_keywords

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = generate_password_hash(request.form['password'])
        db.session.add(User(username=uname, password=pwd))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        user = User.query.filter_by(username=uname).first()
        if user and check_password_hash(user.password, pwd):
            session['user'] = uname
            return redirect(url_for('home'))
        else:
            return "Wrong credentials"
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/summarize_text', methods=['POST', 'GET'])
def summarize_text():
    if request.method == 'POST':
        text = request.form['text']
        summary, keywords = generate_summary(text)
        session['summary_data'] = {
            'title': 'Text Summary',
            'summary': summary,
            'keywords': ', '.join(keywords)
        }
        return render_template('summarize_text.html', summary=summary, keywords=keywords)
    return render_template('summarize_text.html')

@app.route('/summarize_pdf', methods=['POST', 'GET'])
def summarize_pdf():
    if request.method == 'POST':
        file = request.files['pdf_file']
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        summary, keywords = generate_summary(text)
        session['summary_data'] = {
            'title': 'PDF Summary',
            'summary': summary,
            'keywords': ', '.join(keywords)
        }
        return render_template('summarize_pdf.html', summary=summary, keywords=keywords)
    return render_template('summarize_pdf.html')

@app.route('/summarize_image', methods=['POST', 'GET'])
def summarize_image():
    if request.method == 'POST':
        image = request.files['image_file']
        text = pytesseract.image_to_string(Image.open(image))
        summary, keywords = generate_summary(text)
        session['summary_data'] = {
            'title': 'Image Summary',
            'summary': summary,
            'keywords': ', '.join(keywords)
        }
        return render_template('summarize_image.html', summary=summary, keywords=keywords)
    return render_template('summarize_image.html')

@app.route('/summarize_url', methods=['POST', 'GET'])
def summarize_url():
    title = None
    url = None
    if request.method == 'POST':
        url = request.form['url']
        try:
            res = requests.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            paragraphs = soup.find_all('p')
            text = '\n'.join(p.get_text() for p in paragraphs if len(p.get_text()) > 40)
            summary, keywords = generate_summary(text)
            session['summary_data'] = {
                'title': title,
                'summary': summary,
                'keywords': ', '.join(keywords)
            }
            return render_template('summarize_url.html', summary=summary, keywords=keywords, title=title, url=url)
        except Exception as e:
            return f"Error: {str(e)}"
    return render_template('summarize_url.html')

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = session.get('summary_data')
    if not data:
        return "No summary data to download."

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, data.get('title', 'Summary'))

    c.setFont("Helvetica", 12)
    text_object = c.beginText(40, height - 80)
    text_object.setLeading(15)

    summary_lines = data.get('summary', '').split('\n')
    for line in summary_lines:
        text_object.textLine(line)

    keywords = "Keywords: " + data.get('keywords', '')
    text_object.textLine("")
    text_object.textLine(keywords)

    c.drawText(text_object)
    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="summary.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
