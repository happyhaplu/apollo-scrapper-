from app import db
from datetime import datetime, date
import json

class ScrapingJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False)
    search_url = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    total_leads = db.Column(db.Integer, default=0)
    scraped_leads = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    error_message = db.Column(db.Text)
    csv_file_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Rate limiting settings for this job
    delay_between_requests = db.Column(db.Integer, default=10)
    max_results = db.Column(db.Integer, default=1000)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'search_url': self.search_url,
            'status': self.status,
            'total_leads': self.total_leads,
            'scraped_leads': self.scraped_leads,
            'progress': self.progress,
            'error_message': self.error_message,
            'csv_file_path': self.csv_file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'delay_between_requests': self.delay_between_requests,
            'max_results': self.max_results
        }

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_job.id'), nullable=False)
    
    # Personal information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    full_name = db.Column(db.String(200))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    linkedin_url = db.Column(db.String(500))
    
    # Job information
    job_title = db.Column(db.String(200))
    seniority = db.Column(db.String(100))
    department = db.Column(db.String(100))
    
    # Company information
    company_name = db.Column(db.String(200))
    company_domain = db.Column(db.String(200))
    company_website = db.Column(db.String(500))
    company_industry = db.Column(db.String(200))
    company_size = db.Column(db.String(100))
    company_location = db.Column(db.String(200))
    company_linkedin = db.Column(db.String(500))
    
    # Additional data
    years_experience = db.Column(db.Integer)
    location = db.Column(db.String(200))
    raw_data = db.Column(db.Text)  # Store original scraped data as JSON
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    job = db.relationship('ScrapingJob', backref=db.backref('leads', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'linkedin_url': self.linkedin_url,
            'job_title': self.job_title,
            'seniority': self.seniority,
            'department': self.department,
            'company_name': self.company_name,
            'company_domain': self.company_domain,
            'company_website': self.company_website,
            'company_industry': self.company_industry,
            'company_size': self.company_size,
            'company_location': self.company_location,
            'company_linkedin': self.company_linkedin,
            'years_experience': self.years_experience,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DailyUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=date.today, unique=True)
    leads_scraped = db.Column(db.Integer, default=0)
    requests_made = db.Column(db.Integer, default=0)
    jobs_completed = db.Column(db.Integer, default=0)
    
    @classmethod
    def get_today_usage(cls):
        today = date.today()
        usage = cls.query.filter_by(date=today).first()
        if not usage:
            usage = cls(date=today)
            db.session.add(usage)
            db.session.commit()
        return usage
    
    def can_scrape_more_leads(self, additional_leads=0):
        from config import Config
        return (self.leads_scraped + additional_leads) <= Config.MAX_DAILY_LEADS
    
    def can_make_more_requests(self, additional_requests=0):
        from config import Config
        return (self.requests_made + additional_requests) <= Config.MAX_DAILY_REQUESTS
