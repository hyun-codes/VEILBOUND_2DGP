# 맵 편집

맵은 스테이지별로 `maps/stage_01/` 같은 폴더에 둔다. [등불의 방](stage_01/stage1_lantern_room.tmj)은 264×200 월드 픽셀의 Tiled 맵이다. 오브젝트 좌표는 월드 픽셀로 입력한다.

- `PlayerStart`는 시작 등불이 비추는 지면 위의 점이다.
- `Socket`은 지면 위의 받침대 점이다. 정확히 한 곳에 Boolean `initial=true`를 설정한다.
- `Ground`와 `LightPlatform`은 석재 지면과 발판이다. `Wall`과 `Box`도 사각형으로 배치하며, 각 사각형은 빛이 닿는 부분만 충돌한다.
- `Key` 사각형은 빛이 닿은 부분과 플레이어가 겹치면 획득한다. 열쇠가 있는 방에서는 전부 모은 뒤 밝은 `Exit` 영역에 도달한다.

`python main.py --check-map`으로 편집 결과를 검사한다.

Stage 2 [발판 배치 초안](stage_02/platform_samples.tmj)은 낮은 배관에서 오른쪽으로 이동해 기어를 오른 뒤, 위쪽에서 왼쪽으로 돌아가는 형태다. [기계 부품 타일셋](tilesets/stage2_machinery.tsj)의 Tile Collision Editor에서 불투명 픽셀을 따라 만든 충돌 윤곽도 볼 수 있다. 이 맵은 Tiled 편집용이며 게임의 Stage 2 연결과 탐조등 퍼즐 배치는 후속 작업이다.
