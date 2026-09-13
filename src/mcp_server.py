"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture)
cung cấp công cụ chuẩn hóa.

CHỦ ĐỀ:
Trợ lý Quản lý Đơn giao đồ ăn
"""

import json
import sys
from typing import Dict, Any, List

from tools import TOOLS_SCHEMA, dispatch_tool_call


# ==============================================================================
# CẤU HÌNH UTF-8
# ==============================================================================

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# MCP SERVER
# ==============================================================================

class MCPAcademicServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol.

    Giữ nguyên tên class MCPAcademicServer để tương thích
    với cấu trúc project gốc.
    """

    def __init__(
        self,
        server_name: str = "food-order-mcp-server"
    ):
        self.server_name = server_name
        self.version = "2026.1.0"


    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Trả về danh sách các Tools chuẩn giao thức MCP.
        """

        return TOOLS_SCHEMA


    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:

        """
        [TASK 2.1]
        HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER.

        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC.
        """

        # ----------------------------------------------------------------------
        # TODO 2.1: HỌC VIÊN HOÀN THIỆN HÀM GỌI TOOL CHUẨN MCP JSON-RPC
        #
        # 🎯 YÊU CẦU THỰC THI THUẬT TOÁN:
        #
        # 1. Gọi hàm dispatch_tool_call(tool_name, arguments)
        #    để lấy chuỗi JSON kết quả từ Tool Router.
        #
        # 2. Chuyển đổi chuỗi JSON kết quả thành Python Dictionary
        #    bằng json.loads().
        #
        # 3. Đóng gói phản hồi và trả về Dict theo đúng chuẩn MCP JSON-RPC 2.0:
        #
        #    {
        #        "jsonrpc": "2.0",
        #        "server": self.server_name,
        #        "tool": tool_name,
        #        "result": content
        #    }
        # ----------------------------------------------------------------------

        # BƯỚC 1:
        # Gọi Tool Router để thực thi Tool
        tool_result = dispatch_tool_call(
            tool_name,
            arguments
        )

        # BƯỚC 2:
        # Chuyển JSON string thành Python Dictionary
        content = json.loads(
            tool_result
        )

        # BƯỚC 3:
        # Đóng gói phản hồi chuẩn MCP JSON-RPC 2.0
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


# ==============================================================================
# KIỂM THỬ ĐỘC LẬP MCP SERVER
# ==============================================================================

if __name__ == "__main__":

    print(
        "=========================================================="
    )

    print(
        "🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER "
        "(food-order-mcp-server)"
    )

    print(
        "=========================================================="
    )


    # Khởi tạo MCP Server
    server = MCPAcademicServer()


    # Lấy danh sách Tool
    tools = server.list_tools()


    print(
        f"✅ Khởi tạo thành công MCP Server: "
        f"{server.server_name} "
        f"(Version: {server.version})"
    )

    print(
        f"📦 Số lượng Tools công bố: "
        f"{len(tools)}"
    )


    # ==========================================================================
    # KIỂM TRA TRẠNG THÁI TODO 1.2 (TOOL SCHEMA)
    # ==========================================================================

    create_order_tool = next(
        (
            t for t in tools
            if t.get("name") == "create_order"
        ),
        None
    )


    if (
        create_order_tool
        and not create_order_tool
        .get("parameters", {})
        .get("properties")
    ):

        print(
            "⏳ [TODO 1.2]: "
            "Tool 'create_order' chưa được định nghĩa "
            "properties trong 'src/tools.py'."
        )

    elif create_order_tool:

        print(
            "✅ [TODO 1.2]: "
            "Tool 'create_order' đã có schema đầy đủ."
        )

    else:

        print(
            "⚠️ [TODO 1.2]: "
            "Không tìm thấy Tool 'create_order' "
            "trong TOOLS_SCHEMA."
        )


    # ==========================================================================
    # KIỂM TRA TRẠNG THÁI TODO 2.1 (call_tool)
    # ==========================================================================

    test_result = server.call_tool(
        "query_menu",
        {
            "keyword": "Cơm gà"
        }
    )


    if not test_result:

        print(
            "⏳ [TODO 2.1]: "
            "Hàm call_tool() đang trả về rỗng. "
            "Học viên hãy hoàn thiện TODO 2.1 "
            "trong 'src/mcp_server.py'!"
        )

    else:

        print(
            "✅ [TODO 2.1]: "
            "Test dispatch tool 'query_menu' thành công:"
        )

        print(
            "   Phản hồi JSON-RPC: "
            f"{json.dumps(test_result, ensure_ascii=False)}"
        )