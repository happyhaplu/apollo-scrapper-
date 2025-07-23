"""
Simple synchronous scraper for when Redis/Celery is not available
"""
import time
import logging
from datetime import datetime
from scraper import ApolloScraper
from models import ScrapingJob, Lead, DailyUsage, db
from tasks import create_csv_export
from utils import log_scraping_metrics

def scrape_apollo_sync(job_id, search_url, cookies, max_results, delay):
    """Synchronous version of the scraping task"""
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
        
        # Initialize scraper
        scraper = ApolloScraper(cookies=cookies, delay=delay)
        
        # Simple progress callback
        def update_progress(progress, scraped_leads, total_leads):
            if job:
                job.progress = progress
                job.scraped_leads = scraped_leads
                job.total_leads = total_leads
                db.session.commit()
        
        # Start scraping (limited to 100 results for sync mode)
        limited_results = min(max_results, 100)  # Limit for sync processing
        leads_data = scraper.scrape_apollo_search(
            search_url=search_url,
            max_results=limited_results,
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
        daily_usage = DailyUsage.get_today_usage()
        daily_usage.leads_scraped += saved_leads
        daily_usage.requests_made += (saved_leads // 25) + 1
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
        raise Exception(error_message)