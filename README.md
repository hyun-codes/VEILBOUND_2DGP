# VEILBOUND

현실과 그림자 세계를 전환하며 길을 연결하고 위험을 피하는 2D 퍼즐 플랫폼 게임이다. Python + pico2d로 개발하고 Tiled로 맵을 편집한다. 플레이어의 무기·공격 기능은 사용하지 않는다.

## 현재 상태와 실행

Stage 1 이동 기반을 구현했다. 무기 없는 대기·달리기·점프 시작·낙하·착지 모션, 좌우 이동·점프·고체 충돌, 3배 확대 추적 카메라와 추락 복귀를 사용할 수 있다. Shift 세계 전환·출구 클리어·사망 모션은 아직 없으며 Stage 2~3은 계획 문서만 있다.

Windows의 Python 3.13.15, pico2d 1.5.1, PySDL2 0.9.17, pysdl2-dll 2.32.10에서 실행을 확인했다. 현재 환경에는 이미 설치되어 있었으며 새 환경은 다음과 같이 준비한다.

```powershell
cd D:\VEILBOUND_2DGP
python -m pip install -r requirements.txt
python main.py
```

A/D 또는 좌우 방향키로 이동하고 Space로 점프한다. W/S에는 동작을 배정하지 않는다. R은 플레이어·입력·카메라를 시작 상태로 복구한다. F1은 시작·출구 마커와 플레이어 충돌체를 표시/숨긴다. Esc 또는 창 닫기는 종료한다. 포커스를 잃으면 갱신을 멈추고 이동 입력·점프 버퍼·누적 시간을 비운다. 카메라는 자동 추적하며 상하 방향키로 직접 움직이지 않는다.

```powershell
python main.py --world shadow
python main.py --check-map
python -m unittest discover -s tests -v
```

`--world shadow`는 그림자 상태로 고정해 다리 위 이동을 시험하는 옵션이다. R 재시작도 선택한 세계를 유지한다. 실제 플레이 중 Shift 세계 전환은 아직 없다. `--check-map`은 창을 열지 않고 맵을 검사한다. 다른 폴더에서도 `python D:\VEILBOUND_2DGP\main.py`로 실행할 수 있다.

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

Tiled에서 편집할 때는 `assets/`, `maps/tilesets/`, `maps/stage_01/` 구조를 함께 유지한다. 원본 이미지·프레임 설정·맵 타일 배치는 변경하지 않았다. 지면 TSJ의 윗면 타일 5개에 collisionTop=7을 추가해 투명 여백 아래의 실제 지면과 충돌을 맞췄다.

## 확인 범위

2026-11-06: 자동 검사 36개 통과. A/D와 방향키의 중복 입력·해제·반대 방향 입력과 포커스 복귀를 검사하고 실제 SDL의 A/D 누름·해제 변환도 확인했다. 지면 y=183 정렬, 타일 경계 이동, 옆면·천장·착지, 점프 유예 0.08초·입력 버퍼 0.10초와 공중 추가 점프 금지, 키 유지·포커스·재시작, 30/60 FPS의 동일 물리 입력 결과를 검사했다. 현실의 점프 시작 시점을 110가지로 바꾼 검사에서 다리 우회가 없었고 그림자 고정 상태에서는 출구 영역까지 걸어갔다.

실제 800×600 pico2d 창의 SDL 이벤트 큐에 시험 입력을 넣어 달리기·점프·반전·추락 복귀·그림자 다리 통과·창 닫기를 확인했다. 캡처에서 원본 모션·발 위치와 카메라 이동을 시각 확인했다. 사람이 직접 조작한 플레이 테스트와 감각·가독성 평가는 아직이다. Shift 전환·클리어·사망 연출은 검증 대상에 포함하지 않는다.

실제 창 검사를 재현하려면 다음 명령을 사용한다. 캡처는 지정 폴더에 BMP로 저장하며 일반 자동 검사에서는 창을 열지 않는다.

```powershell
python tests/native_movement_check.py --output "$env:TEMP\veilbound-movement-check"
```

현재 시험 수치: 이동 64px/s, 점프 초기 속도 180px/s, 중력 720px/s², 충돌체 6×14px. 월드 좌표 기준이며 최종 조작감은 플레이 후 조정한다. 현실의 틈에서는 추락 복귀만 가능하고, 그림자 다리는 고정 실행 옵션으로만 확인할 수 있다.
