# VEILBOUND

광원 구슬을 옮겨 어둠 속 발판을 드러내는 2D 퍼즐 플랫폼 게임이다. Python과 pico2d로 실행하고 Tiled에서 방을 편집한다.

```powershell
python -m pip install -r requirements.txt
python main.py
```

타이틀에서 W/S 또는 위아래 방향키로 항목을 고르고 Enter나 Space로 선택한다. 마우스로 클릭해도 된다. PLAY는 1스테이지를 시작하며, SETTINGS에서 조작법을 확인하고 메뉴 구슬 움직임을 켜거나 끌 수 있다.

A/D 또는 좌우 방향키로 이동하고 Space로 점프한다. 광원 구슬 근처에서 E를 누르면 가슴의 빈 고리에 들어가며 가슴 중심에서 빛이 퍼진다. 다시 E를 누르면 그 자리에 내려놓는다. 빈 받침대나 투입구 앞에서 E를 누르면 장치에 광원 구슬을 넣는다. R은 방을 다시 시작하고 Esc는 종료한다.

첫 방에서 광원 구슬을 들면 근처 받침대와 바닥이 드러난다. 바닥과 발판은 빛이 닿는 부분만 밟을 수 있다. 다른 받침대에 놓으면 빛이 더 멀리 닿는다.

기본 진행은 노란 우비 아이가 어둠 속에서 헤어진 동생을 찾는 10개 스테이지다. 스테이지 사이에는 통로가 이어진다. 기상과 엔딩 연출 중에는 Space를 새로 눌러 길게 유지하면 넘길 수 있다. `python main.py --stage 6`처럼 1~10 중 번호를 지정하면 해당 방부터 시험한다.

- [제품 기준](PRD.md)
- [Tiled 맵](maps/stage_01/story.tmj)
- [스토리 캠페인과 검증](maps/story_campaign.md)
- [맵 편집 안내](maps/README.md)
- [이전 버전](https://github.com/hyun-codes/VEILBOUND_2DGP/tree/6217a1a38e8b72c7476d2d62ce08eae345344f0a)
