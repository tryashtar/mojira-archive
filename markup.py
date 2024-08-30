import mojira
import tryashtools as tat
import subprocess

def main():
   print('Updating...')
   update_tests()
   print('Building...')
   build()
   print('Checking...')
   check_tests()

def build():
   subprocess.run(['mvn', 'package', 'assembly:single'], cwd='renderer', check=True, stdout=subprocess.DEVNULL)

def convert(text):
   proc = subprocess.run(['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-jar-with-dependencies.jar', text], check=True, capture_output=True)
   return proc.stdout.decode('utf-8')

def check_tests():
   tests = tat.read_json('tests.json')
   for test in tests:
      in_text = test['in']
      out_text = convert(in_text)
      expected_text = test['out']
      if out_text != expected_text:
         print('Test failed!')
         print('Input:')
         print(in_text)
         print('Expected:')
         print(expected_text)
         print('Got:')
         print(out_text)
         print()

def update_tests():
   client = None
   tests = tat.read_json('tests.json')
   for test in tests:
      if 'out' not in test:
         print(test['in'])
         if client is None:
            client = mojira.get_client()
         result = client._session.post('https://bugs.mojang.com/rest/api/1.0/render', json={"rendererType":"atlassian-wiki-renderer","unrenderedMarkup":test['in'],"issueKey":"MC-1"})
         test['out'] = result.content.decode('utf-8')
   if client is not None:
      tat.write_json(tests, 'tests.json')

if __name__ == '__main__':
   main()
