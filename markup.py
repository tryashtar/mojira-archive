import mojira
import tryashtools as tat
import io
import re
import html
import subprocess

def main():
   print('Compiling...')
   subprocess.run(['mvn', 'package', 'assembly:single'], cwd='renderer', check=True, stdout=subprocess.DEVNULL)
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests()

def render(markup: str):
   proc = subprocess.run(['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-jar-with-dependencies.jar', markup], check=True, capture_output=True)
   return proc.stdout.decode('utf-8')

def check_tests():
   tests = tat.read_json('tests.json')
   failed = 0
   passed = 0
   for test in tests:
      in_text = test['in']
      out_text = render(in_text)
      expected_text = test['out']
      if out_text != expected_text:
         failed += 1
         print(f'\033[91m❎ Test {test['index']} failed!')
         print(f'\033[91m\tInput:     {repr(in_text)}')
         print(f'\033[91m\tExpected:  {repr(expected_text)}')
         print(f'\033[91m\tGot:       {repr(out_text)}')
      else:
         passed += 1
         print(f'\033[92m✅ Test {test['index']} passed!')
         print(f'\033[92m\tInput:     {repr(in_text)}')
         print(f'\033[92m\tOutput:    {repr(out_text)}')
   print()
   if passed > 0:
      print(f'\033[92m{passed} tests passed')
   if failed > 0:
      print(f'\033[91m{failed} tests failed')

def update_tests():
   client = None
   tests = tat.read_json('tests.json')
   i = 0
   for test in tests:
      if 'out' not in test:
         print(test['in'])
         if client is None:
            client = mojira.get_client()
         result = client._session.post('https://bugs.mojang.com/rest/api/1.0/render', json={"rendererType":"atlassian-wiki-renderer","unrenderedMarkup":test['in'],"issueKey":"MC-1"})
         test['out'] = result.content.decode('utf-8')
      tat.write_text(f'<!DOCTYPE html><html><div style="background-color:#DDD;display:inline-block">\n\n<pre>{html.escape(test['in'])}</pre>\n\n</div><br/><br/><div style="background-color:#CCC;display:inline-block">\n\n{test['out']}\n\n</div></html>', f'markup-tests/{i}.html')
      test['index'] = i
      i += 1
   if client is not None:
      tat.write_json(tests, 'tests.json')

if __name__ == '__main__':
   main()
