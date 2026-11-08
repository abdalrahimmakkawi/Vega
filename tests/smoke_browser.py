"""Local WebGL smoke check for a saved connected assembly."""

from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=str(CHROME),
        headless=True,
        args=["--enable-webgl", "--use-angle=swiftshader", "--disable-gpu-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8711/", wait_until="domcontentloaded")
    page.locator("#generate").wait_for()
    page.wait_for_function("!document.querySelector('#generate').disabled")
    if len(sys.argv) > 1:
        page.locator("#history").select_option(sys.argv[1])
    else:
        page.locator("#history").select_option(index=1)
    page.locator("#mesh-source").filter(has_text="multi-body concept").wait_for(timeout=120_000)
    if len(sys.argv) > 1:
        assert page.locator("#history").input_value() == sys.argv[1]
    assert "Conditional ideal mixer balance" in page.locator("#topology-panel").inner_text()
    assert "Conditional fluid-dynamics stations" in page.locator("#topology-panel").inner_text()
    assert "Assumed mixed total-pressure recovery" in page.locator("#topology-panel").inner_text()
    assert page.locator("#topology-panel .evidence-table tr").count() == 7
    assert "Ground-structure frame optimization" in page.locator("#topology-panel").inner_text()
    assert "members selected" in page.locator("#topology-panel").inner_text()
    contract=page.locator("#contract-panel").inner_text()
    assert "11/11 connection checks" in contract
    assert "22 exported bodies" in contract
    assert "3 registered fluid routes" in contract
    assert page.locator("#render-style").input_value() == "solid"
    assert page.locator("#cutaway").is_checked()
    page.locator("#comparison-panel strong").wait_for(timeout=30_000)
    assert "Checking" not in page.locator("#comparison-panel").inner_text()
    assert "Assembly length" in page.locator("#comparison-panel").inner_text()
    study_points = int(page.locator("#model").get_attribute("data-study-points"))
    assert study_points > 10_000
    assert not errors, errors
    page.screenshot(path=str(ROOT / "screenshots" / "vega-ui-native-loaded.png"))
    page.locator("#render-style").select_option("interior")
    page.wait_for_timeout(250)
    interior=json.loads(page.locator("#model").get_attribute("data-render-stats"))
    assert interior["mode"] == "interior"
    page.locator("#render-style").select_option("solid")
    page.wait_for_timeout(250)
    solid=json.loads(page.locator("#model").get_attribute("data-render-stats"))
    assert solid["mode"] == "solid"
    assert interior["fitScale"] > solid["fitScale"]
    print({"native_mesh": page.locator("#mesh-source").inner_text(), "study_points": study_points, "page_errors": errors})
    browser.close()
