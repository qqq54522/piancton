from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.ai.skill_loader import INTENT_PROMPT_VERSION
from app.core.errors import AppError
from app.domain.business_intents import BusinessIntentCatalog
from app.domain.query_negation import is_term_negated
from app.domain.runtime_intents import (
    RuntimeIntent,
    RuntimeIntentCatalog,
    runtime_catalog_from_static,
)
from app.domain.search_policy import SearchPolicyCatalog, load_search_policy
from app.schemas.ai import (
    SearchConceptMatch,
    SearchEvidencePointMatch,
    SearchProofPointMatch,
    SearchSystemRouting,
    SearchUnderstanding,
)
from app.services.ai_service import AiService
from app.services.evidence_point_understanding_service import (
    EvidencePointUnderstandingService,
)
from app.services.proof_point_understanding_service import (
    ProofPointUnderstandingService,
)
from app.services.search_models import ConceptMatch, ModelAttemptDiagnostic


@dataclass(frozen=True)
class IntentMatch:
    intent: RuntimeIntent
    confidence: float
    reasons: tuple[str, ...]
    matched_terms: tuple[str, ...]


LOCAL_TRUST_THRESHOLD = 0.85
AMBIGUOUS_CONFIDENCE_GAP = 0.05
UNCERTAIN_FALLBACK_CONFIDENCE = 0.74
EXPLORATION_CONFIDENCE = 0.88
EXPLORATION_OVERRIDE_THRESHOLD = 0.9
LOCAL_MATCHER_VERSION = "2026-07-27.2"
TRANSFER_TRAINING_PHRASES = ("变式训练", "同类题训练")
TRANSFER_TRAINING_CONTEXT = (
    "例题",
    "讲完",
    "讲解后",
    "一道题",
    "题型",
    "换数字",
    "换条件",
    "换问法",
    "会做",
    "不会做",
    "迁移",
)
ERROR_BOOK_CONTEXT = (
    "错题",
    "错题本",
    "错因",
    "历史错题",
    "个人错题",
    "做错",
    "反复错",
)
QUIZ_MEASUREMENT_CONTEXT = (
    "小测",
    "测验",
    "检测",
    "测试",
    "正确率",
    "掌握情况",
    "反馈",
    "分数",
    "测一测",
)
EXAM_STAGE_MARKERS = ("月考", "期中", "期末", "模考", "中考", "高考", "考试", "考前")
EXAM_FOCUS_MARKERS = (
    "划重点",
    "一键划重点",
    "抓重点",
    "重点梳理",
    "重点复习",
    "冲刺",
    "突击",
    "高频考点",
)
TRUSTED_LOCAL_QUERY_TYPES = frozenset(
    {
        "business_intent_search",
        "multi_business_intent_search",
        "exploratory_business_intent_search",
    }
)
PROOF_DETAIL_FILLERS = (
    "帮我找一张",
    "帮我找个",
    "帮我找",
    "给我找一张",
    "给我找个",
    "给我找",
    "我想找一张",
    "我想找个",
    "我想找",
    "想找一张",
    "想找个",
    "想找",
    "有没有",
    "能不能",
    "可不可以",
    "我需要",
    "需要",
    "我想要",
    "想要",
    "推荐一张",
    "推荐",
    "相关素材",
    "相关图片",
    "素材",
    "图片",
    "那种",
    "这种",
    "一个",
    "一张",
    "的图",
    "图",
    "请",
    "的",
)
MIN_PROOF_DETAIL_LENGTH = 4


class QueryUnderstandingService:
    def __init__(
        self,
        ai_service: AiService | None = None,
        catalog: BusinessIntentCatalog | None = None,
        search_policy: SearchPolicyCatalog | None = None,
        runtime_catalog: RuntimeIntentCatalog | None = None,
    ):
        self.ai_service = ai_service
        self.catalog = runtime_catalog or runtime_catalog_from_static(catalog)
        self.search_policy = search_policy or load_search_policy()
        self.proof_points = ProofPointUnderstandingService()
        self.evidence_points = EvidencePointUnderstandingService()
        knowledge = getattr(self.ai_service, "knowledge", None)
        catalog_text = str(getattr(knowledge, "catalog_text", "") or "")
        self._cache_namespace = hashlib.sha256(
            (
                f"{INTENT_PROMPT_VERSION}\n"
                f"{LOCAL_MATCHER_VERSION}\n"
                f"{self.catalog.version}\n{self.proof_points.catalog.version}\n"
                f"{self.evidence_points.catalog.version}\n{catalog_text}"
            ).encode("utf-8")
        ).hexdigest()[:16]

    def understand(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query:
            return None
        negated = self._negated_intent_names(query)
        composed = self._composition_understanding(query, negated)
        if composed is not None:
            return composed
        matches = self._local_matches(query)
        exploration = self._exploration_understanding(query, matches, negated)
        if exploration is not None:
            return exploration
        if matches and self._should_trust_local(query, matches):
            return self._with_local_proof_points(
                query,
                self._understanding_from_matches(
                    query,
                    matches,
                    negated_names=negated,
                ),
            )

        ai_understanding = self._understand_with_ai(query)
        if ai_understanding:
            return _with_negated_concepts(ai_understanding, negated)

        if matches:
            return self._understanding_from_matches(
                query,
                matches,
                negated_names=negated,
                confidence_cap=UNCERTAIN_FALLBACK_CONFIDENCE,
                fallback_reason="本地意图不确定，AI 不可用，使用本地弱兜底",
            )
        if negated:
            return self._negative_only_understanding(query, negated)
        return None

    def cache_key(self, keyword: str) -> str:
        """Namespace cached model understanding by the active database knowledge."""
        normalized_query = _normalize(keyword) or keyword.strip().lower()
        return f"{self._cache_namespace}:{normalized_query}"

    def explicit_understanding(
        self,
        query: str,
        *,
        concept_code: str,
        proof_point_code: str | None = None,
        evidence_point_code: str | None = None,
    ) -> SearchUnderstanding | None:
        intent = next(
            (item for item in self.catalog.intents if item.code == concept_code),
            None,
        )
        if intent is None:
            return None
        evidence = (
            self.evidence_points.catalog.by_code.get(evidence_point_code)
            if evidence_point_code
            else None
        )
        if evidence_point_code and evidence is None:
            return None
        resolved_proof_code = proof_point_code or (
            evidence.proof_point_code if evidence else None
        )
        proof = (
            self.proof_points.catalog.by_code.get(resolved_proof_code)
            if resolved_proof_code
            else None
        )
        if resolved_proof_code and proof is None:
            return None
        if proof and proof.concept_code != concept_code:
            return None
        if evidence and (
            evidence.concept_code != concept_code
            or evidence.proof_point_code != resolved_proof_code
        ):
            return None
        proof_matches = []
        if proof:
            proof_matches.append(
                SearchProofPointMatch(
                    code=proof.code,
                    concept_code=proof.concept_code,
                    name=proof.name,
                    reason="用户手动选择证明点",
                    weight=1.0,
                    evidence_terms=list(proof.search_terms[:3]),
                )
            )
        evidence_matches = []
        if evidence:
            evidence_matches.append(
                SearchEvidencePointMatch(
                    code=evidence.code,
                    proof_point_code=evidence.proof_point_code,
                    concept_code=evidence.concept_code,
                    name=evidence.name,
                    reason="用户手动选择证据表达点",
                    weight=1.0,
                )
            )
        return SearchUnderstanding(
            original_query=query,
            normalized_query=intent.name,
            search_intent=f"用户手动限定为“{intent.name}”",
            query_type="business_intent_search",
            matched_business_concepts=[
                SearchConceptMatch(
                    concept=intent.display_name,
                    relation="direct",
                    reason="用户手动选择卖点",
                    weight=1.0,
                )
            ],
            matched_proof_points=proof_matches,
            matched_evidence_points=evidence_matches,
            search_strategy="按用户手动选择的业务层级执行硬约束搜索",
        )

    def understand_locally(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query:
            return None
        negated = self._negated_intent_names(query)
        composed = self._composition_understanding(query, negated)
        if composed is not None:
            return composed
        matches = self._local_matches(query)
        exploration = self._exploration_understanding(query, matches, negated)
        if exploration is not None:
            return exploration
        if not matches:
            if negated:
                return self._negative_only_understanding(query, negated)
            return None
        if self._should_trust_local(query, matches):
            return self._with_local_proof_points(
                query,
                self._understanding_from_matches(
                    query,
                    matches,
                    negated_names=negated,
                ),
            )
        return self._understanding_from_matches(
            query,
            matches,
            negated_names=negated,
            confidence_cap=UNCERTAIN_FALLBACK_CONFIDENCE,
            fallback_reason="本地意图仍需消歧，不进入高置信卖点主通道",
        )

    def should_use_model(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
    ) -> bool:
        return bool(
            keyword.strip()
            and self.ai_service
            and self.ai_service.provider.configured
            and not self._is_manual_business_filter(local_understanding)
        )

    def needs_proof_point_completion(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
    ) -> bool:
        if (
            self._is_manual_business_filter(local_understanding)
            or
            not self._has_trusted_local_understanding(local_understanding)
            or local_understanding is None
            or local_understanding.matched_proof_points
        ):
            return False
        active_codes = self._active_concept_codes(local_understanding)
        if not active_codes:
            return False
        matched_terms = [
            term
            for match in self._local_matches(keyword)
            if match.intent.code in active_codes
            for term in match.matched_terms
        ]
        remainder = _proof_detail_remainder(keyword, matched_terms)
        return len(remainder) >= MIN_PROOF_DETAIL_LENGTH

    @staticmethod
    def _is_manual_business_filter(
        understanding: SearchUnderstanding | None,
    ) -> bool:
        return bool(
            understanding
            and understanding.search_strategy
            == "按用户手动选择的业务层级执行硬约束搜索"
        )

    def complete_proof_points_with_model(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding,
    ) -> SearchUnderstanding | None:
        if not self.ai_service or not self.supports_staged_model:
            return None
        return self.ai_service.understand_proof_points(keyword, local_understanding)

    def arbitrate_model_understanding(
        self,
        local_understanding: SearchUnderstanding | None,
        model_understanding: SearchUnderstanding | None,
    ) -> SearchUnderstanding | None:
        """Keep trusted local evidence authoritative; use the model for gaps.

        A valid model response only proves that the provider completed the JSON
        contract.  It does not make a contradictory business decision correct.
        Local single, multi and exploratory routes already backed by direct
        high-confidence catalog evidence therefore cannot be removed or changed
        by the model.  Ambiguous, visual and no-reliable local states remain open
        for model completion.
        """
        if model_understanding is None:
            return local_understanding
        if self._has_trusted_local_understanding(local_understanding):
            assert local_understanding is not None
            return self._with_local_proof_points(
                local_understanding.original_query,
                local_understanding,
                model_matches=list(model_understanding.matched_proof_points),
                model_evidence_matches=list(
                    model_understanding.matched_evidence_points
                ),
            )
        return model_understanding

    def understand_with_model(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.ai_service or not self.ai_service.provider.configured:
            return None
        return _with_negated_concepts(
            self.ai_service.understand_search(query),
            self._negated_intent_names(query),
        )

    @property
    def supports_staged_model(self) -> bool:
        return bool(
            self.ai_service
            and callable(getattr(self.ai_service, "route_search_system", None))
            and callable(
                getattr(self.ai_service, "understand_selling_points_from_route", None)
            )
            and callable(getattr(self.ai_service, "understand_proof_points", None))
        )

    def route_with_model(self, keyword: str) -> SearchSystemRouting:
        query = keyword.strip()
        if not query or not self.ai_service or not self.supports_staged_model:
            raise AppError(
                "provider_not_configured",
                "查询理解模型不支持分层调用",
                status_code=503,
            )
        return self.ai_service.route_search_system(query)

    def routed_system_codes(
        self,
        routing: SearchSystemRouting,
    ) -> tuple[str, ...]:
        if not self.ai_service:
            return ()
        resolver = getattr(self.ai_service, "routed_system_codes", None)
        if not callable(resolver):
            return ()
        resolved = resolver(routing)
        if not isinstance(resolved, (list, tuple, set)):
            return ()
        return tuple(str(item) for item in resolved)

    def understand_with_model_route(
        self,
        keyword: str,
        routing: SearchSystemRouting,
    ) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.ai_service or not self.supports_staged_model:
            return None
        return _with_negated_concepts(
            self.ai_service.understand_search_from_route(query, routing),
            self._negated_intent_names(query),
        )

    def understand_selling_points_with_model_route(
        self,
        keyword: str,
        routing: SearchSystemRouting,
    ) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.ai_service or not self.supports_staged_model:
            return None
        try:
            result = _with_negated_concepts(
                self.ai_service.understand_selling_points_from_route(query, routing),
                self._negated_intent_names(query),
            )
        except AppError:
            repaired = self._repair_routed_selling_point_understanding(query, routing)
            if repaired is not None:
                return repaired
            raise
        if result is None or not result.matched_business_concepts:
            repaired = self._repair_routed_selling_point_understanding(query, routing)
            if repaired is not None:
                return repaired
        return result

    def model_attempts_detail(self) -> str:
        provider = getattr(self.ai_service, "provider", None)
        attempts = getattr(provider, "last_attempts", None)
        if not isinstance(attempts, list) or not attempts:
            return ""
        parts = []
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            provider_name = str(attempt.get("provider") or "unknown")
            model = str(attempt.get("model") or "unknown")
            status = str(attempt.get("status") or "unknown")
            duration_ms = int(attempt.get("duration_ms") or 0)
            error = str(attempt.get("error") or "").strip()
            suffix = f"，{error}" if error else ""
            parts.append(f"{provider_name}/{model} {status} {duration_ms}ms{suffix}")
        return "；".join(parts)

    def model_attempts(
        self,
        *,
        task: str,
        layer: str,
    ) -> tuple[ModelAttemptDiagnostic, ...]:
        provider = getattr(self.ai_service, "provider", None)
        attempts = getattr(provider, "last_attempts", None)
        if not isinstance(attempts, list) or not attempts:
            return ()
        rows: list[ModelAttemptDiagnostic] = []
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            rows.append(
                ModelAttemptDiagnostic(
                    task=task,
                    layer=layer,
                    provider=str(attempt.get("provider") or "unknown")[:120],
                    model=str(attempt.get("model") or "unknown")[:120],
                    status=str(attempt.get("status") or "unknown")[:24],
                    duration_ms=int(attempt.get("duration_ms") or 0),
                    fallback_index=_optional_int(attempt.get("fallback_index")),
                    error=str(attempt.get("error") or "")[:300],
                )
            )
        return tuple(rows)

    def review_candidates_with_model(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        candidates: list[dict],
    ):
        query = keyword.strip()
        if (
            not query
            or not candidates
            or not self.ai_service
            or not self.ai_service.provider.configured
            or not callable(
                getattr(self.ai_service, "review_search_candidates", None)
            )
        ):
            return None
        return self.ai_service.review_search_candidates(
            keyword=query,
            understanding=understanding,
            candidates=candidates,
        )

    def understand_proof_points_with_model(
        self,
        keyword: str,
        selling_points: SearchUnderstanding,
    ) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.ai_service or not self.supports_staged_model:
            return None
        return _with_negated_concepts(
            self.ai_service.understand_proof_points(query, selling_points),
            self._negated_intent_names(query),
        )

    def weak_local_fallback(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query:
            return None
        matches = self._local_matches(query)
        negated = self._negated_intent_names(query)
        exploration = self._exploration_understanding(query, matches, negated)
        if exploration is not None:
            return exploration
        if not matches:
            if negated:
                return self._negative_only_understanding(query, negated)
            return None
        return self._understanding_from_matches(
            query,
            matches,
            negated_names=negated,
            confidence_cap=UNCERTAIN_FALLBACK_CONFIDENCE,
            fallback_reason="本地意图不确定，模型不可用，使用本地弱兜底",
        )

    def present_recognized_concepts(
        self,
        keyword: str,
        understanding: SearchUnderstanding | None,
        concept_matches: list[ConceptMatch],
    ) -> SearchUnderstanding | None:
        """Expose the validated concept candidates used by recall to the result UI."""
        if understanding is None and not concept_matches:
            return None
        strong_matches = [match for match in concept_matches if match.score >= 0.9]
        promote_explicit_multi = bool(
            understanding
            and understanding.query_type == "ambiguous_business_intent_search"
            and len(strong_matches) > 1
            and _has_explicit_multi_marker(keyword)
        )
        existing = (
            []
            if promote_explicit_multi
            else list(understanding.matched_business_concepts)
            if understanding
            else []
        )
        existing_keys = {_concept_key(item.concept) for item in existing}
        additions = strong_matches if promote_explicit_multi else concept_matches
        if understanding is not None and not promote_explicit_multi:
            additions = []
        elif len(concept_matches) > 1:
            # Multiple raw database matches are alternatives until query understanding
            # confirms that the sentence genuinely expresses several selling points.
            if not promote_explicit_multi:
                return None
        for match in additions:
            key = _concept_key(match.name)
            if key in existing_keys:
                continue
            existing.append(
                SearchConceptMatch(
                    concept=match.name,
                    relation="direct" if match.score >= 0.9 else "related",
                    reason="；".join(match.reasons) or "本地卖点识别",
                    weight=match.score,
                )
            )
            existing_keys.add(key)

        if not existing:
            return understanding
        existing.sort(key=lambda item: item.weight, reverse=True)
        concept_names = [_display_concept_name(item.concept) for item in existing]
        confirmed_multi = promote_explicit_multi or bool(
            understanding and understanding.query_type == "multi_business_intent_search"
        )
        exploratory = bool(
            understanding and understanding.query_type == "exploratory_business_intent_search"
        )
        if confirmed_multi:
            intent_summary = f"本次需求可能同时涉及：{'、'.join(concept_names[:4])}"
            query_type = "multi_business_intent_search"
            strategy = "按多个候选卖点并行召回，再由素材独有表达和画面语义区分"
        elif exploratory:
            intent_summary = f"你可能在找：{'、'.join(concept_names[:4])}"
            query_type = "exploratory_business_intent_search"
            strategy = "共享入口词命中多个卖点方向，合并展示供二次筛选"
        else:
            intent_summary = (
                understanding.search_intent
                if understanding and understanding.search_intent
                else f"本次需求主要涉及：{concept_names[0]}"
            )
            unresolved_multiple = len(concept_names) > 1
            query_type = (
                "ambiguous_business_intent_search"
                if unresolved_multiple
                else understanding.query_type
                if understanding
                else "business_intent_search"
            )
            strategy = (
                "多个候选尚未确认可以同时成立，不执行多卖点硬路由"
                if unresolved_multiple
                else understanding.search_strategy
                if understanding and understanding.search_strategy
                else "优先按已确认卖点关系召回"
            )
        excluded = list(understanding.excluded_concepts) if understanding else []
        active_codes = {
            intent.code
            for intent in self.catalog.intents
            if _concept_key(intent.display_name) in existing_keys
            or _concept_key(intent.name) in existing_keys
        }
        proof_matches, evidence_matches = self._proof_and_evidence_matches(
            keyword,
            active_codes,
            list(understanding.matched_proof_points) if understanding else [],
            list(understanding.matched_evidence_points) if understanding else [],
        )
        return SearchUnderstanding(
            original_query=understanding.original_query if understanding else keyword,
            normalized_query=(
                understanding.normalized_query
                if understanding and understanding.normalized_query.strip()
                else concept_names[0]
            ),
            search_intent=intent_summary,
            query_type=query_type,
            expanded_terms=list(understanding.expanded_terms) if understanding else [],
            matched_business_concepts=existing,
            matched_proof_points=proof_matches,
            matched_evidence_points=evidence_matches,
            excluded_concepts=_unique([*excluded, *self._negated_intent_names(keyword)]),
            search_strategy=strategy,
        )

    def _local_matches(self, query: str) -> list[IntentMatch]:
        return sorted(
            (
                match
                for intent in self.catalog.intents
                if (match := self._match_intent(query, intent)) is not None
            ),
            key=lambda item: item.confidence,
            reverse=True,
        )

    def _with_local_proof_points(
        self,
        query: str,
        understanding: SearchUnderstanding,
        *,
        model_matches=None,
        model_evidence_matches=None,
    ) -> SearchUnderstanding:
        proof_matches, evidence_matches = self._proof_and_evidence_matches(
            query,
            self._active_concept_codes(understanding),
            list(model_matches or understanding.matched_proof_points),
            list(
                model_evidence_matches
                if model_evidence_matches is not None
                else understanding.matched_evidence_points
            ),
        )
        return understanding.model_copy(
            update={
                "matched_proof_points": proof_matches,
                "matched_evidence_points": evidence_matches,
            }
        )

    def _proof_and_evidence_matches(
        self,
        query: str,
        active_concept_codes: set[str],
        existing_proofs: list[SearchProofPointMatch],
        existing_evidence: list[SearchEvidencePointMatch],
    ) -> tuple[list[SearchProofPointMatch], list[SearchEvidencePointMatch]]:
        proof_matches = self.proof_points.recognize(
            query,
            active_concept_codes,
            existing_proofs,
        )
        evidence_matches = self.evidence_points.recognize(
            query,
            {item.code for item in proof_matches},
            active_concept_codes,
        )
        derived_proofs = []
        proof_catalog = self.proof_points.catalog.by_code
        active_proof_codes = {item.code for item in proof_matches}
        for evidence in evidence_matches:
            if evidence.proof_point_code in active_proof_codes:
                continue
            point = proof_catalog[evidence.proof_point_code]
            derived_proofs.append(
                SearchProofPointMatch(
                    code=point.code,
                    concept_code=point.concept_code,
                    name=point.name,
                    reason=f"由证据表达点反向定位：{evidence.name}",
                    weight=evidence.weight,
                    evidence_terms=[evidence.name],
                )
            )
        if derived_proofs:
            proof_matches = self.proof_points.recognize(
                query,
                active_concept_codes,
                [*proof_matches, *derived_proofs],
            )
        active_proof_codes = {item.code for item in proof_matches}
        return proof_matches, _merge_evidence_matches(
            existing_evidence,
            evidence_matches,
            active_proof_codes,
        )

    def _active_concept_codes(
        self,
        understanding: SearchUnderstanding,
    ) -> set[str]:
        keys = {
            _concept_key(item.concept)
            for item in understanding.matched_business_concepts
            if item.relation == "direct" and item.weight >= LOCAL_TRUST_THRESHOLD
        }
        return {
            intent.code
            for intent in self.catalog.intents
            if _concept_key(intent.display_name) in keys
            or _concept_key(intent.name) in keys
        }

    @staticmethod
    def _has_trusted_local_understanding(
        understanding: SearchUnderstanding | None,
    ) -> bool:
        if understanding is None or understanding.query_type not in TRUSTED_LOCAL_QUERY_TYPES:
            return False
        return any(
            item.relation == "direct" and item.weight >= LOCAL_TRUST_THRESHOLD
            for item in understanding.matched_business_concepts
        )

    def _should_trust_local(self, query: str, matches: list[IntentMatch]) -> bool:
        if not matches:
            return False
        top = matches[0]
        if top.confidence < LOCAL_TRUST_THRESHOLD:
            return False
        if len(matches) == 1:
            return not (self._is_ambiguous_query(query) and top.confidence < 0.95)
        second = matches[1]
        confidence_gap = top.confidence - second.confidence
        # A complete Skill interpretation signal can intentionally be shared by
        # adjacent selling points.  Equal direct evidence at the trusted tier is
        # an exploratory route, not an ambiguous weak fallback.  Generic weak
        # words remain below LOCAL_TRUST_THRESHOLD and cannot enter this branch.
        if _trusted_shared_entry_matches(matches):
            return True
        # A named/official selling-point expression is decisive when every
        # alternative is only a generic supporting word. For example,
        # “AI私教……定位知识薄弱点” explicitly asks for AI私教; the generic
        # “薄弱点” must not downgrade it into an ambiguous global search.
        if _has_unique_explicit_primary(top, matches[1:]):
            return True
        if top.confidence >= 0.9 and second.confidence >= 0.9 and _has_explicit_multi_marker(query):
            return True
        if self._is_ambiguous_query(query) and confidence_gap <= 0.15:
            return False
        if top.confidence >= 0.9 and second.confidence >= 0.9:
            return True
        return confidence_gap > AMBIGUOUS_CONFIDENCE_GAP

    def _understand_with_ai(self, query: str) -> SearchUnderstanding | None:
        if not self.ai_service or not self.ai_service.provider.configured:
            return None
        try:
            return self.ai_service.understand_search(query)
        except AppError:
            return None

    def _understanding_from_matches(
        self,
        query: str,
        matches: list[IntentMatch],
        *,
        negated_names: tuple[str, ...] = (),
        confidence_cap: float | None = None,
        fallback_reason: str | None = None,
    ) -> SearchUnderstanding:
        selected = _candidate_intent_matches(
            matches,
            include_weak_alternatives=confidence_cap is not None,
        )
        primary = selected[0]
        concept_matches: list[SearchConceptMatch] = []
        excluded: list[str] = []
        for match in selected:
            weight = match.confidence
            if confidence_cap is not None:
                weight = min(weight, confidence_cap)
            reasons = list(match.reasons)
            if fallback_reason:
                reasons.append(fallback_reason)
            concept_matches.append(
                SearchConceptMatch(
                    concept=match.intent.display_name,
                    relation="direct" if weight >= LOCAL_TRUST_THRESHOLD else "related",
                    reason="；".join(reasons),
                    weight=weight,
                )
            )
            excluded.extend(match.intent.exclude_concepts)
        excluded.extend(negated_names)
        names = [match.intent.name for match in selected]
        uncertain = confidence_cap is not None
        multiple = len(names) > 1 and not uncertain
        exploratory = multiple and _shares_single_entry_evidence(selected)
        confirmed_multi = multiple and not exploratory
        if exploratory:
            search_intent = f"你可能在找：{'、'.join(names)}"
            query_type = "exploratory_business_intent_search"
            strategy = "共享入口词命中多个卖点方向，合并召回后由用户二次筛选"
        elif confirmed_multi:
            search_intent = f"用户可能同时在找“{'、'.join(names)}”相关素材"
            query_type = "multi_business_intent_search"
            strategy = f"按{'、'.join(names)}多个候选卖点并行召回"
        elif uncertain:
            search_intent = f"当前只能判断可能涉及“{'、'.join(names)}”，仍需消歧"
            query_type = "ambiguous_business_intent_search"
            strategy = "不执行卖点硬路由，继续使用图片话术和画面语义兜底"
        else:
            search_intent = f"用户在找“{primary.intent.name}”相关素材"
            query_type = "business_intent_search"
            strategy = f"优先按{primary.intent.name}对应业务概念召回"
        return SearchUnderstanding(
            original_query=query,
            normalized_query=primary.intent.name,
            search_intent=search_intent,
            query_type=query_type,
            expanded_terms=[],
            matched_business_concepts=concept_matches,
            excluded_concepts=_unique(excluded),
            search_strategy=strategy,
        )

    def _exploration_understanding(
        self,
        query: str,
        matches: list[IntentMatch],
        negated_names: tuple[str, ...],
    ) -> SearchUnderstanding | None:
        """D079: object-less photo entry + explain purpose opens a fixed candidate set.

        “拍一下/拍照 + 马上讲解/点拨解析”没有说明拍摄对象，可能是拍题精学，
        也可能是极速预习复习。此时保持探索型合并召回；只有更强的单卖点证据
        （如明确“拍题”官方表达）才允许硬路由到唯一卖点。
        """
        if matches and matches[0].confidence >= EXPLORATION_OVERRIDE_THRESHOLD:
            return None
        needle = _normalize(query)
        if not needle:
            return None
        intents_by_code = {intent.code: intent for intent in self.catalog.intents}
        for signal in self.catalog.exploration_signals:
            entry_terms = [
                term
                for term in signal.entry_terms
                if _normalize(term) in needle and not is_term_negated(query, term)
            ]
            purpose_terms = [
                term
                for term in signal.purpose_terms
                if _normalize(term) in needle and not is_term_negated(query, term)
            ]
            if not entry_terms or not purpose_terms:
                continue
            candidates = [
                intent
                for code in signal.candidate_codes
                if (intent := intents_by_code.get(code)) is not None
                and intent.display_name not in negated_names
            ]
            if len(candidates) < 2:
                continue
            evidence = "、".join(dict.fromkeys([*entry_terms[:2], *purpose_terms[:2]]))
            names = [intent.name for intent in candidates]
            return SearchUnderstanding(
                original_query=query,
                normalized_query=candidates[0].name,
                search_intent=f"你可能在找：{'、'.join(names)}",
                query_type="exploratory_business_intent_search",
                expanded_terms=[],
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept=intent.display_name,
                        relation="direct",
                        reason=f"无对象拍摄入口与讲解目的组合命中：{evidence}",
                        weight=EXPLORATION_CONFIDENCE,
                    )
                    for intent in candidates
                ],
                excluded_concepts=_unique(list(negated_names)),
                search_strategy="共享入口词命中多个卖点方向，合并召回后由用户二次筛选",
            )
        return None

    def _negative_only_understanding(
        self,
        query: str,
        negated_names: tuple[str, ...],
    ) -> SearchUnderstanding:
        names = "、".join(_display_concept_name(item) for item in negated_names)
        return SearchUnderstanding(
            original_query=query,
            normalized_query=query,
            search_intent=f"用户明确不需要“{names}”，按其余方向全局召回",
            query_type="no_reliable_intent_search",
            expanded_terms=[],
            matched_business_concepts=[],
            excluded_concepts=list(negated_names),
            search_strategy="没有可信卖点主通道，使用图片话术和画面语义全局召回并排除否定卖点",
        )

    def _composition_understanding(
        self,
        query: str,
        negated_names: tuple[str, ...],
    ) -> SearchUnderstanding | None:
        """Apply governed object/time/action compositions before loose term matching."""
        needle = _normalize(query)
        if not needle:
            return None
        intents_by_code = {item.code: item for item in self.catalog.intents}
        candidates = []
        for signal in self.catalog.composition_signals:
            intent = intents_by_code.get(signal.concept_code)
            if (
                intent is None
                or intent.display_name in negated_names
                or intent.name in negated_names
            ):
                continue
            if any(
                _normalize(term) in needle and not is_term_negated(query, term)
                for term in signal.excluded_terms
            ):
                continue
            matched_groups: list[tuple[str, str]] = []
            for group in signal.groups:
                matched = [
                    term
                    for term in group.terms
                    if _normalize(term) in needle and not is_term_negated(query, term)
                ]
                if not matched:
                    break
                matched_groups.append(
                    (group.name, max(matched, key=lambda item: len(_normalize(item))))
                )
            if len(matched_groups) != len(signal.groups):
                continue
            candidates.append((signal.confidence, signal, intent, matched_groups))
        if not candidates:
            return None
        confidence, signal, intent, matched_groups = max(
            candidates,
            key=lambda item: (item[0], sum(len(value) for _, value in item[3])),
        )
        evidence = "；".join(f"{name}={term}" for name, term in matched_groups)
        proof_matches: list[SearchProofPointMatch] = []
        evidence_matches: list[SearchEvidencePointMatch] = []
        proof_name = "直属证明点"
        if signal.proof_point_code:
            proof = self.proof_points.catalog.by_code.get(signal.proof_point_code)
            if proof is not None and proof.concept_code == intent.code:
                proof_name = proof.name
                allowed_evidence = [
                    term
                    for term in signal.evidence_terms
                    if term in (*proof.search_terms, *proof.asset_terms)
                ]
                proof_matches.append(
                    SearchProofPointMatch(
                        code=proof.code,
                        concept_code=proof.concept_code,
                        name=proof.name,
                        reason=f"组合语义命中：{evidence}",
                        weight=confidence,
                        evidence_terms=allowed_evidence[:3],
                    )
                )
                evidence_point = self.evidence_points.catalog.by_code.get(
                    signal.evidence_point_code
                )
                if (
                    evidence_point is not None
                    and evidence_point.concept_code == intent.code
                    and evidence_point.proof_point_code == proof.code
                ):
                    evidence_matches.append(
                        SearchEvidencePointMatch(
                            code=evidence_point.code,
                            proof_point_code=evidence_point.proof_point_code,
                            concept_code=evidence_point.concept_code,
                            name=evidence_point.name,
                            reason=f"组合语义命中：{evidence}",
                            weight=confidence,
                        )
                    )
        return SearchUnderstanding(
            original_query=query,
            normalized_query=intent.name,
            search_intent=f"用户在找“{intent.name}”中{proof_name}相关素材",
            query_type="business_intent_search",
            expanded_terms=[],
            matched_business_concepts=[
                SearchConceptMatch(
                    concept=intent.display_name,
                    relation="direct",
                    reason=f"组合语义命中：{evidence}",
                    weight=confidence,
                )
            ],
            matched_proof_points=proof_matches,
            matched_evidence_points=evidence_matches,
            excluded_concepts=list(negated_names),
            search_strategy="按受治理的组合语义进入卖点主通道，并下钻到直属证明点",
        )

    def _repair_routed_selling_point_understanding(
        self,
        query: str,
        routing: SearchSystemRouting,
    ) -> SearchUnderstanding | None:
        system_codes = self.routed_system_codes(routing)
        if "sync_exam" not in system_codes or not _is_exam_stage_focus_query(query):
            return None
        intent = next(
            (item for item in self.catalog.intents if item.code == "focused_excellence"),
            None,
        )
        if intent is None:
            return None
        negated = self._negated_intent_names(query)
        if intent.display_name in negated or intent.name in negated:
            return None
        proof_matches, evidence_matches = self._proof_and_evidence_matches(
            query,
            {"focused_excellence"},
            [],
            [],
        )
        if not proof_matches and (
            proof := self.proof_points.catalog.by_code.get("pp_exam_focus_stage_review")
        ):
            proof_matches = [
                SearchProofPointMatch(
                    code=proof.code,
                    concept_code=proof.concept_code,
                    name=proof.name,
                    reason="考试阶段重点梳理强信号保护性补全",
                    weight=0.9,
                    evidence_terms=["月考/期中/期末", "划重点"],
                )
            ]
        return SearchUnderstanding(
            original_query=query,
            normalized_query=intent.name,
            search_intent=f"用户在找“{intent.name}”中考试阶段重点梳理相关素材",
            query_type="business_intent_search",
            expanded_terms=[],
            matched_business_concepts=[
                SearchConceptMatch(
                    concept=intent.display_name,
                    relation="direct",
                    reason=(
                        "第一层已路由到同步考点，且原话命中考试阶段重点梳理强信号；"
                        "第二层模型结构不稳定时按知识库强别名保护性补全"
                    ),
                    weight=0.92,
                )
            ],
            matched_proof_points=proof_matches,
            matched_evidence_points=evidence_matches,
            excluded_concepts=list(negated),
            search_strategy="按同步考点强别名补全卖点后继续进入候选召回与第四层复核",
        )

    def _match_intent(
        self,
        keyword: str,
        intent: RuntimeIntent,
    ) -> IntentMatch | None:
        needle = _normalize(keyword)
        if not needle:
            return None
        weighted_groups = [
            (intent.phrases, 0.95, "功能表达命中"),
            (intent.pain_points, 0.9, "家长痛点命中"),
            (intent.interpretation_patterns, 0.88, "自然语言归一化命中"),
            (intent.must_have_concepts, 0.82, "必须概念命中"),
            (intent.nice_to_have_concepts, 0.72, "辅助概念命中"),
        ]
        scores: list[float] = []
        reasons: list[str] = []
        matched_terms: list[str] = []
        exact_only = [
            term
            for term in intent.exact_only_phrases
            if _normalize(term) == needle and not is_term_negated(keyword, term)
        ]
        if exact_only:
            scores.append(0.95)
            reasons.append(f"人工短话术精确命中：{'、'.join(exact_only[:3])}")
            matched_terms.append(needle)
        contextual_exact = _contextual_exact_only_matches(keyword, needle, intent)
        if contextual_exact:
            scores.append(0.95)
            reasons.append(
                f"共享训练话术经上下文消歧：{'、'.join(contextual_exact[:3])}"
            )
            matched_terms.extend(_normalize(term) for term in contextual_exact)
        for terms, score, reason_prefix in weighted_groups:
            matched = [
                term for term in _matched_terms(needle, terms) if not is_term_negated(keyword, term)
            ]
            if not matched:
                continue
            scores.append(score)
            reasons.append(f"{reason_prefix}：{'、'.join(matched[:3])}")
            # 记录查询侧证据：词条比查询长时（反向包含），证据是查询本身。
            matched_terms.extend(
                normalized if (normalized := _normalize(term)) in needle else needle
                for term in matched
            )
        if not scores:
            return None
        if (
            intent.code == "instant_quiz"
            and _contains_any(needle, TRANSFER_TRAINING_PHRASES)
            and _contains_any(needle, TRANSFER_TRAINING_CONTEXT)
            and not _contains_any(needle, QUIZ_MEASUREMENT_CONTEXT)
        ):
            scores = [min(score, 0.62) for score in scores]
            reasons.append("出现例题或变式训练且没有测评结果语义，排除课后小测主意图")
        if _matched_terms(needle, intent.exclude_concepts):
            scores = [min(score, 0.62) for score in scores]
            reasons.append("命中排除概念，降低置信度")
        return IntentMatch(
            intent=intent,
            confidence=max(scores),
            reasons=tuple(reasons),
            matched_terms=_maximal_terms(matched_terms),
        )

    def _negated_intent_names(self, keyword: str) -> tuple[str, ...]:
        """Intents whose only evidence in the query is explicitly negated."""
        needle = _normalize(keyword)
        if not needle:
            return ()
        names: list[str] = []
        for intent in self.catalog.intents:
            groups = [
                intent.phrases,
                intent.pain_points,
                intent.interpretation_patterns,
                intent.must_have_concepts,
            ]
            matched = [term for terms in groups for term in _matched_terms(needle, terms)]
            matched.extend(term for term in intent.exact_only_phrases if _normalize(term) == needle)
            if not matched:
                continue
            if all(is_term_negated(keyword, term) for term in matched):
                names.append(intent.display_name)
        return tuple(_unique(names))

    def _is_ambiguous_query(self, query: str) -> bool:
        needle = _normalize(query)
        return any(
            _normalize(term) in needle
            for term in self.search_policy.ambiguous_terms
            if _normalize(term)
        )


def _matched_terms(needle: str, terms: tuple[str, ...]) -> list[str]:
    matched: list[str] = []
    for term in terms:
        normalized = _normalize(term)
        if len(normalized) < 2:
            continue
        if normalized in needle or (len(needle) >= 4 and needle in normalized):
            matched.append(term)
    return matched


def _is_exam_stage_focus_query(query: str) -> bool:
    needle = _normalize(query)
    if not needle:
        return False
    explicit = ("一键划重点", "月考划重点", "期中划重点", "期末划重点", "期末冲刺")
    if any(_normalize(term) in needle for term in explicit):
        return True
    has_exam = any(_normalize(term) in needle for term in EXAM_STAGE_MARKERS)
    has_focus = any(_normalize(term) in needle for term in EXAM_FOCUS_MARKERS)
    return has_exam and has_focus


def _contextual_exact_only_matches(
    query: str,
    needle: str,
    intent: RuntimeIntent,
) -> list[str]:
    embedded = [
        term
        for term in intent.exact_only_phrases
        if _normalize(term) in needle
        and _normalize(term) != needle
        and not is_term_negated(query, term)
    ]
    training_terms = [term for term in embedded if term in TRANSFER_TRAINING_PHRASES]
    if not training_terms:
        return []
    if intent.code == "transfer_practice":
        return (
            training_terms
            if _contains_any(needle, TRANSFER_TRAINING_CONTEXT)
            and not _contains_any(needle, ERROR_BOOK_CONTEXT)
            else []
        )
    if intent.code == "ai_error_book":
        return training_terms if _contains_any(needle, ERROR_BOOK_CONTEXT) else []
    return []


def _contains_any(needle: str, terms: tuple[str, ...]) -> bool:
    return any(_normalize(term) in needle for term in terms)


def _candidate_intent_matches(
    matches: list[IntentMatch],
    *,
    include_weak_alternatives: bool = False,
) -> list[IntentMatch]:
    if not matches:
        return []
    top_confidence = matches[0].confidence
    return [
        match
        for index, match in enumerate(matches)
        if index == 0
        or (match.confidence >= 0.9 and top_confidence - match.confidence <= 0.18)
        or (
            match.confidence >= LOCAL_TRUST_THRESHOLD
            and top_confidence - match.confidence <= AMBIGUOUS_CONFIDENCE_GAP
            and _shares_trusted_interpretation_evidence(matches[0], match)
        )
        or (
            include_weak_alternatives
            and top_confidence - match.confidence <= AMBIGUOUS_CONFIDENCE_GAP
        )
    ][:4]


def _trusted_shared_entry_matches(matches: list[IntentMatch]) -> bool:
    if len(matches) < 2:
        return False
    top = matches[0]
    shared = [
        match
        for match in matches
        if match.confidence >= LOCAL_TRUST_THRESHOLD
        and top.confidence - match.confidence <= AMBIGUOUS_CONFIDENCE_GAP
        and _shares_trusted_interpretation_evidence(top, match)
    ]
    return len(shared) >= 2


def _shares_trusted_interpretation_evidence(
    primary: IntentMatch,
    candidate: IntentMatch,
) -> bool:
    """Only Skill-level complete signals may bypass ordinary ambiguity.

    Identical official or exact-only words such as “规划” and “老师反馈” are
    deliberately ambiguous and must still reach model/fallback arbitration.
    """
    return bool(
        primary.confidence == EXPLORATION_CONFIDENCE
        and candidate.confidence == EXPLORATION_CONFIDENCE
        and any(reason.startswith("自然语言归一化命中：") for reason in primary.reasons)
        and any(reason.startswith("自然语言归一化命中：") for reason in candidate.reasons)
        and frozenset(candidate.matched_terms) == frozenset(primary.matched_terms)
    )


def _has_unique_explicit_primary(
    primary: IntentMatch,
    alternatives: list[IntentMatch],
) -> bool:
    explicit_reason_prefixes = (
        "功能表达命中：",
        "人工短话术精确命中：",
    )
    return (
        primary.confidence >= 0.95
        and any(reason.startswith(explicit_reason_prefixes) for reason in primary.reasons)
        and all(item.confidence < 0.9 for item in alternatives)
    )


def _maximal_terms(terms: list[str]) -> tuple[str, ...]:
    """Keep only terms that are not substrings of another matched term.

    Entry-word comparison should treat “家长省心” and its fragment “家长” as
    the same evidence, otherwise shared entry words would look like
    independent proof on some intents.
    """
    normalized = _unique([_normalize(term) for term in terms])
    return tuple(
        term
        for term in normalized
        if not any(term != other and term in other for other in normalized)
    )


def _shares_single_entry_evidence(selected: list[IntentMatch]) -> bool:
    """True when several intents were hit by the exact same entry words.

    That pattern means one shared entry word (e.g. “AI拍照”) is registered on
    multiple selling points — the user is exploring, not requesting all of
    them at once.
    """
    term_sets = {frozenset(match.matched_terms) for match in selected}
    return len(term_sets) == 1


def _with_negated_concepts(
    understanding: SearchUnderstanding | None,
    negated_names: tuple[str, ...],
) -> SearchUnderstanding | None:
    if understanding is None or not negated_names:
        return understanding
    return understanding.model_copy(
        update={"excluded_concepts": _unique([*understanding.excluded_concepts, *negated_names])}
    )


def _display_concept_name(value: str) -> str:
    return value.rsplit(">", 1)[-1].strip()


def _concept_key(value: str) -> str:
    return _normalize(_display_concept_name(value))


def _has_explicit_multi_marker(value: str) -> bool:
    normalized = _normalize(value)
    return any(
        marker in normalized for marker in ("既要", "还要", "也要", "又要", "同时", "并且", "以及")
    )


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _merge_evidence_matches(
    primary: list[SearchEvidencePointMatch],
    additions: list[SearchEvidencePointMatch],
    active_proof_codes: set[str],
) -> list[SearchEvidencePointMatch]:
    selected: dict[str, SearchEvidencePointMatch] = {}
    for item in [*primary, *additions]:
        if item.proof_point_code not in active_proof_codes:
            continue
        current = selected.get(item.code)
        if current is None or item.weight > current.weight:
            selected[item.code] = item
    return sorted(selected.values(), key=lambda item: item.weight, reverse=True)


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)


def _proof_detail_remainder(query: str, matched_terms: list[str]) -> str:
    remainder = _normalize(query)
    for term in sorted(
        {_normalize(item) for item in matched_terms if _normalize(item)},
        key=len,
        reverse=True,
    ):
        remainder = remainder.replace(term, "")
    for filler in sorted(PROOF_DETAIL_FILLERS, key=len, reverse=True):
        remainder = remainder.replace(_normalize(filler), "")
    return remainder
