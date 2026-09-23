"""report_template.html + outputs/eda_manifest.json → outputs/eda_report.html"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import config as C

HERE = pathlib.Path(__file__).resolve().parent

def main():
    tpl = (HERE / 'report_template.html').read_text(encoding='utf-8')
    man = (C.OUTPUTS / 'eda_manifest.json').read_text(encoding='utf-8')
    out = C.OUTPUTS / 'eda_report.html'
    html = tpl.replace('__MANIFEST__', man)
    if not html.lstrip().startswith('<meta charset'):
        html = '<meta charset="utf-8">\n' + html
    out.write_text(html, encoding='utf-8')
    print(f"{out}  ({out.stat().st_size/1024:.0f}KB)")

if __name__ == '__main__':
    main()
