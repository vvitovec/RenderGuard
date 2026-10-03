// Headless verification of RenderGuard only; isolated browser, actual API and local model.
import { chromium } from "playwright";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import assert from "node:assert/strict";

const base = process.env.BASE_URL || "http://127.0.0.1:18341";
const out = "output/playwright";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const steps = [];
let provenance;

async function step(name, fn) {
  await fn();
  steps.push({ name, passed: true });
  console.log("PASS", name);
}
async function idle() {
  await page.locator('.shell[data-busy=""]').waitFor({ timeout: 120000 });
}
async function stable() {
  await idle();
  await page
    .locator("img")
    .evaluateAll((images) =>
      Promise.all(images.map((img) => img.decode().catch(() => {}))),
    );
  await page.evaluate(() => document.fonts.ready);
}
async function screenshot(name, locator) {
  await stable();
  if (locator) await locator.screenshot({ path: `${out}/${name}` });
  else await page.screenshot({ path: `${out}/${name}`, fullPage: true });
}
async function view(name) {
  await page.getByRole("button", { name, exact: true }).click();
  await idle();
}
async function persona(role) {
  await page.getByLabel("Demo persona").selectOption(role);
  await idle();
}
async function invoice(id) {
  await page.getByRole("button", { name: "Add invoice", exact: true }).click();
  await page.getByLabel("Synthetic invoice").selectOption(id);
  await page
    .getByRole("button", { name: "Open this case", exact: true })
    .click();
  await page
    .getByText("Evidence ready", { exact: true })
    .first()
    .waitFor({ timeout: 90000 });
  await idle();
}
async function get(path) {
  const response = await context.request.get(base + "/api" + path);
  assert.ok(response.ok(), `GET ${path}: ${response.status()}`);
  return response.json();
}

try {
  await step(
    "English landing and isolated workspace with source provenance",
    async () => {
      await page.goto(base);
      await page
        .getByRole("button", { name: "Open payment workbench" })
        .click();
      await page
        .getByRole("heading", { name: "Payment workbench", exact: true })
        .waitFor();
      await idle();
      provenance = await get("/session");
      assert.match(provenance.source_sha, /^[a-f0-9]{64}$/);
    },
  );
  await step(
    "Actual clean PDF, account-handle model input, human approval and sandbox release",
    async () => {
      await invoice("clean");
      await page
        .getByRole("button", { name: "Prepare guarded proposal", exact: true })
        .click();
      await page
        .getByText("Awaiting reviewer", { exact: true })
        .first()
        .waitFor({ timeout: 120000 });
      await idle();
      await page
        .getByRole("tab", { name: "PDF & AI input", exact: true })
        .click();
      const input = page.getByTestId("model-input");
      assert.match(await input.innerText(), /account_1/);
      assert.doesNotMatch(await input.innerText(), /DE\d{20}/);
      await screenshot(
        "model-input.png",
        page.getByTestId("model-input-summary"),
      );
      await page
        .getByRole("tab", { name: "Rendered page", exact: true })
        .click();
      await persona("reviewer");
      await page
        .getByRole("button", { name: "Approve this exact action", exact: true })
        .click();
      await idle();
      await page
        .getByRole("button", { name: "Release to sandbox ledger", exact: true })
        .click();
      await page
        .getByText("Release recorded.", { exact: true })
        .waitFor({ timeout: 15000 });
      await screenshot("release.png");
      await screenshot("release-detail.png", page.locator(".release-panel"));
      const receipts = await get("/receipts");
      assert.equal(receipts.length, 1);
      assert.equal(receipts[0].bank_connected, false);
    },
  );
  await step(
    "Immutable receipt and redacted audit / CSV downloads",
    async () => {
      await view("Release register");
      assert.equal(
        await page.getByTestId("receipt-register").locator("tbody tr").count(),
        1,
      );
      let pending = page.waitForEvent("download");
      await page.getByRole("link", { name: "Export redacted JSONL" }).click();
      let download = await pending;
      assert.equal(download.suggestedFilename(), "renderguard-audit.jsonl");
      await download.saveAs(`${out}/audit.jsonl`);
      pending = page.waitForEvent("download");
      await page.getByRole("link", { name: "Export release CSV" }).click();
      download = await pending;
      assert.equal(
        download.suggestedFilename(),
        "sandbox-release-register.csv",
      );
      await download.saveAs(`${out}/receipts.csv`);
      assert.match(await readFile(`${out}/receipts.csv`, "utf8"), /TRUE,RG-/);
      const audit = await readFile(`${out}/audit.jsonl`, "utf8");
      assert.doesNotMatch(
        audit,
        /"approval_token"\s*:\s*"[A-Za-z0-9_.-]{40,}"/,
      );
    },
  );
  await step(
    "QR account conflict settles as blocked with zero provider dispatch",
    async () => {
      await persona("operator");
      await view("Workbench");
      await invoice("qr-swap");
      const before = (await get("/session")).usage.model_calls;
      await page
        .getByRole("button", { name: "Prepare guarded proposal", exact: true })
        .click();
      await page
        .getByText("Keep this payment on hold.", { exact: true })
        .waitFor();
      await idle();
      await page
        .getByRole("tab", { name: "Payment fields", exact: true })
        .click();
      assert.equal((await get("/session")).usage.model_calls, before);
      assert.match(
        await page.getByTestId("dispatch-proof").innerText(),
        /dispatch: 0/,
      );
      assert.ok(await page.locator(".comparison .field-conflict").count());
      assert.match(
        await page.locator(".release-panel").innerText(),
        /QR differs from visible recipient/,
      );
      await screenshot("qr-swap.png");
      // Native browser crop of the actual evidence and final decision, with no image editing.
      await stable();
      const left = await page.locator(".evidence-panel").boundingBox();
      const right = await page.locator(".release-panel").boundingBox();
      await page.screenshot({
        path: `${out}/qr-detail.png`,
        clip: {
          x: left.x,
          y: left.y,
          width: right.x + right.width - left.x,
          height: Math.min(540, Math.max(left.height, right.height)),
        },
      });
    },
  );
  await step(
    "Management reports unique invoice outcomes, final controls and separate latency stages",
    async () => {
      await persona("reviewer");
      await view("Release register");
      const metrics = await get("/metrics");
      assert.equal(metrics.payments.released.count, 1);
      assert.equal(metrics.payments.blocked.count, 1);
      assert.ok(metrics.held_controls.qr >= 1);
      assert.ok(metrics.stage_latency.gateway.count > 0);
      assert.match(
        await page.getByTestId("management-summary").innerText(),
        /€1,240.00/,
      );
      assert.match(
        await page.locator(".stage-report").innerText(),
        /Deterministic gateway/,
      );
      await screenshot("register.png");
      await screenshot(
        "audit-detail.png",
        page.getByTestId("management-summary"),
      );
    },
  );
  await step(
    "Live policy privacy action changes the observed final decision",
    async () => {
      await persona("admin");
      await view("Controls");
      const editor = page.getByLabel("Full policy · editable JSON");
      const policy = JSON.parse(await editor.inputValue());
      policy.controls.pii_action = "block";
      await editor.fill(JSON.stringify(policy, null, 2));
      await page
        .getByRole("button", { name: "Apply policy", exact: true })
        .click();
      await idle();
      await stable();
      const top = await page.locator(".policy-provenance").boundingBox();
      const quick = await page.locator(".policy-quick").boundingBox();
      await page.screenshot({
        path: `${out}/controls.png`,
        clip: {
          x: top.x,
          y: top.y,
          width: top.width,
          height: quick.y + quick.height - top.y,
        },
      });
      await view("Test lab");
      await page
        .getByRole("button", { name: "Secret leak", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Evaluate interaction", exact: true })
        .click();
      await idle();
      assert.match(
        await page.locator(".lab-layout aside").innerText(),
        /Sensitive data blocked before dispatch/,
      );
      await screenshot("control-probe.png", page.locator(".lab-layout"));
    },
  );
  await step(
    "A real semantic block appears in final audit and metrics",
    async () => {
      const before = await get("/metrics");
      await page
        .getByRole("button", { name: "Semantic injection", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Evaluate interaction", exact: true })
        .click();
      await idle();
      assert.match(
        await page.locator(".lab-layout aside").innerText(),
        /Semantic instruction check/,
      );
      assert.ok(await page.locator(".lab-layout aside .badge.block").count());
      const after = await get("/metrics");
      assert.equal(
        after.final_interactions.block,
        before.final_interactions.block + 1,
      );
      assert.ok(after.held_controls.semantic >= 1);
      const events = await get("/events");
      assert.ok(
        events.some(
          (event) =>
            event.kind === "interaction.final" &&
            event.verdict === "block" &&
            event.data.checks?.some((check) => check.control === "semantic"),
        ),
      );
    },
  );
  await step(
    "Literal feed canary changes allow to block to allow and restores the original feed",
    async () => {
      const original = (await get("/policy")).feed;
      await page
        .getByRole("button", { name: "Run live feed roundtrip" })
        .click();
      await page.getByTestId("feed-roundtrip").locator("li").nth(2).waitFor();
      await idle();
      const badges = await page
        .getByTestId("feed-roundtrip")
        .locator(".badge")
        .evaluateAll((nodes) => nodes.map((node) => node.className));
      assert.deepEqual(badges, ["badge allow", "badge block", "badge allow"]);
      assert.deepEqual((await get("/policy")).feed, original);
    },
  );
  await step(
    "Recorded full workflow report matches every current fixture and deployed source",
    async () => {
      const manifest = await get("/fixtures");
      const report = await get("/evaluation");
      assert.equal(report.status, "complete");
      assert.equal(report.total, manifest.length);
      assert.equal(report.passed, report.total);
      assert.equal(report.cases.length, manifest.length);
      assert.equal(report.source_sha, report.current_source_sha);
      assert.ok(
        manifest.every((item) =>
          report.cases.some((test) => test.id === item.id),
        ),
      );
      const status = page.getByTestId("evaluation-status");
      assert.equal(await status.getAttribute("data-current"), "true");
      assert.match(await status.innerText(), /Recorded full workflow suite/);
      assert.equal(
        await page
          .getByText("Awaiting matching report", { exact: true })
          .count(),
        0,
      );
      assert.equal(
        await page.getByText("Not recorded", { exact: true }).count(),
        0,
      );
    },
  );
  await step("Mobile workbench remains within the viewport", async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await view("Workbench");
    await page.getByRole("tab", { name: "Rendered page", exact: true }).click();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    );
    await screenshot("mobile-workbench.png");
  });
  await step(
    "Self-hosted API reference loads under the content security policy",
    async () => {
      await page.goto(base + "/docs");
      await page.getByRole("heading", { name: /RenderGuard.*OAS/ }).waitFor();
      assert.ok(
        await page.getByText("/api/documents/upload", { exact: true }).count(),
      );
    },
  );
  assert.deepEqual(errors, [], "Browser runtime errors");
  const report = {
    base_url: base,
    recorded_at: new Date().toISOString(),
    source_sha: provenance.source_sha,
    release_sha: provenance.release_sha,
    passed: steps.length,
    total: steps.length,
    scope:
      "Actual own-app headless Chrome, local model and isolated PDF worker; no mocked network",
    runtime_errors: errors,
    steps,
  };
  await mkdir("evals", { recursive: true });
  await writeFile("evals/browser.json", JSON.stringify(report, null, 2) + "\n");
  console.log("Completed", steps.length, "browser checks");
} catch (error) {
  await page
    .screenshot({ path: `${out}/failure.png`, fullPage: true })
    .catch(() => {});
  throw error;
} finally {
  await context.close();
  await browser.close();
}
