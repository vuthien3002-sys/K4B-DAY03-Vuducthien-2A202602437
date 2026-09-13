"""
🍱 FOOD ORDERING AGENT - STREAMLIT UI
Giao diện trực quan cho Day 03 Lab.

Chạy:
    streamlit run src/ui.py
"""

import json
import os
import sys
from typing import Any, Dict, List, Tuple

import streamlit as st

# Cho phép import các module cùng thư mục src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from mcp_server import MCPAcademicServer
from providers import get_llm_provider
from prompts import MAX_ITERATIONS


# ==============================================================================
# SYSTEM PROMPT CHO FOOD ORDERING AGENT
# ==============================================================================

REACT_AGENT_SYSTEM_PROMPT = """
Bạn là Trợ lý Quản lý Đơn giao đồ ăn.

Bạn có 2 công cụ:
1. query_menu
   - Tra cứu món ăn theo tên, mã món hoặc loại món.
   - Ví dụ:
     {"keyword": "Cơm gà"}
     {"keyword": "Món chính"}
     {"keyword": "Đồ uống"}

2. create_order
   - Tạo đơn hàng.
   - Ví dụ:
     {
       "items": [
         {"item_id": "FOOD001", "quantity": 1}
       ],
       "order_note": "Không cay"
     }

Quy tắc:
- Nếu người dùng chỉ hỏi thông tin món ăn: dùng query_menu rồi trả lời.
- Nếu người dùng muốn đặt món:
  + Tra cứu món trước để lấy item_id, giá và tình trạng còn hàng.
  + Chỉ gọi create_order khi món tồn tại và còn hàng.
- Nếu NOT_FOUND: không bịa thông tin và không tạo đơn.
- Nếu món hết hàng: không tạo đơn.
- Nếu create_order SUCCESS: trả mã đơn, món, số lượng và tổng tiền.
- Với yêu cầu nhiều bước như "một phần cơm + một đồ uống dưới ngân sách":
  + Có thể gọi query_menu nhiều lần.
  + So sánh giá và tình trạng còn hàng.
  + Sau đó gọi create_order với tất cả món phù hợp.
- Không dùng các tool học vụ cũ như academic_query hoặc schedule_appointment.
"""


# ==============================================================================
# CẤU HÌNH UI
# ==============================================================================

st.set_page_config(
    page_title="Food Ordering Agent",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.3rem;
            padding-bottom: 2rem;
        }

        .hero {
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #fff7ed, #ffedd5);
            border: 1px solid #fed7aa;
            margin-bottom: 1rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 2rem;
        }

        .hero p {
            margin: .35rem 0 0 0;
            opacity: .8;
        }

        .status-card {
            padding: .85rem 1rem;
            border-radius: 14px;
            border: 1px solid rgba(128,128,128,.25);
            background: rgba(255,255,255,.03);
            min-height: 92px;
        }

        .menu-card {
            padding: 1rem;
            border-radius: 16px;
            border: 1px solid rgba(128,128,128,.22);
            margin-bottom: .6rem;
        }

        .tool-chip {
            display: inline-block;
            padding: .18rem .55rem;
            border-radius: 999px;
            background: rgba(255, 145, 0, .12);
            margin-right: .35rem;
            font-size: .82rem;
        }

        .small-muted {
            opacity: .7;
            font-size: .9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# KHỞI TẠO BACKEND
# ==============================================================================

@st.cache_resource
def init_backend():
    provider = get_llm_provider()
    server = MCPAcademicServer()
    return provider, server


provider, mcp_server = init_backend()


# ==============================================================================
# HÀM HỖ TRỢ
# ==============================================================================

def unwrap_mcp_result(mcp_result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(mcp_result, dict):
        return {}

    result = mcp_result.get("result", {})
    return result if isinstance(result, dict) else {}


def run_agent(
    user_query: str,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    ReAct Loop cho UI:
    Thought -> Action -> Observation -> ... -> Final Answer
    """

    tools_list = mcp_server.list_tools()

    original_query = user_query
    current_query = user_query

    trace: List[Dict[str, Any]] = []

    for step in range(1, MAX_ITERATIONS + 1):
        llm_response = provider.generate_with_tools(
            current_query,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT,
        )

        thought = llm_response.get("thought", "Đang suy luận...")
        response_type = llm_response.get("type")

        # ----------------------------------------------------------------------
        # FINAL ANSWER
        # ----------------------------------------------------------------------
        if response_type == "text":
            final_answer = llm_response.get("content", "")

            trace.append(
                {
                    "step": step,
                    "type": "FINAL_ANSWER",
                    "thought": thought,
                    "content": final_answer,
                }
            )

            return final_answer, trace

        # ----------------------------------------------------------------------
        # TOOL CALL
        # ----------------------------------------------------------------------
        if response_type == "tool_call":
            tool_name = llm_response.get("tool_name", "")
            arguments = llm_response.get("arguments", {})

            mcp_result = mcp_server.call_tool(
                tool_name,
                arguments,
            )

            observation = unwrap_mcp_result(mcp_result)

            trace.append(
                {
                    "step": step,
                    "type": "TOOL_CALL",
                    "thought": thought,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": observation,
                    "mcp_response": mcp_result,
                }
            )

            observation_str = json.dumps(
                observation,
                ensure_ascii=False,
            )

            # Giữ format này để tương thích với MockOfflineProvider
            # và đồng thời cung cấp Observation cho Gemini ở vòng kế tiếp.
            current_query = f"""
Yêu cầu ban đầu của người dùng:
{original_query}

Ở bước trước, bạn đã gọi Tool:
{tool_name}

Arguments:
{json.dumps(arguments, ensure_ascii=False)}

Observation nhận được từ Tool:
{observation_str}

Hãy tiếp tục xử lý yêu cầu ban đầu dựa trên Observation trên.

Quy tắc:
1. Nếu đã đủ thông tin để trả lời người dùng:
   - Trả về type = "text".
   - Đưa ra Final Answer chính xác.

2. Nếu cần gọi thêm công cụ:
   - Trả về type = "tool_call".
   - Chọn đúng Tool và arguments.

3. Với Trợ lý Quản lý Đơn giao đồ ăn:
   - Nếu người dùng chỉ hỏi thông tin món:
     sau query_menu có thể trả Final Answer.
   - Nếu người dùng yêu cầu đặt món:
     cần đảm bảo món tồn tại và còn hàng trước khi create_order.
   - Nếu cần nhiều loại món:
     có thể query_menu nhiều lần rồi mới create_order.
   - Nếu status là NOT_FOUND:
     không được tự bịa món ăn.
   - Nếu món hết hàng:
     không được tạo đơn.
   - Nếu create_order trả SUCCESS:
     trả mã đơn, món đã đặt, số lượng và tổng tiền.
"""
            continue

        # ----------------------------------------------------------------------
        # RESPONSE KHÔNG HỢP LỆ
        # ----------------------------------------------------------------------
        error_text = (
            "LLM trả về định dạng không hợp lệ. "
            "Không xác định được type là 'text' hay 'tool_call'."
        )

        trace.append(
            {
                "step": step,
                "type": "ERROR",
                "thought": thought,
                "content": error_text,
            }
        )

        return error_text, trace

    final_answer = (
        "Agent đã đạt số vòng xử lý tối đa "
        "nhưng chưa hoàn thành yêu cầu."
    )

    trace.append(
        {
            "step": MAX_ITERATIONS,
            "type": "MAX_ITERATIONS",
            "content": final_answer,
        }
    )

    return final_answer, trace


def query_category(keyword: str) -> List[Dict[str, Any]]:
    result = mcp_server.call_tool(
        "query_menu",
        {"keyword": keyword},
    )
    data = unwrap_mcp_result(result)

    if data.get("status") == "SUCCESS":
        return data.get("data", [])

    return []


def collect_orders_from_trace(trace: List[Dict[str, Any]]):
    orders = []

    for item in trace:
        if item.get("type") != "TOOL_CALL":
            continue

        if item.get("tool_name") != "create_order":
            continue

        obs = item.get("observation", {})

        if obs.get("status") == "SUCCESS":
            orders.append(obs)

    return orders


def format_money(value: Any) -> str:
    try:
        return f"{int(value):,} VNĐ"
    except Exception:
        return str(value)


# ==============================================================================
# SESSION STATE
# ==============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Xin chào 👋 Tôi là **Food Ordering Agent**. "
                "Bạn có thể hỏi menu, kiểm tra món còn hàng hoặc yêu cầu đặt món."
            ),
        }
    ]

if "last_trace" not in st.session_state:
    st.session_state.last_trace = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ==============================================================================
# HEADER
# ==============================================================================

st.markdown(
    """
    <div class="hero">
        <h1>🍱 Food Ordering Agent</h1>
        <p>Trợ lý AI tra cứu menu, kiểm tra tình trạng món và tạo đơn hàng bằng ReAct + MCP.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tool_names = [
    tool.get("name", "")
    for tool in mcp_server.list_tools()
    if tool.get("name")
]


# ==============================================================================
# SIDEBAR
# ==============================================================================

with st.sidebar:
    st.header("⚙️ Agent Control")

    st.caption("Tools đang được MCP Server cung cấp")

    for name in tool_names:
        st.markdown(
            f'<span class="tool-chip">{name}</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("💡 Câu hỏi mẫu")

    examples = [
        "Tra cứu giúp tôi thông tin món Cơm gà.",
        "Đặt giúp tôi 1 phần Cơm gà.",
        "Có những đồ uống nào?",
        (
            "Tìm giúp tôi một phần cơm và một đồ uống "
            "có tổng giá dưới 120.000 đồng. Nếu còn món thì đặt giúp tôi."
        ),
        "Kiểm tra món FOOD9999 và đặt giúp tôi 1 phần.",
    ]

    for i, example in enumerate(examples):
        if st.button(
            example,
            key=f"example_{i}",
            use_container_width=True,
        ):
            st.session_state.pending_prompt = example

    st.divider()

    if st.button(
        "🧹 Xóa lịch sử chat",
        use_container_width=True,
    ):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Đã xóa lịch sử. Bạn muốn tra cứu hoặc đặt món gì?",
            }
        ]
        st.session_state.last_trace = []
        st.session_state.orders = []
        st.rerun()


# ==============================================================================
# MAIN TABS
# ==============================================================================

chat_tab, menu_tab, trace_tab, order_tab = st.tabs(
    [
        "💬 Chat với Agent",
        "📋 Menu",
        "🧠 ReAct Trace",
        "🧾 Đơn hàng",
    ]
)


# ==============================================================================
# TAB CHAT
# ==============================================================================

with chat_tab:
    st.subheader("Trò chuyện với Food Ordering Agent")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input(
        "Ví dụ: Đặt giúp tôi 1 phần Cơm gà..."
    )

    if st.session_state.pending_prompt:
        user_prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if user_prompt:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Agent đang suy luận và gọi công cụ..."):
                answer, trace = run_agent(user_prompt)

            st.markdown(answer)

            tool_steps = [
                x
                for x in trace
                if x.get("type") == "TOOL_CALL"
            ]

            if tool_steps:
                with st.expander(
                    f"🔎 Xem {len(tool_steps)} bước Tool Calling"
                ):
                    for event in tool_steps:
                        st.markdown(
                            f"**Step {event['step']} — "
                            f"`{event['tool_name']}`**"
                        )
                        st.caption(
                            f"Thought: {event.get('thought', '')}"
                        )
                        st.code(
                            json.dumps(
                                event.get("arguments", {}),
                                ensure_ascii=False,
                                indent=2,
                            ),
                            language="json",
                        )
                        st.caption("Observation")
                        st.json(
                            event.get("observation", {})
                        )
                        st.divider()

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.session_state.last_trace = trace

        new_orders = collect_orders_from_trace(trace)

        if new_orders:
            st.session_state.orders.extend(new_orders)

        st.rerun()


# ==============================================================================
# TAB MENU
# ==============================================================================

with menu_tab:
    st.subheader("📋 Thực đơn hiện tại")

    main_items = query_category("Món chính")
    drink_items = query_category("Đồ uống")

    left, right = st.columns(2)

    with left:
        st.markdown("### 🍚 Món chính")

        for item in main_items:
            availability = (
                "✅ Còn hàng"
                if item.get("available")
                else "❌ Hết hàng"
            )

            st.markdown(
                f"""
                <div class="menu-card">
                    <b>{item.get('name')}</b><br>
                    <span class="small-muted">{item.get('item_id')}</span><br><br>
                    💰 {format_money(item.get('price'))}<br>
                    {availability}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        st.markdown("### 🥤 Đồ uống")

        for item in drink_items:
            availability = (
                "✅ Còn hàng"
                if item.get("available")
                else "❌ Hết hàng"
            )

            st.markdown(
                f"""
                <div class="menu-card">
                    <b>{item.get('name')}</b><br>
                    <span class="small-muted">{item.get('item_id')}</span><br><br>
                    💰 {format_money(item.get('price'))}<br>
                    {availability}
                </div>
                """,
                unsafe_allow_html=True,
            )


# ==============================================================================
# TAB TRACE
# ==============================================================================

with trace_tab:
    st.subheader("🧠 ReAct Trace gần nhất")

    if not st.session_state.last_trace:
        st.info(
            "Chưa có trace. Hãy gửi một yêu cầu trong tab Chat trước."
        )

    else:
        for event in st.session_state.last_trace:
            event_type = event.get("type")

            if event_type == "TOOL_CALL":
                st.markdown(
                    f"### Step {event.get('step')} — 🛠️ "
                    f"{event.get('tool_name')}"
                )
                st.write(
                    "**Thought:**",
                    event.get("thought", ""),
                )
                st.write("**Arguments:**")
                st.json(event.get("arguments", {}))
                st.write("**Observation:**")
                st.json(event.get("observation", {}))

            elif event_type == "FINAL_ANSWER":
                st.markdown(
                    f"### Step {event.get('step')} — 🏁 Final Answer"
                )
                st.write(
                    "**Thought:**",
                    event.get("thought", ""),
                )
                st.success(
                    event.get("content", "")
                )

            else:
                st.warning(
                    event.get("content", "Unknown event")
                )

            st.divider()


# ==============================================================================
# TAB ĐƠN HÀNG
# ==============================================================================

with order_tab:
    st.subheader("🧾 Đơn hàng đã tạo trong phiên")

    if not st.session_state.orders:
        st.info(
            "Chưa có đơn hàng nào trong phiên hiện tại."
        )

    else:
        for index, order in enumerate(
            reversed(st.session_state.orders),
            start=1,
        ):
            with st.container(border=True):
                st.markdown(
                    f"### #{index} — {order.get('order_id', 'N/A')}"
                )

                for item in order.get("items", []):
                    st.write(
                        f"• {item.get('quantity', 1)} x "
                        f"{item.get('name', item.get('item_id'))} "
                        f"— {format_money(item.get('subtotal'))}"
                    )

                st.markdown(
                    f"**Tổng tiền: "
                    f"{format_money(order.get('total_price'))}**"
                )

                note = order.get("order_note")

                if note:
                    st.caption(
                        f"Ghi chú: {note}"
                    )
