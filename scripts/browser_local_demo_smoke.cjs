/* Optional local Chromium regression for the downloadable synthetic demo.
   Start scripts/run_local_demo.py first. The test blocks hosted 3D and uses loopback only. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const captureDir = process.env.CI_CAPTURE_DIR;
if (captureDir) fs.mkdirSync(captureDir, { recursive: true });
async function capture(page, name) {
  if (captureDir) await page.screenshot({ path: path.join(captureDir, name + '.png'), fullPage: true });
}

const base = (process.env.WORKBENCH_URL || 'http://127.0.0.1:8765').replace(/\/$/, '');
const errors = [];

(async () => {
  const launch = {
    headless: true,
    args: ['--no-sandbox', '--disable-gpu-sandbox', '--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  };
  if (process.env.CHROMIUM_EXECUTABLE_PATH) launch.executablePath = process.env.CHROMIUM_EXECUTABLE_PATH;
  const browser = await chromium.launch(launch);
  try {
    const context = await browser.newContext({ viewport: { width: 1360, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => {
      if (message.type() === 'error' && !message.text().includes('sketchfab.com')) errors.push('console: ' + message.text());
    });
    await page.route('https://sketchfab.com/**', route => route.abort('blockedbyclient'));

    await page.goto(base + '/#twin', { waitUntil: 'domcontentloaded' });
    await page.locator('#local-demo-banner').waitFor({ state: 'visible' });
    await capture(page, '01-garage');
    assert.match(await page.locator('#local-demo-banner').innerText(), /synthetic demo/i);
    await page.locator('[data-mech-scene="ix_front_axle_workshop"]').waitFor({ state: 'visible' });
    await page.locator('[data-mech-scene="ix_front_axle_workshop"]').click();
    await page.locator('#ix-mech-browser').waitFor({ state: 'visible' });
    await page.waitForFunction(() => document.querySelector('#twinvisualstatus')?.textContent.includes('selectable 3D segments'));
    await page.locator('#ix3d-stage canvas').waitFor({ state: 'visible' });

    await page.locator('#ix-mech-part-list [data-component="tie_rod"]').click();
    const result = page.locator('.ix-mech-catalog-result').first();
    await result.waitFor({ state: 'visible' });
    await result.click();
    const candidateId = await result.getAttribute('data-candidate');
    const assemblyId = await result.getAttribute('data-assembly');
    const number = (await result.locator('strong').innerText()).trim();
    assert.match(number, /^DEMO-/);
    assert(candidateId && assemblyId);
    await page.locator('.ix-mech-evidence h4').waitFor({ state: 'visible' });
    assert.match(await page.locator('.ix-mech-evidence').innerText(), /Catalog occurrence.*installed identity unconfirmed/s);
    assert.match(await page.locator('.ix-mech-evidence').innerText(), /Research: NOT_RESEARCHED · 0\/0 drawings verified locally/);
    assert.match(await page.locator('.ix-mech-evidence').innerText(), /No exact catalog source URL in this record/);
    assert.equal(await page.locator('.ix-mech-evidence a').count(), 0, 'Synthetic evidence must not link to an unsourced OEM drawing');
    await capture(page, '02-selected-component');

    await page.locator('#ix-mech-job-symptom').fill('Synthetic demo symptom for local persistence testing only.');
    await page.locator('.ix-mech-job-form select').selectOption('LEFT');
    await page.locator('.ix-mech-save').click();
    await page.locator('#expertcasepanel').waitFor({ state: 'visible' });
    await page.waitForFunction(() => document.querySelector('#expertcasetitle')?.textContent.includes('road clearance NOT APPROVED'));
    assert((await page.locator('#expertoverview').innerText()).includes(number));
    await capture(page, '03-saved-case');
    const caseId = (await page.locator('#expertcasetitle').innerText()).match(/IX-(\d+)/)?.[1];
    assert(caseId, 'Synthetic local case should have a visible persistent ID');

    await page.locator('#expertoverview button').filter({ hasText: 'Open BMW drawing & part dossier' }).click();
    await page.waitForFunction(part => document.querySelector('#parttitle')?.textContent.includes(part), number);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(part => document.querySelector('#parttitle')?.textContent.includes(part), number);
    const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('325ix-visual-context-v1')));
    assert.equal(saved.part_id, candidateId);
    assert.equal(saved.candidate_id, candidateId);
    assert.equal(saved.candidate_assembly_id, assemblyId);
    assert.equal(saved.front_play_job_id, String(Number(caseId)));

    await page.locator('.tab[data-tab="twin"]').click();
    await page.locator('#ix-mech-browser').waitFor({ state: 'visible' });
    await page.locator('#ix-mech-part-list [data-component="tie_rod"].selected').waitFor({ state: 'visible' });
    await page.locator(`.ix-mech-catalog-result[data-candidate="${candidateId}"].selected`).waitFor({ state: 'visible' });
    if (errors.length) throw new Error('Browser errors: ' + errors.slice(0, 8).join(' | '));

    console.log(`PASS local demo browser: local front axle GLB → ${number} → IX-${String(caseId).padStart(4, '0')} → dossier/reload → restored selection; safety remains NOT_APPROVED`);
    await context.close();
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error('FAIL local demo browser smoke', error);
  process.exit(1);
});
