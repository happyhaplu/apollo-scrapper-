import os
import json
import logging
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from app import app, db, celery, redis_client
from models import ScrapingJob, Lead, DailyUsage
from tasks import scrape_apollo_leads
from utils import validate_apollo_url, estimate_scraping_time
from config import Config
import uuid

@app.route('/')
def index():
    """Main page for Apollo scraper"""
    # Get daily usage stats
    daily_usage = DailyUsage.get_today_usage()
    
    # Get recent jobs
    recent_jobs = ScrapingJob.query.order_by(ScrapingJob.created_at.desc()).limit(10).all()
    
    return render_template('index.html', 
                         daily_usage=daily_usage,
                         recent_jobs=recent_jobs,
                         config=Config)

@app.route('/dashboard')
def dashboard():
    """Dashboard showing all jobs and statistics"""
    # Get all jobs
    jobs = ScrapingJob.query.order_by(ScrapingJob.created_at.desc()).all()
    
    # Get daily usage
    daily_usage = DailyUsage.get_today_usage()
    
    # Calculate statistics
    total_jobs = len(jobs)
    completed_jobs = len([j for j in jobs if j.status == 'completed'])
    failed_jobs = len([j for j in jobs if j.status == 'failed'])
    running_jobs = len([j for j in jobs if j.status in ['pending', 'running']])
    
    total_leads_scraped = sum([j.scraped_leads or 0 for j in jobs if j.status == 'completed'])
    
    stats = {
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'failed_jobs': failed_jobs,
        'running_jobs': running_jobs,
        'total_leads_scraped': total_leads_scraped,
        'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
    }
    
    return render_template('dashboard.html', 
                         jobs=jobs,
                         daily_usage=daily_usage,
                         stats=stats,
                         config=Config)

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Start a new scraping job"""
    try:
        # Get form data
        search_url = request.form.get('search_url', '').strip()
        cookies = request.form.get('cookies', '').strip()
        max_results = int(request.form.get('max_results', 1000))
        delay = int(request.form.get('delay', Config.DEFAULT_DELAY))
        
        # Validate inputs
        if not search_url:
            return jsonify({'error': 'Search URL is required'}), 400
        
        url_valid, url_message = validate_apollo_url(search_url)
        if not url_valid:
            return jsonify({'error': url_message}), 400
        
        if max_results < 1 or max_results > Config.MAX_DAILY_LEADS:
            return jsonify({'error': f'Max results must be between 1 and {Config.MAX_DAILY_LEADS}'}), 400
        
        if delay < Config.MIN_DELAY or delay > Config.MAX_DELAY:
            return jsonify({'error': f'Delay must be between {Config.MIN_DELAY} and {Config.MAX_DELAY} seconds'}), 400
        
        # Check daily limits
        daily_usage = DailyUsage.get_today_usage()
        if not daily_usage.can_scrape_more_leads(max_results):
            return jsonify({
                'error': f'Daily lead limit would be exceeded. Current: {daily_usage.leads_scraped}, Requested: {max_results}, Limit: {Config.MAX_DAILY_LEADS}'
            }), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Create job record
        job = ScrapingJob(
            task_id=task_id,
            search_url=search_url,
            delay_between_requests=delay,
            max_results=max_results,
            status='pending'
        )
        db.session.add(job)
        db.session.commit()
        
        # Start background task (with fallback to sync processing)
        try:
            from app import celery
            task = celery.send_task('tasks.scrape_apollo_leads',
                args=[job.id, search_url, cookies, max_results, delay],
                task_id=task_id
            )
        except Exception as e:
            logging.warning(f"Background processing unavailable: {str(e)}, using synchronous processing")
            # Fallback to synchronous processing for small jobs
            try:
                from simple_scraper import scrape_apollo_sync
                import threading
                
                # Run sync scraper in a separate thread to avoid blocking
                def run_sync_scraper():
                    try:
                        with app.app_context():
                            scrape_apollo_sync(job.id, search_url, cookies, min(max_results, 100), delay)
                    except Exception as sync_error:
                        logging.error(f"Sync scraper failed: {str(sync_error)}")
                        with app.app_context():
                            job_update = ScrapingJob.query.get(job.id)
                            if job_update:
                                job_update.status = 'failed'
                                job_update.error_message = str(sync_error)
                                db.session.commit()
                
                thread = threading.Thread(target=run_sync_scraper)
                thread.daemon = True
                thread.start()
                
            except Exception as sync_error:
                logging.error(f"Fallback sync processing failed: {str(sync_error)}")
                job.status = 'failed'
                job.error_message = f"Both background and sync processing failed: {str(sync_error)}"
                db.session.commit()
                return jsonify({'error': 'Scraping service is temporarily unavailable. Please try again later.'}), 503
        
        # Estimate completion time
        estimated_time = estimate_scraping_time(max_results, delay)
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'task_id': task_id,
            'estimated_time': estimated_time,
            'message': f'Scraping job started. Estimated completion time: {estimated_time}'
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid input values'}), 400
    except Exception as e:
        logging.error(f"Error starting scraping job: {str(e)}")
        return jsonify({'error': 'Failed to start scraping job'}), 500

@app.route('/job_status/<int:job_id>')
def job_status(job_id):
    """Get status of a scraping job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        
        # Get task status from Celery if job is running
        task_info = None
        if job.status in ['pending', 'running'] and job.task_id:
            try:
                task = celery.AsyncResult(job.task_id)
                task_info = {
                    'state': task.state,
                    'info': task.info
                }
            except Exception as e:
                logging.warning(f"Could not get task status: {str(e)}")
        
        response = job.to_dict()
        if task_info:
            response['task_info'] = task_info
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': 'Failed to get job status'}), 500

@app.route('/download_csv/<int:job_id>')
def download_csv(job_id):
    """Download CSV file for a completed job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        
        if job.status != 'completed' or not job.csv_file_path:
            return jsonify({'error': 'CSV file not available'}), 404
        
        csv_path = os.path.join(Config.EXPORT_FOLDER, job.csv_file_path)
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'CSV file not found'}), 404
        
        return send_file(
            csv_path,
            as_attachment=True,
            download_name=job.csv_file_path,
            mimetype='text/csv'
        )
        
    except Exception as e:
        logging.error(f"Error downloading CSV: {str(e)}")
        return jsonify({'error': 'Failed to download CSV'}), 500

@app.route('/cancel_job/<int:job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running scraping job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        
        if job.status not in ['pending', 'running']:
            return jsonify({'error': 'Job cannot be cancelled'}), 400
        
        # Revoke the Celery task
        if job.task_id:
            try:
                celery.control.revoke(job.task_id, terminate=True)
            except Exception as e:
                logging.warning(f"Could not revoke task: {str(e)}")
        
        # Update job status
        job.status = 'cancelled'
        job.error_message = 'Job cancelled by user'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Job cancelled successfully'})
        
    except Exception as e:
        logging.error(f"Error cancelling job: {str(e)}")
        return jsonify({'error': 'Failed to cancel job'}), 500

@app.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    """Delete a job and its associated data"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        
        # Delete CSV file if it exists
        if job.csv_file_path:
            csv_path = os.path.join(Config.EXPORT_FOLDER, job.csv_file_path)
            if os.path.exists(csv_path):
                os.remove(csv_path)
        
        # Delete associated leads
        Lead.query.filter_by(job_id=job.id).delete()
        
        # Delete job
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Job deleted successfully'})
        
    except Exception as e:
        logging.error(f"Error deleting job: {str(e)}")
        return jsonify({'error': 'Failed to delete job'}), 500

@app.route('/leads/<int:job_id>')
def view_leads(job_id):
    """View leads for a specific job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        leads = Lead.query.filter_by(job_id=job_id).all()
        
        leads_data = [lead.to_dict() for lead in leads]
        
        return jsonify({
            'job': job.to_dict(),
            'leads': leads_data,
            'total_leads': len(leads_data)
        })
        
    except Exception as e:
        logging.error(f"Error getting leads: {str(e)}")
        return jsonify({'error': 'Failed to get leads'}), 500

@app.route('/test_auth', methods=['POST'])
def test_authentication():
    """Test Apollo authentication with provided cookies"""
    try:
        cookies = request.form.get('cookies', '').strip()
        
        if not cookies:
            return jsonify({'error': 'Cookies are required for authentication test'}), 400
        
        from scraper import ApolloScraper
        scraper = ApolloScraper(cookies=cookies)
        
        success, message = scraper.test_authentication()
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logging.error(f"Error testing authentication: {str(e)}")
        return jsonify({'error': 'Authentication test failed'}), 500

@app.route('/daily_stats')
def daily_stats():
    """Get daily usage statistics"""
    try:
        daily_usage = DailyUsage.get_today_usage()
        
        return jsonify({
            'date': daily_usage.date.isoformat(),
            'leads_scraped': daily_usage.leads_scraped,
            'requests_made': daily_usage.requests_made,
            'jobs_completed': daily_usage.jobs_completed,
            'leads_remaining': Config.MAX_DAILY_LEADS - daily_usage.leads_scraped,
            'requests_remaining': Config.MAX_DAILY_REQUESTS - daily_usage.requests_made,
            'limits': {
                'max_daily_leads': Config.MAX_DAILY_LEADS,
                'max_daily_requests': Config.MAX_DAILY_REQUESTS
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting daily stats: {str(e)}")
        return jsonify({'error': 'Failed to get daily stats'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
