# 생성 경로

내장 image_gen 사용. 원본 입력은 `../Individual sprites/Jack1.png`와 `../Individual sprites/Jack18.png`였다. 첫 생성 결과를 대상으로 아래의 수정 요청을 한 번 적용한 파일을 보관했다. 첫 결과는 프로젝트에 등록하지 않았다. transparent_background=true로 요청했지만 반투명 번짐이 남아 검수에서 미통과했다.

## 최종 수정 프롬프트 원문

Edit the first image, a six-frame PUSH RIGHT pixel sprite sheet, with the second tiny original character as identity reference. Keep the first image's exact 1536x1024 canvas and 3-column 2-row grid of 512x512 cells, one pose per cell, feet baseline at cell y352, same six pushing poses and fixed extended empty hands. Correct the rendering ONLY: remove ALL soft glow, haze, vignette, bloom, blur, ground shading and translucent fringe. Entire background must be exactly alpha zero, all sprite pixels exactly alpha255, with hard nearest-neighbor pixel edges and a small flat palette. Each logical pixel must be an exact solid 8x8 square, with no antialiasing or gradients. Retain sparse low resolution instead of detailed new art. Match the original character's small headwear silhouette rather than a large new fedora. Keep character height identical across frames and preserve a smooth alternating leg push cycle. No lamp or other object, no weapons, no text, no labels, no grid borders. Transparent black surroundings shown in input are NOT part of artwork. Output the transparent sprite sheet only, no shadows or effects.
