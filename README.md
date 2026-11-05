# VEILBOUND

현실과 그림자 세계를 전환하며 길을 연결하고 위험을 피하는 2D 퍼즐 플랫폼 게임이다. Python + pico2d로 개발하고 Tiled로 맵을 편집한다.

## 현재 상태

개발 기준 문서와 Stage 1 맵 초안이 있다. 아직 실행용 `main.py`나 게임 로직을 작성하지 않았다. Stage 2~3 폴더는 제작 계획을 담고 있으며 플레이 가능한 맵이 아니다.

## 프로젝트 구조

```text
VEILBOUND_2DGP/
├─ PRD.md                 # 게임 규칙·개발 순서·수용 기준
├─ AGENTS.md              # 개발·한국어 커밋·push 규칙
├─ game/                  # 공통 Python 게임 코드 관리 위치
│  └─ README.md           # 코드 역할과 추가 순서
├─ maps/
│  ├─ README.md           # 맵 목록과 경로 규칙
│  ├─ tilesets/           # 모든 스테이지가 공유하는 외부 TSJ
│  ├─ stage_01/           # 사라진 다리: TMJ와 설계·검증 기록
│  ├─ stage_02/           # 뒤틀린 계단: 계획 문서
│  └─ stage_03/           # 위험한 골목: 계획 문서
├─ assets/                # 배경·타일·캐릭터 등 원본 리소스
└─ docs/                  # 발표·기획서 PPT
```

개발을 시작하면 프로젝트 루트에 실행 진입점 `main.py`를 추가한다. 이 파일은 게임 시작·종료 연결을 담당하고, 이동·충돌·카메라 같은 구현은 `game/` 안에 둔다. 위 구조에서 `main.py`는 아직 생성하지 않았다.

- [개발 기준 PRD](PRD.md)
- [코드 관리 안내](game/README.md)
- [맵 목록·편집 방법](maps/README.md)
- [Stage 1 맵 파일](maps/stage_01/stage1_missing_bridge.tmj)
- [발표 PPT](docs/VEILBOUND_발표.pptx)
- [기획서 PPT](docs/VEILBOUND_기획서.pptx)

Stage 1을 Tiled로 열 때는 저장소의 `assets/`, `maps/tilesets/`, `maps/stage_01/` 구조를 함께 유지한다. 실제 게임 실행 방법과 검증한 Python·pico2d 버전은 첫 실행 기능을 구현한 뒤 이 문서에 추가한다.
