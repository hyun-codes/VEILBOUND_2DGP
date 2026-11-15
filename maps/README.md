# 맵 편집

맵은 스테이지별로 `maps/stage_01/` 같은 폴더에 둔다. [등불의 방](stage_01/stage1_lantern_room.tmj)은 264×200 월드 픽셀의 Tiled 맵이다. 오브젝트 좌표는 월드 픽셀로 입력한다.

- `PlayerStart`는 시작 등불이 비추는 지면 위의 점이다.
- `Socket`은 지면 위의 받침대 점이다. 정확히 한 곳에 Boolean `initial=true`를 설정한다.
- `Ground`와 `LightPlatform`은 석재 지면과 발판이다. `Wall`과 `Box`도 사각형으로 배치하며, 각 사각형은 빛이 닿는 부분만 충돌한다.
- `Key` 사각형은 빛이 닿은 부분과 플레이어가 겹치면 획득한다. 열쇠가 있는 방에서는 전부 모은 뒤 밝은 `Exit` 영역에 도달한다.

`python main.py --check-map`으로 편집 결과를 검사한다.

[Stage 2 왕복 탐조등](stage_02/stage2_rail_light.tmj)은 오른쪽 덮개를 지나 아래층 열쇠를 얻고, 왼쪽의 터빈 날개로 올라와 출구에 닿는 방이다. 광원은 `RailPoint`를 Tiled 오브젝트 순서대로 왕복한다. `railRadius`, `railSpeed`, `railPause`는 각각 반지름, 초당 이동 픽셀, 지점 체류 시간(초)이다. 받침대에서 `radius`를 지정하면 휴대등을 꽂았을 때의 범위를 정할 수 있다. Machinery 레이어의 타일은 [기계 부품 타일셋](tilesets/stage2_machinery.tsj)에 정의된 충돌 윤곽을 사용한다. [발판 샘플](stage_02/platform_samples.tmj)은 Tiled에서 모양을 비교할 때 쓴다.

[Stage 3 교차 렌즈](stage_03/stage3_crossed_lenses.tmj)는 중앙 조작대에서 두 갈래 열쇠 경로와 위쪽 출구를 비추는 방이다. `Projector` 옆에서 E를 누를 때마다 같은 이름을 `projector` 속성에 적은 `Focus` 지점을 맵 순서대로 바꾼다. 렌즈와 빛은 약 0.6초에 걸쳐 돌아가며, 지형 충돌도 움직이는 빛을 따라 바뀐다. 각 목표점의 `radius`는 비출 범위다. `Receiver`는 투광기 빛을 받으면 켜지며, 출구는 두 열쇠와 모든 수광부가 필요하다. `fixed=true`가 붙은 시작 등불은 중앙 조작대를 비춘다.
