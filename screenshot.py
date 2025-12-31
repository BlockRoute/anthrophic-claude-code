#!/usr/bin/env python3
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

# Get proxy from environment
proxy_url = os.environ.get('HTTP_PROXY', os.environ.get('http_proxy', ''))

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')

if proxy_url:
    # Extract proxy server without credentials for Chrome
    # Chrome proxy format: --proxy-server=http://host:port
    chrome_options.add_argument(f'--proxy-server={proxy_url}')

# Use chromedriver
service = Service('/opt/node22/bin/chromedriver')

# Create driver
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Navigate to the page
    print("Navigating to docs.docker.com...")
    driver.get('https://docs.docker.com')

    # Wait for page to load
    time.sleep(3)

    # Take screenshot
    print("Taking screenshot...")
    driver.save_screenshot('docker-docs-screenshot.png')
    print("Screenshot saved as docker-docs-screenshot.png")

finally:
    driver.quit()
