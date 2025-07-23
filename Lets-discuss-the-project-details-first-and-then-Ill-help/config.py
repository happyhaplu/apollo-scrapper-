import os

class Config:
    # Apollo scraping settings
    APOLLO_BASE_URL = "https://app.apollo.io"
    
    # Rate limiting settings
    MIN_DELAY = int(os.environ.get('MIN_DELAY', '2'))  # 2 seconds minimum
    MAX_DELAY = int(os.environ.get('MAX_DELAY', '50'))  # 50 seconds maximum
    DEFAULT_DELAY = int(os.environ.get('DEFAULT_DELAY', '10'))  # 10 seconds default
    
    # Daily limits
    MAX_DAILY_LEADS = int(os.environ.get('MAX_DAILY_LEADS', '50000'))  # 50k per day
    MAX_DAILY_REQUESTS = int(os.environ.get('MAX_DAILY_REQUESTS', '5000'))  # 5k requests per day
    
    # Selenium settings
    CHROME_OPTIONS = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    # File paths
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    EXPORT_FOLDER = os.environ.get('EXPORT_FOLDER', 'exports')
    
    # Apollo account settings
    APOLLO_EMAIL_CREDITS_LIMIT = int(os.environ.get('APOLLO_EMAIL_CREDITS_LIMIT', '10000'))  # Monthly limit
