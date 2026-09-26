from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3, os, json, re
import cloudinary, cloudinary.uploader
from huggingface_hub import InferenceClient
from datetime import datetime
import requests as req
import io
from PyPDF2 import PdfReader
import docx

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bca_ai_compass_2026')

HF_TOKEN = os.environ.get('HF_TOKEN', 'YOUR_HF_TOKEN')
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', 'YOUR_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', 'YOUR_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', 'YOUR_API_SECRET')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ncsc2026')

cloudinary.config(cloud_name=CLOUDINARY_CLOUD_NAME, api_key=CLOUDINARY_API_KEY, api_secret=CLOUDINARY_API_SECRET)
hf_client = InferenceClient(token=HF_TOKEN)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database', 'compass.db'))
    conn.row_factory = sqlite3.Row
    return conn

def get_sdb():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database', 'seniors.db'))
    conn.row_factory = sqlite3.Row
    return conn

# FIX: Better Cloudinary upload with proper error handling
def upload_cloud(file_data, folder="bca_ai_compass"):
    try:
        if not file_data:
            return None
        result = cloudinary.uploader.upload(
            file_data,
            resource_type="auto",
            folder=folder
        )
        url = result.get("secure_url")
        print(f"✅ Cloudinary upload success: {url}")  # debug
        return url
    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")  # debug
        return None

def ai_chat(messages, max_tokens=1000):
    try:
        r = hf_client.chat_completion(
            messages=messages,
            model="Qwen/Qwen2.5-72B-Instruct",
            max_tokens=max_tokens,
            temperature=0.7
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def read_url(url, file_type):
    try:
        r = req.get(url, timeout=10)
        if file_type == "PDF":
            reader = PdfReader(io.BytesIO(r.content))
            return "".join([p.extract_text() or "" for p in reader.pages])[:2000]
        elif file_type == "Word":
            d = docx.Document(io.BytesIO(r.content))
            return "\n".join([p.text for p in d.paragraphs])[:2000]
    except:
        return ""
    return ""

def get_about():
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM about_page LIMIT 1").fetchone()
        conn.close()
        return dict(row) if row else {}
    except:
        conn.close()
        return {}

# ── HOME ──
@app.route('/')
def index():
    conn = get_db(); sconn = get_sdb()
    stats = {
        'resources': conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
        'papers': conn.execute("SELECT COUNT(*) FROM past_papers").fetchone()[0],
        'students': conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        'seniors': sconn.execute("SELECT COUNT(*) FROM seniors WHERE is_active=1 AND is_blocked=0").fetchone()[0],
    }
    conn.close(); sconn.close()
    return render_template('index.html', stats=stats)

# ── RESOURCES ──
@app.route('/resources')
def resources():
    conn = get_db()
    resources_list = conn.execute("SELECT * FROM resources ORDER BY subject, topic").fetchall()
    subjects = [r[0] for r in conn.execute("SELECT DISTINCT subject FROM resources").fetchall()]
    conn.close()
    return render_template('resources.html', resources=resources_list, subjects=subjects)

# ── EXAM ──
@app.route('/exam')
def exam():
    conn = get_db()
    papers = conn.execute("SELECT * FROM past_papers ORDER BY subject, year").fetchall()
    ps = [r[0] for r in conn.execute("SELECT DISTINCT subject FROM past_papers").fetchall()]
    rs = [r[0] for r in conn.execute("SELECT DISTINCT subject FROM resources").fetchall()]
    # FIX: Merge both lists and sort
    all_subjects = sorted(list(set(ps + rs)))
    conn.close()
    return render_template('exam.html', papers=papers, paper_subjects=ps, all_subjects=all_subjects)

@app.route('/api/generate-paper', methods=['POST'])
def generate_paper():
    data = request.json
    subject = data.get('subject')
    marks = data.get('marks', 50)
    conn = get_db()
    resources_list = conn.execute("SELECT topic, file_type, link FROM resources WHERE subject=?", (subject,)).fetchall()
    papers_list = conn.execute("SELECT year, paper_link FROM past_papers WHERE subject=?", (subject,)).fetchall()
    conn.close()
    res_text = "".join([f"\nTopic: {r['topic']}\n{read_url(r['link'], r['file_type'])[:300]}\n" for r in resources_list])
    past_text = "".join([f"\nYear: {p['year']}\n{read_url(p['paper_link'], 'PDF')[:300]}\n" for p in papers_list])
    prompt = f"""You are a university professor. Create a real university exam paper.
Subject: {subject}
Total Marks: {marks}
Resource Content: {res_text or 'Use general knowledge about ' + subject}
Past Paper Format: {past_text or 'Standard university format'}

Instructions:
- Total marks must be exactly {marks}
- Use sections: Short Questions (2 marks each), Medium Questions (5 marks each), Long Questions (10 marks each)
- Questions must be based on the subject content provided
- Format exactly like a real university exam paper with proper sections and question numbers"""
    paper = ai_chat([{"role": "user", "content": prompt}], max_tokens=2000)
    return jsonify({"paper": paper})

# ── CAREER ──
@app.route('/career')
def career():
    steps = [
        (1, "💻 Coding Languages", "lang", [("🐍","Python","python"),("🌐","JavaScript","javascript"),("☕","Java","java"),("⚡","C++","cpp"),("📊","R","r"),("💙","Dart","dart"),("🔷","Swift","swift"),("🦀","Kotlin","kotlin")], True),
        (2, "🎨 Frontend Technologies", "frontend", [("🌐","HTML/CSS","html"),("⚛️","React","react"),("💚","Vue.js","vue"),("🔴","Angular","angular"),("💙","Flutter","flutter"),("📱","React Native","reactnative"),("🎨","Tailwind CSS","tailwind"),("🚫","Not Applicable","none")], True),
        (3, "⚙️ Backend Technologies", "backend", [("🟢","Node.js","nodejs"),("🐍","Django","django"),("🐍","Flask","flask"),("⚡","FastAPI","fastapi"),("🍃","Spring Boot","spring"),("🔥","Firebase","firebase"),("☁️","AWS Lambda","aws"),("🚫","Not Applicable","none_b")], True),
        (4, "🗄️ Databases / Frameworks / AI Tools", "framework", [("🐬","MySQL","mysql"),("🍃","MongoDB","mongodb"),("🐘","PostgreSQL","postgresql"),("📊","Power BI","powerbi"),("📈","Tableau","tableau"),("📗","Excel","excel"),("🔥","TensorFlow","tensorflow"),("🔴","PyTorch","pytorch"),("🤗","HuggingFace","huggingface"),("🦜","LangChain","langchain"),("⚡","Scikit-learn","sklearn"),("☁️","AWS/Azure/GCP","cloud_tools")], True),
        (5, "🚀 What Do You Want to Build?", "build", [("🌐","Web Development","web"),("📱","Android / iOS App","mobile"),("📊","Data Analysis","data"),("🤖","AI / ML Model","ai"),("🦜","LLM / ChatBot","llm"),("🔬","Research","research"),("📈","Business Analytics","business"),("🛡️","Cybersecurity","security"),("☁️","Cloud & DevOps","cloud")], False),
    ]
    return render_template('career.html', steps=steps)

@app.route('/api/predict-career', methods=['POST'])
def predict_career():
    try:
        data = request.json
        sel = data.get('selections', {})
        lang = sel.get('lang', []); frontend = sel.get('frontend', [])
        backend = sel.get('backend', []); framework = sel.get('framework', [])
        build = sel.get('build')
        python=ml=stats=sql=web=mobile=security=cloud=1
        if 'python' in lang: python=5
        if 'r' in lang: stats=4
        if any(l in lang for l in ['javascript','dart']): web=4
        if any(l in lang for l in ['java','kotlin']): mobile=4
        if 'swift' in lang: mobile=5
        if 'none' not in frontend and frontend: web=min(5,web+2)
        if any(b in backend for b in ['django','flask','fastapi']): python=min(5,python+1)
        if 'nodejs' in backend: web=min(5,web+1)
        if 'aws' in backend: cloud=min(5,cloud+2)
        if any(f in framework for f in ['mysql','mongodb','postgresql']): sql=5
        if any(f in framework for f in ['powerbi','tableau','excel']): stats=4
        if any(f in framework for f in ['tensorflow','pytorch','sklearn']): ml=5; python=min(5,python+1)
        if any(f in framework for f in ['huggingface','langchain']): ml=5; python=min(5,python+1)
        if 'cloud_tools' in framework: cloud=5
        if build=='ai': ml=5; python=min(5,python+1)
        if build=='llm': ml=5; python=min(5,python+1)
        if build=='data': stats=5; sql=min(5,sql+1)
        if build=='web': web=5
        if build=='mobile': mobile=5
        if build=='security': security=5
        if build=='cloud': cloud=5
        if build=='research': ml=4; stats=4
        try:
            api_r = req.post('http://127.0.0.1:5001/predict', json={
                "python":python,"ml":ml,"stats":stats,"sql":sql,
                "web":web,"mobile":mobile,"security":security,"cloud":cloud,
                "selections":{"fav_lang":lang[0] if lang else '','build_interest':build or '','framework_db':framework[0] if framework else ''}
            }, timeout=5)
            result = api_r.json()
        except:
            result = {"career":"Data Analyst","alt_career":"ML Engineer",
                     "description":"Career API not running. Please start flask_api/app.py",
                     "alt_description":"Career API not running."}
        career_name = result.get('career','Data Analyst')
        alt_career = result.get('alt_career','ML Engineer')
        all_sel = lang+frontend+backend+framework
        csu = {
            'Data Analyst':{'useful':['python','sql','excel','powerbi','tableau','r'],'needed':['Pandas','NumPy','Tableau','Power BI','Advanced Excel','SQL Optimization']},
            'ML Engineer':{'useful':['python','tensorflow','pytorch','sklearn'],'needed':['MLflow','Docker','Kubernetes','Feature Engineering','Model Deployment']},
            'Data Scientist':{'useful':['python','r','tensorflow','pytorch','sklearn','sql'],'needed':['Advanced Statistics','Experiment Design','Seaborn','Storytelling with Data']},
            'Web Developer':{'useful':['javascript','html','react','vue','angular','tailwind','nodejs'],'needed':['REST APIs','TypeScript','Git','Responsive Design','Testing']},
            'Full Stack Developer':{'useful':['javascript','react','nodejs','mongodb','mysql','html'],'needed':['Docker','AWS','CI/CD','System Design','Security Basics']},
            'Android Developer':{'useful':['java','kotlin','firebase','mysql'],'needed':['Android Studio','Jetpack Compose','REST APIs','Material Design']},
            'iOS Developer':{'useful':['swift','firebase'],'needed':['SwiftUI','Xcode','Core Data','ARKit','App Store Publishing']},
            'AI Developer':{'useful':['python','tensorflow','pytorch','sklearn'],'needed':['LangChain','OpenAI API','FastAPI','Vector Databases','Prompt Engineering']},
            'LLM Engineer':{'useful':['python','huggingface','langchain'],'needed':['RAG Systems','Fine-tuning','Vector DB','Embeddings','RLHF']},
            'Prompt Engineer':{'useful':['python','huggingface','langchain'],'needed':['Prompt Design','LLM APIs','NLP Basics','Chain-of-Thought']},
            'MLOps Engineer':{'useful':['python','aws','cloud_tools','tensorflow'],'needed':['MLflow','Kubernetes','Terraform','CI/CD Pipelines','Monitoring']},
            'Cybersecurity Analyst':{'useful':['python','sql','aws','cloud_tools'],'needed':['Network Security','Ethical Hacking','SIEM Tools','Cryptography']},
            'Cloud Engineer':{'useful':['python','aws','cloud_tools'],'needed':['AWS/Azure/GCP Certifications','Kubernetes','Terraform','Linux']},
            'Database Administrator':{'useful':['sql','mysql','postgresql','mongodb'],'needed':['Query Optimization','Backup & Recovery','Database Security','Performance Tuning']},
            'Business Analyst':{'useful':['excel','powerbi','tableau','sql','r'],'needed':['Requirements Gathering','Process Modeling','Stakeholder Management','Agile']},
        }
        cc = {'ML Engineer':'linear-gradient(135deg,#1F4E79,#2E75B6)','Data Scientist':'linear-gradient(135deg,#1a6b3a,#27ae60)','Data Analyst':'linear-gradient(135deg,#7B2D8B,#a855c2)','Web Developer':'linear-gradient(135deg,#b84b00,#e67e22)','Full Stack Developer':'linear-gradient(135deg,#0d4b6b,#1a7fa8)','Android Developer':'linear-gradient(135deg,#2d6b1a,#3daa2a)','iOS Developer':'linear-gradient(135deg,#4a4a4a,#888888)','AI Developer':'linear-gradient(135deg,#0d6b6b,#17a589)','LLM Engineer':'linear-gradient(135deg,#6b1a6b,#a832a8)','Prompt Engineer':'linear-gradient(135deg,#6b4a00,#c4850a)','MLOps Engineer':'linear-gradient(135deg,#003366,#0066cc)','Cybersecurity Analyst':'linear-gradient(135deg,#6b0000,#cc0000)','Cloud Engineer':'linear-gradient(135deg,#004466,#0088cc)','Database Administrator':'linear-gradient(135deg,#334400,#668800)','Business Analyst':'linear-gradient(135deg,#663300,#cc6600)'}
        ce = {'ML Engineer':'🤖','Data Scientist':'🔬','Data Analyst':'📊','Web Developer':'🌐','Full Stack Developer':'🔧','Android Developer':'📱','iOS Developer':'🍎','AI Developer':'💡','LLM Engineer':'🦜','Prompt Engineer':'✍️','MLOps Engineer':'⚙️','Cybersecurity Analyst':'🛡️','Cloud Engineer':'☁️','Database Administrator':'🗄️','Business Analyst':'📈'}
        ci = csu.get(career_name,{'useful':[],'needed':[]})
        ai_info = csu.get(alt_career,{'useful':[],'needed':[]})
        conn = get_db()
        rm = conn.execute("SELECT roadmap_link FROM roadmaps WHERE career_name=?", (career_name,)).fetchone()
        arm = conn.execute("SELECT roadmap_link FROM roadmaps WHERE career_name=?", (alt_career,)).fetchone()
        conn.close()
        return jsonify({
            "career":career_name,"alt_career":alt_career,
            "description":result.get('description',''),"alt_description":result.get('alt_description',''),
            "useful_skills":[s for s in all_sel if s in ci['useful']],
            "needed_skills":ci['needed'],
            "alt_useful_skills":[s for s in all_sel if s in ai_info['useful']],
            "alt_needed_skills":ai_info['needed'],
            "roadmap":rm['roadmap_link'] if rm else None,
            "alt_roadmap":arm['roadmap_link'] if arm else None,
            "color":cc.get(career_name,'linear-gradient(135deg,#1F4E79,#2E75B6)'),
            "alt_color":cc.get(alt_career,'linear-gradient(135deg,#1a6b3a,#27ae60)'),
            "emoji":ce.get(career_name,'🎯'),"alt_emoji":ce.get(alt_career,'🎯')
        })
    except Exception as e:
        return jsonify({"error":str(e)}), 400

# ── CHATBOT ──
@app.route('/chatbot')
def chatbot():
    convs=[]; msgs=[]; cc=session.get('current_conv')
    if session.get('student_id'):
        conn=get_db()
        convs=conn.execute("SELECT DISTINCT conversation_name as name, is_pinned FROM chat_history WHERE student_id=? ORDER BY is_pinned DESC, timestamp DESC",(session['student_id'],)).fetchall()
        if cc:
            msgs=conn.execute("SELECT message, role FROM chat_history WHERE student_id=? AND conversation_name=? ORDER BY timestamp ASC",(session['student_id'],cc)).fetchall()
        conn.close()
    return render_template('chatbot.html', conversations=convs, messages=msgs, current_conv=cc)

@app.route('/chatbot/login', methods=['POST'])
def chatbot_login():
    conn=get_db()
    s=conn.execute("SELECT * FROM students WHERE email=? AND password=?",(request.form.get('email'),request.form.get('password'))).fetchone()
    conn.close()
    if s: session['student_id']=s['id']; session['student_name']=s['name']; flash('Login successful!','success')
    else: flash('Invalid email or password!','danger')
    return redirect(url_for('chatbot'))

@app.route('/chatbot/register', methods=['POST'])
def chatbot_register():
    email=request.form.get('email'); password=request.form.get('password'); name=request.form.get('name')
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email): flash('Invalid email!','danger'); return redirect(url_for('chatbot'))
    conn=get_db()
    if conn.execute("SELECT id FROM students WHERE email=?",(email,)).fetchone(): flash('Email already registered!','danger'); conn.close(); return redirect(url_for('chatbot'))
    conn.execute("INSERT INTO students (name,email,password,course_year) VALUES (?,?,?,?)",(name,email,password,request.form.get('course_year','TY'))); conn.commit(); conn.close()
    flash('Account created! Please login.','success'); return redirect(url_for('chatbot'))

@app.route('/chatbot/logout')
def chatbot_logout():
    session.pop('student_id',None); session.pop('student_name',None); session.pop('current_conv',None)
    return redirect(url_for('chatbot'))

@app.route('/chatbot/new')
def chatbot_new():
    if not session.get('student_id'): return redirect(url_for('chatbot'))
    session['current_conv']=f"Chat {datetime.now().strftime('%d %b %H:%M')}"
    return redirect(url_for('chatbot'))

@app.route('/chatbot/load/<conv_name>')
def chatbot_load(conv_name): session['current_conv']=conv_name; return redirect(url_for('chatbot'))

@app.route('/chatbot/pin/<conv_name>')
def chatbot_pin(conv_name):
    if not session.get('student_id'): return redirect(url_for('chatbot'))
    conn=get_db()
    cur=conn.execute("SELECT is_pinned FROM chat_history WHERE student_id=? AND conversation_name=? LIMIT 1",(session['student_id'],conv_name)).fetchone()
    conn.execute("UPDATE chat_history SET is_pinned=? WHERE student_id=? AND conversation_name=?",(0 if(cur and cur['is_pinned']) else 1,session['student_id'],conv_name))
    conn.commit(); conn.close()
    return redirect(url_for('chatbot'))

@app.route('/chatbot/rename/<conv_name>', methods=['POST'])
def chatbot_rename(conv_name):
    if not session.get('student_id'): return redirect(url_for('chatbot'))
    nn=request.form.get('new_name','').strip()
    if nn:
        conn=get_db()
        conn.execute("UPDATE chat_history SET conversation_name=? WHERE student_id=? AND conversation_name=?",(nn,session['student_id'],conv_name))
        conn.commit(); conn.close()
        if session.get('current_conv')==conv_name: session['current_conv']=nn
    return redirect(url_for('chatbot'))

@app.route('/chatbot/delete/<conv_name>')
def chatbot_delete(conv_name):
    if not session.get('student_id'): return redirect(url_for('chatbot'))
    conn=get_db()
    conn.execute("DELETE FROM chat_history WHERE student_id=? AND conversation_name=?",(session['student_id'],conv_name))
    conn.commit(); conn.close()
    if session.get('current_conv')==conv_name: session.pop('current_conv',None)
    return redirect(url_for('chatbot'))

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data=request.json; user_msg=data.get('message',''); cc=data.get('conv_name','')
    conn=get_db()
    res=conn.execute("SELECT topic, link, file_type FROM resources").fetchall()
    res_text="".join([f"\nTopic: {r['topic']}\n{read_url(r['link'],r['file_type'])[:300]}\n" for r in res])
    sys_prompt=f"""You are an AI Study Assistant for BCA-AI students at Narmad College.
Understand English and Hinglish. Reply in same language as student.
Be friendly like a helpful senior student.
Resources: {res_text or 'No resources yet.'}
If question is NOT related to resources, respond with exactly: OUT_OF_DATA"""
    history=[]
    if session.get('student_id') and cc:
        msgs=conn.execute("SELECT message, role FROM chat_history WHERE student_id=? AND conversation_name=? ORDER BY timestamp ASC LIMIT 10",(session['student_id'],cc)).fetchall()
        history=[{"role":m['role'],"content":m['message']} for m in msgs]
    messages=[{"role":"system","content":sys_prompt}]+history+[{"role":"user","content":user_msg}]
    reply=ai_chat(messages)
    ood="OUT_OF_DATA" in reply
    if ood: reply="I don't have information about this topic yet. Please upload related study material!"
    if session.get('student_id') and cc:
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO chat_history (student_id,conversation_name,message,role,timestamp) VALUES (?,?,?,?,?)",(session['student_id'],cc,user_msg,'user',ts))
        conn.execute("INSERT INTO chat_history (student_id,conversation_name,message,role,timestamp) VALUES (?,?,?,?,?)",(session['student_id'],cc,reply,'assistant',ts))
        conn.commit()
    conn.close()
    return jsonify({"reply":reply,"out_of_data":ood})

@app.route('/api/upload-resource', methods=['POST'])
def upload_resource():
    try:
        file=request.files.get('file'); subject=request.form.get('subject'); topic=request.form.get('topic')
        if not file or not subject or not topic: return jsonify({"success":False,"error":"Missing fields"})
        file_data = file.read()
        url=upload_cloud(file_data)
        if not url: return jsonify({"success":False,"error":"Upload failed"})
        ext=file.filename.split('.')[-1].lower()
        ft="PDF" if ext=='pdf' else "Word" if ext=='docx' else "Image"
        conn=get_db()
        conn.execute("INSERT INTO resources (subject,topic,file_type,link) VALUES (?,?,?,?)",(subject,topic,ft,url))
        conn.commit(); conn.close()
        return jsonify({"success":True})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)})

# ── SENIORS ──
@app.route('/seniors')
def seniors():
    sconn=get_sdb()
    seniors_list=sconn.execute("SELECT * FROM seniors WHERE is_active=1 AND is_blocked=0 ORDER BY id DESC").fetchall()
    posts=sconn.execute("""SELECT sp.*, s.name as senior_name, s.profile_photo_link,
        s.company, s.batch_year FROM senior_posts sp
        JOIN seniors s ON sp.senior_id=s.id
        WHERE s.is_active=1 AND s.is_blocked=0 ORDER BY sp.date DESC""").fetchall()
    batches=[r[0] for r in sconn.execute("SELECT DISTINCT batch_year FROM seniors WHERE is_active=1 AND batch_year IS NOT NULL").fetchall()]
    stats={
        'total_seniors':sconn.execute("SELECT COUNT(*) FROM seniors WHERE is_active=1 AND is_blocked=0").fetchone()[0],
        'total_companies':sconn.execute("SELECT COUNT(DISTINCT company) FROM seniors WHERE is_active=1 AND company IS NOT NULL AND company!=''").fetchone()[0],
        'total_batches':sconn.execute("SELECT COUNT(DISTINCT batch_year) FROM seniors WHERE is_active=1").fetchone()[0],
        'total_posts':sconn.execute("SELECT COUNT(*) FROM senior_posts").fetchone()[0]
    }
    senior=None; my_posts=[]
    if session.get('senior_id'):
        senior=sconn.execute("SELECT * FROM seniors WHERE id=?",(session['senior_id'],)).fetchone()
        my_posts=sconn.execute("SELECT * FROM senior_posts WHERE senior_id=? ORDER BY date DESC",(session['senior_id'],)).fetchall()
    sconn.close()
    return render_template('seniors.html', seniors=seniors_list, posts=posts, batches=batches, stats=stats, senior=senior, my_posts=my_posts)

@app.route('/seniors/login', methods=['POST'])
def seniors_login():
    sconn=get_sdb()
    s=sconn.execute("SELECT * FROM seniors WHERE username=? AND password=? AND is_active=1 AND is_blocked=0",(request.form.get('username'),request.form.get('password'))).fetchone()
    sconn.close()
    if s: session['senior_id']=s['id']; session['senior_name']=s['name']; flash('Login successful!','success')
    else: flash('Invalid credentials or account blocked!','danger')
    return redirect(url_for('seniors'))

@app.route('/seniors/logout')
def seniors_logout():
    session.pop('senior_id',None); session.pop('senior_name',None)
    return redirect(url_for('seniors'))

# FIX: Read file before any operation
@app.route('/seniors/update-profile', methods=['POST'])
def update_senior_profile():
    if not session.get('senior_id'): return redirect(url_for('seniors'))
    
    photo_url = None
    # FIX: Properly read file data
    if 'photo' in request.files:
        photo_file = request.files['photo']
        if photo_file and photo_file.filename:
            file_data = photo_file.read()
            if file_data:
                photo_url = upload_cloud(file_data, "bca_ai_compass/seniors")
    
    achievements = ",".join(request.form.getlist('achievements'))
    sconn = get_sdb()
    
    if photo_url:
        sconn.execute("""UPDATE seniors SET company=?,role=?,bio=?,linkedin=?,github=?,
            instagram=?,contact=?,profile_photo_link=?,achievements=? WHERE id=?""",
            (request.form.get('company'), request.form.get('role'), request.form.get('bio'),
             request.form.get('linkedin'), request.form.get('github'),
             request.form.get('instagram'), request.form.get('contact'),
             photo_url, achievements, session['senior_id']))
    else:
        sconn.execute("""UPDATE seniors SET company=?,role=?,bio=?,linkedin=?,github=?,
            instagram=?,contact=?,achievements=? WHERE id=?""",
            (request.form.get('company'), request.form.get('role'), request.form.get('bio'),
             request.form.get('linkedin'), request.form.get('github'),
             request.form.get('instagram'), request.form.get('contact'),
             achievements, session['senior_id']))
    
    sconn.commit(); sconn.close()
    flash('Profile updated!', 'success')
    return redirect(url_for('seniors'))

@app.route('/seniors/add-post', methods=['POST'])
def add_senior_post():
    if not session.get('senior_id'): return redirect(url_for('seniors'))
    
    img = None
    if 'post_image' in request.files:
        img_file = request.files['post_image']
        if img_file and img_file.filename:
            file_data = img_file.read()
            if file_data:
                img = upload_cloud(file_data, "bca_ai_compass/posts")
    
    sconn = get_sdb()
    sconn.execute("INSERT INTO senior_posts (senior_id,post_image_link,post_caption,project_link,date) VALUES (?,?,?,?,?)",
        (session['senior_id'], img, request.form.get('caption'),
         request.form.get('project_link'), str(datetime.now().date())))
    sconn.commit(); sconn.close()
    flash('Post shared!', 'success')
    return redirect(url_for('seniors'))

@app.route('/seniors/delete-post/<int:pid>')
def delete_senior_post(pid):
    if not session.get('senior_id'): return redirect(url_for('seniors'))
    sconn=get_sdb()
    sconn.execute("DELETE FROM senior_posts WHERE id=? AND senior_id=?",(pid,session['senior_id']))
    sconn.commit(); sconn.close()
    flash('Post deleted!','success')
    return redirect(url_for('seniors'))

# ── SKILLCHECK ──
@app.route('/skillcheck')
def skillcheck():
    if not session.get('student_id'):
        return render_template('skillcheck.html',
            resource_subjects=[], general_subjects=[], 
            history=[], show_register=request.args.get('register')=='1')
    
    conn = get_db()
    # FIX: resource_subjects only from resources table
    resource_subjects = [r[0] for r in conn.execute("SELECT DISTINCT subject FROM resources").fetchall()]
    
    hr = conn.execute("""SELECT subject, score, total, level, weak_topics, timestamp
        FROM skill_attempts WHERE student_id=? ORDER BY id DESC""",
        (session['student_id'],)).fetchall()
    conn.close()
    
    history = [{'subject':h['subject'],'score':h['score'],'total':h['total'],
                'level':h['level'],
                'weak_topics':json.loads(h['weak_topics']) if h['weak_topics'] else [],
                'timestamp':h['timestamp']} for h in hr]
    
    # FIX: general_subjects is always fixed list, completely separate
    general_subjects = [
        "Python Programming", "Machine Learning", "Deep Learning",
        "SQL & Databases", "Web Development", "Data Structures & Algorithms",
        "Statistics & Probability", "Artificial Intelligence", "Computer Networks",
        "Operating Systems", "Software Engineering", "Cybersecurity Basics",
        "Cloud Computing", "Data Analysis", "Natural Language Processing"
    ]
    
    return render_template('skillcheck.html',
        resource_subjects=resource_subjects,
        general_subjects=general_subjects,
        history=history, show_register=False)

@app.route('/skillcheck/login', methods=['POST'])
def skillcheck_login():
    conn=get_db()
    s=conn.execute("SELECT * FROM students WHERE email=? AND password=?",(request.form.get('email'),request.form.get('password'))).fetchone()
    conn.close()
    if s: session['student_id']=s['id']; session['student_name']=s['name']; flash('Login successful!','success')
    else: flash('Invalid email or password!','danger')
    return redirect(url_for('skillcheck'))

@app.route('/skillcheck/register', methods=['POST'])
def skillcheck_register():
    email=request.form.get('email'); password=request.form.get('password'); name=request.form.get('name')
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email): flash('Invalid email!','danger'); return redirect(url_for('skillcheck'))
    conn=get_db()
    if conn.execute("SELECT id FROM students WHERE email=?",(email,)).fetchone(): flash('Email already registered!','danger'); conn.close(); return redirect(url_for('skillcheck'))
    conn.execute("INSERT INTO students (name,email,password,course_year) VALUES (?,?,?,?)",(name,email,password,request.form.get('course_year','TY')))
    conn.commit(); conn.close()
    flash('Account created!','success')
    return redirect(url_for('skillcheck'))

@app.route('/skillcheck/logout')
def skillcheck_logout():
    session.pop('student_id',None); session.pop('student_name',None)
    return redirect(url_for('skillcheck'))

@app.route('/api/generate-mcq', methods=['POST'])
def generate_mcq():
    data=request.json; subject=data.get('subject'); count=data.get('count',10); mtype=data.get('type','general')
    topics=""
    if mtype=='resource':
        conn=get_db()
        tl=[r[0] for r in conn.execute("SELECT topic FROM resources WHERE subject=?",(subject,)).fetchall()]
        conn.close()
        if tl: topics=f"Focus on these specific topics: {', '.join(tl)}"
    prompt=f"""Generate exactly {count} multiple choice questions about {subject}.
{topics}
Return ONLY a valid JSON array with no extra text:
[{{"question":"Question text?","options":["A) Option 1","B) Option 2","C) Option 3","D) Option 4"],"correct":"A","topic":"topic name"}}]
Rules:
- Exactly 4 options labeled A) B) C) D)
- correct field: only A, B, C, or D
- Mix easy, medium, hard questions
- Questions relevant to BCA Computer Science students"""
    response=ai_chat([{"role":"user","content":prompt}],max_tokens=3000)
    try:
        match=re.search(r'\[.*\]',response,re.DOTALL)
        if match:
            questions = json.loads(match.group())
            return jsonify({"questions":questions})
    except Exception as e:
        print(f"MCQ parse error: {e}")
    return jsonify({"questions":[],"error":"Failed to parse questions"})

@app.route('/api/save-attempt', methods=['POST'])
def save_attempt():
    if not session.get('student_id'): return jsonify({"success":False})
    data=request.json; conn=get_db()
    conn.execute("INSERT INTO skill_attempts (student_id,subject,score,total,level,weak_topics,timestamp) VALUES (?,?,?,?,?,?,?)",
        (session['student_id'],data['subject'],data['score'],data['total'],
         data['level'],json.dumps(data['weak_topics']),
         datetime.now().strftime("%d %b %Y %I:%M %p")))
    conn.commit(); conn.close()
    return jsonify({"success":True})

# ── ABOUT ──
@app.route('/about')
def about():
    project_details=[
        ("Project Name","BCA-AI Compass"),
        ("Subject","AI-503: Applied AI"),
        ("University","Veer Narmad South Gujarat University"),
        ("College","Narmad College of Science and Commerce"),
        ("Academic Year","2026-2027"),
        ("Semester","Semester 5 (T.Y.B.C.A.)")
    ]
    return render_template('about.html', about=get_about(), project_details=project_details)

# ── ADMIN ──
@app.route('/admin')
def admin():
    if not session.get('admin'):
        return render_template('admin.html', stats={}, resources=[], seniors=[], papers=[], roadmaps=[], students=[], about={})
    conn=get_db(); sconn=get_sdb()
    stats={
        'resources':conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
        'papers':conn.execute("SELECT COUNT(*) FROM past_papers").fetchone()[0],
        'students':conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        'seniors':sconn.execute("SELECT COUNT(*) FROM seniors").fetchone()[0]
    }
    resources=conn.execute("SELECT * FROM resources ORDER BY subject, topic").fetchall()
    papers=conn.execute("SELECT * FROM past_papers ORDER BY subject, year").fetchall()
    roadmaps=conn.execute("SELECT * FROM roadmaps ORDER BY career_name").fetchall()
    students=conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    seniors=sconn.execute("SELECT * FROM seniors ORDER BY id DESC").fetchall()
    conn.close(); sconn.close()
    return render_template('admin.html', stats=stats, resources=resources, papers=papers,
                           roadmaps=roadmaps, students=students, seniors=seniors, about=get_about())

@app.route('/admin/login', methods=['POST'])
def admin_login():
    if request.form.get('password')==ADMIN_PASSWORD:
        session['admin']=True; flash('Admin login successful!','success')
    else:
        flash('Invalid password!','danger')
    return redirect(url_for('admin'))

@app.route('/admin/logout')
def admin_logout(): session.pop('admin',None); return redirect(url_for('index'))

@app.route('/admin/add-resource', methods=['POST'])
def admin_add_resource():
    if not session.get('admin'): return redirect(url_for('admin'))
    conn=get_db()
    conn.execute("INSERT INTO resources (subject,topic,file_type,link) VALUES (?,?,?,?)",
        (request.form['subject'],request.form['topic'],request.form['file_type'],request.form['link']))
    conn.commit(); conn.close()
    flash('Resource added!','success')
    return redirect(url_for('admin'))

@app.route('/admin/delete-resource/<int:rid>')
def admin_delete_resource(rid):
    if not session.get('admin'): return redirect(url_for('admin'))
    conn=get_db(); conn.execute("DELETE FROM resources WHERE id=?",(rid,)); conn.commit(); conn.close()
    flash('Resource deleted!','success'); return redirect(url_for('admin'))

@app.route('/admin/add-paper', methods=['POST'])
def admin_add_paper():
    if not session.get('admin'): return redirect(url_for('admin'))
    conn=get_db()
    conn.execute("INSERT INTO past_papers (subject,year,paper_link) VALUES (?,?,?)",
        (request.form['subject'],request.form['year'],request.form['paper_link']))
    conn.commit(); conn.close()
    flash('Paper added!','success'); return redirect(url_for('admin'))

@app.route('/admin/delete-paper/<int:pid>')
def admin_delete_paper(pid):
    if not session.get('admin'): return redirect(url_for('admin'))
    conn=get_db(); conn.execute("DELETE FROM past_papers WHERE id=?",(pid,)); conn.commit(); conn.close()
    flash('Paper deleted!','success'); return redirect(url_for('admin'))

@app.route('/admin/add-roadmap', methods=['POST'])
def admin_add_roadmap():
    if not session.get('admin'): return redirect(url_for('admin'))
    conn=get_db()
    conn.execute("INSERT INTO roadmaps (career_name,roadmap_link) VALUES (?,?)",
        (request.form['career_name'],request.form['roadmap_link']))
    conn.commit(); conn.close()
    flash('Roadmap added!','success'); return redirect(url_for('admin'))

@app.route('/admin/delete-roadmap/<int:rid>')
def admin_delete_roadmap(rid):
    if not session.get('admin'): return redirect(url_for('admin'))
    conn=get_db(); conn.execute("DELETE FROM roadmaps WHERE id=?",(rid,)); conn.commit(); conn.close()
    flash('Roadmap deleted!','success'); return redirect(url_for('admin'))

@app.route('/admin/add-senior', methods=['POST'])
def admin_add_senior():
    if not session.get('admin'): return redirect(url_for('admin'))
    sconn=get_sdb()
    sconn.execute("INSERT INTO seniors (username,password,name,batch_year) VALUES (?,?,?,?)",
        (request.form['username'],request.form['password'],
         request.form['name'],request.form.get('batch_year','')))
    sconn.commit(); sconn.close()
    flash('Senior added!','success'); return redirect(url_for('admin'))

@app.route('/admin/delete-senior/<int:sid>')
def admin_delete_senior(sid):
    if not session.get('admin'): return redirect(url_for('admin'))
    sconn=get_sdb(); sconn.execute("DELETE FROM seniors WHERE id=?",(sid,)); sconn.commit(); sconn.close()
    flash('Senior deleted!','success'); return redirect(url_for('admin'))

@app.route('/admin/toggle-senior/<int:sid>')
def admin_toggle_senior(sid):
    if not session.get('admin'): return redirect(url_for('admin'))
    sconn=get_sdb()
    cur=sconn.execute("SELECT is_blocked FROM seniors WHERE id=?",(sid,)).fetchone()
    sconn.execute("UPDATE seniors SET is_blocked=? WHERE id=?",(0 if cur['is_blocked'] else 1,sid))
    sconn.commit(); sconn.close()
    flash('Senior status updated!','success'); return redirect(url_for('admin'))

# FIX: About page update with proper file handling
@app.route('/admin/update-about', methods=['POST'])
def admin_update_about():
    if not session.get('admin'): return redirect(url_for('admin'))
    
    photo_url = None
    if 'dev_photo' in request.files:
        photo_file = request.files['dev_photo']
        if photo_file and photo_file.filename:
            file_data = photo_file.read()
            if file_data:
                photo_url = upload_cloud(file_data, "bca_ai_compass/about")
    
    conn = get_db()
    # Create table if not exists
    conn.execute("""CREATE TABLE IF NOT EXISTS about_page (
        id INTEGER PRIMARY KEY, dev_name TEXT, roll_no TEXT,
        dev_email TEXT, dev_contact TEXT, dev_photo TEXT,
        linkedin TEXT, github TEXT, instagram TEXT,
        college_name TEXT, college_address TEXT,
        dept_email TEXT, college_contact TEXT)""")
    
    existing = conn.execute("SELECT id FROM about_page LIMIT 1").fetchone()
    
    vals = (
        request.form.get('dev_name'), request.form.get('roll_no'),
        request.form.get('dev_email'), request.form.get('dev_contact'),
        request.form.get('linkedin'), request.form.get('github'),
        request.form.get('instagram'), request.form.get('college_name'),
        request.form.get('college_address'), request.form.get('dept_email'),
        request.form.get('college_contact')
    )
    
    if existing:
        if photo_url:
            conn.execute("""UPDATE about_page SET dev_name=?,roll_no=?,dev_email=?,dev_contact=?,
                dev_photo=?,linkedin=?,github=?,instagram=?,college_name=?,college_address=?,
                dept_email=?,college_contact=? WHERE id=1""",
                vals[:4] + (photo_url,) + vals[4:])
        else:
            conn.execute("""UPDATE about_page SET dev_name=?,roll_no=?,dev_email=?,dev_contact=?,
                linkedin=?,github=?,instagram=?,college_name=?,college_address=?,
                dept_email=?,college_contact=? WHERE id=1""", vals)
    else:
        if photo_url:
            conn.execute("""INSERT INTO about_page (id,dev_name,roll_no,dev_email,dev_contact,
                dev_photo,linkedin,github,instagram,college_name,college_address,dept_email,college_contact)
                VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?)""",
                vals[:4] + (photo_url,) + vals[4:])
        else:
            conn.execute("""INSERT INTO about_page (id,dev_name,roll_no,dev_email,dev_contact,
                linkedin,github,instagram,college_name,college_address,dept_email,college_contact)
                VALUES (1,?,?,?,?,?,?,?,?,?,?,?)""", vals)
    
    conn.commit(); conn.close()
    flash('About page updated!','success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)