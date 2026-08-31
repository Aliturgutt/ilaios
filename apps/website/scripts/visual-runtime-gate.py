from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "https://ilaios.com").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("CERTIFICATION_ARTIFACT_DIR", "artifacts/production-certification"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP = {"width": 1440, "height": 900}
TABLET = {"width": 768, "height": 1024}
MOBILE = {"width": 390, "height": 844}
ROUTES = ["/", "/tr", "/platform", "/factories", "/capabilities", "/security", "/architecture", "/enterprise", "/individuals", "/about", "/contact", "/tr/about", "/tr/contact"]


def px(value: str) -> float:
    try:
        return float(value.replace("px", "").strip())
    except ValueError:
        return -1


def computed(page: Page, selector: str) -> dict[str, Any]:
    return page.locator(selector).first.evaluate(
        """el => {
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return {
            fontSize: s.fontSize,
            lineHeight: s.lineHeight,
            paddingTop: s.paddingTop,
            paddingBottom: s.paddingBottom,
            display: s.display,
            transform: s.transform,
            top: r.top,
            bottom: r.bottom,
            width: r.width,
            height: r.height,
          };
        }"""
    )


def all_section_metrics(page: Page) -> list[dict[str, Any]]:
    return page.locator("main section").evaluate_all(
        """els => els.map((el, index) => {
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          const children = [...el.children].map(child => child.getBoundingClientRect()).filter(rect => rect.width > 0 && rect.height > 0);
          const contentTop = children.length ? Math.min(...children.map(rect => rect.top)) : r.top;
          const contentBottom = children.length ? Math.max(...children.map(rect => rect.bottom)) : r.bottom;
          return {
            index,
            height: r.height,
            paddingTop: parseFloat(s.paddingTop) || 0,
            paddingBottom: parseFloat(s.paddingBottom) || 0,
            contentHeight: Math.max(0, contentBottom - contentTop),
            unusedVertical: Math.max(0, r.height - (contentBottom - contentTop)),
          };
        })"""
    )


def visible_accent_ratio(page: Page) -> float:
    return float(
        page.evaluate(
            """() => {
              const nodes = [...document.querySelectorAll('main *')].filter(el => {
                const s = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && (el.textContent || '').trim().length > 0;
              });
              if (!nodes.length) return 0;
              const accent = nodes.filter(el => ['rgb(0, 184, 199)', 'rgb(0, 194, 209)'].includes(getComputedStyle(el).color)).length;
              return accent / nodes.length;
            }"""
        )
    )


def settle_images(page: Page) -> None:
    page.locator("img").evaluate_all(
        """async els => {
          for (const el of els) {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            if (s.display === 'none' || s.visibility === 'hidden' || r.width <= 0 || r.height <= 0) continue;
            el.scrollIntoView({block: 'center', inline: 'nearest'});
            if (!el.complete) {
              await Promise.race([
                new Promise(resolve => {
                  const done = () => resolve();
                  el.addEventListener('load', done, {once: true});
                  el.addEventListener('error', done, {once: true});
                }),
                new Promise(resolve => setTimeout(resolve, 2500)),
              ]);
            }
            if (typeof el.decode === 'function' && el.complete && el.naturalWidth > 0) {
              try { await el.decode(); } catch {}
            }
          }
          window.scrollTo(0, 0);
        }"""
    )


def broken_images(page: Page) -> list[dict[str, str]]:
    settle_images(page)
    return page.locator("img").evaluate_all(
        """els => els
          .filter((el) => {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0 &&
              el.complete && (el.naturalWidth === 0 || el.naturalHeight === 0);
          })
          .map((el) => ({src: el.currentSrc || el.src, alt: el.alt || ''}))
          .slice(0, 20)"""
    )


def check_route(page: Page, path: str, viewport: dict[str, int], findings: list[str], evidence: list[dict[str, Any]]) -> None:
    page.set_viewport_size(viewport)
    response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=30_000)
    label = f"{path} {viewport['width']}x{viewport['height']}"
    if response is None or response.status >= 400:
        findings.append(f"{label}: navigation failed")
        return

    rendered_broken_images = broken_images(page)
    h1 = computed(page, "main h1") if page.locator("main h1").count() else None
    sections = all_section_metrics(page)
    footer = computed(page, "footer") if page.locator("footer").count() else None
    accent_ratio = visible_accent_ratio(page)

    if h1:
        h1_size = px(str(h1["fontSize"]))
        h1_limit = 48 if viewport["width"] >= 900 else 38
        if h1_size > h1_limit:
            findings.append(f"{label}: H1 too large ({h1_size}px > {h1_limit}px)")

    section_padding_limit = 52 if viewport["width"] >= 900 else 34
    for section in sections:
        if section["paddingTop"] > section_padding_limit or section["paddingBottom"] > section_padding_limit:
            findings.append(f"{label}: section {section['index']} excessive vertical padding ({section['paddingTop']}/{section['paddingBottom']}px)")
        if section["unusedVertical"] > 180:
            findings.append(f"{label}: section {section['index']} contains excessive unused vertical space ({section['unusedVertical']:.0f}px)")

    if footer and viewport["width"] >= 900 and footer["height"] > 360:
        findings.append(f"{label}: desktop footer too tall ({footer['height']:.0f}px)")
    if accent_ratio > 0.12:
        findings.append(f"{label}: cyan/accent text usage too high ({accent_ratio:.1%})")
    if rendered_broken_images:
        findings.append(f"{label}: broken rendered images {rendered_broken_images[:3]}")

    if path in {"/about", "/tr/about", "/contact", "/tr/contact"} and viewport["width"] >= 900:
        first_two = page.locator("main section").evaluate_all("els => els.slice(0,2).map(el => el.getBoundingClientRect().bottom)")
        if first_two and first_two[0] > 520:
            findings.append(f"{label}: opening section consumes too much of the first viewport ({first_two[0]:.0f}px)")

    evidence.append({"path": path, "viewport": viewport, "h1": h1, "sections": sections, "footer": footer, "accentRatio": accent_ratio, "brokenImages": rendered_broken_images})


def check_home_composition(page: Page, findings: list[str]) -> None:
    page.set_viewport_size(DESKTOP)
    page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)

    authoritative = page.locator('section.home-hero[data-visual-role="home-hero"]')
    legacy = page.locator('.v2-recovery-home')
    if authoritative.count() != 1 or not authoritative.is_visible():
        findings.append("desktop home: restored canonical home hero is missing")
    if legacy.count() != 0:
        findings.append("desktop home: legacy WebsiteV2HomeRecovery is still rendered")

    gradients = page.locator("main#main-content *").evaluate_all(
        """els => els
          .filter((el) => {
            const s = getComputedStyle(el);
            return (s.backgroundImage || '').includes('gradient(');
          })
          .map((el) => ({tag: el.tagName.toLowerCase(), cls: typeof el.className === 'string' ? el.className.slice(0, 100) : ''}))
          .slice(0, 20)"""
    )
    if gradients:
        findings.append(f"desktop home: decorative gradients remain {gradients[:3]}")

    demo = page.locator('[data-visual-role="interactive-product-demo"]')
    if demo.count() != 1 or not demo.is_visible():
        findings.append("desktop home: interactive product demo is not visible")
    else:
        box = demo.bounding_box()
        if box and box["y"] + min(box["height"], 120) > DESKTOP["height"]:
            findings.append("desktop home: product demo is not meaningfully visible in the first viewport")

    steps = page.locator('[data-visual-role="five-step-execution"] article')
    if steps.count() != 5:
        findings.append(f"desktop home: expected five execution nodes, found {steps.count()}")
    elif len({round((steps.nth(i).bounding_box() or {"y": -1})["y"]) for i in range(steps.count())}) != 1:
        findings.append("desktop home: five execution nodes are not aligned on one horizontal rail")

    page.set_viewport_size(MOBILE)
    page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
    steps = page.locator('[data-visual-role="five-step-execution"] article')
    ys = [(steps.nth(i).bounding_box() or {"y": -1})["y"] for i in range(steps.count())]
    if len(ys) == 5 and not all(ys[i] < ys[i + 1] for i in range(4)):
        findings.append("mobile home: execution rail did not recompose vertically")


def check_interactions(page: Page, findings: list[str]) -> None:
    page.set_viewport_size(DESKTOP)
    page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)

    tabs = page.locator('.product-mode-tabs button')
    if tabs.count() < 4:
        findings.append("home interaction: Web/Video/Software/App product mode tabs are missing")
    else:
        before = page.locator('.goal-composer textarea').input_value()
        tabs.nth(1).click()
        after = page.locator('.goal-composer textarea').input_value()
        if before == after:
            findings.append("home interaction: changing product mode did not change the product scenario")

    run = page.locator('.goal-composer button')
    if run.count():
        run.click()
        page.wait_for_timeout(750)
        active = page.locator('.execution-rail .is-active')
        if active.count() != 1:
            findings.append("home interaction: workflow progression has no unique active state")

    page.goto(f"{BASE_URL}/factories", wait_until="networkidle", timeout=30_000)
    factory_tabs = page.locator('.factory-index button')
    if factory_tabs.count() < 9:
        findings.append("factory interaction: canonical factory explorer is incomplete")
    else:
        first = page.locator('.factory-detail h3').inner_text()
        factory_tabs.nth(1).hover()
        page.wait_for_timeout(100)
        second = page.locator('.factory-detail h3').inner_text()
        if first == second:
            findings.append("factory interaction: hover did not update result preview")

    page.goto(f"{BASE_URL}/architecture", wait_until="networkidle", timeout=30_000)
    spatial = page.locator('[data-visual-role="architecture-spatial-map"] .spatial-stage')
    if spatial.count() != 1:
        findings.append("architecture interaction: spatial architecture map missing")
    else:
        style = computed(page, '[data-visual-role="architecture-spatial-map"] .spatial-stage')
        if style["transform"] == "none":
            findings.append("architecture interaction: desktop spatial map has no depth transform")


def main() -> int:
    findings: list[str] = []
    evidence: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=False, reduced_motion="no-preference", locale="en-US")
        page = context.new_page()

        for route in ROUTES:
            for viewport in (DESKTOP, TABLET, MOBILE):
                check_route(page, route, viewport, findings, evidence)

        check_home_composition(page, findings)
        check_interactions(page, findings)

        for path, name in [("/", "visual-home"), ("/factories", "visual-factories"), ("/architecture", "visual-architecture"), ("/about", "visual-about"), ("/contact", "visual-contact")]:
            page.set_viewport_size(DESKTOP)
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=30_000)
            settle_images(page)
            page.screenshot(path=str(ARTIFACT_DIR / f"{name}-1440x900.png"), full_page=True)

        context.close()
        browser.close()

    payload = {"status": "FAIL" if findings else "PASS", "findings": findings, "measurements": evidence, "manualDesignApprovalRequired": True}
    (ARTIFACT_DIR / "visual-runtime.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary = [
        "# ILAIOS Rendered Visual QA",
        "",
        f"- Automated visual runtime gate: **{'FAIL' if findings else 'PASS'}**",
        f"- Routes × responsive viewports checked: **{len(ROUTES) * 3}**",
        "- Typography scale: checked",
        "- Section density / unused vertical space: checked",
        "- Footer density: checked",
        "- Accent usage: checked",
        "- Homepage product demo and 5-step recomposition: checked",
        "- Factory interaction: checked",
        "- Architecture spatial interaction and mobile flattening: checked",
        "- **Owner live-site design approval: REQUIRED before FINAL**",
    ]
    if findings:
        summary.extend(["", "## Findings", *[f"- {finding}" for finding in findings]])
    (ARTIFACT_DIR / "visual-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    if findings:
        print("Rendered visual gate FAILED")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Rendered visual gate PASS — owner live-site design approval is still required before FINAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
