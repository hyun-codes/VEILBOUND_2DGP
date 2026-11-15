# 맵 편집

맵은 스테이지별로 `maps/stage_01/` 같은 폴더에 둔다. [등불의 방](stage_01/stage1_lantern_room.tmj)은 264×200 월드 픽셀의 Tiled 맵이다. 오브젝트 좌표는 월드 픽셀로 입력한다.

- `PlayerStart`는 영구 지면 위의 점이다.
- `Socket`은 영구 지면 위의 받침대 점이다. 정확히 한 곳에 Boolean `initial=true`를 설정한다.
- `Ground`는 영구 지면, `LightPlatform`은 빛에 반응하는 발판을 나타내는 사각형이다. 발판 윗면 가운데가 조명 판정점이다.
- `Exit`는 출구 영역을 지정하는 사각형이다.

`python main.py --check-map`으로 편집 결과를 검사한다.
