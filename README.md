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
- **Phase 3**: `ARTEMIS_MCP_ENABLED=true` + `ARTEMIS_REPO_DIR` 설정 시
  ARTEMIS 네이티브 MCP 서버(`mobile_*` 5종)를 `McpToolset`으로 추가 연결할 수 있습니다.

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
