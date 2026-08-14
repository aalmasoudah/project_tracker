"""LM Studio strict-schema provider for one project-agent decision."""

from dataclasses import dataclass

from django.conf import settings

from apps.ai_briefings.providers.lm_studio_transport import (
    LMStudioConfigurationError,
    LMStudioResponseError,
    LMStudioTemporaryError,
    LMStudioTransport,
)
from apps.project_agents.prompts import SYSTEM_PROMPT, build_user_prompt
from apps.project_agents.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderResult,
    TemporaryProviderError,
)
from apps.project_agents.schemas import (
    PROPOSAL_ACTIONS,
    READ_TOOLS,
    agent_decision_json_schema,
)


@dataclass(frozen=True, slots=True)
class LMStudioAgentProvider:
    """Generate one bounded project-agent decision through LM Studio."""

    transport: LMStudioTransport

    @classmethod
    def from_settings(cls, *, model_code: str | None = None) -> "LMStudioAgentProvider":
        try:
            configured_model_code = str(settings.LM_STUDIO_MODEL_CODE)
            if model_code is not None and model_code != configured_model_code:
                raise LMStudioConfigurationError(
                    "The requested model does not match the local model."
                )
            transport = LMStudioTransport(
                base_url=str(settings.LM_STUDIO_BASE_URL),
                api_token=str(settings.LM_STUDIO_API_TOKEN),
                model_id=str(settings.LM_STUDIO_MODEL_ID),
                model_code=configured_model_code,
                reasoning_effort=str(settings.LM_STUDIO_REASONING_EFFORT),
                timeout_seconds=int(settings.LM_STUDIO_TIMEOUT_SECONDS),
                max_output_tokens=int(settings.PROJECT_AGENT_MAX_OUTPUT_TOKENS),
                context_length=int(settings.LM_STUDIO_CONTEXT_LENGTH),
                context_token_reserve=int(settings.LM_STUDIO_CONTEXT_TOKEN_RESERVE),
                raw_response_limit=1_000_000,
            )
        except (
            AttributeError,
            TypeError,
            ValueError,
            LMStudioConfigurationError,
        ) as error:
            raise ProviderConfigurationError(
                "LM Studio project-agent configuration is invalid."
            ) from error
        return cls(transport=transport)

    def decide(self, *, context: dict[str, object]) -> ProviderResult:
        observed_refs = context.get("observed_refs", [])
        allowed_citations = (
            frozenset(item for item in observed_refs if isinstance(item, str))
            if isinstance(observed_refs, list)
            else frozenset()
        )
        steps = context.get("steps", [])
        tools_used_value = context.get("tools_used", [])
        tools_used = (
            frozenset(item for item in tools_used_value if isinstance(item, str))
            if isinstance(tools_used_value, list)
            else frozenset()
        )
        if not isinstance(steps, list) or not steps:
            stage = "plan"
        elif len(tools_used) < 2:
            stage = "tool_call"
        else:
            stage = "proposal"
        available_tools = READ_TOOLS - tools_used
        observed_task_ids = frozenset(
            int(ref.removeprefix("task:"))
            for ref in allowed_citations
            if ref.startswith("task:") and ref.removeprefix("task:").isdigit()
        )
        observed_user_ids = frozenset(
            int(ref.removeprefix("team:"))
            for ref in allowed_citations
            if ref.startswith("team:") and ref.removeprefix("team:").isdigit()
        )
        available_actions = {"propose_team_notification"}
        if observed_task_ids:
            available_actions.update(
                {
                    "propose_task_update",
                    "propose_task_comment",
                    "propose_deadline_change",
                }
            )
        if observed_task_ids and observed_user_ids:
            available_actions.add("propose_task_assignment")
        try:
            result = self.transport.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(context),
                schema_name="project_agent_decision",
                schema=agent_decision_json_schema(
                    allowed_citations=allowed_citations,
                    stage=stage,
                    available_tools=available_tools,
                    available_actions=frozenset(available_actions) & PROPOSAL_ACTIONS,
                    observed_task_ids=observed_task_ids,
                    observed_user_ids=observed_user_ids,
                ),
            )
        except LMStudioTemporaryError as error:
            raise TemporaryProviderError(
                str(error),
                retry_after_seconds=error.retry_after_seconds,
            ) from error
        except LMStudioResponseError as error:
            raise ProviderResponseError(
                "LM Studio returned an unusable agent response."
            ) from error
        return ProviderResult(
            data=result.data,
            provider_code="lm_studio",
            model_code=result.model_code,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            output_tokens=result.output_tokens,
        )
