from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "piancton_all_interface_flow.png"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def font(size: int, index: int = 0) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size, index=index)
            except OSError:
                return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


TITLE = font(58)
SUBTITLE = font(28)
LANE_TITLE = font(30)
SCREEN_TITLE = font(25)
ROUTE = font(19)
BODY = font(21)
SMALL = font(18)
TINY = font(16)


@dataclass(frozen=True)
class Screen:
    key: str
    title: str
    route: str
    sections: tuple[str, ...]
    xy: tuple[int, int, int, int]
    accent: str
    fill: str = "#ffffff"


def rounded(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], radius: int, fill: str, outline: str, width: int = 2) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, fnt: ImageFont.ImageFont) -> None:
    draw.text(xy, value, fill=fill, font=fnt)


def lane(draw: ImageDraw.ImageDraw, title: str, xy: tuple[int, int, int, int], fill: str, accent: str) -> None:
    rounded(draw, xy, 30, fill, "#cbd5e1", 2)
    x1, y1, _, _ = xy
    text(draw, (x1 + 30, y1 + 22), title, "#0f172a", LANE_TITLE)
    draw.line((x1 + 30, y1 + 62, x1 + 250, y1 + 62), fill=accent, width=5)


def wrap_text(value: str, chars: int) -> list[str]:
    lines: list[str] = []
    for raw in value.split("\n"):
        if not raw:
            lines.append("")
            continue
        lines.extend(wrap(raw, width=chars, break_long_words=False, replace_whitespace=False))
    return lines


def draw_section(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], label: str, accent: str) -> None:
    x1, y1, x2, y2 = xy
    rounded(draw, xy, 12, "#f8fafc", "#e2e8f0", 1)
    draw.ellipse((x1 + 12, y1 + 13, x1 + 24, y1 + 25), fill=accent)
    available = max(8, int((x2 - x1 - 48) / 21))
    lines = wrap_text(label, available)[:3]
    yy = y1 + 9
    for line in lines:
        text(draw, (x1 + 34, yy), line, "#334155", SMALL)
        yy += 24


def draw_screen(draw: ImageDraw.ImageDraw, screen: Screen) -> None:
    x1, y1, x2, y2 = screen.xy
    rounded(draw, screen.xy, 18, screen.fill, screen.accent, 3)
    draw.rounded_rectangle((x1, y1, x2, y1 + 50), radius=18, fill="#f8fafc", outline=screen.accent, width=0)
    draw.rectangle((x1, y1 + 30, x2, y1 + 52), fill="#f8fafc")
    draw.line((x1, y1 + 52, x2, y1 + 52), fill="#dbeafe", width=1)
    text(draw, (x1 + 18, y1 + 13), screen.title, "#0f172a", SCREEN_TITLE)
    if screen.route:
        text(draw, (x2 - 18 - len(screen.route) * 10, y1 + 18), screen.route, "#64748b", ROUTE)

    section_top = y1 + 72
    section_gap = 14
    section_height = max(56, min(74, int((y2 - section_top - 24 - section_gap * (len(screen.sections) - 1)) / max(1, len(screen.sections)))))
    yy = section_top
    for item in screen.sections:
        if yy + section_height > y2 - 18:
            break
        draw_section(draw, (x1 + 18, yy, x2 - 18, yy + section_height), item, screen.accent)
        yy += section_height + section_gap


def center(screen: Screen) -> tuple[int, int]:
    x1, y1, x2, y2 = screen.xy
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def side(screen: Screen, name: str) -> tuple[int, int]:
    x1, y1, x2, y2 = screen.xy
    if name == "left":
        return (x1, (y1 + y2) // 2)
    if name == "right":
        return (x2, (y1 + y2) // 2)
    if name == "top":
        return ((x1 + x2) // 2, y1)
    if name == "bottom":
        return ((x1 + x2) // 2, y2)
    return center(screen)


def arrow_head(draw: ImageDraw.ImageDraw, previous: tuple[int, int], end: tuple[int, int], color: str) -> None:
    px, py = previous
    ex, ey = end
    if abs(ex - px) >= abs(ey - py):
        direction = 1 if ex >= px else -1
        points = [(ex, ey), (ex - 18 * direction, ey - 11), (ex - 18 * direction, ey + 11)]
    else:
        direction = 1 if ey >= py else -1
        points = [(ex, ey), (ex - 11, ey - 18 * direction), (ex + 11, ey - 18 * direction)]
    draw.polygon(points, fill=color)


def label(draw: ImageDraw.ImageDraw, point: tuple[int, int], value: str, color: str) -> None:
    if not value:
        return
    bbox = draw.textbbox(point, value, font=TINY, anchor="mm")
    padded = (bbox[0] - 9, bbox[1] - 5, bbox[2] + 9, bbox[3] + 5)
    rounded(draw, padded, 8, "#ffffff", "#bfdbfe", 1)
    draw.text(point, value, fill=color, font=TINY, anchor="mm")


def connect(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    value: str = "",
    color: str = "#2563eb",
    width: int = 4,
) -> None:
    for first, second in zip(points, points[1:]):
        draw.line((first, second), fill=color, width=width)
    arrow_head(draw, points[-2], points[-1], color)
    if value:
        label(draw, points[len(points) // 2], value, color)


def draw_legend(draw: ImageDraw.ImageDraw) -> None:
    rounded(draw, (3420, 86, 5070, 230), 20, "#ffffff", "#cbd5e1", 2)
    text(draw, (3450, 112), "读图说明", "#0f172a", SCREEN_TITLE)
    items = [
        ("#2563eb", "页面跳转 / 用户操作"),
        ("#f97316", "素材维护动作"),
        ("#6366f1", "后台治理输入"),
        ("#64748b", "日志、统计、审计沉淀"),
    ]
    x = 3452
    y = 158
    for color, value in items:
        draw.line((x, y + 10, x + 38, y + 10), fill=color, width=5)
        arrow_head(draw, (x + 20, y + 10), (x + 38, y + 10), color)
        text(draw, (x + 52, y), value, "#334155", SMALL)
        x += 390


def main() -> None:
    image = Image.new("RGB", (5200, 3480), "#ffffff")
    draw = ImageDraw.Draw(image)

    text(draw, (90, 70), "卖点智库低保真界面原型与全页面流程", "#0f172a", TITLE)
    text(draw, (94, 142), "按当前 React 路由和页面模块绘制：每个框代表一个真实页面、弹窗、面板或页面内部子界面。", "#475569", SUBTITLE)
    draw_legend(draw)

    lane(draw, "一、入口与应用外壳", (70, 270, 5130, 610), "#f8fafc", "#64748b")
    lane(draw, "二、业务用户主流程：搜索、结果、详情、下载、Agent 解释", (70, 670, 5130, 1420), "#ecfdf5", "#16a34a")
    lane(draw, "三、设计师 / 管理员素材维护流：上传、分析、审核、版本、回收站", (70, 1480, 5130, 2250), "#fff7ed", "#f97316")
    lane(draw, "四、管理员后台治理：卖点、渠道、API、搜索运营、身份码、统计、权限、审计", (70, 2310, 5130, 3240), "#eef2ff", "#6366f1")

    screens = {
        "login": Screen("login", "登录页", "/login", ("用户名 / 密码输入", "登录按钮", "失败提示与重试"), (130, 360, 560, 560), "#64748b"),
        "auth": Screen("auth", "鉴权守卫", "ProtectedRoute", ("未登录：跳转登录", "已登录：进入 Layout", "读取当前用户角色"), (720, 360, 1160, 560), "#64748b"),
        "layout": Screen("layout", "应用外壳", "Layout", ("左侧导航 / 移动端菜单", "账号菜单 / 退出登录", "页面内容区 Outlet"), (1320, 350, 1780, 570), "#0284c7", "#f0f9ff"),
        "role": Screen("role", "角色导航分发", "role", ("business：只看业务素材", "designer：上传/维护/回收", "admin：后台全部入口"), (1940, 350, 2400, 570), "#0284c7", "#f0f9ff"),
        "notfound": Screen("notfound", "兜底页", "*", ("无匹配路由", "NotFound 页面", "返回可用入口"), (2560, 370, 2940, 545), "#94a3b8"),

        "home": Screen("home", "素材库首页", "/", ("顶部全局搜索框", "渠道 / 场景 / GIF 预览", "排序与素材瀑布流", "空库时引导上传"), (130, 790, 690, 1320), "#16a34a"),
        "filter": Screen("filter", "手动筛选抽屉", "ManualFilterRail", ("卖点下拉", "证明点下拉", "应用 / 重置", "只做结果后收窄"), (760, 790, 1190, 1115), "#16a34a"),
        "loading": Screen("loading", "搜索加载 / 错误态", "SearchState", ("20-60 秒进度提示", "外部增强超时提示", "重新尝试 / 清除搜索"), (760, 1145, 1190, 1345), "#16a34a"),
        "result": Screen("result", "搜索结果区", "SemanticSearchResult", ("匹配摘要 / 卖点理解", "渠道推荐说明", "项目篮 ProjectBasket", "结果卡片 + 反馈面板"), (1300, 780, 1900, 1330), "#16a34a"),
        "detail_biz": Screen("detail_biz", "素材详情业务视图", "/image/:id", ("大图预览", "素材信息 / 身份码", "相关素材推荐", "业务侧推荐栏"), (2040, 780, 2640, 1330), "#16a34a"),
        "download": Screen("download", "预览 / 下载", "DownloadMenu", ("预览不计数", "下载写入统计", "主图 / 版本下载"), (2780, 820, 3220, 1170), "#16a34a"),
        "agent": Screen("agent", "素材库 Agent", "AssetAgentWidget", ("个人会话列表", "加入图片上下文", "解释卖点 / 场景 / 话术", "每日 00:00 重置"), (3360, 775, 3970, 1335), "#10b981", "#f0fdf4"),
        "share": Screen("share", "分享链接入口", "/share/:code", ("解析素材码 / 版本码", "确定性重定向", "不进入语义搜索"), (4130, 840, 4630, 1160), "#16a34a"),

        "upload": Screen("upload", "上传主图弹窗", "UploadDialog", ("选择图片 / 批量提示", "素材名称与重名检查", "渠道必填", "卖点/证明点/证据点可选", "提交后自动分配身份码"), (130, 1600, 760, 2150), "#f97316"),
        "phrase": Screen("phrase", "上传前话术生成", "PhraseGenerator", ("选择生成数量", "读取图片 + 标题 + 卖点", "生成候选素材话术", "人工修改后提交"), (860, 1600, 1360, 2010), "#f97316"),
        "detail_designer": Screen("detail_designer", "素材详情设计师视图", "/image/:id", ("大图预览", "信息面板", "重新分析", "删除入口"), (1480, 1600, 2030, 2140), "#f97316"),
        "ai": Screen("ai", "AI 分析面板", "ImageAiAnalysisPanel", ("画面事实", "场景判断", "卖点建议", "分析失败状态"), (2145, 1600, 2645, 2010), "#f97316"),
        "workspace": Screen("workspace", "素材工作台", "AssetWorkspacePanel", ("版本管理", "来源链接", "业务分类", "卖点关系审核", "素材话术审核"), (2755, 1585, 3405, 2165), "#f97316"),
        "version": Screen("version", "版本 / 删除弹窗", "VersionDialog", ("新增主图/派生图", "设为主图", "删除变体确认"), (3540, 1605, 4015, 2010), "#f97316"),
        "trash": Screen("trash", "回收站", "/trash", ("已删除图片列表", "恢复", "永久删除"), (4140, 1605, 4640, 2010), "#f97316"),

        "concepts": Screen("concepts", "卖点管理", "/admin/concepts", ("六大体系", "16 个卖点", "公共话术编辑", "AI 建议需确认"), (130, 2450, 690, 2940), "#6366f1"),
        "channels": Screen("channels", "渠道管理", "/admin/channels", ("渠道标签列表", "渠道家族 / 尺寸语境", "渠道话术", "搜索结果推荐说明"), (790, 2450, 1350, 2940), "#6366f1"),
        "api": Screen("api", "API 中心", "/admin/api-center", ("健康度监测", "API 管理 / Key 指纹", "调度配置 / 任务槽位", "调用链路日志", "中转站与维护状态"), (1450, 2415, 2070, 2990), "#6366f1"),
        "ops": Screen("ops", "搜索运营", "/admin/search-ops", ("总览 / 项目治理", "待处理问题 / AI 待审核", "概念健康 / 素材资产", "源文件健康 / 模型速度", "素材缺口 / 反馈归档"), (2170, 2415, 2800, 2990), "#6366f1"),
        "codes": Screen("codes", "身份码管理", "/admin/identity-codes", ("素材码 / 版本码", "状态筛选", "复制身份码", "删除后不释放旧码"), (2900, 2450, 3460, 2940), "#6366f1"),
        "usage": Screen("usage", "使用统计", "/admin/usage", ("今日 / 7 / 30 / 90 天", "登录 / 访问 / 下载", "用户使用量", "最近事件"), (3560, 2450, 4120, 2940), "#6366f1"),
        "users": Screen("users", "用户管理", "/admin/users", ("创建账号", "角色切换", "启用 / 停用", "重置密码"), (4220, 2450, 4780, 2940), "#6366f1"),
        "audit": Screen("audit", "审计日志", "/admin/audit", ("后台操作记录", "API 变更摘要", "非敏感审计", "排查留痕"), (1450, 3050, 2070, 3195), "#6366f1"),
    }

    for screen in screens.values():
        draw_screen(draw, screen)

    blue = "#2563eb"
    orange = "#f97316"
    purple = "#6366f1"
    gray = "#64748b"

    connect(draw, [side(screens["login"], "right"), side(screens["auth"], "left")], "登录成功", blue)
    connect(draw, [side(screens["auth"], "right"), side(screens["layout"], "left")], "进入应用", blue)
    connect(draw, [side(screens["layout"], "right"), side(screens["role"], "left")], "读取角色", blue)
    connect(draw, [side(screens["layout"], "right"), (2480, 460), side(screens["notfound"], "left")], "异常路由", gray, 3)

    connect(draw, [side(screens["role"], "bottom"), (2170, 645), (410, 645), side(screens["home"], "top")], "业务默认入口", blue)
    connect(draw, [side(screens["home"], "right"), side(screens["filter"], "left")], "打开筛选", blue)
    connect(draw, [side(screens["home"], "right"), (725, 1215), side(screens["loading"], "left")], "输入搜索词", blue)
    connect(draw, [side(screens["loading"], "right"), side(screens["result"], "left")], "返回结果", blue)
    connect(draw, [side(screens["filter"], "right"), (1240, 950), side(screens["result"], "left")], "应用条件", blue)
    connect(draw, [side(screens["result"], "right"), side(screens["detail_biz"], "left")], "点素材卡片", blue)
    connect(draw, [side(screens["detail_biz"], "right"), side(screens["download"], "left")], "预览/下载", blue)
    connect(draw, [side(screens["detail_biz"], "right"), (3290, 1060), side(screens["agent"], "left")], "加入上下文", blue)
    connect(draw, [side(screens["share"], "left"), side(screens["detail_biz"], "right")], "精确定位", blue)

    connect(draw, [side(screens["role"], "bottom"), (2170, 1450), (430, 1450), side(screens["upload"], "top")], "上传主图", orange)
    connect(draw, [side(screens["upload"], "right"), side(screens["phrase"], "left")], "生成话术", orange)
    connect(draw, [side(screens["phrase"], "left"), (810, 1845), side(screens["upload"], "right")], "回填表单", orange)
    connect(draw, [side(screens["upload"], "right"), (1430, 1990), side(screens["detail_designer"], "left")], "上传成功", orange)
    connect(draw, [side(screens["detail_designer"], "right"), side(screens["ai"], "left")], "重新分析", orange)
    connect(draw, [side(screens["detail_designer"], "right"), (2700, 1870), side(screens["workspace"], "left")], "维护素材", orange)
    connect(draw, [side(screens["workspace"], "right"), side(screens["version"], "left")], "版本操作", orange)
    connect(draw, [side(screens["version"], "right"), side(screens["trash"], "left")], "删除", orange)
    connect(draw, [side(screens["trash"], "left"), (4070, 2130), (1700, 2130), side(screens["detail_designer"], "bottom")], "恢复", orange)

    connect(draw, [side(screens["role"], "bottom"), (2170, 2285), (1760, 2285), side(screens["api"], "top")], "管理员后台", purple)
    connect(draw, [side(screens["concepts"], "right"), side(screens["channels"], "left")], "后台导航", purple, 3)
    connect(draw, [side(screens["channels"], "right"), side(screens["api"], "left")], "后台导航", purple, 3)
    connect(draw, [side(screens["api"], "right"), side(screens["ops"], "left")], "后台导航", purple, 3)
    connect(draw, [side(screens["ops"], "right"), side(screens["codes"], "left")], "后台导航", purple, 3)
    connect(draw, [side(screens["codes"], "right"), side(screens["usage"], "left")], "后台导航", purple, 3)
    connect(draw, [side(screens["usage"], "right"), side(screens["users"], "left")], "后台导航", purple, 3)

    connect(draw, [side(screens["api"], "bottom"), side(screens["audit"], "top")], "写审计", gray, 3)
    connect(draw, [side(screens["ops"], "bottom"), (2485, 3030), (2055, 3120), side(screens["audit"], "right")], "反馈归档", gray, 3)

    connect(draw, [side(screens["concepts"], "top"), (410, 2380), (410, 1428), side(screens["home"], "bottom")], "公共话术/卖点", purple, 3)
    connect(draw, [side(screens["channels"], "top"), (1070, 2380), (965, 1428), side(screens["filter"], "bottom")], "渠道话术", purple, 3)
    connect(draw, [side(screens["api"], "top"), (1760, 2310), (3600, 2310), (3600, 1428), side(screens["agent"], "bottom")], "asset_agent_chat", purple, 3)
    connect(draw, [side(screens["api"], "top"), (1760, 2265), (2385, 2265), side(screens["ai"], "bottom")], "图片分析/话术生成", purple, 3)
    connect(draw, [side(screens["api"], "top"), (1760, 2290), (965, 2290), side(screens["loading"], "bottom")], "搜索理解", purple, 3)
    connect(draw, [side(screens["codes"], "top"), (3180, 2365), (4380, 2365), side(screens["share"], "bottom")], "身份码台账", purple, 3)
    connect(draw, [side(screens["usage"], "top"), (3840, 2370), (1620, 2370), (1620, 1350), side(screens["result"], "bottom")], "下载/访问统计", gray, 3)
    connect(draw, [side(screens["users"], "top"), (4500, 2350), (4500, 330), (2170, 330), side(screens["role"], "top")], "角色权限", purple, 3)
    connect(draw, [side(screens["ops"], "top"), (2485, 2350), (1600, 2350), (1600, 1350), side(screens["result"], "bottom")], "搜索日志/反馈", gray, 3)

    rounded(draw, (90, 3270, 5110, 3420), 20, "#f8fafc", "#cbd5e1", 2)
    text(draw, (125, 3298), "核心运行规则", "#0f172a", SCREEN_TITLE)
    notes = [
        "身份码 / 分享链接：先走确定性查找，直接进入素材详情，不让模型猜。",
        "普通搜索：统一走 API 中心做体系、卖点、证明点理解，再受 accepted 人工关系约束。",
        "素材库 Agent：只解释图片、卖点、场景和话术，不写入业务事实；每个用户会话隔离。",
        "API Key：只在后台 API 中心维护，文档和仓库只放示例格式，不暴露真实密钥。",
    ]
    x = 125
    y = 3340
    for note in notes:
        draw.ellipse((x, y + 5, x + 12, y + 17), fill="#2563eb")
        text(draw, (x + 22, y), note, "#334155", SMALL)
        y += 28

    image.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
