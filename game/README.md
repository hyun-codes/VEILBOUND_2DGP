# 게임 코드

루트의 `main.py`가 `game/app.py`의 실행과 입력 처리를 호출한다. `lantern_room.py`는 등불, 발판, 플레이어 상태를 관리하고 `lantern_view.py`는 방을 그린다. 맵 로딩, 카메라 좌표, 충돌과 고정 시간 갱신은 각 공통 모듈에서 처리한다.

`title_screen.py`는 시작 화면의 메뉴 입력과 그리기를 맡는다. `--stage`를 지정하면 해당 방으로 바로 들어간다.

점프는 `lantern_room.py`의 공통 물리로 처리한다. `app.py`는 Space의 누른 순간과 유지 상태(`jump_held`)를 각각 전달한다. 기존 입력 재생 호출은 유지 상태를 생략하면 최대 높이 점프로 실행된다. 발판 이탈 유예 0.10초, 착지 입력 버퍼 0.12초, 최소 상승 0.06초와 버튼 해제 후 상승 중력 2400, 상승/하강 중력 960/1056, 1픽셀 천장 모서리 보정을 적용한다. 코요테 타임은 마지막 지지면이 현재 빛 충돌에도 남아 있어야 유효하다. 모서리 보정도 현재 밝은 고체와 이동 경로를 검사한다.

설계 참고: [Celeste 개발자의 입력 보정 설명](https://www.mattmakesgames.com/articles/celeste_and_forgiveness/index.html), [Kyle Pittman의 Building a Better Jump 발표 소개](https://www.gdcvault.com/play/1023148/Math-for-Game-Programmers-Building). 적용 수치와 빛 소멸 시 예외는 VEILBOUND의 설계 판단이다. 정점 체공 보정이나 수평 관성은 추가하지 않았다. `tests/test_jump.py`는 입력 유예·만료, 빛 소멸, 높이 조절, 모서리/천장 충돌, 실제 앱의 Space 유지·해제 전달을 검사한다.

착지 전 저장된 점프는 착지 프레임에 시작한다. 해제 후 다시 Space를 유지해도 같은 점프의 제동을 취소하지 않는다. 조사 범위·측정값과 검증 한계는 [점프 조작 개선 기록](../docs/jump_controls.md)을 따른다.
