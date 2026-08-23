"""The 11-Step Agent Execution Loop Orchestrator with Process Sandbox and Phase 3 Registry."""

from agents.base import AgentState, BaseAgent
from agents.planner import TaskPlanner
from agents.verifier import OutputVerifier
from config.schema import ModelTier, PermissionLevel
from conversation.personality import PersonaGovernor
from core.context import SessionContext
from core.exceptions import (
    HumanConfirmationRequiredError,
    MalformedToolRequestError,
    ModelRoutingError,
    OutputValidationError,
    PermissionDeniedError,
    ProviderUnavailableError,
    SandboxViolationError,
    SecurityError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    UnknownParameterError,
    VerificationFailureError,
)
from memory.long_term import SensitivityLevel
from memory.manager import MemoryManager
from model_routing.router import ModelRouter
from model_routing.schemas import (
    ChatMessage,
    MessageRole,
    ModelRequest,
    ModelResponse,
)
from sandbox.process_executor import ProcessSandboxExecutor
from security.audit_logger import AuditLogger
from security.permissions import ApprovalCard, ApprovalToken, PermissionDecision, PermissionEngine
from tools.registry import ToolRegistry


class AgentLoop(BaseAgent):
    """Deterministic 11-step agent execution pipeline with strict capability validation."""

    def __init__(
        self,
        model_router: ModelRouter,
        permission_engine: PermissionEngine,
        tool_registry: ToolRegistry,
        memory_manager: MemoryManager,
        audit_logger: AuditLogger,
        task_planner: TaskPlanner | None = None,
        output_verifier: OutputVerifier | None = None,
        sandbox_executor: ProcessSandboxExecutor | None = None,
    ) -> None:
        self.router = model_router
        self.permission_engine = permission_engine
        self.tool_registry = tool_registry
        self.memory = memory_manager
        self.audit = audit_logger
        self.planner = task_planner or TaskPlanner()
        self.verifier = output_verifier or OutputVerifier()
        self.sandbox_executor = sandbox_executor or ProcessSandboxExecutor()
        self.state = AgentState.IDLE

    async def process_turn(
        self,
        user_query: str,
        context: SessionContext,
        approval_token: ApprovalToken | None = None,
        approval_card: ApprovalCard | None = None,
        proactive_advisory: str | None = None,
    ) -> ModelResponse:
        """Execute complete 11-step turn pipeline with fail-closed error handling."""
        context.touch()
        correlation_id_str = str(context.correlation_id)
        session_id_str = str(context.session_id)

        # 1. RECEIVE & 2. NORMALIZE
        self.state = AgentState.PARSING_INTENT
        normalized_query = user_query.strip()
        if not normalized_query:
            return ModelResponse(
                model_name="jarvis-core",
                provider_name="system",
                content="Please provide a query or instruction.",
            )

        # 3. CONTEXT ASSEMBLY & MEMORY RETRIEVAL (With Tier & Sensitivity Gating)
        system_prompt = PersonaGovernor.construct_system_prompt(context)
        user_msg = ChatMessage(role=MessageRole.USER, content=normalized_query)
        self.memory.add_working_message(user_msg)

        proactive_context_str = ""
        effective_advisory = proactive_advisory or getattr(context, "proactive_advisory", None)
        if effective_advisory:
            proactive_context_str = f"\n{effective_advisory}\n"

        memory_context_str = ""
        # Access control: LOCKED tier cannot access persistent memory
        if context.permission_level != PermissionLevel.LOCKED:
            max_sens = (
                SensitivityLevel.SENSITIVE
                if context.permission_level == PermissionLevel.SENSITIVE
                else SensitivityLevel.NORMAL
            )
            relevant_memories = await self.memory.recall(
                normalized_query,
                max_sensitivity=max_sens,
                session_id=session_id_str,
                limit=3,
            )
            if relevant_memories:
                memory_lines = "\n".join(
                    f"- [{m.category.value}] {m.content}" for m in relevant_memories
                )
                memory_context_str = (
                    f"\n<untrusted_memory_data source=\"persistent_memory\">\n"
                    f"{memory_lines}\n"
                    f"</untrusted_memory_data>\n"
                )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt + proactive_context_str + memory_context_str),
            *self.memory.get_working_messages(),
        ]

        # 4. INTENT & 5. PLAN (Model Routing with Tool Capability Schemas)
        self.state = AgentState.PLANNING
        tool_schemas = self.tool_registry.get_tool_schemas_for_model()
        model_request = ModelRequest(
            messages=messages,
            tier=ModelTier.FAST.value,
            tools=tool_schemas,
        )

        try:
            initial_response = await self.router.route(model_request, tier=ModelTier.FAST)
        except (ProviderUnavailableError, ModelRoutingError) as err:
            self.state = AgentState.ERROR
            self.audit.log(
                actor_id=context.device_id,
                session_id=session_id_str,
                correlation_id=correlation_id_str,
                event_type="PROVIDER_ERROR",
                action_type="MODEL_ROUTING",
                risk_level="NORMAL",
                target_resource="model_router",
                parameters={"error": str(err)},
                decision="FAIL_CLOSED",
            )
            return ModelResponse(
                model_name="jarvis-core",
                provider_name="system",
                content=f"I apologize, {context.get_salutation()}, but the requested model provider is unavailable. Failing closed safely.",
            )

        # 7. TOOL DECISION: Check if model proposed tool calls
        if not initial_response.tool_calls:
            self.state = AgentState.COMPLETED
            assistant_msg = ChatMessage(role=MessageRole.ASSISTANT, content=initial_response.content)
            self.memory.add_working_message(assistant_msg)
            self.audit.log(
                actor_id=context.device_id,
                session_id=session_id_str,
                correlation_id=correlation_id_str,
                event_type="CONVERSATION_TURN",
                action_type="DIALOGUE",
                risk_level="NORMAL",
                target_resource="in_memory_dialogue",
                parameters={"query_length": len(normalized_query)},
                decision="COMPLETED",
            )
            return initial_response

        # Process Tool Calls
        for tool_call in initial_response.tool_calls:
            self.audit.log(
                actor_id=context.device_id,
                session_id=session_id_str,
                correlation_id=correlation_id_str,
                event_type="TOOL_REQUESTED",
                action_type=tool_call.tool_name,
                risk_level="NORMAL",
                target_resource=tool_call.tool_name,
                parameters=tool_call.arguments,
                decision="VALIDATING",
            )

            tool = self.tool_registry.get_tool(tool_call.tool_name)
            if not tool:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="TOOL_DENIED",
                    action_type="TOOL_LOOKUP",
                    risk_level="NORMAL",
                    target_resource=tool_call.tool_name,
                    parameters={},
                    decision="TOOL_NOT_FOUND",
                )
                raise ToolNotFoundError(f"Requested tool '{tool_call.tool_name}' is not registered.")

            # Validate input arguments strictly
            try:
                self.tool_registry.validate_tool_arguments(tool_call.tool_name, tool_call.arguments)
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="TOOL_VALIDATED",
                    action_type=tool.definition.name,
                    risk_level=tool.definition.risk_level.value,
                    target_resource=tool.definition.tool_id,
                    parameters=tool_call.arguments,
                    decision="SCHEMA_VALID",
                )
            except (MalformedToolRequestError, UnknownParameterError) as err:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="TOOL_DENIED",
                    action_type=tool.definition.name,
                    risk_level=tool.definition.risk_level.value,
                    target_resource=tool.definition.tool_id,
                    parameters=tool_call.arguments,
                    decision=f"MALFORMED_ARGS:{err}",
                )
                raise err

            target_res = str(tool_call.arguments.get("path", tool_call.arguments.get("target", "sandbox/virtual")))

            # 6. SAFETY & PERMISSION CHECK
            decision = self.permission_engine.evaluate(
                session=context,
                action_name=tool.definition.name,
                required_level=tool.definition.permission_tier,
                action_category=tool.definition.action_category,
                target_resource=target_res,
                parameters=tool_call.arguments,
                approval_token=approval_token,
                card=approval_card,
                tool_id=tool.definition.tool_id,
            )

            if decision == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION:
                self.state = AgentState.AWAITING_CONFIRMATION
                card = ApprovalCard.create(
                    action_name=tool.definition.name,
                    action_category=tool.definition.action_category,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    risk_summary=f"Executing {tool.definition.name} ({tool.definition.risk_level.value} risk) requires human confirmation.",
                    tool_id=tool.definition.tool_id,
                    tool_version=tool.definition.version,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                )
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="APPROVAL_REQUIRED",
                    action_type=tool.definition.name,
                    risk_level=tool.definition.risk_level.value,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision="CARD_ISSUED",
                )
                raise HumanConfirmationRequiredError(tool.definition.name, card)

            if decision != PermissionDecision.AUTHORIZED:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="TOOL_DENIED",
                    action_type=tool.definition.name,
                    risk_level=tool.definition.risk_level.value,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision=f"DENIED:{decision.value}",
                )
                raise PermissionDeniedError(f"Permission denied for tool '{tool.definition.name}': {decision.value}")

            # If approval token was provided, consume it to prevent replay
            if approval_token:
                approval_token.consume()
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="APPROVAL_GRANTED",
                    action_type=tool.definition.name,
                    risk_level=tool.definition.risk_level.value,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision="TOKEN_CONSUMED",
                    approval_token_id=str(approval_token.token_id),
                )

            # 8. EXECUTION (Within Process Sandbox)
            self.state = AgentState.EXECUTING_TOOL
            self.audit.log(
                actor_id=context.device_id,
                session_id=session_id_str,
                correlation_id=correlation_id_str,
                event_type="TOOL_STARTED",
                action_type=tool.definition.name,
                risk_level=tool.definition.risk_level.value,
                target_resource=target_res,
                parameters=tool_call.arguments,
                decision="RUNNING",
            )

            try:
                tool_result = await self.sandbox_executor.execute_tool(tool, tool_call.arguments, context)
            except ToolTimeoutError as t_err:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="TOOL_TIMEOUT",
                    action_type=tool.definition.name,
                    risk_level=tool.definition.risk_level.value,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision="TIMED_OUT",
                )
                raise t_err
            except (SandboxViolationError, OutputValidationError) as sec_err:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="TOOL_FAILED",
                    action_type=tool.definition.name,
                    risk_level="HIGH",
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision=f"BLOCKED:{sec_err}",
                )
                raise sec_err

            # 9. OUTPUT VALIDATION & VERIFICATION
            self.state = AgentState.VERIFYING_OUTPUT
            try:
                verified_output = self.verifier.verify_tool_result(tool_result, tool.definition)
            except OutputValidationError as o_err:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    session_id=session_id_str,
                    correlation_id=correlation_id_str,
                    event_type="OUTPUT_VALIDATION_FAILED",
                    action_type=tool.definition.name,
                    risk_level="HIGH",
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision=str(o_err),
                )
                raise o_err

            self.audit.log(
                actor_id=context.device_id,
                session_id=session_id_str,
                correlation_id=correlation_id_str,
                event_type="TOOL_COMPLETED",
                action_type=tool.definition.name,
                risk_level=tool.definition.risk_level.value,
                target_resource=target_res,
                parameters={"execution_time_ms": tool_result.execution_time_ms},
                decision="SUCCESS",
            )

            messages.append(
                ChatMessage(
                    role=MessageRole.TOOL,
                    content=verified_output,
                    tool_call_id=tool_call.call_id,
                )
            )

        # 10. RESPONSE SYNTHESIS & 11. AUDIT
        self.state = AgentState.SYNTHESIZING_RESPONSE
        synthesis_req = ModelRequest(messages=messages, tier=ModelTier.REASONING.value)
        final_response = await self.router.route(synthesis_req, tier=ModelTier.REASONING)

        self.state = AgentState.COMPLETED
        assistant_msg = ChatMessage(role=MessageRole.ASSISTANT, content=final_response.content)
        self.memory.add_working_message(assistant_msg)

        self.audit.log(
            actor_id=context.device_id,
            session_id=session_id_str,
            correlation_id=correlation_id_str,
            event_type="AGENT_EXECUTION_COMPLETED",
            action_type="TOOL_RUN",
            risk_level="NORMAL",
            target_resource="sandbox",
            parameters={"tool_calls_count": len(initial_response.tool_calls)},
            decision="SUCCESS",
            approval_token_id=str(approval_token.token_id) if approval_token else None,
        )

        return final_response
