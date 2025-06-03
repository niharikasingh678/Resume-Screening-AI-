from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import re
import PyPDF2
import docx
from werkzeug.utils import secure_filename
from datetime import datetime
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = 'your-secret-key-change-this'

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

def extract_text_from_file(file_path):
    """Extract text based on file extension"""
    extension = file_path.rsplit('.', 1)[1].lower()
    if extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif extension == 'docx':
        return extract_text_from_docx(file_path)
    elif extension == 'txt':
        return extract_text_from_txt(file_path)
    else:
        return "Unsupported file format"

class ResumeAnalyzer:
    def __init__(self):
        # Keywords for different categories
        self.technical_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'sql', 'mysql', 'postgresql', 'mongodb', 'html', 'css', 'git',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'machine learning',
            'data science', 'tensorflow', 'pytorch', 'flask', 'django', 'spring'
        ]
        
        self.soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving',
            'analytical', 'creative', 'adaptable', 'organized', 'detail-oriented',
            'collaborative', 'innovative', 'strategic', 'project management'
        ]
        
        self.education_keywords = [
            'bachelor', 'master', 'phd', 'degree', 'university', 'college',
            'engineering', 'computer science', 'mba', 'certification'
        ]
        
        self.experience_indicators = [
            'years', 'experience', 'worked', 'developed', 'managed', 'led',
            'implemented', 'created', 'designed', 'built', 'achieved'
        ]

    def extract_email(self, text):
        """Extract email address from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else None

    def extract_phone(self, text):
        """Extract phone number from text"""
        phone_patterns = [
            r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
            r'\+?(\d{1,3})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                return ''.join(phones[0])
        return None

    def count_keywords(self, text, keywords):
        """Count occurrences of keywords in text"""
        text_lower = text.lower()
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        return found_keywords

    def analyze_experience_level(self, text):
        """Analyze experience level based on text content"""
        text_lower = text.lower()
        
        # More specific patterns for years of experience
        experience_patterns = [
            r'(\d+)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp|working)',
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:in|with|of)',
            r'(?:experience|exp).*?(\d+)\s*(?:years?|yrs?)',
            r'(\d+)\s*(?:years?|yrs?)\s*(?:professional|work|career)'
        ]
        
        found_years = []
        for pattern in experience_patterns:
            years = re.findall(pattern, text_lower)
            found_years.extend([int(year) for year in years])
        
        # Strong fresher/entry-level indicators
        fresher_indicators = [
            'fresher', 'fresh graduate', 'recent graduate', 'new graduate',
            'entry level', 'entry-level', 'seeking first job', 'first opportunity',
            'no experience', 'no prior experience', 'looking for internship',
            'student', 'final year', 'pursuing', 'completing degree',
            'career objective', 'seeking opportunity', 'enthusiastic beginner'
        ]
        
        # Strong senior indicators (only if really senior)
        senior_indicators = [
            'senior manager', 'senior director', 'senior architect', 
            'team lead', 'project manager', 'technical lead',
            'senior consultant', 'principal engineer', 'chief',
            'head of', 'vp ', 'vice president', 'director of'
        ]
        
        # Junior/entry indicators
        junior_indicators = [
            'intern', 'trainee', 'junior', 'associate', 'assistant',
            'entry', 'beginner', 'starting career'
        ]
        
        # Check for explicit fresher indicators first
        if any(indicator in text_lower for indicator in fresher_indicators):
            return "Fresher", "0"
        
        # If years are explicitly mentioned, use them
        if found_years:
            max_years = max(found_years)
            # Filter out unrealistic years (like graduation years)
            if max_years > 50:  # Likely a year, not experience
                found_years = [y for y in found_years if y <= 50]
                max_years = max(found_years) if found_years else 0
            
            if max_years == 0:
                return "Fresher", "0"
            elif max_years <= 1:
                return "Entry Level", f"{max_years}"
            elif max_years <= 3:
                return "Junior", f"{max_years}"
            elif max_years <= 7:
                return "Mid-level", f"{max_years}"
            else:
                return "Senior", f"{max_years}"
        
        # Check for senior indicators (be more strict)
        senior_count = sum(1 for indicator in senior_indicators if indicator in text_lower)
        if senior_count >= 2:  # Need multiple senior indicators
            return "Senior", "5+"
        
        # Check for junior indicators
        if any(indicator in text_lower for indicator in junior_indicators):
            return "Entry Level", "0-1"
        
        # Check for educational indicators that suggest fresh graduate
        education_fresh_indicators = [
            'bachelor', 'b.tech', 'b.e.', 'bca', 'mca', 'master',
            'graduated', 'degree', 'university', 'college'
        ]
        
        work_indicators = [
            'worked', 'employed', 'job', 'company', 'organization',
            'developed', 'managed', 'led', 'supervised', 'coordinated'
        ]
        
        education_mentions = sum(1 for indicator in education_fresh_indicators if indicator in text_lower)
        work_mentions = sum(1 for indicator in work_indicators if indicator in text_lower)
        
        # If lots of education mentions but few work mentions, likely fresher
        if education_mentions > work_mentions and work_mentions < 3:
            return "Fresher", "0"
        
        # Default to entry level if unclear
        return "Entry Level", "0-1"

    def calculate_score(self, analysis):
        """Calculate overall resume score"""
        score = 0
        max_score = 100
        
        # Contact information (10 points)
        if analysis['contact_info']['email']:
            score += 5
        if analysis['contact_info']['phone']:
            score += 5
        
        # Technical skills (30 points) - adjusted for experience level
        tech_skill_count = len(analysis['technical_skills'])
        experience_level = analysis['experience_level'][0]
        
        if experience_level in ['Fresher', 'Entry Level']:
            # More lenient for freshers - even 2-3 skills are good
            score += min(tech_skill_count * 5, 30)
        else:
            score += min(tech_skill_count * 3, 30)
        
        # Soft skills (20 points)
        soft_skill_count = len(analysis['soft_skills'])
        score += min(soft_skill_count * 2, 20)
        
        # Education (20 points for freshers, 15 for experienced)
        education_count = len(analysis['education_keywords'])
        if experience_level in ['Fresher', 'Entry Level']:
            score += min(education_count * 4, 20)
        else:
            score += min(education_count * 3, 15)
        
        # Experience indicators (15 points for freshers, 25 for experienced)
        experience_count = len(analysis['experience_indicators'])
        if experience_level in ['Fresher', 'Entry Level']:
            # For freshers, focus on projects, coursework, internships
            score += min(experience_count * 3, 15)
        else:
            score += min(experience_count * 2, 25)
        
        # Bonus points for freshers with projects/internships
        if experience_level in ['Fresher', 'Entry Level']:
            project_keywords = ['project', 'internship', 'coursework', 'assignment', 
                              'certification', 'workshop', 'seminar', 'training']
            project_count = sum(1 for keyword in project_keywords 
                              if keyword in analysis.get('text', '').lower())
            score += min(project_count * 2, 10)
        
        return min(score, max_score)

    def analyze_resume(self, text):
        """Main method to analyze resume text"""
        analysis = {
            'text': text,  # Store original text for reference
            'contact_info': {
                'email': self.extract_email(text),
                'phone': self.extract_phone(text)
            },
            'technical_skills': self.count_keywords(text, self.technical_skills),
            'soft_skills': self.count_keywords(text, self.soft_skills),
            'education_keywords': self.count_keywords(text, self.education_keywords),
            'experience_indicators': self.count_keywords(text, self.experience_indicators),
            'experience_level': self.analyze_experience_level(text),
            'word_count': len(text.split()),
            'character_count': len(text)
        }
        
        analysis['score'] = self.calculate_score(analysis)
        analysis['recommendations'] = self.generate_recommendations(analysis)
        
        return analysis

    def generate_recommendations(self, analysis):
        """Generate recommendations based on analysis"""
        recommendations = []
        experience_level = analysis['experience_level'][0]
        
        if not analysis['contact_info']['email']:
            recommendations.append("Add a professional email address")
        
        if not analysis['contact_info']['phone']:
            recommendations.append("Include a phone number for contact")
        
        # Experience-level specific recommendations
        if experience_level in ['Fresher', 'Entry Level']:
            if len(analysis['technical_skills']) < 3:
                recommendations.append("Add more relevant technical skills from your coursework or self-learning")
            
            if len(analysis['soft_skills']) < 2:
                recommendations.append("Highlight soft skills gained through projects, group work, or internships")
            
            # Check for project keywords
            project_keywords = ['project', 'internship', 'coursework', 'assignment']
            if not any(keyword in analysis.get('text', '').lower() for keyword in project_keywords):
                recommendations.append("Include academic projects, internships, or relevant coursework")
            
            recommendations.append("Consider adding certifications or online courses to strengthen your profile")
            
        else:
            if len(analysis['technical_skills']) < 5:
                recommendations.append("Consider adding more relevant technical skills")
            
            if len(analysis['soft_skills']) < 3:
                recommendations.append("Highlight more soft skills and interpersonal abilities")
        
        # General recommendations
        if analysis['word_count'] < 150:
            if experience_level in ['Fresher', 'Entry Level']:
                recommendations.append("Expand your resume with more details about projects, education, and skills")
            else:
                recommendations.append("Consider expanding your resume with more details about your experience")
        elif analysis['word_count'] > 800:
            recommendations.append("Consider condensing your resume for better readability")
        
        if len(analysis['experience_indicators']) < 3:
            if experience_level in ['Fresher', 'Entry Level']:
                recommendations.append("Use more action verbs to describe your projects and achievements")
            else:
                recommendations.append("Use more action verbs to describe your professional achievements")
        
        return recommendations

# Initialize the analyzer
analyzer = ResumeAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract text from file
        text = extract_text_from_file(file_path)
        
        # Clean up - remove file after processing
        try:
            os.remove(file_path)
        except:
            pass
        
        if text.startswith("Error"):
            return jsonify({'error': text}), 400
        
        # Analyze resume
        analysis = analyzer.analyze_resume(text)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'filename': file.filename
        })
    
    return jsonify({'error': 'Invalid file type. Please upload PDF, DOC, DOCX, or TXT files.'}), 400

@app.route('/analyze-text', methods=['POST'])
def analyze_text():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text = data['text']
    if len(text.strip()) == 0:
        return jsonify({'error': 'Empty text provided'}), 400
    
    # Analyze resume
    analysis = analyzer.analyze_resume(text)
    
    return jsonify({
        'success': True,
        'analysis': analysis
    })

if __name__ == '__main__':
    app.run(debug=True)


# Create templates directory and HTML template
template_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Resume Screening Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .main-content {
            padding: 40px;
        }
        
        .upload-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            border: 2px dashed #dee2e6;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .upload-section:hover {
            border-color: #4facfe;
            background: #f0f8ff;
        }
        
        .file-input-wrapper {
            position: relative;
            display: inline-block;
            cursor: pointer;
            margin: 20px 0;
        }
        
        .file-input {
            display: none;
        }
        
        .file-input-button {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            border: none;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        
        .file-input-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4);
        }
        
        .text-input-section {
            margin-top: 30px;
        }
        
        .text-input {
            width: 100%;
            min-height: 200px;
            padding: 15px;
            border: 2px solid #dee2e6;
            border-radius: 10px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
        }
        
        .text-input:focus {
            outline: none;
            border-color: #4facfe;
        }
        
        .analyze-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 15px;
            transition: all 0.3s ease;
        }
        
        .analyze-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4facfe;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .results {
            display: none;
            margin-top: 30px;
        }
        
        .score-display {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .score-circle {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            margin: 0 auto 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            color: white;
        }
        
        .score-excellent { background: linear-gradient(135deg, #4CAF50, #45a049); }
        .score-good { background: linear-gradient(135deg, #2196F3, #1976D2); }
        .score-average { background: linear-gradient(135deg, #FF9800, #F57C00); }
        .score-poor { background: linear-gradient(135deg, #F44336, #D32F2F); }
        
        .analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .analysis-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #4facfe;
        }
        
        .analysis-card h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        
        .skill-tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin: 2px;
        }
        
        .recommendation-list {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            padding: 20px;
        }
        
        .recommendation-list h3 {
            color: #856404;
            margin-bottom: 15px;
        }
        
        .recommendation-item {
            background: white;
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #ffc107;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border: 1px solid #f5c6cb;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .main-content {
                padding: 20px;
            }
            
            .analysis-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Resume Screening Tool</h1>
            <p>Upload your resume and get instant AI-powered analysis and feedback</p>
        </div>
        
        <div class="main-content">
            <div class="upload-section">
                <h2>📄 Upload Resume</h2>
                <p>Supported formats: PDF, DOC, DOCX, TXT (Max 16MB)</p>
                
                <div class="file-input-wrapper">
                    <input type="file" id="fileInput" class="file-input" accept=".pdf,.doc,.docx,.txt">
                    <button class="file-input-button" onclick="document.getElementById('fileInput').click()">
                        Choose File
                    </button>
                </div>
                
                <div id="fileName" style="margin-top: 10px; color: #666;"></div>
            </div>
            
            <div class="text-input-section">
                <h3>Or paste your resume text here:</h3>
                <textarea id="resumeText" class="text-input" placeholder="Paste your resume content here..."></textarea>
                <button class="analyze-button" onclick="analyzeText()">Analyze Text</button>
            </div>
            
            <div class="loading" id="loading">
                <div class="loading-spinner"></div>
                <p>Analyzing your resume... Please wait.</p>
            </div>
            
            <div class="results" id="results">
                <div class="score-display">
                    <div class="score-circle" id="scoreCircle">
                        <span id="scoreValue">0</span>%
                    </div>
                    <h2 id="scoreLabel">Resume Score</h2>
                </div>
                
                <div class="analysis-grid" id="analysisGrid">
                    <!-- Analysis cards will be inserted here -->
                </div>
                
                <div class="recommendation-list" id="recommendations">
                    <h3>💡 Recommendations for Improvement</h3>
                    <div id="recommendationItems">
                        <!-- Recommendations will be inserted here -->
                    </div>
                </div>
            </div>
            
            <div class="error" id="error" style="display: none;"></div>
        </div>
    </div>

    <script>
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('fileName').textContent = `Selected: ${file.name}`;
                uploadFile(file);
            }
        });

        function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            showLoading();
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    displayResults(data.analysis);
                } else {
                    showError(data.error);
                }
            })
            .catch(error => {
                hideLoading();
                showError('An error occurred while uploading the file.');
                console.error('Error:', error);
            });
        }

        function analyzeText() {
            const text = document.getElementById('resumeText').value.trim();
            if (!text) {
                showError('Please enter some text to analyze.');
                return;
            }
            
            showLoading();
            
            fetch('/analyze-text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    displayResults(data.analysis);
                } else {
                    showError(data.error);
                }
            })
            .catch(error => {
                hideLoading();
                showError('An error occurred while analyzing the text.');
                console.error('Error:', error);
            });
        }

        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
        }

        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }

        function showError(message) {
            document.getElementById('error').textContent = message;
            document.getElementById('error').style.display = 'block';
            document.getElementById('results').style.display = 'none';
        }

        function displayResults(analysis) {
            document.getElementById('error').style.display = 'none';
            
            // Display score
            const scoreValue = document.getElementById('scoreValue');
            const scoreCircle = document.getElementById('scoreCircle');
            const scoreLabel = document.getElementById('scoreLabel');
            
            scoreValue.textContent = analysis.score;
            
            // Set score color based on value
            scoreCircle.className = 'score-circle';
            if (analysis.score >= 80) {
                scoreCircle.classList.add('score-excellent');
                scoreLabel.textContent = 'Excellent Resume!';
            } else if (analysis.score >= 60) {
                scoreCircle.classList.add('score-good');
                scoreLabel.textContent = 'Good Resume';
            } else if (analysis.score >= 40) {
                scoreCircle.classList.add('score-average');
                scoreLabel.textContent = 'Average Resume';
            } else {
                scoreCircle.classList.add('score-poor');
                scoreLabel.textContent = 'Needs Improvement';
            }
            
            // Display analysis cards
            const analysisGrid = document.getElementById('analysisGrid');
            analysisGrid.innerHTML = '';
            
            // Contact Information
            const contactCard = createAnalysisCard('📞 Contact Information', [
                `Email: ${analysis.contact_info.email || 'Not found'}`,
                `Phone: ${analysis.contact_info.phone || 'Not found'}`
            ]);
            analysisGrid.appendChild(contactCard);
            
            // Technical Skills
            const techCard = createAnalysisCard('💻 Technical Skills', 
                analysis.technical_skills.length > 0 ? analysis.technical_skills : ['No technical skills detected']
            );
            analysisGrid.appendChild(techCard);
            
            // Soft Skills
            const softCard = createAnalysisCard('🤝 Soft Skills', 
                analysis.soft_skills.length > 0 ? analysis.soft_skills : ['No soft skills detected']
            );
            analysisGrid.appendChild(softCard);
            
            // Experience Level
            const expCard = createAnalysisCard('📈 Experience Level', [
                `Level: ${analysis.experience_level[0]}`,
                `Years: ${analysis.experience_level[1]}`
            ]);
            analysisGrid.appendChild(expCard);
            
            // Resume Stats
            const statsCard = createAnalysisCard('📊 Resume Statistics', [
                `Word Count: ${analysis.word_count}`,
                `Character Count: ${analysis.character_count}`,
                `Education Keywords: ${analysis.education_keywords.length}`,
                `Experience Indicators: ${analysis.experience_indicators.length}`
            ]);
            analysisGrid.appendChild(statsCard);
            
            // Display recommendations
            const recommendationItems = document.getElementById('recommendationItems');
            recommendationItems.innerHTML = '';
            
            if (analysis.recommendations.length > 0) {
                analysis.recommendations.forEach(rec => {
                    const recItem = document.createElement('div');
                    recItem.className = 'recommendation-item';
                    recItem.textContent = rec;
                    recommendationItems.appendChild(recItem);
                });
            } else {
                const noRecItem = document.createElement('div');
                noRecItem.className = 'recommendation-item';
                noRecItem.textContent = 'Great job! No major improvements needed.';
                recommendationItems.appendChild(noRecItem);
            }
            
            document.getElementById('results').style.display = 'block';
        }

        function createAnalysisCard(title, items) {
            const card = document.createElement('div');
            card.className = 'analysis-card';
            
            const cardTitle = document.createElement('h3');
            cardTitle.textContent = title;
            card.appendChild(cardTitle);
            
            if (Array.isArray(items)) {
                items.forEach(item => {
                    if (title.includes('Skills') && items.length > 1 && item !== 'No technical skills detected' && item !== 'No soft skills detected') {
                        const skillTag = document.createElement('span');
                        skillTag.className = 'skill-tag';
                        skillTag.textContent = item;
                        card.appendChild(skillTag);
                    } else {
                        const itemDiv = document.createElement('div');
                        itemDiv.textContent = item;
                        itemDiv.style.marginBottom = '5px';
                        card.appendChild(itemDiv);
                    }
                });
            }
            
            return card;
        }
    </script>
</body>
</html>
'''

# Save the template
import os
if not os.path.exists('templates'):
    os.makedirs('templates')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(template_html)

print("Template file created successfully!")