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
    return [0, 1500, 3200, 3900, 4400, 5600].map((time) => {
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

test("Test A: mouth articulates across syllables during speech, closes on silence, and ignores mic", async ({ page }, testInfo) => {
  await page.goto("/dev/voice-mascot-preview");
  const mascot = page.getByTestId("animated-morshidi-mascot");
  const rig = page.getByTestId("mascot-body-container");

  // 1. Idle is closed
  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");

  // 2. Student mic alone does not trigger speech mouth
  await page.getByRole("button", { name: "listening" }).click();
  await page.getByTestId("microphone-audio-level").fill("0.8");
  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");
  await expect(mascot).toHaveAttribute("data-speaking", "false");

  // 3. Start speech
  await page.getByRole("button", { name: "speaking" }).click();
  await setAssistantLevel(page, 0.25);
  await expect(mascot).toHaveAttribute("data-speaking", "true");

  // Verify multiple mouth state transitions occur over continuous speech
  const observedStates = new Set<string>();
  const deadline = Date.now() + 800;
  while (Date.now() < deadline) {
    const state = await mascot.getAttribute("data-mouth-state");
    if (state) observedStates.add(state);
    if (observedStates.size >= 3) break;
    await page.waitForTimeout(30);
  }
  expect(observedStates.has("open")).toBe(true);
  expect(observedStates.has("half")).toBe(true);
  expect(observedStates.has("closed")).toBe(true);
  expect(observedStates.size).toBeGreaterThanOrEqual(3);
  await attachStateScreenshot(rig, "test-a-speaking-cadence", testInfo);

  // 4. Return to silence closes immediately
  await setAssistantLevel(page, 0);
  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");
});

test("Test B: right hand gestures early (>= 6px displacement within 1.5s) during spoken response", async ({ page }, testInfo) => {
  await page.goto("/dev/voice-mascot-preview");
  const mascot = page.getByTestId("animated-morshidi-mascot");
  const rig = page.getByTestId("mascot-body-container");
  const rightArm = page.getByTestId("mascot-arm-right");
  const body = page.getByTestId("mascot-body-base");

  // Verify initial rest
  await expect(mascot).toHaveAttribute("data-mouth-state", "closed");
  await expect(rightArm).toHaveCSS("transform", "none");

  // Start speaking without overrides (gesture="auto")
  await page.getByRole("button", { name: "speaking" }).click();
  await setAssistantLevel(page, 0.3);

  // Measure right arm animation during the first 1.5s (apex is at 1.1s = 1100ms)
  const maxDisplacement = await rightArm.evaluate((element) => {
    const animation = element.getAnimations()[0];
    if (!animation) return 0;
    animation.pause();
    const bounds = [0, 400, 800, 1100, 1500].map((t) => {
      animation.currentTime = t;
      return element.getBoundingClientRect();
    });
    const rest = bounds[0];
    return Math.max(...bounds.map((b) => Math.hypot(b.x - rest.x, b.y - rest.y)));
  });

  // Must displace visibly by >= 6px at standard desktop rendering (natural visible motion)
  expect(maxDisplacement).toBeGreaterThanOrEqual(6);

  // Torso remains stationary
  await expect(body).toHaveCSS("transform", "none");
  await expectJointConnected(page.getByTestId("body-joint-right"), page.getByTestId("arm-joint-right"));
  await attachStateScreenshot(rig, "test-b-early-right-gesture", testInfo);
});

test("Test C: longer speech alternates gestures with natural rest pauses and no simultaneous flailing", async ({ page }, testInfo) => {
  await page.goto("/dev/voice-mascot-preview");
  await page.getByRole("button", { name: "speaking" }).click();
  await setAssistantLevel(page, 0.3);

  const leftArm = page.getByTestId("mascot-arm-left");
  const rightArm = page.getByTestId("mascot-arm-right");
  const rig = page.getByTestId("mascot-body-container");

  // Sample both arms over a full cycle (6.4s = 6400ms)
  const timeline = await Promise.all([
    leftArm.evaluate((element) => {
      const anim = element.getAnimations()[0];
      if (!anim) return [];
      anim.pause();
      // Sample times: 0, 1100 (right apex), 2700 (rest pause), 3900 (left apex), 5600 (rest pause)
      return [0, 1100, 2700, 3900, 5600].map((t) => {
        anim.currentTime = t;
        return getComputedStyle(element).transform;
      });
    }),
    rightArm.evaluate((element) => {
      const anim = element.getAnimations()[0];
      if (!anim) return [];
      anim.pause();
      return [0, 1100, 2700, 3900, 5600].map((t) => {
        anim.currentTime = t;
        return getComputedStyle(element).transform;
      });
    }),
  ]);

  const [leftTransforms, rightTransforms] = timeline;
  const isRest = (tf: string) => tf === "none" || tf === "matrix(1, 0, 0, 1, 0, 0)";

  // At t=0: both at rest
  expect(isRest(leftTransforms[0])).toBe(true);
  expect(isRest(rightTransforms[0])).toBe(true);

  // At t=1100ms: right arm gestures, left arm remains at rest
  expect(!isRest(rightTransforms[1])).toBe(true);
  expect(isRest(leftTransforms[1])).toBe(true);

  // At t=2700ms: both arms in natural rest pause
  expect(isRest(leftTransforms[2])).toBe(true);
  expect(isRest(rightTransforms[2])).toBe(true);

  // At t=3900ms: left arm gestures, right arm remains at rest
  expect(!isRest(leftTransforms[3])).toBe(true);
  expect(isRest(rightTransforms[3])).toBe(true);

  // At t=5600ms: both arms in natural rest pause
  expect(isRest(leftTransforms[4])).toBe(true);
  expect(isRest(rightTransforms[4])).toBe(true);

  // Joints remain connected
  await expectJointConnected(page.getByTestId("body-joint-left"), page.getByTestId("arm-joint-left"));
  await expectJointConnected(page.getByTestId("body-joint-right"), page.getByTestId("arm-joint-right"));
  await attachStateScreenshot(rig, "test-c-alternating-gestures", testInfo);
});
