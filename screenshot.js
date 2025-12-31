const { chromium } = require('playwright');

(async () => {
  try {
    const browser = await chromium.launch({
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security'],
      headless: true
    });

    const context = await browser.newContext({
      ignoreHTTPSErrors: true
    });

    const page = await context.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });

    console.log('Navigating to docs.docker.com...');
    await page.goto('https://docs.docker.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for content to render
    console.log('Waiting for page to render...');
    await page.waitForTimeout(3000);

    console.log('Taking screenshot...');
    await page.screenshot({ path: 'docker-docs-screenshot.png', fullPage: true });

    await browser.close();
    console.log('Screenshot saved as docker-docs-screenshot.png');
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
})();
