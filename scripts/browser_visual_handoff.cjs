/* Integrated browser regression for the 3D -> BMW catalog -> persistent case/mission journey.
   Requires a local V4 runtime corpus, scripts/preview_server.py, Playwright and Chromium.
   The preview server stores mutable jobs in a disposable temporary directory. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const base = (process.env.WORKBENCH_URL || 'http://127.0.0.1:8080').replace(/\/$/, '');
const errors = [];

(async () => {
  const launchOptions = {
    headless: true,
    args: ['--no-sandbox', '--disable-gpu-sandbox', '--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  };
  if (process.env.CHROMIUM_EXECUTABLE_PATH) launchOptions.executablePath = process.env.CHROMIUM_EXECUTABLE_PATH;
  const browser = await chromium.launch(launchOptions);
  try {
    const context = await browser.newContext({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    page.setDefaultTimeout(45000);
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => {
      // The public hosted viewer is intentionally blocked in this offline regression.
      if (message.type() === 'error' && !message.text().includes('sketchfab.com')) errors.push('console: ' + message.text());
    });
    await page.route('https://sketchfab.com/**', route => route.abort('blockedbyclient'));

    await page.goto(base + '/#twin', { waitUntil: 'domcontentloaded' });
    await page.locator('[data-mech-scene="ix_front_axle_workshop"]').waitFor({ state: 'visible' });
    await page.locator('[data-mech-scene="ix_front_axle_workshop"]').click();
    await page.locator('#ix-mech-browser').waitFor({ state: 'visible' });
    await page.locator('#ix-mech-part-list [data-component="tie_rod"]').click();
    await page.locator('.ix-mech-catalog-result').first().waitFor({ state: 'visible' });

    const exact = page.locator('.ix-mech-catalog-result').filter({ hasText: '32211701039' });
    const selected = (await exact.count()) ? exact.first() : page.locator('.ix-mech-catalog-result').first();
    await selected.click();
    const candidateId = await selected.getAttribute('data-candidate');
    const candidateAssembly = await selected.getAttribute('data-assembly');
    const candidateNumber = (await selected.locator('strong').innerText()).trim();
    assert(candidateId && candidateAssembly, 'A selected catalog occurrence must retain its row and parent assembly IDs');

    await page.locator('#ix-mech-job-symptom').fill('Steering movement observed at standstill; source remains unknown.');
    await page.locator('.ix-mech-job-form select').selectOption('LEFT');
    await page.locator('.ix-mech-save').click();
    await page.locator('#expertcasepanel').waitFor({ state: 'visible' });
    await page.waitForFunction(() => document.querySelector('#expertcasetitle')?.textContent.includes('road clearance NOT APPROVED'));
    const handoff = await page.locator('#expertoverview').innerText();
    assert.match(handoff, /Visual workshop handoff/);
    assert(handoff.includes(candidateNumber), 'The persisted front-wheel-play case should retain the catalog candidate');
    const caseMatch = (await page.locator('#expertcasetitle').innerText()).match(/IX-(\d+)/);
    assert(caseMatch, 'Saved case ID should be visible in the guided-workflow UI');
    const jobId = Number(caseMatch[1]);

    await page.locator('#expertoverview button').filter({ hasText: 'Open BMW drawing & part dossier' }).click();
    await page.locator('#detailpanel:not([hidden])').waitFor({ state: 'visible' });
    await page.waitForFunction(number => document.querySelector('#parttitle')?.textContent.includes(number), candidateNumber);
    assert.match(await page.locator('#partevidence').innerText(), /applicability|evidence|fitment/i);

    // Return to the same mechanical locator after crossing into the catalog dossier.
    await page.locator('.tab[data-tab="twin"]').click();
    await page.locator('#ix-mech-browser').waitFor({ state: 'visible' });
    await page.locator('#ix-mech-part-list [data-component="tie_rod"].selected').waitFor({ state: 'visible' });
    await page.locator(`.ix-mech-catalog-result[data-candidate="${candidateId}"].selected`).waitFor({ state: 'visible' });

    // Switch into OEM 2D and confirm the chosen assembly/dossier are retained.
    await page.locator('#twin2d').click();
    await page.locator('#twin-diagram-panel:not([hidden])').waitFor({ state: 'visible' });
    await page.locator('.visual-diagram-wrap').waitFor({ state: 'visible' });
    await page.waitForFunction(number => document.querySelector('#twin-system-list')?.textContent.includes(number), candidateNumber);
    const beforeReload = await page.evaluate(() => JSON.parse(localStorage.getItem('325ix-visual-context-v1')));
    assert.equal(beforeReload.mode, 'oem');
    assert.equal(beforeReload.system_id, 'steering');
    assert.equal(beforeReload.assembly_id, candidateAssembly);
    assert(beforeReload.part_id, 'Selected BMW part dossier should persist alongside the assembly');
    assert.equal(beforeReload.front_play_job_id, String(jobId));

    // Full refresh restores the 2D assembly, selected dossier and mission link.
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('#twin-diagram-panel:not([hidden])').waitFor({ state: 'visible' });
    await page.locator('.visual-diagram-wrap').waitFor({ state: 'visible' });
    await page.waitForFunction(number => document.querySelector('#twin-system-list')?.textContent.includes(number), candidateNumber);

    await page.locator('#twin-system-list button').filter({ hasText: 'Open or start restoration mission' }).click();
    await page.locator('#livingmissiontitle').waitFor({ state: 'visible' });
    await page.waitForFunction(id => document.querySelector('#livingmissiontitle')?.textContent.includes(id), 'IX-' + String(jobId).padStart(4, '0'));
    assert.match(await page.locator('#livingmissionrisk').innerText(), /NOT[_ ]APPROVED/);

    // Reopen after refresh and use browser-back to return to the same visual context.
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(id => document.querySelector('#livingmissiontitle')?.textContent.includes(id), 'IX-' + String(jobId).padStart(4, '0'));
    const missionState = await page.evaluate(() => JSON.parse(localStorage.getItem('325ix-visual-context-v1')));
    assert.equal(missionState.workspace, 'mission');
    assert.equal(missionState.mission_job_id, String(jobId));
    assert.equal(missionState.front_play_job_id, String(jobId));
    await page.goBack();
    await page.waitForFunction(() => location.hash === '#twin');
    await page.locator('#twin-diagram-panel:not([hidden])').waitFor({ state: 'visible' });
    await page.locator('.visual-diagram-wrap').waitFor({ state: 'visible' });
    await page.waitForFunction(number => document.querySelector('#twin-system-list')?.textContent.includes(number), candidateNumber);

    const restored = await page.evaluate(() => JSON.parse(localStorage.getItem('325ix-visual-context-v1')));
    assert.equal(restored.workspace, 'twin');
    assert.equal(restored.system_id, 'steering');
    assert.equal(restored.assembly_id, candidateAssembly);
    assert.equal(restored.mission_job_id, String(jobId));
    assert.equal(restored.mode, 'oem');
    if (errors.length) throw new Error('Browser errors: ' + errors.slice(0, 8).join(' | '));

    console.log(`PASS integrated browser handoff: scene tie_rod -> ${candidateNumber} -> IX-${String(jobId).padStart(4, '0')} -> BMW dossier -> OEM 2D -> reload -> mission -> browser-back; safety remains NOT_APPROVED`);
    await context.close();
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error('FAIL integrated browser visual handoff', error);
  process.exit(1);
});
