"""Deterministic agent used only for development and automated proof."""

from dataclasses import dataclass
from typing import cast

from apps.project_agents.providers.base import ProviderResult
from apps.project_agents.schemas import empty_payload


@dataclass(frozen=True, slots=True)
class FakeAgentProvider:
    model_code: str

    def decide(self, *, context: dict[str, object]) -> ProviderResult:
        language = str(context.get("language", "ar"))
        steps = cast(list[dict[str, object]], context.get("steps", []))
        tools_used = cast(list[str], context.get("tools_used", []))
        observed_refs = cast(list[str], context.get("observed_refs", []))
        has_plan = any(item.get("type") == "plan" for item in steps)
        has_proposal = any(item.get("type") == "proposal" for item in steps)
        payload = empty_payload()
        if not has_plan:
            data = self._decision(
                kind="plan",
                summary=(
                    "سأحلل حالة المشروع ومصادر التأخير ثم أعد خطة تعافٍ قابلة للمراجعة."
                    if language == "ar"
                    else (
                        "I will inspect project health and delay sources, then "
                        "prepare a reviewable recovery plan."
                    )
                ),
                plan_steps=(
                    [
                        "مراجعة ذاكرة التشغيل السابقة",
                        "فحص حالة المشروع",
                        "تحليل المخاطر",
                        "إعداد مقترح",
                        "التحقق النهائي",
                    ]
                    if language == "ar"
                    else [
                        "Review prior memory",
                        "Inspect project state",
                        "Analyze risks",
                        "Prepare proposal",
                        "Verify final state",
                    ]
                ),
                payload=payload,
            )
        elif not tools_used:
            tool = (
                "recall_reviewed_agent_runs"
                if bool(context.get("reviewed_memory_available"))
                else "get_project_snapshot"
            )
            data = self._decision(kind="tool_call", tool_code=tool, payload=payload)
        elif len(set(tools_used)) == 1:
            first = tools_used[0]
            if first == "recall_reviewed_agent_runs":
                tool = "get_project_snapshot"
            else:
                snapshot = self._tool_result(steps, "get_project_snapshot")
                counts = self._first_data(snapshot)
                overdue = counts.get("overdue_tasks", 0)
                blocked = counts.get("blocked_tasks", 0)
                tool = (
                    "list_overdue_and_blocked_tasks"
                    if (isinstance(overdue, int) and overdue > 0)
                    or (isinstance(blocked, int) and blocked > 0)
                    else "get_upcoming_milestones"
                )
            data = self._decision(kind="tool_call", tool_code=tool, payload=payload)
        elif not has_proposal:
            task = self._first_task(steps)
            citation = (
                f"task:{task['task_id']}"
                if task is not None
                else observed_refs[0]
                if observed_refs
                else ""
            )
            if task is not None:
                payload["task_id"] = task["task_id"]
                payload["comment"] = (
                    "مقترح متابعة من وكيل التعافي: يرجى تحديث العائق والخطوة "
                    "التالية والموعد المتوقع."
                    if language == "ar"
                    else (
                        "Recovery-agent follow-up: please update the blocker, "
                        "next step, and expected date."
                    )
                )
                action = "propose_task_comment"
            else:
                payload["task_id"] = None
                payload["notification_topic"] = "project_recovery_follow_up"
                action = "propose_team_notification"
            data = self._decision(
                kind="proposal",
                summary=(
                    "تم إعداد مقترح متابعة بشري قبل أي تغيير."
                    if language == "ar"
                    else (
                        "A human-reviewed follow-up proposal is ready before any "
                        "change."
                    )
                ),
                action_code=action,
                payload=payload,
                citations=[citation] if citation else [],
                findings=[
                    {
                        "text": "تم تحليل حالة المشروع من الأدلة المتاحة."
                        if language == "ar"
                        else "Project state was analyzed from the available evidence.",
                        "citations": [citation],
                    }
                ]
                if citation
                else [],
                recommendations=[
                    {
                        "text": "راجع المقترح قبل التنفيذ."
                        if language == "ar"
                        else "Review the proposal before execution.",
                        "citations": [citation],
                    }
                ]
                if citation
                else [],
            )
        else:
            citation = observed_refs[0] if observed_refs else ""
            data = self._decision(
                kind="final",
                summary=(
                    "اكتمل التحليل وتوقف التشغيل بانتظار القرار البشري على المقترح."
                    if language == "ar"
                    else (
                        "Analysis is complete and paused for the human proposal "
                        "decision."
                    )
                ),
                payload=payload,
                findings=[
                    {
                        "text": "تم تحليل حالة المشروع من الأدلة المتاحة."
                        if language == "ar"
                        else "Project state was analyzed from the available evidence.",
                        "citations": [citation],
                    }
                ]
                if citation
                else [],
                recommendations=[
                    {
                        "text": "راجع المقترح قبل التنفيذ."
                        if language == "ar"
                        else "Review the proposal before execution.",
                        "citations": [citation],
                    }
                ]
                if citation
                else [],
            )
        return ProviderResult(
            data=data,
            provider_code="fake",
            model_code=self.model_code,
            input_tokens=10,
            cached_input_tokens=0,
            output_tokens=10,
        )

    @staticmethod
    def _decision(
        *,
        kind: str,
        payload: dict[str, object],
        summary: str = "",
        plan_steps: list[str] | None = None,
        tool_code: str | None = None,
        action_code: str | None = None,
        citations: list[str] | None = None,
        findings: list[dict[str, object]] | None = None,
        recommendations: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {
            "kind": kind,
            "summary": summary,
            "plan_steps": plan_steps or [],
            "tool_code": tool_code,
            "arguments": {},
            "action_code": action_code,
            "payload": payload,
            "citations": citations or [],
            "findings": findings or [],
            "recommendations": recommendations or [],
        }

    @staticmethod
    def _tool_result(
        steps: list[dict[str, object]], tool_code: str
    ) -> dict[str, object]:
        for step in reversed(steps):
            if step.get("type") == "observation" and step.get("tool_code") == tool_code:
                result = step.get("result")
                if isinstance(result, dict):
                    return cast(dict[str, object], result)
        return {}

    @staticmethod
    def _first_data(result: dict[str, object]) -> dict[str, object]:
        items = result.get("items", [])
        if isinstance(items, list) and items and isinstance(items[0], dict):
            data = items[0].get("data")
            if isinstance(data, dict):
                return cast(dict[str, object], data)
        return {}

    def _first_task(self, steps: list[dict[str, object]]) -> dict[str, object] | None:
        result = self._tool_result(steps, "list_overdue_and_blocked_tasks")
        data = self._first_data(result)
        return data if isinstance(data.get("task_id"), int) else None
