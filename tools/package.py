"""Build host-specific ZIPs from the single skill source; no upload."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills/rental-finder-cn'
VERSION='0.1.0'

def build(destination):
    destination=Path(destination).resolve()
    if destination==SOURCE or SOURCE in destination.parents: raise ValueError('输出不能位于技能源码内')
    destination.mkdir(parents=True,exist_ok=True)
    paths=[]
    for host in ('codex','workbuddy'):
        path=destination/f'rental-finder-cn-{host}-{VERSION}.zip'
        with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for src in sorted(SOURCE.rglob('*')):
                if not src.is_file() or '__pycache__' in src.parts or src.suffix=='.pyc': continue
                rel=src.relative_to(SOURCE).as_posix()
                content=src.read_bytes()
                if host=='workbuddy' and rel=='SKILL.md':
                    text=content.decode('utf-8'); end=text.index('\n---',4)
                    extra='\ndescription_zh: "按地点、预算、设施和朝向查找中国出租住房，优先江浙沪。"\ndescription_en: "Find and compare rental housing in China with source evidence."\nversion: "'+VERSION+'"\nauthor: "rental-finder-cn contributors"'
                    content=(text[:end]+extra+text[end:]).encode('utf-8')
                archive.writestr(rel,content)
            archive.write(ROOT/'LICENSE','LICENSE')
        paths.append(path)
    checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (destination/'SHA256SUMS.json').write_text(json.dumps(checksums,indent=2)+'\n',encoding='utf-8')
    return paths

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    try:
        for path in build(args.output): print(path)
    except (ValueError,OSError) as e: parser.exit(2,str(e)+'\n')
