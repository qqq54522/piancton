from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PillowImage
from PIL import ImageDraw, ImageFont
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept
from app.models.image import Image
from app.services.asset_identity_service import AssetIdentityService
from app.services.search_index_sync import SearchIndexSync

PLACEHOLDER_PREFIX = "测试占位"
PLACEHOLDER_ACTOR = "placeholder-seed"
PLACEHOLDER_SOURCE_REF = "scripts/seed_placeholder_assets.py"
DEFAULT_PLACEHOLDER_COUNT = 320
REFERENCE_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "understand-image-search-intent"
    / "references"
)
SELLING_POINT_MAP_PATH = REFERENCE_DIR / "selling-point-map.json"

CHANNEL_PLAN = [
    ("PPT", 1280, 720, "PPT演示风格"),
    ("品牌手册", 1400, 1000, "品牌规范风格"),
    ("手机端大图", 1280, 960, "移动端场景风格"),
    ("手机端小图", 900, 900, "移动端入口风格"),
    ("官网大图", 1600, 900, "官网首屏风格"),
    ("官网小图", 1000, 760, "官网模块风格"),
    ("PPT、品牌手册", 1400, 900, "复用规范风格"),
    ("PPT、手机端大图", 1280, 900, "宣发复用风格"),
    ("PPT、官网小图", 1200, 760, "模块复用风格"),
    ("品牌手册、官网大图", 1600, 1000, "品牌官网风格"),
    ("手机端大图、官网大图", 1280, 960, "跨端场景风格"),
    ("手机端小图、官网小图", 900, 760, "入口模块风格"),
    ("手机端大图、手机端小图", 1080, 1080, "移动多尺寸风格"),
    ("PPT、品牌手册、官网大图", 1600, 900, "全渠道复用风格"),
]
SCENE_PLAN: tuple[bool | None, ...] = (True, False, None, True, False)
RELATION_PLAN = ("expresses", "expresses", "expresses", "supports")

PALETTES = [
    ("#2563eb", "#eff6ff", "#172554"),
    ("#16a34a", "#f0fdf4", "#052e16"),
    ("#dc2626", "#fef2f2", "#450a0a"),
    ("#7c3aed", "#f5f3ff", "#2e1065"),
    ("#0891b2", "#ecfeff", "#083344"),
    ("#ca8a04", "#fefce8", "#422006"),
    ("#db2777", "#fdf2f8", "#500724"),
    ("#4f46e5", "#eef2ff", "#1e1b4b"),
]

ASSET_PHRASES_BY_CODE = {
    "school_sync": ["学校教材同步的占位素材", "教材版本一致", "课程章节同步"],
    "animation_explanation": ["动画讲知识点的占位素材", "抽象知识可视化", "知识点动画演示"],
    "instant_quiz": ["课后小测占位素材", "学完检测一下", "课堂掌握结果"],
    "new_curriculum_prediction": ["新课标新考法占位素材", "跨学科情境题", "新考法预测"],
    "focused_excellence": ["专项培优占位素材", "薄弱重难点突破", "压轴题专项"],
    "transfer_practice": ["举一反三占位素材", "换个问法也会做", "同类题迁移练习"],
    "expert_planning": ["专家规划占位素材", "命题专家设计", "教材编者规划"],
    "stage_transition": ["学段衔接占位素材", "小升初衔接", "初升高过渡"],
    "universal_method": ["万能解法占位素材", "一题多解", "底层方法训练"],
    "ai_learning_plan": ["AI定制学习方案占位素材", "量身定制课表", "学习路径自动规划"],
    "ai_tutor_qa": ["AI私教答疑占位素材", "随时提问答疑", "作业卡住有人讲"],
    "photo_guided_learning": ["AI拍题精学占位素材", "拍题分步引导", "拒绝直接给答案"],
    "rapid_preview_review": ["极速预习复习占位素材", "课前快速预习", "课后快速复习"],
    "ai_error_book": ["AI错题本占位素材", "错题自动归档", "同类题推荐"],
    "human_teacher_supervision": ["真人老师督学占位素材", "老师提醒打卡", "学习过程有人管"],
    "learning_report": ["学情报告反馈占位素材", "微信学习周报", "家长看到学习结果"],
}


@dataclass(frozen=True)
class PlaceholderSpec:
    serial_no: int
    variant_no: int
    concept_code: str
    concept_name: str
    system_name: str
    secondary_concept_code: str | None
    secondary_concept_name: str | None
    title: str
    channel: str
    width: int
    height: int
    is_scene_image: bool | None
    style_label: str
    relation_role: str
    proof_point_code: str | None
    evidence_point_code: str | None
    phrases: tuple[str, ...]


def load_ordered_concepts() -> list[tuple[str, str]]:
    raw = json.loads(SELLING_POINT_MAP_PATH.read_text(encoding="utf-8"))
    ordered: list[tuple[str, str]] = []
    for system in raw.get("systems", []):
        system_name = str(system.get("displayName") or "")
        for item in system.get("sellingPoints", []):
            ordered.append((str(item["code"]), system_name))
    return ordered


def build_specs(
    concepts_by_code: dict[str, BusinessConcept],
    count: int,
) -> list[PlaceholderSpec]:
    proof_by_concept: dict[str, list[str]] = {}
    for point in load_proof_point_catalog().points:
        proof_by_concept.setdefault(point.concept_code, []).append(point.code)
    evidence_by_proof: dict[str, list[str]] = {}
    for point in load_evidence_point_catalog().points:
        evidence_by_proof.setdefault(point.proof_point_code, []).append(point.code)

    ordered_concepts = load_ordered_concepts()
    specs: list[PlaceholderSpec] = []
    if count <= 0 or not ordered_concepts:
        return specs

    for index in range(count):
        concept_index = index % len(ordered_concepts)
        variant_no = index // len(ordered_concepts) + 1
        concept_code, system_name = ordered_concepts[concept_index]
        concept = concepts_by_code.get(concept_code)
        if concept is None:
            continue
        channel, width, height, style_label = CHANNEL_PLAN[
            (concept_index + variant_no - 1) % len(CHANNEL_PLAN)
        ]
        is_scene_image = SCENE_PLAN[(index + variant_no) % len(SCENE_PLAN)]
        relation_role = RELATION_PLAN[
            (variant_no + concept_index - 1) % len(RELATION_PLAN)
        ]
        proof_code = (proof_by_concept.get(concept_code) or [None])[0]
        evidence_code = (evidence_by_proof.get(proof_code or "") or [None])[0]
        secondary_code = None
        secondary_name = None
        if variant_no % 5 == 0 and len(ordered_concepts) > 1:
            secondary_code = ordered_concepts[(concept_index + 1) % len(ordered_concepts)][0]
            secondary = concepts_by_code.get(secondary_code)
            secondary_name = secondary.name if secondary is not None else None
        scene_phrase = (
            "场景图"
            if is_scene_image is True
            else "非场景图"
            if is_scene_image is False
            else "未标注场景"
        )
        phrases = tuple(
            str(item)
            for item in dict.fromkeys([
                *(ASSET_PHRASES_BY_CODE.get(concept_code) or []),
                f"{channel}可用{concept.name}",
                f"{concept.name}测试图",
                f"{concept.name}{scene_phrase}",
                *((
                    f"同时可参考{secondary_name}",
                    f"{concept.name}和{secondary_name}混合测试",
                ) if secondary_name else ()),
            ])
        )
        specs.append(
            PlaceholderSpec(
                serial_no=index + 1,
                variant_no=variant_no,
                concept_code=concept_code,
                concept_name=concept.name,
                system_name=system_name,
                secondary_concept_code=secondary_code,
                secondary_concept_name=secondary_name,
                title=(
                    f"{PLACEHOLDER_PREFIX}｜批量{variant_no:02d}｜"
                    f"{concept.name}｜{channel}"
                ),
                channel=channel,
                width=width,
                height=height,
                is_scene_image=is_scene_image,
                style_label=style_label,
                relation_role=relation_role,
                proof_point_code=proof_code,
                evidence_point_code=evidence_code,
                phrases=phrases,
            )
        )
    return specs


def draw_placeholder(spec: PlaceholderSpec, path: Path, palette_index: int) -> None:
    primary, background, ink = PALETTES[palette_index % len(PALETTES)]
    image = PillowImage.new("RGB", (spec.width, spec.height), background)
    draw = ImageDraw.Draw(image)
    font_large = load_font(54)
    font_medium = load_font(32)
    font_small = load_font(24)

    margin = max(36, min(spec.width, spec.height) // 18)
    draw.rounded_rectangle(
        (margin, margin, spec.width - margin, spec.height - margin),
        radius=28,
        fill="white",
        outline=primary,
        width=4,
    )
    draw.rectangle((margin, margin, spec.width - margin, margin + 86), fill=primary)
    draw.text((margin + 32, margin + 24), "TEST PLACEHOLDER", fill="white", font=font_medium)

    body_top = margin + 132
    draw.text((margin + 36, body_top), safe_ascii(spec.concept_code), fill=ink, font=font_large)
    draw.text(
        (margin + 36, body_top + 78),
        f"channel: {safe_ascii(spec.channel)}",
        fill=ink,
        font=font_medium,
    )
    draw.text(
        (margin + 36, body_top + 126),
        f"system: {safe_ascii(spec.system_name)}",
        fill=ink,
        font=font_small,
    )
    scene_label = (
        "scene: yes"
        if spec.is_scene_image is True
        else "scene: no"
        if spec.is_scene_image is False
        else "scene: unset"
    )
    draw.text(
        (margin + 36, body_top + 164),
        f"variant: {spec.variant_no:02d} / {scene_label}",
        fill=ink,
        font=font_small,
    )

    for offset, phrase in enumerate(spec.phrases[:3]):
        y = body_top + 220 + offset * 48
        draw.rounded_rectangle(
            (margin + 36, y, min(spec.width - margin - 36, margin + 560), y + 34),
            radius=17,
            fill=background,
            outline=primary,
            width=2,
        )
        draw.text((margin + 54, y + 7), safe_ascii(phrase), fill=ink, font=font_small)

    marker_size = min(spec.width, spec.height) // 5
    x1 = spec.width - margin - marker_size - 28
    y1 = spec.height - margin - marker_size - 28
    draw.rounded_rectangle((x1, y1, x1 + marker_size, y1 + marker_size), radius=28, fill=primary)
    channel_mark = spec.channel[:6].encode("ascii", "ignore").decode() or "CH"
    draw.text(
        (x1 + 28, y1 + marker_size // 2 - 16),
        channel_mark,
        fill="white",
        font=font_small,
    )

    image.save(path, format="PNG", optimize=True)


def safe_ascii(value: str) -> str:
    converted = value.encode("ascii", "ignore").decode().strip()
    return converted or "placeholder"


def load_font(size: int):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def semantic_profile(spec: PlaceholderSpec) -> str:
    return json.dumps(
        {
            "schema_version": 3,
            "visual_facts": [
                f"测试占位图：{spec.concept_name}",
                f"渠道占位：{spec.channel}",
                f"样式占位：{spec.style_label}",
                f"批量变体：{spec.variant_no:02d}",
                (
                    "场景图占位"
                    if spec.is_scene_image is True
                    else "非场景图占位"
                    if spec.is_scene_image is False
                    else "未标注场景状态占位"
                ),
            ],
            "scenes": [
                "业务测试占位素材",
                "可用于搜索与渠道筛选验收",
            ],
            "business_context": {
                "primary_concept": spec.concept_name,
                "secondary_concept": spec.secondary_concept_name,
                "relation_role": spec.relation_role,
                "channel": spec.channel,
            },
            "asset_search_phrases": list(spec.phrases),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def sync_existing_placeholder(
    image: Image,
    spec: PlaceholderSpec,
    concepts: dict[str, BusinessConcept],
) -> bool:
    group = image.asset_group
    if (
        group is None
        or group.created_by != PLACEHOLDER_ACTOR
        or not group.title.startswith(PLACEHOLDER_PREFIX)
    ):
        return False
    concept = concepts[spec.concept_code]
    group.approval_status = "approved"
    group.publish_status = "published"
    group.style_label = spec.style_label
    group.is_scene_image = spec.is_scene_image
    group.primary_proof_point_code = spec.proof_point_code
    group.primary_evidence_point_code = spec.evidence_point_code
    image.channel = spec.channel
    image.width = spec.width
    image.height = spec.height
    image.aspect_ratio = spec.width / spec.height
    image.semantic_profile_json = semantic_profile(spec)

    primary_link = next(
        (
            link
            for link in group.concept_links
            if link.concept_id == concept.id
            and link.origin == "manual"
            and link.source_ref == PLACEHOLDER_SOURCE_REF
        ),
        None,
    )
    if primary_link is None:
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role=spec.relation_role,
                origin="manual",
                review_status="accepted",
                confidence=1.0,
                evidence_reason=f"测试占位素材，明确用于覆盖 {concept.name} 的搜索验收。",
                source_ref=PLACEHOLDER_SOURCE_REF,
            )
        )
    else:
        primary_link.relation_role = spec.relation_role
        primary_link.review_status = "accepted"
        primary_link.confidence = 1.0
        primary_link.evidence_reason = (
            f"测试占位素材，明确用于覆盖 {concept.name} 的搜索验收。"
        )

    existing_phrases = {
        phrase.phrase
        for phrase in group.search_phrases
        if phrase.origin == "manual"
    }
    group.search_phrases.extend(
        AssetSearchPhrase(
            phrase=phrase,
            origin="manual",
            review_status="accepted",
            weight=1.0,
        )
        for phrase in spec.phrases
        if phrase not in existing_phrases
    )
    return True


def resolve_storage_path(root: Path, key: str | None) -> Path | None:
    if not key:
        return None
    target = (root / key).resolve()
    root_resolved = root.resolve()
    if target == root_resolved or root_resolved not in target.parents:
        raise ValueError(f"storage key escaped storage root: {key}")
    return target


def resolve_thumbnail_path(root: Path, key: str | None) -> Path | None:
    if not key:
        return None
    target = (root / ".thumbnails" / key).resolve()
    root_resolved = root.resolve()
    if target == root_resolved or root_resolved not in target.parents:
        raise ValueError(f"thumbnail key escaped storage root: {key}")
    return target


def seed(count: int = DEFAULT_PLACEHOLDER_COUNT, dry_run: bool = False) -> tuple[int, int]:
    settings = get_settings()
    storage_root = settings.storage_dir
    thumbnails = storage_root / ".thumbnails"
    storage_root.mkdir(parents=True, exist_ok=True)
    thumbnails.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        concepts = {
            item.code: item
            for item in db.scalars(
                select(BusinessConcept).where(BusinessConcept.status == "active")
            ).all()
        }
        specs = build_specs(concepts, max(count, 0))

        created = skipped = 0
        search_index = SearchIndexSync.from_settings()
        identities = AssetIdentityService(db)
        for index, spec in enumerate(specs):
            existing = db.scalar(select(Image).where(Image.title == spec.title))
            if existing is not None:
                if not dry_run and sync_existing_placeholder(existing, spec, concepts):
                    search_index.upsert_image(existing)
                skipped += 1
                continue
            if dry_run:
                print(f"would create: {spec.title} [{spec.channel}] -> {spec.concept_code}")
                created += 1
                continue

            image_id = str(uuid.uuid4())
            storage_key = f"{uuid.uuid4()}.png"
            thumbnail_key = f"{uuid.uuid4()}.jpg"
            image_path = storage_root / storage_key
            thumbnail_path = thumbnails / thumbnail_key
            draw_placeholder(spec, image_path, index)
            with PillowImage.open(image_path) as image:
                thumbnail = image.copy()
                thumbnail.thumbnail((settings.thumbnail_max_size, settings.thumbnail_max_size))
                thumbnail.convert("RGB").save(
                    thumbnail_path,
                    format="JPEG",
                    quality=82,
                    optimize=True,
                )

            concept = concepts[spec.concept_code]
            group = AssetGroup(
                asset_code=identities.allocate_asset_code(),
                title=spec.title,
                approval_status="approved",
                publish_status="published",
                style_label=spec.style_label,
                is_scene_image=spec.is_scene_image,
                primary_proof_point_code=spec.proof_point_code,
                primary_evidence_point_code=spec.evidence_point_code,
                created_by=PLACEHOLDER_ACTOR,
            )
            image = Image(
                id=image_id,
                version_code=identities.allocate_version_code(group.asset_code, 1),
                title=spec.title,
                file_name=(
                    f"placeholder-{spec.serial_no:04d}-"
                    f"{spec.concept_code}-{safe_ascii(spec.channel).replace(' ', '-')}.png"
                ),
                storage_key=storage_key,
                thumbnail_storage_key=thumbnail_key,
                media_type="image/png",
                size_bytes=image_path.stat().st_size,
                uploader=PLACEHOLDER_ACTOR,
                image_summary=(
                    f"这是一张用于测试的占位素材，模拟“{spec.concept_name}”卖点在"
                    f"“{spec.channel}”渠道下的可用图片。"
                ),
                semantic_profile_json=semantic_profile(spec),
                asset_group=group,
                asset_role="primary",
                width=spec.width,
                height=spec.height,
                aspect_ratio=spec.width / spec.height,
                channel=spec.channel,
                version_no=1,
                is_current=True,
            )
            group.primary_image_id = image_id
            group.concept_links.append(
                AssetConceptLink(
                    concept=concept,
                    relation_role=spec.relation_role,
                    origin="manual",
                    review_status="accepted",
                    confidence=1.0,
                    evidence_reason=f"测试占位素材，明确用于覆盖 {concept.name} 的搜索验收。",
                    source_ref=PLACEHOLDER_SOURCE_REF,
                )
            )
            if spec.secondary_concept_code is not None:
                secondary = concepts.get(spec.secondary_concept_code)
                if secondary is not None:
                    group.concept_links.append(
                        AssetConceptLink(
                            concept=secondary,
                            relation_role="supports",
                            origin="manual",
                            review_status="accepted",
                            confidence=0.82,
                            evidence_reason=(
                                "测试占位素材，用于模拟一张图同时支持多个卖点的验收。"
                            ),
                            source_ref=PLACEHOLDER_SOURCE_REF,
                        )
                    )
            group.search_phrases.extend(
                AssetSearchPhrase(
                    phrase=phrase,
                    origin="manual",
                    review_status="accepted",
                    weight=1.0,
                )
                for phrase in spec.phrases
            )
            db.add(image)
            db.flush()
            identities.register_group(group)
            identities.register_image(image)
            db.flush()
            search_index.upsert_image(image)
            created += 1

        db.commit()
        return created, skipped


def load_placeholder_groups(db) -> list[AssetGroup]:
    return db.scalars(
        select(AssetGroup).where(
            AssetGroup.created_by == PLACEHOLDER_ACTOR,
            AssetGroup.title.startswith(PLACEHOLDER_PREFIX),
        )
    ).all()


def delete_placeholders(dry_run: bool = False) -> tuple[int, int, int]:
    settings = get_settings()
    storage_root = settings.storage_dir
    with SessionLocal() as db:
        groups = load_placeholder_groups(db)
        image_ids: list[str] = []
        file_paths: list[Path] = []
        for group in groups:
            for image in group.images:
                image_ids.append(image.id)
                for path in (
                    resolve_storage_path(storage_root, image.storage_key),
                    resolve_thumbnail_path(storage_root, image.thumbnail_storage_key),
                ):
                    if path is not None:
                        file_paths.append(path)

        if dry_run:
            for group in groups[:20]:
                print(f"would delete: {group.title}")
            if len(groups) > 20:
                print(f"... and {len(groups) - 20} more placeholder groups")
            return len(groups), len(image_ids), len(file_paths)

        search_index = SearchIndexSync.from_settings()
        for image_id in image_ids:
            search_index.delete_image(image_id)
        for group in groups:
            db.delete(group)
        db.commit()

        deleted_files = 0
        for path in file_paths:
            if path.exists():
                path.unlink()
                deleted_files += 1
        return len(groups), len(image_ids), deleted_files


def status() -> tuple[int, int, dict[str, int], dict[str, int]]:
    with SessionLocal() as db:
        groups = load_placeholder_groups(db)
        channel_counts: dict[str, int] = {}
        scene_counts = {"true": 0, "false": 0, "unset": 0}
        image_count = 0
        for group in groups:
            if group.is_scene_image is True:
                scene_counts["true"] += 1
            elif group.is_scene_image is False:
                scene_counts["false"] += 1
            else:
                scene_counts["unset"] += 1
            for image in group.images:
                image_count += 1
                channel = image.channel or "未标注渠道"
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
        return len(groups), image_count, channel_counts, scene_counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed published placeholder assets for local search testing."
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("seed", "delete", "status"),
        default="seed",
        help="Action to run. Defaults to seed.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_PLACEHOLDER_COUNT,
        help=(
            "How many placeholder assets to target when seeding. "
            f"Default: {DEFAULT_PLACEHOLDER_COUNT}."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Backward-compatible alias for --count.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended assets without writing files or database rows.",
    )
    args = parser.parse_args()
    count = args.limit if args.limit is not None else args.count
    if args.action == "delete":
        groups, images, files = delete_placeholders(dry_run=args.dry_run)
        action = "would delete" if args.dry_run else "deleted"
        print(f"Placeholder assets: {action}_groups={groups}, images={images}, files={files}")
        return
    if args.action == "status":
        groups, images, channels, scenes = status()
        print(f"Placeholder assets: groups={groups}, images={images}")
        print(f"Channels: {json.dumps(channels, ensure_ascii=False, sort_keys=True)}")
        print(f"Scenes: {json.dumps(scenes, ensure_ascii=False, sort_keys=True)}")
        return

    created, skipped = seed(count=count, dry_run=args.dry_run)
    action = "would create" if args.dry_run else "created"
    print(f"Placeholder assets: {action}={created}, skipped_existing={skipped}, target={count}")


if __name__ == "__main__":
    main()
