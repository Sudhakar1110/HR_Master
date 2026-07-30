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

## Installation

### Prerequisites
- ERPNext v15+ installed via Frappe Bench
- Python 3.11+

### Steps

```bash
# Navigate to your bench directory
cd ~/frappe-bench

# Get the app
bench get-app https://github.com/Sudhakar1110/HR_Master.git

# Install on your site
bench --site your-site.com install-app hr_master

# Migrate (creates tables, runs patches)
bench --site your-site.com migrate
```

### Post-Installation Setup

1. Assign **HR Master Roles** (HR Master Admin, Recruiter, Hiring Manager, Viewer)
2. Configure **Recruitment Settings** for your organization
3. Add **Skills** to the Skill master
4. Create **Job Descriptions** and start sourcing candidates

## Quick Start

1. **Enter JD**: Go to HR Master > Job Description and paste your JD
2. **Search Portals**: Click "Search Portals" button to find matching candidates
3. **Review Rankings**: View ranked candidates with match scores
4. **Shortlist**: Mark candidates as shortlisted
5. **Schedule Interviews**: Use the Interview Schedule doctype
6. **Generate Offers**: Create offer letters for selected candidates

## Roles & Permissions

| Role | Description |
|------|-------------|
| HR Master Admin | Full access to all features |
| HR Master Recruiter | Can create JDs, search, rank candidates |
| HR Master Hiring Manager | Can view rankings, schedule interviews |
| HR Master Viewer | Read-only access |

## License

MIT
