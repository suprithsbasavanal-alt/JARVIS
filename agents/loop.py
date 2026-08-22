"""The 11-Step Agent Execution Loop Orchestrator."""

from agents.base import AgentState, BaseAgent
from agents.planner import TaskPlanner
from agents.verifier import OutputVerifier
from config.schema import ModelTier
from conversation.personality import PersonaGovernor
from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from memory.manager import MemoryManager
from model_routing.router import ModelRouter
from model_routing.schemas import (
    ChatMessage,
    MessageRole,
    ModelRequest,
    ModelResponse,
)
from security.audit_logger import AuditLogger
from security.permissions import ApprovalCard, ApprovalToken, PermissionDecision, PermissionEngine
from tools.registry import ToolRegistry


class AgentLoop(BaseAgent):
    """Coordinates request understanding, safety checks, tool execution, and response synthesis."""

    def __init__(
        self,
        model_router: ModelRouter,
        permission_engine: PermissionEngine,
        tool_registry: ToolRegistry,
        memory_manager: MemoryManager,
        audit_logger: AuditLogger,
        task_planner: TaskPlanner | None = None,
        output_verifier: OutputVerifier | None = None,
    ) -> None:
        self.router = model_router
        self.permission_engine = permission_engine
        self.tool_registry = tool_registry
        self.memory = memory_manager
        self.audit = audit_logger
        self.planner = task_planner or TaskPlanner()
        self.verifier = output_verifier or OutputVerifier()
        self.state = AgentState.IDLE

    async def process_turn(
        self,
        user_query: str,
        context: SessionContext,
        approval_token: ApprovalToken | None = None,
        approval_card: ApprovalCard | None = None,
    ) -> ModelResponse:
        """Execute complete 11-step turn pipeline."""
        self.state = AgentState.PARSING_INTENT
        context.touch()

        # Step 1 & 2: User input ingestion & salutation derivation
        system_prompt = PersonaGovernor.construct_system_prompt(context)
        user_msg = ChatMessage(role=MessageRole.USER, content=user_query)
        self.memory.add_working_message(user_msg)

        # Step 3: Context assembly with memory recall
        relevant_memories = await self.memory.recall(user_query, limit=3)
        memory_context_str = ""
        if relevant_memories:
            memory_context_str = "\nRelevant Persistent Memories:\n" + "\n".join(
                f"- [{m.category.value}] {m.content}" for m in relevant_memories
            )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt + memory_context_str),
            *self.memory.get_working_messages(),
        ]

        # Step 4 & 5: Model request with tool schemas
        tool_schemas = self.tool_registry.get_tool_schemas_for_model()
        model_request = ModelRequest(
            messages=messages,
            tier=ModelTier.FAST.value,
            tools=tool_schemas,
        )

        self.state = AgentState.PLANNING
        initial_response = await self.router.route(model_request, tier=ModelTier.FAST)

        # If model did not request tool calls, synthesize and return directly
        if not initial_response.tool_calls:
            self.state = AgentState.COMPLETED
            assistant_msg = ChatMessage(role=MessageRole.ASSISTANT, content=initial_response.content)
            self.memory.add_working_message(assistant_msg)
            self.audit.log(
                actor_id=context.device_id,
                action_type="CONVERSATION_TURN",
                permission_level=context.permission_level.value,
                target_resource="in_memory_dialogue",
                parameters={"query_length": len(user_query)},
                decision="COMPLETED",
            )
            return initial_response

        # Process Tool Calls
        for tool_call in initial_response.tool_calls:
            tool = self.tool_registry.get_tool(tool_call.tool_name)
            if not tool:
                continue

            target_res = str(tool_call.arguments.get("path", tool_call.arguments.get("target", "sandbox/virtual")))

            # Step 6: Security & Permission Check
            decision = self.permission_engine.evaluate(
                session=context,
                action_name=tool.metadata.name,
                required_level=tool.metadata.required_permission_level,
                action_category=tool.metadata.action_category,
                target_resource=target_res,
                parameters=tool_call.arguments,
                approval_token=approval_token,
                card=approval_card,
            )

            # Step 7: Handle Confirmation or Denial
            if decision == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION:
                self.state = AgentState.AWAITING_CONFIRMATION
                card = ApprovalCard.create(
                    action_name=tool.metadata.name,
                    action_category=tool.metadata.action_category,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    risk_summary=f"Executing {tool.metadata.name} requires owner authorization.",
                )
                self.audit.log(
                    actor_id=context.device_id,
                    action_type=tool.metadata.name,
                    permission_level=context.permission_level.value,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision="REQUIRES_CONFIRMATION",
                )
                raise HumanConfirmationRequiredError(tool.metadata.name, str(card.card_id))

            if decision != PermissionDecision.AUTHORIZED:
                self.state = AgentState.ERROR
                self.audit.log(
                    actor_id=context.device_id,
                    action_type=tool.metadata.name,
                    permission_level=context.permission_level.value,
                    target_resource=target_res,
                    parameters=tool_call.arguments,
                    decision=f"DENIED:{decision.value}",
                )
                raise PermissionDeniedError(f"Permission denied for tool '{tool.metadata.name}': {decision.value}")

            # Step 8: Sandboxed Tool Execution
            self.state = AgentState.EXECUTING_TOOL
            tool_result = await tool.execute(tool_call.arguments, context)

            # Step 9 & 10: Verification & Sanitization
            self.state = AgentState.VERIFYING_OUTPUT
            verified_output = self.verifier.verify_tool_result(tool_result)

            # Add tool output to context and synthesize final response
            messages.append(
                ChatMessage(
                    role=MessageRole.TOOL,
                    content=verified_output,
                    tool_call_id=tool_call.call_id,
                )
            )

        # Step 11: Final Response Synthesis & Audit
        self.state = AgentState.SYNTHESIZING_RESPONSE
        synthesis_req = ModelRequest(messages=messages, tier=ModelTier.REASONING.value)
        final_response = await self.router.route(synthesis_req, tier=ModelTier.REASONING)

        self.state = AgentState.COMPLETED
        assistant_msg = ChatMessage(role=MessageRole.ASSISTANT, content=final_response.content)
        self.memory.add_working_message(assistant_msg)

        self.audit.log(
            actor_id=context.device_id,
            action_type="AGENT_LOOP_EXECUTION",
            permission_level=context.permission_level.value,
            target_resource="tool_execution",
            parameters={"tools_count": len(initial_response.tool_calls)},
            decision="COMPLETED",
            approval_token_id=str(approval_token.token_id) if approval_token else None,
        )

        return final_response
