"""
내 발로란트 보유 아이템(UUID)을 가져와 owned.json / owned.js 로 저장합니다.

사용법
  1) pip install requests
  2) 라이엇 클라이언트로 로그인한 상태에서 발로란트를 실행해 둡니다.
  3) python fetch_owned.py            (한국 서버는 기본값 kr)
     python fetch_owned.py --shard ap (필요하면 서버 지정: kr / ap / na / eu)
  4) 생성된 owned.js 를 valorant-combo.html 과 같은 폴더에 두고 html을 엽니다.

주의
  - 라이엇 공식 지원 API가 아니라 로컬 클라이언트와 내부 API를 쓰는 방식이라 언제든 바뀔 수 있습니다.
  - 토큰은 메모리에서만 쓰고 파일에는 저장하지 않습니다. 아이템 UUID만 저장합니다.
  - 읽기 전용 조회만 합니다. 다른 사람 계정에는 쓰지 마세요.
"""
import argparse, base64, json, os, sys
import requests, urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # 로컬 자체서명 인증서

# 아이템 종류 ID (커뮤니티 문서 기준). 일부가 틀렸거나 바뀌었으면 해당 종류만 건너뜁니다.
ITEM_TYPES = {
    "skin_level": "e7c63390-eda7-46e0-bb7a-a6abdacd2433",
    "skin_chroma": "3ad1b2b2-acdb-4524-852f-954a76ddae0a",
    "buddy": "dd3bf334-87f3-40bd-b043-682a57a8dc3a",
    "player_card": "3f296c07-64c3-494c-923b-fe692a4fa1bd",
    "spray": "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475",
    "flex": "03a572de-4234-31ed-d344-ababa488f981",
}


VP_ID = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"  # VP 통화 ID
# exe로 묶었을 때도 exe가 있는 폴더에 결과 파일을 저장합니다
BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


def read_lockfile():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        sys.exit("Windows의 LOCALAPPDATA를 찾지 못했습니다. 발로란트가 설치된 Windows PC에서 실행하세요.")
    path = os.path.join(base, "Riot Games", "Riot Client", "Config", "lockfile")
    try:
        name, pid, port, password, proto = open(path).read().split(":")
    except FileNotFoundError:
        sys.exit("lockfile이 없습니다. 라이엇 클라이언트/발로란트를 먼저 실행하고 로그인하세요.")
    return port, password, proto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="kr")
    shard = ap.parse_args().shard

    port, pw, proto = read_lockfile()
    r = requests.get(f"{proto}://127.0.0.1:{port}/entitlements/v1/token",
                     auth=("riot", pw), verify=False, timeout=10)
    if r.status_code != 200:
        sys.exit(f"토큰을 받지 못했습니다 ({r.status_code}). 로그인 상태인지 확인하세요.")
    t = r.json()
    access, ent, puuid = t["accessToken"], t["token"], t["subject"]

    version = requests.get("https://valorant-api.com/v1/version", timeout=10).json()["data"]["riotClientVersion"]
    platform = base64.b64encode(json.dumps({
        "platformType": "PC", "platformOS": "Windows",
        "platformOSVersion": "10.0.19042.1.256.64bit", "platformChipset": "Unknown",
    }).encode()).decode()
    headers = {
        "Authorization": f"Bearer {access}",
        "X-Riot-Entitlements-JWT": ent,
        "X-Riot-ClientVersion": version,
        "X-Riot-ClientPlatform": platform,
    }

    items, counts = set(), {}
    for name, type_id in ITEM_TYPES.items():
        url = f"https://pd.{shard}.a.pvp.net/store/v1/entitlements/{puuid}/{type_id}"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"[건너뜀] {name}: HTTP {res.status_code}")
                continue
            ids = [e["ItemID"] for e in res.json().get("Entitlements", [])]
        except Exception as ex:
            print(f"[건너뜀] {name}: {ex}")
            continue
        counts[name] = len(ids)
        items.update(ids)
        print(f"{name}: {len(ids)}개")

    # 상점 기준 가격(VP). 스킨은 1레벨 UUID 기준이며 레벨업/변형 가격은 포함되지 않습니다.
    prices = {}
    try:
        res = None
        for u in ("store/v1/offers", "store/v1/offers/"):
            res = requests.get(f"https://pd.{shard}.a.pvp.net/{u}", headers=headers, timeout=20)
            if res.status_code == 200:
                break
        data = res.json()
        offers = data.get("Offers", []) if isinstance(data, dict) else []
        print(f"가격 조회: HTTP {res.status_code}, 오퍼 {len(offers)}개")
        for o in offers:
            vp = (o.get("Cost") or {}).get(VP_ID)
            if vp is None:
                continue
            prices[o["OfferID"]] = vp
            for rw in o.get("Rewards", []):
                prices[rw["ItemID"]] = vp
        print(f"가격 정보: {len(prices)}개")
        if offers and not prices:
            print("비용 키 예시:", list((offers[0].get("Cost") or {}).keys()))
        if not offers:
            dbg = os.path.join(BASE, "offers_debug.txt")
            with open(dbg, "w", encoding="utf-8") as f:
                f.write(res.text[:2000])
            print("응답 앞부분을 offers_debug.txt에 저장했습니다.")
    except Exception as ex:
        print(f"[건너뜀] 가격 정보: {ex}")

    if not items:
        sys.exit("가져온 항목이 없습니다. --shard 값(kr/ap/na/eu)이나 로그인 상태를 확인하세요.")

    out = sorted(items)
    here = BASE
    with open(os.path.join(here, "owned.json"), "w", encoding="utf-8") as f:
        json.dump({"items": out, "prices": prices, "counts": counts}, f, ensure_ascii=False)
    with open(os.path.join(here, "owned.js"), "w", encoding="utf-8") as f:
        f.write("window.OWNED=" + json.dumps(out) + ";window.PRICES=" + json.dumps(prices) + ";")
    print(f"\n저장 완료: owned.json, owned.js ({len(out)}개 UUID)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e.code)
    finally:
        if getattr(sys, "frozen", False):
            input("\n엔터를 누르면 종료합니다...")