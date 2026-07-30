# HR Master - AI-Powered Candidate Sourcing & Ranking System for ERPNext v15+

HR Master is a comprehensive Frappe/ERPNext v15+ application that revolutionizes talent acquisition by automatically searching job portals (LinkedIn, Naukri, etc.) and ranking candidates based on Job Description (JD) match scores.

## Features

- 🔍 **Smart JD Parsing** - Extract key skills, experience, education, and requirements from any Job Description
- 🌐 **Multi-Portal Search** - Search LinkedIn, Naukri and other job portals automatically
- 📊 **AI-Powered Ranking** - Rank candidates using NLP-based skill matching and semantic analysis
- 📋 **Candidate Management** - Full lifecycle management from sourcing to interview scheduling
- 🎯 **Match Score Analysis** - Comprehensive skill-by-skill and overall match percentage
- 🔔 **Smart Notifications** - Automated alerts for shortlisted candidates and interview schedules
- 📈 **Advanced Reports** - Candidate match reports and JD analysis dashboards
- 🔄 **Background Jobs** - Automated scheduled searches and re-ranking
- 🔐 **Role-Based Access** - Secure HR, Recruiter, and Manager role hierarchies

## Tech Stack

- **Framework:** Frappe Framework v15+, ERPNext v15+
- **AI/ML:** NLTK, Scikit-learn for NLP-based matching
- **Backend:** Python 3.11+
- **Search:** BeautifulSoup, Requests for portal scraping
- **Scheduling:** Frappe Background Jobs / Scheduler Events

## Installation

### Prerequisites
- ERPNext v15+ installed via Frappe Bench
- Python 3.11+

### Steps

```bash
# Navigate to your bench directory
cd ~/frappe-bench

# Create the app
bench new-app hr_master

# Copy the HR Master source files to the app directory
# Or clone from repository
git clone https://github.com/your-org/hr_master apps/hr_master

# Install the app
bench setup requirements
bench build --app hr_master

# Install on your site
bench --site your-site.com install-app hr_master

# Migrate (creates tables, runs patches)
bench --site your-site.com migrate

# Configure HR Master
bench --site your-site.com console
```

### Post-Installation Setup

1. Create a **Job Portal Config** record with API keys/credentials
2. Assign **HR Master Roles** (HR Master Admin, Recruiter, Hiring Manager)
3. Configure **Email Notifications** for candidate alerts
4. Set up **Background Jobs** schedules in hooks.py

## Quick Start

1. **Add Skills**: Navigate to HR Master > Masters > Skills
2. **Enter JD**: Go to HR Master > Sourcing > Job Description and paste your JD
3. **Search Portals**: Click "Search Portals" button to find matching candidates
4. **Review Rankings**: View ranked candidates with match scores
5. **Shortlist**: Mark candidates as shortlisted
6. **Schedule Interviews**: Use the Interview Schedule doctype

## Architecture

```
hr_master/
├── hr_master/
│   ├── api/                    # REST API endpoints
│   ├── doctype/               # Document Types
│   │   ├── job_description/   # JD management
│   │   ├── candidate/         # Candidate profiles
│   │   ├── candidate_ranking/ # Match scores
│   │   ├── job_portal_search/ # Search management
│   │   ├── job_portal_config/ # Portal configurations
│   │   ├── interview_schedule/# Interview management
│   │   ├── skill/             # Skills master
│   │   └── department/        # Departments
│   ├── report/                # Custom reports
│   ├── workspace/             # Desk UI layouts
│   ├── notification/          # Alerts & notifications
│   ├── workflow/              # Approval workflows
│   ├── dashboard_chart/       # Analytics charts
│   └── patches/              # DB migration patches
└── configuration files
```

## Roles & Permissions

| Role | Description |
|------|-------------|
| HR Master Admin | Full access to all features |
| HR Master Recruiter | Can create JDs, search, rank candidates |
| HR Master Hiring Manager | Can view rankings, schedule interviews |
| HR Master Viewer | Read-only access |

## API Endpoints

- `POST /api/method/hr_master.api.search_candidates` - Search portals for candidates
- `POST /api/method/hr_master.api.rank_candidates` - Rank candidates against JD
- `GET /api/method/hr_master.api.get_candidate_details` - Get full candidate profile
- `POST /api/method/hr_master.api.sync_from_portal` - Sync candidates from portal

## License

MIT
