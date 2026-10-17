"""
모든 아이템(스킨, 변형, 총기장식, 카드, 스프레이, 플렉스)의 대표색을 미리 계산해
colors.json / colors.js 로 저장합니다. 웹페이지는 이 파일이 있으면 브라우저에서 색을
다시 계산하지 않아 훨씬 빠르고, 누가 열어도 결과가 같습니다.

사용법
  pip install requests pillow
  python precompute_colors.py            # 새로 생긴 아이템만 계산 (이어하기)
  python precompute_colors.py --force    # 전부 다시 계산 (분류 기준을 바꿨을 때)

색이 틀린 항목 수동 보정
  color_overrides.json 에 아이템 id 또는 화면에 보이는 이름과 색 계열을 적고 다시 실행하세요.
  예) {"프라임 밴달": "blue", "2a6c...-uuid": "dark"}
  계열: red orange yellow green cyan blue purple pink light gray dark
"""
import argparse, io, json, math, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

API = "https://valorant-api.com/v1/"
HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = re.compile(r"스탠다드|무작위|Standard|Random")
FAM_COLOR = {
    "red": [0, 0.8, 0.5], "orange": [30, 0.8, 0.5], "yellow": [55, 0.8, 0.5],
    "green": [120, 0.8, 0.45], "cyan": [185, 0.8, 0.5], "blue": [225, 0.8, 0.55],
    "purple": [280, 0.8, 0.55], "pink": [325, 0.8, 0.6],
    "light": [-1, 0, 0.8], "gray": [-1, 0, 0.45], "dark": [-1, 0, 0.15],
}


def get(path):
    r = requests.get(API + path, params={"language": "ko-KR"}, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def collect():
    """id -> (이미지 URL, 종류 gun/icon, 표시 이름)"""
    items, alias = {}, {}
    for w in get("weapons"):
        for s in w["skins"]:
            if SKIP.search(s["displayName"]):
                continue
            lv, ch = s.get("levels") or [], s.get("chromas") or []
            img = (s.get("displayIcon")
                   or (lv[0].get("displayIcon") if lv else None)
                   or (ch[0].get("fullRender") if ch else None))
            if not img:
                continue
            items[s["uuid"]] = (img, "gun", s["displayName"])
            alias[s["uuid"] + "-base"] = s["uuid"]  # 화면의 '기본' 변형은 스킨과 같은 이미지
            for c in ch:
                url = c.get("fullRender") or c.get("displayIcon")
                if url:
                    items[c["uuid"]] = (url, "gun", c["displayName"])
    for b in get("buddies"):
        if b.get("displayIcon"):
            items[b["uuid"]] = (b["displayIcon"], "icon", b["displayName"])
    for c in get("playercards"):
        url = c.get("smallArt") or c.get("displayIcon")
        if url:
            items[c["uuid"]] = (url, "icon", c["displayName"])
    for s in get("sprays"):
        url = s.get("fullTransparentIcon") or s.get("displayIcon")
        if url:
            items[s["uuid"]] = (url, "icon", s["displayName"])
    for f in get("flex"):
        if f.get("displayIcon"):
            items[f["uuid"]] = (f["displayIcon"], "icon", f["displayName"])
    return items, alias


def analyze(data, gun):
    """index.html 의 analyze() 와 같은 방식 (총: 포인트 색 우선, 아이콘: 면적 우선)"""
    s_min, cov = (0.3, 0.03) if gun else (0.18, 0.12)
    im = Image.open(io.BytesIO(data)).convert("RGBA").resize((32, 32), Image.BILINEAR)
    bx, by, bw = [0.0] * 12, [0.0] * 12, [0.0] * 12
    n = cc = 0
    sl = viv = 0.0
    for r, g, b, a in im.getdata():
        if a < 128:
            continue
        r, g, b = r / 255, g / 255, b / 255
        mx, mn = max(r, g, b), min(r, g, b)
        l, df = (mx + mn) / 2, mx - mn
        s = 0 if df == 0 else df / (1 - abs(2 * l - 1))
        h = 0.0
        if df:
            if mx == r:
                h = ((g - b) / df) % 6
            elif mx == g:
                h = (b - r) / df + 2
            else:
                h = (r - g) / df + 4
            h *= 60
        n += 1
        sl += l
        if s < s_min or l < 0.1 or l > 0.93:
            continue
        w = s * (1 - abs(2 * l - 1)) if gun else s
        cc += 1
        viv += s
        k = int(h // 30) % 12
        bw[k] += w
        bx[k] += w * math.cos(math.radians(h))
        by[k] += w * math.sin(math.radians(h))
    if not n:
        return None
    L = round(sl / n, 2)
    if cc / n < cov:
        return [-1, 0, L]
    best = max(range(12), key=lambda k: bw[k] + bw[(k - 1) % 12] + bw[(k + 1) % 12])
    ks = (best, (best - 1) % 12, (best + 1) % 12)
    X, Y = sum(bx[k] for k in ks), sum(by[k] for k in ks)
    h = math.degrees(math.atan2(Y, X)) % 360
    return [round(h), round(min(1, viv / cc), 2), L]


def work(args):
    uid, (url, kind, _name) = args
    for attempt in range(3):
        try:
            res = requests.get(url, timeout=30)
            res.raise_for_status()
            return uid, analyze(res.content, kind == "gun")
        except Exception:
            time.sleep(1 + attempt)
    return uid, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    opt = ap.parse_args()

    path = os.path.join(HERE, "colors.json")
    colors = {}
    if os.path.exists(path) and not opt.force:
        colors = json.load(open(path, encoding="utf-8"))

    items, alias = collect()
    todo = [(u, v) for u, v in items.items() if u not in colors]
    print(f"전체 {len(items)}개 중 새로 계산할 항목 {len(todo)}개")

    done = 0
    with ThreadPoolExecutor(opt.workers) as ex:
        for uid, col in ex.map(work, todo):
            if col:
                colors[uid] = col
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(todo)}")
    for a, src in alias.items():
        if src in colors:
            colors[a] = colors[src]

    ov_path = os.path.join(HERE, "color_overrides.json")
    if os.path.exists(ov_path):
        ov = json.load(open(ov_path, encoding="utf-8"))
        names = {}
        for u, (_, _, name) in items.items():
            names.setdefault(name, []).append(u)
        applied = 0
        for key, fam in ov.items():
            if fam not in FAM_COLOR:
                print(f"[무시] {key}: 알 수 없는 계열 {fam}")
                continue
            for u in ([key] if key in items or key in alias else names.get(key, [])):
                colors[u] = FAM_COLOR[fam]
                applied += 1
        print(f"수동 보정 {applied}개 적용")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(colors, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HERE, "colors.js"), "w", encoding="utf-8") as f:
        f.write("window.COLORS=" + json.dumps(colors, ensure_ascii=False, separators=(",", ":")) + ";")
    print(f"저장 완료: colors.json, colors.js ({len(colors)}개)")


if __name__ == "__main__":
    sys.exit(main())
