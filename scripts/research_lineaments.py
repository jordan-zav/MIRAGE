"""Pin third-party research sources and verify Git blob identities on download.

Not imported by the package. Explicit invocation is the model download request.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


TEED_COMMIT = '40fa4b1391dc6424f88989d0ca75d5b592c8681d'


def read(url):
    with urlopen(Request(url, headers={'User-Agent': 'MIRAGE-local-research'}), timeout=90) as response:
        return response.read()


def main(destination, sources):
    destination, sources = Path(destination), Path(sources)
    destination.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    records = []
    repos = [('swaxi/SGTool', '805ac7d39c99690143367f62affc0e3c5a7a97cd',
              ['LICENSE', 'calcs/worms/BSDWorms_COPYRIGHT.txt']),
             ('hellozhuo/pidinet', 'master', ['LICENSE']),
             ('xavysp/DexiNed', '08ed67ad0579f3969536a9719cdc1b829fb74fc1', ['LICENSE']),
             ('xavysp/TEED', TEED_COMMIT,
              ['LICENSE', 'README.md', 'ted.py', 'utils/AF/Fsmish.py',
               'utils/AF/Xsmish.py', 'utils/img_processing.py',
               'checkpoints/BIPED/7/7_model.pth'])]
    for repo, commit, paths in repos:
        tree = json.loads(read(f'https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1'))
        commit = tree['sha']
        objects = {entry['path']: entry for entry in tree['tree']}
        for name in paths:
            url = f'https://raw.githubusercontent.com/{repo}/{commit}/{name}'
            data = read(url)
            blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if blob != objects[name]['sha']:
                raise ValueError('Git blob mismatch: '+url)
            # Models stay in the development session; code is kept on O:.
            target = ((destination/'models'/'teed-pretrained.pth') if name.endswith('.pth')
                      else (sources/repo.split('/')[-1]/name) if name.endswith('.py')
                      else destination/'licenses'/(repo.replace('/', '-')+'-'+Path(name).name.replace('.md', '.txt')))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(data)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == hashlib.sha256(data).hexdigest()
            records.append({'repository': repo, 'commit': commit, 'file': name, 'url': url,
                            'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': blob,
                            'local': str(target), 'weight': name.endswith('.pth')})
    (destination/'research_sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(json.dumps({'verified_sources': len(records)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    parser.add_argument('sources')
    args = parser.parse_args()
    main(args.destination, args.sources)
