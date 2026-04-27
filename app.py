import os
from dotenv import load_dotenv
load_dotenv()  # Load .env file for local development

import smtplib
import json
from email.message import EmailMessage
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Supabase credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Safety check
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL or SUPABASE_KEY not set! Please check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Admin credentials
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'portfolio2026')

# Email config
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASS = os.environ.get('GMAIL_PASS')

# ---------- Helper functions ----------
def send_email_notification(name, email, message):
    if not GMAIL_USER or not GMAIL_PASS:
        print("⚠️ Email not configured. Skipping email notification.")
        return
    try:
        msg = EmailMessage()
        msg.set_content(f"New message from {name} ({email}):\n\n{message}")
        msg['Subject'] = f"Portfolio Contact: {name}"
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print("✅ Email notification sent")
    except Exception as e:
        print(f"❌ Email error: {e}")

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ---------- Public API ----------
@app.route('/api/data')
def get_data():
    result = supabase.table('site_data').select('section, content').execute()
    data = {row['section']: row['content'] for row in result.data}
    return jsonify(data)

@app.route('/api/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    if not name or not email or not message:
        return jsonify({"error": "All fields required"}), 400
    supabase.table('contacts').insert({
        "name": name,
        "email": email,
        "message": message,
        "created_at": datetime.now().isoformat()
    }).execute()
    send_email_notification(name, email, message)
    return jsonify({"success": True})

# ---------- Visitor Counter API ----------
@app.route('/api/visitor', methods=['GET'])
def get_visitor_count():
    try:
        result = supabase.table('visitor_count').select('count').eq('id', 1).execute()
        if result.data:
            return jsonify({"count": result.data[0]['count']})
        return jsonify({"count": 0})
    except Exception as e:
        return jsonify({"count": 0, "error": str(e)}), 500

@app.route('/api/visitor/increment', methods=['POST'])
def increment_visitor():
    try:
        # Get current count
        result = supabase.table('visitor_count').select('count').eq('id', 1).execute()
        current = result.data[0]['count'] if result.data else 0
        new_count = current + 1
        supabase.table('visitor_count').update({
            'count': new_count,
            'updated_at': datetime.now().isoformat()
        }).eq('id', 1).execute()
        return jsonify({"count": new_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Admin Login ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# ---------- Admin Dashboard ----------
@app.route('/admin')
@admin_required
def admin_dashboard():
    result = supabase.table('site_data').select('*').execute()
    site_data = result.data
    contacts = supabase.table('contacts').select('*').order('created_at', desc=True).execute()
    return render_template('admin_panel.html', data=site_data, contacts=contacts.data)

# ---------- Reset Data Route (insert default data) ----------
@app.route('/admin/reset_data')
@admin_required
def reset_data():
    default_data = [
        ('home', {
            "title": "Furqan Raza",
            "tagline": "Aspiring Web Developer | Frontend Expert | Full-Stack",
            "description": "Building responsive, user-centric web apps with modern stacks & 3D vision. Experienced in softskills engineering & customer service."
        }),
        ('skills', [
            "HTML5/CSS3", "JavaScript (Core)", "React.js/Redux", "Context API",
            "Node.js", "RESTful APIs", "Supabase", "JWT/OAuth", "Git & GitHub",
            "Tailwind CSS", "Bootstrap", "Responsive Design", "Vercel/Netlify/Render",
            "Web Performance Optimization", "Cross-browser Compatibility", "Java (OOP)"
        ]),
        ('experience', [
            {"title": "Softskills Engineering", "company": "Professional Development | Freelance / Contract", "desc": "Delivered training and consultancy in communication, teamwork, leadership, and problem-solving for tech teams."},
            {"title": "Call Center Fronter (Medicare Campaign)", "company": "9 months · Healthcare Support", "desc": "Worked as a front-line agent for a Medicare campaign, handling inbound/outbound calls, resolving patient queries, managing claims assistance."}
        ]),
        ('education', [
            {"degree": "BS Software Engineering", "institute": "Virtual University (Ongoing)"},
            {"degree": "ICS (Statistics)", "institute": "Concept Colleges"},
            {"degree": "Matric in Computer Science", "institute": "Concept School"}
        ]),
        ('projects', [
            {"name": "Dynamic Portfolio", "desc": "Modern portfolio with smooth UI, optimized responsiveness.", "link": "https://osama-pctl.vercel.app/#home"},
            {"name": "Accomplishment Portfolio", "desc": "High-performance portfolio highlighting achievements, skills.", "link": "http://m-aqib-8cvul.vercel.app/accomplishments"}
        ]),
        ('about', {
            "who": "A highly motivated and detail-oriented aspiring Web Developer with a strong foundation in front-end and back-end development. Currently enhancing practical skills through hands-on internship experience. Proficient in Java, web development fundamentals, and essential development tools. Passionate about emerging technologies and creating innovative digital solutions.",
            "personal": {
                "dob": "07-12-2007",
                "nationality": "Pakistani",
                "languages": "English, Urdu",
                "interests": "Skill Learning, Technology, Teamwork, Social Networking"
            }
        })
    ]
    
    supabase.table('site_data').delete().neq('section', 'dummy').execute()
    for section, content in default_data:
        supabase.table('site_data').insert({
            "section": section,
            "content": content,
            "updated_at": datetime.now().isoformat()
        }).execute()
    
    return redirect(url_for('admin_dashboard'))

# ---------- CRUD routes for admin ----------
@app.route('/admin/update', methods=['POST'])
@admin_required
def admin_update():
    section = request.form.get('section')
    content = request.form.get('content')
    try:
        parsed = json.loads(content)
    except:
        parsed = content
    supabase.table('site_data').update({'content': parsed, 'updated_at': datetime.now().isoformat()}).eq('section', section).execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_experience', methods=['POST'])
@admin_required
def add_experience():
    title = request.form.get('title')
    company = request.form.get('company')
    desc = request.form.get('desc')
    result = supabase.table('site_data').select('content').eq('section', 'experience').execute()
    current = result.data[0]['content'] if result.data else []
    current.append({"title": title, "company": company, "desc": desc})
    supabase.table('site_data').update({'content': current}).eq('section', 'experience').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_experience/<int:index>')
@admin_required
def delete_experience(index):
    result = supabase.table('site_data').select('content').eq('section', 'experience').execute()
    current = result.data[0]['content']
    if 0 <= index < len(current):
        current.pop(index)
        supabase.table('site_data').update({'content': current}).eq('section', 'experience').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_education', methods=['POST'])
@admin_required
def add_education():
    degree = request.form.get('degree')
    institute = request.form.get('institute')
    result = supabase.table('site_data').select('content').eq('section', 'education').execute()
    current = result.data[0]['content'] if result.data else []
    current.append({"degree": degree, "institute": institute})
    supabase.table('site_data').update({'content': current}).eq('section', 'education').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_education/<int:index>')
@admin_required
def delete_education(index):
    result = supabase.table('site_data').select('content').eq('section', 'education').execute()
    current = result.data[0]['content']
    if 0 <= index < len(current):
        current.pop(index)
        supabase.table('site_data').update({'content': current}).eq('section', 'education').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_project', methods=['POST'])
@admin_required
def add_project():
    name = request.form.get('name')
    desc = request.form.get('desc')
    link = request.form.get('link')
    result = supabase.table('site_data').select('content').eq('section', 'projects').execute()
    current = result.data[0]['content'] if result.data else []
    current.append({"name": name, "desc": desc, "link": link})
    supabase.table('site_data').update({'content': current}).eq('section', 'projects').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_project/<int:index>')
@admin_required
def delete_project(index):
    result = supabase.table('site_data').select('content').eq('section', 'projects').execute()
    current = result.data[0]['content']
    if 0 <= index < len(current):
        current.pop(index)
        supabase.table('site_data').update({'content': current}).eq('section', 'projects').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_skill', methods=['POST'])
@admin_required
def add_skill():
    new_skill = request.form.get('skill')
    result = supabase.table('site_data').select('content').eq('section', 'skills').execute()
    current = result.data[0]['content'] if result.data else []
    if new_skill not in current:
        current.append(new_skill)
        supabase.table('site_data').update({'content': current}).eq('section', 'skills').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_skill/<int:index>')
@admin_required
def delete_skill(index):
    result = supabase.table('site_data').select('content').eq('section', 'skills').execute()
    current = result.data[0]['content']
    if 0 <= index < len(current):
        current.pop(index)
        supabase.table('site_data').update({'content': current}).eq('section', 'skills').execute()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_contact/<int:id>')
@admin_required
def delete_contact(id):
    supabase.table('contacts').delete().eq('id', id).execute()
    return redirect(url_for('admin_dashboard'))

# ---------- TEST DATABASE CONNECTION ----------
@app.route('/test_db')
def test_db():
    try:
        result = supabase.table('site_data').select('*').limit(1).execute()
        return f"✅ Connected to Supabase! Found {len(result.data)} rows in site_data table."
    except Exception as e:
        return f"❌ Error: {e}"

# ---------- Frontend ----------
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)