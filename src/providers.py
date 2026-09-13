"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.

CHỦ ĐỀ:
Trợ lý Quản lý Đơn giao đồ ăn
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


load_dotenv()


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """
    Offline Mock Provider dùng để chạy thử mà không tốn API Key.

    Mock này mô phỏng đúng chủ đề:
    Trợ lý Quản lý Đơn giao đồ ăn.
    """

    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

        # Lưu trạng thái ngắn hạn để mô phỏng ReAct nhiều bước,
        # đặc biệt cho TC04: món chính -> đồ uống -> create_order.
        self._active_query = None
        self._stage = None
        self._selected_main = None

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return (
            f"[Mock Chatbot Response]: Tôi đã nhận được câu hỏi '{prompt}'. "
            "Chế độ Chatbot Baseline không có Tool nên không thể xác minh "
            "menu, giá hoặc tình trạng món theo dữ liệu thực tế."
        )

    @staticmethod
    def _extract_original_query(prompt: str) -> str:
        """
        Lấy đúng câu hỏi gốc của người dùng.

        app.py ở các vòng sau sẽ nối thêm Observation và rất nhiều quy tắc
        có các từ như 'đặt', 'create_order'. Nếu kiểm tra toàn bộ prompt,
        Mock sẽ hiểu nhầm câu chỉ-tra-cứu thành yêu cầu đặt hàng.
        """
        marker = "Yêu cầu ban đầu của người dùng:"

        if marker not in prompt:
            return prompt.strip()

        tail = prompt.split(marker, 1)[1].strip()

        stop_markers = [
            "\n\nỞ bước trước",
            "\n\nTool vừa thực thi",
            "\n\nTham số:",
            "\n\nArguments:",
            "\n\nObservation",
            "\n\nHãy tiếp tục",
            "\n\nQUY TẮC:",
            "\n\nQuy tắc:"
        ]

        cut_positions = [
            tail.find(m)
            for m in stop_markers
            if tail.find(m) != -1
        ]

        if cut_positions:
            tail = tail[:min(cut_positions)]

        return tail.strip()

    @staticmethod
    def _extract_quantity(user_query: str) -> int:
        """Lấy số lượng từ chính câu hỏi gốc của người dùng."""
        query_lower = user_query.lower()

        patterns = [
            r"(\d+)\s*(?:phần|suất|món)",
            r"(?:đặt|mua|lấy)\s*(?:giúp tôi\s*)?(\d+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)

            if match:
                try:
                    value = int(match.group(1))
                    if value > 0:
                        return value
                except Exception:
                    pass

        return 1

    @staticmethod
    def _extract_keyword(user_query: str) -> str:
        """Xác định keyword để gọi query_menu từ câu hỏi gốc."""
        query_lower = user_query.lower()

        code_match = re.search(
            r"\b(?:food|drink)\d+\b",
            query_lower,
            re.IGNORECASE
        )

        if code_match:
            return code_match.group(0).upper()

        known_items = {
            "cơm gà": "Cơm gà",
            "cơm sườn": "Cơm sườn",
            "phở bò": "Phở bò",
            "trà chanh": "Trà chanh",
            "cà phê sữa": "Cà phê sữa",
            "món chính": "Món chính",
            "đồ uống": "Đồ uống"
        }

        for phrase, canonical in known_items.items():
            if phrase in query_lower:
                return canonical

        # Nếu chỉ nói "cơm" thì tìm trong nhóm món chính.
        if "cơm" in query_lower:
            return "Món chính"

        return "Món chính"

    @staticmethod
    def _extract_observation(prompt: str):
        """Đọc JSON Observation mà app.py nạp vào lượt ReAct kế tiếp."""
        markers = [
            "Observation từ MCP Server:",
            "Observation nhận được từ Tool:",
            "Observation:"
        ]

        for marker in markers:
            if marker in prompt:
                tail = prompt.split(marker, 1)[1].strip()
                decoder = json.JSONDecoder()

                try:
                    obj, _ = decoder.raw_decode(tail)

                    if isinstance(obj, dict):
                        return obj

                except Exception:
                    pass

        return None

    @staticmethod
    def _is_intro_query(user_query: str) -> bool:
        """
        TC01: câu hỏi giới thiệu chức năng phải trả lời trực tiếp,
        không được gọi Tool.
        """
        q = user_query.lower()

        intro_phrases = [
            "giới thiệu",
            "hỗ trợ những gì",
            "bạn làm được gì",
            "bạn có thể làm gì",
            "chức năng của bạn",
            "bạn hỗ trợ gì"
        ]

        return any(phrase in q for phrase in intro_phrases)

    @staticmethod
    def _wants_order(user_query: str) -> bool:
        """Chỉ xét ý định đặt hàng từ câu hỏi gốc, không xét prompt nối thêm."""
        q = user_query.lower()

        return any(
            phrase in q
            for phrase in [
                "đặt giúp",
                "đặt cho",
                "đặt 1",
                "đặt một",
                "đặt món",
                "tạo đơn",
                "mua giúp",
                "nếu còn thì đặt",
                "nếu còn hàng thì đặt"
            ]
        )

    @staticmethod
    def _is_combo_budget_query(user_query: str) -> bool:
        """Nhận diện TC04: cần cả món chính và đồ uống theo ngân sách."""
        q = user_query.lower()

        has_main = "cơm" in q or "món chính" in q
        has_drink = "đồ uống" in q or "nước" in q
        has_budget = (
            "dưới" in q
            or "không quá" in q
            or "ngân sách" in q
            or "120.000" in q
            or "120000" in q
        )

        return has_main and has_drink and has_budget

    def _reset_session_if_needed(self, user_query: str):
        """Reset trạng thái Mock khi sang câu hỏi/test case mới."""
        if self._active_query != user_query:
            self._active_query = user_query
            self._stage = None
            self._selected_main = None

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:

        user_query = self._extract_original_query(prompt)
        query_lower = user_query.lower()
        obs = self._extract_observation(prompt)

        self._reset_session_if_needed(user_query)

        available_tools = {
            tool.get("name")
            for tool in tools_schema
            if tool.get("name")
        }

        # ======================================================================
        # SAU KHI CÓ OBSERVATION
        # ======================================================================

        if obs is not None:
            status = obs.get("status")

            # TC05 / edge case
            if status == "NOT_FOUND":
                self._stage = None

                return {
                    "type": "text",
                    "content": obs.get(
                        "message",
                        "Không tìm thấy món ăn theo yêu cầu."
                    ),
                    "thought": (
                        "Tool trả về NOT_FOUND nên không được bịa dữ liệu "
                        "và không được tạo đơn."
                    )
                }

            if status == "OUT_OF_STOCK":
                self._stage = None

                return {
                    "type": "text",
                    "content": obs.get(
                        "message",
                        "Món ăn hiện đã hết hàng."
                    ),
                    "thought": (
                        "Tool báo món đã hết hàng nên không thể tiếp tục tạo đơn."
                    )
                }

            # create_order đã thành công -> Final Answer
            if status == "SUCCESS" and "order_id" in obs:
                items = obs.get("items", [])

                item_text = ", ".join(
                    f"{item.get('quantity', 1)} x "
                    f"{item.get('name', item.get('item_id', 'món'))}"
                    for item in items
                )

                total = obs.get("total_price", 0)
                order_id = obs.get("order_id", "")

                self._stage = None
                self._selected_main = None

                return {
                    "type": "text",
                    "content": (
                        f"Đặt hàng thành công. Mã đơn {order_id}. "
                        f"Món đã đặt: {item_text}. "
                        f"Tổng tiền: {total:,} VNĐ."
                    ),
                    "thought": (
                        "create_order đã trả SUCCESS nên đã đủ thông tin "
                        "để trả Final Answer."
                    )
                }

            # Kết quả query_menu
            if status == "SUCCESS" and "data" in obs:
                data = obs.get("data", [])

                if not data:
                    self._stage = None

                    return {
                        "type": "text",
                        "content": "Không có dữ liệu món ăn phù hợp.",
                        "thought": (
                            "query_menu trả SUCCESS nhưng danh sách dữ liệu rỗng."
                        )
                    }

                # ==============================================================
                # TC04: Món chính -> Đồ uống -> create_order cả hai món
                # ==============================================================

                if self._is_combo_budget_query(user_query):

                    # Đã nhận kết quả món chính
                    if self._stage == "WAITING_MAIN":
                        available_main = [
                            item
                            for item in data
                            if item.get("available") is True
                        ]

                        if not available_main:
                            self._stage = None

                            return {
                                "type": "text",
                                "content": (
                                    "Hiện không có món chính phù hợp còn hàng."
                                ),
                                "thought": (
                                    "Không tìm thấy món chính available=true "
                                    "nên không thể tiếp tục tạo combo."
                                )
                            }

                        # Chọn món chính rẻ nhất còn hàng để dễ thỏa ngân sách.
                        self._selected_main = min(
                            available_main,
                            key=lambda item: item.get("price", 10**18)
                        )

                        self._stage = "WAITING_DRINK"

                        return {
                            "type": "tool_call",
                            "tool_name": "query_menu",
                            "arguments": {
                                "keyword": "Đồ uống"
                            },
                            "thought": (
                                f"Đã chọn món chính "
                                f"{self._selected_main.get('name')} "
                                f"giá {self._selected_main.get('price', 0):,} VNĐ. "
                                "Tiếp theo cần tra cứu đồ uống để tạo tổ hợp "
                                "dưới ngân sách."
                            )
                        }

                    # Đã nhận kết quả đồ uống
                    if self._stage == "WAITING_DRINK":
                        available_drinks = [
                            item
                            for item in data
                            if item.get("available") is True
                        ]

                        if not available_drinks or not self._selected_main:
                            self._stage = None

                            return {
                                "type": "text",
                                "content": (
                                    "Không tìm được tổ hợp món chính và đồ uống "
                                    "phù hợp để đặt."
                                ),
                                "thought": (
                                    "Thiếu món chính đã chọn hoặc không có đồ uống "
                                    "còn hàng."
                                )
                            }

                        # TC04 đang yêu cầu dưới 120.000 đồng.
                        budget = 120000

                        valid_drinks = [
                            drink
                            for drink in available_drinks
                            if (
                                self._selected_main.get("price", 0)
                                + drink.get("price", 0)
                            ) < budget
                        ]

                        if not valid_drinks:
                            self._stage = None

                            return {
                                "type": "text",
                                "content": (
                                    "Không tìm thấy tổ hợp một phần cơm và "
                                    "một đồ uống có tổng giá dưới 120.000 VNĐ."
                                ),
                                "thought": (
                                    "Không có đồ uống nào tạo được tổ hợp "
                                    "thỏa ngân sách."
                                )
                            }

                        selected_drink = min(
                            valid_drinks,
                            key=lambda item: item.get("price", 10**18)
                        )

                        self._stage = "WAITING_ORDER"

                        return {
                            "type": "tool_call",
                            "tool_name": "create_order",
                            "arguments": {
                                "items": [
                                    {
                                        "item_id": self._selected_main.get("item_id"),
                                        "quantity": 1
                                    },
                                    {
                                        "item_id": selected_drink.get("item_id"),
                                        "quantity": 1
                                    }
                                ]
                            },
                            "thought": (
                                f"Đã chọn "
                                f"{self._selected_main.get('name')} + "
                                f"{selected_drink.get('name')} với tổng "
                                f"{self._selected_main.get('price', 0) + selected_drink.get('price', 0):,} VNĐ, "
                                "nhỏ hơn 120.000 VNĐ. Tôi sẽ gọi create_order "
                                "để đặt cả hai món."
                            )
                        }

                # ==============================================================
                # TC02 / TC03: tra cứu một món
                # ==============================================================

                wants_order = self._wants_order(user_query)

                if wants_order:
                    available_item = next(
                        (
                            item
                            for item in data
                            if item.get("available") is True
                        ),
                        None
                    )

                    if not available_item:
                        self._stage = None

                        return {
                            "type": "text",
                            "content": (
                                "Món bạn yêu cầu hiện không còn hàng "
                                "nên tôi chưa thể tạo đơn."
                            ),
                            "thought": (
                                "Kết quả query_menu không có món available=true, "
                                "vì vậy không gọi create_order."
                            )
                        }

                    if "create_order" not in available_tools:
                        return {
                            "type": "text",
                            "content": (
                                "Không tìm thấy công cụ create_order "
                                "trong danh sách Tool hiện tại."
                            ),
                            "thought": (
                                "Không thể tạo đơn vì create_order không được công bố."
                            )
                        }

                    quantity = self._extract_quantity(user_query)

                    self._stage = "WAITING_ORDER"

                    return {
                        "type": "tool_call",
                        "tool_name": "create_order",
                        "arguments": {
                            "items": [
                                {
                                    "item_id": available_item.get("item_id"),
                                    "quantity": quantity
                                }
                            ]
                        },
                        "thought": (
                            f"Đã tra cứu được món {available_item.get('name')} "
                            "và món còn hàng. Người dùng có yêu cầu đặt món, "
                            "nên tôi sẽ gọi create_order."
                        )
                    }

                # TC02: chỉ tra cứu -> KHÔNG create_order
                lines = []

                for item in data:
                    state = (
                        "còn hàng"
                        if item.get("available")
                        else "hết hàng"
                    )

                    lines.append(
                        f"{item.get('name')} ({item.get('item_id')}): "
                        f"{item.get('price', 0):,} VNĐ - {state}"
                    )

                self._stage = None

                return {
                    "type": "text",
                    "content": (
                        "Kết quả tra cứu: "
                        + "; ".join(lines)
                        + "."
                    ),
                    "thought": (
                        "Người dùng chỉ yêu cầu tra cứu thông tin món, "
                        "không yêu cầu đặt hàng, nên trả Final Answer."
                    )
                }

            return {
                "type": "text",
                "content": obs.get(
                    "message",
                    f"Phản hồi từ công cụ: "
                    f"{json.dumps(obs, ensure_ascii=False)}"
                ),
                "thought": (
                    "Đã nhận Observation và không cần gọi thêm Tool."
                )
            }

        # ======================================================================
        # LƯỢT ĐẦU: CHƯA CÓ OBSERVATION
        # ======================================================================

        # TC01: giới thiệu chức năng -> trả text, không gọi tool
        if self._is_intro_query(user_query):
            return {
                "type": "text",
                "content": (
                    "Tôi là Trợ lý Quản lý Đơn giao đồ ăn. "
                    "Tôi có thể hỗ trợ bạn tra cứu món ăn, giá, "
                    "tình trạng còn hàng và tạo đơn đặt món."
                ),
                "thought": (
                    "Người dùng chỉ hỏi giới thiệu chức năng, "
                    "không cần gọi Tool."
                )
            }

        # TC04: phải bắt đầu bằng món chính, sau đó mới đồ uống
        if self._is_combo_budget_query(user_query):
            if "query_menu" not in available_tools:
                return {
                    "type": "text",
                    "content": (
                        "Không tìm thấy công cụ query_menu "
                        "trong danh sách Tool hiện tại."
                    ),
                    "thought": (
                        "Không thể tra cứu vì query_menu không được công bố."
                    )
                }

            self._stage = "WAITING_MAIN"

            return {
                "type": "tool_call",
                "tool_name": "query_menu",
                "arguments": {
                    "keyword": "Món chính"
                },
                "thought": (
                    "Người dùng cần một phần cơm và một đồ uống "
                    "theo ngân sách. Trước tiên tôi sẽ tra cứu "
                    "danh sách món chính còn hàng."
                )
            }

        # Các yêu cầu đồ ăn còn lại
        has_food_context = any(
            keyword in query_lower
            for keyword in [
                "món",
                "cơm",
                "phở",
                "trà",
                "cà phê",
                "đồ uống",
                "food",
                "drink"
            ]
        ) or bool(
            re.search(
                r"\b(?:food|drink)\d+\b",
                query_lower,
                re.IGNORECASE
            )
        )

        if has_food_context:
            if "query_menu" not in available_tools:
                return {
                    "type": "text",
                    "content": (
                        "Không tìm thấy công cụ query_menu "
                        "trong danh sách Tool hiện tại."
                    ),
                    "thought": (
                        "Không thể tra cứu vì query_menu không được công bố."
                    )
                }

            keyword = self._extract_keyword(user_query)
            self._stage = "WAITING_QUERY"

            return {
                "type": "tool_call",
                "tool_name": "query_menu",
                "arguments": {
                    "keyword": keyword
                },
                "thought": (
                    f"Người dùng đang hỏi về món ăn. "
                    f"Tôi sẽ gọi query_menu với từ khóa '{keyword}'."
                )
            }

        # Không thuộc nghiệp vụ cần Tool
        return {
            "type": "text",
            "content": (
                "[Mock Agent Response]: Tôi là Trợ lý Quản lý Đơn giao đồ ăn. "
                "Bạn có thể yêu cầu tôi tra cứu món hoặc đặt món."
            ),
            "thought": (
                "Câu hỏi không yêu cầu tra cứu hay tạo đơn, "
                "nên trả lời trực tiếp."
            )
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-3.6-flash"
        self._mock_fallback = MockOfflineProvider()

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return (
                "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! "
                "Đang sử dụng chế độ Mock."
            )

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

            return response.text

        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print(
                "ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. "
                "Tự động chuyển sang Mock Offline."
            )

            return self._mock_fallback.generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            function_declarations = []

            for tool in tools_schema:
                if not tool.get("name") or not tool.get("parameters"):
                    continue

                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[
                    {
                        "function_declarations": function_declarations
                    }
                ] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, "args") and call.args else {}

                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": (
                        f"Gemini quyết định gọi công cụ '{call.name}' "
                        f"với tham số: {json.dumps(args, ensure_ascii=False)}"
                    )
                }

            return {
                "type": "text",
                "content": response.text or "",
                "thought": (
                    "Gemini phản hồi trực tiếp bằng văn bản "
                    "(không cần gọi công cụ)."
                )
            }

        except Exception as e:
            print(
                f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). "
                "Tự động fallback về Mock."
            )

            return self._mock_fallback.generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        self._mock_fallback = MockOfflineProvider()

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return (
                "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! "
                "Đang sử dụng chế độ Mock."
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:

        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print(
                "ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. "
                "Tự động chuyển sang Mock Offline."
            )

            return self._mock_fallback.generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            tools = []

            for tool in tools_schema:
                if not tool.get("name"):
                    continue

                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                call = msg.tool_calls[0]

                args = (
                    json.loads(call.function.arguments)
                    if call.function.arguments
                    else {}
                )

                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": (
                        f"OpenAI quyết định gọi công cụ '{call.function.name}' "
                        f"với tham số: {json.dumps(args, ensure_ascii=False)}"
                    )
                }

            return {
                "type": "text",
                "content": msg.content or "",
                "thought": (
                    "OpenAI phản hồi trực tiếp bằng văn bản "
                    "(không cần gọi công cụ)."
                )
            }

        except Exception as e:
            print(
                f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). "
                "Tự động fallback về Mock."
            )

            return self._mock_fallback.generate_with_tools(
                prompt,
                tools_schema,
                system_prompt
            )


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable."""

    provider_type = os.getenv(
        "LLM_PROVIDER",
        "gemini"
    ).lower()

    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")

        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()

        return MockOfflineProvider()

    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")

        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()

        return MockOfflineProvider()

    elif provider_type == "mock":
        return MockOfflineProvider()

    else:
        return MockOfflineProvider()
