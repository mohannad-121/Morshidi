import { createHash } from "node:crypto";
import { expect, test, type Locator, type Page, type TestInfo } from "@playwright/test";

test.use({ video: "on" });

const RIG_ASSETS = [
  "/brand/mascot/morshidi-mascot.png",
  "/brand/mascot/rig/body-base-mask.svg",
  "/brand/mascot/rig/arm-left-mask.svg",
  "/brand/mascot/rig/arm-right-mask.svg",
  "/brand/mascot/rig/shoulder-restoration.png",
  "/brand/mascot/rig/shoulder-restoration-mask.svg",
  "/brand/mascot/rig/mouth-closed.svg",
  "/brand/mascot/rig/mouth-half.svg",
  "/brand/mascot/rig/mouth-open.svg",
];

async function captureIsolatedBodyScreenshot(body: Locator) {
  const page = body.page();
  await page.evaluate(() => {
    const aura = document.querySelector('[data-testid="mascot-aura"]');
    const mouth = document.querySelector('[data-testid="mascot-mouth-layer"]');
    const underlay = document.querySelector('[data-testid="mascot-shoulder-underlay"]');
    const leftArm = document.querySelector('[data-testid="mascot-arm-left"]');
    const rightArm = document.querySelector('[data-testid="mascot-arm-right"]');
    if (aura) (aura as HTMLElement).style.display = "none";
    if (mouth) (mouth as HTMLElement).style.display = "none";
    if (underlay) (underlay as HTMLElement).style.display = "none";
    if (leftArm) (leftArm as HTMLElement).style.display = "none";
    if (rightArm) (rightArm as HTMLElement).style.display = "none";
  });
  const screenshot = await body.screenshot({ animations: "disabled" });
  await page.evaluate(() => {
    const aura = document.querySelector('[data-testid="mascot-aura"]');
    const mouth = document.querySelector('[data-testid="mascot-mouth-layer"]');
    const underlay = document.querySelector('[data-testid="mascot-shoulder-underlay"]');
    const leftArm = document.querySelector('[data-testid="mascot-arm-left"]');
    const rightArm = document.querySelector('[data-testid="mascot-arm-right"]');
    if (aura) (aura as HTMLElement).style.display = "";
    if (mouth) (mouth as HTMLElement).style.display = "";
    if (underlay) (underlay as HTMLElement).style.display = "";
    if (leftArm) (leftArm as HTMLElement).style.display = "";
    if (rightArm) (rightArm as HTMLElement).style.display = "";
  });
  return screenshot;
}

async function attachStateScreenshot(
  locator: Locator,
  name: string,
  testInfo: TestInfo,
) {
  const screenshot = await locator.screenshot({ animations: "disabled" });
  await testInfo.attach(`${name}.png`, { body: screenshot, contentType: "image/png" });
  return screenshot;
}

async function computedTransform(locator: Locator) {
  return locator.evaluate((element) => getComputedStyle(element).transform);
}

async function expectJointConnected(bodyJoint: Locator, armJoint: Locator) {
  const [bodyBox, armBox] = await Promise.all([bodyJoint.boundingBox(), armJoint.boundingBox()]);
  expect(bodyBox).not.toBeNull();
  expect(armBox).not.toBeNull();
  expect(Math.abs(bodyBox!.x - armBox!.x)).toBeLessThanOrEqual(1.2);
  expect(Math.abs(bodyBox!.y - armBox!.y)).toBeLessThanOrEqual(1.2);
}

async function setAssistantLevel(page: Page, level: number) {
  await page.getByTestId("assistant-audio-level").fill(level.toString());
}

test("verifies mouth states, stable torso, connected shoulder pivots, gestures, return to idle, and interruption", async ({
  page,
}, testInfo) => {
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => failedRequests.push(request.url()));

  await page.goto("/dev/voice-mascot-preview");
  const mascot = page.getByTestId("animated-morshidi-mascot");
  const rig = page.getByTestId("mascot-body-container");
  const body = page.getByTestId("mascot-body-base");
  const leftArm = page.getByTestId("mascot-arm-left");
  const rightArm = page.getByTestId("mascot-arm-right");

  await expect(mascot).toBeVisible();
  await expect(mascot.locator("img")).toHaveCount(7);
  await expect
    .poll(() =>
      mascot.locator("img").evaluateAll((images) =>
        images.every((image) => (image as HTMLImageElement).complete),
      ),
    )
    .toBe(true);

  for (const asset of RIG_ASSETS) {
    const response = await page.request.get(asset);
    expect(response.status(), asset).toBe(200);
  }

  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");
  await expect(body).toHaveCSS("transform", "none");
  await expect(leftArm).toHaveCSS("transform", "none");
  await expect(rightArm).toHaveCSS("transform", "none");
  const idleBody = await captureIsolatedBodyScreenshot(body);
  await attachStateScreenshot(rig, "01-idle-closed", testInfo);

  await page.getByRole("button", { name: "speaking" }).click();
  await page.getByRole("button", { name: "none", exact: true }).click();
  await setAssistantLevel(page, 0.08);
  await expect(mascot).toHaveAttribute("data-mouth-state", "half");
  await expect(mascot.locator('[data-mouth-frame="half"]')).toHaveCSS("opacity", "1");
  await expect(body).toHaveCSS("transform", "none");
  expect((await captureIsolatedBodyScreenshot(body)).equals(idleBody)).toBe(true);
  await attachStateScreenshot(rig, "02-low-speech-half-mouth", testInfo);

  await setAssistantLevel(page, 0.3);
  await expect(mascot).toHaveAttribute("data-mouth-state", "open");
  await expect(mascot.locator('[data-mouth-frame="open"]')).toHaveCSS("opacity", "1");
  expect((await captureIsolatedBodyScreenshot(body)).equals(idleBody)).toBe(true);
  await attachStateScreenshot(rig, "03-high-speech-open-mouth", testInfo);

  const leftBefore = await leftArm.boundingBox();
  await page.getByRole("button", { name: "left", exact: true }).click();
  await expect.poll(() => computedTransform(leftArm)).not.toBe("none");
  const leftAfter = await leftArm.boundingBox();
  expect(leftBefore).not.toBeNull();
  expect(leftAfter).not.toBeNull();
  expect(
    Math.max(
      Math.abs(leftAfter!.x - leftBefore!.x),
      Math.abs(leftAfter!.y - leftBefore!.y),
    ),
  ).toBeGreaterThan(1);
  await expectJointConnected(page.getByTestId("body-joint-left"), page.getByTestId("arm-joint-left"));
  await expect(body).toHaveCSS("transform", "none");
  await attachStateScreenshot(rig, "04-left-hand-gesture", testInfo);

  await page.getByRole("button", { name: "right", exact: true }).click();
  await expect.poll(() => computedTransform(rightArm)).not.toBe("none");
  await expectJointConnected(
    page.getByTestId("body-joint-right"),
    page.getByTestId("arm-joint-right"),
  );
  await attachStateScreenshot(rig, "05-right-hand-gesture", testInfo);

  await page.getByRole("button", { name: "listening" }).click();
  await page.getByRole("button", { name: "none", exact: true }).click();
  await setAssistantLevel(page, 0);
  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");
  await expect(leftArm).toHaveCSS("transform", "none");
  await expect(rightArm).toHaveCSS("transform", "none");
  await expect(body).toHaveCSS("transform", "none");
  await attachStateScreenshot(rig, "06-returned-to-idle", testInfo);

  await page.getByRole("button", { name: "speaking" }).click();
  await page.getByRole("button", { name: "auto", exact: true }).click();
  await setAssistantLevel(page, 0.3);
  await expect(mascot).toHaveAttribute("data-mouth-state", "open");
  await page.getByRole("button", { name: "listening" }).click();
  await setAssistantLevel(page, 0);
  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");
  await expect(leftArm).toHaveCSS("animation-name", "none");
  await expect(rightArm).toHaveCSS("animation-name", "none");
  await expect.poll(() => computedTransform(leftArm)).toBe("none");
  await expect.poll(() => computedTransform(rightArm)).toBe("none");
  await attachStateScreenshot(rig, "07-interrupted-closed", testInfo);

  expect(createHash("sha256").update(idleBody).digest("hex")).toMatch(/^[a-f0-9]{64}$/);
  expect(failedRequests).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("automatic gestures are occasional and keep the shoulder joints fixed", async ({ page }) => {
  await page.goto("/dev/voice-mascot-preview");
  await page.getByRole("button", { name: "speaking" }).click();
  await setAssistantLevel(page, 0.3);

  const leftArm = page.getByTestId("mascot-arm-left");
  const animationName = await leftArm.evaluate((element) => getComputedStyle(element).animationName);
  expect(animationName).toBe("mascot-gesture-left");

  const samples = await leftArm.evaluate((element) => {
    const animation = element.getAnimations()[0];
    if (!animation) return [];
    animation.pause();
    return [0, 800, 1520, 2400, 4000, 7200].map((time) => {
      animation.currentTime = time;
      return getComputedStyle(element).transform;
    });
  });

  expect(new Set(samples).size).toBeGreaterThan(2);
  expect(samples.filter((sample) => sample === "none" || sample === "matrix(1, 0, 0, 1, 0, 0)").length).toBeGreaterThanOrEqual(3);
  await expectJointConnected(page.getByTestId("body-joint-left"), page.getByTestId("arm-joint-left"));
});

test("reduced motion freezes both arms while preserving discrete audio mouth state", async ({ browser }, testInfo) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto("/dev/voice-mascot-preview");
  await page.getByRole("button", { name: "speaking" }).click();
  await setAssistantLevel(page, 0.3);

  const mascot = page.getByTestId("animated-morshidi-mascot");
  const body = page.getByTestId("mascot-body-base");
  const leftArm = page.getByTestId("mascot-arm-left");
  const rightArm = page.getByTestId("mascot-arm-right");
  const bodyBefore = await body.screenshot({ animations: "disabled" });

  await expect(mascot).toHaveAttribute("data-mouth-state", "open");
  await expect(leftArm).toHaveCSS("animation-name", "none");
  await expect(rightArm).toHaveCSS("animation-name", "none");
  await expect(leftArm).toHaveCSS("transform", "none");
  await expect(rightArm).toHaveCSS("transform", "none");
  await page.waitForTimeout(500);
  expect((await body.screenshot({ animations: "disabled" })).equals(bodyBefore)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await attachStateScreenshot(page.getByTestId("mascot-body-container"), "08-reduced-motion", testInfo);
  await context.close();
});

test("real voice modal shell portals above navigation without starting a voice session", async ({ page }) => {
  await page.goto("/dev/voice-mascot-preview");
  await page.getByRole("button", { name: "Open real modal shell" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("animated-morshidi-mascot")).toBeVisible();
  const evidence = await dialog.evaluate((element) => ({
    parentIsBody: element.parentElement === document.body,
    zIndex: Number(getComputedStyle(element).zIndex),
    bounds: element.getBoundingClientRect().toJSON(),
    viewport: { width: innerWidth, height: innerHeight },
  }));

  expect(evidence.parentIsBody).toBe(true);
  expect(evidence.zIndex).toBeGreaterThanOrEqual(100);
  expect(evidence.bounds.x).toBe(0);
  expect(evidence.bounds.y).toBe(0);
  expect(evidence.bounds.width).toBe(evidence.viewport.width);
  expect(evidence.bounds.height).toBe(evidence.viewport.height);
});
