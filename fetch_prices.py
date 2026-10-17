"""
상점 가격표(VP)를 받아 prices.js / prices.json 으로 저장합니다.
가격은 계정과 무관한 공개 정보라서, 개발자가 가끔 한 번 만들어 사이트와 함께 올리면
방문자는 아무것도 할 필요가 없습니다. (방문자 PC에서 토큰을 읽을 필요도 없습니다.)

HenrikDev API(비공식 커뮤니티 API)의 store-offers 를 사용하며 API 키가 필요합니다.
  발급 방법: https://docs.henrikdev.xyz 참고

키는 파일에 적지 말고 환경변수로 넘기세요. (키가 담긴 파일을 GitHub에 올리면 안 됩니다)
  PowerShell:
      $env:HENRIK_KEY="발급받은키"
      python fetch_prices.py
  명령 프롬프트(cmd):
      set HENRIK_KEY=발급받은키
      python fetch_prices.py

실행 후 생긴 prices.js 를 index.html 과 같은 폴더에 두고 커밋하면 됩니다.
상점에서 현재 판매하지 않는 스킨(이벤트, 배틀패스 등)은 없을 수 있고,
그런 항목은 화면에서 등급별 추정가(~)로 표시됩니다.
"""
import json, os, sys

import requests

VP_ID = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://api.henrikdev.xyz/valorant/v1/store-offers"


def main():
    key = os.environ.get("HENRIK_KEY") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not key:
        sys.exit("HENRIK_KEY 환경변수(또는 첫 번째 인자)로 API 키를 넘겨 주세요.")

    res = requests.get(URL, headers={"Authorization": key}, timeout=60)
    print(f"HTTP {res.status_code}")
    if res.status_code != 200:
        print(res.text[:500])
        sys.exit("가격표를 받지 못했습니다. 키와 응답 내용을 확인하세요.")

    data = res.json().get("data") or {}
    offers = data.get("Offers", [])
    prices = {}
    for o in offers:
        vp = (o.get("Cost") or {}).get(VP_ID)
        rewards = o.get("Rewards") or []
        # 번들(여러 아이템을 한 가격에 파는 오퍼)은 개별 가격이 아니므로 제외
        if vp is None or len(rewards) != 1:
            continue
        prices[o["OfferID"]] = vp
        prices[rewards[0]["ItemID"]] = vp
    print(f"오퍼 {len(offers)}개 중 VP 개별 가격 {len(prices)}개")
    if not prices:
        sys.exit("VP 가격을 찾지 못했습니다. 응답 형식이 바뀌었을 수 있습니다.")

    with open(os.path.join(HERE, "prices.json"), "w", encoding="utf-8") as f:
        json.dump(prices, f, separators=(",", ":"))
    with open(os.path.join(HERE, "prices.js"), "w", encoding="utf-8") as f:
        f.write("window.PRICE_TABLE=" + json.dumps(prices, separators=(",", ":")) + ";")
    print("저장 완료: prices.json, prices.js")


if __name__ == "__main__":
    main()
