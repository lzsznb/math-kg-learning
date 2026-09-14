import os
import json
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .tools import knowledge_graph_tools

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

agent_llm = ChatOpenAI(
    model="deepseek-v4-pro",
    openai_api_key=DEEPSEEK_API_KEY,
    openai_api_base="https://api.deepseek.com",
    temperature=0.7,
    max_tokens=2048,
    extra_body={"thinking": {"type": "disabled"}},
).bind_tools(knowledge_graph_tools)

AGENT_SYSTEM_PROMPT = (
    "你是一个主动型高中数学智能学习助手。你对每个用户的职责是：\n"
    "1. 分析用户知识状态（已会、薄弱、未学）\n"
    "2. 诊断薄弱点和缺失的前置知识\n"
    "3. 给出个性化的每日学习建议和推荐学习路径\n\n"
    "核心能力——自适应诊断流程（当用户问及学习状况或首次交互时）：\n"
    "- 先调用 analyze_user_model_tool（传入用户的 progress JSON）获取完整分析\n"
    "- 根据返回的 module_mastery（模块掌握度）、weak_points（薄弱点）、recommendations（推荐顺序）\n"
    "- 给出结构化的回答：模块掌握概况 → 薄弱点 → 缺失前置 → 下一步学习建议\n\n"
    "工作流程（必须严格遵守）：\n"
    "1. 判断需要什么信息，调用一个工具\n"
    "2. 工具返回结果后，立即基于结果用自然语言回答\n"
    "3. 不得再次调用任何工具——即使结果不完整也直接回答\n\n"
    "绝对禁止：\n"
    "- 禁止连续调用多个工具\n"
    "- 禁止在已经拿到工具结果后还继续调用工具\n"
    "- 禁止重复调用同一个工具\n\n"
    "其他工具说明：\n"
    "- get_community_analysis / explain_node_community：社区分析\n"
    "- get_centrality_analysis：中心性分析\n"
    "- update_edge_weight_tool / get_adaptive_path_tool：动态加权边\n"
    "- 用户觉得某个前置知识难时，用 update_edge_weight_tool 增大权重\n"
    "- 使用 get_adaptive_path_tool 获取基于当前权重的个性化学习路径\n\n"
    "最终回答中引用知识点时，用双引号括起来。\n"
    "回答要简洁实用，适合高中生的理解水平。\n"
    "注意：请使用中文回答。\n"
)

def _clean_state_messages(state: dict) -> dict:
    for msg in state.get("messages", []):
        if hasattr(msg, "additional_kwargs"):
            msg.additional_kwargs.pop("reasoning_content", None)
            getattr(msg, "response_metadata", {}).pop("reasoning_content", None)
    return state

def _clean_output_message(msg):
    if hasattr(msg, "additional_kwargs"):
        msg.additional_kwargs.pop("reasoning_content", None)
        getattr(msg, "response_metadata", {}).pop("reasoning_content", None)
    return msg

agent_memory = MemorySaver()

agent_executor = create_react_agent(
    model=agent_llm,
    tools=knowledge_graph_tools,
    prompt=AGENT_SYSTEM_PROMPT,
    checkpointer=agent_memory,
    pre_model_hook=_clean_state_messages,
    post_model_hook=_clean_output_message,
)
