"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any


# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [

    # Tool 1: Đã được định nghĩa mẫu sẵn cho Học viên tham khảo
    {
        "name": "query_menu",
        "description": "Tra cứu thông tin món ăn trong thực đơn bằng tên, mã món hoặc loại món.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Tên, mã hoặc loại món cần tra cứu (ví dụ: 'Cơm gà', 'FOOD001', 'Món chính')"
                }
            },
            "required": ["keyword"]
        }
    },

    # --------------------------------------------------------------------------
    # TODO 1.2: HỌC VIÊN HOÀN THIỆN TOOL SCHEMA CHO 'create_order'
    # 🎯 YÊU CẦU THIẾT KẾ SCHEMA (JSON SCHEMA STANDARD):
    # 1. Tool dùng để tạo đơn đặt đồ ăn.
    # 2. Thiết kế các tham số (properties) để LLM trích xuất:
    #    - items (array): Danh sách các món ăn cần đặt
    #    - item_id (string): Mã món ăn
    #    - quantity (integer): Số lượng món ăn
    #    - order_note (string): Ghi chú cho đơn hàng
    # 3. Khai báo danh sách các trường bắt buộc (required).
    # --------------------------------------------------------------------------

    {
        "name": "create_order",
        "description": "Tạo đơn đặt đồ ăn sau khi đã xác định món ăn và số lượng người dùng muốn đặt.",
        "parameters": {
            "type": "object",
            "properties": {

                # TODO 1.2: Khai báo các thuộc tính tham số cho Tool tại đây...

                "items": {
                    "type": "array",
                    "description": "Danh sách các món ăn cần đặt.",
                    "items": {
                        "type": "object",
                        "properties": {

                            "item_id": {
                                "type": "string",
                                "description": "Mã món ăn cần đặt (ví dụ: 'FOOD001')"
                            },

                            "quantity": {
                                "type": "integer",
                                "description": "Số lượng món ăn cần đặt",
                                "minimum": 1
                            }
                        },

                        "required": [
                            "item_id",
                            "quantity"
                        ]
                    }
                },

                "order_note": {
                    "type": "string",
                    "description": "Ghi chú thêm cho đơn hàng (ví dụ: 'không cay')"
                }
            },

            "required": [
                "items"
            ]

            # TODO 1.2: Khai báo danh sách các trường bắt buộc tại đây...
        }
    }
]


# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {

    "FOOD001": {
        "name": "Cơm gà",
        "category": "Món chính",
        "price": 65000,
        "available": True
    },

    "FOOD002": {
        "name": "Cơm sườn",
        "category": "Món chính",
        "price": 70000,
        "available": True
    },

    "FOOD003": {
        "name": "Phở bò",
        "category": "Món chính",
        "price": 60000,
        "available": False
    },

    "DRINK002": {
        "name": "Trà chanh",
        "category": "Đồ uống",
        "price": 25000,
        "available": True
    },

    "DRINK003": {
        "name": "Cà phê sữa",
        "category": "Đồ uống",
        "price": 30000,
        "available": True
    }
}


def execute_query_menu(keyword: str) -> str:
    """Thực thi tra cứu món ăn theo tên, mã hoặc loại món"""

    keyword = keyword.strip().lower()

    results = []

    for item_id, item in MOCK_DATABASE.items():

        if (
            keyword in item_id.lower()
            or keyword in item["name"].lower()
            or keyword in item["category"].lower()
        ):

            results.append({
                "item_id": item_id,
                "name": item["name"],
                "category": item["category"],
                "price": item["price"],
                "available": item["available"]
            })

    if results:

        return json.dumps({
            "status": "SUCCESS",
            "count": len(results),
            "data": results
        }, ensure_ascii=False)

    else:

        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy món ăn phù hợp với '{keyword}'"
        }, ensure_ascii=False)


def execute_create_order(items: list, order_note: str = "") -> str:
    """Thực thi tạo đơn đặt đồ ăn"""

    order_items = []
    total_price = 0

    for requested_item in items:

        item_id = requested_item.get("item_id", "").strip().upper()
        quantity = requested_item.get("quantity", 1)

        # Kiểm tra món có tồn tại hay không
        if item_id not in MOCK_DATABASE:

            return json.dumps({
                "status": "NOT_FOUND",
                "message": f"Không tìm thấy món ăn có mã '{item_id}'."
            }, ensure_ascii=False)

        item = MOCK_DATABASE[item_id]

        # Kiểm tra món còn hàng hay không
        if not item["available"]:

            return json.dumps({
                "status": "OUT_OF_STOCK",
                "item_id": item_id,
                "item_name": item["name"],
                "message": f"Món '{item['name']}' hiện đã hết hàng."
            }, ensure_ascii=False)

        # Kiểm tra số lượng
        if quantity < 1:

            return json.dumps({
                "status": "INVALID_QUANTITY",
                "message": f"Số lượng của món '{item['name']}' phải lớn hơn 0."
            }, ensure_ascii=False)

        subtotal = item["price"] * quantity

        total_price += subtotal

        order_items.append({
            "item_id": item_id,
            "name": item["name"],
            "price": item["price"],
            "quantity": quantity,
            "subtotal": subtotal
        })

    return json.dumps({
        "status": "SUCCESS",
        "order_id": "ORD-2026-001",
        "items": order_items,
        "total_price": total_price,
        "order_note": order_note,
        "message": f"Đặt hàng thành công. Tổng tiền: {total_price:,} VNĐ."
    }, ensure_ascii=False)


# ==============================================================================
# 3. ROUTER GỌI TOOL THỰC TẾ
# ==============================================================================

TOOL_ROUTER = {
    "query_menu": execute_query_menu,
    "create_order": execute_create_order
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""

    if tool_name in TOOL_ROUTER:

        try:
            return TOOL_ROUTER[tool_name](**arguments)

        except Exception as e:

            return json.dumps({
                "status": "EXECUTION_ERROR",
                "error": str(e)
            }, ensure_ascii=False)

    return json.dumps({
        "status": "UNKNOWN_TOOL",
        "error": f"Tool '{tool_name}' không tồn tại!"
    }, ensure_ascii=False)


# ==============================================================================
# KIỂM TRA NHANH KHI CHẠY FILE tools.py
# ==============================================================================

if __name__ == "__main__":

    print(
        f"✅ [TOOLS CHECK]: Đã đăng ký thành công "
        f"{len(TOOLS_SCHEMA)} Native Tools trong TOOLS_SCHEMA!"
    )

    # --------------------------------------------------------------------------
    # TEST TOOL 1: query_menu
    # --------------------------------------------------------------------------

    test_query = dispatch_tool_call(
        "query_menu",
        {
            "keyword": "Cơm gà"
        }
    )

    query_result = json.loads(test_query)

    if query_result.get("status") == "SUCCESS":

        item = query_result["data"][0]

        print(
            f"🧪 Kết quả gọi thử query_menu: "
            f"Status SUCCESS "
            f"(Món {item['name']} - {item['price']:,} VNĐ)"
        )

    else:

        print(
            f"🧪 Kết quả gọi thử query_menu: "
            f"{test_query}"
        )


    # --------------------------------------------------------------------------
    # TEST TOOL 2: create_order
    # Đơn hàng gồm 1 Cơm gà
    # --------------------------------------------------------------------------

    test_order = dispatch_tool_call(
        "create_order",
        {
            "items": [
                {
                    "item_id": "FOOD001",
                    "quantity": 1
                }
            ],
            "order_note": "Không cay"
        }
    )

    order_result = json.loads(test_order)

    if order_result.get("status") == "SUCCESS":

        item_names = ", ".join(
            f"{item['quantity']} x {item['name']}"
            for item in order_result["items"]
        )

        print(
            f"🧪 Kết quả gọi thử create_order: "
            f"Status SUCCESS "
            f"(Mã đơn {order_result['order_id']} - "
            f"{item_names} - "
            f"Tổng tiền {order_result['total_price']:,} VNĐ)"
        )

    else:

        print(
            f"🧪 Kết quả gọi thử create_order: "
            f"{test_order}"
        )