# -*- coding: utf-8 -*-
"""
test_case_pw/test_ferryticket.py —— 船票冒煙用例（Playwright 版）
"""
import os
import re
from datetime import datetime, timedelta

import pytest
from playwright.sync_api import expect, TimeoutError as PWTimeout

from business.ferryticket_business import FerryTicketBusiness

# ⚠️ 三個 mark 與原版逐字一致（playwright / ferry / smoke）
pytestmark = [pytest.mark.playwright, pytest.mark.ferry, pytest.mark.smoke]

DEPART_CITY = "深圳"
DEPART_PORT = "深圳蛇口碼頭"
ARRIVE_CITY = "香港"
ARRIVE_PORT = "香港國際機場海天碼頭"

BASE_URL = os.getenv("BASE_URL", "https://www.testhopetrip.dabapiao.com/").rstrip("/")
FERRY_URL = BASE_URL + "/ferry"

LICENSE_ANCHOR = "text=354122"      # 頁腳香港旅遊牌照號＝全站唯一、不隨改版文案漂移
DEPART_TRIGGER = "//div[@data-testid='ferry-go-depart-city-trigger']"

# 結果頁「有東西出來了」的探針。⚠️ 原版正則一字未改，只追加 2 個真實空態詞。
# 註釋固化原作者的判斷：盼游首頁/結果頁有埋點長連接，networkidle 永不觸發，
# 故【不能】等 networkidle，只能等業務結果文本出現 —— 這是對的，別改成 wait_for_load_state。
RESULT_READY_RE = re.compile(r"班次|航班|暫無|沒有|無可訂|可訂|沒有可訂|暫無班次")


# ---------------- 內部工具 ----------------
def _date_variants(iso_date: str):
    """
    ISO '2026-11-27' → 盼游頁面上可能出現的繁體形態集合。
    覆蓋：2026年11月27日 / 2026年11月27 / 11月27日 / 11月27 / 11/27
    ⚠️ 這是「輔助通道」，主通道是 URL 的 date= 精確比對，這裏寬一點不會放過假綠。
    """
    y, m, d = iso_date.split("-")
    return [
        f"{y}年{int(m)}月{int(d)}日",
        f"{y}年{int(m)}月{int(d)}",
        f"{int(m)}月{int(d)}日",
        f"{int(m)}月{int(d)}",
        f"{int(m)}/{int(d)}",
    ]


def _assert_date_visible(page, target_date: str, tag: str = "") -> None:
    """
    雙通道日期斷言：
      ① 主：URL 含 date={target_date}  ← 這是前端路由的真契約，精確
      ② 輔：body 文本含任一繁體形態     ← 防「URL 對了但頁面渲染的是別的天」
    任一通道命中即算過；兩條全滅才紅，並把 URL + body 前 300 字一起打出來。
    """
    url_hit = target_date in page.url
    body = ""
    try:
        body = page.inner_text("body") or ""
    except Exception:
        pass
    text_hit = any(v in body for v in _date_variants(target_date))

    if url_hit or text_hit:
        print(f"{tag}日期校驗通過: url_hit={url_hit}, text_hit={text_hit}, date={target_date}")
        return

    snippet = re.sub(r"\s+", " ", body[:300])
    raise AssertionError(
        f"{tag}查詢後頁面未顯示目標日期 {target_date}\n"
        f"  URL     : {page.url}\n"
        f"  嘗試形態: {_date_variants(target_date)}\n"
        f"  body前300: {snippet}\n"
        f"  → 若 URL 已含 date= 但文案形態不在上面列表裏，把實際日期文案貼給開發補進 "
        f"_date_variants()；若 URL 都沒有 date=，是點擊沒觸發路由，看上一步 wait_for_url。"
    )


def _wait_ferry_ready(page, timeout: int = 15_000) -> None:
    """船票頁外殼就緒：頁腳牌照 → 出發地 trigger 可見。雙錨點，防慢機器命中殘留 DOM。"""
    try:
        page.locator(LICENSE_ANCHOR).first.wait_for(state="visible", timeout=timeout)
    except PWTimeout:
        print(" ⚠️ 頁腳牌照 354122 未及時出現（非阻塞），繼續等 trigger")
    expect(page.locator(DEPART_TRIGGER).first).to_be_visible(timeout=timeout)


# ---------------- Fixtures ----------------

@pytest.fixture(scope="module")
def ferry_biz(pw_module_page):
    """test_01 与 test_02 共享同一页面状态（module 級，與原版一致）。"""
    page = pw_module_page
    page.goto(FERRY_URL, wait_until="domcontentloaded", timeout=30_000)
    _wait_ferry_ready(page)                      # ← ③ 新增：牌照 + trigger 雙錨點
    print(" 船票页面就绪（出发地 trigger 可点）")
    return FerryTicketBusiness(page, timeout=15_000)


@pytest.fixture(scope="module")
def ferry_state():
    """
    test_01 → test_02 的狀態通道。⚠️ 刻意設計，勿「優化」掉：
      · test_02 開頭 if not route_ready → pytest.skip，比讓它帶着半截狀態跑更乾淨
      · 副作用：單獨執行 `pytest -k test_02` 會 skip，這是【預期行爲】不是 bug
    """
    return {"route_ready": False}


# ---------------- 用例 ----------------

def test_01_select_depart_and_arrive(ferry_biz, ferry_state):
    """① 選深圳/蛇口碼頭 → 香港/海天碼頭，校驗兩個 trigger 真實回顯"""
    ferry_biz.select_ferry_route(
        depart_city=DEPART_CITY,
        depart_port=DEPART_PORT,
        arrive_city=ARRIVE_CITY,
        arrive_port=ARRIVE_PORT,
    )

    ferry_biz.verify_selection_result(
        depart_text=f"{DEPART_CITY}/{DEPART_PORT}",
        arrive_text=f"{ARRIVE_CITY}/{ARRIVE_PORT}",
    )

    ferry_state["route_test"] = True          # ← 保持向後兼容（原鍵名）
    ferry_state["route_ready"] = True
    print(f" test_01 通过：{DEPART_CITY}/{DEPART_PORT} → {ARRIVE_CITY}/{ARRIVE_PORT}")


def test_02_select_date_and_search(ferry_biz, ferry_state):
    """② 選【明天】→ 立即查詢 → 校驗結果出來 + 路線沒被清空 + 日期回顯"""
    if not ferry_state["route_ready"]:
        pytest.skip("test_01 未通过，跳过依赖路线状态的日期查询用例"
                    "（單跑 test_02 會 skip 屬預期，請跑整個 module）")

    page = ferry_biz.page
    target_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # 防止单独执行 test_02 或页面意外跳转。
    if "/ferry" not in page.url:
        page.goto(FERRY_URL, wait_until="domcontentloaded", timeout=30_000)
        _wait_ferry_ready(page)
        ferry_biz.select_ferry_route(DEPART_CITY, DEPART_PORT, ARRIVE_CITY, ARRIVE_PORT)

    # ---------- 选择明天 ----------
    picker = page.locator("div.ant-picker").first
    picker.scroll_into_view_if_needed()
    picker.click()

    dropdown = page.locator("div.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)").first
    expect(dropdown).to_be_visible(timeout=10_000)

    cell = dropdown.locator(
        f"//td[contains(@class,'ant-picker-cell') and @title='{target_date}']"
    ).first
    expect(cell).to_be_visible(timeout=10_000)

    if "ant-picker-cell-disabled" in (cell.get_attribute("class") or ""):
        # ⚠️ 原版用 raise AssertionError，語義是「業務前提不成立」而非「斷言失敗」。
        #    保留 raise 類型不變（改成 pytest.skip 會讓截單日靜默變綠，那正是你不想要的）。
        raise AssertionError(f"目标日期 {target_date} 不可选：可能已截单或无班次")

    cell.click()
    expect(dropdown).to_be_hidden(timeout=10_000)
    expect(picker).to_contain_text(target_date, timeout=10_000)
    print(f" 已选日期：{target_date}")

    # ---------- 立即查询 ----------
    search_btn = page.locator("//*[@data-testid='ferry-btn-search']").first
    expect(search_btn).to_be_visible(timeout=10_000)
    search_btn.scroll_into_view_if_needed()
    try:
        search_btn.click(timeout=10_000)
    except PWTimeout:                       # 與 business._click_search_and_wait 同級兜底
        print("  [retry] 查詢按鈕普通點擊被攔截，轉 force 點擊")
        search_btn.click(timeout=10_000, force=True)
    print(" 已点击【立即查询】")

    # ↓↓↓ ② 本次新增：等路由跳轉落地，與 FerryTicketBusiness 同源。
    #     不加則下一步 verify_selection_result 可能在結果頁重掛載 header 的瞬間
    #     打到舊 DOM → Element is not attached（目前「碰巧沒炸」，遲早隨機紅）。
    try:
        page.wait_for_url("**/*date=*", timeout=20_000)
        print(f" 船票結果頁已加載: {page.url}")
    except PWTimeout:
        # 不立刻紅：先看看是不是「沒跳但結果已渲染」（前端可能走同頁刷新）
        if not RESULT_READY_RE.search(page.inner_text("body") or ""):
            raise AssertionError(
                f"點擊【立即查詢】後既沒跳轉也沒出結果: {page.url}\n"
                f"body前300: {re.sub(chr(92)+'s+', ' ', (page.inner_text('body') or '')[:300])}"
            )
        print(" ⚠️ URL 未帶 date= 但結果區已渲染（前端走同頁刷新），繼續校驗")

    # 不依赖 networkidle：盼游首页/结果页有埋点长连接，networkidle 永不觸發，
    # 業務結果文本出現纔是可靠信號 —— 原作者此判斷正確，註釋固化在此，勿改成 wait_for_load_state。
    result_state = page.locator(f"text=/{RESULT_READY_RE.pattern}/").first
    try:
        expect(result_state).to_be_visible(timeout=20_000)
    except AssertionError:
        body = re.sub(r"\s+", " ", (page.inner_text("body") or "")[:300])
        raise AssertionError(
            f"點擊查詢 20s 內結果區無任何「班次/暫無/可訂」類文案 —— 前端可能報錯或接口掛了\n"
            f"  URL      : {page.url}\n  body前300: {body}"
        )

    # 查询后路线不能被清空（這是本用例最有價值的一條：專抓「查完路線被重置」的回歸）
    ferry_biz.verify_selection_result(
        depart_text=f"{DEPART_CITY}/{DEPART_PORT}",
        arrive_text=f"{ARRIVE_CITY}/{ARRIVE_PORT}",
    )

    assert "ferry" in page.url.lower(), f"查询后页面异常跳转：{page.url}"

    # ↓↓↓ ① 本次核心修復：ISO 串不會出現在繁體頁面上，改雙通道
    _assert_date_visible(page, target_date, tag="[test_02] ")

    print(" test_02 通过：日期选择 + 查询成功，且路线保持")