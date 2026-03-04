"""
LionCore Technologies - Backend API
====================================
Flask REST API with SQLite database
Routes: Auth, Enrollments, Contact, Courses, Admin Dashboard
"""

from flask import Flask, jsonify, request, g
from flask.wrappers import Response
import sqlite3, hashlib, jwt, datetime, os, json, re, functools

# ── App config ──────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'lioncore-secret-2026-change-in-production')
app.config['DATABASE']   = os.path.join(os.path.dirname(__file__), 'database', 'lioncore.db')

# ── CORS (manual — no extra package needed) ─────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.route("/", methods=["GET"])
def home():
    return "LionCore API is running 🦁"

# ── Database helpers ─────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db: db.close()

def query_db(sql, args=(), one=False, commit=False):
    db  = get_db()
    cur = db.execute(sql, args)
    if commit:
        db.commit()
        return cur.lastrowid
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

# ── Password helpers ─────────────────────────────────────────
def hash_password(pw):
    salt = os.urandom(16).hex()
    h    = hashlib.sha256((salt + pw).encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(pw, stored):
    try:
        salt, h = stored.split(':')
        return hashlib.sha256((salt + pw).encode()).hexdigest() == h
    except Exception:
        return False

# ── JWT helpers ──────────────────────────────────────────────
def make_token(user_id, role):
    payload = {
        'sub'  : user_id,
        'role' : role,
        'iat'  : datetime.datetime.utcnow(),
        'exp'  : datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])

def require_auth(roles=None):
    """Decorator — validates JWT and optionally checks role."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get('Authorization', '')
            if not auth.startswith('Bearer '):
                return jsonify({'error': 'Missing token'}), 401
            try:
                data = decode_token(auth.split(' ')[1])
                g.user_id   = data['sub']
                g.user_role = data['role']
                if roles and g.user_role not in roles:
                    return jsonify({'error': 'Forbidden'}), 403
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except Exception:
                return jsonify({'error': 'Invalid token'}), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ── Validation helpers ───────────────────────────────────────
def valid_email(e):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', e or ''))

def require_fields(data, *fields):
    missing = [f for f in fields if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400
    return None

# ════════════════════════════════════════════════════════════
# DATABASE INIT
# ════════════════════════════════════════════════════════════
def init_db():
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
    with app.app_context():
        db = get_db()
        db.executescript("""
        -- Users (admin / staff)
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            role       TEXT    NOT NULL DEFAULT 'staff',
            created_at TEXT    DEFAULT (datetime('now'))
        );

        -- Enrollments (Boot Camp applications)
        CREATE TABLE IF NOT EXISTS enrollments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT NOT NULL,
            last_name   TEXT NOT NULL,
            email       TEXT NOT NULL,
            phone       TEXT,
            course      TEXT NOT NULL,
            background  TEXT,
            status      TEXT NOT NULL DEFAULT 'pending',
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- Contact messages
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL,
            subject    TEXT NOT NULL,
            message    TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'unread',
            replied_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Courses catalogue
        CREATE TABLE IF NOT EXISTS courses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            category    TEXT NOT NULL,
            description TEXT,
            duration    TEXT,
            level       TEXT DEFAULT 'Beginner',
            price       REAL DEFAULT 0,
            modules     TEXT,
            active      INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- Consultancy requests
        CREATE TABLE IF NOT EXISTS consultancy (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            phone       TEXT,
            company     TEXT,
            service     TEXT NOT NULL,
            description TEXT,
            budget      TEXT,
            status      TEXT NOT NULL DEFAULT 'new',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- Newsletter subscribers
        CREATE TABLE IF NOT EXISTS subscribers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT UNIQUE NOT NULL,
            active     INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        db.commit()

        # Seed default admin
        existing = db.execute("SELECT id FROM users WHERE email='admin@lioncoretech.com'").fetchone()
        if not existing:
            db.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                ('Admin', 'admin@lioncoretech.com', hash_password('LionCore@2026'), 'admin')
            )
            db.commit()
            print("✅ Default admin created: admin@lioncoretech.com / LionCore@2026")

        # Seed courses
        count = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        if count == 0:
            courses = [
                ('Infrastructure',        'Education', 'Windows Server, Linux, Cloud & Virtualization',    '12 weeks', 'Beginner', 500,  '["Windows Server Essentials","Windows Server Admin","Linux Fundamentals","Linux Admin","Cloud Computing","Virtualization"]'),
                ('Web Development',       'Education', 'Front-End, Back-End and Mobile App Development',  '16 weeks', 'Beginner', 600,  '["Front-End Development","Back-End Development","Mobile App Development"]'),
                ('Networking',            'Education', 'Networking basics, routing and switching',         '8 weeks',  'Beginner', 400,  '["Networking Basics","Routing & Switching"]'),
                ('Data Science & AI',     'Education', 'Machine Learning, Data Engineering & Big Data',   '20 weeks', 'Intermediate', 800, '["Machine Learning","Data Engineering","Data Analysis","Big Data"]'),
                ('Programming',           'Education', 'Python, JavaScript and Java fundamentals',         '12 weeks', 'Beginner', 500,  '["Python","JavaScript","Java"]'),
                ('Database Admin',        'Education', 'Database design, management and administration',   '10 weeks', 'Beginner', 450,  '["Database Basics","Advanced Database","DBA"]'),
                ('Cybersecurity',         'Education', 'Network security, ethical hacking & SOC analysis', '16 weeks', 'Intermediate', 700, '["Network Security","Ethical Hacking","SOC Analysis"]'),
                ('Cloud & DevOps',        'Education', 'AWS/Azure, Docker, Kubernetes and CI/CD',          '14 weeks', 'Intermediate', 750, '["AWS/Azure","Docker","Kubernetes","CI/CD"]'),
                ('IT Infrastructure',     'Consultancy','End-to-end enterprise IT infrastructure design',  'Project',  'N/A', 0, '[]'),
                ('Cloud Migration',       'Consultancy','Strategic cloud adoption and workload migration',  'Project',  'N/A', 0, '[]'),
                ('Cybersecurity Audit',   'Consultancy','Security audits, pen testing and compliance',     'Project',  'N/A', 0, '[]'),
                ('Digital Transformation','Consultancy','Industry 4.0 roadmaps and ERP integration',       'Project',  'N/A', 0, '[]'),
                ('Custom Software',       'Consultancy','Bespoke web, mobile and enterprise apps',         'Project',  'N/A', 0, '[]'),
                ('Data Analytics',        'Consultancy','BI dashboards, AI analytics and data pipelines',  'Project',  'N/A', 0, '[]'),
            ]
            db.executemany(
                "INSERT INTO courses (title,category,description,duration,level,price,modules) VALUES (?,?,?,?,?,?,?)",
                courses
            )
            db.commit()
            print("✅ Courses seeded")

        print("✅ Database ready")

# ════════════════════════════════════════════════════════════
# ROUTES — HEALTH
# ════════════════════════════════════════════════════════════
@app.route('/api/health')
def health():
    return jsonify({
        'status'  : 'ok',
        'app'     : 'LionCore Technologies API',
        'version' : '1.0.0',
        'time'    : datetime.datetime.utcnow().isoformat()
    })

# ════════════════════════════════════════════════════════════
# ROUTES — AUTH
# ════════════════════════════════════════════════════════════
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    err  = require_fields(data, 'email', 'password')
    if err: return err

    user = query_db("SELECT * FROM users WHERE email=?", [data['email']], one=True)
    if not user or not verify_password(data['password'], user['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = make_token(user['id'], user['role'])
    return jsonify({
        'token': token,
        'user' : {'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']}
    })

@app.route('/api/auth/me', methods=['GET'])
@require_auth()
def me():
    user = query_db("SELECT id,name,email,role,created_at FROM users WHERE id=?", [g.user_id], one=True)
    if not user: return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))

@app.route('/api/auth/change-password', methods=['POST'])
@require_auth()
def change_password():
    data = request.get_json() or {}
    err  = require_fields(data, 'current_password', 'new_password')
    if err: return err

    user = query_db("SELECT * FROM users WHERE id=?", [g.user_id], one=True)
    if not verify_password(data['current_password'], user['password']):
        return jsonify({'error': 'Current password incorrect'}), 400
    if len(data['new_password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    query_db("UPDATE users SET password=? WHERE id=?",
             [hash_password(data['new_password']), g.user_id], commit=True)
    return jsonify({'message': 'Password updated successfully'})

# ════════════════════════════════════════════════════════════
# ROUTES — COURSES (public)
# ════════════════════════════════════════════════════════════
@app.route('/api/courses')
def get_courses():
    cat    = request.args.get('category')
    search = request.args.get('search', '')
    sql    = "SELECT * FROM courses WHERE active=1"
    args   = []
    if cat:
        sql += " AND category=?"; args.append(cat)
    if search:
        sql += " AND (title LIKE ? OR description LIKE ?)"; args += [f'%{search}%', f'%{search}%']
    sql += " ORDER BY category, title"
    rows  = query_db(sql, args)
    result = []
    for r in rows:
        d = dict(r)
        try: d['modules'] = json.loads(d['modules'] or '[]')
        except: d['modules'] = []
        result.append(d)
    return jsonify(result)

@app.route('/api/courses/<int:cid>')
def get_course(cid):
    row = query_db("SELECT * FROM courses WHERE id=? AND active=1", [cid], one=True)
    if not row: return jsonify({'error': 'Course not found'}), 404
    d = dict(row)
    try: d['modules'] = json.loads(d['modules'] or '[]')
    except: d['modules'] = []
    return jsonify(d)

# ════════════════════════════════════════════════════════════
# ROUTES — ENROLLMENTS (public submit + admin manage)
# ════════════════════════════════════════════════════════════
@app.route('/api/enroll', methods=['POST'])
def enroll():
    data = request.get_json() or {}
    err  = require_fields(data, 'first_name', 'last_name', 'email', 'course')
    if err: return err
    if not valid_email(data['email']):
        return jsonify({'error': 'Invalid email address'}), 400

    rid = query_db(
        "INSERT INTO enrollments (first_name,last_name,email,phone,course,background) VALUES (?,?,?,?,?,?)",
        [data['first_name'], data['last_name'], data['email'],
         data.get('phone',''), data['course'], data.get('background','')],
        commit=True
    )
    return jsonify({'message': 'Enrollment submitted successfully!', 'id': rid}), 201

@app.route('/api/enrollments')
@require_auth(['admin', 'staff'])
def list_enrollments():
    status = request.args.get('status')
    course = request.args.get('course')
    sql    = "SELECT * FROM enrollments WHERE 1=1"
    args   = []
    if status: sql += " AND status=?"; args.append(status)
    if course: sql += " AND course=?"; args.append(course)
    sql += " ORDER BY created_at DESC"
    rows = query_db(sql, args)
    return jsonify([dict(r) for r in rows])

@app.route('/api/enrollments/<int:eid>', methods=['PUT'])
@require_auth(['admin', 'staff'])
def update_enrollment(eid):
    data = request.get_json() or {}
    fields, args = [], []
    for f in ('status', 'notes'):
        if f in data: fields.append(f"{f}=?"); args.append(data[f])
    if not fields: return jsonify({'error': 'Nothing to update'}), 400
    args.append(eid)
    query_db(f"UPDATE enrollments SET {', '.join(fields)} WHERE id=?", args, commit=True)
    return jsonify({'message': 'Enrollment updated'})

@app.route('/api/enrollments/<int:eid>', methods=['DELETE'])
@require_auth(['admin'])
def delete_enrollment(eid):
    query_db("DELETE FROM enrollments WHERE id=?", [eid], commit=True)
    return jsonify({'message': 'Enrollment deleted'})

# ════════════════════════════════════════════════════════════
# ROUTES — CONTACT MESSAGES
# ════════════════════════════════════════════════════════════
@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json() or {}
    err  = require_fields(data, 'name', 'email', 'subject', 'message')
    if err: return err
    if not valid_email(data['email']):
        return jsonify({'error': 'Invalid email address'}), 400

    rid = query_db(
        "INSERT INTO messages (name,email,subject,message) VALUES (?,?,?,?)",
        [data['name'], data['email'], data['subject'], data['message']],
        commit=True
    )
    return jsonify({'message': 'Message sent successfully!', 'id': rid}), 201

@app.route('/api/messages')
@require_auth(['admin', 'staff'])
def list_messages():
    status = request.args.get('status')
    sql  = "SELECT * FROM messages"
    args = []
    if status: sql += " WHERE status=?"; args.append(status)
    sql += " ORDER BY created_at DESC"
    rows = query_db(sql, args)
    return jsonify([dict(r) for r in rows])

@app.route('/api/messages/<int:mid>', methods=['PUT'])
@require_auth(['admin', 'staff'])
def update_message(mid):
    data = request.get_json() or {}
    fields, args = [], []
    for f in ('status',):
        if f in data: fields.append(f"{f}=?"); args.append(data[f])
    if data.get('status') == 'replied':
        fields.append("replied_at=?"); args.append(datetime.datetime.utcnow().isoformat())
    if not fields: return jsonify({'error': 'Nothing to update'}), 400
    args.append(mid)
    query_db(f"UPDATE messages SET {', '.join(fields)} WHERE id=?", args, commit=True)
    return jsonify({'message': 'Message updated'})

@app.route('/api/messages/<int:mid>', methods=['DELETE'])
@require_auth(['admin'])
def delete_message(mid):
    query_db("DELETE FROM messages WHERE id=?", [mid], commit=True)
    return jsonify({'message': 'Message deleted'})

# ════════════════════════════════════════════════════════════
# ROUTES — CONSULTANCY REQUESTS
# ════════════════════════════════════════════════════════════
@app.route('/api/consultancy', methods=['POST'])
def request_consultancy():
    data = request.get_json() or {}
    err  = require_fields(data, 'name', 'email', 'service')
    if err: return err
    if not valid_email(data['email']):
        return jsonify({'error': 'Invalid email address'}), 400

    rid = query_db(
        "INSERT INTO consultancy (name,email,phone,company,service,description,budget) VALUES (?,?,?,?,?,?,?)",
        [data['name'], data['email'], data.get('phone',''), data.get('company',''),
         data['service'], data.get('description',''), data.get('budget','')],
        commit=True
    )
    return jsonify({'message': 'Consultancy request submitted!', 'id': rid}), 201

@app.route('/api/consultancy')
@require_auth(['admin', 'staff'])
def list_consultancy():
    rows = query_db("SELECT * FROM consultancy ORDER BY created_at DESC")
    return jsonify([dict(r) for r in rows])

@app.route('/api/consultancy/<int:cid>', methods=['PUT'])
@require_auth(['admin', 'staff'])
def update_consultancy(cid):
    data = request.get_json() or {}
    fields, args = [], []
    for f in ('status',):
        if f in data: fields.append(f"{f}=?"); args.append(data[f])
    if not fields: return jsonify({'error': 'Nothing to update'}), 400
    args.append(cid)
    query_db(f"UPDATE consultancy SET {', '.join(fields)} WHERE id=?", args, commit=True)
    return jsonify({'message': 'Request updated'})

# ════════════════════════════════════════════════════════════
# ROUTES — NEWSLETTER
# ════════════════════════════════════════════════════════════
@app.route('/api/newsletter/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json() or {}
    if not valid_email(data.get('email','')):
        return jsonify({'error': 'Invalid email address'}), 400
    try:
        query_db("INSERT INTO subscribers (email) VALUES (?)", [data['email']], commit=True)
        return jsonify({'message': 'Subscribed successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Already subscribed!'}), 200

@app.route('/api/newsletter/unsubscribe', methods=['POST'])
def unsubscribe():
    data = request.get_json() or {}
    query_db("UPDATE subscribers SET active=0 WHERE email=?", [data.get('email','')], commit=True)
    return jsonify({'message': 'Unsubscribed successfully'})

@app.route('/api/newsletter/subscribers')
@require_auth(['admin'])
def list_subscribers():
    rows = query_db("SELECT * FROM subscribers WHERE active=1 ORDER BY created_at DESC")
    return jsonify([dict(r) for r in rows])

# ════════════════════════════════════════════════════════════
# ROUTES — ADMIN DASHBOARD STATS
# ════════════════════════════════════════════════════════════
@app.route('/api/admin/stats')
@require_auth(['admin', 'staff'])
def admin_stats():
    total_enrollments  = query_db("SELECT COUNT(*) as c FROM enrollments", one=True)['c']
    pending_enrollments= query_db("SELECT COUNT(*) as c FROM enrollments WHERE status='pending'", one=True)['c']
    approved_enrollments=query_db("SELECT COUNT(*) as c FROM enrollments WHERE status='approved'", one=True)['c']
    total_messages     = query_db("SELECT COUNT(*) as c FROM messages", one=True)['c']
    unread_messages    = query_db("SELECT COUNT(*) as c FROM messages WHERE status='unread'", one=True)['c']
    total_consultancy  = query_db("SELECT COUNT(*) as c FROM consultancy", one=True)['c']
    new_consultancy    = query_db("SELECT COUNT(*) as c FROM consultancy WHERE status='new'", one=True)['c']
    total_subscribers  = query_db("SELECT COUNT(*) as c FROM subscribers WHERE active=1", one=True)['c']
    total_courses      = query_db("SELECT COUNT(*) as c FROM courses WHERE active=1", one=True)['c']

    # Enrollments by course (top 5)
    by_course = query_db(
        "SELECT course, COUNT(*) as count FROM enrollments GROUP BY course ORDER BY count DESC LIMIT 5"
    )

    # Enrollments last 7 days
    weekly = query_db(
        "SELECT date(created_at) as day, COUNT(*) as count FROM enrollments "
        "WHERE created_at >= date('now','-7 days') GROUP BY day ORDER BY day"
    )

    # Latest 5 enrollments
    recent_enrollments = query_db(
        "SELECT id,first_name,last_name,email,course,status,created_at FROM enrollments ORDER BY created_at DESC LIMIT 5"
    )

    # Latest 5 messages
    recent_messages = query_db(
        "SELECT id,name,email,subject,status,created_at FROM messages ORDER BY created_at DESC LIMIT 5"
    )

    return jsonify({
        'summary': {
            'total_enrollments'   : total_enrollments,
            'pending_enrollments' : pending_enrollments,
            'approved_enrollments': approved_enrollments,
            'total_messages'      : total_messages,
            'unread_messages'     : unread_messages,
            'total_consultancy'   : total_consultancy,
            'new_consultancy'     : new_consultancy,
            'total_subscribers'   : total_subscribers,
            'total_courses'       : total_courses,
        },
        'enrollments_by_course' : [dict(r) for r in by_course],
        'weekly_enrollments'    : [dict(r) for r in weekly],
        'recent_enrollments'    : [dict(r) for r in recent_enrollments],
        'recent_messages'       : [dict(r) for r in recent_messages],
    })

# ════════════════════════════════════════════════════════════
# ROUTES — USER MANAGEMENT (admin only)
# ════════════════════════════════════════════════════════════
@app.route('/api/admin/users')
@require_auth(['admin'])
def list_users():
    rows = query_db("SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC")
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/users', methods=['POST'])
@require_auth(['admin'])
def create_user():
    data = request.get_json() or {}
    err  = require_fields(data, 'name', 'email', 'password')
    if err: return err
    if not valid_email(data['email']):
        return jsonify({'error': 'Invalid email'}), 400
    try:
        uid = query_db(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            [data['name'], data['email'], hash_password(data['password']),
             data.get('role','staff')], commit=True
        )
        return jsonify({'message': 'User created', 'id': uid}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 409

@app.route('/api/admin/users/<int:uid>', methods=['DELETE'])
@require_auth(['admin'])
def delete_user(uid):
    if uid == g.user_id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    query_db("DELETE FROM users WHERE id=?", [uid], commit=True)
    return jsonify({'message': 'User deleted'})

# ════════════════════════════════════════════════════════════
# ROUTES — COURSES ADMIN (CRUD)
# ════════════════════════════════════════════════════════════
@app.route('/api/admin/courses', methods=['POST'])
@require_auth(['admin'])
def create_course():
    data = request.get_json() or {}
    err  = require_fields(data, 'title', 'category')
    if err: return err
    cid = query_db(
        "INSERT INTO courses (title,category,description,duration,level,price,modules) VALUES (?,?,?,?,?,?,?)",
        [data['title'], data['category'], data.get('description',''),
         data.get('duration',''), data.get('level','Beginner'),
         data.get('price',0), json.dumps(data.get('modules',[]))],
        commit=True
    )
    return jsonify({'message': 'Course created', 'id': cid}), 201

@app.route('/api/admin/courses/<int:cid>', methods=['PUT'])
@require_auth(['admin'])
def update_course(cid):
    data   = request.get_json() or {}
    fields, args = [], []
    for f in ('title','category','description','duration','level','price','active'):
        if f in data: fields.append(f"{f}=?"); args.append(data[f])
    if 'modules' in data:
        fields.append("modules=?"); args.append(json.dumps(data['modules']))
    if not fields: return jsonify({'error': 'Nothing to update'}), 400
    args.append(cid)
    query_db(f"UPDATE courses SET {', '.join(fields)} WHERE id=?", args, commit=True)
    return jsonify({'message': 'Course updated'})

@app.route('/api/admin/courses/<int:cid>', methods=['DELETE'])
@require_auth(['admin'])
def delete_course(cid):
    query_db("UPDATE courses SET active=0 WHERE id=?", [cid], commit=True)
    return jsonify({'message': 'Course deactivated'})

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print("\n🦁 LionCore Technologies API starting...")
    print("📡 API: http://localhost:5000")
    print("📋 Admin: admin@lioncoretech.com / LionCore@2026\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
