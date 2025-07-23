import os
import csv
import json
import logging
from datetime import datetime
from celery import current_task
from app import celery, db
from models import ScrapingJob, Lead, DailyUsage
from scraper import ApolloScraper
from utils import sanitize_filename, log_scraping_metrics
from config import Config

@celery.task(bind=True)
def scrape_apollo_leads(self, job_id, search_url, cookies, max_results, delay):
    """Background task to scrape Apollo leads"""
    
    def update_progress(progress, scraped_leads, total_leads):
        """Update job progress in database"""
        try:
            job = ScrapingJob.query.get(job_id)
            if job:
                job.progress = progress
                job.scraped_leads = scraped_leads
                job.total_leads = total_leads
                job.status = 'running'
                db.session.commit()
                
                # Update task state
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': progress,
                        'scraped_leads': scraped_leads,
                        'total_leads': total_leads,
                        'status': 'running'
                    }
                )
        except Exception as e:
            logging.error(f"Error updating progress: {str(e)}")
    
    try:
        # Get job from database
        job = ScrapingJob.query.get(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")
        
        # Update job status
        job.status = 'running'
        db.session.commit()
        
        log_scraping_metrics(job_id, 'job_started', {
            'search_url': search_url,
            'max_results': max_results,
            'delay': delay
        })
        
        # Check daily limits
        daily_usage = DailyUsage.get_today_usage()
        if not daily_usage.can_scrape_more_leads(max_results):
            raise Exception(f"Daily lead limit exceeded. Current: {daily_usage.leads_scraped}, Limit: {Config.MAX_DAILY_LEADS}")
        
        if not daily_usage.can_make_more_requests(max_results // 25):  # Estimate requests needed
            raise Exception(f"Daily request limit exceeded. Current: {daily_usage.requests_made}, Limit: {Config.MAX_DAILY_REQUESTS}")
        
        # Initialize scraper
        scraper = ApolloScraper(cookies=cookies, delay=delay)
        
        # Test authentication if cookies provided
        if cookies:
            auth_success, auth_message = scraper.test_authentication()
            if not auth_success:
                logging.warning(f"Authentication test failed: {auth_message}")
        
        # Start scraping
        leads_data = scraper.scrape_apollo_search(
            search_url=search_url,
            max_results=max_results,
            progress_callback=update_progress
        )
        
        if not leads_data:
            raise Exception("No leads were scraped")
        
        # Save leads to database
        saved_leads = 0
        for lead_data in leads_data:
            try:
                lead = Lead(
                    job_id=job_id,
                    first_name=lead_data.get('first_name', ''),
                    last_name=lead_data.get('last_name', ''),
                    full_name=lead_data.get('full_name', ''),
                    email=lead_data.get('email', ''),
                    phone=lead_data.get('phone', ''),
                    linkedin_url=lead_data.get('linkedin_url', ''),
                    job_title=lead_data.get('job_title', ''),
                    seniority=lead_data.get('seniority', ''),
                    department=lead_data.get('department', ''),
                    company_name=lead_data.get('company_name', ''),
                    company_domain=lead_data.get('company_domain', ''),
                    company_website=lead_data.get('company_website', ''),
                    company_industry=lead_data.get('company_industry', ''),
                    company_size=lead_data.get('company_size', ''),
                    company_location=lead_data.get('company_location', ''),
                    company_linkedin=lead_data.get('company_linkedin', ''),
                    years_experience=lead_data.get('years_experience', 0),
                    location=lead_data.get('location', ''),
                    raw_data=lead_data.get('raw_data', '')
                )
                db.session.add(lead)
                saved_leads += 1
            except Exception as e:
                logging.error(f"Error saving lead: {str(e)}")
                continue
        
        db.session.commit()
        
        # Create CSV export
        csv_filename = create_csv_export(job_id, leads_data)
        
        # Update job with results
        job.status = 'completed'
        job.scraped_leads = saved_leads
        job.total_leads = len(leads_data)
        job.progress = 100.0
        job.completed_at = datetime.utcnow()
        job.csv_file_path = csv_filename
        db.session.commit()
        
        # Update daily usage
        daily_usage.leads_scraped += saved_leads
        daily_usage.requests_made += (saved_leads // 25) + 1  # Estimate requests made
        daily_usage.jobs_completed += 1
        db.session.commit()
        
        log_scraping_metrics(job_id, 'job_completed', {
            'total_leads': saved_leads,
            'csv_file': csv_filename
        })
        
        return {
            'status': 'completed',
            'scraped_leads': saved_leads,
            'total_leads': len(leads_data),
            'csv_file': csv_filename,
            'message': f'Successfully scraped {saved_leads} leads'
        }
        
    except Exception as e:
        error_message = str(e)
        logging.error(f"Job {job_id} failed: {error_message}")
        
        # Update job with error
        try:
            job = ScrapingJob.query.get(job_id)
            if job:
                job.status = 'failed'
                job.error_message = error_message
                db.session.commit()
        except:
            pass
        
        log_scraping_metrics(job_id, 'job_failed', {'error': error_message})
        
        # Update task state
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': error_message,
                'status': 'failed'
            }
        )
        
        raise Exception(error_message)

def create_csv_export(job_id, leads_data):
    """Create CSV file with lead data"""
    try:
        # Ensure export directory exists
        os.makedirs(Config.EXPORT_FOLDER, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"apollo_leads_job_{job_id}_{timestamp}.csv"
        filename = sanitize_filename(filename)
        csv_path = os.path.join(Config.EXPORT_FOLDER, filename)
        
        # CSV headers
        headers = [
            'First Name', 'Last Name', 'Full Name', 'Email', 'Phone',
            'LinkedIn URL', 'Job Title', 'Seniority', 'Department',
            'Company Name', 'Company Domain', 'Company Website',
            'Company Industry', 'Company Size', 'Company Location',
            'Company LinkedIn', 'Years Experience', 'Location', 'Scraped At'
        ]
        
        # Write CSV file
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for lead in leads_data:
                row = [
                    lead.get('first_name', ''),
                    lead.get('last_name', ''),
                    lead.get('full_name', ''),
                    lead.get('email', ''),
                    lead.get('phone', ''),
                    lead.get('linkedin_url', ''),
                    lead.get('job_title', ''),
                    lead.get('seniority', ''),
                    lead.get('department', ''),
                    lead.get('company_name', ''),
                    lead.get('company_domain', ''),
                    lead.get('company_website', ''),
                    lead.get('company_industry', ''),
                    lead.get('company_size', ''),
                    lead.get('company_location', ''),
                    lead.get('company_linkedin', ''),
                    lead.get('years_experience', 0),
                    lead.get('location', ''),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
                writer.writerow(row)
        
        logging.info(f"CSV export created: {csv_path}")
        return filename
        
    except Exception as e:
        logging.error(f"Error creating CSV export: {str(e)}")
        return None

@celery.task
def cleanup_old_jobs():
    """Clean up old completed jobs and files"""
    try:
        from datetime import timedelta
        
        # Delete jobs older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        old_jobs = ScrapingJob.query.filter(
            ScrapingJob.created_at < cutoff_date,
            ScrapingJob.status.in_(['completed', 'failed'])
        ).all()
        
        for job in old_jobs:
            # Delete CSV file if it exists
            if job.csv_file_path:
                csv_path = os.path.join(Config.EXPORT_FOLDER, job.csv_file_path)
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                    logging.info(f"Deleted old CSV file: {csv_path}")
            
            # Delete leads associated with job
            Lead.query.filter_by(job_id=job.id).delete()
            
            # Delete job
            db.session.delete(job)
        
        db.session.commit()
        logging.info(f"Cleaned up {len(old_jobs)} old jobs")
        
    except Exception as e:
        logging.error(f"Error during cleanup: {str(e)}")
