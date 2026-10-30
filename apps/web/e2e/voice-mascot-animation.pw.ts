import { expect, test, type Locator } from "@playwright/test";

type MotionSample = {
  transform: string;
  animationName: string;
  animationPlayState: string;
  top: number;
  left: number;
};

async function sampleMotion(locator: Locator): Promise<MotionSample> {
  return locator.evaluate((element) => {
    const styles = getComputedStyle(element);
    const bounds = element.getBoundingClientRect();

    return {
      transform: styles.transform,
      animationName: styles.animationName,
      animationPlayState: styles.animationPlayState,
      top: bounds.top,
      left: bounds.left,
    };
  });
}

async function sampleAcrossFrames(locator: Locator, delays: number[]) {
  const samples = [await sampleMotion(locator)];
  for (const delay of delays) {
    await locator.page().waitForTimeout(delay);
    samples.push(await sampleMotion(locator));
  }
  return samples;
}

function verticalTravel(samples: MotionSample[]) {
  const positions = samples.map((sample) => sample.top);
  return Math.max(...positions) - Math.min(...positions);
}

test("renders the official mascot with visibly moving idle and speaking cadences", async ({ page }, testInfo) => {
  await page.goto("/dev/voice-mascot-preview");

  const mascot = page.getByTestId("animated-morshidi-mascot");
  const body = page.getByTestId("mascot-body-container");
  const image = page.getByTestId("morshidi-mascot-unified").locator("img");

  await expect(mascot).toBeVisible();
  await expect(image).toHaveAttribute("src", /morshidi-mascot\.png/);
  await expect(image).toHaveJSProperty("complete", true);

  const idleSamples = await sampleAcrossFrames(body, [600, 600, 600, 600, 600, 600]);
  expect(idleSamples[0].animationName).toBe("mascot-breathe");
  expect(idleSamples[0].animationPlayState).toBe("running");
  expect(new Set(idleSamples.map((sample) => sample.transform)).size).toBeGreaterThan(2);
  expect(verticalTravel(idleSamples)).toBeGreaterThanOrEqual(4.5);

  await page.getByRole("button", { name: "speaking" }).click();
  await expect(mascot).toHaveAttribute("data-speaking", "true");
  const speakingSamples = await sampleAcrossFrames(body, [400, 400, 400, 400, 400, 400]);
  expect(speakingSamples[0].animationName).toBe("mascot-speaking");
  expect(speakingSamples[0].animationPlayState).toBe("running");
  expect(new Set(speakingSamples.map((sample) => sample.transform)).size).toBeGreaterThan(3);
  expect(verticalTravel(speakingSamples)).toBeGreaterThanOrEqual(5.5);
  expect(speakingSamples.some((sample) => Math.abs(sample.left - speakingSamples[0].left) >= 1)).toBe(true);

  console.log(
    `[mascot-motion] ${JSON.stringify({
      idleVerticalTravel: Number(verticalTravel(idleSamples).toFixed(2)),
      idleTransforms: new Set(idleSamples.map((sample) => sample.transform)).size,
      speakingVerticalTravel: Number(verticalTravel(speakingSamples).toFixed(2)),
      speakingHorizontalTravel: Number(
        (
          Math.max(...speakingSamples.map((sample) => sample.left)) -
          Math.min(...speakingSamples.map((sample) => sample.left))
        ).toFixed(2),
      ),
      speakingTransforms: new Set(speakingSamples.map((sample) => sample.transform)).size,
    })}`,
  );

  await testInfo.attach("motion-samples.json", {
    body: JSON.stringify({ idleSamples, speakingSamples }, null, 2),
    contentType: "application/json",
  });

  await page.getByRole("button", { name: "listening" }).click();
  await expect(mascot).toHaveAttribute("data-speaking", "false");
  await expect(body).toHaveCSS("animation-name", "mascot-breathe");
});

test("assistant audio activates speaking while microphone audio remains isolated", async ({ page }) => {
  await page.goto("/dev/voice-mascot-preview");
  const mascot = page.getByTestId("animated-morshidi-mascot");
  const body = page.getByTestId("mascot-body-container");

  await page.getByRole("button", { name: "listening" }).click();
  await page.getByTestId("microphone-audio-level").fill("0.85");
  await expect(mascot).toHaveAttribute("data-speaking", "false");
  await expect(body).toHaveCSS("animation-name", "mascot-breathe");

  await page.getByTestId("assistant-audio-level").fill("0.22");
  await expect(mascot).toHaveAttribute("data-speaking", "true");
  await expect(body).toHaveCSS("animation-name", "mascot-speaking");

  await page.getByRole("button", { name: "delegating" }).click();
  await expect(mascot).toHaveAttribute("data-speaking", "false");
  await expect(body).toHaveCSS("animation-name", "mascot-breathe");

  await page.getByRole("button", { name: "ended" }).click();
  await expect(mascot).toHaveAttribute("data-speaking", "false");
});

test("real voice modal shell portals above the global navigation without starting a call", async ({ page }) => {
  await page.goto("/dev/voice-mascot-preview");
  await page.getByRole("button", { name: "Open real modal shell" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("animated-morshidi-mascot")).toBeVisible();

  const modalEvidence = await dialog.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      parentIsBody: element.parentElement === document.body,
      zIndex: Number(getComputedStyle(element).zIndex),
      top: bounds.top,
      left: bounds.left,
      width: bounds.width,
      height: bounds.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    };
  });

  expect(modalEvidence.parentIsBody).toBe(true);
  expect(modalEvidence.zIndex).toBeGreaterThanOrEqual(100);
  expect(modalEvidence.top).toBe(0);
  expect(modalEvidence.left).toBe(0);
  expect(modalEvidence.width).toBe(modalEvidence.viewportWidth);
  expect(modalEvidence.height).toBe(modalEvidence.viewportHeight);
});

test("reduced motion freezes mascot transforms", async ({ browser }) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto("/dev/voice-mascot-preview");

  const body = page.getByTestId("mascot-body-container");
  const samples = await sampleAcrossFrames(body, [300, 600]);
  expect(samples[0].animationName).toBe("none");
  expect(new Set(samples.map((sample) => sample.transform)).size).toBe(1);
  expect(verticalTravel(samples)).toBeLessThan(0.1);

  await expect(page.getByTestId("voice-mascot-preview")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await context.close();
});
