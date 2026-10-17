from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
import sqlite3
import os
import csv
import io
from datetime import datetime, date, timedelta
import calendar
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clinic-select-secret-key-2024')
DATABASE = 'clinic.db'

# Ensure Arabic locale-like formatting
def to_arabic_numerals(num_str):
    if num_str is None:
        return ''
    num_str = str(num_str)
    arabic_digits = {'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
                     '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'}
    return ''.join(arabic_digits.get(c, c) for c in num_str)

# Context processor for template globals
@app.context_processor
def inject_globals():
    return {
        'arabic_nums': to_arabic_numerals,
        'today': date.today().isoformat(),
        'current_user': session.get('full_name'),
        'current_role': session.get('role')
    }

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            color TEXT DEFAULT '#0d9488',
            schedule TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            age INTEGER,
            gender TEXT,
            address TEXT,
            medical_history TEXT,
            blood_type TEXT,
            allergies TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            visit_date TEXT NOT NULL,
            diagnosis TEXT,
            prescription TEXT,
            notes TEXT,
            follow_up_date TEXT,
            type TEXT DEFAULT 'استشارة',
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT,
            type TEXT DEFAULT 'استشارة',
            status TEXT DEFAULT 'قيد الانتظار',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    ''')
    
    # Seed demo users
    cursor.execute('SELECT COUNT(*) as count FROM users')
    if cursor.fetchone()['count'] == 0:
        users = [
            ('Habiba', 'admin123', 'حبيبة', 'admin'),
            ('Reem', 'user123', 'ريم', 'receptionist')
        ]
        cursor.executemany('''
            INSERT INTO users (username, password, full_name, role)
            VALUES (?, ?, ?, ?)
        ''', users)
    
    # Seed demo doctors
    cursor.execute('SELECT COUNT(*) as count FROM doctors')
    if cursor.fetchone()['count'] == 0:
        doctors = [
            ('د. أحمد محمد', 'الباطنة', '01001234567', 'ahmed@clinic.com', '#0d9488', 'السبت - الأربعاء: ٩ ص - ٩ م'),
            ('د. سارة علي', 'الأطفال', '01009876543', 'sara@clinic.com', '#2563eb', 'السبت - الخميس: ١٠ ص - ٨ م'),
            ('د. خالد محمود', 'العظام', '01005678901', 'khaled@clinic.com', '#7c3aed', 'الأحد - الخميس: ١١ ص - ٧ م'),
            ('د. نور الدين فؤاد', 'الأسنان', '01006789012', 'nour@clinic.com', '#db2777', 'السبت - الأربعاء: ١٠ ص - ٩ م'),
            ('د. رانيا حسين', 'الجلدية', '01007890123', 'rania@clinic.com', '#ea580c', 'الأحد - الخميس: ٩ ص - ٥ م'),
            ('د. هالة عبدالرحمن', 'النساء والتوليد', '01008901234', 'hala@clinic.com', '#0891b2', 'السبت - الأربعاء: ١١ ص - ٨ م')
        ]
        cursor.executemany('''
            INSERT INTO doctors (name, department, phone, email, color, schedule)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', doctors)
    
    # Seed demo patients
    cursor.execute('SELECT COUNT(*) as count FROM patients')
    if cursor.fetchone()['count'] == 0:
        patients = [
            ('محمد عبدالله', '01001112233', 35, 'ذكر', 'القاهرة - مدينة نصر', 'ضغط مرتفع خفيف، لا يوجد أمراض مزمنة أخرى', 'A+', 'لا يوجد'),
            ('فاطمة أحمد', '01002223344', 28, 'أنثى', 'الجيزة - الدقي', 'أنيميا خفيفة، حامل في الشهر السابع', 'O+', 'البنسلين'),
            ('علي محمود', '01003334455', 52, 'ذكر', 'القاهرة - المعادي', 'سكري نوع ثاني، ارتفاع كوليسترول', 'B+', 'ال sulfa'),
            ('نورا سعيد', '01004445566', 41, 'أنثى', 'الإسكندرية - سموحة', 'صداع مزمن، حساسية موسمية', 'AB+', 'الغبار'),
            ('خالد عمر', '01005556677', 15, 'ذكر', 'القاهرة - مصر الجديدة', 'ربو خفيف، يستخدم inhaler', 'O-', 'الفول السوداني'),
            ('سارة حسن', '01006667788', 33, 'أنثى', 'الجيزة - المهندسين', 'صحة جيدة عموماً، فحص دوري', 'A-', 'لا يوجد'),
            ('أحمد كمال', '01007778899', 60, 'ذكر', 'القاهرة -Heliopolis', 'قصور في القلب، ضغط مرتفع', 'B+', 'الأسبرين'),
            ('مريم جمال', '01008889900', 22, 'أنثى', 'الإسكندرية - العصافرة', 'تهاب حلق متكرر، فقر دم', 'O+', 'لا يوجد'),
            ('يوسف إبراهيم', '01009990011', 45, 'ذكر', 'القاهرة - التجمع', 'مشاكل في الغضروف الرقبي', 'A+', 'لا يوجد'),
            ('ليلى محمد', '01001001122', 8, 'أنثى', 'الجيزة - فيصل', 'صحة جيدة، متابعة نمو', 'B-', 'لا يوجد'),
            ('حسن علي', '01002112233', 70, 'ذكر', 'القاهرة - الزمالك', 'سكري، ضغط، خشونة مفاصل', 'O+', 'الأدوية المضادة للتخثر'),
            ('دنيا رامي', '01003223344', 30, 'أنثى', 'الإسكندرية - رشدي', 'ألم أسفل الظهر، متلازمة تكيس المبايض', 'A+', 'لا يوجد'),
            ('عمر خالد', '01004334455', 38, 'ذكر', 'القاهرة - مدينتي', 'تسوس أسنان، التهاب لثة', 'O+', 'لا يوجد'),
            ('رنا محمود', '01005445566', 27, 'أنثى', 'الجيزة - أكتوبر', 'حب شباب، تصبغات جلدية', 'B+', 'بعض مستحضرات التجميل'),
            ('سامي إبراهيم', '01006556677', 55, 'ذكر', 'القاهرة - الشروق', 'ضغط مرتفع، سكر', 'AB+', 'لا يوجد'),
            ('ندى علاء', '01007667788', 32, 'أنثى', 'الإسكندرية - جليم', 'متابعة حمل، فحص دوري', 'A-', 'لا يوجد'),
            ('تامر حسني', '01008778899', 42, 'ذكر', 'القاهرة - العباسية', 'صداع نصفي، توتر', 'B-', 'لا يوجد')
        ]
        cursor.executemany('''
            INSERT INTO patients (name, phone, age, gender, address, medical_history, blood_type, allergies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', patients)
    
    # Seed demo visits
    cursor.execute('SELECT COUNT(*) as count FROM visits')
    if cursor.fetchone()['count'] == 0:
        visits = [
            (1, 1, (date.today() - timedelta(days=5)).isoformat(), 'ارتفاع ضغط خفيف', 'amlodipine 5mg مرة يومياً', 'متابعة بعد أسبوع', (date.today() + timedelta(days=2)).isoformat(), 'متابعة'),
            (3, 1, (date.today() - timedelta(days=10)).isoformat(), 'سكري نوع ثاني', 'metformin 500mg مرتين يومياً', 'نظام غذائي منخفض الكربوهيدرات', (date.today() + timedelta(days=5)).isoformat(), 'متابعة'),
            (2, 2, (date.today() - timedelta(days=3)).isoformat(), 'فحص دوري للحامل', 'حديد وفيتامينات', 'الحالة مستقرة', (date.today() + timedelta(days=14)).isoformat(), 'كشف'),
            (5, 2, (date.today() - timedelta(days=7)).isoformat(), 'ربو تحسسي', 'salbutamol عند الحاجة', 'تجنب المهيجات', (date.today() + timedelta(days=10)).isoformat(), 'متابعة'),
            (9, 3, (date.today() - timedelta(days=12)).isoformat(), 'انزلاق غضروفي بسيط', 'مسكنات ومضاد التهاب', 'جلسات علاج طبيعي', (date.today() + timedelta(days=7)).isoformat(), 'جلسة'),
            (7, 1, (date.today() - timedelta(days=15)).isoformat(), 'قصور قلبي مزمن', 'furosemide 40mg', 'مراقبة الوزن يومياً', (date.today() + timedelta(days=3)).isoformat(), 'متابعة'),
            (11, 3, (date.today() - timedelta(days=8)).isoformat(), 'خشونة ركبة', 'علاج موضعي ومسكن', 'تجنب الوقوف الطويل', (date.today() + timedelta(days=6)).isoformat(), 'جلسة'),
            (13, 4, (date.today() - timedelta(days=4)).isoformat(), 'تسوس في ضرس العقل', 'حشو مؤقت ومضاد حيوي', 'متابعة بعد أسبوع لإزالة العصب', (date.today() + timedelta(days=7)).isoformat(), 'متابعة'),
            (14, 5, (date.today() - timedelta(days=6)).isoformat(), 'حب شباب التهابي', 'جل موضعي + مضاد حيوي', 'تجنب أشعة الشمس', (date.today() + timedelta(days=10)).isoformat(), 'متابعة'),
            (16, 6, (date.today() - timedelta(days=9)).isoformat(), 'متابعة حمل شهر رابع', 'فيتامينات وحمض فوليك', 'الحالة مستقرة', (date.today() + timedelta(days=21)).isoformat(), 'كشف'),
            (12, 4, (date.today() - timedelta(days=11)).isoformat(), 'جرثومة في اللثة', 'غسول فموي ومضاد', 'متابعة بعد ٥ أيام', (date.today() + timedelta(days=5)).isoformat(), 'متابعة'),
            (15, 1, (date.today() - timedelta(days=2)).isoformat(), 'ارتفاع سكر الدم', 'تعديل جرعة metformin', 'متابعة بعد ٣ أيام', (date.today() + timedelta(days=3)).isoformat(), 'متابعة')
        ]
        cursor.executemany('''
            INSERT INTO visits (patient_id, doctor_id, visit_date, diagnosis, prescription, notes, follow_up_date, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', visits)
    
    # Seed demo appointments for today and upcoming
    cursor.execute('SELECT COUNT(*) as count FROM appointments')
    if cursor.fetchone()['count'] == 0:
        today_str = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        appointments = [
            (1, 1, today_str, '09:00', 'متابعة', 'مؤكد', 'متابعة ضغط'),
            (2, 2, today_str, '09:30', 'كشف', 'مؤكد', 'فحص دوري للحامل'),
            (3, 1, today_str, '10:00', 'متابعة', 'قيد الانتظار', 'متابعة سكري'),
            (5, 2, today_str, '10:30', 'متابعة', 'مؤكد', 'متابعة ربو'),
            (9, 3, today_str, '11:00', 'جلسة', 'قيد الانتظار', 'جلسة علاج طبيعي'),
            (7, 1, today_str, '11:30', 'متابعة', 'مؤكد', 'متابعة قلب'),
            (11, 3, today_str, '12:00', 'جلسة', 'قيد الانتظار', 'خشونة ركبة'),
            (4, 1, tomorrow, '09:00', 'استشارة', 'قيد الانتظار', 'صداع مزمن'),
            (6, 2, (date.today() + timedelta(days=2)).isoformat(), '10:00', 'كشف', 'قيد الانتظار', 'فحص دوري'),
            (8, 2, (date.today() + timedelta(days=3)).isoformat(), '11:00', 'استشارة', 'قيد الانتظار', 'تعب عام'),
            (13, 4, today_str, '12:30', 'متابعة', 'مؤكد', 'حشو ضرس'),
            (14, 5, today_str, '13:00', 'كشف', 'قيد الانتظار', 'حب شباب'),
            (16, 6, today_str, '13:30', 'متابعة', 'مؤكد', 'متابعة حمل'),
            (12, 4, (date.today() + timedelta(days=1)).isoformat(), '14:00', 'متابعة', 'قيد الانتظار', 'التهاب لثة'),
            (15, 1, today_str, '14:30', 'متابعة', 'قيد الانتظار', 'تعديل علاج سكر'),
            (17, 5, (date.today() + timedelta(days=2)).isoformat(), '15:00', 'استشارة', 'قيد الانتظار', 'تساقط شعر'),
            (10, 6, (date.today() + timedelta(days=4)).isoformat(), '15:30', 'كشف', 'قيد الانتظار', 'فحص دوري')
        ]
        cursor.executemany('''
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, type, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', appointments)
    
    conn.commit()
    conn.close()

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f'مرحباً {user["full_name"]}، تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute('SELECT COUNT(*) as count FROM doctors')
    doctors_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM patients')
    patients_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM appointments WHERE appointment_date = ? AND status != ?', (today, 'ملغي'))
    today_appointments = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM appointments WHERE status = ?', ('قيد الانتظار',))
    pending_appointments = cursor.fetchone()['count']
    
    cursor.execute('''
        SELECT a.*, p.name as patient_name, p.phone as patient_phone, d.name as doctor_name, d.color
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.appointment_date >= ? AND a.status != ?
        ORDER BY a.appointment_date, a.appointment_time
        LIMIT 10
    ''', (today, 'ملغي'))
    upcoming = cursor.fetchall()
    
    cursor.execute('''
        SELECT d.name, d.department, d.color, COUNT(a.id) as count
        FROM doctors d
        LEFT JOIN appointments a ON d.id = a.doctor_id AND a.appointment_date = ? AND a.status != ?
        GROUP BY d.id
    ''', (today, 'ملغي'))
    doctor_stats = cursor.fetchall()
    
    cursor.execute('''
        SELECT COUNT(*) as count FROM appointments 
        WHERE appointment_date = ? AND status = ?
    ''', (today, 'مؤكد'))
    confirmed_today = cursor.fetchone()['count']
    
    cursor.execute('''
        SELECT COUNT(*) as count FROM visits WHERE visit_date >= ?
    ''', ((date.today() - timedelta(days=30)).isoformat(),))
    monthly_visits = cursor.fetchone()['count']
    
    conn.close()
    return render_template('index.html', 
                         doctors_count=doctors_count,
                         patients_count=patients_count,
                         today_appointments=today_appointments,
                         pending_appointments=pending_appointments,
                         confirmed_today=confirmed_today,
                         monthly_visits=monthly_visits,
                         upcoming=upcoming,
                         doctor_stats=doctor_stats)

@app.route('/doctors', methods=['GET', 'POST'])
@login_required
def doctors():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        if session.get('role') != 'admin':
            flash('غير مصرح لك بإضافة أو تعديل الأطباء', 'danger')
            return redirect(url_for('doctors'))
        
        name = request.form['name']
        department = request.form['department']
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        color = request.form.get('color', '#0d9488')
        schedule = request.form.get('schedule', '')
        doctor_id = request.form.get('id')
        
        if doctor_id:
            cursor.execute('''
                UPDATE doctors SET name=?, department=?, phone=?, email=?, color=?, schedule=?
                WHERE id=?
            ''', (name, department, phone, email, color, schedule, doctor_id))
            flash('تم تحديث بيانات الطبيب بنجاح', 'success')
        else:
            cursor.execute('''
                INSERT INTO doctors (name, department, phone, email, color, schedule)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, department, phone, email, color, schedule))
            flash('تم إضافة الطبيب بنجاح', 'success')
        conn.commit()
        return redirect(url_for('doctors'))
    
    cursor.execute('SELECT * FROM doctors ORDER BY id')
    all_doctors = cursor.fetchall()
    conn.close()
    return render_template('doctors.html', doctors=all_doctors)

@app.route('/doctors/delete/<int:id>')
@admin_required
def delete_doctor(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM doctors WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('تم حذف الطبيب بنجاح', 'success')
    return redirect(url_for('doctors'))

@app.route('/patients', methods=['GET', 'POST'])
@login_required
def patients():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form.get('phone', '')
        age = request.form.get('age') or None
        gender = request.form.get('gender', '')
        address = request.form.get('address', '')
        medical_history = request.form.get('medical_history', '')
        blood_type = request.form.get('blood_type', '')
        allergies = request.form.get('allergies', '')
        patient_id = request.form.get('id')
        
        if patient_id:
            cursor.execute('''
                UPDATE patients SET name=?, phone=?, age=?, gender=?, address=?, medical_history=?, blood_type=?, allergies=?
                WHERE id=?
            ''', (name, phone, age, gender, address, medical_history, blood_type, allergies, patient_id))
            flash('تم تحديث بيانات المريض بنجاح', 'success')
        else:
            cursor.execute('''
                INSERT INTO patients (name, phone, age, gender, address, medical_history, blood_type, allergies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, phone, age, gender, address, medical_history, blood_type, allergies))
            flash('تم إضافة المريض بنجاح', 'success')
        conn.commit()
        return redirect(url_for('patients'))
    
    search = request.args.get('search', '')
    if search:
        cursor.execute('''
            SELECT * FROM patients 
            WHERE name LIKE ? OR phone LIKE ?
            ORDER BY id DESC
        ''', (f'%{search}%', f'%{search}%'))
    else:
        cursor.execute('SELECT * FROM patients ORDER BY id DESC')
    all_patients = cursor.fetchall()
    conn.close()
    return render_template('patients.html', patients=all_patients, search=search)

@app.route('/patients/delete/<int:id>')
@admin_required
def delete_patient(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM visits WHERE patient_id=?', (id,))
    cursor.execute('DELETE FROM appointments WHERE patient_id=?', (id,))
    cursor.execute('DELETE FROM patients WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('تم حذف المريض بنجاح', 'success')
    return redirect(url_for('patients'))

@app.route('/patient/<int:id>', methods=['GET', 'POST'])
@login_required
def patient_detail(id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        visit_date = request.form['visit_date']
        diagnosis = request.form.get('diagnosis', '')
        prescription = request.form.get('prescription', '')
        notes = request.form.get('notes', '')
        follow_up_date = request.form.get('follow_up_date') or None
        visit_type = request.form.get('type', 'استشارة')
        visit_id = request.form.get('visit_id')
        
        if visit_id:
            cursor.execute('''
                UPDATE visits SET doctor_id=?, visit_date=?, diagnosis=?, prescription=?, notes=?, follow_up_date=?, type=?
                WHERE id=?
            ''', (doctor_id, visit_date, diagnosis, prescription, notes, follow_up_date, visit_type, visit_id))
            flash('تم تحديث الجلسة بنجاح', 'success')
        else:
            cursor.execute('''
                INSERT INTO visits (patient_id, doctor_id, visit_date, diagnosis, prescription, notes, follow_up_date, type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id, doctor_id, visit_date, diagnosis, prescription, notes, follow_up_date, visit_type))
            flash('تم إضافة الجلسة بنجاح', 'success')
        conn.commit()
        return redirect(url_for('patient_detail', id=id))
    
    cursor.execute('SELECT * FROM patients WHERE id=?', (id,))
    patient = cursor.fetchone()
    
    cursor.execute('SELECT * FROM doctors ORDER BY name')
    all_doctors = cursor.fetchall()
    
    cursor.execute('''
        SELECT v.*, d.name as doctor_name, d.department
        FROM visits v
        JOIN doctors d ON v.doctor_id = d.id
        WHERE v.patient_id=?
        ORDER BY v.visit_date DESC
    ''', (id,))
    visits = cursor.fetchall()
    
    cursor.execute('''
        SELECT a.*, d.name as doctor_name, d.color
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id=?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (id,))
    appointments = cursor.fetchall()
    
    conn.close()
    return render_template('patient_detail.html', patient=patient, doctors=all_doctors, visits=visits, appointments=appointments)

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        doctor_id = request.form['doctor_id']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form.get('appointment_time', '')
        app_type = request.form.get('type', 'استشارة')
        status = request.form.get('status', 'قيد الانتظار')
        notes = request.form.get('notes', '')
        appointment_id = request.form.get('id')
        
        if appointment_id:
            cursor.execute('''
                UPDATE appointments SET patient_id=?, doctor_id=?, appointment_date=?, appointment_time=?, type=?, status=?, notes=?
                WHERE id=?
            ''', (patient_id, doctor_id, appointment_date, appointment_time, app_type, status, notes, appointment_id))
            flash('تم تحديث الموعد بنجاح', 'success')
        else:
            cursor.execute('''
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, type, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, doctor_id, appointment_date, appointment_time, app_type, status, notes))
            flash('تم حجز الموعد بنجاح', 'success')
        conn.commit()
        return redirect(url_for('appointments'))
    
    date_filter = request.args.get('date', '')
    doctor_filter = request.args.get('doctor', '')
    status_filter = request.args.get('status', '')
    
    query = '''
        SELECT a.*, p.name as patient_name, p.phone as patient_phone, d.name as doctor_name, d.color
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE 1=1
    '''
    params = []
    
    if date_filter:
        query += ' AND a.appointment_date = ?'
        params.append(date_filter)
    if doctor_filter:
        query += ' AND a.doctor_id = ?'
        params.append(doctor_filter)
    if status_filter:
        query += ' AND a.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY a.appointment_date DESC, a.appointment_time'
    
    cursor.execute(query, params)
    all_appointments = cursor.fetchall()
    
    cursor.execute('SELECT * FROM doctors ORDER BY name')
    all_doctors = cursor.fetchall()
    
    cursor.execute('SELECT id, name FROM patients ORDER BY name')
    all_patients = cursor.fetchall()
    
    conn.close()
    return render_template('appointments.html', 
                         appointments=all_appointments, 
                         doctors=all_doctors, 
                         patients=all_patients,
                         date_filter=date_filter,
                         doctor_filter=doctor_filter,
                         status_filter=status_filter)

@app.route('/appointments/delete/<int:id>')
@login_required
def delete_appointment(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM appointments WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('تم حذف الموعد بنجاح', 'success')
    return redirect(url_for('appointments'))

@app.route('/appointments/status/<int:id>/<status>')
@login_required
def update_appointment_status(id, status):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE appointments SET status=? WHERE id=?', (status, id))
    conn.commit()
    conn.close()
    flash('تم تحديث حالة الموعد بنجاح', 'success')
    return redirect(request.referrer or url_for('appointments'))

@app.route('/calendar')
@login_required
def calendar_view():
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    conn = get_db()
    cursor = conn.cursor()
    
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    cursor.execute('''
        SELECT a.*, p.name as patient_name, d.name as doctor_name, d.color
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.appointment_date BETWEEN ? AND ? AND a.status != ?
        ORDER BY a.appointment_time
    ''', (first_day.isoformat(), last_day.isoformat(), 'ملغي'))
    appointments = cursor.fetchall()
    
    appointments_by_date = {}
    for app in appointments:
        d = app['appointment_date']
        if d not in appointments_by_date:
            appointments_by_date[d] = []
        appointments_by_date[d].append(app)
    
    cursor.execute('SELECT * FROM doctors ORDER BY name')
    all_doctors = cursor.fetchall()
    conn.close()
    
    cal = calendar.Calendar()
    weeks = cal.monthdayscalendar(year, month)
    
    month_name = ['', 'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'][month]
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    return render_template('calendar.html',
                         year=year,
                         month=month,
                         month_name=month_name,
                         weeks=weeks,
                         appointments_by_date=appointments_by_date,
                         doctors=all_doctors,
                         prev_month=prev_month,
                         prev_year=prev_year,
                         next_month=next_month,
                         next_year=next_year)

@app.route('/api/available-slots')
@login_required
def available_slots():
    doctor_id = request.args.get('doctor_id')
    app_date = request.args.get('date')
    
    if not doctor_id or not app_date:
        return jsonify({'slots': []})
    
    all_slots = []
    for hour in range(9, 21):
        for minute in [0, 30]:
            all_slots.append(f"{hour:02d}:{minute:02d}")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appointment_time FROM appointments 
        WHERE doctor_id=? AND appointment_date=? AND status != ?
    ''', (doctor_id, app_date, 'ملغي'))
    booked = [row['appointment_time'] for row in cursor.fetchall()]
    conn.close()
    
    available = [slot for slot in all_slots if slot not in booked]
    return jsonify({'slots': available, 'booked': booked})

# Reports and Printing
@app.route('/reports/daily-appointments')
@login_required
def report_daily_appointments():
    report_date = request.args.get('date', date.today().isoformat())
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.age, p.gender, 
               d.name as doctor_name, d.department, d.color
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.appointment_date = ? AND a.status != ?
        ORDER BY a.appointment_time
    ''', (report_date, 'ملغي'))
    appointments = cursor.fetchall()
    
    cursor.execute('SELECT * FROM doctors ORDER BY name')
    doctors = cursor.fetchall()
    conn.close()
    
    return render_template('report_daily_appointments.html', 
                         appointments=appointments, 
                         report_date=report_date,
                         doctors=doctors)

@app.route('/reports/patient-prescription/<int:patient_id>/<int:visit_id>')
@login_required
def report_patient_prescription(patient_id, visit_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM patients WHERE id=?', (patient_id,))
    patient = cursor.fetchone()
    
    cursor.execute('''
        SELECT v.*, d.name as doctor_name, d.department
        FROM visits v
        JOIN doctors d ON v.doctor_id = d.id
        WHERE v.id=?
    ''', (visit_id,))
    visit = cursor.fetchone()
    
    conn.close()
    
    if not patient or not visit:
        flash('السجل غير موجود', 'danger')
        return redirect(url_for('patients'))
    
    return render_template('report_prescription.html', patient=patient, visit=visit)

@app.route('/reports/export/appointments')
@login_required
def export_appointments_csv():
    report_date = request.args.get('date', date.today().isoformat())
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.appointment_time, p.name as patient_name, p.phone, p.age, p.gender,
               d.name as doctor_name, d.department, a.type, a.status, a.notes
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.appointment_date = ? AND a.status != ?
        ORDER BY a.appointment_time
    ''', (report_date, 'ملغي'))
    appointments = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['الوقت', 'المريض', 'الهاتف', 'العمر', 'الجنس', 'الطبيب', 'القسم', 'النوع', 'الحالة', 'ملاحظات'])
    
    for app in appointments:
        writer.writerow([
            app['appointment_time'], app['patient_name'], app['phone'], app['age'],
            app['gender'], app['doctor_name'], app['department'], app['type'], app['status'], app['notes']
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': f'attachment; filename=appointments-{report_date}.csv'
        }
    )

@app.route('/reports/export/patients')
@login_required
def export_patients_csv():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patients ORDER BY name')
    patients = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['الاسم', 'الهاتف', 'العمر', 'الجنس', 'فصيلة الدم', 'حساسية', 'العنوان', 'التاريخ المرضي'])
    
    for patient in patients:
        writer.writerow([
            patient['name'], patient['phone'], patient['age'], patient['gender'],
            patient['blood_type'], patient['allergies'], patient['address'], patient['medical_history']
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': 'attachment; filename=patients.csv'
        }
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
