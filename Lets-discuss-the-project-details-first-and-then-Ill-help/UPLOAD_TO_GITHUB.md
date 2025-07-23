# Files to Upload to GitHub for Apollo Lead Scraper

## Required Files for Deployment

### Core Application Files
- `main.py` - Entry point for deployment
- `app.py` - Flask application setup
- `models.py` - Database models (ScrapingJob, Lead, DailyUsage)
- `routes.py` - Web interface and API endpoints
- `scraper.py` - Apollo.io scraping engine
- `tasks.py` - Background job processing
- `utils.py` - Helper functions
- `config.py` - Application configuration

### Deployment Configuration Files
- `render.yaml` - Render deployment (FREE TIER)
- `railway.json` - Railway deployment 
- `nixpacks.toml` - Railway build configuration
- `Procfile` - Heroku deployment
- `app.json` - Heroku app configuration
- `runtime.txt` - Python version specification
- `pyproject.toml` - Python dependencies (REQUIRED)

### Frontend Files
- `templates/` folder with all HTML files:
  - `base.html`
  - `index.html` 
  - `dashboard.html`
  - `404.html`
  - `500.html`
- `static/` folder with CSS/JS files

### Database & Instance
- `instance/apollo_scraper.db` - Demo database with 3 sample leads

### Documentation
- `README.md` - Project documentation
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `.gitignore` - Git ignore file

## Upload Priority (Essential Files First)

### MUST HAVE (Critical for deployment):
1. `main.py`
2. `app.py` 
3. `pyproject.toml`
4. `render.yaml`
5. `templates/` folder
6. `models.py`
7. `routes.py`
8. `scraper.py`

### SHOULD HAVE (For full functionality):
- All other Python files
- `static/` folder
- `instance/apollo_scraper.db` (demo data)
- Documentation files

## File Structure in GitHub Repository:
```
apollo-lead-scraper/
├── main.py
├── app.py
├── models.py
├── routes.py
├── scraper.py
├── tasks.py
├── utils.py
├── config.py
├── pyproject.toml
├── render.yaml
├── railway.json
├── nixpacks.toml
├── Procfile
├── app.json
├── runtime.txt
├── README.md
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── 404.html
│   └── 500.html
├── static/
│   ├── css/
│   └── js/
└── instance/
    └── apollo_scraper.db
```