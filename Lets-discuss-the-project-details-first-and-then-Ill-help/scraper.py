import time
import json
import logging
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
from config import Config
from utils import (
    clean_text, extract_email, extract_phone, extract_linkedin_url,
    calculate_smart_delay, format_company_size, log_scraping_metrics,
    parse_apollo_cookies
)

class ApolloScraper:
    def __init__(self, cookies=None, delay=Config.DEFAULT_DELAY):
        self.cookies = parse_apollo_cookies(cookies) if cookies else {}
        self.delay = delay
        self.driver = None
        self.error_count = 0
        self.success_count = 0
        self.session_leads = []
        
    def setup_driver(self):
        """Setup Chrome WebDriver with optimal settings"""
        try:
            from chrome_setup import setup_chrome_for_replit
            
            # Use the optimized Chrome setup
            self.driver, error = setup_chrome_for_replit()
            if not self.driver:
                raise Exception(error)
            
            # Execute script to hide automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set cookies if provided
            if self.cookies:
                self.driver.get(Config.APOLLO_BASE_URL)
                for name, value in self.cookies.items():
                    try:
                        self.driver.add_cookie({
                            'name': name,
                            'value': value,
                            'domain': '.apollo.io'
                        })
                    except Exception as e:
                        logging.warning(f"Failed to set cookie {name}: {str(e)}")
            
            logging.info("Chrome WebDriver setup completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to setup Chrome WebDriver: {str(e)}")
            return False
    
    def wait_for_page_load(self, timeout=30):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            # Additional wait for Apollo's React components
            time.sleep(3)
            return True
        except TimeoutException:
            logging.warning("Page load timeout")
            return False
    
    def smart_delay(self):
        """Apply smart delay between requests"""
        delay = calculate_smart_delay(self.delay, self.error_count, self.success_count)
        logging.debug(f"Applying delay of {delay:.2f} seconds")
        time.sleep(delay)
    
    def extract_lead_data(self, lead_element):
        """Extract comprehensive lead data from a lead element"""
        try:
            lead_data = {
                'first_name': '',
                'last_name': '',
                'full_name': '',
                'email': '',
                'phone': '',
                'linkedin_url': '',
                'job_title': '',
                'seniority': '',
                'department': '',
                'company_name': '',
                'company_domain': '',
                'company_website': '',
                'company_industry': '',
                'company_size': '',
                'company_location': '',
                'company_linkedin': '',
                'years_experience': 0,
                'location': '',
                'raw_data': ''
            }
            
            # Get the HTML content
            html_content = lead_element.get_attribute('innerHTML')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Store raw data
            lead_data['raw_data'] = json.dumps(html_content)
            
            # Extract name information
            name_selectors = [
                '[data-cy="person-name"]',
                '.zp_xVJ20',
                '.person-name',
                '[class*="name"]'
            ]
            
            for selector in name_selectors:
                try:
                    name_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    full_name = clean_text(name_element.text)
                    if full_name:
                        lead_data['full_name'] = full_name
                        name_parts = full_name.split(' ')
                        if len(name_parts) >= 1:
                            lead_data['first_name'] = name_parts[0]
                        if len(name_parts) >= 2:
                            lead_data['last_name'] = ' '.join(name_parts[1:])
                        break
                except NoSuchElementException:
                    continue
            
            # Extract email
            email_selectors = [
                '[data-cy="person-email"]',
                '.zp_Iu6Pf',
                '[class*="email"]',
                'a[href^="mailto:"]'
            ]
            
            for selector in email_selectors:
                try:
                    email_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    email = clean_text(email_element.text) or email_element.get_attribute('href', '').replace('mailto:', '')
                    if '@' in email:
                        lead_data['email'] = email
                        break
                except NoSuchElementException:
                    continue
            
            # If no email found, try to extract from text content
            if not lead_data['email']:
                lead_data['email'] = extract_email(html_content)
            
            # Extract phone number
            phone_selectors = [
                '[data-cy="person-phone"]',
                '.zp_Yz4Ml',
                '[class*="phone"]'
            ]
            
            for selector in phone_selectors:
                try:
                    phone_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    phone = clean_text(phone_element.text)
                    if phone:
                        lead_data['phone'] = phone
                        break
                except NoSuchElementException:
                    continue
            
            # If no phone found, try to extract from text content
            if not lead_data['phone']:
                lead_data['phone'] = extract_phone(html_content)
            
            # Extract LinkedIn URL
            linkedin_selectors = [
                'a[href*="linkedin.com"]',
                '[data-cy="person-linkedin"]'
            ]
            
            for selector in linkedin_selectors:
                try:
                    linkedin_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    linkedin_url = linkedin_element.get_attribute('href')
                    if linkedin_url and 'linkedin.com' in linkedin_url:
                        lead_data['linkedin_url'] = linkedin_url
                        break
                except NoSuchElementException:
                    continue
            
            # Extract job title
            title_selectors = [
                '[data-cy="person-title"]',
                '.zp_Y6y8d',
                '[class*="title"]',
                '[class*="job-title"]'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    job_title = clean_text(title_element.text)
                    if job_title:
                        lead_data['job_title'] = job_title
                        break
                except NoSuchElementException:
                    continue
            
            # Extract company information
            company_selectors = [
                '[data-cy="person-company"]',
                '.zp_J1j1x',
                '[class*="company"]'
            ]
            
            for selector in company_selectors:
                try:
                    company_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    company_name = clean_text(company_element.text)
                    if company_name:
                        lead_data['company_name'] = company_name
                        break
                except NoSuchElementException:
                    continue
            
            # Extract location
            location_selectors = [
                '[data-cy="person-location"]',
                '.zp_MC4wf',
                '[class*="location"]'
            ]
            
            for selector in location_selectors:
                try:
                    location_element = lead_element.find_element(By.CSS_SELECTOR, selector)
                    location = clean_text(location_element.text)
                    if location:
                        lead_data['location'] = location
                        break
                except NoSuchElementException:
                    continue
            
            # Extract additional company details from company link/popup if available
            try:
                company_link = lead_element.find_element(By.CSS_SELECTOR, 'a[href*="/companies/"]')
                if company_link:
                    company_url = company_link.get_attribute('href')
                    # Extract company domain from URL if possible
                    if '/companies/' in company_url:
                        lead_data['company_domain'] = company_url.split('/companies/')[-1].split('/')[0]
            except NoSuchElementException:
                pass
            
            self.success_count += 1
            logging.debug(f"Successfully extracted lead data for: {lead_data['full_name']}")
            return lead_data
            
        except Exception as e:
            self.error_count += 1
            logging.error(f"Error extracting lead data: {str(e)}")
            return None
    
    def get_total_results(self):
        """Get total number of results from the search"""
        try:
            # Common selectors for result count
            result_selectors = [
                '[data-cy="results-count"]',
                '.zp_xqF0w',
                '[class*="results"]',
                '[class*="count"]'
            ]
            
            for selector in result_selectors:
                try:
                    result_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    result_text = clean_text(result_element.text)
                    
                    # Extract number from text like "1,234 results" or "1234 people"
                    import re
                    numbers = re.findall(r'[\d,]+', result_text)
                    if numbers:
                        total = int(numbers[0].replace(',', ''))
                        logging.info(f"Found {total} total results")
                        return total
                except NoSuchElementException:
                    continue
            
            # Fallback: count visible lead elements
            lead_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-cy="person"], .zp_xVJ20, [class*="person-row"]')
            logging.info(f"Fallback count: {len(lead_elements)} visible leads")
            return len(lead_elements) * 25  # Estimate based on pagination
            
        except Exception as e:
            logging.error(f"Error getting total results: {str(e)}")
            return 0
    
    def scrape_current_page(self):
        """Scrape leads from the current page"""
        leads = []
        
        try:
            # Wait for leads to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="person"], .zp_xVJ20, [class*="person-row"]'))
            )
            
            # Find all lead elements on the page
            lead_selectors = [
                '[data-cy="person"]',
                '.zp_xVJ20',
                '[class*="person-row"]',
                '[class*="contact-row"]'
            ]
            
            lead_elements = []
            for selector in lead_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    lead_elements = elements
                    break
            
            logging.info(f"Found {len(lead_elements)} lead elements on current page")
            
            # Extract data from each lead
            for i, lead_element in enumerate(lead_elements):
                try:
                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", lead_element)
                    time.sleep(0.5)
                    
                    lead_data = self.extract_lead_data(lead_element)
                    if lead_data and lead_data['full_name']:  # Only add if we got meaningful data
                        leads.append(lead_data)
                        log_scraping_metrics(None, 'lead_extracted', {
                            'lead_name': lead_data['full_name'],
                            'has_email': bool(lead_data['email']),
                            'has_phone': bool(lead_data['phone'])
                        })
                    
                    # Short delay between lead extractions
                    if i < len(lead_elements) - 1:
                        time.sleep(random.uniform(0.5, 1.5))
                        
                except Exception as e:
                    logging.error(f"Error processing lead element {i}: {str(e)}")
                    continue
            
            logging.info(f"Successfully scraped {len(leads)} leads from current page")
            return leads
            
        except TimeoutException:
            logging.error("Timeout waiting for leads to load")
            return []
        except Exception as e:
            logging.error(f"Error scraping current page: {str(e)}")
            return []
    
    def go_to_next_page(self):
        """Navigate to the next page of results"""
        try:
            # Common selectors for next page button
            next_selectors = [
                '[data-cy="next-page"]',
                '.zp_Zkc2Q[aria-label="Next"]',
                'button[aria-label="Next"]',
                '.pagination-next',
                '[class*="next"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled() and next_button.is_displayed():
                        # Scroll to button and click
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        next_button.click()
                        
                        # Wait for page to load
                        self.wait_for_page_load()
                        logging.info("Successfully navigated to next page")
                        return True
                except NoSuchElementException:
                    continue
            
            logging.info("No next page button found or available")
            return False
            
        except Exception as e:
            logging.error(f"Error navigating to next page: {str(e)}")
            return False
    
    def scrape_apollo_search(self, search_url, max_results=1000, progress_callback=None):
        """Main scraping method for Apollo search results"""
        try:
            if not self.setup_driver():
                raise Exception("Failed to setup WebDriver")
            
            # Navigate to search URL
            logging.info(f"Navigating to search URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for page to load
            if not self.wait_for_page_load():
                raise Exception("Page failed to load")
            
            # Check if we need to login
            if '/sign-in' in self.driver.current_url or 'login' in self.driver.current_url.lower():
                raise Exception("Authentication required. Please provide valid cookies or login credentials.")
            
            # Get total results
            total_results = self.get_total_results()
            actual_max = min(max_results, total_results)
            
            logging.info(f"Starting to scrape {actual_max} leads from {total_results} total results")
            
            all_leads = []
            page_num = 1
            
            while len(all_leads) < actual_max:
                logging.info(f"Scraping page {page_num}")
                
                # Scrape current page
                page_leads = self.scrape_current_page()
                
                if not page_leads:
                    logging.warning(f"No leads found on page {page_num}, stopping")
                    break
                
                # Add leads up to our limit
                remaining_slots = actual_max - len(all_leads)
                leads_to_add = page_leads[:remaining_slots]
                all_leads.extend(leads_to_add)
                
                # Update progress
                progress = len(all_leads) / actual_max * 100
                if progress_callback:
                    progress_callback(progress, len(all_leads), actual_max)
                
                logging.info(f"Page {page_num} complete. Total leads: {len(all_leads)}/{actual_max}")
                
                # Check if we've reached our limit
                if len(all_leads) >= actual_max:
                    break
                
                # Apply smart delay before next page
                self.smart_delay()
                
                # Try to go to next page
                if not self.go_to_next_page():
                    logging.info("No more pages available")
                    break
                
                page_num += 1
                
                # Safety check to prevent infinite loops
                if page_num > 1000:
                    logging.warning("Reached maximum page limit (1000), stopping")
                    break
            
            logging.info(f"Scraping completed. Total leads extracted: {len(all_leads)}")
            log_scraping_metrics(None, 'scraping_completed', {
                'total_leads': len(all_leads),
                'pages_scraped': page_num,
                'success_rate': self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0
            })
            
            return all_leads
            
        except Exception as e:
            logging.error(f"Scraping failed: {str(e)}")
            raise e
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("WebDriver closed")
    
    def test_authentication(self):
        """Test if authentication is working"""
        try:
            if not self.setup_driver():
                return False, "Failed to setup WebDriver"
            
            # Navigate to Apollo dashboard
            self.driver.get(f"{Config.APOLLO_BASE_URL}/#/home")
            self.wait_for_page_load()
            
            # Check if we're redirected to login
            current_url = self.driver.current_url
            if '/sign-in' in current_url or 'login' in current_url.lower():
                return False, "Authentication failed - redirected to login page"
            
            # Check for user-specific elements
            user_indicators = [
                '[data-cy="user-menu"]',
                '.user-avatar',
                '[class*="user"]',
                '[class*="profile"]'
            ]
            
            for selector in user_indicators:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    return True, "Authentication successful"
                except NoSuchElementException:
                    continue
            
            return False, "Authentication status unclear"
            
        except Exception as e:
            return False, f"Authentication test failed: {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()
