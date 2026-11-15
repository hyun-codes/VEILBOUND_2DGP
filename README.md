# VEILBOUND

등불을 옮겨 어둠 속 발판을 드러내는 2D 퍼즐 플랫폼 게임이다. Python과 pico2d로 실행하고 Tiled에서 방을 편집한다.

```powershell
python -m pip install -r requirements.txt
python main.py
```

A/D 또는 좌우 방향키로 이동하고 Space로 점프한다. 등불이나 빈 받침대 근처에서 E를 눌러 등불을 드는 동작과 내려놓는 동작을 한다. R은 방을 다시 시작하고 Esc는 종료한다.

첫 방에서 등불을 들면 근처 받침대와 바닥이 드러난다. 바닥과 발판은 빛이 닿는 부분만 밟을 수 있다. 다른 받침대에 놓으면 빛이 더 멀리 닿는다.

첫 방의 출구는 Stage 2 왕복 탐조등으로 이어진다. 두 번째 방부터 시험하려면 `python main.py --stage 2`를 실행한다.

- [제품 기준](PRD.md)
- [Tiled 맵](maps/stage_01/stage1_lantern_room.tmj)
- [맵 편집 안내](maps/README.md)
- [이전 버전](https://github.com/hyun-codes/VEILBOUND_2DGP/tree/6217a1a38e8b72c7476d2d62ce08eae345344f0a)
