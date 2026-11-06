# 맵 관리

스테이지별 배치와 기록은 각 `stage_XX/` 폴더에 둔다. 공통 타일셋은 `tilesets/`, 이미지 원본은 프로젝트의 `assets/`에서 공유한다.

| 스테이지 | 문서 | 맵 상태 |
| --- | --- | --- |
| 1: 사라진 다리 | [설계·에셋 분석·검증 기록](stage_01/README.md) | [TMJ](stage_01/stage1_missing_bridge.tmj), 자동·SDL 경로 검증, 사람의 평가 전 |
| 2: 뒤틀린 계단 | [퍼즐 원형·검증](stage_02/README.md) | [가로등 퍼즐 TMJ](stage_02/stage2_lamp_room.tmj), 자동·SDL 경로 검증, 사람의 평가 전 |
| 3: 위험한 골목 | [제작 계획](stage_03/README.md) | 아직 TMJ 없음 |

## 공통 타일셋

- [지면 타일셋](tilesets/outer_city.tsj)
- [건물·소품 타일셋](tilesets/outer_city_props.tsj)

Tiled 공식 문서는 여러 맵이 메타데이터를 공유할 수 있도록 외부 타일셋 사용을 권장한다. 스테이지마다 TSJ와 원본 이미지를 복사하지 않는다. 공통 타일 속성·충돌 정보를 수정하면 이를 참조하는 모든 맵이 영향을 받으므로 함께 검증한다.

## 경로 규칙

경로는 참조가 적힌 파일의 위치에서 해석한다.

| 참조 | 예시 |
| --- | --- |
| Stage 1 TMJ에서 공유 TSJ | `../tilesets/outer_city.tsj` |
| 공유 TSJ에서 원본 PNG | `../../assets/Outer City/Outer_City_Tileset.png` |
| Stage 1 TMJ 이미지 레이어에서 PNG | `../../assets/Outer City/Outer_City_Sky_BG.png` |

새 맵은 저장소 내부 상대경로를 사용한다. 폴더 이동 후에는 TMJ·TSJ를 파싱해 이미지 실존 여부를 검사하고 Tiled로 로드해 확인한다. Stage 1은 별도 수정으로 Common 그룹 오프셋을 `(0,0)`으로 정리해 시작점·다리·출구의 좌표 정렬을 검증했다. 수정 근거와 남은 플레이 검증은 [PRD 7.2장](../PRD.md#72-stage-1-정렬-수정-기록)에 기록되어 있다.

화면 크기·카메라 요구사항은 [PRD](../PRD.md)를 따른다. 기존 맵의 `pixelScale=2` 같은 표시 메타데이터는 과거 값이다. 현재 실행 미리보기는 이를 읽지 않고 app.py의 정수 3배·전체 창 설정을 사용한다. 추적 카메라와 맵 설정을 데이터로 연결할 때 동기화한다. 실행 방법은 [루트 README](../README.md)를 따른다.

근거: [Tiled 공식 문서: 외부 타일셋](https://doc.mapeditor.org/en/stable/manual/editing-tilesets/).
