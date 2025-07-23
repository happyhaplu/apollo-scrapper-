import re
import json
import random
import time
from urllib.parse import urlparse, parse_qs
import logging
from config import Config

def validate_apollo_url(url):
    """Validate if the URL is a valid Apollo.io search URL"""
    try:
        parsed = urlparse(url)
        if 'apollo.io' not in parsed.netloc:
            return False, "URL must be from apollo.io domain"
        
        if '#/people' not in url and '/people' not in url:
            return False, "URL must be an Apollo people search URL"
        
        return True, "Valid Apollo search URL"
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

def extract_search_params(url):
    """Extract search parameters from Apollo URL"""
    try:
        # Apollo uses hash-based routing, so we need to parse the hash part
        if '#' in url:
            hash_part = url.split('#')[1]
            if '?' in hash_part:
                query_part = hash_part.split('?')[1]
                # Parse the query parameters
                params = {}
                for param in query_part.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
                return params
        return {}
    except Exception as e:
        logging.error(f"Error extracting search params: {str(e)}")
        return {}

def clean_text(text):
    """Clean extracted text data"""
    if not text:
        return ""
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', str(text).strip())
    
    # Remove common unwanted characters
    text = re.sub(r'[^\w\s@.,-]', '', text)
    
    return text

def extract_email(text):
    """Extract email from text using regex"""
    if not text:
        return ""
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""

def extract_phone(text):
    """Extract phone number from text"""
    if not text:
        return ""
    
    # Common phone patterns
    phone_patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\(\d{3}\)\s?\d{3}-\d{4}'
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return ""

def extract_linkedin_url(text):
    """Extract LinkedIn URL from text"""
    if not text:
        return ""
    
    linkedin_pattern = r'https?://[a-z]*\.?linkedin\.com/in/[a-zA-Z0-9-]+'
    match = re.search(linkedin_pattern, text)
    return match.group(0) if match else ""

def calculate_smart_delay(base_delay=None, error_count=0, success_count=0):
    """Calculate smart delay based on success/error rates"""
    if base_delay is None:
        base_delay = Config.DEFAULT_DELAY
    
    # Increase delay if we're getting errors
    if error_count > success_count:
        delay = min(base_delay * (1 + error_count * 0.1), Config.MAX_DELAY)
    else:
        # Decrease delay if we're successful
        delay = max(base_delay * (1 - success_count * 0.05), Config.MIN_DELAY)
    
    # Add some randomness to avoid pattern detection
    jitter = random.uniform(0.8, 1.2)
    delay = delay * jitter
    
    return max(Config.MIN_DELAY, min(delay, Config.MAX_DELAY))

def format_company_size(size_text):
    """Format company size text to standardized format"""
    if not size_text:
        return ""
    
    size_text = size_text.lower().strip()
    
    size_mappings = {
        '1-10': 'Small (1-10)',
        '11-50': 'Small (11-50)',
        '51-200': 'Medium (51-200)',
        '201-500': 'Medium (201-500)',
        '501-1000': 'Large (501-1000)',
        '1001-5000': 'Large (1001-5000)',
        '5001-10000': 'Enterprise (5001-10000)',
        '10000+': 'Enterprise (10000+)'
    }
    
    for size_range, formatted in size_mappings.items():
        if size_range.replace('-', ' to ') in size_text or size_range in size_text:
            return formatted
    
    return size_text.title()

def sanitize_filename(filename):
    """Sanitize filename for safe file creation"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('._')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def parse_apollo_cookies(cookies_string):
    """Parse Apollo cookies from string format"""
    try:
        if isinstance(cookies_string, str):
            # Try to parse as JSON first
            if cookies_string.strip().startswith('[') or cookies_string.strip().startswith('{'):
                cookies_data = json.loads(cookies_string)
                if isinstance(cookies_data, list):
                    return {cookie['name']: cookie['value'] for cookie in cookies_data}
                elif isinstance(cookies_data, dict):
                    return cookies_data
            else:
                # Parse as key=value; format
                cookies = {}
                for cookie in cookies_string.split(';'):
                    if '=' in cookie:
                        key, value = cookie.split('=', 1)
                        cookies[key.strip()] = value.strip()
                return cookies
        return {}
    except Exception as e:
        logging.error(f"Error parsing cookies: {str(e)}")
        return {}

def estimate_scraping_time(total_leads, delay_seconds):
    """Estimate total scraping time"""
    total_seconds = total_leads * delay_seconds
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m"
    else:
        return f"{int(minutes)}m"

def log_scraping_metrics(job_id, action, data=None):
    """Log scraping metrics for monitoring"""
    log_data = {
        'job_id': job_id,
        'action': action,
        'timestamp': time.time(),
        'data': data or {}
    }
    
    logging.info(f"SCRAPING_METRICS: {json.dumps(log_data)}")
