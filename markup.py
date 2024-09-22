import mojira
import tryashtools as tat
import html
import subprocess
import json
import os

def main():
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests(extended=True)

def convert(markup: str, process: subprocess.Popen):
   process.stdin.write((json.dumps({'markup':markup}) + '\n'))
   process.stdin.flush()
   output = json.loads(process.stdout.readline())
   return output['rendered']

def get_tests(extended: bool):
   tests = tat.read_json('tests.json')
   for test in tests:
      yield test
   index = len(tests)
   if extended:
      for file in tat.get_files('/d/Archives/Mojira/dump/markup'):
         name = tat.base_name(file)
         markup_data = tat.read_json(file)
         matching_file = os.path.join('/d/Archives/Mojira/dump/tickets', name + '.json')
         ticket_data = tat.read_json(matching_file)
         for field in ['description', 'customfield_12700', 'environment']:
            if (out_val := markup_data.get(field)) is not None and (in_val := ticket_data['fields'].get(field)) is not None:
               yield {'in':in_val,'out':out_val,'index':index}
               index += 1

def check_tests(extended=False):
   print('Compiling...')
   subprocess.run(['mvn', 'package', 'assembly:single'], cwd='renderer', check=True, stdout=subprocess.DEVNULL)
   process = subprocess.Popen(['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-jar-with-dependencies.jar'], encoding='utf-8', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
   print('Loading tests...')
   failed = 0
   passed = 0
   for test in get_tests(extended):
      in_text = test['in']
      out_text = convert(in_text, process)
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
      tat.write_text(f'<!DOCTYPE html><html><head><link rel="stylesheet" href="wiki.css"></head><div style="background-color:#DDD;display:inline-block">\n\n<pre>{html.escape(test['in'])}</pre>\n\n</div><br/><br/><div class="wiki-edit" style="background-color:#CCC;display:inline-block"><div class="wiki-edit-content">\n\n{test['out']}\n\n</div></div></html>', f'markup-tests/{i}.html')
      test['index'] = i
      i += 1
   if client is not None:
      tat.write_json(tests, 'tests.json')

if __name__ == '__main__':
   main()
