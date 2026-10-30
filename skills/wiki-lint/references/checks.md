# 검사 도구 범위

Python 3.10+, `markdown-it-py`, `PyYAML`을 사용한다. `scripts/requirements.txt`의 의존성을 작업용 환경에 설치한다. 도구는 파일을 쓰거나 네트워크에 접속하지 않는다.

```sh
python <skill-dir>/scripts/wiki_lint.py <wiki-dir> --source-root <workspace-root>
python <skill-dir>/scripts/wiki_lint.py <wiki-dir> --source-root <workspace-root> --json
```

지원: CommonMark Markdown 상대 링크·이미지·참조형 링크, URL 인코딩된 경로, 같은 문서의 앵커, 일반 ATX/Setext 제목, 중복 제목, YAML 파싱·필수 키·타입·실제 달력 날짜, 로컬 출처 존재, 다른 페이지의 인바운드 링크가 없는 고아 후보, 파일명 기반 충돌 사본 후보. 코드 블록과 inline code의 가짜 링크는 검사하지 않는다.

기본 허브는 `index.md,overview.md,catalog.md,log.md`다. 허브는 frontmatter가 없어도 되지만 있는 경우 type/updated를 검사한다. 다른 지식 페이지는 type/updated/sources를 요구한다. `sources`는 문자열 목록이며 로컬 경로는 `--source-root` 기준이다. http(s) 출처는 존재 확인을 하지 않는다.

기본 타입은 entity/concept/source/overview/index/catalog/log다. 기존 스키마가 다르면 예를 들어 `--types entity,concept,source,question,synthesis`로 전체 허용 목록을 지정한다. 허브 이름이 대문자면 `--hub INDEX.md --hub LOG.md`처럼 실제 허브를 모두 전달한다. 옵션은 기본값에 추가하지 않고 대체한다.

기본 제외 경로 요소는 `_to_delete`, `.git`, `__pycache__`다. 기존 규칙이 다르면 `--exclude`를 반복해 전체 제외 목록을 지정한다. 파일과 출처의 경계는 source-root이고, 지정하지 않으면 링크는 wiki의 부모 안에서만 확인한다. 로컬 sources가 있는데 source-root가 없으면 검사 미완료로 표시한다. 경계 밖 대상이나 위키 밖을 가리키는 심볼릭 링크를 따라가 읽지 않는다.

종료 코드:

- 0: 검사한 구조에서 오류 없음. warning이 있을 수 있음. 의미 검토 결과가 아님.
- 1: 깨진 링크·잘못된 메타데이터 등 구조 오류 있음.
- 2: 파일 읽기/의존성/범위 오류, 지원 밖 구문 등으로 검사 미완료. 다른 finding도 함께 확인.

## 수동 보완

- `[[wikilink]]`와 HTML 링크·사용자 정의 anchor는 미완료로 보고한다. 기존 전용 린터 또는 수동 검토로 보완한다. 자동 변환하지 않는다.
- 앵커 생성은 일반적인 GitHub 스타일의 한글/영문 제목을 다룬다. 특수 Unicode, HTML, 사용자 정의 렌더러의 세부 slug는 실제 렌더러와 대조한다. CommonMark 파서가 링크로 인식하지 않은 잘못된 Markdown 문법은 별도 검토 대상이다.
- 줄은 해당 Markdown 블록의 시작 줄이다. 여러 줄 문단에서는 정확한 링크 줄과 다를 수 있다.
- orphan은 단순 인바운드 링크 수다. index에서의 실제 도달 가능성, 누락된 catalog 행, 미인제스트 파일, 총계는 에이전트가 별도로 대조한다.
- 출처 파일의 존재는 내용의 정확성·해시 일치·전체 반영을 증명하지 않는다. URL 접근성, 출처 권위, stale, 모순, 중요한 누락 개념은 의미 검토로 확인한다.
- 파일명만으로 모든 동기화 충돌 사본을 탐지할 수 없다. 서비스별 이름 관례와 실제 변경을 확인한다.

스크립트 성공만 보고 위키 전체가 정상이라고 결론 내리지 않는다.
