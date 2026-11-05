# VEILBOUND

현실과 그림자 세계를 전환하며 길을 연결하고 위험을 피하는 2D 퍼즐 플랫폼 게임이다. Python + pico2d로 개발하고 Tiled로 맵을 편집한다. 플레이어의 무기·공격 기능은 사용하지 않는다.

## 현재 상태와 실행

Stage 1 맵 미리보기를 구현했다. 800×600 창에서 원본 픽셀을 정수 3배로 표시하고 카메라를 이동해 맵을 확인할 수 있다. 시작점·출구 표시는 디버그 마커다. 플레이어 이동·점프·충돌, Shift 세계 전환, 사망·클리어는 아직 구현하지 않았다. Stage 2~3은 계획 문서만 있다.

Windows의 Python 3.13.15, pico2d 1.5.1, PySDL2 0.9.17, pysdl2-dll 2.32.10에서 실행을 확인했다. 현재 환경에는 이미 설치되어 있었으며 새 환경은 다음과 같이 준비한다.

```powershell
cd D:\VEILBOUND_2DGP
python -m pip install -r requirements.txt
python main.py
```

방향키는 미리보기 카메라를 이동하고 R은 카메라를 시작점으로 복구한다. F1은 시작·출구 마커를 표시/숨기고 Esc 또는 창 닫기는 종료한다. 창이 포커스를 잃으면 갱신을 멈추고 입력·누적 시간을 비운다. 현재 R은 게임 재시작이 아니다.

```powershell
python main.py --world shadow
python main.py --check-map
python -m unittest discover -s tests -v
```

`--world shadow`는 실행 시 선택하는 정적 그림자 미리보기다. 실제 플레이 중 세계 전환을 구현했다는 뜻은 아니다. `--check-map`은 창을 열지 않고 맵을 검사한다. 다른 폴더에서도 `python D:\VEILBOUND_2DGP\main.py`로 실행할 수 있다.

## 프로젝트 구조

```text
VEILBOUND_2DGP/
├─ main.py                # 실행 진입점
├─ requirements.txt       # 검증한 실행 의존성
├─ PRD.md                 # 게임 규칙·개발 순서·수용 기준
├─ AGENTS.md              # 개발·한국어 커밋·push 규칙
├─ game/                  # 실행 흐름·객체 관리·맵 로더·카메라·렌더링
├─ tests/                 # 객체 관리·고정 시간·좌표·맵·실행 상태 검사
├─ maps/
│  ├─ tilesets/           # 공통 외부 TSJ
│  ├─ stage_01/           # 사라진 다리: TMJ와 설계·검증 기록
│  ├─ stage_02/           # 뒤틀린 계단: 계획 문서
│  └─ stage_03/           # 위험한 골목: 계획 문서
├─ assets/                # 배경·타일·캐릭터 원본 리소스
└─ docs/                  # 발표·기획서 PPT
```

- [개발 기준 PRD](PRD.md)
- [코드 역할과 설계 근거](game/README.md)
- [맵 목록·편집 방법](maps/README.md)
- [Stage 1 맵](maps/stage_01/stage1_missing_bridge.tmj)
- [발표 PPT](docs/VEILBOUND_발표.pptx), [기획서 PPT](docs/VEILBOUND_기획서.pptx)

Tiled에서 편집할 때는 `assets/`, `maps/tilesets/`, `maps/stage_01/` 구조를 함께 유지한다. 원본 이미지와 타일 배치는 이번 실행 기능에서 변경하지 않았다.

## 확인 범위

자동 검사 21개와 실제 pico2d 창의 현실·그림자 렌더링, 각각 5프레임 뒤 종료, 다른 작업 폴더에서의 리소스 로딩을 확인했다. 실제 SDL 출력 캡처에서 800×600 크기, 현실의 단절·그림자 다리, 원본 건물·지면 정렬을 확인했다.

키 입력·포커스 처리와 예외 시 종료는 자동 검사로 확인했다. 사람이 직접 키보드를 조작한 플레이 테스트, 실제 이동·충돌·점프·퍼즐 밸런스 검증은 수행하지 않았다. 현재 자동 검사의 시간 비교는 루프의 스텝 수 검사이며 플레이어 물리 검증이 아니다.
