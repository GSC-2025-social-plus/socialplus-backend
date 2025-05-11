# functions/main.py

# --- 1. 필요한 Import 문들 ---
# --- Firestore 서비스 임포트 ---
import firestore_service
# --- 챗봇 서비스 임포트 ---
import chatbot_service

import firebase_functions.https_fn as https_fn
import firebase_admin
import json
import google.generativeai as genai # Gemini API 사용
import os # 환경 변수 사용
import datetime # 타임스탬프 등 필요 시 사용

# --- 2. Firebase Admin SDK 초기화 (함수 밖, 모듈 로드 시점) ---
try:
    firebase_admin.initialize_app()
except Exception:
    pass  # 이미 초기화된 경우 무시

# --- 3. Gemini API 설정 (함수 밖, 모듈 로드 시점) ---
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        API_KEY = None
else:
    print("Error: GEMINI_API_KEY environment variable not set.")

# functions/main.py

# ... (다른 import 문들 및 함수들 - call_gemini_api, clean_json_string 등은 그대로 둡니다)

# --- 6. HTTP 트리거 함수 - startConversation (수정: firestore_service 사용) ---
@https_fn.on_request()
def startConversation(req: https_fn.Request):
    """
    새로운 대화 세션을 시작하는 Cloud Function.
    요청 본문에 userId, scenario 등을 포함하고,
    새 세션 ID와 초기 상태를 Firestore에 저장 후 반환합니다.
    """
    # --- Firestore 클라이언트 초기화는 firestore_service 내부에서 처리하거나,
    #     Admin SDK 초기화가 되어 있으면 firestore_service가 사용합니다.
    #     여기서는 직접 db 클라이언트를 초기화하지 않습니다.

    # --- POST 요청 확인 ---
    if req.method != 'POST':
        return https_fn.Response("Method Not Allowed", status=405)

    # --- 함수 전체의 핵심 로직을 감싸는 가장 바깥쪽 try 블록 시작 ---
    try:
        # --- 요청 데이터 파싱 및 추출 ---
        request_data = req.get_json()
        if not request_data:
            print("Error: No JSON data provided in request body.")
            return https_fn.Response("No JSON data provided", status=400)

        user_id = request_data.get('userId')
        scenario_id_from_request = request_data.get('scenario') # 요청에서 받은 시나리오 ID

        if not user_id or not scenario_id_from_request:
            print("Error: Missing userId or scenario in request body.")
            return https_fn.Response("Missing userId or scenario in request body", status=400)

        # --- FirestoreService를 통해 시나리오 정보 불러오기 ---
        try:
            scenario_data = firestore_service.get_scenario(scenario_id_from_request) # <-- firestore_service 함수 호출

            if scenario_data is None: # 문서가 없으면 firestore_service에서 None 반환
                print(f"Error: Scenario document '{scenario_id_from_request}' not found.")
                return https_fn.Response(f"Scenario '{scenario_id_from_request}' not found.", status=404)

            # --- 시나리오 데이터에서 필요한 정보 추출 및 유효성 검사 ---
            # 시나리오 문서에 필수 필드가 모두 있는지 확인
            system_instruction = scenario_data.get('system_instruction')
            initial_missions_from_scenario = scenario_data.get('initial_missions')
            analysis_criteria_from_scenario = scenario_data.get('analysis_criteria')
            # 새로 추가된 필드 (필수는 아니지만 불러옵니다)
            name_korean = scenario_data.get('name_korean', scenario_id_from_request)
            description_for_user = scenario_data.get('description_for_user', '시나리오 설명이 없습니다.')
            bot_initial_message = scenario_data.get('bot_initial_message', '안녕하세요!')

            # 필수 필드가 누락된 경우 오류
            if not system_instruction or not isinstance(initial_missions_from_scenario, dict) or not isinstance(analysis_criteria_from_scenario, dict):
                 print(f"Error: Missing or invalid essential fields in scenario document '{scenario_id_from_request}'.")
                 return https_fn.Response(f"Invalid scenario data for '{scenario_id_from_request}'. Check 'system_instruction', 'initial_missions', 'analysis_criteria'.", status=500)


        except Exception as e: # <--- firestore_service 함수 호출 중 발생한 예외 처리
            print(f"Error calling firestore_service.get_scenario or processing data: {e}")
            return https_fn.Response(f"Error reading scenario data for '{scenario_id_from_request}'.", status=500)


        # --- 초기 세션 데이터 구성 (불러온 시나리오 데이터 활용) ---
        # 세션 문서에 저장할 초기 데이터
        initial_session_data = {
            'userId': user_id,
            'scenarioId': scenario_id_from_request,
            'scenarioName': name_korean,
            'scenarioDescription': description_for_user,
            'history': [],

            # 시나리오에서 불러온 initial_missions 정보를 기반으로 세션의 missions 상태 구성
            'missions': {
                mission_id: {
                    "description": mission_details.get("description", ""),
                    "completed": False,
                    "stampImageId": mission_details.get("stampImageId", "stamp_initial"),
                } for mission_id, mission_details in initial_missions_from_scenario.items()
            },

            'status': 'active',
            'startTime': datetime.datetime.now(datetime.timezone.utc).isoformat(),

            # AI 분석 기준 및 시스템 지침도 세션 데이터에 함께 저장 (sendMessage에서 사용)
            'analysis_criteria': analysis_criteria_from_scenario,
            'system_instruction': system_instruction,

            # 챗봇 첫 메시지 저장 (startConversation 응답 시 반환)
            'botInitialMessage': bot_initial_message
        }

        # --- FirestoreService를 통해 초기 세션 데이터 생성 ---
        try:
            new_session_id = firestore_service.create_session(initial_session_data) # <-- firestore_service 함수 호출
            print(f"New session {new_session_id} created for user {user_id} with scenario '{scenario_id_from_request}'.")

        except Exception as e: # <--- firestore_service 함수 호출 중 발생한 예외 처리
            print(f"Error calling firestore_service.create_session: {e}")
            return https_fn.Response("Error creating new session.", status=500)


        # --- 프론트엔드 응답 구성 및 반환 ---
        response_data = {
            "sessionId": new_session_id,
            "botInitialMessage": initial_session_data['botInitialMessage'],
            "initialStatus": {
                 "userId": initial_session_data['userId'],
                 "scenarioId": initial_session_data['scenarioId'],
                 "scenarioName": initial_session_data['scenarioName'],
                 "scenarioDescription": initial_session_data['scenarioDescription'],
                 "missions": initial_session_data['missions'],
                 "status": initial_session_data['status'],
                 "startTime": initial_session_data['startTime'],
            }
        }
        try:
            return https_fn.Response(json.dumps(response_data), mimetype="application/json")
        except Exception as e:
            print(f"Error composing final response (startConversation): {e}")
            return https_fn.Response("An internal server error occurred while formatting response.", status=500)

    except Exception as e: # <--- 가장 바깥쪽 try 블록에 대한 except (예상치 못한 오류)
        print(f"Cloud Function 실행 중 예상치 못한 오류 (startConversation): {e}")
        return https_fn.Response("An internal server error occurred during session creation.", status=500)

# --- 5. HTTP 트리거 함수 - sendMessage (수정: firestore_service 사용) ---
@https_fn.on_request()
def sendMessage(req: https_fn.Request):
    """
    사용자 메시지를 받아 챗봇 응답을 생성하고 반환하는 Cloud Function
    프론트엔트로부터 POST 요청을 받습니다.
    요청 본문에 userId, sessionId, message를 포함해야 합니다.
    """
    # --- Firestore 클라이언트 초기화는 firestore_service 내부에서 처리합니다.
    #     여기서는 직접 db 클라이언트를 초기화하지 않습니다.

    # 5-2. API 키 체크 (함수 안)
    if not API_KEY:
         print("Error: API_KEY is not set. Cannot process message.")
         return https_fn.Response("Internal Server Error: API key not configured.", status=500)

    # 5-3. 요청 데이터 파싱 및 추출
    if req.method != 'POST':
        return https_fn.Response("Method Not Allowed", status=405)

    try:
        request_data = req.get_json()
        if not request_data:
            return https_fn.Response("No JSON data provided", status=400)

        user_id = request_data.get('userId')
        session_id = request_data.get('sessionId')
        user_message = request_data.get('message')

        if not user_id or not session_id or not user_message:
             print("Error: Missing userId, sessionId, or message in request body")
             return https_fn.Response("Missing userId, sessionId, or message in request body", status=400)
    except Exception as e:
        print(f"Request parsing error: {e}")
        return https_fn.Response("Invalid request format.", status=400)


    # --- FirestoreService를 통해 세션 데이터 읽어오기 (시나리오 데이터 포함!) ---
    try:
        session_data = firestore_service.get_session(session_id) # <-- firestore_service 함수 호출

        if session_data is None: # 문서가 없으면 firestore_service에서 None 반환
            print(f"Error: Session document {session_id} not found for user {user_id}.")
            return https_fn.Response("Invalid session ID.", status=404)

        # 필요한 필드가 있는지 확인 및 불러오기 (startConversation에서 이 구조를 보장했어야 합니다)
        conversation_history = session_data.get('history', [])
        mission_status = session_data.get('missions', {})
        session_status = session_data.get('status', 'active')
        scenario_id_from_session = session_data.get('scenarioId', 'unknown_scenario')

        # --- 시나리오 데이터 불러오기 (세션 문서에 저장된 것 사용) ---
        # startConversation에서 이 필드들이 저장되었다고 가정합니다.
        system_instruction = session_data.get('system_instruction')
        analysis_criteria = session_data.get('analysis_criteria')
        # scenarioName, scenarioDescription 등 다른 필드도 필요시 불러오기


        # 시나리오 데이터 필수 필드 유효성 검사 (startConversation에서 저장했어야 함)
        if not system_instruction or not isinstance(analysis_criteria, dict):
             print(f"Error: Missing or invalid scenario data in session document {session_id}. Scenario ID: {scenario_id_from_session}")
             return https_fn.Response(f"Invalid session data for '{session_id}'. Missing scenario details.", status=500)


    except Exception as e: # <--- firestore_service 함수 호출 중 발생한 예외 처리
        print(f"Error calling firestore_service.get_session or processing data: {e}")
        return https_fn.Response("Error reading session data.", status=500)


    # 5-5. 불러온 데이터 활용하여 챗봇 로직 수행 및 상태 업데이트
    # 사용자의 현재 메시지를 대화 기록에 추가 (Firestore 저장 전)
    updated_history = conversation_history + [{'role': 'user', 'parts': [user_message]}]

    # 챗봇 응답 생성 (업데이트된 history 사용, 시나리오 system_instruction 전달)
    # get_chatbot_response 함수 시그니처 변경 필요 없음 (이미 수정 완료)
    model_response_text = chatbot_service.get_chatbot_response(user_message, updated_history, system_instruction)


    # 봇 응답을 history에 추가 (Firestore 저장 전)
    if model_response_text and not model_response_text.startswith("죄송해요"):
         updated_history.append({'role': 'model', 'parts': [model_response_text]})


    # 사용자 입력 분석 (시나리오 analysis_criteria 전달)
    # analyze_user_input_with_ai 함수 시그니처 변경 필요 없음 (이미 수정 완료)
    analysis_result = chatbot_service.analyze_user_input_with_ai(user_message, analysis_criteria)


    # 미션 상태 업데이트 (현재 미션 상태, 분석 결과 전달)
    # update_mission_status 함수 시그니처 변경 필요 없음 (이미 수정 완료)
    updated_mission_status, newly_completed_missions = chatbot_service.update_mission_status(mission_status, analysis_result)


    # 세션 종료 조건 체크 (analysis_result에 termination_requested 있음)
    updated_session_status = session_status
    if analysis_result.get("termination_requested"):
        updated_session_status = 'ended'


    # 5-6. 업데이트된 상태를 FirestoreService를 통해 저장
    # history와 missions, status만 업데이트합니다.
    updated_session_data = {
         'history': updated_history,
         'missions': updated_mission_status,
         'status': updated_session_status,
    }
    # 세션 상태가 'ended'로 변경되면 종료 시간 기록
    if updated_session_status == 'ended' and session_status != 'ended':
        updated_session_data['endTime'] = datetime.datetime.now(datetime.timezone.utc)

    try:
        firestore_service.update_session(session_id, updated_session_data) # <-- firestore_service 함수 호출
        print(f"Session {session_id} data updated in Firestore. Status: {updated_session_status}, Completed Missions: {newly_completed_missions}")
    except Exception as e: # <--- firestore_service 함수 호출 중 발생한 예외 처리
        print(f"Error calling firestore_service.update_session: {e}")
        return https_fn.Response("Error updating session data.", status=500)


    # 5-7. 프론트엔드 응답 구성 및 반환
    response_data = {
        "botMessage": model_response_text,
        "sessionStatus": updated_session_status,
        "completedMissions": newly_completed_missions,
    }

    try:
        return https_fn.Response(json.dumps(response_data), mimetype="application/json")
    except Exception as e:
        print(f"Error composing final response: {e}")
        return https_fn.Response("An internal server error occurred while formatting response.", status=500)