// Headless, isolated browser verification of RenderGuard only. No personal apps/sessions.
import {chromium} from 'playwright';
import {mkdir, writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const base=process.env.BASE_URL||'http://127.0.0.1:18341';
const out='output/playwright';
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,channel:'chrome'});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
const page=await context.newPage();
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
const steps=[];
async function step(name,fn){await fn();steps.push({name,passed:true});console.log('PASS',name)}
async function newWorkspace(){await page.getByRole('button',{name:'New workspace',exact:true}).click();await page.getByRole('button',{name:'Add invoice',exact:true}).waitFor();}
async function invoice(id){await page.getByRole('button',{name:'Add invoice',exact:true}).click();await page.getByLabel('Synthetic invoice').selectOption(id);await page.getByRole('button',{name:'Open this case',exact:true}).click();await page.getByText('Evidence ready',{exact:true}).first().waitFor({timeout:90000});}
try{
 await step('English landing and isolated workspace',async()=>{await page.goto(base);await page.getByRole('button',{name:'Open payment workbench'}).click();await page.getByRole('heading',{name:'Payment workbench',exact:true}).waitFor();});
 await step('Actual clean PDF, local model, reviewer approval and sandbox release',async()=>{
  await invoice('clean');await page.getByRole('button',{name:'Prepare guarded proposal',exact:true}).click();await page.getByText('Awaiting reviewer',{exact:true}).first().waitFor({timeout:100000});
  await page.getByRole('tab',{name:'PDF & AI input',exact:true}).click();await page.getByRole('heading',{name:'What the AI actually received'}).waitFor();assert.match(await page.locator('.text-evidence').innerText(),/account_1/);
  await page.getByRole('tab',{name:'Rendered page',exact:true}).click();await page.getByLabel('Demo persona').selectOption('reviewer');await page.getByRole('button',{name:'Approve this exact action',exact:true}).click();await page.getByRole('button',{name:'Release to sandbox ledger',exact:true}).click();await page.getByText('Release recorded.',{exact:true}).waitFor({timeout:15000});
  await page.screenshot({path:out+'/release.png',fullPage:true});
 });
 await step('Immutable receipt and redacted audit/CSV downloads',async()=>{
  await page.getByRole('button',{name:'Release register',exact:true}).click();await page.locator('.register table').first().waitFor();assert.equal(await page.locator('.register table').first().locator('tbody tr').count(),1);
  const downloadPromise=page.waitForEvent('download');await page.getByRole('link',{name:'Export redacted JSONL'}).click();const download=await downloadPromise;assert.equal(download.suggestedFilename(),'renderguard-audit.jsonl');await download.saveAs(out+'/audit.jsonl');
  const csvPromise=page.waitForEvent('download');await page.getByRole('link',{name:'Export release CSV'}).click();const csv=await csvPromise;assert.equal(csv.suggestedFilename(),'sandbox-release-register.csv');await csv.saveAs(out+'/receipts.csv');
  await page.screenshot({path:out+'/register.png',fullPage:true});
 });
 await step('QR recipient discrepancy blocks preparation and exposes exact fields',async()=>{
  await newWorkspace();await invoice('qr-swap');await page.getByRole('button',{name:'Prepare guarded proposal',exact:true}).click();await page.getByText('Keep this payment on hold.',{exact:true}).waitFor();await page.getByRole('tab',{name:'Payment fields',exact:true}).click();assert.match(await page.locator('.comparison').innerText(),/QR differs from visible recipient/);await page.screenshot({path:out+'/qr-swap.png',fullPage:true});
 });
 await step('Policy privacy action changes observed gateway behavior',async()=>{
  await page.getByLabel('Demo persona').selectOption('admin');await page.getByRole('button',{name:'Controls',exact:true}).click();await page.getByLabel('Full policy · editable JSON').waitFor();const policy=JSON.parse(await page.getByLabel('Full policy · editable JSON').inputValue());policy.controls.pii_action='block';await page.getByLabel('Full policy · editable JSON').fill(JSON.stringify(policy,null,2));await page.getByRole('button',{name:'Apply policy',exact:true}).click();await page.getByText('Applied atomically.',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Test lab',exact:true}).click();await page.getByRole('button',{name:'Secret leak',exact:true}).click();await page.getByRole('button',{name:'Evaluate interaction',exact:true}).click();await page.getByRole('heading',{name:'Observed decision'}).waitFor();assert.match(await page.locator('.lab-layout aside').innerText(),/Sensitive data blocked before dispatch/);await page.screenshot({path:out+'/control-probe.png',fullPage:true});
 });
 await step('Live signature catalog can be removed in isolated workspace',async()=>{
  await page.getByRole('button',{name:'Controls',exact:true}).click();await page.getByLabel('Signature feed · workspace override').fill(JSON.stringify({version:'browser-judge-edit',entries:[]},null,2));await page.getByRole('button',{name:'Apply signature catalog',exact:true}).click();await page.getByText('Signature catalog saved for this workspace.',{exact:false}).waitFor();
 });
 await step('Mobile workflow stays within viewport and remains usable',async()=>{
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Workbench',exact:true}).click();await page.getByRole('tab',{name:'Rendered page',exact:true}).click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));await page.locator('.render img').evaluate(img=>img.decode());await page.screenshot({path:out+'/mobile-workbench.png',fullPage:true});
 });
 await step('Self-hosted API reference loads under the content security policy',async()=>{await page.goto(base+'/docs');await page.getByRole('heading',{name:/RenderGuard.*OAS/}).waitFor();assert.ok(await page.getByText('/api/documents/upload',{exact:true}).count());});
 assert.deepEqual(errors,[],'Browser runtime errors');
 const report={base_url:base,recorded_at:new Date().toISOString(),passed:steps.length,total:steps.length,scope:'Actual own-app headless Chrome, local model and isolated PDF worker; no mocked network',runtime_errors:errors,steps};
 await mkdir('evals',{recursive:true});await writeFile('evals/browser.json',JSON.stringify(report,null,2)+'\n');
 console.log('Completed',steps.length,'browser checks');
}catch(error){await page.screenshot({path:out+'/failure.png',fullPage:true}).catch(()=>{});throw error}
finally{await context.close();await browser.close();}
