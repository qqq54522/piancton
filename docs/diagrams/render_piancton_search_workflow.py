from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "piancton_search_workflow.png"

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


TITLE = font(38)
NODE = font(26)
EDGE = font(22)
NOTE = font(20)


@dataclass(frozen=True)
class Node:
    key: str
    text: str
    kind: str
    center: tuple[int, int]
    size: tuple[int, int]

    @property
    def box(self) -> tuple[int, int, int, int]:
        x, y = self.center
        w, h = self.size
        return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)


def draw_text_center(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int) -> None:
    lines: list[str] = []
    for raw in text.split("\n"):
        lines.extend(wrap(raw, width=width) or [""])
    heights = [draw.textbbox((0, 0), line, font=NODE)[3] for line in lines]
    total_h = sum(heights) + (len(lines) - 1) * 8
    y = xy[1] - total_h // 2
    for line, h in zip(lines, heights):
        draw.text((xy[0], y), line, fill="#111827", font=NODE, anchor="ma")
        y += h + 8


def draw_node(draw: ImageDraw.ImageDraw, node: Node) -> None:
    x1, y1, x2, y2 = node.box
    if node.kind == "decision":
        x, y = node.center
        w, h = node.size
        points = [(x, y - h // 2), (x + w // 2, y), (x, y + h // 2), (x - w // 2, y)]
        draw.polygon(points, fill="#ffffff", outline="#d8dce2")
        draw.line(points + [points[0]], fill="#d8dce2", width=2)
        draw_text_center(draw, node.text, node.center, 12)
        return
    draw.rounded_rectangle(node.box, radius=18, fill="#ffffff", outline="#d8dce2", width=2)
    draw_text_center(draw, node.text, node.center, 16)


def anchor(node: Node, side: str) -> tuple[int, int]:
    x1, y1, x2, y2 = node.box
    if node.kind == "decision":
        x, y = node.center
        w, h = node.size
        if side == "top":
            return (x, y - h // 2)
        if side == "bottom":
            return (x, y + h // 2)
        if side == "left":
            return (x - w // 2, y)
        if side == "right":
            return (x + w // 2, y)
    if side == "top":
        return ((x1 + x2) // 2, y1)
    if side == "bottom":
        return ((x1 + x2) // 2, y2)
    if side == "left":
        return (x1, (y1 + y2) // 2)
    if side == "right":
        return (x2, (y1 + y2) // 2)
    return node.center


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    label: str = "",
    label_at: tuple[int, int] | None = None,
) -> None:
    color = "#8a8f98"
    for a, b in zip(points, points[1:]):
        draw.line((a, b), fill=color, width=3)
    px, py = points[-2]
    ex, ey = points[-1]
    if abs(ex - px) >= abs(ey - py):
        direction = 1 if ex >= px else -1
        head = [(ex, ey), (ex - 16 * direction, ey - 10), (ex - 16 * direction, ey + 10)]
    else:
        direction = 1 if ey >= py else -1
        head = [(ex, ey), (ex - 10, ey - 16 * direction), (ex + 10, ey - 16 * direction)]
    draw.polygon(head, fill=color)
    if label:
        lx, ly = label_at or points[len(points) // 2]
        draw.text((lx, ly), label, fill="#111827", font=EDGE, anchor="mm")


def main() -> None:
    image = Image.new("RGB", (1350, 2600), "#ffffff")
    draw = ImageDraw.Draw(image)

    draw.text((70, 54), "卖点智库核心业务流程图", fill="#111827", font=TITLE)
    draw.text(
        (70, 104),
        "身份码精确查找、普通卖点搜索、素材上传入库三条链路",
        fill="#6b7280",
        font=NOTE,
    )

    nodes = {
        "A": Node("A", "业务人员输入搜索词", "process", (260, 210), (360, 86)),
        "B": Node("B", "身份码/分享链接?", "decision", (260, 460), (320, 300)),
        "C": Node("C", "确定性查找", "process", (220, 760), (250, 86)),
        "D": Node("D", "返回精确素材", "process", (220, 910), (270, 86)),
        "S": Node("S", "API 库存", "process", (650, 410), (210, 86)),
        "E": Node("E", "API 调度中心选择模型", "process", (650, 760), (390, 86)),
        "F": Node("F", "业务体系识别", "process", (650, 910), (260, 86)),
        "G": Node("G", "核心卖点识别", "process", (650, 1060), (260, 86)),
        "H": Node("H", "读取公共话术和业务知识", "process", (650, 1210), (390, 86)),
        "I": Node("I", "查询人工审核关系", "process", (650, 1360), (310, 86)),
        "J": Node("J", "读取素材专属话术", "process", (650, 1510), (310, 86)),
        "K": Node("K", "排序与解释", "process", (650, 1660), (230, 86)),
        "L": Node("L", "有可信素材?", "decision", (650, 1870), (280, 230)),
        "O": Node("O", "素材上传", "process", (1050, 210), (230, 86)),
        "P": Node("P", "图片分析/话术生成", "process", (1050, 410), (330, 86)),
        "Q": Node("Q", "人工审核卖点关系", "process", (1050, 710), (330, 86)),
        "R": Node("R", "正式进入搜索库", "process", (1050, 860), (290, 86)),
        "M": Node("M", "返回素材结果", "process", (930, 2085), (250, 86)),
        "V": Node("V", "素材库 Agent 解释\n为什么能用/怎么用/怎么讲", "process", (930, 2245), (390, 112)),
        "N": Node("N", "返回无可靠素材", "process", (400, 2110), (270, 86)),
        "T": Node("T", "搜索日志", "process", (650, 2405), (220, 86)),
        "U": Node("U", "评测与调优", "process", (650, 2520), (230, 86)),
    }

    for node in nodes.values():
        draw_node(draw, node)

    draw_arrow(draw, [anchor(nodes["A"], "bottom"), anchor(nodes["B"], "top")])
    draw_arrow(draw, [anchor(nodes["B"], "bottom"), anchor(nodes["C"], "top")], "是", (220, 600))
    draw_arrow(draw, [anchor(nodes["C"], "bottom"), anchor(nodes["D"], "top")])

    draw_arrow(
        draw,
        [anchor(nodes["B"], "right"), (455, 600), (520, 720), anchor(nodes["E"], "left")],
        "否",
        (460, 600),
    )
    draw_arrow(draw, [anchor(nodes["S"], "bottom"), (650, 620), anchor(nodes["E"], "top")])
    chain = ["E", "F", "G", "H", "I", "J", "K", "L"]
    for first, second in zip(chain, chain[1:]):
        draw_arrow(draw, [anchor(nodes[first], "bottom"), anchor(nodes[second], "top")])

    draw_arrow(draw, [anchor(nodes["O"], "bottom"), anchor(nodes["P"], "top")])
    draw_arrow(draw, [anchor(nodes["P"], "bottom"), anchor(nodes["Q"], "top")])
    draw_arrow(draw, [anchor(nodes["Q"], "bottom"), anchor(nodes["R"], "top")])
    draw_arrow(draw, [anchor(nodes["L"], "right"), (790, 1990), anchor(nodes["M"], "top")], "有", (795, 1980))
    draw_arrow(draw, [anchor(nodes["L"], "left"), (510, 1990), anchor(nodes["N"], "top")], "无", (505, 1980))
    draw_arrow(draw, [anchor(nodes["M"], "bottom"), anchor(nodes["V"], "top")])
    draw_arrow(draw, [anchor(nodes["V"], "bottom"), (930, 2365), anchor(nodes["T"], "right")])
    draw_arrow(draw, [anchor(nodes["N"], "bottom"), (400, 2365), anchor(nodes["T"], "left")])
    draw_arrow(draw, [anchor(nodes["T"], "bottom"), anchor(nodes["U"], "top")])

    draw.text(
        (70, 2570),
        "规则：身份码/分享链接先精确查找；普通搜索走 API 中心卖点理解；Agent 只解释素材，不写入业务事实。",
        fill="#4b5563",
        font=NOTE,
    )

    image.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
