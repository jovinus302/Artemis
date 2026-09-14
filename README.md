# artemis

Google ADK(Agent Development Kit) 에이전트 위에 Google ARTEMIS(Android 자동화 프레임워크)를
툴(FunctionTool)로 연결하는 제품 저장소입니다. 자연어 지시를 받아 실제 Android 기기/에뮬레이터를
조작하는 ADK 에이전트를 만드는 것이 목표입니다.

## ARTEMIS란

- 저장소: [google/artemis](https://github.com/google/artemis), Apache-2.0, Alpha 단계
- 자연어 목표(goal)를 받아 Android 기기를 직접 조작하는 자동화 호스트
- 두 가지 실행 프로파일 제공
  - `flash`: 빠른 반응형 루프. 짧고 결정적인 UI 플로우에 적합
  - `pro`: 계획 수립 + 검증(Checker)까지 포함하는 다단계 워크플로우용
- 인터페이스: Web UI(기본 포트 8000), CLI, MCP 서버(`mobile_*` 툴 5종), Python SDK(`artemis-client`)

## Google ADK란

- 버전: 2.9.0, 공식 사이트: [adk.dev](https://adk.dev)
- 에이전트 폴더 규약: `<agent_dir>/__init__.py`(`from . import agent`) + `agent.py`의
  `root_agent` 변수를 ADK CLI/Web UI가 찾아 로드합니다.

## ARTEMIS와 ADK의 관계

두 프로젝트 사이에 공식 통합은 없습니다. 이 저장소는 기본적으로 ARTEMIS의 HTTP Python SDK
(`artemis-client`)를 ADK `FunctionTool`로 감싸는 방식을 사용합니다(`agents/artemis_agent/artemis_tools.py`).
ARTEMIS가 제공하는 네이티브 MCP 서버(`mobile_*` 5종 툴)를 그대로 붙이는 방법도 옵션으로
제공합니다(`agents/artemis_agent/mcp_tools.py`, 기본 비활성).

## 설치 및 실행

```powershell
cd C:\Users\siheon.ryu\Desktop\workspace\R2P\artemis
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 키 없이 검증
.\.venv\Scripts\python.exe scripts\check_env.py
.\.venv\Scripts\adk.exe --help
.\.venv\Scripts\python.exe -m pytest -q

# 키 있을 때
.\.venv\Scripts\python.exe scripts\smoke_proxy.py
.\.venv\Scripts\adk.exe run agents\artemis_agent
.\.venv\Scripts\adk.exe web agents --port 8080
```

`.env.example`을 복사해 `.env`를 만들고 실제 값을 채워 넣으세요. `.env`와 `PROXY_MODELS.md`는
`.gitignore`에 등록되어 있어 커밋되지 않습니다.

## 단계별 로드맵

- **Phase 1 (현재)**: Claude 프록시(Anthropic 호환 LiteLLM 게이트웨이)로 ADK 에이전트가
  동작하는 상태. ARTEMIS 호스트가 떠 있지 않으므로 `artemis_*` 툴은 항상
  `{"status": "error", ...}` dict를 반환합니다(모델이 결과를 지어내지 않도록 설계).
- **Phase 2**: Gemini API 키와 실제 Android 기기/에뮬레이터를 확보한 뒤,
  `..\artemis-upstream` 경로에 `google/artemis`를 clone하고 그 저장소의 `.\start.bat`으로
  ARTEMIS 호스트를 띄우면, 같은 툴들이 실제 자동화를 수행합니다.
  (사내망에서 Gemini API 직결 없이 개발용으로만 돌리고 싶다면
  `docs/artemis-upstream-proxy-only.md`의 proxy-only 셋업을 참고하세요.)

  ### Gemini API 키 준비

  - Google AI Pro/Ultra 구독은 AI Studio 웹 UI에만 적용되며 API 키 사용에는 적용되지 않습니다
    (참고: https://ai.google.dev/gemini-api/docs/google-ai-plans). API 키는 별도 무료 티어에서
    시작합니다.
  - 무료 키 발급 절차: https://aistudio.google.com/apikey 접속 -> "Create API key" ->
    발급된 키에 "Unrestricted" 라벨이 붙어 있으면 "Add restrictions"로
    "Restrict to Gemini API only"를 설정하세요 (2026-09부터 제한 없는(unrestricted) 키는
    403으로 거부됩니다, 참고: https://ai.google.dev/gemini-api/docs/api-key).
  - 발급받은 동일한 키 값을 루트 `.env`의 `GOOGLE_API_KEY`(ADK용)와 `GEMINI_API_KEY`(ARTEMIS용)
    둘 다에 넣으세요.
  - `.env.example`의 (B) Gemini 섹션에 `GOOGLE_API_KEY` 옆에 `GEMINI_API_KEY` 항목도 있으니
    같은 값을 채우면 됩니다.
  - 무료 티어 한도(비공식 측정치: gemini-3.8-flash 기준 분당 5 RPM / 일 20 RPD)로는 ARTEMIS
    태스크를 끝까지 완주하기 어렵습니다 -> AI Studio에서 "Set up billing"으로 Cloud Billing을
    연결해 유료 Tier 1로 전환하세요(Vertex AI 프로젝트 설정은 불필요). 예상 비용은 태스크당
    약 $0.3~3 수준이며 기본 월 사용한도(cap)는 $250입니다. 유료 티어에서는 요청 데이터가
    모델 학습에 사용되지 않습니다.
  - 키가 정상 동작하는지 확인하는 PowerShell 예시(값은 환경변수로만 참조하고 화면에 직접
    찍지 마세요):
    ```powershell
    $h = @{ "x-goog-api-key" = $env:GEMINI_API_KEY; "Content-Type" = "application/json" }
    Invoke-WebRequest -Uri "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent" -Method Post -Headers $h -Body '{"contents":[{"parts":[{"text":"ping"}]}]}' | Select-Object StatusCode
    ```
  - 사내 LLM 프록시(`PROXY_MODELS.md` 목록)에는 `gemini-robotics-er-2-preview`가 없어서,
    프록시만으로는 ARTEMIS의 시각 그라운딩(visual grounding)을 수행할 수 없습니다 -- 이 때문에
    Gemini API 키를 구글에 직접 연결하는 것이 Phase 2에 필수입니다.
- **Phase 3**: `ARTEMIS_MCP_ENABLED=true` + `ARTEMIS_REPO_DIR` 설정 시
  ARTEMIS 네이티브 MCP 서버(`mobile_*` 5종)를 `McpToolset`으로 추가 연결할 수 있습니다.

## 네트워크 제약 (사내망)

- 사내망에서는 Google/Anthropic/OpenAI 등 외부 API 엔드포인트에 직접 연결하는 경로가
  TLS 핸드셰이크 단계에서 차단됩니다(DNS 조회와 TCP 연결(SYN/ACK)까지는 성공하지만,
  그 다음 TLS handshake에서 끊깁니다). 사내 LiteLLM 프록시(`ANTHROPIC_BASE_URL` 경유)만
  통과 가능합니다.
- 확인 방법 예시:
  ```powershell
  curl -sS -o NUL -w "%{http_code}" https://generativelanguage.googleapis.com/
  ```
  이 명령이 curl exit code 35(SSL connect error)로 실패하면 차단된 것입니다.
- 따라서 **Phase 2(ARTEMIS 실제 런타임)는 사내망에서 바로 동작하지 않습니다.** ARTEMIS
  자체가 화면 그라운딩에 `gemini-robotics-er-2-preview` 모델을 하드코딩해서 Gemini API에
  직접 연결하며(별도의 base_url 오버라이드 옵션이 없습니다), 이 연결이 사내망에서
  차단되기 때문입니다. `.env`에 `GEMINI_API_KEY`를 넣어 두어도 사내망 안에서는 그 키가
  유효한지조차 검증할 수 없습니다(요청 자체가 TLS 단계에서 도달하지 못합니다).
- Phase 2를 실제로 진행하려면 다음 세 가지 중 하나가 필요합니다.
  1. 네트워크팀에 `generativelanguage.googleapis.com` 아웃바운드 허용을 요청한다.
  2. 사내 프록시 관리자에게 `gemini-robotics-er-2-preview` 등 ER(Element Recognition)
     모델 추가를 요청하고, ARTEMIS 쪽 소스에 base_url 오버라이드 패치를 적용한다.
  3. 사내망 밖의 호스트에서 ARTEMIS 호스트(daemon)를 띄우고, 이 저장소의
     `ARTEMIS_BASE_URL`을 그 원격 주소로 지정해 `artemis-client`(HTTP 기반 SDK)로
     원격 연결한다. artemis-client는 HTTP 기반이라 구조상 이 방식이 가능합니다.
- 이 저장소의 기본값(`ADK_MODEL_BACKEND=auto`)은 이런 사내망 제약을 감안해,
  `ANTHROPIC_API_KEY`가 있으면 `GEMINI_API_KEY`/`GOOGLE_API_KEY`가 함께 있어도 항상
  anthropic(프록시) 경로를 우선합니다. 자세한 내용은
  `agents/artemis_agent/model.py`의 `_backend()` 주석을 참고하세요.

## 주의사항

- **ARTEMIS는 Gemini API 키가 사실상 필수입니다** — 화면 그라운딩(Grounding)이 Gemini의
  ER(Element Recognition) 계열 모델에 하드코딩되어 있어, Phase 2 이전에는 실제 자동화가
  동작하지 않습니다.
- ARTEMIS 기본 포트(8000)가 이미 사용 중이라면 ADK Web UI는
  `adk web --port 8080` 처럼 다른 포트를 지정하세요.
- Windows에서는 ADK의 `--reload` 옵션을 비활성 상태로 두세요(파일 감시자 이슈).
- `.env` 파일은 항상 UTF-8(BOM 없음)로 저장하세요.
- `model="claude-..."` 형태의 문자열을 `LlmAgent`에 직접 넘기지 마세요. ADK 모델 레지스트리는
  `claude-.*` 패턴을 Vertex AI 전용 `Claude` 클래스로 매핑하는데, 이 클래스는
  `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION`이 없으면 곧바로 `ValueError`를 던집니다.
  대신 `agents/artemis_agent/model.py`처럼 `AnthropicLlm(model=..., max_tokens=...)` 인스턴스를
  직접 생성해 넘겨야 합니다(공식 Anthropic SDK가 `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY`
  환경변수를 스스로 읽습니다).
- `PROXY_MODELS.md`와 `.env`는 절대 커밋하지 마세요.
