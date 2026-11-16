# VEILBOUND

등불을 옮겨 어둠 속 발판을 드러내는 2D 퍼즐 플랫폼 게임이다. Python과 pico2d로 실행하고 Tiled에서 방을 편집한다.

```powershell
python -m pip install -r requirements.txt
python main.py
```

A/D 또는 좌우 방향키로 이동하고 Space로 점프한다. 등불 근처에서 E로 집고, 들고 있을 때 E로 그 자리에 내려놓는다. 빈 받침대나 투입구 앞에서 E를 누르면 장치에 등불을 넣는다. R은 방을 다시 시작하고 Esc는 종료한다.

첫 방에서 등불을 들면 근처 받침대와 바닥이 드러난다. 바닥과 발판은 빛이 닿는 부분만 밟을 수 있다. 다른 받침대에 놓으면 빛이 더 멀리 닿는다.

기본 진행은 Stage 1 등불의 방 → Stage 2 왕복 탐조등 → Stage 3 교차 렌즈 → Stage 4 화물 승강로 → Stage 5 점등실 순서다. 마지막 방을 바로 시험하려면 `python main.py --stage 5`를 실행한다. 빛이 닿은 등잔에 다가가 E를 누르면 점등된다.

Stage 4에서는 등불을 내려놓고 A/D로 상자에 붙어 걸으면 상자를 민다.

- [제품 기준](PRD.md)
- [Tiled 맵](maps/stage_01/stage1_lantern_room.tmj)
- [맵 편집 안내](maps/README.md)
- [이전 버전](https://github.com/hyun-codes/VEILBOUND_2DGP/tree/6217a1a38e8b72c7476d2d62ce08eae345344f0a)
