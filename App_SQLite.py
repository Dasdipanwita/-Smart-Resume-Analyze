import streamlit as st
import pandas as pd
import base64
import time
import datetime
import io
import re
import os
import json
import random
import sqlite3
import pdfplumber
import plotly.express as px
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage # Import PDFPage for accurate page counting
from streamlit_tags import st_tags
from dotenv import load_dotenv
import streamlit.components.v1 as components

load_dotenv() # Load variables from .env file

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon="📄",
    layout="wide"
)

# --- LOAD CSS AND JAVASCRIPT ---
def load_css():
    # Load completely new CSS design
    with open(os.path.join(os.path.dirname(__file__), "new_style.css")) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load custom CSS
load_css()

# Professional styling is now handled by new_style.css

# Function to inject custom JavaScript
def inject_js(js_code):
    components.html(
        f"""
        <script type="text/javascript">
        // Wrap in a function to avoid global scope issues
        (function() {{
            {js_code}
            
            // Call the initialization function
            document.addEventListener('DOMContentLoaded', function() {{
                initializeApp();
            }});
            
            // Also try to run it immediately in case DOM is already loaded
            try {{
                initializeApp();
            }} catch(e) {{
                console.log('Will initialize on DOMContentLoaded');
            }}
        }})();
        </script>
        """,
        height=0,
    )

# --- SQLITE DATABASE SETUP ---
@st.cache_resource
def init_db_connection():
    """Initializes a connection to SQLite database."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'resume_analyzer.db')
        connection = sqlite3.connect(db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
        return connection
    except Exception as e:
        st.sidebar.warning(f"DB Connection failed: {e}. Data will not be saved.")
        return None

def setup_database(connection):
    """Sets up the necessary database and table if they don't exist."""
    if connection:
        cursor = connection.cursor()
        try:
            # SQLite doesn't need CREATE DATABASE command - database is created when connecting
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    Email_ID TEXT NOT NULL,
                    resume_score TEXT NOT NULL,
                    Timestamp TEXT NOT NULL,
                    Page_no TEXT NOT NULL,
                    Predicted_Field TEXT NOT NULL,
                    User_level TEXT NOT NULL,
                    Actual_skills TEXT NOT NULL,
                    Recommended_skills TEXT NOT NULL,
                    Recommended_courses TEXT NOT NULL,
                    UNIQUE(Name, Email_ID)
                );
            """)
            connection.commit()
        finally:
            cursor.close()
def insert_data(connection, name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    """Inserts or updates candidate data in the database."""
    if connection:
        cursor = connection.cursor()
        try:
            # Check if the record already exists
            cursor.execute("SELECT ID FROM user_data WHERE Name = ? AND Email_ID = ?", (name, email))
            data = cursor.fetchone()

            if data:
                # Record exists, so we can update it (optional)
                update_sql = """
                    UPDATE user_data SET
                        resume_score = ?, Timestamp = ?, Page_no = ?, Predicted_Field = ?,
                        User_level = ?, Actual_skills = ?, Recommended_skills = ?, Recommended_courses = ?
                    WHERE ID = ?
                """
                update_values = (str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, str(skills), str(recommended_skills), str(courses), data[0])
                cursor.execute(update_sql, update_values)
                st.success("Resume analysis updated successfully!") # Inform user of update
            else:
                # Record does not exist, insert a new one
                insert_sql = """
                    INSERT INTO user_data (Name, Email_ID, resume_score, Timestamp, Page_no, Predicted_Field, User_level, Actual_skills, Recommended_skills, Recommended_courses)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, str(skills), str(recommended_skills), str(courses))
                cursor.execute(insert_sql, rec_values)
                st.success("Resume analysis saved successfully!") # Inform user of new save

            connection.commit()
        finally:
            cursor.close()

# --- HELPER FUNCTIONS ---
def load_recommendation_data(file_path='courses.json'):
    """Loads course/skill recommendations from JSON, with safe fallback defaults."""
    default_data = {
        "Data Science": {
            "courses": [
                ["Machine Learning Crash Course by Google [Free]", "https://developers.google.com/machine-learning/crash-course"],
                ["Machine Learning A-Z by Udemy", "https://www.udemy.com/course/machinelearning/"],
                ["Machine Learning by Andrew NG", "https://www.coursera.org/learn/machine-learning"],
                ["Data Scientist Master Program of Simplilearn (IBM)", "https://www.simplilearn.com/big-data-and-analytics/senior-data-scientist-masters-program-training"],
                ["Data Science Foundations: Fundamentals by LinkedIn", "https://www.linkedin.com/learning/data-science-foundations-fundamentals-5"]
            ],
            "skills": ["Data Visualization", "Predictive Analysis", "Statistical Modeling", "Data Mining", "ML Algorithms", "Keras", "Pytorch", "Scikit-learn", "Tensorflow", "Flask", "Streamlit"]
        },
        "Web Development": {
            "courses": [
                ["Django Crash course [Free]", "https://youtu.be/e1IyzVyrLSU"],
                ["Python and Django Full Stack Web Developer Bootcamp", "https://www.udemy.com/course/python-and-django-full-stack-web-developer-bootcamp"],
                ["React Crash Course [Free]", "https://youtu.be/Dorf8i6lCuk"]
            ],
            "skills": ["React", "Django", "Node JS", "React JS", "Javascript", "Angular JS", "Flask"]
        },
        "Android Development": {
            "courses": [
                ["Android Development for Beginners [Free]", "https://youtu.be/fis26HvvDII"],
                ["Android App Development Specialization", "https://www.coursera.org/specializations/android-app-development"],
                ["Complete Android Developer Course", "https://www.udemy.com/course/complete-android-n-developer-course/"]
            ],
            "skills": ["Java", "Kotlin", "XML", "Android Studio", "Firebase", "SQLite", "Material Design"]
        },
        "IOS Development": {
            "courses": [
                ["iOS App Development with Swift", "https://www.coursera.org/specializations/app-development"],
                ["Complete iOS Developer Course", "https://www.udemy.com/course/ios-13-app-development-bootcamp/"]
            ],
            "skills": ["Swift", "Objective-C", "Xcode", "Core Data", "UIKit", "SwiftUI"]
        },
        "UI-UX Development": {
            "courses": [
                ["Google UX Design Professional Certificate", "https://www.coursera.org/professional-certificates/google-ux-design"],
                ["UI/UX Design Specialization", "https://www.coursera.org/specializations/ui-ux-design"]
            ],
            "skills": ["Figma", "Adobe XD", "Sketch", "Prototyping", "User Research", "Wireframing", "Visual Design"]
        }
    }
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = json.load(file)
                return data
        else:
            # Create the file with default data
            with open(file_path, 'w') as file:
                json.dump(default_data, file, indent=4)
            return default_data
    except Exception as e:
        st.warning(f"Could not load recommendation data: {e}. Using defaults.")
        return default_data

def pdf_reader(file):
    """Extracts text from PDF using pdfplumber for better accuracy."""
    try:
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def count_pdf_pages(file):
    """Counts the number of pages in a PDF file."""
    try:
        with pdfplumber.open(file) as pdf:
            return len(pdf.pages)
    except Exception as e:
        st.error(f"Error counting PDF pages: {e}")
        return 0

def parse_resume(text):
    """Parses resume text and extracts relevant information with improved regex."""
    if not text.strip():
        return None
    
    # Initialize data structure
    resume_data = {
        'name': 'Not Found',
        'email': 'Not Found',
        'mobile_number': 'Not Found',
        'skills': [],
    }
    
    # --- 1. Improved Name Extraction ---
    # Try to find a line with 2-3 words that is likely a name
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:5]:  # Check the first 5 lines
        if 2 <= len(line.split()) <= 4 and not re.search(r'\d|@|http|:|www', line, re.IGNORECASE):
            resume_data['name'] = line
            break
            
    # --- 2. Improved Email Extraction ---
    # A robust regex for finding email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    if email_match:
        resume_data['email'] = email_match.group(0)
    
    # --- 3. Improved Mobile Number Extraction ---
    # A powerful regex that handles various formats (e.g., +91, (xxx), xxx-xxx-xxxx)
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4,}'
    phone_match = re.search(phone_pattern, text)
    if phone_match:
        # Clean up the found number by removing non-digit characters
        resume_data['mobile_number'] = re.sub(r'\D', '', phone_match.group(0))

    # --- 4. Skill Extraction (remains the same) ---
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 'express',
        'django', 'flask', 'spring', 'hibernate', 'mysql', 'postgresql', 'mongodb',
        'html', 'css', 'bootstrap', 'jquery', 'php', 'laravel', 'codeigniter',
        'machine learning', 'data science', 'artificial intelligence', 'deep learning',
        'tensorflow', 'keras', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'git', 'github', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'android', 'ios', 'swift', 'kotlin', 'flutter', 'react native',
        'figma', 'adobe', 'photoshop', 'illustrator', 'sketch', 'ui', 'ux'
    ]
    
    text_lower = text.lower()
    found_skills = {skill.title() for skill in skill_keywords if skill in text_lower}
    resume_data['skills'] = sorted(list(found_skills))
    
    return resume_data

def recommend_skills_and_courses(skills, field):
    """Recommends skills and courses based on detected field."""
    recommendation_data = load_recommendation_data()
    
    if field in recommendation_data:
        recommended_skills = recommendation_data[field]['skills']
        courses = recommendation_data[field]['courses']
        
        # Filter out skills already present
        missing_skills = [skill for skill in recommended_skills if skill.lower() not in [s.lower() for s in skills]]
        
        return missing_skills[:10], courses[:5]  # Limit recommendations
    
    return [], []

def predict_field(skills):
    """Predicts the field based on skills."""
    skill_text = ' '.join(skills).lower()
    
    # Define field keywords
    field_keywords = {
        'Data Science': ['python', 'machine learning', 'data', 'pandas', 'numpy', 'tensorflow', 'keras', 'scikit-learn'],
        'Web Development': ['html', 'css', 'javascript', 'react', 'angular', 'node', 'django', 'flask', 'php'],
        'Android Development': ['android', 'java', 'kotlin', 'xml'],
        'IOS Development': ['ios', 'swift', 'objective-c', 'xcode'],
        'UI-UX Development': ['ui', 'ux', 'figma', 'adobe', 'sketch', 'design']
    }
    
    field_scores = {}
    for field, keywords in field_keywords.items():
        score = sum(1 for keyword in keywords if keyword in skill_text)
        field_scores[field] = score
    
    if field_scores and max(field_scores.values()) > 0:
        return max(field_scores, key=field_scores.get)
    
    return "General"

def calculate_resume_score(resume_data):
    """Calculates a resume score based on various factors."""
    score = 0
    
    # Basic information (30 points)
    if resume_data.get('name'): score += 10
    if resume_data.get('email'): score += 10
    if resume_data.get('mobile_number'): score += 10
    
    # Skills (40 points)
    skill_count = len(resume_data.get('skills', []))
    if skill_count >= 10: score += 40
    elif skill_count >= 7: score += 30
    elif skill_count >= 5: score += 20
    elif skill_count >= 3: score += 10
    
    # Additional factors (30 points)
    # This is a simplified scoring system
    score += min(30, skill_count * 2)
    
    return min(100, score)  # Cap at 100

def determine_candidate_level(score, skills_count):
    """Determines candidate level based on score and skills."""
    if score >= 80 and skills_count >= 8:
        return "Experienced"
    elif score >= 60 and skills_count >= 5:
        return "Intermediate"
    else:
        return "Fresher"

# --- MAIN APPLICATION ---
def main():
    # Header
    st.markdown("""
    <div class="app-header">
        <h1>🎯 Smart Resume Analyzer</h1>
        <p>AI-Powered Resume Analysis & Career Recommendations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize database
    connection = init_db_connection()
    if connection:
        setup_database(connection)
        st.sidebar.success("✅ Database connected (SQLite)")
    
    # Sidebar with custom styling
    st.sidebar.markdown('<div class="app-header"><h2>User Selection</h2></div>', unsafe_allow_html=True)
    
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose your role:", activities)

    # Inject JavaScript for UI enhancements
    with open(os.path.join(os.path.dirname(__file__), "script.js"), 'r') as file:
        js_content = file.read()
        inject_js(js_content)

    if choice == 'Normal User':
        # --- USER INTERFACE ---
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        
        # Custom upload area with professional styling
        st.markdown("""
        <div class="upload-section">
            <h3>📤 Upload Your Resume</h3>
            <p>Drag and drop your PDF resume here or click to browse</p>
        """, unsafe_allow_html=True)
        
        # Place the file uploader inside our custom container
        pdf_file = st.file_uploader("", type=["pdf"])
        
        # Close the upload area container
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Close the main container
        st.markdown('</div>', unsafe_allow_html=True)
        
        if pdf_file is not None:
            # Create a persistent in-memory copy for multiple reads
            pdf_bytes = io.BytesIO(pdf_file.getvalue())
            
            # Display the PDF and analyze it
            col1, col2 = st.columns([3, 5])
            
            with col1:
                st.markdown('<div class="main-card">', unsafe_allow_html=True)
                st.markdown('<h2 class="app-header">Resume Preview</h2>', unsafe_allow_html=True)
                
                # Display the PDF with custom styling
                base64_pdf = base64.b64encode(pdf_bytes.read()).decode('utf-8')
                pdf_display = f'<div class="resume-display"><iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe></div>'
                st.markdown(pdf_display, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Rewind after preview read
                pdf_bytes.seek(0)

            with col2:
                # --- RESUME ANALYSIS ---
                st.markdown('<div class="main-card">', unsafe_allow_html=True)
                st.markdown('<h2 class="app-header">Resume Analysis</h2>', unsafe_allow_html=True)
                
                # Show loading animation
                with st.spinner("Analyzing your resume..."):
                    # Ensure stream at start before text extraction
                    pdf_bytes.seek(0)
                    resume_text = pdf_reader(pdf_bytes)
                    resume_data = parse_resume(resume_text)
                    
                    # Accurately count pages using the new function
                    # Rewind again before counting pages
                    pdf_bytes.seek(0)
                    page_count = count_pdf_pages(pdf_bytes)
                    resume_data['no_of_pages'] = page_count


                if resume_data:
                    # Welcome message with animation
                    st.markdown(f'<div class="info-card"><h3>👋 Hello {resume_data["name"]}!</h3></div>', unsafe_allow_html=True)
                    
                    # Basic info section with styled cards
                    st.markdown('<h3 class="app-header">Your Basic Info</h3>', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f'<div class="info-card"><strong>📧 Email:</strong> {resume_data["email"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-card"><strong>📱 Mobile:</strong> {resume_data["mobile_number"]}</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f'<div class="info-card"><strong>📄 Pages:</strong> {resume_data["no_of_pages"]}</div>', unsafe_allow_html=True)
                    
                    # Skills section
                    st.markdown('<h3 class="app-header">🛠️ Detected Skills</h3>', unsafe_allow_html=True)
                    if resume_data['skills']:
                        skills_html = ''.join([f'<span class="skill-tag">{skill}</span>' for skill in resume_data['skills']])
                        st.markdown(f'<div class="info-card">{skills_html}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="info-card warning-card">No specific technical skills detected. Consider adding more technical skills to your resume.</div>', unsafe_allow_html=True)
                    
                    # Predict field and calculate score
                    predicted_field = predict_field(resume_data['skills'])
                    resume_score = calculate_resume_score(resume_data)
                    candidate_level = determine_candidate_level(resume_score, len(resume_data['skills']))
                    
                    # Score and level
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Resume Score", f"{resume_score}%", delta=None)
                    with col2:
                        st.metric("Candidate Level", candidate_level, delta=None)
                    
                    # Field prediction
                    st.markdown(f'<div class="info-card success-card"><strong>🎯 Predicted Field:</strong> {predicted_field}</div>', unsafe_allow_html=True)
                    
                    # Recommendations
                    recommended_skills, recommended_courses = recommend_skills_and_courses(resume_data['skills'], predicted_field)
                    
                    if recommended_skills:
                        st.markdown('<h3 class="app-header">💡 Recommended Skills</h3>', unsafe_allow_html=True)
                        skills_html = ''.join([f'<span class="skill-tag">{skill}</span>' for skill in recommended_skills])
                        st.markdown(f'<div class="info-card">{skills_html}</div>', unsafe_allow_html=True)
                    
                    if recommended_courses:
                        st.markdown('<h3 class="app-header">📚 Recommended Courses</h3>', unsafe_allow_html=True)
                        for course_name, course_link in recommended_courses:
                            st.markdown(f'<div class="info-card">📖 <a href="{course_link}" target="_blank">{course_name}</a></div>', unsafe_allow_html=True)
                    
                    # Save to database
                    if connection:
                        try:
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            insert_data(
                                connection,
                                resume_data['name'],
                                resume_data['email'],
                                resume_score,
                                timestamp,
                                resume_data['no_of_pages'],
                                predicted_field,
                                candidate_level,
                                resume_data['skills'],
                                recommended_skills,
                                recommended_courses
                            )
                            st.success("✅ Data saved successfully!")
                        except Exception as e:
                            st.error(f"Error saving data: {e}")
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    elif choice == 'Admin':
        # --- ADMIN INTERFACE ---
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h2 class="app-header">Admin Dashboard</h2>', unsafe_allow_html=True)
        
        # Admin authentication
        admin_user = st.text_input("Username")
        admin_pass = st.text_input("Password", type='password')
        
        if st.button("Login"):
            if admin_user == os.environ.get('ADMIN_USER', 'admin') and admin_pass == os.environ.get('ADMIN_PASS', 'admin'):
                st.success("✅ Login successful!")
                
                if connection:
                    # Display user data
                    cursor = connection.cursor()
                    cursor.execute("SELECT * FROM user_data ORDER BY ID DESC")
                    data = cursor.fetchall()
                    
                    if data:
                        # Convert to DataFrame for better display
                        df = pd.DataFrame(data)
                        st.dataframe(df)
                        
                        # Download option
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Data as CSV",
                            data=csv,
                            file_name=f"resume_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No data available yet.")
                else:
                    st.warning("Database not connected.")
            else:
                st.error("❌ Invalid credentials!")
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()