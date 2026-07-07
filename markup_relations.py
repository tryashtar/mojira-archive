import bisect
import typing
import os
import pathlib
import dotenv
import markup
from relations import load_one, save_one

MarkupRelation = typing.TypedDict('MarkupRelation', {
   'descriptions': list[str],
   'environments': list[str],
   'comments': dict[str, list[str]]
})

class MarkupRelations:
   issues: dict[str, MarkupRelation]
   users: dict[str, MarkupRelation]

   def __init__(self):
      self.issues = {}
      self.users = {}

   def load(self, folder: pathlib.Path):
      self.issues.clear()
      self.users.clear()
      load_one(self.issues, folder / 'issues.json')
      load_one(self.users, folder / 'users.json')

   def save(self, folder: pathlib.Path):
      save_one(self.issues, folder / 'issues.json')
      save_one(self.users, folder / 'users.json')

def append(source: dict[str, MarkupRelation], key: str, subkey: str, value: str):
   if key not in source:
      source[key] = {
         'descriptions': [],
         'environments': [],
         'comments': {},
      }
   bisect.insort(source[key][subkey], value)

def append_comment(source: dict[str, MarkupRelation], key: str, issue_id: str, comment_id: str):
   if key not in source:
      source[key] = {
         'descriptions': [],
         'environments': [],
         'comments': {},
      }
   if issue_id not in source[key]['comments']:
      source[key]['comments'][issue_id] = []
   bisect.insort(source[key]['comments'][issue_id], comment_id)

def main():
   dotenv.load_dotenv()
   markup_source = markup.MarkupSource(pathlib.Path(os.environ['ARCHIVE_MARKUP']))
   relations = MarkupRelations()
   for i, issue_folder in enumerate(markup_source.folder.iterdir()):
      issue_id = issue_folder.stem
      if i % 10000 == 0:
         print(i)
      desc_path = markup_source.get_issue_description_path(issue_id)
      if desc_path.exists():
         desc = markup_source.get_issue_description(issue_id)
         parsed = markup.parse_markup(desc)
         for entry in parsed.issues:
            append(relations.issues, entry.key, 'descriptions', issue_id)
         for entry in parsed.users:
            append(relations.users, entry.username, 'descriptions', issue_id)
      env_path = markup_source.get_issue_environment_path(issue_id)
      if env_path.exists():
         env = markup_source.get_issue_environment(issue_id)
         parsed = markup.parse_markup(env)
         for entry in parsed.issues:
            append(relations.issues, entry.key, 'environments', issue_id)
         for entry in parsed.users:
            append(relations.users, entry.username, 'environments', issue_id)
      comments_folder = issue_folder / 'comments'
      if comments_folder.exists():
         for comment_path in comments_folder.iterdir():
            comment_id = comment_path.stem
            comment = markup_source.get_comment_body(issue_id, comment_id)
            parsed = markup.parse_markup(comment)
            for entry in parsed.issues:
               append_comment(relations.issues, entry.key, issue_id, comment_id)
            for entry in parsed.users:
               append_comment(relations.users, entry.username, issue_id, comment_id)
   relations.save(pathlib.Path(os.environ['ARCHIVE_MARKUP_RELATIONS']))

if __name__ == '__main__':
   main()
