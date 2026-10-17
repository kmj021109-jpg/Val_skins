# 발로란트 스킨 조합기

총, 변형(크로마), 총기장식, 플레이어 카드, 스프레이, 플렉스를 직접 조합해 보고
색이 어울리는 순서로 추천받는 비공식 팬 프로젝트입니다.

- 이 프로젝트는 Riot Games와 관련이 없으며 Riot Games의 보증을 받지 않았습니다.
- VALORANT 및 관련 이미지, 이름은 Riot Games의 상표 또는 자산입니다.
- 아이템 정보와 이미지는 [valorant-api.com](https://valorant-api.com)에서 가져옵니다.
- 가격이 `~`로 표시되면 상점가가 아니라 등급별 추정가입니다.

## 내 보유 목록 쓰기 (선택)

화면 오른쪽 아래 "owned.js 만드는 법"을 따라 PC에서 `fetch_owned.py`를 실행하고,
생긴 `owned.json`을 "보유 목록 불러오기"로 선택하세요.
라이엇 비공식 내부 API를 쓰는 방식이라 언제든 막힐 수 있고, 모든 처리는 내 PC에서만 일어납니다.
토큰은 저장하지 않고, `owned.js` / `owned.json`은 서버에 올리지 마세요(.gitignore에 포함).

## 개발자용

색을 미리 계산해 두면 방문자 브라우저가 색을 계산하지 않아 빠르고 결과도 일정합니다.

    pip install requests pillow
    python precompute_colors.py          # colors.json / colors.js 생성 (이어하기 지원)
    python precompute_colors.py --force  # 분류 기준을 바꿨을 때 전체 재계산

색이 틀린 항목은 `color_overrides.json`에 `{"아이템 이름 또는 id": "blue"}` 형식으로 적고 다시 실행합니다.
계열: red orange yellow green cyan blue purple pink light gray dark

## 배포 (GitHub Pages)

1. `python precompute_colors.py` 실행 후 `colors.js`가 생겼는지 확인
2. 이 폴더에서 `git init`, `git add .`, `git status`로 `owned.js` 등이 목록에 없는지 확인
3. `git commit -m "init"` 후 GitHub에 새 저장소를 만들고 안내대로 `git push`
4. 저장소 Settings → Pages → Branch를 `main`, 폴더를 `/ (root)`로 지정
5. 몇 분 뒤 `https://<아이디>.github.io/<저장소 이름>/`에서 접속
