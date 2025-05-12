챗봇 백엔드 시스템 (Cloud Functions + Firestore + Gemini API)
이 프로젝트는 Google Cloud Functions (2세대, Python), Cloud Firestore 데이터베이스, Google Gemini API를 활용하여 상태를 관리하고 시나리오 기반의 대화 및 미션 수행 기능을 제공하는 챗봇 백엔드 시스템입니다.

✨ 주요 기능
세션 관리: 사용자별 대화 세션을 Firestore에 저장하고 관리합니다.
시나리오 기반 대화: Firestore에 정의된 시나리오 데이터를 동적으로 불러와 각 시나리오에 맞는 챗봇 페르소나, 대화 지침, 초기 미션을 설정합니다.
미션 추적 및 완료: 사용자의 입력 내용을 Gemini AI로 분석하여 시나리오별 미션 완료 여부를 판단하고 세션 상태에 반영합니다.
대화 종료 조건: AI 분석을 통해 사용자의 종료 의사를 감지하고 세션을 종료합니다.
모듈화된 코드: Firestore 및 챗봇(AI) 관련 로직을 분리하여 코드의 가독성 및 유지보수성을 높였습니다.

🚀 사용 기술
Google Cloud Functions (2nd gen): 서버리스 함수 실행 환경
Google Cloud Firestore: NoSQL 클라우드 데이터베이스 (세션 및 시나리오 데이터 저장)
Google Gemini API (gemini-2.0-flash): 챗봇 응답 생성 및 사용자 입력 분석
Python 3.12: 백엔드 개발 언어
Firebase Admin SDK (Python): Firestore 접근
Google Generative AI SDK (Python): Gemini API 호출
Firebase CLI: 배포 및 에뮬레이터 실행
📁 프로젝트 구조
functions 디렉토리 안에 소스 코드가 있습니다.

/your-project-root
├── functions
│   ├── .gitignore
│   ├── main.py           # Cloud Functions 진입점 (HTTP 트리거 함수 정의 및 오케스트레이션)
│   ├── firestore_service.py # Firestore 데이터 읽기/쓰기/업데이트 로직
│   ├── chatbot_service.py # Gemini API 호출, 프롬프트 구성, AI 분석 로직
│   └── requirements.txt  # Python 종속성 목록
├── .firebaserc           # Firebase 프로젝트 설정
├── firebase.json         # Firebase 호스팅/Functions 등 설정
└── (기타 프로젝트 파일)

main.py: HTTP 요청(startConversation, sendMessage)을 받아 요청을 파싱하고, firestore_service와 chatbot_service의 함수들을 호출하여 전체 챗봇 로직 흐름을 제어합니다. Firebase Admin SDK 및 Gemini API 초기화도 수행합니다.

firestore_service.py: Cloud Firestore 데이터베이스와의 모든 상호작용(시나리오/세션 읽기, 세션 생성/업데이트)을 담당합니다.

chatbot_service.py: Google Gemini API를 사용한 모든 로직(챗봇 응답 생성, 사용자 입력 분석 프롬프트 구성, 분석 결과 파싱, 미션 상태 업데이트)을 담당합니다.

requirements.txt: 프로젝트에 필요한 파이썬 라이브러리 목록(firebase_admin, google-generativeai, firebase-functions, requests, textwrap 등)을 정의합니다.

🤝 프론트엔드 연동 방법
이 백엔드 시스템은 표준 HTTP API를 통해 프론트엔드 애플리케이션과 통신합니다. 프론트엔드 개발자는 이 백엔드 코드를 직접 실행하거나 빌드할 필요가 없으며, 배포된 Cloud Functions의 URL을 사용하여 비동기적으로 API를 호출하기만 하면 됩니다.

1. Cloud Functions 기본 URL 확인
Google Cloud Functions 콘솔 또는 Firebase 콘솔에서 배포된 startConversation 또는 sendMessage 함수의 트리거 URL을 확인합니다. 두 함수는 동일한 Cloud Functions 인스턴스에 배포되어 있다면 기본 URL 경로가 같을 것입니다. 이 기본 URL을 프론트엔드에서 API 호출 시 사용합니다.

 URL 구조:
https://[REGION]-[PROJECT_ID].cloudfunctions.net/startConversation
https://[REGION]-[PROJECT_ID].cloudfunctions.net/sendMessage

프론트엔드에서는 https://[REGION]-[PROJECT_ID].cloudfunctions.net/ 부분을 기본 URL로 사용하고, 각 엔드포인트(/startConversation, /sendMessage)를 붙여서 호출합니다.

2. API 호출 (JavaScript 예시)
프론트엔드(JavaScript 환경)에서는 Workspace API 등을 사용하여 비동기적으로 백엔드 API를 호출할 수 있습니다.

2.1. 세션 시작 (startConversation 호출)

JavaScript

const baseUrl = "YOUR_CLOUD_FUNCTIONS_BASE_URL"; // 예: "https://us-central1-your-project-id.cloudfunctions.net/"
const userId = "user123"; // 사용자 식별자 (프론트엔드에서 관리)
const scenarioId = "park_friend_scenario"; // 시작할 시나리오 ID (Firestore 문서 ID)

fetch(`${baseUrl}startConversation`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    userId: userId,
    scenario: scenarioId
  })
})
.then(response => {
  if (!response.ok) {
    // 오류 응답 처리
    // 백엔드에서 보낸 오류 메시지를 파싱하여 사용자에게 보여줄 수 있습니다.
    return response.text().then(text => { throw new Error(`HTTP error! status: ${response.status}, message: ${text}`) });
  }
  return response.json();
})
.then(data => {
  console.log("세션 시작 성공:", data);
  const sessionId = data.sessionId;
  const botInitialMessage = data.botInitialMessage;
  const initialStatus = data.initialStatus;

  // 받은 sessionId와 초기 상태 정보를 사용하여 UI 업데이트 및 메시지 전송 준비
  console.log("새 세션 ID:", sessionId);
  console.log("봇 첫 메시지:", botInitialMessage);
  console.log("초기 상태:", initialStatus);

  // 이제 이 sessionId를 사용하여 sendMessage 함수를 호출할 수 있습니다.
})
.catch(error => {
  console.error("세션 시작 중 오류 발생:", error);
  // 오류 메시지를 사용자에게 표시 등
});
2.2. 메시지 전송 (sendMessage 호출)

JavaScript

const baseUrl = "YOUR_CLOUD_FUNCTIONS_BASE_URL"; // 예: "https://us-central1-your-project-id.cloudfunctions.net/"
const userId = "user123"; // 현재 사용자 ID
const currentSessionId = "이전에_startConversation에서_받은_sessionId"; // 현재 활성화된 세션 ID
const userMessage = "사용자가 입력한 메시지"; // 예: "안녕? 오늘 기분은 어때?"

fetch(`${baseUrl}sendMessage`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    userId: userId,
    sessionId: currentSessionId,
    message: userMessage
  })
})
.then(response => {
  if (!response.ok) {
     // 오류 응답 처리
     // 백엔드에서 보낸 오류 메시지를 파싱하여 사용자에게 보여줄 수 있습니다.
     return response.text().then(text => { throw new Error(`HTTP error! status: ${response.status}, message: ${text}`) });
  }
  return response.json();
})
.then(data => {
  console.log("메시지 전송 및 응답 성공:", data);
  const botMessage = data.botMessage; // 챗봇 응답 메시지
  const sessionStatus = data.sessionStatus; // 업데이트된 세션 상태 ('active' 또는 'ended')
  const completedMissions = data.completedMissions; // 새로 완료된 미션 ID 목록

  // 받은 정보를 사용하여 UI 업데이트
  console.log("챗봇 응답:", botMessage);
  console.log("세션 상태:", sessionStatus);
  console.log("완료된 미션:", completedMissions);

  // 세션 상태가 'ended'가 되면 대화 종료 처리
  if (sessionStatus === 'ended') {
    console.log("대화가 종료되었습니다.");
    // 대화 종료 UI 표시 등
  }

  // newly_completed_missions 목록을 보고 해당하는 미션 UI에 완료 표시 및 도장 표시
  completedMissions.forEach(missionId => {
      console.log(`${missionId} 미션이 완료되었습니다!`);
      // 프론트엔드에서 missionId에 해당하는 미션 UI를 찾아 완료 상태로 표시
      // Firestore에서 세션 문서를 실시간으로 구독하거나, sendMessage 응답에 전체 미션 상태를 포함시켜 동기화하는 방법을 선택할 수 있습니다.
  });

})
.catch(error => {
  console.error("메시지 전송 중 오류 발생:", error);
  // 오류 메시지를 사용자에게 표시 등
});
3. 필요한 정보
프론트엔드 개발자는 백엔드 코드를 알 필요 없이 다음 정보만 알고 있으면 됩니다.

Cloud Functions 기본 URL
API 엔드포인트 경로 (/startConversation, /sendMessage)
각 엔드포인트의 요청 본문 형식 (JSON 구조 및 필드 이름)
각 엔드포인트의 응답 본문 형식 (JSON 구조 및 필드 이름)
시나리오 ID 목록 (프론트엔드에서 사용자에게 선택지를 제공해야 한다면, 이는 백엔드 API를 추가하여 시나리오 목록을 불러오거나 수동으로 관리할 수 있습니다.)
미션 ID 및 stampImageId 규칙 (미션 완료 시 UI 업데이트를 위해)
이 정보를 바탕으로 프론트엔드 애플리케이션을 개발하여 백엔드와 연동할 수 있습니다. 프론트엔드에서는 이 백엔드 기능을 사용하여 사용자 대화, 미션 표시, 상태 업데이트 등 사용자 경험 관련 로직을 구현하게 됩니다.

⚙️ 설정 및 배포
1. 필수 조건
Python 3.8 이상 설치
Firebase CLI 설치 및 로그인 (npm install -g firebase-tools, firebase login)
Google Cloud Platform 프로젝트 및 Firebase 프로젝트 설정
2. Firebase 프로젝트 설정
Firebase 콘솔에서 새 프로젝트를 생성하거나 기존 프로젝트를 선택합니다.
프로젝트에서 Cloud Functions 및 Cloud Firestore 기능을 활성화합니다.
Cloud Firestore 데이터베이스를 생성합니다.
Firestore 메뉴에서 데이터베이스 만들기를 선택합니다.
모드는 Native mode를 선택합니다.
리전은 Cloud Functions를 배포할 리전과 동일하게 선택합니다. (예: us-central1 또는 asia-northeast3)
3. 환경 변수 설정
Google Cloud Vertex AI 콘솔 또는 Google AI for Developers 사이트에서 Gemini API 키를 발급받습니다.

Firebase CLI를 사용하여 Cloud Functions에 환경 변수를 설정합니다.

Bash

firebase functions:config:set gemini.api_key="YOUR_GEMINI_API_KEY"
주의: 실제 API 키 값을 직접 노출하지 않도록 주의하세요.
코드는 os.getenv("GEMINI_API_KEY")를 사용합니다. Firebase CLI가 설정한 값은 환경 변수로 제공됩니다.

4. 종속성 설치
functions 디렉토리로 이동하여 requirements.txt에 정의된 파이썬 종속성을 설치합니다.

Bash

cd functions
pip install -r requirements.txt
5. Firestore 시나리오 데이터 추가
Cloud Firestore 데이터베이스에 scenarios 컬렉션을 생성하고, 각 시나리오에 대한 문서를 추가합니다. 각 문서의 Document ID는 시나리오를 식별하는 고유한 ID가 됩니다 (예: park_friend_scenario).

시나리오 문서의 구조는 다음과 같습니다.

JSON

// 컬렉션: scenarios
// 문서 ID: park_friend_scenario (예시)
{
  "name_korean": "공원에서 친구 만나기", // 시나리오 한글 이름 (프론트엔드 표시용)
  "description_for_user": "오랜만에 친구를 만나 공원에서 편안하게 대화하는 시나리오입니다.", // 사용자에게 보여줄 설명

  "system_instruction": "너는 사용자와 오랜만에 만나는 친구야. 우리는 오늘 공원에서 가벼운 일상 이야기를 하면서 서로를 더 잘 알아갈 거야. 우리의 목표는 자연스럽게 대화하며 친구로서 유대감을 쌓는 것이야. 기억해! 우리는 오래된 친구처럼 편안하게 대화할 거야.", // Gemini API에 전달될 시스템 지침

  "initial_missions": { // 초기 미션 목록 (맵 형태)
    "mission1_greeting": { // 미션 ID (키): string (예: ASCII 기반)
      "description": "인사 후 기분 언급", // 미션 설명
      "stampImageId": "stamp_initial" // 미션 완료 시 표시할 도장 이미지 ID
    },
    "mission2_interests": {
      "description": "관심사 언급",
      "stampImageId": "stamp_initial"
    }
    // 필요한 다른 미션들 추가
  },

  "analysis_criteria": { // AI 분석 기준 (맵 형태)
    "completes_mission1_greeting_keywords": ["안녕", "기분", "잘 지내", "별일 없지"], // 미션1 완료 판단 키워드 목록 (필드 이름 형식: "completes_미션ID_keywords")
    "completes_mission2_interests_keywords": ["관심사", "취미", "좋아하는 것", "무슨 일 해"], // 미션2 완료 판단 키워드 목록
    // 다른 미션의 분석 기준 필드 추가

    "termination_keywords": ["다음에 보자", "나중에 보자", "그만하자", "안녕히 계세요"], // 종료 요청 판단 키워드 목록
    // AI 분석에 필요한 다른 데이터 추가 가능
  },

  "bot_initial_message": "오랜만이네! 오늘 날씨도 딱 좋은데, 공원에서 이야기 좀 나눌까?" // 시나리오 시작 시 챗봇의 첫 메시지 (선택 사항)
}
주의: analysis_criteria 내부의 미션 완료 판단 필드 이름은 completes_ + initial_missions의 미션 ID + _keywords 형식(completes_mission1_greeting_keywords)을 따르고 있습니다. chatbot_service.py의 analyze_user_input_with_ai 함수가 이 규칙을 기반으로 작동합니다.

6. Cloud Functions 배포
프로젝트 루트 디렉토리에서 다음 명령을 실행하여 Cloud Functions를 배포합니다.

Bash

firebase deploy --only functions
배포가 완료되면 Google Cloud 콘솔의 Cloud Functions 또는 Firebase 콘솔에서 함수 URL을 확인할 수 있습니다.

💡 API 엔드포인트
배포된 Cloud Functions URL을 통해 백엔드 API를 호출할 수 있습니다.

1. startConversation
새로운 대화 세션을 시작합니다.

URL: [Cloud Functions Base URL]/startConversation
메서드: POST
요청 본문 (JSON):
JSON

{
  "userId": "고유한사용자ID", // 예: "user123"
  "scenario": "시나리오_문서_ID" // 예: "park_friend_scenario"
}
응답 본문 (JSON): 성공 시 새로 생성된 세션 정보와 초기 챗봇 메시지를 반환합니다.
JSON

{
  "sessionId": "새로_생성된_세션_ID", // 이 ID를 sendMessage 호출 시 사용
  "botInitialMessage": "안녕하세요! [시나리오 시작 메시지]", // 챗봇의 첫 메시지 (시나리오 데이터에서 로드)
  "initialStatus": { // 초기 세션 상태 정보 (프론트엔드 사용)
    "userId": "...",
    "scenarioId": "...",
    "scenarioName": "...",
    "scenarioDescription": "...",
    "missions": { /* 초기 미션 상태 목록 (모두 completed: false) */ },
    "status": "active",
    "startTime": "ISO 8601 형식 타임스탬프"
  }
}
2. sendMessage
세션에 사용자 메시지를 전송하고 챗봇 응답 및 업데이트된 세션 상태를 받습니다.

URL: [Cloud Functions Base URL]/sendMessage
메서드: POST
요청 본문 (JSON):
JSON

{
  "userId": "고유한사용자ID", // startConversation과 동일해야 함
  "sessionId": "현재_세션_ID", // startConversation 응답에서 받은 ID
  "message": "사용자의 입력 메시지" // 예: "안녕? 오늘 기분은 어때?"
}
응답 본문 (JSON): 성공 시 챗봇 응답, 업데이트된 세션 상태, 새로 완료된 미션 목록을 반환합니다.
JSON

{
  "botMessage": "챗봇의 응답 메시지",
  "sessionStatus": "업데이트된_세션_상태", // 예: "active" 또는 "ended"
  "completedMissions": ["새로_완료된_미션_ID_1", "새로_완료된_미션_ID_2"] // 새로 완료된 미션 ID 목록 (없으면 빈 배열)
  // 필요에 따라 현재 미션 상태 전체 등을 추가할 수 있습니다.
  // "currentMissionsStatus": { /* 업데이트된 전체 미션 상태 */ }
}
🚶‍♂️ 동작 방식 (개요)
startConversation 호출: 프론트엔드에서 userId와 scenario ID를 담아 startConversation 함수를 호출합니다.
startConversation 함수는 firestore_service.get_scenario를 호출하여 해당 시나리오 데이터를 Firestore에서 불러옵니다.
시나리오 데이터를 바탕으로 초기 세션 데이터 구조를 구성하고, firestore_service.create_session를 호출하여 새로운 세션 문서를 Firestore의 sessions 컬렉션에 저장합니다.
새로 생성된 sessionId와 초기 세션 정보를 프론트엔드에 반환합니다.
sendMessage 호출: 프론트엔드에서 userId, sessionId, message를 담아 sendMessage 함수를 호출합니다.
sendMessage 함수는 firestore_service.get_session를 호출하여 해당 세션 데이터를 Firestore에서 불러옵니다. 이 세션 데이터에는 이전에 저장된 대화 기록, 미션 상태, 시나리오 관련 정보(system_instruction, analysis_criteria)가 포함되어 있습니다.
불러온 대화 기록에 사용자의 현재 메시지를 추가합니다.
chatbot_service.get_chatbot_response를 호출하여 챗봇 응답을 생성합니다. 이 함수는 세션 데이터에서 불러온 시나리오별 system_instruction과 현재까지의 대화 기록을 Gemini API에 전달합니다.
chatbot_service.analyze_user_input_with_ai를 호출하여 사용자 입력의 의미를 분석합니다. 이 함수는 세션 데이터에서 불러온 시나리오별 analysis_criteria를 바탕으로 AI 분석 프롬프트를 구성하고 Gemini API 분석 결과를 파싱합니다.
chatbot_service.update_mission_status를 호출하여 analyze_user_input_with_ai의 결과를 바탕으로 미션 상태를 업데이트하고 새로 완료된 미션 목록을 식별합니다.
analyze_user_input_with_ai 결과에 종료 요청이 포함되어 있으면 세션 상태를 'ended'로 변경합니다.
업데이트된 대화 기록, 미션 상태, 세션 상태를 firestore_service.update_session를 호출하여 Firestore에 저장합니다.
챗봇 응답 메시지, 업데이트된 세션 상태, 새로 완료된 미션 목록을 프론트엔드에 반환합니다.
