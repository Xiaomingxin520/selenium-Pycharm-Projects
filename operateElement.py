# -*- coding: utf-8 -*-
"""
operateelement.py —— 基礎操作封裝層（Playwright 版）
"""
from functools import wraps
from typing import Union, Optional

from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

try:
    import allure
    _ALLURE = True
except ImportError:                                    # pragma: no cover
    _ALLURE = False

DEFAULT_TIMEOUT = 10_000

# 定位器歸一：兼容舊 XPath 字符串

def to_locator(page: Page, target: Union[str, Locator]) -> Locator:

    if isinstance(target, Locator):
        return target

    s = (target or "").strip()
    if not s:
        raise ValueError(" to_locator(): 定位器爲空字符串 —— 這通常是常量寫漏了，"
                         "不是「找不到元素」，請先查 page 層常量區。")

    if s.startswith(("xpath=", "css=", "text=", "role=", "id=", "data-testid=")):
        return page.locator(s)

    # 裸 XPath 啓發式識別
    if s.startswith(("/", "(", ".")) or "//" in s or "/@" in s:
        return page.locator(f"xpath={s}")

    return page.locator(s)          # 當作 CSS

# Allure 步驟：自動生成可讀步驟名

def _describe(target, fallback: str) -> str:
    """從入參反解出人話描述，讓 Allure 報告裏每一步都能一眼看懂。"""
    if isinstance(target, Locator):
        try:
            return f"{fallback}: {target}"
        except Exception:
            return fallback
    s = str(target or "").strip()
    # 優先取 testid，最可讀
    if "data-testid=" in s:
        import re as _re
        m = _re.search(r"data-testid=['\"]?([^'\"\]\s)]+)", s)
        if m:
            return f"{fallback} [testid={m.group(1)}]"
    if "text=" in s:
        import re as _re
        m = _re.search(r"text=?['\"]?([^'\"\]]{1,24})", s)
        if m:
            return f"{fallback} 「{m.group(1)}」"
    tail = s if len(s) <= 60 else s[:57] + "..."
    return f"{fallback}: {tail}"


def allure_step(title: Optional[str] = None):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _ALLURE:
                return func(*args, **kwargs)

            desc_override = kwargs.pop("desc", None)
            if desc_override:
                step_name = desc_override
            else:
                head = args[1] if len(args) > 1 else (kwargs.get("locator") or "")
                step_name = _describe(head, title or func.__name__)
                if title and title != func.__name__:
                    step_name = f"{title} · {step_name}"

            with allure.step(step_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# 命中測試診斷：誰擋住了我的點擊？

_HIT_PROBE_JS = """(el) => {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const hit = document.elementFromPoint(cx, cy);
    const cs = el.ownerDocument.defaultView.getComputedStyle(el);
    const chain = [];
    let n = hit;
    while (n && chain.length < 5) {
        chain.push(n.tagName + (n.className ? '.' + String(n.className).trim().split(/\\s+/).slice(0,2).join('.') : '')
                 + (n.dataset && n.dataset.testid ? '[testid=' + n.dataset.testid + ']' : ''));
        n = n.parentElement;
    }
    return {
        point: [Math.round(cx), Math.round(cy)],
        box: {w: Math.round(r.width), h: Math.round(r.height)},
        selfStyle: {display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
                    pointerEvents: cs.pointerEvents},
        hitIsSelf: !!hit && (hit === el || el.contains(hit)),
        hitChain: chain,
        maskCount: document.querySelectorAll('.ant-modal-mask,.ant-drawer-mask,.ant-popover,.ant-tooltip').length
    };
}"""


class OperateElement:

    def __init__(self, page: Page, timeout: int = DEFAULT_TIMEOUT):
        self.page = page
        self.timeout = timeout
        # 與原版對齊：page 級默認超時統一由這層設定，page 層不必各自 set_default_timeout
        page.set_default_timeout(timeout)

    # ==================== 內部工具 ====================

    def _loc(self, target: Union[str, Locator]) -> Locator:
        return to_locator(self.page, target)

    def _probe(self, loc: Locator) -> dict:
        """命中測試診斷。任何環節出錯都返回可打印的 dict，絕不拋。"""
        try:
            return loc.evaluate(_HIT_PROBE_JS)
        except Exception as exc:
            return {"(探針失敗)": str(exc)[:160]}

    def _diag(self, loc: Locator, desc: str) -> str:
        """把「是誰擋住了」拼成一段能直接貼進缺陷單的文字。"""
        p = self._probe(loc)
        if "(探針失敗)" in p:
            return f"  命中探針失敗（元素可能已脫離 DOM）: {p['(探針失敗)']}"
        verdict = "命中點是自己 " if p.get("hitIsSelf") else \
                  " 命中點是【別的元素】—— 這就是點擊被攔截的原因"
        return (
            f"  ── 點擊命中診斷 [{desc}] ────────────────────\n"
            f"  目標方框 : {p.get('box')}  中心點={p.get('point')}\n"
            f"  自身樣式 : {p.get('selfStyle')}\n"
            f"  命中判定 : {verdict}\n"
            f"  命中鏈   : {' → '.join(p.get('hitChain', [])) or '(空)'}\n"
            f"  頁面具名層: mask/popover/tooltip 共 {p.get('maskCount')} 個\n"
            f"  → 若命中鏈頂部是 .ant-modal-mask / .ant-drawer-mask：\n"
            f"     有個【已關閉但未銷毀】的彈窗遮罩還在吃點擊（antd 默認行爲），\n"
            f"     這是【前端缺陷】，不是用例問題；臨時繞過用 force=True，\n"
            f"     並在缺陷單裏貼這段診斷。\n"
            f"  ──────────────────────────────────────────────"
        )

    # ==================== 對外操作方法 ====================

    @allure_step()
    def click(self, target: Union[str, Locator], *,
              force: bool = False,
              timeout: Optional[int] = None,
              scroll: bool = True,
              desc: str = "") -> None:

        loc = self._loc(target)
        to = timeout or self.timeout
        label = desc or _describe(target, "click")

        if scroll:
            try:
                loc.scroll_into_view_if_needed(timeout=to)
            except PWTimeout:
                print(f" ⚠️ scroll_into_view 超時（不阻塞，繼續嘗試點擊）：{label}")

        if force:
            try:
                loc.click(timeout=to, force=True)
                print(f" ✔ click(force): {label}")
                return
            except Exception as exc:
                raise AssertionError(
                    f" 強制點擊仍失敗：{label}\n{self._diag(loc, label)}\n"
                    f"  原始異常: {type(exc).__name__}: {str(exc)[:200]}\n"
                    f"  → force 都點不動 = 元素不在視口 / 已脫離 DOM / 被 opacity:0 "
                    f"但 pointer-events 仍生效的層覆蓋。【別再加第三級降級】，"
                    f"這是需要報給前端的缺陷。"
                ) from None

        try:
            loc.click(timeout=to)
            print(f" ✔ click: {label}")
        except PWTimeout:
            # ↓↓↓ 原版這裏直接重試同一條路徑。現改爲「先診斷，再降級」↓↓↓
            print(self._diag(loc, label))
            print(f"  [retry] 普通點擊被攔截，轉 force 點擊：{label}")
            try:
                loc.click(timeout=to, force=True)
                print(f" ✔ click(force 降級成功，⚠️ 建議提缺陷單): {label}")
            except Exception as exc:
                raise AssertionError(
                    f" 點擊失敗（真點擊 + force 均失敗）：{label}\n"
                    f"  原始異常: {type(exc).__name__}: {str(exc)[:200]}\n"
                    f"  → 上面那段命中診斷請整段貼進缺陷單。"
                ) from None

    @allure_step()
    def fill(self, target: Union[str, Locator], text: str, *,
             timeout: Optional[int] = None,
             verify: bool = True,
             desc: str = "") -> None:

        loc = self._loc(target)
        to = timeout or self.timeout
        label = desc or _describe(target, "fill")

        loc.scroll_into_view_if_needed(timeout=to)
        try:
            loc.fill("", timeout=to)          # 先顯式清空（fill 本身也會清，這步是雙保險）
            loc.fill(str(text if text is not None else ""), timeout=to)
        except PWTimeout as exc:
            raise AssertionError(
                f" 無法定位輸入框：{label}\n"
                f"  定位器: {target}\n  原始異常: {str(exc)[:200]}"
            ) from None

        print(f" ✔ fill: {label} = {'***' if 'pwd' in label.lower() or '密碼' in label else text!r}")

        if verify:
            try:
                actual = loc.input_value(timeout=3_000)
            except Exception:
                return                        # 回讀失敗不阻塞（可能不是 <input>）
            if actual != str(text if text is not None else ""):
                # ⚠️ 不吞：這是「你以爲輸進去了、其實被組件改寫了」，
                #    比找不到元素更危險，必須紅。
                raise AssertionError(
                    f" 輸入值被組件改寫：{label}\n"
                    f"  期望: {str(text)!r}\n  實際 value: {actual!r}\n"
                    f"  → 常見原因：AntD Input 的 maxLength / formatter / "
                    f"onChange 裏做了 trim 或區號拼接。\n"
                    f"  → 若這是【預期行爲】（如手機號自動加 +852），把該處"
                    f"verify=False 並寫明理由，別關全局開關。"
                )

    @allure_step()
    def press_sequentially(self, target: Union[str, Locator], text: str, *,
                           delay: int = 60,
                           timeout: Optional[int] = None,
                           desc: str = "") -> None:
        """
        逐鍵輸入。 只在【真的需要 keydown 逐鍵觸發聯動】時用（如下拉搜索框
        靠 onChange 每次按鍵過濾候選）。普通表單請用 fill()，快 10 倍以上。
        """
        loc = self._loc(target)
        loc.scroll_into_view_if_needed(timeout=timeout or self.timeout)
        loc.click(timeout=timeout or self.timeout)
        loc.press_sequentially(str(text), delay=delay, timeout=timeout or self.timeout)
        print(f" ✔ press_sequentially: {desc or _describe(target, 'type')} = {text!r}")

    @allure_step()
    def get_text(self, target: Union[str, Locator], *,
                 timeout: Optional[int] = None,
                 desc: str = "") -> str:

        loc = self._loc(target)
        try:
            loc.wait_for(state="visible", timeout=timeout or self.timeout)
            txt = loc.inner_text(timeout=timeout or self.timeout)
        except PWTimeout as exc:
            raise AssertionError(
                f" 獲取文本失敗（元素 {self.timeout}ms 內不可見）：{desc or _describe(target,'get_text')}\n"
                f"  定位器: {target}\n  原始異常: {str(exc)[:200]}\n"
                f"  → 若這是「隱藏域取值」場景，改用 get_attribute(loc, 'data-xxx')，"
                f"別把這裏改成 state='attached' —— 那會讓後面所有斷言拿到空串還以爲正常。"
            ) from None
        return (txt or "").replace("\u3000", " ").strip()

    @allure_step()
    def get_attribute(self, target: Union[str, Locator], name: str, *,
                      timeout: Optional[int] = None,
                      desc: str = "") -> str:
        """讀屬性（data-city-id / data-station-id / aria-selected / class 首選這條）。"""
        loc = self._loc(target)
        try:
            loc.wait_for(state="attached", timeout=timeout or self.timeout)
            return loc.get_attribute(name, timeout=timeout or self.timeout) or ""
        except PWTimeout as exc:
            raise AssertionError(
                f" 讀屬性失敗 @{name}：{desc or _describe(target,'get_attr')}\n"
                f"  原始異常: {str(exc)[:160]}"
            ) from None

    @allure_step()
    def clear(self, target: Union[str, Locator], *,
              timeout: Optional[int] = None,
              desc: str = "") -> None:
        loc = self._loc(target)
        try:
            loc.fill("", timeout=timeout or self.timeout)
        except PWTimeout:
            raise AssertionError(f" 清除文本失敗：{desc or _describe(target,'clear')}") from None
        print(f" ✔ clear: {desc or _describe(target, 'clear')}")

    # ==================== 斷言族（④ 空值即 fail） ====================

    @allure_step()
    def assert_text(self, target: Union[str, Locator], expected_text: str, *,
                    timeout: Optional[int] = None,
                    desc: str = "") -> None:

        exp = _norm_expected(expected_text)
        if not exp:
            raise ValueError(
                f" assert_text 的 expected_text 爲空（拿到 {expected_text!r}）→ 此斷言會恆真。\n"
                f"  用例：{desc or _describe(target,'assert_text')}\n"
                f"  → 數據驅動請在讀 CSV 那層就 fail（test_login.py 已加），"
                f"這裏是第二道閘，別刪。"
            )
        actual = self.get_text(target, timeout=timeout, desc=desc)
        if exp not in actual:
            raise AssertionError(
                f"文本断言失败！\n"
                f"预期包含：{exp}\n"
                f"实际文本：{actual!r}\n"
                f"定位器  ：{target}\n"
                f"當前URL ：{self.page.url}\n"
                f"→ 若是「繁簡/全半角」差异，用 assert_text_re()；\n"
                f"→ 若是「错误信息張冠李戴」要精確匹配，用 assert_text_exact()。"
            )
        print(f" ✔ assert_text 通過：含「{exp}」（實際 {actual!r}）")

    @allure_step()
    def assert_text_exact(self, target: Union[str, Locator], expected_text: str, *,
                          timeout: Optional[int] = None,
                          desc: str = "") -> None:
        """
        """
        exp = _norm_expected(expected_text)
        if not exp:
            raise ValueError(" assert_text_exact 的 expected_text 爲空 → 此斷言會恆真，拒絕執行。")
        actual = self.get_text(target, timeout=timeout, desc=desc)
        if actual != exp:
            raise AssertionError(
                f"文本精确断言失败！\n预期：{exp!r}\n实际：{actual!r}\n定位器：{target}"
            )
        print(f" ✔ assert_text_exact 通過：{actual!r}")

    @allure_step()
    def assert_text_re(self, target: Union[str, Locator], pattern: str, *,
                       timeout: Optional[int] = None,
                       desc: str = "") -> None:
        """正則匹配。給「金額 HKD\\d+起」「日期 2026年11月27日」這類形態用。"""
        import re
        if not (pattern or "").strip():
            raise ValueError(" assert_text_re 的 pattern 爲空 → 拒絕執行。")
        actual = self.get_text(target, timeout=timeout, desc=desc)
        if not re.search(pattern, actual):
            raise AssertionError(
                f"文本正则断言失败！\n模式：{pattern!r}\n实际：{actual!r}\n定位器：{target}"
            )
        print(f" ✔ assert_text_re 通過：/{pattern}/ ← {actual!r}")

    @allure_step()
    def assert_visible(self, target: Union[str, Locator], *,
                       timeout: Optional[int] = None,
                       desc: str = "") -> None:

        loc = self._loc(target)
        try:
            loc.wait_for(state="visible", timeout=timeout or self.timeout)
        except PWTimeout as exc:
            ids = _page_testids(self.page, prefix=None, limit=12)
            raise AssertionError(
                f" 斷言可見失敗（{self.timeout}ms 內不可見）：{desc or _describe(target,'assert_visible')}\n"
                f"  定位器: {target}\n  當前URL: {self.page.url}\n"
                f"  頁面上 testid（前12個）: {ids}\n"
                f"  → 報錯若是 waiting for locator(...)  = 選擇器沒命中任何節點（testid 寫錯/未加）\n"
                f"  → 報錯若是 element is not visible    = 節點在，但 display:none（沒觸發打開）\n"
                f"     【這兩個報錯含義天差地別，先看第一個詞再動手】\n"
                f"  原始異常: {str(exc)[:160]}"
            ) from None
        print(f" ✔ assert_visible 通過：{desc or _describe(target,'assert_visible')}")

    @allure_step()
    def assert_hidden(self, target: Union[str, Locator], *,
                      timeout: Optional[int] = None,
                      desc: str = "") -> None:
        """斷言消失（彈窗收起 / loading 轉圈結束 首選這條，比 sleep 可靠）。"""
        loc = self._loc(target)
        try:
            loc.wait_for(state="hidden", timeout=timeout or self.timeout)
        except PWTimeout as exc:
            raise AssertionError(
                f" 斷言消失失敗（{self.timeout}ms 後仍可見）：{desc or _describe(target,'assert_hidden')}\n"
                f"  定位器: {target}\n  當前文本: {(loc.inner_text() or '')[:80]!r}\n"
                f"  原始異常: {str(exc)[:160]}"
            ) from None
        print(f" ✔ assert_hidden 通過：{desc or _describe(target,'assert_hidden')}")

    @allure_step()
    def assert_count(self, target: Union[str, Locator], expected: int, *,
                     timeout: Optional[int] = None,
                     desc: str = "") -> None:
        """
        斷言命中數量。結果頁「候選班次 ≥1」、列表「恰好 1 條」用這條。
        ⚠️ Locator 惰性求值 → 自帶重試，不用自己寫輪詢。
        """
        loc = self._loc(target)
        try:
            from playwright.sync_api import expect as _expect
            _expect(loc).to_have_count(expected, timeout=timeout or self.timeout)
        except Exception as exc:
            actual = loc.count()
            raise AssertionError(
                f"數量斷言失敗：{desc or _describe(target,'assert_count')}\n"
                f"預期 {expected} 個，實際 {actual} 個\n定位器：{target}\n"
                f"原始異常: {str(exc)[:160]}"
            ) from None
        print(f" ✔ assert_count 通過：{expected} 個 ← {desc or ''}")

    # ==================== 等待族（少用；Locator 自帶自動等待） ====================

    def wait_visible(self, target: Union[str, Locator], *,
                     timeout: Optional[int] = None) -> Locator:
        """⚠️ 只在「後續要對同一 locator 做多次操作」時用。
        單次 click/fill 前【不要】調這個 —— Locator 已自帶等待，多寫一層
        只會把 attached/visible 語義搞混（見 bus-go-arrive-city-modal 那次事故）。"""
        loc = self._loc(target)
        loc.wait_for(state="visible", timeout=timeout or self.timeout)
        return loc

    def wait_hidden(self, target: Union[str, Locator], *,
                    timeout: Optional[int] = None) -> None:
        loc = self._loc(target)
        loc.wait_for(state="hidden", timeout=timeout or self.timeout)

    def wait_url_has(self, fragment: str, timeout: int = 20_000) -> str:
        """等 URL 含片段（登錄/查詢跳轉完成標誌）。返回當前 URL。"""
        try:
            self.page.wait_for_url(f"**/*{fragment}*", timeout=timeout)
        except PWTimeout:
            raise AssertionError(
                f" 等待 URL 含「{fragment}」超時({timeout}ms)：當前 {self.page.url}\n"
                f"  → 常見：表單校驗沒過導致沒跳轉；看頁面有無 AntD 錯誤 Toast"
            ) from None
        return self.page.url

    send_keys = fill
# 模塊級小工具
def _norm_expected(v) -> str:
    """期望文本歸一：None/'<null>'/'NULL'/'None'/'nan' → ''；全角空格 → 半角。"""
    if v is None:
        return ""
    s = str(v).replace("\u3000", " ").strip()
    if s.lower() in ("<null>", "null", "none", "nan"):
        return ""
    return s


def _page_testids(page: Page, prefix: Optional[str] = None, limit: int = 12) -> list:
    """出錯時把頁面上現存的 testid 打出來，免得對着空日誌猜。"""
    try:
        flt = f".filter(t=>t.startsWith('{prefix}'))" if prefix else ""
        return page.evaluate(
            f"() => [...document.querySelectorAll('[data-testid]')]"
            f".map(e=>e.dataset.testid){flt}.slice(0,{limit})"
        )
    except Exception:
        return []