"""
Demo test to show Apollo scraper functionality without Chrome dependencies
"""
import json
from datetime import datetime
from app import app, db
from models import ScrapingJob, Lead, DailyUsage

def create_demo_job():
    """Create a demo scraping job with sample data"""
    with app.app_context():
        # Create demo job
        job = ScrapingJob(
            task_id="demo-test-12345",
            search_url="https://app.apollo.io/#/people?page=1&personTitles[]=founder%20and%20ceo",
            delay_between_requests=3,
            max_results=5,
            status='completed',
            progress=100.0,
            scraped_leads=3,
            total_leads=3,
            completed_at=datetime.utcnow(),
            csv_file_path="demo_leads.csv"
        )
        db.session.add(job)
        db.session.commit()
        
        # Create demo leads
        demo_leads = [
            {
                'job_id': job.id,
                'first_name': 'John',
                'last_name': 'Smith',
                'full_name': 'John Smith',
                'email': 'john.smith@example.com',
                'phone': '+1-555-123-4567',
                'linkedin_url': 'https://linkedin.com/in/johnsmith',
                'job_title': 'Founder & CEO',
                'seniority': 'C-Level',
                'department': 'Executive',
                'company_name': 'TechCorp Inc',
                'company_domain': 'techcorp.com',
                'company_website': 'https://techcorp.com',
                'company_industry': 'Technology',
                'company_size': '50-200',
                'company_location': 'San Francisco, CA',
                'company_linkedin': 'https://linkedin.com/company/techcorp',
                'years_experience': 10,
                'location': 'San Francisco, CA',
                'raw_data': json.dumps({'source': 'apollo_demo'})
            },
            {
                'job_id': job.id,
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'full_name': 'Sarah Johnson',
                'email': 'sarah.johnson@innovate.io',
                'phone': '+1-555-987-6543',
                'linkedin_url': 'https://linkedin.com/in/sarahjohnson',
                'job_title': 'CTO & Co-Founder',
                'seniority': 'C-Level',
                'department': 'Engineering',
                'company_name': 'InnovateLab',
                'company_domain': 'innovate.io',
                'company_website': 'https://innovate.io',
                'company_industry': 'Software',
                'company_size': '25-50',
                'company_location': 'Austin, TX',
                'company_linkedin': 'https://linkedin.com/company/innovatelab',
                'years_experience': 8,
                'location': 'Austin, TX',
                'raw_data': json.dumps({'source': 'apollo_demo'})
            },
            {
                'job_id': job.id,
                'first_name': 'Michael',
                'last_name': 'Chen',
                'full_name': 'Michael Chen',
                'email': 'michael.chen@growth.co',
                'phone': '+1-555-456-7890',
                'linkedin_url': 'https://linkedin.com/in/michaelchen',
                'job_title': 'VP of Engineering',
                'seniority': 'VP',
                'department': 'Engineering',
                'company_name': 'GrowthCo',
                'company_domain': 'growth.co',
                'company_website': 'https://growth.co',
                'company_industry': 'Marketing Technology',
                'company_size': '100-500',
                'company_location': 'New York, NY',
                'company_linkedin': 'https://linkedin.com/company/growthco',
                'years_experience': 12,
                'location': 'New York, NY',
                'raw_data': json.dumps({'source': 'apollo_demo'})
            }
        ]
        
        for lead_data in demo_leads:
            lead = Lead(**lead_data)
            db.session.add(lead)
        
        db.session.commit()
        
        # Update daily usage
        daily_usage = DailyUsage.get_today_usage()
        daily_usage.leads_scraped += 3
        daily_usage.requests_made += 1
        daily_usage.jobs_completed += 1
        db.session.commit()
        
        print(f"Demo job created with ID: {job.id}")
        return job.id

if __name__ == '__main__':
    job_id = create_demo_job()
    print(f"Demo data created successfully! Job ID: {job_id}")