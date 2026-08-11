#!/usr/bin/env python3
"""
Zuglänge je Halt — aus Wagenzahl, Kupplung (Flügelung) und coupledSection
(Kapazitätsverstärkung) errechnet, für den Abgleich gegen reale
Bahnsteiglängen (siehe tools/overpass_platforms.py).

Längenmaßstab (~26,2 m/Wagen, aus den takt.rolling-Angaben der App
abgeleitet): 3=80m · 4=105m · 5=130m · 6=156m · 7=184m · 8=210m.
Gekuppelte Verbände addieren sich (z.B. 3+6=236m).

Nutzung:
    python3 tools/lengths.py --data data/lines.json --out data/train_lengths.json
"""
import argparse
import collections
import json
import pathlib

CAR_LENGTH_M = {3: 80, 4: 105, 5: 130, 6: 156, 7: 184, 8: 210}


def car_length(n_cars):
    return CAR_LENGTH_M.get(n_cars, round(n_cars * 26.2))


def stop_index(variant, name):
    for i, s in enumerate(variant["stops"]):
        if s["name"] == name:
            return i
    return None


def extra_cars_per_stop(variant):
    """Zusätzliche Wagen je Halt-Index aus coupling (Flügelung, Partner mit
    eigener Wagenzahl) bzw. coupledSection (reine Kapazitätsverstärkung,
    kein eigener Linienpartner)."""
    sl = variant["stops"]
    n = len(sl)
    extra = [0] * n

    cp = variant.get("coupling")
    if cp:
        a = stop_index(variant, cp["coupledFrom"]) if cp.get("coupledFrom") else 0
        b = stop_index(variant, cp["coupledTo"]) if cp.get("coupledTo") else n - 1
        if a is not None and b is not None:
            for i in range(a, b + 1):
                extra[i] = cp["partnerCars"]

    cs = variant.get("coupledSection")
    if cs:
        a = stop_index(variant, cs["from"]) if cs.get("from") else 0
        b = stop_index(variant, cs["to"]) if cs.get("to") else n - 1
        if a is not None and b is not None:
            for i in range(a, b + 1):
                extra[i] = cs["extraCars"]

    return extra


def train_length_per_stop(data):
    """Für jede Station: die längste dort verkehrende Zugkomposition über
    alle Richtungsvarianten hinweg (= Bahnsteig-Mindestlänge)."""
    max_len = collections.defaultdict(int)
    who = collections.defaultdict(list)

    for k, v in data.items():
        extra = extra_cars_per_stop(v)
        for i, s in enumerate(v["stops"]):
            if extra[i]:
                length = car_length(v["cars"]) + car_length(extra[i])
                cars_desc = f"{v['cars']}+{extra[i]}"
            else:
                length = car_length(v["cars"])
                cars_desc = str(v["cars"])
            who[s["name"]].append({"key": k, "line": v["name"], "cars": cars_desc, "length_m": length})
            if length > max_len[s["name"]]:
                max_len[s["name"]] = length

    out = []
    for st, L in max_len.items():
        top = sorted(who[st], key=lambda x: -x["length_m"])[0]
        out.append(
            {
                "station": st,
                "max_length_m": L,
                "line": top["line"],
                "key": top["key"],
                "cars": top["cars"],
                "all_variants": sorted(who[st], key=lambda x: -x["length_m"]),
            }
        )
    return sorted(out, key=lambda r: -r["max_length_m"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--out", default="data/train_lengths.json")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    result = train_length_per_stop(data)

    pathlib.Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    over210 = sum(1 for r in result if r["max_length_m"] > 210)
    print(f"{len(result)} Stationen -> {args.out} ({over210} davon über 210 m)")


if __name__ == "__main__":
    main()
