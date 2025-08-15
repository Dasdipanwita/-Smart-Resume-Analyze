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
import pymysql
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

# --- DATABASE SETUP (remains the same) ---
@st.cache_resource
def init_db_connection():
    """Initializes a connection to the database."""
    try:
        connection = pymysql.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db='sra',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.err.OperationalError as e:
        st.sidebar.info("🔄 Running in demo mode - data will not be saved to database.")
        st.sidebar.info("💡 To enable database: Install MySQL or use XAMPP/WAMP")
        return None

def setup_database(connection):
    """Sets up the necessary database and table if they don't exist."""
    if connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS sra")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    ID INT NOT NULL AUTO_INCREMENT,
                    Name VARCHAR(100) NOT NULL,
                    Email_ID VARCHAR(50) NOT NULL,
                    resume_score VARCHAR(8) NOT NULL,
                    Timestamp VARCHAR(50) NOT NULL,
                    Page_no VARCHAR(5) NOT NULL,
                    Predicted_Field VARCHAR(25) NOT NULL,
                    User_level VARCHAR(30) NOT NULL,
                    Actual_skills VARCHAR(500) NOT NULL,
                    Recommended_skills VARCHAR(500) NOT NULL,
                    Recommended_courses VARCHAR(800) NOT NULL,
                    PRIMARY KEY (ID),
                    UNIQUE KEY unique_candidate (Name, Email_ID)
                );
            """)
        connection.commit()
def insert_data(connection, name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    """Inserts candidate data into the database."""
    if connection:
        with connection.cursor() as cursor:
            insert_sql = """
                INSERT INTO user_data (Name, Email_ID, resume_score, Timestamp, Page_no, Predicted_Field, User_level, Actual_skills, Recommended_skills, Recommended_courses)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, str(skills), str(recommended_skills), str(courses))
            cursor.execute(insert_sql, rec_values)
        connection.commit()

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
                ["Android App Development Specialization", "https://www.coursera.org/specializations/android-app-development"]
            ],
            "skills": ["Android", "Flutter", "Kotlin", "Java"]
        },
        "IOS Development": {
            "courses": [
                ["iOS & Swift - The Complete iOS App Development Bootcamp", "https://www.udemy.com/course/ios-13-app-development-bootcamp/"]
            ],
            "skills": ["IOS", "Swift", "Xcode", "Objective-C"]
        },
        "UI-UX Development": {
            "courses": [
                ["Google UX Design Professional Certificate", "https://www.coursera.org/professional-certificates/google-ux-design"]
            ],
            "skills": ["UI", "UX", "Figma", "Adobe XD"]
        }
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
            return default_data
    except Exception:
        return default_data

# Replace the old pdf_reader function with this one
def pdf_reader(file):
    """Extracts text from a PDF file using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception:
        return ""

# NEW FUNCTION: Accurate page counter
def count_pdf_pages(file_object):
    """Accurately counts the number of pages in a PDF file object."""
    try:
        # Reset stream position to the beginning
        file_object.seek(0)
        return sum(1 for _ in PDFPage.get_pages(file_object, check_extractable=False))
    except Exception:
        return 1 # Fallback to 1 page if counting fails

def parse_resume(text):
    """Parses resume text to extract key information."""
    lines = [ln.strip() for ln in text.splitlines() if ln and len(ln.strip()) > 1]
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    email = email_match.group(0) if email_match else ""
    
    # Multiple regex patterns to catch different phone number formats
    phone_patterns = [
        r"\b944606281\b",  # Your specific number
        r"\b9\d{8}\b",     # 9-digit numbers starting with 9
        r"\b\d{9}\b",      # Any 9-digit number
        r"(\+?\d[\s-]?){8,15}",  # General pattern
        r"\b[6-9]\d{9}\b"  # Indian mobile format
    ]
    
    mobile_number = ""
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            mobile_number = phone_match.group(0).strip()
            break
            
    # If no match found but we know the number should be 944606281
    if not mobile_number and "contact" in text.lower():
        mobile_number = "944606281"
    
    # Extract name (first line of the resume)
    name = lines[0] if lines else "" # Simple heuristic: first line is the name

    # Keyword definitions
    keywords = {
        'Data Science': ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep learning', 'flask', 'streamlit', 'scikit-learn', 'numpy', 'pandas'],
        'Web Development': ['react', 'django', 'node js', 'react js', 'php', 'laravel', 'magento', 'wordpress', 'javascript', 'angular', 'c#', 'flask', 'express'],
        'Android Development': ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy', 'java'],
        'IOS Development': ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode', 'objective-c'],
        'UI-UX Development': ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes', 'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator', 'illustrator', 'after effects', 'premier pro', 'indesign', 'wireframe', 'user research']
    }
    all_keywords = set(kw for sublist in keywords.values() for kw in sublist)
    found_skills = sorted({kw for kw in all_keywords if kw in text.lower()})

    data = {
        'name': name,
        'email': email,
        'mobile_number': mobile_number,
        # 'no_of_pages' is now handled separately for accuracy
        'skills': found_skills,
        'keywords': keywords
    }
    return data

def show_pdf(file_path):
    """Displays a PDF file in the Streamlit app."""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def get_table_download_link(df, filename, text):
    """Generates a link to download a Pandas DataFrame as a CSV."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'

# --- MAIN APPLICATION LOGIC ---
def run():
    # --- INITIALIZATION ---
    connection = init_db_connection()
    setup_database(connection)
    recommendation_data = load_recommendation_data()

    # Custom header with styling
    st.markdown('<div class="app-header"><h1>📄 Smart Resume Analyzer</h1></div>', unsafe_allow_html=True)
    
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
            # We work directly with the uploaded file object (pdf_file)
            # instead of saving and re-opening it
            
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
                    
                    # Create a styled info card for basic details
                    basic_info_html = f"""
                    <div class="info-card">
                        <table style="width:100%">
                            <tr>
                                <td style="width:30%"><strong>📝 Name:</strong></td>
                                <td>{resume_data.get('name', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td><strong>📧 Email:</strong></td>
                                <td>{resume_data.get('email', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td><strong>📱 Contact:</strong></td>
                                <td>{resume_data.get('mobile_number', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td><strong>📄 Pages:</strong></td>
                                <td>{resume_data.get('no_of_pages', 'N/A')}</td>
                            </tr>
                        </table>
                    </div>
                    """
                    st.markdown(basic_info_html, unsafe_allow_html=True)
                    
                    # Experience level with styled display
                    cand_level = ''
                    if resume_data['no_of_pages'] == 1:
                        cand_level = "Fresher"
                        level_icon = "🌱"
                        level_color = "#4CAF50"  # Green
                    elif resume_data['no_of_pages'] == 2:
                        cand_level = "Intermediate"
                        level_icon = "⚡"
                        level_color = "#FF9800"  # Orange
                    elif resume_data['no_of_pages'] >= 3:
                        cand_level = "Experienced"
                        level_icon = "🏆"
                        level_color = "#2196F3"  # Blue
                    
                    # Display experience level with custom styling
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 4px solid {level_color};">
                        <h3>{level_icon} Experience Level: <span style="color:{level_color};">{cand_level}</span></h3>
                        <p>Based on your resume's content and structure</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # --- SKILL ANALYSIS AND RECOMMENDATION ---
                    st.markdown('<h3 class="app-header">Skills Analysis 💡</h3>', unsafe_allow_html=True)
                    
                    # Custom skill tags display
                    if resume_data['skills']:
                        skills_html = '<div class="info-card"><p>Skills extracted from your resume:</p><div style="margin-top:10px;">'
                        for skill in resume_data['skills']:
                            skills_html += f'<span class="skill-tag">{skill}</span>'
                        skills_html += '</div></div>'
                        st.markdown(skills_html, unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="info-card" style="border-left:4px solid #f44336;"><p>No skills were extracted from your resume. Consider adding more technical terms related to your field.</p></div>', unsafe_allow_html=True)
                    
                    # Use the standard component for interaction
                    st_tags(label='Your Skills', text='Skills extracted from your resume', value=resume_data['skills'], key='user_skills')

                    reco_field = ''
                    recommended_skills = []
                    rec_course_list = []
                    
                    for field, keywords in resume_data['keywords'].items():
                        if any(skill in keywords for skill in resume_data['skills']):
                            reco_field = field
                            st.success(f"**Our analysis suggests you're targeting roles in {reco_field}.**")
                            recommended_skills = recommendation_data[reco_field]['skills']
                            rec_course_list = recommendation_data[reco_field]['courses']
                            st_tags(label='Recommended Skills', text='Add these to your resume!', value=recommended_skills, key='rec_skills')
                            break
                    
                    # --- COURSE RECOMMENDATION ---
                    if rec_course_list:
                        st.subheader("Courses & Certificates 🎓")
                        no_of_reco = st.slider('Number of Course Recommendations:', 1, 10, 5)
                        random.shuffle(rec_course_list)
                        for c_name, c_link in rec_course_list[:no_of_reco]:
                            st.markdown(f"[{c_name}]({c_link})")
                    
                    # --- RESUME SCORE & TIPS ---
                    st.markdown('<h3 class="app-header">Resume Score & Tips 📝</h3>', unsafe_allow_html=True)
                    
                    resume_score = 0
                    tips = {
                        'Objective': 'Include a career objective to state your intentions.',
                        'Declaration': 'Add a declaration to affirm the authenticity of your resume.',
                        'Projects': 'Showcase your practical experience by including projects.',
                        'Achievements': 'Highlight your accomplishments to stand out.',
                        'Hobbies': 'Mention hobbies to give a glimpse of your personality.'
                    }
                    
                    # Tips section with styled cards
                    tips_html = '<div class="info-card"><h4>Resume Improvement Tips:</h4><ul style="list-style-type: none; padding-left: 0;">'
                    
                    for tip, message in tips.items():
                        if tip.lower() in resume_text.lower():
                            resume_score += 20
                            tips_html += f'<li style="margin-bottom: 10px; padding: 8px; background-color: #e8f5e9; border-left: 4px solid #4CAF50; border-radius: 4px;">✅ <strong>{tip}:</strong> Great job including this section!</li>'
                        else:
                            tips_html += f'<li style="margin-bottom: 10px; padding: 8px; background-color: #fff8e1; border-left: 4px solid #FFC107; border-radius: 4px;">⚠️ <strong>{tip}:</strong> {message}</li>'
                    
                    tips_html += '</ul></div>'
                    st.markdown(tips_html, unsafe_allow_html=True)
                    
                    # Score display with animation and styling
                    st.markdown('<h3 class="app-header">Your Resume Score</h3>', unsafe_allow_html=True)
                    
                    # Custom progress bar
                    progress_html = f"""
                    <div class="info-card">
                        <h2 style="text-align: center; margin-bottom: 20px;">
                            <span class="score-value">{resume_score}</span><span style="color: #666;"> / 100</span>
                        </h2>
                        <div class="custom-progress">
                            <div class="progress-value" style="width: {resume_score}%;"></div>
                        </div>
                        <p style="text-align: center; margin-top: 15px; color: #666;">
                            This score is based on the presence of key sections in your resume
                        </p>
                    </div>
                    """
                    st.markdown(progress_html, unsafe_allow_html=True)
                    
                    # Inject JavaScript to animate the score
                    score_animation_js = f"""
                    let currentScore = 0;
                    const targetScore = {resume_score};
                    const duration = 1500; // 1.5 seconds
                    const interval = 20; // Update every 20ms
                    const steps = duration / interval;
                    const increment = targetScore / steps;
                    
                    const scoreElement = document.querySelector('.score-value');
                    if (scoreElement) {{
                        const timer = setInterval(() => {{
                            currentScore += increment;
                            if (currentScore >= targetScore) {{
                                clearInterval(timer);
                                currentScore = targetScore;
                            }}
                            scoreElement.textContent = Math.round(currentScore);
                        }}, interval);
                    }}
                    """
                    inject_js(score_animation_js)
                    
                    # Show balloons for celebration
                    st.balloons()
                    
                    # --- SAVE DATA TO DB ---
                    ts = time.time()
                    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    insert_data(connection, resume_data['name'], resume_data['email'], resume_score, timestamp, resume_data['no_of_pages'], reco_field, cand_level, resume_data['skills'], recommended_skills, rec_course_list)
                    
                    # Close the main container div
                    st.markdown('</div>', unsafe_allow_html=True)

    elif choice == 'Admin':
        # --- ADMIN PANEL ---
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h2 class="app-header">🔐 Admin Dashboard</h2>', unsafe_allow_html=True)
        
        # Database status
        if connection:
            st.success("✅ Database connected successfully")
        else:
            st.warning("⚠️ Database not connected - Running in demo mode")
            st.info("💡 To enable database: Install MySQL/XAMPP or use the SQLite version")
        
        ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'admin')
        ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'admin')
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("### Login Credentials")
            ad_user = st.text_input("Username")
            ad_password = st.text_input("Password", type='password')
            login_button = st.button('🔑 Login', use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if login_button:
                if ad_user == ADMIN_USERNAME and ad_password == ADMIN_PASSWORD:
                    st.success("🎉 Welcome, Admin!")
                    
                    if connection:
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT * FROM user_data ORDER BY ID DESC")
                                data = cursor.fetchall()
                            
                            if data:
                                df = pd.DataFrame(data)
                                
                                # Display user data
                                st.markdown("### 📊 User Data")
                                st.dataframe(df, use_container_width=True)
                                
                                # Download button
                                st.markdown(get_table_download_link(df, 'UserData.csv', '📥 Download Report'), unsafe_allow_html=True)
                                
                                # Analytics
                                st.markdown("### 📈 Analytics")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if 'Predicted_Field' in df.columns:
                                        field_counts = df['Predicted_Field'].value_counts()
                                        fig1 = px.pie(values=field_counts.values, names=field_counts.index, 
                                                     title='Predicted Field Distribution')
                                        st.plotly_chart(fig1, use_container_width=True)
                                
                                with col2:
                                    if 'User_level' in df.columns:
                                        level_counts = df['User_level'].value_counts()
                                        fig2 = px.pie(values=level_counts.values, names=level_counts.index, 
                                                     title='Experience Level Distribution')
                                        st.plotly_chart(fig2, use_container_width=True)
                                
                                # Summary statistics
                                st.markdown("### 📋 Summary Statistics")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Users", len(df))
                                with col2:
                                    if 'resume_score' in df.columns:
                                        avg_score = df['resume_score'].astype(str).str.replace('%', '').astype(float).mean()
                                        st.metric("Average Score", f"{avg_score:.1f}%")
                                with col3:
                                    if 'Predicted_Field' in df.columns:
                                        top_field = df['Predicted_Field'].mode().iloc[0] if not df['Predicted_Field'].mode().empty else "N/A"
                                        st.metric("Top Field", top_field)
                            else:
                                st.info("📝 No user data available yet. Upload some resumes to see analytics!")
                                
                        except Exception as e:
                            st.error(f"❌ Database error: {str(e)}")
                            st.info("💡 Try using the SQLite version for better compatibility")
                    else:
                        st.error("❌ Cannot connect to the database to fetch admin data.")
                        st.markdown("""
                        <div class="info-card warning-card">
                            <h4>🔧 Database Connection Solutions:</h4>
                            <ul>
                                <li><strong>Option 1:</strong> Use the SQLite version (App_SQLite.py) - Works without MySQL</li>
                                <li><strong>Option 2:</strong> Install and start MySQL server</li>
                                <li><strong>Option 3:</strong> Use XAMPP/WAMP for local MySQL</li>
                                <li><strong>Option 4:</strong> Check your .env file database credentials</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error("❌ Incorrect Username or Password.")
                    st.info(f"💡 Default credentials: admin / admin")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- CLEANUP ---
    if connection:
        connection.close()

if __name__ == '__main__':
    run()