# 에셋

타이틀 저수조 배경은 `ui/title_reservoir.png`에 있다. 타이틀에서 사용하는 [Cinzel 라이선스](ui/fonts/Cinzel-OFL.txt)는 글꼴과 함께 넣었다.

Stage 1 전용 배경과 공용으로 쓸 수 있는 지형·소품 PNG를 직접 제작했다. 좌표와 충돌은 Tiled의 방 데이터가 결정한다.

- `environments/stage_01/pump_hall.png`는 방 크기에 맞춘 264×200 배경이다.
- `environments/stage_01/lantern_darkness.png`는 빛의 중심부터 가장자리까지 어두워지는 221×221 투명도 마스크다. 등불 위치와 상태에 맞춰 확대해 그린다.
- `tiles/stone_ledge.png`와 `tiles/lantern_ledge.png`는 가로로 반복해 그리는 16×16 바닥과 16×5 발판이다.
- `props/exit_door.png`는 13×24 셀 두 개에 일반 문과 도착 후 문을 담았다.
- `characters/player/raincoat_child.png`는 21×22 셀 일곱 개에 대기, 걷기 네 장, 상승, 낙하를 담았다. 발 기준점은 (10, 20), 가슴 구멍의 중심은 (10, 13)이다.
- `characters/player/raincoat_child_death.png`는 같은 기준점을 사용하는 21×22 셀 여섯 장에 노란 후드 아이가 쓰러지는 모션을 담았다.
- `props/light_orb.png`는 바닥·받침대에 놓인 구슬, 고정 조명, 가슴에 끼운 광원을 담았다. `props/lantern_socket.png`(10×7)는 구슬 받침대에 재사용한다.

Stage 2의 발판은 `tiles/stage_02/`의 기계 부품 세 종류를 사용한다. 구부러진 배관은 완만한 계단, 깨진 기어는 가파른 층계, 터빈 날개는 기울어진 착지면으로 그렸다. Tiled에서 볼 수 있는 발판 배치와 충돌 윤곽은 [맵 편집 안내](../maps/README.md)에 있다.

Stage 2의 `environments/stage_02/hoist_chain.png`는 사슬 고리와 톱니를 두 줄로 나눠 각 131×75 프레임 여덟 개를 담는다. 고리는 운반대가 이동할 때 최대 2화면 픽셀 위아래로 움직이며, 톱니는 고정된 축에서 회전한다. `props/chain_carriage.png`는 사슬을 따라 움직이는 13×13 광원 운반대다.

Stage 3의 투광기는 `props/projector_stand.png`와 회전하는 구리·은색 렌즈 헤드로 구성한다. `props/lens_receiver.png`의 두 셀은 벽에 붙은 수광부의 소등·점등 상태다.

`props/brass_key.png`는 Stage 2와 Stage 3에서 사용하는 14×10 황동 열쇠다. 열쇠 오브젝트의 가운데와 바닥을 기준으로 놓이며 방의 조명에 따라 드러난다.

`props/cargo_crate.png`는 Stage 4의 16×16 운반 상자다. 금속 모서리와 대각 보강대로 일반 발판과 구분한다.

Stage 6의 배경은 `environments/stage_06/reservoir_hall.png`, 투입관과 배수 배관은 같은 폴더의 `pump_fittings.png`에 있다. 물은 `reservoir_water.png`의 표면 프레임 두 장을 반복하며, `props/drain_valve.png`는 밸브의 소등·전원·배수 방향 상태를 그린다.
