"""Built-in Job Description templates for HR Master.

Each template pre-fills the portal's "New Job Description" form (reviewed by
the user before submission) so common roles can be posted in one click.
"""

from __future__ import unicode_literals

TEMPLATES = [
    {
        "key": "backend_python",
        "title": "Backend Developer (Python)",
        "job_title": "Backend Developer",
        "employment_type": "Full-Time",
        "location": "Bengaluru",
        "remote_option": "Hybrid",
        "min_experience_years": 3,
        "max_experience_years": 7,
        "salary_range_min": 1800000,
        "salary_range_max": 3500000,
        "vacancies": 2,
        "required_skills": ["Python", "Django", "SQL", "REST APIs"],
        "preferred_skills": ["PostgreSQL", "Redis", "Docker", "AWS"],
        "qualifications": "Bachelor's in Computer Science or related field; 3+ years building backend services at scale.",
        "job_description_raw": (
            "We are looking for a Backend Developer to design, build and maintain "
            "scalable server-side services and APIs. You will own features end-to-end, "
            "write clean maintainable code, and collaborate closely with frontend and "
            "product teams.\n\n"
            "Responsibilities:\n"
            "- Design and implement REST APIs and background jobs in Python (Django)\n"
            "- Optimize database queries and system performance\n"
            "- Write unit tests and participate in code reviews\n"
            "- Deploy and monitor services in a cloud environment\n\n"
            "Requirements:\n"
            "- Strong Python and SQL skills, solid understanding of data structures\n"
            "- Experience with version control (Git) and agile workflows\n"
            "- Good communication and problem-solving skills"
        ),
    },
    {
        "key": "frontend_react",
        "title": "Frontend Developer (React)",
        "job_title": "Frontend Developer",
        "employment_type": "Full-Time",
        "location": "Remote",
        "remote_option": "Remote",
        "min_experience_years": 2,
        "max_experience_years": 6,
        "salary_range_min": 1500000,
        "salary_range_max": 3000000,
        "vacancies": 2,
        "required_skills": ["JavaScript", "React", "TypeScript", "HTML", "CSS"],
        "preferred_skills": ["Next.js", "Redux", "Tailwind CSS", "Jest"],
        "qualifications": "Portfolio of shipped web applications; 2+ years with modern frontend frameworks.",
        "job_description_raw": (
            "We are hiring a Frontend Developer to build fast, accessible and delightful "
            "web interfaces. You will work on user-facing products used by thousands of "
            "people every day.\n\n"
            "Responsibilities:\n"
            "- Build reusable React components and page-level features\n"
            "- Translate designs into pixel-perfect, responsive UIs\n"
            "- Improve performance, accessibility and test coverage\n\n"
            "Requirements:\n"
            "- Strong JavaScript/TypeScript and React experience\n"
            "- Solid understanding of the browser and web performance\n"
            "- An eye for detail and clean component architecture"
        ),
    },
    {
        "key": "fullstack",
        "title": "Full Stack Developer",
        "job_title": "Full Stack Developer",
        "employment_type": "Full-Time",
        "location": "Hyderabad",
        "remote_option": "Hybrid",
        "min_experience_years": 3,
        "max_experience_years": 8,
        "salary_range_min": 2000000,
        "salary_range_max": 4000000,
        "vacancies": 3,
        "required_skills": ["JavaScript", "Python", "React", "Node.js", "SQL"],
        "preferred_skills": ["Django", "PostgreSQL", "Docker", "AWS", "Redis"],
        "qualifications": "3+ years building full-stack products end-to-end.",
        "job_description_raw": (
            "We are looking for a Full Stack Developer who enjoys owning features from "
            "database schema to polished UI. You will ship fast in a small, senior team.\n\n"
            "Responsibilities:\n"
            "- Build and maintain APIs (Python/Node.js) and frontend interfaces (React)\n"
            "- Design data models and write efficient queries\n"
            "- Deploy, monitor and troubleshoot production services\n\n"
            "Requirements:\n"
            "- Proven full-stack delivery experience\n"
            "- Comfortable across the stack: JS, Python, SQL and cloud\n"
            "- Strong ownership and communication skills"
        ),
    },
    {
        "key": "data_scientist",
        "title": "Data Scientist",
        "job_title": "Data Scientist",
        "employment_type": "Full-Time",
        "location": "Bengaluru",
        "remote_option": "On-site",
        "min_experience_years": 3,
        "max_experience_years": 8,
        "salary_range_min": 2200000,
        "salary_range_max": 4500000,
        "vacancies": 1,
        "required_skills": ["Python", "Machine Learning", "Statistics", "SQL"],
        "preferred_skills": ["TensorFlow", "PyTorch", "Pandas", "Airflow"],
        "qualifications": "MS/PhD in a quantitative field or equivalent experience.",
        "job_description_raw": (
            "We are hiring a Data Scientist to turn messy data into models that drive "
            "real business decisions — from recommendations to forecasting.\n\n"
            "Responsibilities:\n"
            "- Build and evaluate ML models and A/B experiments\n"
            "- Own end-to-end data pipelines and feature engineering\n"
            "- Communicate findings clearly to non-technical stakeholders\n\n"
            "Requirements:\n"
            "- Strong Python, statistics and SQL fundamentals\n"
            "- Production ML experience is a plus\n"
            "- Curiosity and a rigorous, data-driven mindset"
        ),
    },
    {
        "key": "devops",
        "title": "DevOps Engineer",
        "job_title": "DevOps Engineer",
        "employment_type": "Full-Time",
        "location": "Remote",
        "remote_option": "Remote",
        "min_experience_years": 3,
        "max_experience_years": 8,
        "salary_range_min": 2000000,
        "salary_range_max": 3800000,
        "vacancies": 1,
        "required_skills": ["AWS", "Docker", "Kubernetes", "CI/CD", "Terraform"],
        "preferred_skills": ["Linux", "Python", "Prometheus", "Grafana", "Helm"],
        "qualifications": "3+ years in cloud infrastructure and automation.",
        "job_description_raw": (
            "We are looking for a DevOps Engineer to build reliable, secure and "
            "automated cloud infrastructure that our engineering teams love.\n\n"
            "Responsibilities:\n"
            "- Manage AWS infrastructure with IaC (Terraform)\n"
            "- Maintain Kubernetes clusters and CI/CD pipelines\n"
            "- Monitor systems, improve reliability and cut costs\n\n"
            "Requirements:\n"
            "- Deep AWS, Docker and Kubernetes experience\n"
            "- Strong scripting/automation skills\n"
            "- Calm, methodical incident response"
        ),
    },
    {
        "key": "product_manager",
        "title": "Product Manager",
        "job_title": "Product Manager",
        "employment_type": "Full-Time",
        "location": "Mumbai",
        "remote_option": "Hybrid",
        "min_experience_years": 4,
        "max_experience_years": 9,
        "salary_range_min": 2500000,
        "salary_range_max": 4500000,
        "vacancies": 1,
        "required_skills": ["Product Strategy", "Roadmapping", "Analytics", "User Research"],
        "preferred_skills": ["SQL", "Figma", "Agile", "OKRs"],
        "qualifications": "4+ years as a product manager shipping software products.",
        "job_description_raw": (
            "We are hiring a Product Manager to own the roadmap for a growing SaaS "
            "product — from customer discovery to launch and iteration.\n\n"
            "Responsibilities:\n"
            "- Define vision, strategy and quarterly roadmaps\n"
            "- Run discovery, prioritize ruthlessly and write clear specs\n"
            "- Partner with design and engineering to ship high-quality releases\n\n"
            "Requirements:\n"
            "- Strong analytical and communication skills\n"
            "- Data-informed decision making (SQL a plus)\n"
            "- Empathy for users and a bias for action"
        ),
    },
    {
        "key": "ux_designer",
        "title": "UI/UX Designer",
        "job_title": "UI/UX Designer",
        "employment_type": "Full-Time",
        "location": "Remote",
        "remote_option": "Remote",
        "min_experience_years": 2,
        "max_experience_years": 6,
        "salary_range_min": 1200000,
        "salary_range_max": 2500000,
        "vacancies": 1,
        "required_skills": ["Figma", "UI Design", "UX Research", "Prototyping"],
        "preferred_skills": ["Design Systems", "HTML", "CSS", "Motion Design"],
        "qualifications": "Strong portfolio demonstrating end-to-end product design.",
        "job_description_raw": (
            "We are looking for a UI/UX Designer to craft intuitive, beautiful "
            "experiences across our web product.\n\n"
            "Responsibilities:\n"
            "- Design flows, wireframes and high-fidelity prototypes in Figma\n"
            "- Maintain and evolve our design system\n"
            "- Run usability tests and iterate with real feedback\n\n"
            "Requirements:\n"
            "- Portfolio with shipped or launched work\n"
            "- Excellent visual and interaction design skills\n"
            "- Collaborative, feedback-positive mindset"
        ),
    },
    {
        "key": "sales_executive",
        "title": "Sales Executive (B2B)",
        "job_title": "Sales Executive",
        "employment_type": "Full-Time",
        "location": "Delhi",
        "remote_option": "On-site",
        "min_experience_years": 2,
        "max_experience_years": 7,
        "salary_range_min": 800000,
        "salary_range_max": 1800000,
        "vacancies": 3,
        "required_skills": ["B2B Sales", "Negotiation", "CRM", "Communication"],
        "preferred_skills": ["Salesforce", "Lead Generation", "Cold Outreach"],
        "qualifications": "2+ years in B2B sales with a track record of closing deals.",
        "job_description_raw": (
            "We are hiring a Sales Executive to grow our enterprise pipeline and "
            "close new business in the region.\n\n"
            "Responsibilities:\n"
            "- Prospect, qualify and nurture leads through the pipeline\n"
            "- Run demos and negotiate commercial terms\n"
            "- Maintain accurate CRM hygiene and forecasts\n\n"
            "Requirements:\n"
            "- Proven B2B closing experience\n"
            "- Strong communication and relationship skills\n"
            "- Self-starter comfortable with targets"
        ),
    },
    {
        "key": "qa_engineer",
        "title": "QA / Test Engineer",
        "job_title": "QA Engineer",
        "employment_type": "Full-Time",
        "location": "Pune",
        "remote_option": "Hybrid",
        "min_experience_years": 2,
        "max_experience_years": 6,
        "salary_range_min": 900000,
        "salary_range_max": 1800000,
        "vacancies": 2,
        "required_skills": ["Manual Testing", "Test Cases", "API Testing", "Bug Tracking"],
        "preferred_skills": ["Selenium", "Python", "Cypress", "JMeter"],
        "qualifications": "2+ years in software quality assurance.",
        "job_description_raw": (
            "We are looking for a QA Engineer to own quality across our web "
            "applications — manual and automated.\n\n"
            "Responsibilities:\n"
            "- Design and execute test plans and test cases\n"
            "- Automate critical regression flows\n"
            "- Report, track and verify defects to closure\n\n"
            "Requirements:\n"
            "- Strong understanding of QA processes and testing types\n"
            "- API testing experience\n"
            "- Automation skills (Selenium/Cypress) are a plus"
        ),
    },
]


def get_templates():
    """Return the list of built-in JD templates (public API for the portal)."""
    return TEMPLATES
