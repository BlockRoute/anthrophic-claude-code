#!/usr/bin/env python3
from html2image import Html2Image
import os

# Use the Playwright-downloaded Chromium
chromium_path = '/root/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome'

# Initialize with the chromium executable and flags
hti = Html2Image(
    browser_executable=chromium_path,
    size=(1920, 1080),
    custom_flags=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
)

# Take screenshot from the local HTML file
print("Rendering HTML to image...")
hti.screenshot(
    html_file='docker-docs.html',
    save_as='docker-docs-screenshot.png',
    size=(1920, 1080)
)

print("Screenshot saved as docker-docs-screenshot.png")
