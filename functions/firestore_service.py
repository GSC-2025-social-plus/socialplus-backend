# functions/firestore_service.py

import firebase_admin
import firebase_admin.firestore
import datetime # 필요시 사용

# Firestore 클라이언트 인스턴스를 함수 호출 시마다 생성하지 않고,
# 모듈 레벨에서 필요할 때 한 번만 생성하거나, 함수의 컨텍스트에서 관리하는 방식이 효율적일 수 있습니다.
# 여기서는 함수 호출 시 초기화 또는 캐시된 인스턴스 사용 방식을 따릅니다.

def get_firestore_client():
    """Firestore 클라이언트 인스턴스를 반환"""
    try:
        # Firebase Admin SDK가 초기화되어 있다면 클라이언트 반환
        # 초기화는 main.py 등 앱 시작 시 한 번만 수행되어야 합니다.
        return firebase_admin.firestore.client()
    except ValueError:
        # 아직 초기화되지 않았다면 오류 발생 (main.py에서 초기화 필수)
        print("Firebase Admin SDK has not been initialized.")
        raise # 초기화되지 않았으면 진행할 수 없으므로 예외 발생

def get_scenario(scenario_id: str):
    """
    Firestore에서 시나리오 문서를 불러와 반환
    """
    db = get_firestore_client()
    scenario_doc_ref = db.collection('scenarios').document(scenario_id)
    scenario_doc = scenario_doc_ref.get()

    if not scenario_doc.exists:
        return None # 문서가 없으면 None 반환

    return scenario_doc.to_dict()

def get_session(session_id: str):
    """
    Firestore에서 세션 문서를 불러와 반환
    """
    db = get_firestore_client()
    session_doc_ref = db.collection('sessions').document(session_id)
    session_doc = session_doc_ref.get()

    if not session_doc.exists:
        return None # 문서가 없으면 None 반환

    return session_doc.to_dict()

def create_session(initial_session_data: dict):
    """
    Firestore에 새로운 세션 문서를 생성하고 문서 ID를 반환
    """
    db = get_firestore_client()
    new_session_ref = db.collection('sessions').document()
    new_session_id = new_session_ref.id

    # startConversation에서 이미 데이터 유효성 검사를 거친 데이터라고 가정
    new_session_ref.set(initial_session_data, merge=False) # 새 문서이므로 merge=False

    return new_session_id

def update_session(session_id: str, updated_session_data: dict):
    """
    Firestore의 기존 세션 문서를 업데이트
    """
    db = get_firestore_client()
    session_doc_ref = db.collection('sessions').document(session_id)

    # startConversation에서 이미 데이터 유효성 검사를 거친 데이터라고 가정
    session_doc_ref.update(updated_session_data) # 기존 문서 업데이트


# 필요하다면 세션 기록 추가, 미션 상태 업데이트 등 더 세분화된 함수를 추가할 수 있습니다.
# 하지만 일단은 startConversation/sendMessage에서 호출할 상위 함수들 위주로 만듭니다.