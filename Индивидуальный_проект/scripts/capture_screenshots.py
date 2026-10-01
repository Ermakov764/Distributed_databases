#!/usr/bin/env python3
"""
Реальные скриншоты Swagger UI + терминальных JSON-ответов стенда.
Ничего не рисует вручную: только page.screenshot() браузера и вывод curl в PNG через терминал.

Запуск (стенд уже поднят, uvicorn на :8000):
  source .venv/bin/activate
  pip install playwright
  playwright install chromium
  python scripts/capture_screenshots.py
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
BASE = "http://127.0.0.1:8000"


def sh(cmd: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True,
        check=check,
        cwd=str(ROOT),
    )


def wait_api(timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = sh(f"curl -sf {BASE}/health", check=False)
            if r.returncode == 0:
                return
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit("API не отвечает на /health")


def save_terminal_png(name: str, title: str, body: str, page=None) -> Path:
    """Реальный HTML-рендер текста ответа в браузере → PNG (не ручная отрисовка таблицы)."""
    OUT.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body {{ margin:0; background:#0d1117; color:#e6edf3;
         font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  .bar {{ background:#161b22; border-bottom:1px solid #30363d; padding:10px 16px; font-size:14px; }}
  pre {{ margin:0; padding:16px; white-space:pre-wrap; word-break:break-word; font-size:13px; line-height:1.45; }}
</style></head>
<body>
  <div class="bar">{title}</div>
  <pre id="c"></pre>
  <script>
    document.getElementById('c').textContent = {json.dumps(body)};
  </script>
</body></html>"""
    html_path = OUT / f"_{name}.html"
    html_path.write_text(html, encoding="utf-8")
    png_path = OUT / f"{name}.png"

    def _shot(pg) -> None:
        pg.goto(html_path.as_uri(), wait_until="domcontentloaded")
        height = pg.evaluate("() => Math.min(Math.max(document.body.scrollHeight, 400), 2400)")
        pg.set_viewport_size({"width": 1280, "height": int(height)})
        time.sleep(0.15)
        pg.screenshot(path=str(png_path), full_page=True)

    if page is not None:
        _shot(page)
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page(viewport={"width": 1280, "height": 900})
            _shot(pg)
            browser.close()
    html_path.unlink(missing_ok=True)
    print(f"  saved {png_path.name}")
    return png_path


def expand_swagger(page) -> None:
    page.goto(f"{BASE}/docs", wait_until="networkidle")
    page.wait_for_selector(".opblock", timeout=30000)
    # раскрыть все операции
    for btn in page.locator(".opblock-summary").all():
        try:
            btn.click(timeout=1000)
            time.sleep(0.05)
        except Exception:
            pass
    time.sleep(0.3)


def try_execute(page, method: str, path_contains: str, body: dict | None = None, path_params: dict | None = None) -> None:
    """Открыть операцию в Swagger, заполнить и Execute."""
    op = page.locator(".opblock").filter(has_text=path_contains).filter(has_text=method.upper()).first
    op.scroll_into_view_if_needed()
    # если свёрнуто — открыть
    if "is-open" not in (op.get_attribute("class") or ""):
        op.locator(".opblock-summary").click()
    time.sleep(0.2)
    try_btn = op.locator("button.try-out__btn")
    if try_btn.count() and "Cancel" not in (try_btn.first.inner_text() or ""):
        try_btn.first.click()
        time.sleep(0.2)
    if path_params:
        for name, value in path_params.items():
            inp = op.locator(f'input[placeholder="{name}"], input[name="{name}"]').first
            if inp.count():
                inp.fill(str(value))
    if body is not None:
        ta = op.locator("textarea.body-param__text, .body-param textarea").first
        if ta.count():
            ta.fill(json.dumps(body, ensure_ascii=False, indent=2))
    exec_btn = op.locator("button.execute").first
    exec_btn.click()
    time.sleep(0.8)


def capture_swagger_flow() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        page.goto(f"{BASE}/docs", wait_until="networkidle")
        page.wait_for_selector(".opblock", timeout=30000)
        page.screenshot(path=str(OUT / "01_swagger_home.png"), full_page=True)
        print("  saved 01_swagger_home.png")

        # Health через UI
        try_execute(page, "get", "/health")
        page.locator(".opblock").filter(has_text="/health").first.screenshot(
            path=str(OUT / "02_swagger_health.png")
        )
        print("  saved 02_swagger_health.png")

        # Warehouses list
        try_execute(page, "get", "/api/{region}/warehouses", path_params={"region": "WEST"})
        page.locator(".opblock").filter(has_text="/api/{region}/warehouses").filter(has_text="GET").first.screenshot(
            path=str(OUT / "03_swagger_warehouses_get.png")
        )
        print("  saved 03_swagger_warehouses_get.png")

        # Products list
        try_execute(page, "get", "/api/{region}/products", path_params={"region": "WEST"})
        page.locator(".opblock").filter(has_text="/api/{region}/products").filter(has_text="GET").first.screenshot(
            path=str(OUT / "04_swagger_products_get.png")
        )
        print("  saved 04_swagger_products_get.png")

        # Create warehouse
        try_execute(
            page,
            "post",
            "/api/{region}/warehouses",
            path_params={"region": "WEST"},
            body={"code": "WH-WEST-SCR", "name": "Склад для скрина"},
        )
        page.locator(".opblock").filter(has_text="/api/{region}/warehouses").filter(has_text="POST").first.screenshot(
            path=str(OUT / "05_swagger_warehouse_post.png")
        )
        print("  saved 05_swagger_warehouse_post.png")

        # Create product
        try_execute(
            page,
            "post",
            "/api/{region}/products",
            path_params={"region": "WEST"},
            body={"sku": "SKU-SCR-1", "title": "Товар для скрина"},
        )
        page.locator(".opblock").filter(has_text="/api/{region}/products").filter(has_text="POST").first.screenshot(
            path=str(OUT / "06_swagger_product_post.png")
        )
        print("  saved 06_swagger_product_post.png")

        # Stock list
        try_execute(page, "get", "/api/{region}/stock", path_params={"region": "WEST"})
        page.locator(".opblock").filter(has_text="/api/{region}/stock").filter(has_text="GET").first.screenshot(
            path=str(OUT / "07_swagger_stock_get.png")
        )
        print("  saved 07_swagger_stock_get.png")

        # Create order on seed warehouse/product (id=1)
        try_execute(
            page,
            "post",
            "/api/{region}/orders",
            path_params={"region": "WEST"},
            body={"warehouse_id": 1, "product_id": 1, "qty": 1},
        )
        page.locator(".opblock").filter(has_text="/api/{region}/orders").filter(has_text="POST").first.screenshot(
            path=str(OUT / "08_swagger_order_post.png")
        )
        print("  saved 08_swagger_order_post.png")

        browser.close()


def capture_from_demo_json() -> None:
    jdir = OUT / "json"
    if not jdir.exists():
        return
    mapping = [
        ("00_health", "GET /health — состояние узлов"),
        ("02_warehouse_create", "POST /api/WEST/warehouses — создание склада"),
        ("05_product_create", "POST /api/WEST/products — создание товара"),
        ("07_stock_create", "POST /api/WEST/stock — создание остатка"),
        ("09_order_create", "POST /api/WEST/orders — создание заявки"),
        ("10_status_DELIVERED", "Цепочка статусов → DELIVERED"),
        ("11_events", "GET events — журнал shipment_events"),
        ("12_cross_region", "Отказ по критерию контура (EAST↔WEST)"),
        ("13_write_fail", "Отказ записи при docker stop west-primary"),
        ("13_read_replica", "Чтение с replica при отказе primary"),
        ("14_health_after_restart", "Health после docker start west-primary"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for stem, title in mapping:
            path = jdir / f"{stem}.json"
            if not path.exists():
                print(f"  skip missing {path.name}")
                continue
            raw = path.read_text(encoding="utf-8")
            try:
                pretty = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            except Exception:
                pretty = raw
            save_terminal_png(f"api_{stem}", title, pretty, page=page)
        browser.close()


def capture_compose_ps() -> None:
    r = sh("docker compose ps", check=False)
    body = (r.stdout or "") + (r.stderr or "")
    save_terminal_png("00_docker_compose_ps", "docker compose ps — 4 узла PostgreSQL", body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wait_api()
    print("== docker compose ps ==")
    capture_compose_ps()
    print("== swagger screenshots ==")
    capture_swagger_flow()
    print("== JSON response screenshots ==")
    capture_from_demo_json()
    print(f"Done → {OUT}")


if __name__ == "__main__":
    main()
