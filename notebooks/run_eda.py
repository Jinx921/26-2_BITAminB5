"""EDA 전체 실행 → 터미널 출력 + outputs/tables/*.csv + manifest.json"""
import sys, pathlib, json, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
import config as C
from eda import all_tables

pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 60)

def slug(i, s):
    keep = ''.join(ch if ch.isalnum() else '_' for ch in s)
    return f"{i:02d}_{keep.strip('_')[:40]}"

def main():
    t0 = time.time()
    C.TABLES.mkdir(parents=True, exist_ok=True)
    manifest, i = [], 0
    for group, tables in all_tables():
        print(f"\n{'#'*80}\n# {group}\n{'#'*80}")
        for title, df, note in tables:
            i += 1
            name = slug(i, title)
            path = C.TABLES / f"{name}.csv"
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f"\n[{i}] {title}\n{'-'*len(title)}")
            print(df.to_string(index=False))
            print(f"  ※ {note}")
            manifest.append({'group': group, 'title': title, 'note': note, 'file': path.name,
                             'columns': [str(c) for c in df.columns],
                             'rows': df.astype(object).where(pd.notna(df), None).values.tolist()})
    out = C.OUTPUTS / 'eda_manifest.json'
    out.write_text(json.dumps(manifest, ensure_ascii=False, default=str), encoding='utf-8')
    print(f"\n{'='*80}\n표 {len(manifest)}개 저장 → {C.TABLES}\nmanifest → {out}\n소요 {time.time()-t0:.1f}초")

if __name__ == '__main__':
    main()
