"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)

Thực thi so sánh giữa:
- Chatbot Baseline (Cấp 2)
- ReAct Agent kết nối MCP Server (Cấp 3)

CHỦ ĐỀ:
Trợ lý Quản lý Đơn giao đồ ăn
"""

import json
import os
import sys
import time

from dotenv import load_dotenv


# ==============================================================================
# 1. THIẾT LẬP PATH
# ==============================================================================

sys.path.append(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ==============================================================================
# 2. UTF-8 OUTPUT
# ==============================================================================

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# 3. IMPORT PROJECT MODULES
# ==============================================================================

from mcp_server import MCPAcademicServer
from providers import get_llm_provider
from prompts import MAX_ITERATIONS


load_dotenv()


# ==============================================================================
# 4. SYSTEM PROMPTS THEO CHỦ ĐỀ ĐƠN GIAO ĐỒ ĂN
# ==============================================================================

CHATBOT_BASELINE_PROMPT = """
Bạn là trợ lý quản lý đơn giao đồ ăn.

Bạn hỗ trợ người dùng:
- Hỏi thông tin món ăn.
- Hỏi giá món ăn.
- Hỏi các thông tin chung về thực đơn.

Đây là Chatbot Baseline nên bạn KHÔNG có quyền sử dụng Tool.

Không được tự bịa dữ liệu món ăn, giá hoặc tình trạng còn hàng.
"""


REACT_AGENT_SYSTEM_PROMPT = """
Bạn là ReAct Agent chuyên hỗ trợ QUẢN LÝ ĐƠN GIAO ĐỒ ĂN.

Bạn chỉ được sử dụng các Tool được cung cấp trong danh sách Native Tools.

Các Tool chính:

1. query_menu
Dùng để tra cứu món ăn theo:
- tên món
- mã món
- loại món

Ví dụ:
{
    "keyword": "Cơm gà"
}

Kết quả có thể chứa:
- item_id
- name
- category
- price
- available


2. create_order
Dùng để tạo đơn đặt đồ ăn.

Cấu trúc arguments:

{
    "items": [
        {
            "item_id": "FOOD001",
            "quantity": 1
        }
    ],
    "order_note": "Không cay"
}


QUY TẮC XỬ LÝ:

1. Nếu người dùng muốn tra cứu món:
   - Gọi query_menu.
   - Sau khi nhận Observation, trả lời dựa trên dữ liệu thực tế.

2. Nếu người dùng muốn đặt món bằng tên món:
   - Trước tiên gọi query_menu.
   - Lấy item_id và available từ Observation.
   - Nếu available = true thì gọi create_order.
   - Nếu available = false thì không được tạo đơn.

3. Nếu người dùng nói:
   "Kiểm tra món X còn hàng không, nếu còn thì đặt giúp tôi"

   Bắt buộc xử lý theo chuỗi:

   query_menu
   -> Observation
   -> create_order
   -> Observation
   -> Final Answer

4. Nếu Tool trả:
   status = NOT_FOUND

   thì:
   - Không được bịa dữ liệu.
   - Không được gọi create_order.
   - Thông báo không tìm thấy món.

5. Nếu Tool trả:
   status = OUT_OF_STOCK

   thì:
   - Không được tạo đơn.
   - Thông báo món đã hết hàng.

6. Nếu create_order trả SUCCESS:
   - Trả lời mã đơn.
   - Tên món.
   - Số lượng.
   - Tổng tiền.

7. Không sử dụng các Tool cũ:
   - academic_query
   - schedule_appointment

8. Không tự chuyển yêu cầu đồ ăn thành:
   - sinh viên
   - GPA
   - cố vấn học tập
   - lịch tư vấn
   - mã sinh viên

Luôn dựa trên Observation thực tế từ Tool.
"""


# ==============================================================================
# 5. LOAD TEST CASES
# ==============================================================================

def load_test_cases():
    """
    Tải danh sách test cases từ:
    config/test_cases.json

    Nếu chưa có thì dùng:
    config/test_cases.example.json
    """

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    config_path = os.path.join(
        base_dir,
        "config",
        "test_cases.json"
    )

    if not os.path.exists(config_path):

        example_path = os.path.join(
            base_dir,
            "config",
            "test_cases.example.json"
        )

        if os.path.exists(example_path):

            print(
                "⚠️ [CONFIG NOTICE]: "
                "Chưa thấy file 'config/test_cases.json'. "
                "Đang dùng file mẫu."
            )

            config_path = example_path

        else:

            config_path = "test_cases.json"

    with open(
        config_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ==============================================================================
# 6. SAVE WATERFALL TRACE
# ==============================================================================

def save_waterfall_trace(trace_data: list):
    """
    Lưu Waterfall Trace ra:
    docs/trace_waterfall.json
    """

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    docs_dir = os.path.join(
        base_dir,
        "docs"
    )

    os.makedirs(
        docs_dir,
        exist_ok=True
    )

    trace_path = os.path.join(
        docs_dir,
        "trace_waterfall.json"
    )

    with open(
        trace_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            trace_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"📊 [OBSERVABILITY]: "
        f"Đã lưu {len(trace_data)} sự kiện "
        f"Waterfall Trace tại '{trace_path}'!"
    )


# ==============================================================================
# 7. CHATBOT BASELINE
# ==============================================================================

def run_baseline_chatbot(
    user_query: str,
    provider
):
    """
    Chatbot Baseline không sử dụng Tool.
    """

    print(
        f"\n💬 [CHATBOT BASELINE] "
        f"Câu hỏi: {user_query}"
    )

    response = provider.generate(
        user_query,
        system_prompt=CHATBOT_BASELINE_PROMPT
    )

    print(
        f"🤖 Chatbot phản hồi:\n"
        f"{response}"
    )


# ==============================================================================
# 8. TASK 2.2 — REACT LOOP VÀ NATIVE TOOL CALLING
# ==============================================================================

def run_react_agent(
    user_query: str,
    provider,
    mcp_server: MCPAcademicServer
) -> list:

    """
    [TASK 2.2]

    ReAct Loop:

    Thought
        ↓
    Action
        ↓
    mcp_server.call_tool()
        ↓
    Observation
        ↓
    Thought tiếp theo
        ↓
    ...
        ↓
    Final Answer
    """

    print(
        f"\n🤖 [REACT AGENT] "
        f"Câu hỏi: {user_query}"
    )


    step = 0

    trace_logs = []


    # --------------------------------------------------------------------------
    # Tool Schema được lấy từ MCP Server
    # MCP Server sẽ trả TOOLS_SCHEMA trong tools.py
    # --------------------------------------------------------------------------

    tools_list = mcp_server.list_tools()


    # Yêu cầu gốc của người dùng
    original_query = user_query


    # Nội dung gửi cho LLM ở mỗi vòng
    current_query = user_query


    # --------------------------------------------------------------------------
    # TODO 2.2:
    # HỌC VIÊN HOÀN THIỆN REACT LOOP
    #
    # Yêu cầu:
    #
    # 1. while step < MAX_ITERATIONS
    #
    # 2. Nếu type == "text":
    #       In Final Answer
    #       break
    #
    # 3. Nếu type == "tool_call":
    #       gọi mcp_server.call_tool()
    #       nhận Observation
    #       nạp Observation cho lượt tiếp theo
    # --------------------------------------------------------------------------

    while step < MAX_ITERATIONS:

        step += 1

        step_start_time = time.time()


        print(
            f"\n--- 🔄 Vòng lặp ReAct Loop "
            f"(Step {step}/{MAX_ITERATIONS}) ---"
        )


        # ======================================================================
        # THOUGHT
        # ======================================================================

        llm_response = provider.generate_with_tools(
            current_query,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )


        latency_ms = round(
            (time.time() - step_start_time) * 1000,
            2
        )


        thought = llm_response.get(
            "thought",
            "Đang suy luận..."
        )


        print(
            f"🧠 [Thought]: "
            f"{thought}"
        )


        # ======================================================================
        # TRƯỜNG HỢP 1:
        # LLM TRẢ VỀ type == "text"
        # ======================================================================

        if llm_response.get("type") == "text":

            final_content = llm_response.get(
                "content",
                ""
            )


            print(
                f"🏁 [Final Answer]: "
                f"{final_content}"
            )


            trace_logs.append({
                "step": step,
                "query": original_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })


            # type == "text"
            # -> kết thúc vòng lặp
            break


        # ======================================================================
        # TRƯỜNG HỢP 2:
        # LLM TRẢ VỀ type == "tool_call"
        # ======================================================================

        elif llm_response.get("type") == "tool_call":

            tool_name = llm_response.get(
                "tool_name"
            )


            arguments = llm_response.get(
                "arguments",
                {}
            )


            # ==================================================================
            # ACTION
            # ==================================================================

            print(
                f"🛠️ [Action Proposed]: "
                f"{tool_name}({arguments})"
            )


            # ==================================================================
            # TOOL EXECUTION QUA MCP SERVER
            #
            # TASK 2.1 nằm trong mcp_server.py
            #
            # app.py KHÔNG gọi dispatch_tool_call() trực tiếp.
            # ==================================================================

            mcp_result = mcp_server.call_tool(
                tool_name,
                arguments
            )


            # ==================================================================
            # LẤY RESULT TỪ PHẢN HỒI MCP JSON-RPC
            #
            # MCP trả dạng:
            #
            # {
            #     "jsonrpc": "2.0",
            #     "server": "...",
            #     "tool": "...",
            #     "result": {...}
            # }
            # ==================================================================

            if isinstance(
                mcp_result,
                dict
            ):

                obs_data = mcp_result.get(
                    "result",
                    {}
                )

            else:

                obs_data = {}


            # ==================================================================
            # OBSERVATION
            # ==================================================================

            observation_str = json.dumps(
                obs_data,
                ensure_ascii=False
            )


            print(
                f"👁️ [Observation từ MCP Server]: "
                f"{observation_str}"
            )


            # ==================================================================
            # TRACE LOG
            # ==================================================================

            trace_logs.append({
                "step": step,
                "query": original_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })


            # ==================================================================
            # NẠP OBSERVATION CHO LƯỢT TIẾP THEO
            #
            # KHÔNG break ở đây.
            #
            # Agent phải quay lại vòng while để suy luận tiếp.
            # ==================================================================

            current_query = f"""
Yêu cầu ban đầu của người dùng:

{original_query}


Ở bước trước bạn đã gọi Tool:

{tool_name}


Arguments:

{json.dumps(arguments, ensure_ascii=False)}


Observation từ MCP Server:

{observation_str}


Hãy tiếp tục xử lý yêu cầu ban đầu dựa trên Observation này.


QUY TẮC:

1. Nếu đã đủ thông tin:
   trả về type = "text" và đưa ra Final Answer.

2. Nếu vẫn cần thực hiện hành động:
   trả về type = "tool_call" và gọi Tool phù hợp.

3. Nếu vừa gọi query_menu và người dùng chỉ muốn tra cứu:
   trả Final Answer từ kết quả tra cứu.

4. Nếu vừa gọi query_menu và người dùng muốn đặt món:
   - Kiểm tra status.
   - Kiểm tra available.
   - Lấy item_id từ Observation.
   - Nếu món còn hàng thì gọi create_order.

5. create_order phải dùng cấu trúc:

{{
    "items": [
        {{
            "item_id": "FOOD001",
            "quantity": 1
        }}
    ]
}}

6. Nếu Observation có:
   status = "NOT_FOUND"

   thì không được gọi create_order.

7. Nếu:
   available = false

   hoặc:

   status = "OUT_OF_STOCK"

   thì không được tạo đơn.

8. Nếu create_order trả SUCCESS:
   trả Final Answer gồm:
   - mã đơn
   - món đã đặt
   - số lượng
   - tổng tiền

9. Không được sử dụng:
   academic_query
   schedule_appointment

Tiếp tục suy luận.
"""


            # Không break
            # Vòng while tiếp tục


        # ======================================================================
        # RESPONSE KHÔNG HỢP LỆ
        # ======================================================================

        else:

            final_answer = (
                "LLM trả về định dạng không hợp lệ. "
                "Không xác định được type là "
                "'text' hay 'tool_call'."
            )


            print(
                f"⚠️ [ERROR]: "
                f"{final_answer}"
            )


            trace_logs.append({
                "step": step,
                "query": original_query,
                "action_type": "ERROR",
                "thought": thought,
                "output": final_answer,
                "latency_ms": latency_ms
            })


            break


    # ==========================================================================
    # MAX ITERATIONS
    # ==========================================================================

    else:

        final_answer = (
            "Agent đã đạt số vòng xử lý tối đa "
            "nhưng chưa hoàn thành yêu cầu."
        )


        print(
            f"⚠️ [MAX ITERATIONS]: "
            f"{final_answer}"
        )


        trace_logs.append({
            "step": step,
            "query": original_query,
            "action_type": "FINAL_ANSWER",
            "thought": "Đạt giới hạn MAX_ITERATIONS.",
            "output": final_answer,
            "latency_ms": 0
        })


    return trace_logs


# ==============================================================================
# 9. MAIN PROGRAM
# ==============================================================================

if __name__ == "__main__":

    print(
        "=========================================================="
    )

    print(
        "🍱 DAY 03 LAB - "
        "TRỢ LÝ QUẢN LÝ ĐƠN GIAO ĐỒ ĂN"
    )

    print(
        "=========================================================="
    )


    # ==========================================================================
    # LLM PROVIDER
    # ==========================================================================

    provider = get_llm_provider()


    # ==========================================================================
    # MCP SERVER
    #
    # Giữ tên MCPAcademicServer
    # để tương thích project gốc.
    # ==========================================================================

    mcp_server = MCPAcademicServer()


    print(
        f"🔌 LLM Provider: "
        f"{provider.__class__.__name__}"
    )


    print(
        f"🌐 MCP Server: "
        f"{mcp_server.server_name}\n"
    )


    # ==========================================================================
    # LOAD TEST CASES
    # ==========================================================================

    tests = load_test_cases()


    print(
        f"✅ Đã tải thành công "
        f"{len(tests)} Test Cases thử nghiệm.\n"
    )


    # ==========================================================================
    # INTERACTIVE MODE
    # ==========================================================================

    if "--interactive" in sys.argv:

        print(
            "🎮 [INTERACTIVE MODE] "
            "Trò chuyện trực tiếp với ReAct Agent:"
        )


        print(
            "💡 Gợi ý câu hỏi thử nghiệm:"
        )


        print(
            "   - Tra cứu món: "
            "'Tra cứu món Cơm gà'"
        )


        print(
            "   - Tra cứu danh mục: "
            "'Có những món chính nào?'"
        )


        print(
            "   - Đặt món: "
            "'Đặt giúp tôi 1 phần Cơm gà'"
        )


        print(
            "   - ReAct đa bước: "
            "'Kiểm tra Cơm gà còn hàng không, "
            "nếu còn thì đặt giúp tôi 1 phần'"
        )


        print(
            "   - Edge case: "
            "'Kiểm tra món FOOD9999 "
            "và đặt giúp tôi 1 phần'"
        )


        print(
            "   - Gõ 'exit' hoặc 'quit' "
            "để kết thúc.\n"
        )


        while True:

            try:

                user_input = input(
                    "👤 Người dùng hỏi: "
                ).strip()


                if (
                    not user_input
                    or user_input.lower()
                    in ["exit", "quit"]
                ):

                    print(
                        "👋 Tạm biệt! "
                        "Kết thúc phiên trò chuyện."
                    )

                    break


                logs = run_react_agent(
                    user_input,
                    provider,
                    mcp_server
                )


                save_waterfall_trace(
                    logs
                )


            except (
                KeyboardInterrupt,
                EOFError
            ):

                print(
                    "\n👋 Đã thoát phiên tương tác."
                )

                break


    # ==========================================================================
    # TEST SUITE MODE
    # ==========================================================================

    elif "--all" in sys.argv:

        print(
            "🚀 [TEST SUITE MODE] "
            "Kiểm tra các Test Cases:"
        )


        completed_count = 0
        todo_count = 0
        all_traces = []


        for tc in tests:

            print(
                "\n=================================================="
            )


            print(
                f"🧪 [{tc['id']}] "
                f"Loại test: {tc['type']} "
                f"(Độ phức tạp: {tc['complexity']})"
            )


            print(
                f"📌 Kỳ vọng: "
                f"{tc['expected_behavior']}"
            )


            if tc["question"].strip().startswith(
                "TODO"
            ):

                print(
                    "⏸️ [CHƯA KÍCH HOẠT - "
                    "ĐANG LÀ TODO]:"
                )


                print(
                    f"   {tc['question']}"
                )


                todo_count += 1


            else:

                logs = run_react_agent(
                    tc["question"],
                    provider,
                    mcp_server
                )


                all_traces.extend(
                    logs
                )


                completed_count += 1


        print(
            "\n=================================================="
        )


        print(
            f"📊 [KẾT QUẢ TEST SUITE]: "
            f"Đã thực thi "
            f"{completed_count}/{len(tests)} "
            f"Test Cases | "
            f"{todo_count} Test Cases TODO"
        )


        if all_traces:

            save_waterfall_trace(
                all_traces
            )


    # ==========================================================================
    # DEFAULT MODE
    # ==========================================================================

    else:

        print(
            "ℹ️ HƯỚNG DẪN SỬ DỤNG:"
        )


        print(
            "  1. Chat trực tiếp:"
        )

        print(
            "     python src/app.py --interactive"
        )


        print(
            "\n  2. Chạy toàn bộ Test Cases:"
        )

        print(
            "     python src/app.py --all"
        )