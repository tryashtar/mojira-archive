import mojira
import tryashtools as tat
import html
import subprocess
import json
import pathlib

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests(dump, extended=True)

def get_process(dump: mojira.Dump):
   print('Configuring...')
   relations = tat.read_json(dump.root_folder / 'relations.json')
   input_args = {'issues':str(dump.tickets_folder),'users':str(dump.users_folder),'attachments':str(dump.attachments_folder)}
   print('Compiling...')
   subprocess.run(['mvn', 'package', 'assembly:single'], cwd='renderer', check=True, stdout=subprocess.DEVNULL)
   print('Starting...')
   process = subprocess.Popen(['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-jar-with-dependencies.jar', json.dumps(input_args)], encoding='utf-8', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
   process.stdin.write(json.dumps({'type':'configure','issue_map':{k: int(v) for k, v in relations['issues'].items()}}) + '\n')
   process.stdin.flush()
   return process

def convert(process: subprocess.Popen, markup: str, key: int | None):
   process.stdin.write((json.dumps({'type':'render','markup':markup,'issue':key}) + '\n'))
   process.stdin.flush()
   output = json.loads(process.stdout.readline())
   return output['rendered']

def get_tests(dump: mojira.Dump | None):
   tests = tat.read_json('tests.json')
   for test in tests:
      yield test
   index = len(tests)
   if dump is not None:
      for file in tat.get_files(dump.root_folder / 'markup'):
         name = tat.base_name(file)
         key = int(name)
         markup_data = tat.read_json(file)
         matching_file = dump.get_issue_path(name)
         ticket_data = tat.read_json(matching_file)
         for field in ['description', 'customfield_12700', 'environment']:
            if (out_val := markup_data.get(field)) is not None and (in_val := ticket_data['fields'].get(field)) is not None:
               yield {'in':in_val,'out':out_val,'index':index,'key':key}
               index += 1
         if 'comments' in markup_data:
            for i in range(len(markup_data['comments'])):
               out_val = markup_data['comments'][i]
               in_val = ticket_data['fields']['comment']['comments'][i]['body']
               yield {'in':in_val,'out':out_val,'index':index,'key':key}
               index += 1
         if 'history' in markup_data:
            for i in range(len(markup_data['history'])):
               for k,value in markup_data['history'][i].items():
                  old_out = value['from']
                  new_out = value['to']
                  for entry in ticket_data['changelog']['histories'][i]['items']:
                     if entry['field'] == k:
                        old_in = entry['fromString']
                        new_in = entry['toString']
                        if old_in is not None:
                           yield {'in':old_in,'out':old_out,'index':index,'key':key}
                           index += 1
                        if new_in is not None:
                           yield {'in':new_in,'out':new_out,'index':index,'key':key}
                           index += 1

def check_tests(dump: mojira.Dump, extended=False):
   failed = 0
   passed = 0
   process = get_process(dump)
   for test in get_tests(dump if extended else None):
      in_text = test['in']
      out_text = convert(process, in_text, test.get('key'))
      expected_text = test['out']
      if out_text != expected_text:
         failed += 1
         print(f'\033[91m❎ Test {test['index']} failed!\033[0m')
         print(f'\033[91m\tInput:     {repr(in_text)}\033[0m')
         print(f'\033[91m\tExpected:  {repr(expected_text)}\033[0m')
         print(f'\033[91m\tGot:       {repr(out_text)}\033[0m')
      else:
         passed += 1
         print(f'\033[92m✅ Test {test['index']} passed!\033[0m')
         print(f'\033[92m\tInput:     {repr(in_text)}\033[0m')
         print(f'\033[92m\tOutput:    {repr(out_text)}\033[0m')
   print()
   if passed > 0:
      print(f'\033[92m{passed} tests passed\033[0m')
   if failed > 0:
      print(f'\033[91m{failed} tests failed\033[0m')

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
