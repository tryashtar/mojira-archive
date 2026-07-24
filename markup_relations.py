import bisect
import os
import pathlib
import typing

import dotenv

import markup
import relations

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
      relations.load_one(self.issues, folder / 'issues.json')
      relations.load_one(self.users, folder / 'users.json')

   def save(self, folder: pathlib.Path):
      relations.save_one(self.issues, folder / 'issues.json')
      relations.save_one(self.users, folder / 'users.json')

def append(source: dict[str, MarkupRelation], mapper: dict[str, str], key: str, subkey: str, value: str):
   if key not in mapper:
      return
   key = mapper[key]
   if key not in source:
      source[key] = {
         'descriptions': [],
         'environments': [],
         'comments': {},
      }
   if value not in source[key][subkey]:
      bisect.insort(source[key][subkey], value)

def append_comment(source: dict[str, MarkupRelation], mapper: dict[str, str], key: str, issue_id: str, comment_id: str):
   if key not in mapper:
      return
   key = mapper[key]
   if key not in source:
      source[key] = {
         'descriptions': [],
         'environments': [],
         'comments': {},
      }
   if issue_id not in source[key]['comments']:
      source[key]['comments'][issue_id] = []
   if comment_id not in source[key]['comments'][issue_id]:
      bisect.insort(source[key]['comments'][issue_id], comment_id)

def create_relations(source: markup.MarkupSource, keys: relations.KeyLookups) -> MarkupRelations:
   result = MarkupRelations()
   for issue_folder in source.folder.iterdir():
      issue_id = issue_folder.stem
      desc_path = source.get_issue_description_path(issue_id)
      if desc_path.exists():
         desc = source.get_issue_description(issue_id)
         parsed = markup.parse_markup(desc)
         for entry in parsed.issues:
            append(result.issues, keys.issue_keys, entry.key, 'descriptions', issue_id)
         for entry in parsed.users:
            append(result.users, keys.user_keys, entry.username.casefold(), 'descriptions', issue_id)
      env_path = source.get_issue_environment_path(issue_id)
      if env_path.exists():
         env = source.get_issue_environment(issue_id)
         parsed = markup.parse_markup(env)
         for entry in parsed.issues:
            append(result.issues, keys.issue_keys, entry.key, 'environments', issue_id)
         for entry in parsed.users:
            append(result.users, keys.user_keys, entry.username.casefold(), 'environments', issue_id)
      comments_folder = issue_folder / 'comments'
      if comments_folder.exists():
         for comment_path in comments_folder.iterdir():
            comment_id = comment_path.stem
            comment = source.get_comment_body(issue_id, comment_id)
            parsed = markup.parse_markup(comment)
            for entry in parsed.issues:
               append_comment(result.issues, keys.issue_keys, entry.key, issue_id, comment_id)
            for entry in parsed.users:
               append_comment(result.users, keys.user_keys, entry.username.casefold(), issue_id, comment_id)
   return result

def main():
   dotenv.load_dotenv()
   source = markup.MarkupSource(pathlib.Path(os.environ['ARCHIVE_MARKUP']))
   keys = relations.KeyLookups()
   keys.load(pathlib.Path(os.environ['ARCHIVE_RELATIONS']) / 'keys')
   result = create_relations(source, keys)
   print('Writing...')
   result.save(pathlib.Path(os.environ['ARCHIVE_MARKUP_RELATIONS']))

if __name__ == '__main__':
   main()
