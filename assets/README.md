# 에셋

Stage 1 전용 배경과 공용으로 쓸 수 있는 지형·소품 PNG를 직접 제작했다. 좌표와 충돌은 Tiled의 방 데이터가 결정한다.

- `environments/stage_01/pump_hall.png`는 방 크기에 맞춘 264×200 배경이다.
- `tiles/stone_ledge.png`와 `tiles/lantern_ledge.png`는 가로로 반복해 그리는 16×16 바닥과 16×5 발판이다.
- `props/exit_door.png`는 13×24 셀 두 개에 일반 문과 도착 후 문을 담았다.
- `characters/player/lantern_keeper.png`는 16×18 셀 일곱 개에 대기, 걷기 네 장, 점프, 낙하를 담았다. 발 기준점은 (8, 16)이다.
- `props/lantern.png`(7×9)는 들거나 내려놓을 때 공유한다. `props/lantern_socket.png`(10×7)는 세 받침대에 반복 배치한다.
