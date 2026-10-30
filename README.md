# Codex Basic Skills

기존 문서 폴더를 그대로 쓰는 LLM Wiki와, 만들기 전에 설계를 점검하는 Codex용 공용 스킬입니다. 개인 노트, 연구 자료, 학습 기록, 팀 문서 등 다양한 지식베이스에 사용할 수 있습니다.

특정 회사·프로젝트·내부 도구를 전제로 하지 않습니다. 폴더 분류, 파일명, 페이지 타입은 사용자의 기존 구조와 운영 규칙을 따릅니다. 아래 업무 폴더는 사용 예시입니다.

| 스킬 | 하는 일 |
|---|---|
| [wiki-setup](skills/wiki-setup/SKILL.md) | 원본을 옮기지 않고 위키를 만들거나 기존 위키에 Codex 운영 규칙 추가 |
| [wiki-ingest](skills/wiki-ingest/SKILL.md) | 새 자료 검증 → 업무 폴더 배치 → 관련 지식 합성 → 색인·인벤토리·로그 갱신 |
| [wiki-lint](skills/wiki-lint/SKILL.md) | 구조 검사와 의미 검토로 모순·낡은 정보·미반영 자료·다음 질문 찾기 |
| [grilling](skills/grilling/SKILL.md) | 문서·코드를 먼저 조사하고, 중요한 설계 갈림길을 한 번에 하나씩 질문 |
| [grill-me](skills/grill-me/SKILL.md) | 같은 인터뷰를 짧은 이름으로 시작; 단독 설치도 가능 |

## 설치

이 저장소의 `skills/<이름>` 폴더를 Codex가 읽는 사용자 스킬 디렉터리 또는 프로젝트의 `.agents/skills/`에 복사하세요. 사용자 디렉터리는 일반적으로 `~/.codex/skills/`입니다. 같은 이름의 스킬이 이미 있으면 내용을 비교하고 필요한 변경만 병합하세요. 기존 개인 설정을 덮어쓰지 마세요.

Codex에 이렇게 요청해도 됩니다:

```text
https://github.com/bigbulgogiburger/codex-basic-skills 에서
wiki-setup, wiki-ingest, wiki-lint, grilling, grill-me 스킬을 설치해줘.
같은 이름이 이미 있으면 먼저 차이를 확인해줘.
```

위키 3종을 함께 설치하면 setup → ingest → lint 흐름으로 사용할 수 있습니다. 각각 독립적으로도 동작하며, 다른 스킬이 없으면 해당 SKILL.md에 적힌 수동 절차를 따릅니다. Claude 전용 slash command, plugin, 디바이스 브리지, Jira 연결은 필요하지 않습니다.

## 사용

```text
$wiki-setup 이 업무 폴더를 LLM Wiki로 만들어줘. 기존 원본은 그대로 둬.
$wiki-ingest 이 회의록을 적절한 폴더에 배치하고 위키에 반영해줘.
$wiki-ingest 이 자료는 위키에만 반영해줘. 파일은 옮기지 마.
$wiki-lint 이 위키에서 모순과 오래된 정보, 빠진 원본을 찾아줘.
$grill-me 이 기능 계획의 빈틈을 하나씩 질문해줘.
```

`wiki-setup`은 루트 `AGENTS.md`에 **작업 주제와 관계없이 시작할 때 위키 색인 → 개요 → 최신 로그를 먼저 읽는 규칙**을 반드시 넣습니다. 기존 AGENTS.md의 다른 지침은 보존합니다. 위키 질의와 재사용 가능한 분석의 환원도 이 운영 규칙에 포함됩니다.

```text
업무 폴더/
├── AGENTS.md             # Codex 운영 스키마 및 필수 시작 순서
├── 회의록/               # 기존 원본: 배치 후 내용 보존
├── 계약/                 # 기존 분류·파일명 관례 유지
└── wiki/
    ├── index.md          # 페이지별 링크 + 한 줄 설명
    ├── overview.md       # 근거가 있는 전체 개요
    ├── catalog.md        # 원본 인벤토리 및 반영 범위
    ├── log.md            # 끝에만 추가하는 작업 이력
    ├── entities/
    ├── concepts/
    └── sources/          # 필요할 때만 개별 자료의 심층 요약
```

`raw`는 원본의 **역할**입니다. `raw/`라는 폴더를 만들 필요는 없습니다. 이미 `raw/`를 사용하는 위키도 그대로 유지합니다. 초기화는 전체 자료를 읽었다는 뜻이 아니며, 아직 읽지 않은 원본은 미인제스트로 남깁니다.

## 검사 도구

`wiki-lint`의 Python 도구는 읽기 전용입니다. Python 3.10+에서 필요한 패키지만 별도 환경에 설치합니다:

```sh
python -m pip install -r skills/wiki-lint/scripts/requirements.txt
python skills/wiki-lint/scripts/wiki_lint.py /path/to/wiki --source-root /path/to/workspace
python -m unittest discover -s tests -v
```

기계 검사의 정상 종료는 내용의 정확성이나 위키 전체 건강을 보증하지 않습니다. 도구의 범위와 한계는 [검사 안내](skills/wiki-lint/references/checks.md)에 있습니다.

## 설계 근거

Andrej Karpathy의 **LLM Wiki** 패턴을 바탕으로 원본 보존, 지속적인 지식 합성, 위키 우선 탐색과 설계 인터뷰를 Codex용으로 구성했습니다. 패턴의 원칙과 이 저장소의 운영상 선택은 [설계 노트](docs/design.md)에서 구분합니다.
