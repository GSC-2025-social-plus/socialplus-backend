# functions/main.py

# --- 1. 필요한 Import 문들 ---
import firebase_functions.https_fn as https_fn
import firebase_admin
# firebase_admin.firestore는 firestore_service에서 임포트하므로 여기서는 필요 없습니다.
import json
# textwrap는 chatbot_service에서 임포트하므로 여기서는 필요 없습니다.
import google.generativeai as genai # Gemini API 사용
import os # 환경 변수 사용
import datetime # 타임스탬프 등 필요 시 사용

# --- 로컬 모듈 임포트 (상대 경로 임포트 문제 해결) ---
# 같은 디렉토리에 있는 모듈은 이렇게 임포트합니다.
import firestore_service # firestore_service.py 파일이 같은 디렉토리에 있어야 합니다.
import chatbot_service # chatbot_service.py 파일이 같은 디렉토리에 있어야 합니다.


# --- 2. Firebase Admin SDK 초기화 (함수 밖, 모듈 로드 시점) ---
# Firestore 서비스에서도 이 초기화된 앱을 사용합니다.
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

# --- 4. 챗봇 핵심 로직 함수들 (수정 완료됨) ---
# 이 함수들은 firestore_service를 직접 사용하지 않습니다.
# call_gemini_api, clean_json_string, get_chatbot_response, analyze_user_input_with_ai, update_mission_status
# 이 함수들은 리팩토링 다음 단계에서 chatbot_service.py로 완전히 분리될 예정입니다.
# 현재는 main.py에 있다고 가정하고 sendMessage에서 호출합니다.
# 따라서 이 부분에 해당 함수들의 실제 코드가 정의되어 있어야 합니다.
# (이 코드는 이전 대화에서 제공된 수정된 함수 정의를 포함해야 합니다.)

# --- CORS 헤더 추가 헬퍼 함수 ---
# 모든 응답에 이 함수를 호출하여 CORS 헤더를 추가합니다.
def add_cors_headers(response: https_fn.Response):
    """
    HTTP 응답에 CORS(Cross-Origin Resource Sharing) 헤더를 추가합니다.
    개발 단계에서는 모든 출처를 허용하고, 운영 환경에서는 프론트엔드 출처만 허용하도록 변경해야 합니다.
    """
    # --- 운영 환경 배포 시에는 '*' 대신 프론트엔드의 실제 출처(Origin)를 명시해야 합니다! ---
    # 예: response.headers['Access-Control-Allow-Origin'] = 'https://your-frontend-domain.com'
    # 여러 출처를 허용해야 한다면 요청의 Origin 헤더 값을 읽어와 허용된 목록에 있는지 확인 후 해당 Origin을 Access-Control-Allow-Origin 값으로 설정해야 합니다.
    # 현재는 개발 편의를 위해 모든 출처 허용 (*)
    response.headers['Access-Control-Allow-Origin'] = '*'

    # 허용할 HTTP 메서드
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'

    # 허용할 HTTP 헤더 (프론트엔드 요청에서 Content-Type 등을 보낼 경우 필요)
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type' # 필요한 다른 헤더도 추가

    # 프리플라이트 응답 캐시 시간 (초 단위)
    response.headers['Access-Control-Max-Age'] = '3600' # 브라우저가 프리플라이트 응답을 1시간 캐시

    return response

# --- 6. HTTP 트리거 함수 - startConversation (수정: CORS 헤더 추가) ---
@https_fn.on_request()
def startConversation(req: https_fn.Request):
    """
    새로운 대화 세션을 시작하는 Cloud Function.
    """
    # --- CORS: 프리플라이트(OPTIONS) 요청 처리 ---
    if req.method == 'OPTIONS':
        # OPTIONS 요청에는 응답 본문 없이 204 상태 코드를 반환하는 것이 일반적입니다.
        response = https_fn.Response("", status=204)
        return add_cors_headers(response) # OPTIONS 응답에도 CORS 헤더 추가!

    # --- POST 요청 확인 ---
    if req.method != 'POST':
        response = https_fn.Response("Method Not Allowed", status=405)
        return add_cors_headers(response) # 405 응답에도 CORS 헤더 추가!

    # --- 함수 본래 로직 (요청 파싱, 시나리오 로드, 세션 생성 등) ---
    try:
        # --- 요청 데이터 파싱 및 추출 ---
        request_data = req.get_json()
        if not request_data:
            print("Error: No JSON data provided in request body.")
            response = https_fn.Response("No JSON data provided", status=400)
            return add_cors_headers(response) # 400 응답에도 CORS 헤더 추가!

        user_id = request_data.get('userId')
        scenario_id_from_request = request_data.get('scenario') # 요청에서 받은 시나리오 ID

        if not user_id or not scenario_id_from_request:
            print("Error: Missing userId or scenario in request body.")
            response = https_fn.Response("Missing userId or scenario in request body", status=400)
            return add_cors_headers(response) # 400 응답에도 CORS 헤더 추가!

        # --- FirestoreService를 통해 시나리오 정보 불러오기 ---
        try:
            scenario_data = firestore_service.get_scenario(scenario_id_from_request) # <-- firestore_service 함수 호출

            if scenario_data is None: # 문서가 없으면 firestore_service에서 None 반환
                print(f"Error: Scenario document '{scenario_id_from_request}' not found.")
                response = https_fn.Response(f"Scenario '{scenario_id_from_request}' not found.", status=404)
                return add_cors_headers(response) # 404 응답에도 CORS 헤더 추가!

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
                 response = https_fn.Response(f"Invalid scenario data for '{scenario_id_from_request}'. Check 'system_instruction', 'initial_missions', 'analysis_criteria'.", status=500)
                 return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!


        except Exception as e: # <--- firestore_service 함수 호출 중 발생한 예외 처리
            print(f"Error calling firestore_service.get_scenario or processing data: {e}")
            response = https_fn.Response(f"Error reading scenario data for '{scenario_id_from_request}'.", status=500)
            return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!

                                    
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
            response = https_fn.Response("Error creating new session.", status=500)
            return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!


        # --- 프론트엔드 응답 구성 ---
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

        # --- JSON 응답 반환 (CORS 헤더 추가!) ---
        try:
            response = https_fn.Response(json.dumps(response_data), mimetype="application/json")
            return add_cors_headers(response) # <-- 여기에서 CORS 헤더 추가!
        except Exception as e:
            print(f"Error composing final response (startConversation): {e}")
            response = https_fn.Response("An internal server error occurred while formatting response.", status=500)
            return add_cors_headers(response) # <-- 오류 응답에도 CORS 헤더 추가!

    except Exception as e: # <--- 가장 바깥쪽 try 블록에 대한 except (예상치 못한 오류)
        print(f"Cloud Function 실행 중 예상치 못한 오류 (startConversation): {e}")
        response = https_fn.Response("An internal server error occurred during session creation.", status=500)
        return add_cors_headers(response) # <-- 오류 응답에도 CORS 헤더 추가!


# --- 5. HTTP 트리거 함수 - sendMessage (수정: CORS 헤더 추가) ---
@https_fn.on_request()
def sendMessage(req: https_fn.Request):
    """
    사용자 메시지를 받아 챗봇 응답을 생성하고 반환하는 Cloud Function
    """
    # --- CORS: 프리플라이트(OPTIONS) 요청 처리 ---
    if req.method == 'OPTIONS':
        response = https_fn.Response("", status=204) # 204 No Content
        return add_cors_headers(response) # OPTIONS 응답에도 CORS 헤더 추가!

    # --- POST 요청 확인 ---
    if req.method != 'POST':
        response = https_fn.Response("Method Not Allowed", status=405)
        return add_cors_headers(response) # 405 응답에도 CORS 헤더 추가!

    # 5-2. API 키 체크 (함수 안)
    if not API_KEY:
         print("Error: API_KEY is not set. Cannot process message.")
         response = https_fn.Response("Internal Server Error: API key not configured.", status=500)
         return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!

    # --- 함수 본래 로직 (요청 파싱, 세션 로드, 챗봇 로직 수행 등) ---
    try:
        # 5-3. 요청 데이터 파싱 및 추출
        request_data = req.get_json()
        if not request_data:
            response = https_fn.Response("No JSON data provided", status=400)
            return add_cors_headers(response) # 400 응답에도 CORS 헤더 추가!

        user_id = request_data.get('userId')
        session_id = request_data.get('sessionId')
        user_message = request_data.get('message')

        if not user_id or not session_id or not user_message:
             print("Error: Missing userId, sessionId, or message in request body")
             response = https_fn.Response("Missing userId, sessionId, or message in request body", status=400)
             return add_cors_headers(response) # 400 응답에도 CORS 헤더 추가!

        # --- FirestoreService를 통해 세션 데이터 읽어오기 (시나리오 데이터 포함!) ---
        try:
            session_data = firestore_service.get_session(session_id) # <-- firestore_service 함수 호출

            if session_data is None: # 문서가 없으면 firestore_service에서 None 반환
                print(f"Error: Session document {session_id} not found for user {user_id}.")
                response = https_fn.Response("Invalid session ID.", status=404)
                return add_cors_headers(response) # 404 응답에도 CORS 헤더 추가!

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
                 response = https_fn.Response(f"Invalid session data for '{session_id}'. Missing scenario details.", status=500)
                 return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!


        except Exception as e: # <--- firestore_service 함수 호출 중 발생한 예외 처리
            print(f"Error calling firestore_service.get_session or processing data: {e}")
            response = https_fn.Response("Error reading session data.", status=500)
            return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!


        # 5-5. 불러온 데이터 활용하여 챗봇 로직 수행 및 상태 업데이트
        # 사용자의 현재 메시지를 대화 기록에 추가 (Firestore 저장 전)
        updated_history = conversation_history + [{'role': 'user', 'parts': [user_message]}]

        # 챗봇 응답 생성 (업데이트된 history 사용, 시나리오 system_instruction 전달)
        # get_chatbot_response 함수는 chatbot_service에 있다고 가정
        # TODO: chatbot_service.py 파일에 이 함수가 정의되어 있어야 합니다.
        model_response_text = chatbot_service.get_chatbot_response(user_message, updated_history, system_instruction)


        # 봇 응답을 history에 추가 (Firestore 저장 전)
        if model_response_text and not model_response_text.startswith("죄송해요"):
             updated_history.append({'role': 'model', 'parts': [model_response_text]})


        # 사용자 입력 분석 (시나리오 analysis_criteria 전달)
        # analyze_user_input_with_ai 함수는 chatbot_service에 있다고 가정
        # TODO: chatbot_service.py 파일에 이 함수가 정의되어 있어야 합니다.
        analysis_result = chatbot_service.analyze_user_input_with_ai(user_message, analysis_criteria, session_data.get('system_instruction',''))


        # 미션 상태 업데이트 (현재 미션 상태, 분석 결과 전달)
        # update_mission_status 함수는 chatbot_service에 있다고 가정
        # TODO: chatbot_service.py 파일에 이 함수가 정의되어 있어야 합니다.
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
            response = https_fn.Response("Error updating session data.", status=500)
            return add_cors_headers(response) # 500 응답에도 CORS 헤더 추가!


        # 5-7. 프론트엔드 응답 구성 및 반환
        response_data = {
            "botMessage": model_response_text,
            "sessionStatus": updated_session_status,
            "completedMissions": newly_completed_missions,
        }

        try:
            response = https_fn.Response(json.dumps(response_data), mimetype="application/json")
            return add_cors_headers(response) # <-- 여기에서 CORS 헤더 추가!
        except Exception as e:
            print(f"Error composing final response: {e}")
            response = https_fn.Response("An internal server error occurred while formatting response.", status=500)
            return add_cors_headers(response) # <-- 오류 응답에도 CORS 헤더 추가!

    except Exception as e: # <--- 가장 바깥쪽 try 블록에 대한 except
        print(f"Cloud Function 실행 중 예상치 못한 오류: {e}")
        response = https_fn.Response("An internal server error occurred during message processing.", status=500)
        return add_cors_headers(response) # <-- 오류 응답에도 CORS 헤더 추가!
