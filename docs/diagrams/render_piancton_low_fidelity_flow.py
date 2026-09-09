from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "piancton_low_fidelity_flow.png"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


TITLE = font(46)
SUBTITLE = font(24)
LANE_TITLE = font(26)
BOX_TITLE = font(24)
BODY = font(20)
SMALL = font(18)


@dataclass(frozen=True)
class Box:
    key: str
    title: str
    lines: tuple[str, ...]
    xy: tuple[int, int, int, int]
    fill: str
    border: str


def draw_round_box(draw: ImageDraw.ImageDraw, box: Box) -> None:
    x1, y1, x2, y2 = box.xy
    draw.rounded_rectangle(box.xy, radius=18, fill=box.fill, outline=box.border, width=3)
    draw.text((x1 + 22, y1 + 18), box.title, fill="#0f172a", font=BOX_TITLE)
    draw.line((x1 + 20, y1 + 58, x2 - 20, y1 + 58), fill=box.border, width=1)
    y = y1 + 76
    for line in box.lines:
        for part in wrap(line, width=18):
            draw.text((x1 + 22, y), part, fill="#334155", font=BODY)
            y += 29


def center(box: Box) -> tuple[int, int]:
    x1, y1, x2, y2 = box.xy
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def point(box: Box, side: str) -> tuple[int, int]:
    x1, y1, x2, y2 = box.xy
    if side == "left":
        return (x1, (y1 + y2) // 2)
    if side == "right":
        return (x2, (y1 + y2) // 2)
    if side == "top":
        return ((x1 + x2) // 2, y1)
    if side == "bottom":
        return ((x1 + x2) // 2, y2)
    return center(box)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    label: str = "",
    color: str = "#2563eb",
) -> None:
    draw.line((start, end), fill=color, width=4)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex >= sx else -1
        head = [(ex, ey), (ex - 16 * direction, ey - 10), (ex - 16 * direction, ey + 10)]
    else:
        direction = 1 if ey >= sy else -1
        head = [(ex, ey), (ex - 10, ey - 16 * direction), (ex + 10, ey - 16 * direction)]
    draw.polygon(head, fill=color)
    if label:
        lx = (sx + ex) // 2
        ly = (sy + ey) // 2 - 28
        bbox = draw.textbbox((lx, ly), label, font=SMALL)
        pad = 8
        draw.rounded_rectangle(
            (bbox[0] - pad, bbox[1] - 4, bbox[2] + pad, bbox[3] + 4),
            radius=8,
            fill="#ffffff",
            outline="#dbeafe",
        )
        draw.text((lx, ly), label, fill=color, font=SMALL, anchor="mm")


def poly_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    label: str = "",
    color: str = "#2563eb",
) -> None:
    for first, second in zip(points, points[1:]):
        draw.line((first, second), fill=color, width=4)
    ex, ey = points[-1]
    px, py = points[-2]
    if abs(ex - px) >= abs(ey - py):
        direction = 1 if ex >= px else -1
        head = [(ex, ey), (ex - 16 * direction, ey - 10), (ex - 16 * direction, ey + 10)]
    else:
        direction = 1 if ey >= py else -1
        head = [(ex, ey), (ex - 10, ey - 16 * direction), (ex + 10, ey - 16 * direction)]
    draw.polygon(head, fill=color)
    if label:
        mid = points[len(points) // 2]
        bbox = draw.textbbox(mid, label, font=SMALL, anchor="mm")
        draw.rounded_rectangle(
            (bbox[0] - 8, bbox[1] - 4, bbox[2] + 8, bbox[3] + 4),
            radius=8,
            fill="#ffffff",
            outline="#dbeafe",
        )
        draw.text(mid, label, fill=color, font=SMALL, anchor="mm")


def lane(draw: ImageDraw.ImageDraw, title: str, xy: tuple[int, int, int, int], fill: str) -> None:
    draw.rounded_rectangle(xy, radius=28, fill=fill, outline="#cbd5e1", width=2)
    draw.text((xy[0] + 26, xy[1] + 18), title, fill="#0f172a", font=LANE_TITLE)


def main() -> None:
    image = Image.new("RGB", (2400, 1700), "#ffffff")
    draw = ImageDraw.Draw(image)

    draw.text((80, 55), "卖点智库低保真界面原型与页面流程", fill="#0f172a", font=TITLE)
    draw.text(
        (82, 116),
        "按真实 React/FastAPI 项目页面模块绘制：登录 -> 素材库 -> 搜索/详情/维护 -> 管理后台",
        fill="#475569",
        font=SUBTITLE,
    )

    lane(draw, "入口与应用外壳", (60, 170, 2340, 380), "#f8fafc")
    lane(draw, "业务用户主流程", (60, 420, 2340, 720), "#ecfdf5")
    lane(draw, "设计师 / 管理员素材维护流", (60, 760, 2340, 1080), "#fff7ed")
    lane(draw, "管理员运营与系统配置", (60, 1120, 2340, 1580), "#eef2ff")

    boxes = {
        "login": Box("login", "登录页 /login", ("用户名/密码", "登录按钮", "失败提示"), (110, 230, 420, 350), "#f1f5f9", "#64748b"),
        "shell": Box("shell", "应用外壳 Layout", ("左侧导航", "账号菜单", "角色权限", "页面内容区"), (560, 220, 940, 360), "#e0f2fe", "#0284c7"),
        "nav": Box("nav", "角色导航分发", ("business", "designer", "admin"), (1060, 230, 1330, 350), "#e0f2fe", "#0284c7"),
        "home": Box("home", "素材库首页 /", ("全局搜索框", "渠道/卖点筛选", "排序", "素材卡片网格"), (110, 500, 450, 675), "#ffffff", "#16a34a"),
        "result": Box("result", "搜索结果区", ("动态匹配卖点", "结果卡片", "身份码复制", "搜索反馈/项目篮"), (590, 490, 955, 685), "#ffffff", "#16a34a"),
        "detail": Box("detail", "素材详情 /image/:id", ("大图预览", "身份码", "下载菜单", "相关素材推荐"), (1095, 490, 1465, 685), "#ffffff", "#16a34a"),
        "download": Box("download", "预览 / 下载", ("预览不计数", "下载计数", "按版本下载"), (1610, 510, 1940, 665), "#ffffff", "#16a34a"),
        "upload": Box("upload", "上传主图弹窗", ("选图片", "选渠道", "选卖点", "填素材话术", "上传并发布"), (110, 845, 455, 1040), "#ffffff", "#f97316"),
        "workspace": Box("workspace", "素材工作台", ("版本管理", "来源链接", "业务分类", "卖点关系审核", "素材话术审核"), (590, 840, 960, 1045), "#ffffff", "#f97316"),
        "ai": Box("ai", "AI 分析面板", ("画面事实", "场景判断", "卖点建议", "话术建议", "错误状态"), (1110, 840, 1465, 1045), "#ffffff", "#f97316"),
        "trash": Box("trash", "回收站 /trash", ("已删除图片", "恢复", "永久删除"), (1610, 855, 1940, 1030), "#ffffff", "#f97316"),
        "concepts": Box("concepts", "卖点管理", ("六大体系", "16 个卖点", "公共话术", "启用/停用"), (110, 1210, 430, 1390), "#ffffff", "#6366f1"),
        "channels": Box("channels", "渠道管理", ("渠道标签", "渠道话术", "推荐说明"), (475, 1210, 795, 1390), "#ffffff", "#6366f1"),
        "api": Box("api", "API 中心", ("新增 API", "健康检查", "任务路由", "调用链路", "容量/排除"), (840, 1190, 1185, 1410), "#ffffff", "#6366f1"),
        "ops": Box("ops", "搜索运营", ("概览/治理", "问题/审核队列", "概念健康", "性能/素材缺口", "反馈归档"), (1230, 1190, 1580, 1410), "#ffffff", "#6366f1"),
        "codes": Box("codes", "身份码管理", ("一图一码", "仅活动图片", "复制", "查看图片"), (1625, 1210, 1945, 1390), "#ffffff", "#6366f1"),
        "users": Box("users", "用户与权限", ("admin", "designer", "business", "重置密码"), (1990, 1210, 2310, 1390), "#ffffff", "#6366f1"),
        "audit": Box("audit", "审计 / 使用统计", ("审计日志", "登录", "访问", "下载"), (840, 1440, 1185, 1550), "#ffffff", "#6366f1"),
    }

    for box in boxes.values():
        draw_round_box(draw, box)

    arrow(draw, point(boxes["login"], "right"), point(boxes["shell"], "left"), "登录成功")
    arrow(draw, point(boxes["shell"], "right"), point(boxes["nav"], "left"), "读角色")
    poly_arrow(draw, [point(boxes["nav"], "bottom"), (1195, 410), (280, 410), point(boxes["home"], "top")], "默认进入")
    arrow(draw, point(boxes["home"], "right"), point(boxes["result"], "left"), "输入搜索词")
    arrow(draw, point(boxes["result"], "right"), point(boxes["detail"], "left"), "点素材卡片")
    arrow(draw, point(boxes["detail"], "right"), point(boxes["download"], "left"), "预览/下载")
    poly_arrow(draw, [point(boxes["nav"], "bottom"), (1195, 745), (280, 745), point(boxes["upload"], "top")], "上传主图")
    arrow(draw, point(boxes["upload"], "right"), point(boxes["workspace"], "left"), "上传成功")
    arrow(draw, point(boxes["workspace"], "right"), point(boxes["ai"], "left"), "AI 分析")
    poly_arrow(draw, [point(boxes["detail"], "bottom"), (1280, 745), point(boxes["workspace"], "top")], "维护素材")
    arrow(draw, point(boxes["workspace"], "right"), point(boxes["trash"], "left"), "删除版本")
    poly_arrow(draw, [point(boxes["nav"], "bottom"), (1195, 1100), (1012, 1100), point(boxes["api"], "top")], "管理员后台")
    arrow(draw, point(boxes["api"], "left"), point(boxes["channels"], "right"), "后台导航")
    arrow(draw, point(boxes["api"], "right"), point(boxes["ops"], "left"), "后台导航")
    arrow(draw, point(boxes["ops"], "right"), point(boxes["codes"], "left"), "后台导航")
    arrow(draw, point(boxes["codes"], "right"), point(boxes["users"], "left"), "后台导航")
    arrow(draw, point(boxes["audit"], "right"), point(boxes["ops"], "bottom"), "复盘")

    note_xy = (80, 1588)
    draw.rounded_rectangle((note_xy[0], note_xy[1], 2320, 1660), radius=18, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw.text(
        (note_xy[0] + 22, note_xy[1] + 20),
        "核心规则：单张图片身份码先走精确查找；普通搜索走 API 中心的卖点理解，再受 accepted 人工关系约束。API Key 只放后台，不写进文档或仓库。",
        fill="#0f172a",
        font=SUBTITLE,
    )

    image.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
