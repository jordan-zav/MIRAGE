"""One-time source migration; retained for review of byte-preserving changes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    src = ROOT / 'src'
    package = src / 'mirage'
    package.mkdir(exist_ok=True)
    (package / 'ai').mkdir(exist_ok=True)
    for source in [*src.glob('*.py'), *src.joinpath('ai').glob('*.py')]:
        relative = source.relative_to(src)
        target = package / relative
        if target.exists():
            raise FileExistsError(target)
        text = source.read_text(encoding='utf-8')
        if source.name in ('cli.py', 'gui.py'):
            for name in ('adaptive', 'ai.parameter_advisor', 'config', 'pipeline'):
                text = text.replace('from ' + name + ' import', 'from .' + name + ' import')
        if source.name == 'parameter_advisor.py':
            text = text.replace('if __package__ and "." in __package__:', 'if __package__ and "." in __package__:')
        target.write_text(text, encoding='utf-8')
        module = str(relative.with_suffix('')).replace('\\', '.')
        if module == 'ai.__init__':
            module = 'ai'
        wrapper = ('"""Compatibility import for pre-1.3 source callers."""\n'
                   'import importlib\nimport sys\n'
                   f'_module = importlib.import_module("mirage.{module}")\n'
                   'sys.modules[__name__] = _module\n'
                   'globals().update(vars(_module))\n')
        if source.name == 'cli.py':
            wrapper += 'if __name__ == "__main__":\n    raise SystemExit(_module.main())\n'
        if source.name == 'gui.py':
            # GUI entry point is kept in a wrapper below after inspection.
            wrapper = ('"""Compatibility launcher for the standalone GUI."""\n'
                       'if __name__ == "__main__":\n'
                       '    import runpy\n    runpy.run_module("mirage.gui", run_name="__main__")\n'
                       'else:\n    from mirage.gui import LineamentGUI\n')
        source.write_text(wrapper, encoding='utf-8')


if __name__ == '__main__':
    main()
