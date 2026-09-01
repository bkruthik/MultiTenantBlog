# MultiTenantBlog — Multi-Tenant Social & Community Platform
A modern multi-tenant community and social blogging platform built with **Django** and **Tailwind CSS**. Designed for organizations, study clubs, interest groups, and dev teams with strict data isolation, role-based access control (RBAC), interactive social features, and built-in moderation.
---
## 🚀 Key Features
- **Multi-Tenant Architecture**: Strict row-level data isolation across independent communities with custom URL slugs. Direct URL tampering across tenants is rejected.
- **Strict Role-Based Access Control (RBAC)** (Server-Side Enforced):
  - **ADMIN**: Full CRUD on posts, manage members, promote/demote editors, kick members, transfer ownership.
  - **EDITOR**: Create, publish, and edit community posts.
  - **VIEWER**: Read-only + like posts/comments, vote in polls, and join discussions (server blocks edit/delete requests with HTTP 403).
- **Public & Private Communities**: Open public spaces with 1-click join or invitation-only private groups with access restriction.
- **Community & User Avatars**: Custom image URL integration or quick emoji avatar selector (18+ presets), rendered across feeds, comments, crew chat, member directories, and the navbar.
- **Interactive Community Polls**: Attach multi-choice polls to posts with percentage progress bars and database-enforced single-vote constraint.
- **Threaded Comments & Likes**: Nested 1-level reply threads, comment likes, and author badges.
- **YouTube Video Cards**: Zero iframe/embed errors; HD thumbnail preview cards with direct launch buttons + native HTML5 player for `.mp4` files.
- **Smart Category Auto-Detection**: Automatically infers topic categories from title and content keywords, plus dynamic custom category discovery.
- **Community Crew Chat Board**: Tenant-scoped community message board for member discussions.
- **Reporting & Moderation System**: User & community reporting system with staff-only moderation inbox (`/reports/inbox/`).
- **Anti-Hijack Password Reset**: Single-use cryptographically signed token verification requiring both username and matching registered email.
---
## 🔒 RBAC Permission Matrix
| Action | ADMIN | EDITOR | VIEWER | Server Enforcement |
|---|:---:|:---:|:---:|:---:|
| View Community Feed & Posts | ✅ | ✅ | ✅ | Private checks |
| Like Posts & Comments | ✅ | ✅ | ✅ | Member check |
| Vote in Community Polls | ✅ | ✅ | ✅ | Single-vote DB constraint |
| Add Comments & Replies | ✅ | ✅ | ✅ | Member check |
| Create New Posts | ✅ | ✅ | ❌ | HTTP 403 on Viewer POST |
| Edit Own Posts | ✅ | ✅ | ❌ | HTTP 403 on Viewer POST |
| Edit Any Post in Tenant | ✅ | ❌ | ❌ | HTTP 403 on Editor POST |
| Delete Posts | ✅ | ❌ | ❌ | HTTP 403 on Non-Admin |
| Promote / Demote Members | ✅ | ❌ | ❌ | HTTP 403 on Non-Admin |
| Remove (Kick) Members | ✅ | ❌ | ❌ | HTTP 403 on Non-Admin |
| Transfer Primary Admin Role | ✅ | ❌ | ❌ | HTTP 403 on Non-Admin |
---
## 🛠️ Tech Stack
- **Backend**: Python 3.11+, Django 5.2+
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: Django Templates, Tailwind CSS
- **Authentication**: Django Auth with custom RBAC & Single-Use Password Reset Tokens
---
## 📦 Getting Started
### 1. Clone the Repository
```bash
git clone https://github.com/your-username/MultiTenantBlog.git
cd MultiTenantBlog
2. Create and Activate a Virtual Environment
bash


# Windows
python -m venv venv
venv\Scripts\activate
# macOS / Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
bash


pip install -r requirements.txt
4. Configure Environment Variables
Copy .env.example to create your local .env:

bash


cp .env.example .env
Update .env with your secret key and database credentials:

ini


SECRET_KEY=your-secure-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=multitenant_blog
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
5. Run Migrations & Seed Sample Data
bash


python manage.py migrate
python manage.py seed_data
6. Start Development Server
bash


python manage.py runserver
Visit http://127.0.0.1:8000 in your browser.

📁 Project Structure
text


MultiTenantBlog/
├── MultiTenantBlog/      # Core settings, WSGI/ASGI, global URL routing
├── accounts/             # Authentication, UserProfile, secure password reset
├── memberships/          # Multi-tenant membership & RBAC models
├── posts/                # Posts, Likes, Comments, Polls, feed views & templates
├── reports/              # User/community report system & moderation inbox
├── tenants/              # Community creation, Explore directory, Crew Chat board
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── manage.py             # Django CLI
