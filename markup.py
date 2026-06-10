import pathlib
import bs4
from jiratypes import Issue
import mojira
import subprocess
import json
import relations

class MarkupSource:
   def __init__(self, folder: pathlib.Path):
      self.folder = folder

   def get_issue_description_path(self, issue_id: str, revision_id: str | None=None) -> pathlib.Path:
      if revision_id is None:
         return self.folder / issue_id / 'description.html'
      return self.folder / issue_id / 'revisions' / revision_id / 'description.html'

   def get_issue_environment_path(self, issue_id: str, revision_id: str | None=None) -> pathlib.Path:
      if revision_id is None:
         return self.folder / issue_id / 'environment.html'
      return self.folder / issue_id / 'revisions' / revision_id / 'environment.html'

   def get_comment_body_path(self, issue_id: str, comment_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'comments' / (comment_id + '.html')

   def get_secret_comment_body_path(self, issue_id: str, comment_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'secret_comments' / (comment_id + '.html')

   def get_issue_description(self, issue_id: str, revision_id: str | None=None) -> bs4.BeautifulSoup:
      with open(self.get_issue_description_path(issue_id, revision_id), 'r', encoding='utf-8') as file:
         return bs4.BeautifulSoup(file, 'html.parser')

   def get_issue_environment(self, issue_id: str, revision_id: str | None=None) -> bs4.BeautifulSoup:
      with open(self.get_issue_environment_path(issue_id, revision_id), 'r', encoding='utf-8') as file:
         return bs4.BeautifulSoup(file, 'html.parser')

   def get_comment_body(self, issue_id: str, comment_id: str) -> bs4.BeautifulSoup:
      with open(self.get_comment_body_path(issue_id, comment_id), 'r', encoding='utf-8') as file:
         return bs4.BeautifulSoup(file, 'html.parser')

   def get_secret_comment_body(self, issue_id: str, comment_id: str) -> bs4.BeautifulSoup:
      with open(self.get_secret_comment_body_path(issue_id, comment_id), 'r', encoding='utf-8') as file:
         return bs4.BeautifulSoup(file, 'html.parser')

   def render_issue(self, issue: Issue, renderer: subprocess.Popen):
      issue_id = int(issue['id'])
      if issue['fields']['description'] is not None:
         path = self.get_issue_description_path(issue['id'])
         render_to_file(renderer, issue_id, issue['fields']['description'], path)
      if 'environment' in issue['fields'] and issue['fields']['environment'] is not None:
         path = self.get_issue_environment_path(issue['id'])
         render_to_file(renderer, issue_id, issue['fields']['environment'], path)
      for revision in issue['changelog']['histories']:
         for entry in revision['items']:
            if entry['fromString'] is not None:
               if entry['field'] == 'description':
                  path = self.get_issue_description_path(issue['id'], revision['id'])
                  render_to_file(renderer, issue_id, entry['fromString'], path)
               elif entry['field'] == 'environment':
                  path = self.get_issue_environment_path(issue['id'], revision['id'])
                  render_to_file(renderer, issue_id, entry['fromString'], path)
      for comment in issue['fields']['comment']['comments']:
         path = self.get_comment_body_path(issue['id'], comment['id'])
         render_to_file(renderer, issue_id, comment['body'], path)

def main():
   print('Loading...')
   archive = mojira.Archive(folder=pathlib.Path('/d/Archives/Mojira/data'))
   rels = relations.Relations()
   rels.load(pathlib.Path('/d/Archives/Mojira/relations'))
   secret_comments = mojira.SecretComments(pathlib.Path('/d/Archives/Mojira/secret_comments.json'))
   markup_out = pathlib.Path('/d/Archives/Mojira/markup')
   process = get_process(archive, rels, '.')
   source = MarkupSource(markup_out)
   print('Converting...')
   for i, issue in enumerate(archive.issues()):
      if i % 10000 == 0:
         print(i)
      source.render_issue(issue, process)
   print('Secrets...')
   for issue_id, comments in secret_comments.comments.items():
      print(issue_id)
      for comment in comments:
         path = source.get_secret_comment_body_path(issue_id, comment['id'])
         render_to_file(process, int(issue_id), comment['body'], path)

def get_process(archive: mojira.Archive, rels: relations.Relations, root: str) -> subprocess.Popen:
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
   configure_data = {
      'type': 'configure',
      'issue_map': issue_map,
      'user_map': rels.user_keys
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

def render_to_file(renderer: subprocess.Popen, issue_id: int, markup: str, path: pathlib.Path):
   if not path.exists():
      html = convert(renderer, markup, issue_id)
      path.parent.mkdir(parents=True, exist_ok=True)
      with open(path, 'w', encoding='utf-8') as file:
         file.write(html)

if __name__ == '__main__':
   main()
