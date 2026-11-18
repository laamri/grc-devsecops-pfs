// Used by validate_compose.py; Playwright is installed only in a temporary folder.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const [base, title] = process.argv.slice(2);
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,
  });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);
    page.setDefaultNavigationTimeout(15000);
    const failures = [];
    const apiRequests = [];
    page.on('pageerror', error => failures.push(error.message));
    page.on('requestfailed', request => {
      // Reload intentionally cancels any request still in flight from the old page.
      if (request.failure()?.errorText !== 'net::ERR_ABORTED') {
        failures.push({ url: request.url(), error: request.failure()?.errorText });
      }
    });
    page.on('request', request => {
      if (request.resourceType() === 'fetch') {
        assert.equal(new URL(request.url()).origin, new URL(base).origin);
        apiRequests.push(new URL(request.url()).pathname);
      }
    });
    assert.equal((await page.goto(base)).status(), 200);
    console.error('Browser: page loaded');
    await page.waitForFunction(() => {
      const body = document.body.innerText;
      return /Auth Service \(8001\):\s*ok/.test(body)
        && /Task Service \(8002\):\s*ok/.test(body);
    });
    console.error('Browser: both health badges are ok');
    await page.getByRole('textbox').fill(title);
    const created = page.waitForResponse(response =>
      response.url().includes('/api/task/tasks') && response.request().method() === 'POST'
        && response.status() !== 308);
    await page.getByRole('button', { name: 'Ajouter', exact: true }).click();
    const response = await created;
    console.error('Browser: creation response received', response.status());
    assert.equal(response.status(), 200);
    // Verify the UI's own JSON handling through the rendered task, not CDP body replay.
    await page.getByRole('listitem').filter({ hasText: title }).waitFor();
    console.error('Browser: created task is visible');
    await page.reload();
    await page.getByRole('listitem').filter({ hasText: title }).waitFor();
    console.error('Browser: task is visible after reload');
    assert.deepEqual(failures, []);
    assert(apiRequests.includes('/api/auth/health'));
    assert(apiRequests.includes('/api/task/health'));
    assert(apiRequests.some(path => path.startsWith('/api/task/tasks')));
    console.log(JSON.stringify({
      page: 'HTTP 200', auth: 'ok', task: 'ok',
      createdTitle: title, visibleAfterReload: true,
      allFetchesSameOrigin: true, errors: failures,
    }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
