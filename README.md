# 📝 Content Summarizer  

This is a **text summarizer web app** that can summarize content from:  
- ✍️ Plain Text  
- 🖼️ Image (using OCR)  
- 📄 PDF files  
- 🔗 URLs (web pages)  

It also allows users to **download the summary** and includes a **login/register system** for a personalized experience.

---

## Live Demo Link  
https://multi-source-summarizer-1.onrender.com/  

---

## 🚀 Features

- ✅ Summarize typed or pasted text
- ✅ Extract and summarize text from **images** (OCR)
- ✅ Extract and summarize from **PDFs**
- ✅ Fetch and summarize content from **URLs**
- ✅ **Download** summary as a `.txt` file
- ✅ Login and Signup system with password protection

---

## 💻 Technologies Used

- **Frontend**: HTML, CSS, JavaScript  
- **Backend**: Flask (Python)  
- **Database**: SQLite  
- **OCR**: Tesseract OCR  
- **Other**: Flask session management, file handling

---

## 📦 How to Run the Project

### 1. Clone the repository

git clone https://github.com/Sakshitak19/multi_source_summarizer.git
cd multi_source_summarizer  

### 2. Create virtual environment (optional but recommended)   

python -m venv venv  
venv\Scripts\activate  # for Windows  
#source venv/bin/activate  # for Linux/macOS  

### 3. Install dependencies  
pip install flask pytesseract pillow requests beautifulsoup4  

### 4. Install Tesseract OCR  
Download from: https://github.com/tesseract-ocr/tesseract  
After install, make sure it's added to your system path 

### 5. Run the app  
python app.py  


---

## 📁 Folder Structure  

multi_source_summarizer/  
│
├── static/               # CSS, JS, Images  
├── templates/            # HTML files  
├── instance/             # Contains SQLite database  
├── app.py                # Main Flask app  
├── utils.py              # (Optional) helper functions  
├── requirements.txt      # Python dependencies  
└── README.md  


---

## 🔐 Security  
Make sure to:  
- Hide your database using .gitignore
- Don't upload instance/database.db to GitHub


Add this to .gitignore:
- instance/database.db


---

## Made with 💖 by Sakshi Tak  
## Feel free to ⭐️ this repo if you find it helpful!  
 
