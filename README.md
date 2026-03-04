# 🦁 LionCore Technologies — Backend API

A full REST API backend for the LionCore Technologies website, built with **Python Flask** and **SQLite**.

---

## 🚀 Quick Start

### 1. Install Python (if not installed)
Download from: https://python.org/downloads (Python 3.8+)

### 2. Install dependencies
```bash
pip install flask PyJWT python-dotenv
```

### 3. Run the server
```bash
python app.py
```

Server starts at: **http://localhost:5000**

Default admin login:
- **Email:** admin@lioncoretech.com
- **Password:** LionCore@2026

---

## 📁 Project Structure

```
lioncore-backend/
├── app.py              ← Main API server (all routes)
├── requirements.txt    ← Python dependencies
├── .env.example        ← Environment config template
├── .gitignore          ← Git ignore rules
├── README.md           ← This file
└── database/
    └── lioncore.db     ← SQLite database (auto-created)
```

---

## 🔌 API Endpoints

### Public Endpoints (no login required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Server health check |
| GET | `/api/courses` | List all courses |
| GET | `/api/courses/:id` | Get single course |
| POST | `/api/enroll` | Submit enrollment application |
| POST | `/api/contact` | Send contact message |
| POST | `/api/consultancy` | Submit consultancy request |
| POST | `/api/newsletter/subscribe` | Subscribe to newsletter |
| POST | `/api/newsletter/unsubscribe` | Unsubscribe from newsletter |

### Auth Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login and get JWT token |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/change-password` | Change password |

### Admin Endpoints (JWT token required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/enrollments` | List all enrollments |
| PUT | `/api/enrollments/:id` | Update enrollment status |
| DELETE | `/api/enrollments/:id` | Delete enrollment |
| GET | `/api/messages` | List all messages |
| PUT | `/api/messages/:id` | Update message status |
| DELETE | `/api/messages/:id` | Delete message |
| GET | `/api/consultancy` | List consultancy requests |
| PUT | `/api/consultancy/:id` | Update consultancy status |
| GET | `/api/newsletter/subscribers` | List subscribers |
| GET | `/api/admin/users` | List system users |
| POST | `/api/admin/users` | Create new user |
| DELETE | `/api/admin/users/:id` | Delete user |
| POST | `/api/admin/courses` | Create new course |
| PUT | `/api/admin/courses/:id` | Update course |
| DELETE | `/api/admin/courses/:id` | Deactivate course |

---

## 📨 Request / Response Examples

### Enroll in a course
```json
POST /api/enroll
{
  "first_name": "John",
  "last_name":  "Doe",
  "email":      "john@example.com",
  "phone":      "+23272000000",
  "course":     "Web Development",
  "background": "I am a graduate looking to switch into tech"
}
```
Response:
```json
{ "message": "Enrollment submitted successfully!", "id": 1 }
```

### Login
```json
POST /api/auth/login
{ "email": "admin@lioncoretech.com", "password": "LionCore@2026" }
```
Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user":  { "id": 1, "name": "Admin", "email": "admin@lioncoretech.com", "role": "admin" }
}
```

### Use token for protected routes
```
GET /api/enrollments
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🗄️ Database Tables

| Table | Description |
|-------|-------------|
| `users` | Admin and staff accounts |
| `enrollments` | Boot Camp course applications |
| `messages` | Contact form submissions |
| `consultancy` | Consultancy service requests |
| `courses` | Course catalogue |
| `subscribers` | Newsletter email subscribers |

---

## 🔗 Connecting the Frontend Website

In your `index.html`, replace the form `onsubmit` handlers to call the API:

```javascript
// Enrollment form
async function handleEnroll(e) {
  e.preventDefault();
  const form = e.target;
  const response = await fetch('http://localhost:5000/api/enroll', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      first_name: form.querySelector('[name=first_name]').value,
      last_name:  form.querySelector('[name=last_name]').value,
      email:      form.querySelector('[name=email]').value,
      course:     form.querySelector('[name=course]').value,
    })
  });
  const data = await response.json();
  alert(data.message);
}

// Contact form
async function handleContact(e) {
  e.preventDefault();
  const form = e.target;
  await fetch('http://localhost:5000/api/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name:    form.querySelector('[name=name]').value,
      email:   form.querySelector('[name=email]').value,
      subject: form.querySelector('[name=subject]').value,
      message: form.querySelector('[name=message]').value,
    })
  });
}
```

---

## 🌐 Deploying to Production (Free Options)

### Option A — Railway.app (Recommended, Free)
1. Go to https://railway.app and sign up
2. Click **New Project → Deploy from GitHub**
3. Select your `lioncore-technologies` repo
4. Add environment variable: `SECRET_KEY=your-secret-key`
5. Railway auto-detects Flask and deploys!
6. Your API URL: `https://lioncore-backend.up.railway.app`

### Option B — Render.com (Free)
1. Go to https://render.com and sign up
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Set **Start Command:** `python app.py`
5. Add env var: `SECRET_KEY=your-secret-key`
6. Deploy!

### Option C — PythonAnywhere (Free)
1. Go to https://pythonanywhere.com
2. Upload your files
3. Create a web app → Flask
4. Point to `app.py`

---

## 🔒 Security Checklist for Production

- [ ] Change `SECRET_KEY` to a long random string
- [ ] Change admin password from default
- [ ] Set `FLASK_DEBUG=False`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Add rate limiting to public endpoints
- [ ] Enable HTTPS only
- [ ] Restrict CORS to your domain only

---

## 👤 Default Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@lioncoretech.com | LionCore@2026 | Admin |

**⚠️ Change the default password immediately after first login!**

---

## 📞 Support

**LionCore Technologies**
- Email: info@lioncoretech.com
- Phone: +232 72 811111
- Address: 13 Lab Lane, Wilkinson Road, Freetown, Sierra Leone
