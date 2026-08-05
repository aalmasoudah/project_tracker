"""Deterministic development and test provider."""

from typing import cast

from apps.ai_briefings.providers.base import ProviderResult


class FakeBriefingProvider:
    def generate(
        self,
        *,
        evidence: dict[str, object],
        language: str,
        detail_level: str,
        repair: bool = False,
    ) -> ProviderResult:
        del detail_level, repair
        project = cast(dict[str, object], evidence["project"])
        counts = cast(dict[str, object], evidence["counts"])
        records = cast(list[dict[str, object]], evidence["records"])
        project_ref = str(project["source_ref"])
        blocked = [item for item in records if item.get("status") == "blocked"]
        upcoming = [item for item in records if item.get("due_date")]
        if language == "ar":
            summary = (
                f"ملخص تجريبي للمشروع {project['code']} وحالته {project['status']}."
            )
            progress = project["progress_percentage"] or "غير متاحة"
            highlight_text = f"نسبة التقدم الحالية هي {progress}."
            action_text = "راجع عناصر المشروع ذات الأولوية مع الفريق المسؤول."
            gap_text = "هذا موجز تجريبي حتمي للاختبار المحلي."
            risk_text = "توجد مهمة متوقفة تحتاج إلى متابعة."
            upcoming_text = "يوجد عنصر قادم ضمن نافذة الموجز."
        else:
            summary = (
                f"Deterministic test summary for project {project['code']} in "
                f"{project['status']} status."
            )
            highlight_text = (
                "Current progress is "
                f"{project['progress_percentage'] or 'unavailable'}."
            )
            action_text = "Review priority project items with the responsible team."
            gap_text = "This is deterministic fake output for local testing."
            risk_text = "A blocked task requires follow-up."
            upcoming_text = "An item is due within the briefing window."
        risks: list[dict[str, object]] = []
        if blocked:
            risks.append(
                {
                    "text": risk_text,
                    "severity": "high",
                    "citations": [str(blocked[0]["source_ref"])],
                }
            )
        upcoming_items: list[dict[str, object]] = []
        if upcoming:
            upcoming_items.append(
                {
                    "text": upcoming_text,
                    "citations": [str(upcoming[0]["source_ref"])],
                }
            )
        data_gaps = [gap_text]
        if bool(evidence["truncated"]):
            data_gaps.append(
                "تم اختصار الأدلة بسبب حد السجلات."
                if language == "ar"
                else "Evidence was truncated by the record limit."
            )
        data: dict[str, object] = {
            "summary": summary,
            "highlights": [
                {
                    "text": highlight_text,
                    "citations": [project_ref],
                }
            ],
            "risks": risks,
            "upcoming": upcoming_items,
            "recommended_actions": [
                {
                    "text": action_text,
                    "citations": [project_ref],
                }
            ],
            "data_gaps": data_gaps,
        }
        active_tasks = counts.get("active_tasks")
        return ProviderResult(
            data=data,
            provider_code="fake",
            model_code="deterministic",
            input_tokens=active_tasks if isinstance(active_tasks, int) else 0,
            cached_input_tokens=0,
            output_tokens=0,
        )
