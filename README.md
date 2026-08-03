# HR Master - AI-Powered Candidate Sourcing & Ranking for ERPNext v15+

HR Master is a comprehensive **Frappe / ERPNext v15** app that helps recruiting teams source, rank, and manage candidates end-to-end — from job description and job-portal search through skill-based match scoring, interview scheduling, feedback, and offers.

Built and verified against **Frappe 15.100.0 / ERPNext 15.118.1 / HRMS 15.63.2** (Python 3.11).

---

## Features

- 🏠 **HR Recruiting Portal** — a complete web portal (no Desk needed): dashboard KPIs, JD management, portal search, ranked results, candidate profiles, Ask Me AI chat, dark/light theme
- 🔍 **JD Parsing & Analysis** — extract skills from any job description, score JD completeness, and get skill suggestions by category
- 🌐 **Job Portal Search** — queue searches for a JD across live sources (Remotive + Arbeitnow free/no-key, SerpAPI/Google Jobs + Adzuna key-based) with Demo sample candidates; import results into Candidates
- 📊 **AI-Powered Ranking** — weighted skill match (60%) + experience (25%) + education (15%) scoring with per-skill breakdowns and recommendations
- 🤖 **Ask Me (AI Assistant)** — chat with AI about any JD or candidate, plus 6 one-click AI tools (summary, screening questions, interview questions, skills, search keywords, salary benchmark). Powered by Gemini / Groq / OpenAI / DeepSeek / local Ollama when configured; smart rule-based fallback otherwise
- 📋 **Candidate Lifecycle** — Candidate, Resume (with parsed sections), Ranking, Interview Schedule, Interview Feedback, and Offer Management
- 🔄 **Workflow Driven** — the *Candidate Evaluation* workflow moves records through Pending → Evaluated → Shortlisted → Interview Scheduled → Selected / Rejected / On Hold
- 📈 **11 Built-in Reports** — candidate match, hiring funnel, skill gap, time-to-hire, recruiter/offer/interview performance, and more
- 🏠 **HR Master Workspace** — 8 shortcuts, 4 cards with 26 links, and 11 live "Key Metrics" number cards
- 🔔 **Notifications & Email Templates** — shortlisted, interview scheduled, offer generated/accepted, hired, and more
- 🔐 **Role-Based Access** — Admin, Recruiter, Hiring Manager, and Viewer roles

---

## Requirements

| Component | Version |
|---|---|
| Frappe / ERPNext | v15+ (verified on 15.100.0 / 15.118.1) |
| Python | 3.11+ |
| Bench | 5.x |

---

## Installation

```bash
# 1. Get the app
cd ~/frappe-bench-v15
bench get-app https://github.com/Sudhakar1110/HR_Master.git

# 2. Install on your site
bench --site your-site.com install-app hr_master

# 3. Migrate (creates tables, imports fixtures, seeds data)
bench --site your-site.com migrate

# 4. Restart services
bench restart
```

Open the **HR Master** workspace from the module list (or `/app/hr-master`).

### What gets created automatically

`after_install` / `after_migrate` hooks (`hr_master.setup.install`) run these phases — **no manual setup required**:

| Phase | Creates |
|---|---|
| `ensure_module_def` | `Module Def: HR Master` (refreshes module maps) |
| `create_workflow_masters` | 7 **Workflow States** + 7 **Workflow Action Masters** used by the Candidate Evaluation workflow |
| `sync_all_resources` | Imports all **70 JSON fixtures** from disk (doctypes, reports, workspace, number cards, notifications, print formats, letter heads, workflow, email templates) |
| `create_seed_data` | 4 roles, 10 common departments, 44 common skills |
| `set_default_config` | Defaults for **Job Portal Config** & **Recruitment Settings**, plus default email templates |

> ✅ A healthy migrate prints: `HR Master: workflow masters ready` and `HR Master: synced resources - 41 imported, 29 skipped`.
> The **29 skipped** are the DocType definition files — Frappe's native migrate already synced them (see *Troubleshooting*).

### Post-Installation Setup

1. Assign **HR Master roles** (HR Master Admin, Recruiter, Hiring Manager, Viewer) to your users
2. Review **Recruitment Settings** and **Job Portal Config** (defaults are pre-filled)
3. Create a **Job Description** and use **Search Portals** to start sourcing
4. Upload a **Resume** to a Candidate to auto-parse skills and experience

---

## Project Structure

```
hr_master/
└── hr_master/                          # Python package
    ├── api/                            # Whitelisted REST endpoints
    │   ├── candidate_api.py            #   parse_resume, get_candidate_details, bulk status
    │   ├── jd_api.py                   #   JD skill parsing & completeness analysis
    │   ├── ranking_api.py              #   rank candidates, ranking summary
    │   └── search_api.py               #   portal search, import results, search status
    ├── boot.py                         # boot session config
    ├── hooks.py                        # app hooks (scheduler, doc_events, after_migrate)
    ├── modules.py                      # Frappe v15 module registration (get_data)
    ├── setup/
    │   └── install.py                  # after_install / after_migrate seeding phases
    ├── tasks/                          # scheduled background jobs (search, ranking, email…)
    ├── utils/                          # helpers (csv import, duplicate detection, export…)
    ├── security/                       # rate limiting, job monitoring, error logging
    ├── hr_master/                      # the "HR Master" module folder
    │   ├── patches/                    #   migration patches (create_initial_custom_fields)
    │   ├── doctype/                    #   29 doctype folders (17 parents + 12 child tables)
    │   ├── report/                     #   11 script reports
    │   ├── workspace/                  #   HR Master workspace
    │   ├── number_card/                #   11 number cards
    │   ├── workflow/                   #   Candidate Evaluation workflow
    │   ├── notification/               #   8 notifications
    │   ├── print_format/               #   3 print formats
    │   ├── email_template/             #   4 email templates
    │   └── letter_head/                #   2 letter heads
    └── ...
```

---

## Doctypes (29 — 17 parents + 12 child tables)

| DocType | Child Tables | Purpose |
|---|---|---|
| **Job Description** | `JD Skill Detail` | JD with required/preferred skills, experience, salary range |
| **Candidate** | `Candidate Skill Detail` | Candidate profile with skills, source, status |
| **Resume** | `Resume Skill`, `Resume Experience`, `Resume Education`, `Resume Certification` | Parsed resume sections |
| **Candidate Ranking** | `Skill Match Detail` | Skill-by-skill match scores against a JD |
| **Interview Schedule** | `Interviewer Detail` | Interview rounds, type, interviewer panel |
| **Interview Feedback** | `Feedback Skill Rating` | Per-skill interview ratings and recommendation |
| **Offer Management** | `Offer Skill` | Offer letters with CTC, join date, status |
| **Job Portal Search** | `Portal Search Result` | Portal search runs and per-portal results |
| **Job Portal Config** | `Portal Notification Recipient` | Single: portal API keys, auto-search, thresholds |
| **Recruitment Settings** | — | Single: parsing, dedupe, notifications, rate limits |
| **Email Template Config** | — | Reusable email templates (invitation, offer, rejection) |
| **Skill** | — | Skill master with category |
| **Department** | — | Departments (synced from ERPNext) |
| **Candidate Activity Log** | — | Audit trail per candidate |
| **Candidate Timeline** | — | Timeline events per candidate |
| **Search History** | — | Saved portal search queries |
| **Search Filters** | — | Saved filter presets |

---

## Reports (11)

Candidate Match Report · JD Analysis Report · Recruitment Dashboard Report · Hiring Funnel Report · Candidate Source Report · Recruiter Performance Report · Interview Performance Report · Offer Acceptance Report · Skill Gap Analysis Report · Time-to-Hire Report · Recruitment Analytics Report

All are Script Reports with `.py` controllers **and** `.js` filter definitions — open them from **Reports & Analytics** in the workspace.

---

## Workflow: Candidate Evaluation

Applies to **Candidate Ranking**:

```
Pending ──Evaluate──▶ Evaluated ──Shortlist──▶ Shortlisted ──Schedule Interview──▶ Interview Scheduled
   │                      │                        │                                  │
   │                      ├──Reject──▶ Rejected    ├──Reject──▶ Rejected              ├──Reject──▶ Rejected
   └──Reject──▶ Rejected  └──On Hold──▶ On Hold    ├──On Hold──▶ On Hold              ├──On Hold──▶ On Hold
                                                     ├──Hire──▶ Selected               └──Hire──▶ Selected
                                                     └──Re-evaluate──▶ Evaluated
```

The 7 **Workflow States** (Pending, Evaluated, Shortlisted, Interview Scheduled, Rejected, On Hold, Selected) and 7 **Workflow Action Masters** (Evaluate, Shortlist, Reject, Schedule Interview, Put on Hold, Re-evaluate, Hire) are seeded automatically on install/migrate.

---

## Step-by-Step Workflow: From JD to Hire

This is the complete end-to-end hiring flow in HR Master — what you click in the portal, and exactly what happens in the backend at each step.

### 0. Setup (one time)

1. **Install & assign roles** — after `bench migrate`, assign the four HR Master roles to your users: **Admin** (everything), **Recruiter** (create JDs, search, rank), **Hiring Manager** (view, schedule interviews, submit feedback), **Viewer** (read-only).
2. **Optional: enable AI** — Desk → **Recruitment Settings → AI Configuration**: pick a provider (Gemini free / Groq free / OpenAI / DeepSeek / local Ollama), paste the API key, tick *Enable AI Features*. Without this, all AI tools still work but fall back to rule-based suggestions (see *Ask Me* below).
3. **Review Job Portal Config** — Remotive + Arbeitnow are enabled and free by default; add a SerpAPI or Adzuna key for more live data if you want it.

### 1. Create a Job Description

- In the portal: **Job Descriptions → New JD** (or create one in Desk).
- Fill in the title, department, employment type, location, experience range, salary range, required/preferred skills, and the description text.
- **Behind the scenes:** `create_jd()` builds and *submits* the Job Description (status → *Open*). Required/Preferred skills are stored as child rows (`JD Skill Detail`) and any new skills are auto-created in the Skill master.

### 2. (Optional) Prepare with Ask Me

The **✨ Ask Me** panel helps before you search: Suggest Skills, Interview Questions, JD Summary, Screening Questions, Search Keywords, Salary Range — or just type any question into the chat box. With AI configured these are generated by your provider; without it they are rule-based but still useful.

### 3. Search Portals

- Click **🔎 Search Portals** on the JD page.
- **Behind the scenes:** a `Job Portal Search` record is created (*Queued*) and a background job (`process_candidate_search`) calls each enabled portal; every result is stored as a `Portal Search Result` row with its source, title, company, location, skills summary and experience.
- The page **auto-refreshes** when the job finishes (per-portal counts appear on the JD page). See *Portal Search Sources* below for which portals actually return data.

### 4. Review the Results

- Open **Search History → View** (or the ranked results page).
- Each result shows a **match %** (weighted skill overlap + experience range vs the JD) with ✓ matched / ✗ missing skills.
- Click a candidate name: if it's already imported the full **Candidate profile** opens; otherwise a **preview page** with an **Import** button.

### 5. Import Candidates

- Click **Import All** or **Import** on a single result.
- **Behind the scenes:** `import_result_to_candidate()` creates a `Candidate` (status *New*), stores the skills summary, and parses it into structured `Candidate Skill Detail` rows — this is exactly what the ranking engine scores.

### 6. Rank Candidates

- Click **📊 Rank Candidates** on the JD page.
- **Behind the scenes:** every candidate is scored against the JD:
  - **Skill match (60%)** — weighted by importance (Required ×3 / Preferred ×2 / Good to Have ×1), adjusted for proficiency and years of experience, with a penalty for missing required skills; each skill is recorded in `Skill Match Detail`.
  - **Experience match (25%)** — how the candidate's total years compare with the JD's min/max range.
  - **Education match (15%)** — against the JD's education requirement.
  - A `Candidate Ranking` is created/updated (status *Evaluated*) with a recommendation (**Strong Yes → Strong No**), the per-skill breakdown, and the candidate's `total_match_score` is updated.

### 7. Workflow: Evaluate → Shortlist → Reject / Hold / Hire

On the results page (and the candidate page's **Actions ▾** menu) you can advance each ranking:

- **Evaluate** → Evaluated · **Shortlist** → Shortlisted · **Reject** → Rejected · **Put on Hold** → On Hold · **Hire** → Selected (available from Shortlisted / Interview Scheduled)
- **Behind the scenes:** `set_ranking_status()` applies the *Candidate Evaluation* workflow using Frappe v15's `frappe.model.workflow` and falls back to a direct state change so the portal never blocks an action. **Hiring also flips the linked Candidate's status → Selected**, which updates the Hired Candidates KPI, reports, and the *Candidate Hired* notification.

### 8. Interviews & Feedback

- **📅 Schedule Interview** (candidate page) → creates an `Interview Schedule` (round, type, mode, panel) and moves the ranking to *Interview Scheduled*.
- **✓ Submit Feedback** after the interview → an `Interview Feedback` with technical / communication / cultural-fit / problem-solving scores, strengths, weaknesses, and a Hire / No recommendation.

### 9. Offers

- **💌 Create Offer** (candidate page) → an `Offer Management` draft with base salary, variable pay (Total CTC is auto-computed), and benefits.
- Status lifecycle: **Draft → Approval Pending → Approved → Offer Sent → Accepted / Declined**.
- When the offer is **Accepted**, the candidate is automatically marked **Selected** and the *Offer Accepted* activity is logged — the time-to-hire and offer-acceptance reports pick it up.

### 10. Reporting & Dashboards

- The **dashboard** shows live KPIs (total candidates, active JDs, shortlists, interviews scheduled, offers released/accepted, hires, average match score) with count-up animations and click-throughs.
- **11 script reports** cover candidate match, hiring funnel, skill gaps, time-to-hire, offer acceptance, candidate sources, recruiter/interview performance, JD analysis, and a recruitment dashboard.
- **Notifications** fire on key events: candidate ranked/shortlisted/hired, interview scheduled, feedback submitted, offer generated/accepted, resume uploaded.

### 11. Ongoing Automation

- **Hourly** — auto-rank pending candidates, process pending search results
- **Daily** — auto-search portals, update JD statuses
- **Daily long** — archive old searches, process pending resumes
- **Cron** — report generation, duplicate scans, AI ranking, search-index rebuild, email queue

### Portal Search Sources

| Source | Returns data? | Key needed | Notes |
|---|---|---|---|
| **Remotive** | ✅ Live | None (free) | Remote-jobs feed, keyword-matched to the JD |
| **Arbeitnow** | ✅ Live | None (free) | Job-board feed, keyword-matched to the JD |
| **SerpAPI (Google Jobs)** | ✅ Live | API key | Real listings; free tier ~100 searches/month |
| **Adzuna** | ✅ Live | App ID + key | Real listings; free tier ~500 requests/day |
| **Demo** | ✅ Sample | None | Built-in sample candidates — perfect for trying the full pipeline with zero keys |
| **LinkedIn** | ❌ Placeholder | — | No public People Search API (requires approved Talent Solutions contract) |
| **Naukri / Monster** | ❌ Placeholder | — | No public API |
| **Indeed** | ⚠ Legacy only | Publisher ID | Free Publisher API retired; works only with IDs created before the shutdown |

---

## REST API (whitelisted methods)

All endpoints are `frappe.whitelist()` and can be called via `/api/method/hr_master.api.*` (a few are rate-limited via `hr_master.security.rate_limiter`). The portal pages call these server-side; Desk client scripts call them via `frappe.call`.

| Module | Method | Purpose |
|---|---|---|
| `candidate_api` | `parse_resume(candidate_name, file_url)` | Parse resume file → text + extracted skills |
| `candidate_api` | `get_candidate_details(candidate_name)` | Candidate + rankings + interviews |
| `candidate_api` | `bulk_update_candidate_status(candidates, status)` | Bulk status update |
| `jd_api` | `parse_skills_from_jd(jd_text)` | Extract skills from JD text |
| `jd_api` | `analyze_jd_complexity(jd_name)` | Completeness score + coverage flags |
| `jd_api` | `suggest_skills_for_jd(jd_name)` | Related skills by category |
| `ranking_api` | `rank_all_candidates_for_jd(job_description_name)` | Score all candidates for a JD |
| `ranking_api` | `rank_candidates_from_search(search_name)` | Score candidates from a portal search |
| `ranking_api` | `get_candidate_ranking_summary(jd_name)` | Top-20 rankings summary |
| `search_api` | `search_candidates_for_jd(job_description_name)` | Queue a portal search (background job) |
| `search_api` | `import_search_results(search_name)` | Import results as Candidate records |
| `search_api` | `get_search_status(search_name)` | Search progress + per-portal counts |
| `portal_actions` | `set_ranking_status(ranking_name, action)` | Advance a ranking through the Candidate Evaluation workflow |
| `portal_actions` | `schedule_interview(data)` / `create_offer(data)` / `submit_feedback(data)` | Portal interview / offer / feedback actions |
| `ai_api` | `ask_ai(job_description_name, message)` / `ask_ai_about_candidate(candidate_name, message)` | Ask Me chat for a JD or candidate |
| `ai_api` | `suggest_jd_skills` / `suggest_jd_summary` / `generate_interview_questions` / `suggest_screening_questions` / `suggest_search_keywords` / `suggest_salary_range` | Ask Me one-click AI tools |

---

## Roles & Permissions

| Role | Description |
|---|---|
| HR Master Admin | Full access to all features and settings |
| HR Master Recruiter | Create JDs, run searches, rank candidates |
| HR Master Hiring Manager | View rankings, schedule interviews, submit feedback |
| HR Master Viewer | Read-only access |

---

## Scheduled Background Jobs

| Schedule | Jobs |
|---|---|
| Hourly | Auto-rank pending candidates, process pending search results |
| Daily | Auto-search portals, update JD statuses |
| Daily long | Archive old searches, process pending resumes |
| Cron | Weekly/daily report generation, duplicate scans, AI ranking, search-index rebuild, email queue |

---

## Troubleshooting

**"HR Master: synced resources - 41 imported, 29 skipped" — is the 29 a problem?**
No. The 29 skipped files are exactly the **29 DocType JSON definitions**. Frappe's native migrate step (`Updating DocTypes for hr_master`) already syncs them to the site, so `sync_all_resources` skips re-importing them to avoid clobbering site-level changes. `41 imported + 29 skipped = 70` = every JSON fixture in the app.

**Popup: "Workflow State Evaluated not found / The resource you are looking for is not available"**
The Candidate Evaluation workflow's child rows link to standalone **Workflow State** / **Workflow Action Master** records, which fixture imports do not create. Fix: ensure you're on the latest code and run migrate — the `create_workflow_masters` phase seeds them (look for `HR Master: workflow masters ready`). Immediate repair without migrate:
```bash
bench --site your-site.com execute hr_master.hr_master.setup.install.create_workflow_masters
```

**Number card shows "Unknown column 'None'"**
An old fixture referenced invented field names. Re-run `bench --site your-site.com migrate` after pulling the latest code to refresh the Number Card fixtures.

**"Module HR Master not found" / "No module named 'hr_master.hr_master'"?**
The module folder must exist as `hr_master/hr_master/hr_master/` (package → module). Pull the latest code and run `bench --site your-site.com migrate`.

**Child tables (Skill Match Detail, Resume Skill, etc.) missing / shown as orphaned**
Re-run `bench --site your-site.com migrate` — `sync_all_resources` imports every child-table JSON file in each doctype directory.

After any fix: hard-refresh the browser (**Ctrl+Shift+R**) — some Desk errors are cached per page load.

---

## License

MIT
