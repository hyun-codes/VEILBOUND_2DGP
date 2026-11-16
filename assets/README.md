# 에셋

Stage 1 전용 배경과 공용으로 쓸 수 있는 지형·소품 PNG를 직접 제작했다. 좌표와 충돌은 Tiled의 방 데이터가 결정한다.

- `environments/stage_01/pump_hall.png`는 방 크기에 맞춘 264×200 배경이다.
- `environments/stage_01/lantern_darkness.png`는 빛의 중심부터 가장자리까지 어두워지는 221×221 투명도 마스크다. 등불 위치와 상태에 맞춰 확대해 그린다.
- `tiles/stone_ledge.png`와 `tiles/lantern_ledge.png`는 가로로 반복해 그리는 16×16 바닥과 16×5 발판이다.
- `props/exit_door.png`는 13×24 셀 두 개에 일반 문과 도착 후 문을 담았다.
- `characters/player/shadow_child.png`는 21×22 셀 일곱 개에 대기, 걷기 네 장, 상승, 낙하를 담았다. 모든 셀의 발과 가슴 중심은 각각 (10, 20), (10, 13)이다.
- `props/light_orb.png`는 바닥·받침대에 놓인 구슬, 고정 조명, 가슴에 끼운 광원을 담았다. `props/lantern_socket.png`(10×7)는 구슬 받침대에 재사용한다.

Stage 2의 발판은 `tiles/stage_02/`의 기계 부품 세 종류를 사용한다. 구부러진 배관은 완만한 계단, 깨진 기어는 가파른 층계, 터빈 날개는 기울어진 착지면으로 그렸다. Tiled에서 볼 수 있는 발판 배치와 충돌 윤곽은 [맵 편집 안내](../maps/README.md)에 있다.

Stage 2의 사슬과 톱니는 `environments/stage_02/hoist_chain.png`에 그려져 있다. `props/chain_carriage.png`는 사슬을 따라 움직이는 13×13 광원 운반대다.

Stage 3의 투광기는 `props/projector_stand.png`와 회전하는 구리·은색 렌즈 헤드로 구성한다. `props/lens_receiver.png`의 두 셀은 벽에 붙은 수광부의 소등·점등 상태다.

`props/brass_key.png`는 Stage 2와 Stage 3에서 사용하는 14×10 황동 열쇠다. 열쇠 오브젝트의 가운데와 바닥을 기준으로 놓이며 방의 조명에 따라 드러난다.

`props/cargo_crate.png`는 Stage 4의 16×16 운반 상자다. 금속 모서리와 대각 보강대로 일반 발판과 구분한다.
