## 챗봇 백엔드 시스템  
**(Cloud Functions + Firestore + Gemini API)**

Google Cloud Functions(2세대, Python), Cloud Firestore, Google Gemini API를 활용하여  
시나리오 기반 대화 및 미션 수행을 지원하는 챗봇 백엔드입니다.

---

### ✨ 주요 기능

- **세션 관리**  
  Firestore에 사용자별 대화 세션을 저장·관리  
- **시나리오 기반 대화**  
  Firestore에 정의된 시나리오 데이터를 동적으로 불러와  
  - 챗봇 페르소나 설정  
  - 대화 지침(system instruction) 적용  
  - 초기 미션 할당  
- **미션 추적 및 완료**  
  사용자의 입력을 Gemini AI로 분석 →  
  시나리오별 미션 완료 여부 판단 →  
  세션 상태 업데이트  
- **대화 종료 조건**  
  AI 분석을 통해 ‘종료 키워드’ 감지 시 세션 종료  
- **모듈화된 코드 구조**  
  Firestore 연동 로직(`/firestore_service.py`)과  
  AI 연산 로직(`/chatbot_service.py`) 분리  

---

### 🚀 사용 기술

| 기술               | 설명                                              |
| ------------------ | ------------------------------------------------- |
| Cloud Functions    | 2세대 Python 기반 서버리스 함수 실행 환경         |
| Cloud Firestore    | NoSQL 클라우드 DB (세션·시나리오 데이터 저장)     |
| Gemini API         | 챗봇 응답 생성·사용자 입력 분석 (gemini-2.0-flash) |
| Python 3.12        | 백엔드 개발 언어                                  |
| Firebase Admin SDK | Firestore 접근                                    |
| Generative AI SDK  | Gemini API 호출                                   |
| Firebase CLI       | 배포 및 로컬 에뮬레이터 관리                      |

---

### 📁 프로젝트 구조

```
/your-project-root
├── functions
│   ├── .gitignore
│   ├── main.py
│   ├── firestore_service.py
│   ├── chatbot_service.py
│   └── requirements.txt
├── .firebaserc
├── firebase.json
└── README.md (이 파일)
```

- **`main.py`**  
  - HTTP 트리거 함수(startConversation, sendMessage) 정의  
  - 요청 파싱 → 서비스 로직 호출 → 초기화  
- **`firestore_service.py`**  
  Firestore CRUD (시나리오/세션 생성·읽기·업데이트)  
- **`chatbot_service.py`**  
  - Gemini API 호출  
  - 프롬프트 구성  
  - 사용자 입력 분석  
  - 미션 상태 업데이트  
- **`requirements.txt`**  
  - `firebase_admin`, `google-generativeai`, `firebase-functions`, `requests`, `textwrap` 등

---

## 🤝 프론트엔드 연동

백엔드는 **표준 HTTP API**를 통해 통신하므로,  
프론트엔드 개발자는 함수 URL만 알면 됩니다.


1. **요청 함수 URL 구조**  
   ```
   https://[REGION]-[PROJECT_ID].cloudfunctions.net/
   ```
2. **엔드포인트**  
   - `startConversation`  
   - `sendMessage`
3. **요청함수url** 
   https://sendmessage-imrcv7okwa-uc.a.run.app
   https://startconversation-imrcv7okwa-uc.a.run.app
---

### 1) startConversation 호출 예시 (JavaScript)

```js
const baseUrl    = "https://us-central1-your-project-id.cloudfunctions.net/";
const userId     = "user123";
const scenarioId = "park_friend_scenario";

fetch(`${baseUrl}startConversation`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ userId, scenario: scenarioId })
})
.then(res => {
  if (!res.ok) throw new Error(`status ${res.status}`);
  return res.json();
})
.then(data => {
  console.log("세션 시작:", data);
  // data.sessionId, data.botInitialMessage, data.initialStatus 활용
})
.catch(err => console.error(err));
```

---

### 2) sendMessage 호출 예시 (JavaScript)

```js
const baseUrl       = "https://us-central1-your-project-id.cloudfunctions.net/";
const userId         = "user123";
const sessionId      = "받은_sessionId";
const userMessage    = "안녕? 오늘 기분은 어때?";

fetch(`${baseUrl}sendMessage`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    userId, sessionId, message: userMessage
  })
})
.then(res => {
  if (!res.ok) throw new Error(`status ${res.status}`);
  return res.json();
})
.then(data => {
  console.log("응답:", data.botMessage);
  console.log("세션 상태:", data.sessionStatus);
  console.log("완료된 미션:", data.completedMissions);
})
.catch(err => console.error(err));
```

---

## ⚙️ 설정 및 배포

1. **필수 조건**  
   - Python ≥3.8  
   - Firebase CLI (`npm install -g firebase-tools`)  
   - GCP & Firebase 프로젝트

2. **Firebase 프로젝트 설정**  
   - Cloud Functions & Firestore 활성화  
   - Firestore 모드: Native  
   - 리전: 함수 배포 리전과 일치

3. **환경 변수 설정**  
   ```bash
   firebase functions:config:set gemini.api_key="YOUR_GEMINI_API_KEY"
   ```

4. **종속성 설치**  
   ```bash
   cd functions
   pip install -r requirements.txt
   ```

5. **시나리오 데이터 추가**  
   Firestore `scenarios` 컬렉션에 문서 생성  
   ```json
   {
     "name_korean": "공원에서 친구 만나기",
     "description_for_user": "오랜만에 친구를 만나 공원에서 대화하는 시나리오입니다.",
     "system_instruction": "너는 사용자와 오랜만에 만나는 친구야…",
     "initial_missions": { … },
     "analysis_criteria": { … },
     "bot_initial_message": "오랜만이네! 오늘 날씨도 좋다!"
   }
   ```

6. **배포**  
   ```bash
   firebase deploy --only functions
   ```

---

## 💡 API 엔드포인트 요약

| 엔드포인트               | 메서드 | 요청 예시 (JSON)                                       | 응답 예시 (JSON)                             |
| ------------------------ | ------ | ------------------------------------------------------ | -------------------------------------------- |
| `/startConversation`     | POST   | `{ "userId": "...", "scenario": "..." }`               | `{ sessionId, botInitialMessage, initialStatus }` |
| `/sendMessage`           | POST   | `{ "userId": "...", "sessionId": "...", "message":"..." }` | `{ botMessage, sessionStatus, completedMissions }` |
