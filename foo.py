import importlib.util


if __name__ == '__main__':
    print('Hello world')
    spec = importlib.util.spec_from_file_location('Ark', '/Users/hgiesel/.vim/plugged/vim-ankify/tools/arkutil.py')
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    foo.ArkUri('grou:gr-2#@')
