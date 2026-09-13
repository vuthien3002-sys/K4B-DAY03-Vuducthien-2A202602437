# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** [Vũ Đức Thiện]  
> **Mã Sinh Viên / Mã Học viên:** [2A202602437]  
> **Chủ đề Lựa chọn:** [Trợ lý Quản lý Đơn giao đồ ăn]  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** |3 / 5 | Hệ thống cần thực hiện nhiều bước liên tiếp: hiểu yêu cầu của người dùng → tra cứu món ăn → kiểm tra tình trạng còn/hết món → kiểm tra giá và số lượng → tính tổng tiền → đối chiếu với yêu cầu/ngân sách → xác nhận thông tin → tạo đơn hàng. Với yêu cầu phức tạp, Agent còn phải lựa chọn món hoặc combo phù hợp trước khi đặt hàng. |
| **2. Tool Interaction** |4 / 5 | Agent cần tương tác với dữ liệu bên ngoài thông qua MCP Server/API/Cơ sở dữ liệu. Ví dụ, tool query_menu() dùng để tra cứu menu, giá và tình trạng món; tool create_order() dùng để tạo đơn hàng. Trong hệ thống thực tế có thể kết nối thêm dữ liệu nhà hàng, đơn hàng và trạng thái giao hàng. |
| **3. Dynamic Decision** | 3/ 5 | Quyết định ở bước sau phụ thuộc trực tiếp vào kết quả của bước trước. Ví dụ, nếu món còn hàng và phù hợp ngân sách thì Agent tiếp tục tạo đơn; nếu món hết hàng thì Agent phải tìm món thay thế hoặc hỏi lại người dùng; nếu tổng tiền vượt ngân sách thì Agent phải điều chỉnh lựa chọn thay vì đặt đơn ngay. |
| **4. Long Horizon Goal** | 4 / 5 | Agent cần duy trì mục tiêu của người dùng xuyên suốt nhiều bước, chẳng hạn loại món, số lượng, ngân sách và yêu cầu đặc biệt cho đến khi đơn hàng được tạo thành công. Sau khi đặt hàng, Agent còn có thể tiếp tục theo dõi trạng thái chuẩn bị và giao hàng. Tuy nhiên, quy trình thường hoàn thành trong một khoảng thời gian tương đối ngắn nên chưa cần mức độ duy trì mục tiêu rất dài như các Agent quản lý dự án hoặc nghiên cứu dài hạn. |
| **TỔNG ĐIỂM AGENTIC FIT** | 14/ 20** | *Nếu tổng điểm > 12/20: Bài toán rất phù hợp triển khai Agentic System.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY`
> (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi
> `python src/app.py --all`.
> Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dưới đây là một đoạn Waterfall Trace tiêu biểu của Test Case đặt món Cơm gà.
Agent sử dụng `query_menu` để tra cứu thông tin món trước, sau đó tiếp tục
suy luận và gọi `create_order` để tạo đơn hàng.

```json
[
  {
    "step": 1,
    "query": "Đặt giúp tôi 1 phần Cơm gà.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "query_menu",
    "arguments": {
      "keyword": "Cơm gà"
    },
    "observation": {
      "status": "SUCCESS",
      "count": 1,
      "data": [
        {
          "item_id": "FOOD001",
          "name": "Cơm gà",
          "category": "Món chính",
          "price": 65000,
          "available": true
        }
      ]
    },
    "latency_ms": 2476.14
  },
  {
    "step": 2,
    "query": "Đặt giúp tôi 1 phần Cơm gà.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "create_order",
    "arguments": {
      "items": [
        {
          "quantity": 1,
          "item_id": "FOOD001"
        }
      ]
    },
    "observation": {
      "status": "SUCCESS",
      "order_id": "ORD-2026-001",
      "items": [
        {
          "item_id": "FOOD001",
          "name": "Cơm gà",
          "price": 65000,
          "quantity": 1,
          "subtotal": 65000
        }
      ],
      "total_price": 65000,
      "order_note": "",
      "message": "Đặt hàng thành công. Tổng tiền: 65,000 VNĐ."
    },
    "latency_ms": 2648.72
  },
  {
    "step": 3,
    "query": "Đặt giúp tôi 1 phần Cơm gà.",
    "action_type": "FINAL_ANSWER",
    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "Đơn hàng của bạn đã được đặt thành công! Mã đơn hàng: ORD-2026-001. Món đã đặt: Cơm gà. Số lượng: 1 phần. Tổng tiền: 65,000 VNĐ",
    "latency_ms": 3711.29
  }
]

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 7 lượt.
- **Kết quả đẩy Repo nộp bài:** [X] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
