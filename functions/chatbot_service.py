# functions/chatbot_service.py

# --- 1. 필요한 Import 문들 ---
import google.generativeai as genai # Gemini API 사용
import json
import textwrap
import os # API 키 체크 등에 필요
import datetime # 타임스탬프 등 필요 시 사용

# API_KEY는 main.py에서 설정되어 genai.configure()가 호출된다고 가정합니다.
# 하지만 안전성을 위해 서비스 함수 내부에서 API_KEY 전역 변수를 체크하는 것이 좋습니다.
API_KEY = os.getenv("GEMINI_API_KEY") # 여기서 다시 로드하거나 main.py에서 설정된 것을 사용


# --- 2. 챗봇 핵심 로직 함수들 ---

# call_gemini_api 함수
def call_gemini_api(prompt: str, model_instance):
    """
    Gemini API를 호출하고 응답 텍스트를 반환하는 함수.
    오류 처리를 포함합니다.
    """
    # API_KEY = os.getenv("GEMINI_API_KEY") # 필요시 여기서 다시 로드
    if not API_KEY:
        print("Warning: Cannot call Gemini API - API key not available in chatbot_service.")
        return None
    try:
        # model_instance는 genai.GenerativeModel 객체
        response = model_instance.generate_content(prompt) # 단일 프롬프트 전달
        if hasattr(response, 'text') and response.text:
            return response.text
        # API 차단 피드백 확인
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            print(f"API 차단: {response.prompt_feedback.block_reason}")
            return None
        return None
    except Exception as e:
        print(f"Gemini API 호출 오류 (call_gemini_api): {e}")
        return None


# clean_json_string 함수
def clean_json_string(text: str) -> str:
    """
    Gemini 응답에서 JSON 문자열만 추출하고 코드 블록 표식을 제거하는 함수.
    """
    try:
        t = text.strip()
        if t.startswith('```json'):
            t = t[len('```json'):].strip()
        if t.startswith('```'):
            t = t[3:].strip()
        if t.endswith('```'):
            t = t[:-3].strip()
        return t.strip()
    except Exception as e:
        print(f"Error cleaning JSON string: {e}")
        return text


# get_chatbot_response 함수
def get_chatbot_response(user_message: str, conversation_history: list, system_instruction: str):
    """
    대화 기록, 사용자 메시지, 시나리오별 시스템 지침을 바탕으로 챗봇 응답 생성
    """
    # API_KEY = os.getenv("GEMINI_API_KEY") # 필요시 여기서 다시 로드
    if not API_KEY:
        print("Warning: Cannot generate chatbot response - API key not available in chatbot_service.")
        return "죄송해요, 지금은 대화할 수 없습니다 (API 설정 오류)."
    if not system_instruction:
         print("Error: system_instruction is missing for chatbot response.")
         return "죄송해요, 챗봇 설정 오류로 대화할 수 없습니다."

    try:
        # 모델 인스턴스 생성 (전달받은 system_instruction 사용)
        chat_model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=system_instruction
        )
        contents = conversation_history + [{'role': 'user', 'parts': [user_message]}]

        # print(f"Contents sent to generate_content (inside get_chatbot_response): {contents}") # 로그 너무 길면 주석 처리

        response = chat_model.generate_content(contents)

        # 응답 텍스트 확인 및 반환
        if hasattr(response, 'text') and response.text:
             return response.text
        # API 차단 피드백 확인
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
             print(f"API 차단: {response.prompt_feedback.block_reason}")
             return "죄송해요, 부적절한 내용이 감지되어 답변할 수 없습니다."

        return "" # 유효한 응답 텍스트가 없는 경우 빈 문자열 반환

    except Exception as e:
        print(f"Error generating chatbot response: {e}")
        return "죄송해요, 답변 생성 중 오류가 발생했습니다."


# analyze_user_input_with_ai 함수
def analyze_user_input_with_ai(user_input: str, analysis_criteria: dict):
    """
    사용자 입력을 분석하여 미션 완료, 종료 요청 여부 판단
    시나리오별 analysis_criteria를 참고하여 동적으로 판단합니다.
    """
    # API_KEY = os.getenv("GEMINI_API_KEY") # 필요시 여기서 다시 로드
    if not API_KEY:
        print("Warning: Gemini API key not available for analysis in chatbot_service.")
        return {"termination_requested": False} # API 키 없으면 분석 불가, 종료 요청 False 반환

    # analysis_criteria 딕셔너리의 필수 키 확인 및 기본값 설정
    if not isinstance(analysis_criteria, dict):
        print(f"Error: analysis_criteria is not a dictionary. Type: {type(analysis_criteria)}")
        return {"termination_requested": False}

    mission_keywords_criteria = {
        key: value for key, value in analysis_criteria.items()
        if key.endswith("_keywords") and isinstance(value, list)
    }
    termination_keywords = analysis_criteria.get("termination_keywords", [])
    if not isinstance(termination_keywords, list):
         termination_keywords = []


    # AI 분석 프롬프트 구성
    json_fields = {}
    criteria_description_lines = []

    for mission_keyword_field, keywords in mission_keywords_criteria.items():
        mission_id = mission_keyword_field.replace("_keywords", "")
        json_result_field_name = f"completes_{mission_id}"
        json_fields[json_result_field_name] = "boolean"
        criteria_description_lines.append(f"- Completes mission '{mission_id}': Does the input express meaning related to {keywords}? If yes, set '{json_result_field_name}' to true.")

    json_fields["termination_requested"] = "boolean"
    criteria_description_lines.append(f"- Termination requested: Does the input express a clear intent to end the conversation (e.g., saying goodbye)? Keywords like {termination_keywords} might be relevant. If yes, set 'termination_requested' to true.")

    json_format_string = json.dumps(json_fields, indent=2).replace('": "boolean"', '": boolean')
    criteria_description = "\n".join(criteria_description_lines)

    analysis_prompt = textwrap.dedent(f"""
        Analyze the user's last input based on the following criteria and respond only in the specified JSON format.
        ```json
        {json_format_string}
        ```
        Criteria to check:
        {criteria_description}

        User input: "{user_input}"
        Only respond with the JSON object. Do not include any preamble or additional text.
    """)

    # 기본 분석 결과 딕셔너리 구성 (AI 응답 파싱 실패 시 사용)
    default_analysis_result = {key: False for key in json_fields.keys()}


    try:
        # 분석 AI 모델 (system_instruction 고정)
        analysis_model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction="You are a helpful assistant that analyzes user input for a conversational AI application. Respond strictly in the requested JSON format. Do not include any preamble or additional text."
        )
        raw = analysis_model.generate_content([{'role':'user','parts':[analysis_prompt]}])

        raw_text = raw.text if hasattr(raw,'text') else ''
        cleaned_json = clean_json_string(raw_text)

        try:
             data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
             print(f"Error decoding analysis JSON: {e}. Raw response: {raw_text}")
             return default_analysis_result
        except Exception as e:
             print(f"Unexpected error during JSON parsing: {e}. Raw response: {raw_text}")
             return default_analysis_result

        result = {}
        for key in json_fields.keys():
             result[key] = data.get(key, False)

        return result

    except Exception as e:
        print(f"Error during analysis: {e}")
        return default_analysis_result


# update_mission_status 함수
def update_mission_status(current_missions: dict, analysis_result: dict):
    """
    미션 상태 갱신 및 새로 완료된 미션 목록 반환
    analysis_result의 불리언 값과 current_missions 상태를 기반으로 작동합니다.
    analysis_result 필드 이름과 current_missions 미션 ID 간의 연결을 가정합니다.
    """
    updated = current_missions.copy()
    completed = []
    now = datetime.datetime.now(datetime.timezone.utc) # 타임스탬프 미리 가져오기

    # current_missions 딕셔너리 (세션에 저장된 미션 정의)를 순회하면서
    # 각 미션 ID에 해당하는 analysis_result 필드를 확인합니다.
    for mission_id, mission_details in list(updated.items()): # 순회 중 딕셔너리 변경 가능성 고려하여 list()로 복사
        # 해당 미션이 이미 완료 상태가 아니고,
        if mission_details.get("completed") is not True:
             # analysis_result에서 이 미션 ID에 해당하는 완료 플래그의 이름을 구성
             # analyze_user_input_with_ai에서 "completes_" + mission_id 형태로 반환한다고 가정
             analysis_key = f"completes_{mission_id}"

             # analysis_result에 해당 플래그가 있고 그 값이 True이면
             if analysis_result.get(analysis_key) is True:
                  # 미션 완료 상태로 업데이트
                  # 업데이트할 필드만 명시적으로 지정하는 것이 안전
                  if mission_id in updated: # updated 딕셔너리에 미션 ID가 있는지 다시 확인
                      updated[mission_id]["completed"] = True
                      updated[mission_id]["completedTimestamp"] = now # 완료 시 타임스탬프 추가
                      # stampImageId는 이미 startConversation에서 로드되어 current_missions에 있으므로 여기서 변경할 필요 없음
                      completed.append(mission_id) # 새로 완료된 미션 ID 목록에 추가

    return updated, completed