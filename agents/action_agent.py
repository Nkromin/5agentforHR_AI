"""Action Agent - Executes tools for HR actions ONLY."""
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from agents.state import AgentState
from tools import TOOLS
import re


ACTION_AGENT_PROMPT = """You are an HR Action Assistant. You ONLY execute specific HR tools when explicitly requested.

AVAILABLE TOOLS:
1. create_hr_ticket(issue: str) - Creates an HR support ticket
2. check_leave_balance(employee_id: str) - Checks remaining leave days

STRICT RULES:
1. You can ONLY use the tools listed above
2. Do NOT answer policy questions - those are not your job
3. Do NOT create tickets unless explicitly asked to "create a ticket" or "raise a ticket"
4. Do NOT hallucinate tool results

TO USE A TOOL, respond in this EXACT format:
TOOL: tool_name
PARAM: parameter_value

EXAMPLES:
User: "Check my leave balance for EMP001"
Response:
TOOL: check_leave_balance
PARAM: EMP001

User: "Create a ticket for laptop not working"
Response:
TOOL: create_hr_ticket
PARAM: laptop not working

User: "Check my leave balance" (no employee ID provided)
Response: I need your employee ID to check your leave balance. Please provide it (e.g., EMP001).

User: "What is the leave policy?"
Response: I can only execute HR actions like checking leave balance or creating tickets. For policy questions, please ask separately.

Current request: {query}

Your response:"""


class ActionAgent:
    """Action agent that executes HR tools ONLY when explicitly requested."""

    def __init__(self, llm: ChatGroq):
        """
        Initialize with shared LLM instance.
        Tools are isolated to this agent only.

        Args:
            llm: Shared Groq LLM instance
        """
        self.llm = llm
        # Tools are ONLY accessible within this agent
        self.available_tools = TOOLS

    def _parse_tool_call(self, response_text: str) -> tuple:
        """
        Parse tool call from LLM response.

        Args:
            response_text: Raw LLM response

        Returns:
            Tuple of (tool_name, parameter) or (None, None)
        """
        tool_match = re.search(r'TOOL:\s*(\w+)', response_text, re.IGNORECASE)
        param_match = re.search(r'PARAM:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE)

        if tool_match and param_match:
            tool_name = tool_match.group(1).strip().lower()
            param = param_match.group(1).strip()
            return tool_name, param

        return None, None

    def _execute_tool(self, tool_name: str, param: str, debug_log: list) -> dict:
        """
        Execute a tool safely.

        Args:
            tool_name: Name of the tool
            param: Parameter for the tool
            debug_log: Debug log to append to

        Returns:
            Tool execution result
        """
        debug_log.append(f"[ACTION AGENT] Executing tool: {tool_name} with param: {param}")

        if tool_name in self.available_tools:
            try:
                result = self.available_tools[tool_name](param)
                debug_log.append(f"[ACTION AGENT] Tool result: {result}")
                return {
                    "success": True,
                    "tool": tool_name,
                    "parameter": param,
                    "result": result
                }
            except Exception as e:
                debug_log.append(f"[ACTION AGENT] Tool error: {str(e)}")
                return {
                    "success": False,
                    "tool": tool_name,
                    "parameter": param,
                    "error": str(e)
                }
        else:
            debug_log.append(f"[ACTION AGENT] Unknown tool: {tool_name}")
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name}"
            }

    def run(self, state: AgentState) -> AgentState:
        """
        Execute tools based on user request.
        Tools are isolated to this agent only.

        Args:
            state: Current agent state

        Returns:
            Updated state with action response
        """
        user_input = state["user_input"]
        debug_log = state.get("debug_log", []) or []

        debug_log.append(f"[ACTION AGENT] Processing: {user_input}")

        # Get tool decision from LLM
        prompt = ACTION_AGENT_PROMPT.format(query=user_input)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        debug_log.append(f"[ACTION AGENT] LLM response: {response_text}")

        # Parse tool call
        tool_name, param = self._parse_tool_call(response_text)

        if tool_name and param:
            # Execute the tool
            tool_result = self._execute_tool(tool_name, param, debug_log)

            if tool_result["success"]:
                state["tool_calls"] = [tool_result]
                state["action_response"] = tool_result["result"]["message"]
            else:
                state["tool_calls"] = [tool_result]
                state["action_response"] = f"Error: {tool_result.get('error', 'Unknown error')}"
        else:
            # No valid tool call - return the LLM's response (might be asking for clarification)
            debug_log.append("[ACTION AGENT] No tool call detected")
            state["tool_calls"] = []
            state["action_response"] = response_text

        state["debug_log"] = debug_log
        return state

        return state

