# ARTEMIS upstream proxy-only 개발 셋업

## 왜 필요한가

사내망에서는 Google/OpenAI/Anthropic API 호스트에 직접 연결하는 경로가 TLS 핸드셰이크
단계에서 차단됩니다(DNS/TCP는 성공하지만 TLS handshake에서 끊깁니다). 사내 LiteLLM
프록시(OpenAI 호환 엔드포인트)만 통과 가능합니다. 그런데 ARTEMIS(google/artemis)는
기본값이 Gemini API 직결이라, 사내망에서는 아무 설정도 하지 않으면 LLM 호출이 전부
TLS 오류로 실패합니다. 이 문서는 ARTEMIS를 **프록시 경유 전용(proxy-only)** 으로 돌리기
위한 로컬 패치와 설정을 설명합니다. 개발 편의를 위한 것으로, 제품 배포 대상이 아닙니다.

## 패치가 바꾸는 것 (`patches/artemis-upstream-proxy-only.patch`)

google/artemis `371aa6d` 위에 커밋 1개(`93698ae`)를 적용합니다.

- `config/artemis.jsonc`: 모든 노드(default, object_detector, hopper,
  flash.step_summarizer, memory.chunking)를 provider `openai`, model
  `gemini/gemini-3.5-flash`(프록시가 서빙)로 변경.
- `artemis/config/llm.py`: `lightweight_judge_default()`와
  `_expand_default_into_nodes`의 설정 없을 때 폴백이 provider `google`로
  하드코딩돼 있던 것을 `openai`로 변경(Pro 모드 judge도 프록시를 타도록).
- `artemis/agents/flash/summarizer.py`, `artemis/agents/flash/runner.py`,
  `artemis/memory/chunking.py`: 이 세 파일이 `get_google_llm()`을 직접 호출해
  jsonc 설정을 무시하던 업스트림 버그. `get_openai_llm()`으로 고쳐 설정된
  provider가 실제로 적용되도록 함.

## 설치 방법

```powershell
cd <제품 저장소 루트>
powershell -ExecutionPolicy Bypass -File scripts\setup_artemis_upstream.ps1
```

- 기본적으로 `..\artemis-upstream`에 clone합니다(`-TargetDir`로 변경 가능).
- `uv`가 없으면 설치하고 `uv sync`를 실행합니다.
- `config/artemis-upstream/.env.example`을 `<target>\.env`로 복사합니다(기존 `.env`는
  덮어쓰지 않습니다). 복사 후 `OPENAI_API_KEY`(LiteLLM virtual key)와, 필요하다면
  `ADB_DEVICE_SERIAL`을 채우세요.
- Claude Code에 MCP 서버 두 개를 user scope로 등록합니다(`-SkipMcp`로 생략 가능).
- 무엇이 실행될지만 보려면 `-DryRun`을 붙이세요.

## Claude Code에서 MCP 서버 사용

등록 후에는 **새 Claude Code 세션**을 열어야 MCP 서버가 인식됩니다.

- `artemis`: 툴 5종(`mobile_*`). 이 중 `mobile_run_task`만 내부 LLM(프록시)을 사용하고,
  나머지는 로컬 상태 조회입니다.
- `artemis-adb`: raw ADB 툴 13종, LLM을 전혀 사용하지 않는 저수준 기기 제어입니다.

### 알려진 이슈: cold-start race

MCP 서버를 막 띄운 직후 첫 `mobile_run_task` 호출이 "Task runner process terminated
unexpectedly" 오류로 실패할 수 있습니다. 데몬 콜드스타트 경쟁 조건(race)으로 보이며,
**한 번 재시도하면 대부분 성공**합니다.

## 업스트림 상태

이 로컬 패치가 고치는 버그는 google/artemis#95로 리포트했고, 더 일반화된 fix PR을
제출 중입니다. 그 PR이 머지되면 `artemis/agents/flash/*.py`, `memory/chunking.py`,
`artemis/config/llm.py`에 대한 코드 패치는 대부분 불필요해지고, `config/artemis.jsonc`와
`.env` 설정만 남을 것으로 예상합니다. 그 전까지는 이 저장소의 패치를 계속 재적용해야
합니다.

## 참고: 시각 그라운딩 모델 제한

업스트림 기본 그라운딩 모델인 `gemini-robotics-er-2-preview`는 우리 프록시 키로는
허용되지 않습니다. 그래서 이 패치는 그라운딩도 `gemini-3.5-flash` + UI-tree 백엔드
(`ARTEMIS_HIERARCHY_BACKEND=auto`) 조합으로 대체합니다. 클릭 정확도가 부족하면 프록시
관리자에게 `gemini-robotics-er-2-preview` 모델 허용을 요청하세요.
