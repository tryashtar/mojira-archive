import pathlib
import mojira
import subprocess
import json
import relations

def main():
   print('Loading...')
   archive = mojira.Archive(folder=pathlib.Path('/d/Archives/Mojira/data'))
   rels = relations.Relations()
   rels.load(pathlib.Path('/d/Archives/Mojira/relations'))
   markup_out = pathlib.Path('/d/Archives/Mojira/markup')
   process = get_process(archive, rels, '.')
   print('Converting...')
   for issue in archive.issues():
      if issue['fields']['description'] is not None:
         out_path = markup_out / issue['id'] / 'description.html'
         if not out_path.exists():
            print(f'{issue['id']} / {issue['key']} desc')
            markup = convert(process, issue['fields']['description'], int(issue['id']))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as file:
               file.write(markup)
      for revision in issue['changelog']['histories']:
         for entry in revision['items']:
            if entry['field'] == 'description' and entry['fromString'] is not None:
               out_path = markup_out / issue['id'] / 'revisions' / (revision['id'] + '.html')
               if not out_path.exists():
                  print(f'{issue['id']} / {issue['key']} rev {revision['id']}')
                  markup = convert(process, entry['fromString'], int(issue['id']))
                  out_path.parent.mkdir(parents=True, exist_ok=True)
                  with open(out_path, 'w', encoding='utf-8') as file:
                     file.write(markup)

def get_process(archive: mojira.Archive, rels: relations.Relations, root: str):
   print('Configuring...')
   input_args = {
      'issues': str(archive.issues_folder),
      'users': str(archive.users_folder),
      'attachments': str(archive.attachments_folder),
      'root': root
   }
   print('Compiling...')
   subprocess.run(['mvn', 'package'], cwd='renderer', check=True)
   print('Starting...')
   process = subprocess.Popen(
      ['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-shaded.jar', json.dumps(input_args)],
      encoding='utf-8',
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE
   )
   assert process.stdin is not None
   issue_map = {k: int(v) for k, v in rels.issue_keys.items()}
   user_map = {k.lower(): v for k, v in rels.user_keys.items()}
   configure_data = {
      'type': 'configure',
      'issue_map': issue_map,
      'user_map': user_map
   }
   process.stdin.write(json.dumps(configure_data) + '\n')
   process.stdin.flush()
   return process

def convert(process: subprocess.Popen, markup: str, issue_id: int | None) -> str:
   assert process.stdin is not None
   command = {
      'type': 'render',
      'markup': markup,
      'issue': issue_id
   }
   process.stdin.write((json.dumps(command) + '\n'))
   process.stdin.flush()
   assert process.stdout is not None
   output_text = process.stdout.readline()
   output = json.loads(output_text)
   return output['rendered']

if __name__ == '__main__':
   main()
