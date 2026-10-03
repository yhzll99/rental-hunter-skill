"""Copy the Codex-compatible skill to an explicitly selected skills directory."""
import argparse
import shutil
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]/'skills/rental-finder-cn'

def install(skills_dir):
    parent=Path(skills_dir).expanduser().resolve()
    if parent==SOURCE or SOURCE in parent.parents: raise ValueError('安装目标不能位于技能源码内')
    dest=parent/SOURCE.name
    if dest.exists() or dest.is_symlink(): raise FileExistsError(f'已存在，未覆盖：{dest}')
    parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(SOURCE,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return dest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skills-dir',type=Path,required=True,help='如项目中的 .agents/skills')
    a=p.parse_args()
    try: print(install(a.skills_dir))
    except (ValueError,OSError) as e: p.exit(2,str(e)+'\n')
