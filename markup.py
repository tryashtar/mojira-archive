import pathlib
import typing
import jira
import mojira
import tryashtools as tat
import html
import subprocess
import json

def main():
   dump = mojira.get_dump()
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests(dump, extended=True, show_passed=False)

def get_process(dump: mojira.Dump, ids: dict[str, typing.Any]):
   print('Configuring...')
   input_args = {'issues':str(dump.tickets_folder),'users':str(dump.users_folder),'attachments':str(dump.attachments_folder)}
   print('Compiling...')
   subprocess.run(['mvn', 'package'], cwd='renderer', check=True, stdout=subprocess.DEVNULL)
   print('Starting...')
   process = subprocess.Popen(['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-shaded.jar', json.dumps(input_args)], encoding='utf-8', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
   issue_map = {k: int(v) for k, v in ids['issues'].items()}
   user_map = {k.lower(): v for k, v in ids['users'].items()}
   process.stdin.write(json.dumps({'type':'configure','issue_map':issue_map,'user_map':user_map}) + '\n')
   process.stdin.flush()
   return process

def convert(process: subprocess.Popen, markup: str, key: int | None):
   process.stdin.write((json.dumps({'type':'render','markup':markup,'issue':key}) + '\n'))
   process.stdin.flush()
   output_text = process.stdout.readline()
   output = json.loads(output_text)
   return output['rendered']

def get_tests(test_file: pathlib.Path | None, folder: pathlib.Path | None):
   if test_file is not None:
      tests = tat.read_json(test_file)
      for test in tests:
         test['source'] = f'index {test['index']}'
         yield {'markup':test['in'], 'rendered':test['out'], 'key':test.get('key'), 'source':f'test index {test['index']}'}
   if folder is not None:
      for file in tat.get_files(folder):
         name = tat.base_name(file)
         key = int(name)
         markup_data = tat.read_json(file)
         for i,entry in enumerate(markup_data):
            yield {'markup':entry['markup'], 'rendered':entry['rendered'], 'key':key, 'source':f'markup {name} index {i}','file':file}

def check_tests(dump: mojira.Dump, extended=False, show_passed=True):
   failed = 0
   passed = 0
   ids = tat.read_json(dump.root_folder / 'ids.json')
   process = get_process(dump, ids)
   file_tests = pathlib.Path('tests.json')
   folder_tests = pathlib.Path('/d/Archives/Mojira/markup-tests/tickets') if extended else None
   tests = get_tests(file_tests, folder_tests)
   client = None
   for test in tests:
      in_text = test['markup']
      out_text = convert(process, in_text, test.get('key'))
      expected_text = test['rendered']
      if out_text != expected_text and 'file' in test:
         if client is None:
            client = mojira.get_client()
         try:
            retry_text = render_from_jira(client, in_text, test.get('key'))
         except jira.JIRAError as e:
            print(f'Test {test['source']} update error {e.text}')
            continue
         if retry_text != expected_text:
            print(f'Test {test['source']} updated')
         expected_text = retry_text
      if out_text != expected_text:
         failed += 1
         print(f'\033[93m❎ Test {test['source']} failed!\033[0m')
         print(f'\033[93m\tInput:     {repr(in_text)}\033[0m')
         print(f'\033[93m\tExpected:  {repr(expected_text)}\033[0m')
         print(f'\033[93m\tGot:       {repr(out_text)}\033[0m')
      else:
         passed += 1
         if show_passed:
            print(f'\033[92m✅ Test {test['source']} passed!\033[0m')
            print(f'\033[92m\tInput:     {repr(in_text)}\033[0m')
            print(f'\033[92m\tOutput:    {repr(out_text)}\033[0m')
   print()
   if passed > 0:
      print(f'\033[92m{passed} tests passed\033[0m')
   if failed > 0:
      print(f'\033[93m{failed} tests failed\033[0m')

def render_from_jira(client: jira.JIRA, markup: str, key: str | None):
   post_data = {"rendererType":"atlassian-wiki-renderer","unrenderedMarkup":markup}
   if key is not None:
      if '-' not in str(key):
         key = client.issue(key).key
      post_data['issueKey'] = key
   result = client._session.post('https://bugs.mojang.com/rest/api/1.0/render', json=post_data)
   return result.content.decode('utf-8')

def update_tests():
   client = None
   tests = tat.read_json('tests.json')
   i = 0
   for test in tests:
      if 'out' not in test:
         print(test['in'])
         if client is None:
            client = mojira.get_client()
         test['out'] = render_from_jira(client, test['in'], test.get('key'))
      tat.write_text(f'<!DOCTYPE html><html><head><link rel="stylesheet" href="wiki.css"></head><div style="background-color:#DDD;display:inline-block">\n\n<pre>{html.escape(test['in'])}</pre>\n\n</div><br/><br/><div class="wiki-edit" style="background-color:#CCC;display:inline-block"><div class="wiki-edit-content">\n\n{test['out']}\n\n</div></div></html>', f'markup-tests/{i}.html')
      test['index'] = i
      i += 1
   if client is not None:
      tat.write_json(tests, 'tests.json')

if __name__ == '__main__':
   main()
