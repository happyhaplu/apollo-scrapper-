"""
Chrome WebDriver setup for Replit environment
"""
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_chrome_for_replit():
    """Setup Chrome WebDriver optimized for Replit environment"""
    try:
        # Set up Chrome options
        chrome_options = Options()
        
        # Essential headless options
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-background-networking')
        
        # Window size
        chrome_options.add_argument('--window-size=1920,1080')
        
        # User agent to avoid detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
        
        # Anti-detection options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set up service with automatic driver management
        service = Service()
        
        # Create driver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to hide automation
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logging.info("Chrome WebDriver setup successful")
        return driver, None
        
    except Exception as e:
        error_msg = f"Chrome setup failed: {str(e)}"
        logging.error(error_msg)
        return None, error_msg

def test_chrome_setup():
    """Test Chrome setup"""
    driver, error = setup_chrome_for_replit()
    if driver:
        try:
            driver.get("https://httpbin.org/user-agent")
            title = driver.title
            logging.info(f"Chrome test successful. Page title: {title}")
            driver.quit()
            return True, "Chrome setup working"
        except Exception as e:
            driver.quit()
            return False, f"Chrome test failed: {str(e)}"
    else:
        return False, error

if __name__ == '__main__':
    success, message = test_chrome_setup()
    print(f"Chrome test: {'SUCCESS' if success else 'FAILED'} - {message}")