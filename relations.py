import pathlib
import typing
import mojira
import bisect
import dataclasses
import json

UserRelations = typing.TypedDict('UserRelations', {
   'created': list[str],
   'reported': list[str],
   'assigned': list[str],
   'comments': list[str],
   'edits': list[str],
   'changes': list[str]
})

VersionRelations = typing.TypedDict('VersionRelations', {
   'affected': list[str],
   'fixed': list[str]
})

@dataclasses.dataclass
class Relations:
   issue_keys: dict[str, str]
   user_keys: dict[str, str]
   groups: dict[str, list[str]]
   projects: dict[str, list[str]]
   resolutions: dict[str, list[str]]
   users: dict[str | None, UserRelations]
   versions: dict[str, VersionRelations]
   labels: dict[str, list[str]]
   categories: dict[str, list[str]]
   confirmation: dict[str, list[str]]
   priority: dict[str, list[str]]
   area: dict[str, list[str]]

   def __init__(self):
      self.issue_keys = {}
      self.user_keys = {}
      self.groups = {}
      self.projects = {}
      self.resolutions = {}
      self.users = {}
      self.versions = {}
      self.labels = {}
      self.categories = {}
      self.confirmation = {}
      self.priority = {}
      self.area = {}

   def load(self, folder: pathlib.Path):
      self.folder = folder
      load_one(self.issue_keys, folder / 'issue_keys.json')
      load_one(self.user_keys, folder / 'user_keys.json')
      load_one(self.groups, folder / 'groups.json')
      load_one(self.projects, folder / 'projects.json')
      load_one(self.resolutions, folder / 'resolutions.json')
      load_one(self.users, folder / 'users.json')
      load_one(self.versions, folder / 'versions.json')
      load_one(self.labels, folder / 'labels.json')
      load_one(self.categories, folder / 'categories.json')
      load_one(self.confirmation, folder / 'confirmation.json')
      load_one(self.priority, folder / 'priority.json')
      load_one(self.area, folder / 'area.json')

   def save(self, folder: pathlib.Path):
      save_one(self.issue_keys, folder / 'issue_keys.json')
      save_one(self.user_keys, folder / 'user_keys.json')
      save_one(self.groups, folder / 'groups.json')
      save_one(self.projects, folder / 'projects.json')
      save_one(self.resolutions, folder / 'resolutions.json')
      save_one(self.users, folder / 'users.json')
      save_one(self.versions, folder / 'versions.json')
      save_one(self.labels, folder / 'labels.json')
      save_one(self.categories, folder / 'categories.json')
      save_one(self.confirmation, folder / 'confirmation.json')
      save_one(self.priority, folder / 'priority.json')
      save_one(self.area, folder / 'area.json')

def load_one(data: dict, path: pathlib.Path):
   data.clear()
   for key, value in mojira.load_or(path, {}).items():
      data[key] = value

def save_one(data: dict, path: pathlib.Path):
   path.parent.mkdir(parents=True, exist_ok=True)
   with open(path, 'w', encoding='utf-8') as file:
      json.dump(data, file)

def append(start: dict, path: list, value):
   block = start
   for i, entry in enumerate(path):
      if entry is None:
         entry = ''
      if entry not in block:
         if i == len(path) - 1:
            block[entry] = []
         else:
            block[entry] = {}
      block = block[entry]
      if i == len(path) - 1:
         bisect.insort(block, value)

def create_relations(archive: mojira.Archive) -> Relations:
   relations = Relations()
   print('Tickets...')
   issue_ids = list(archive.issue_ids())
   total = len(issue_ids)
   for i, issue_id in enumerate(issue_ids):
      issue = archive.get_issue_data(issue_id)
      assert issue is not None
      if i % 100 == 0:
         print(f'{i+1} / {total} - {issue['key']}')
      relations.issue_keys[issue['key']] = issue_id
      fields = issue['fields']
      append(relations.resolutions, [fields['resolution']], issue_id)
      append(relations.projects, [fields['project']], issue_id)
      if 'versions' in fields:
         for version in fields['versions']:
            append(relations.versions, [version, 'affected'], issue_id)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            append(relations.versions, [version, 'fixed'], issue_id)
      for label in fields['labels']:
         append(relations.labels, [label], issue_id)
      if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
         append(relations.area, [fields['customfield_12800']['id']], issue_id)
      if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
         append(relations.priority, [fields['customfield_12200']['id']], issue_id)
      if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
         for entry in fields['customfield_11901']:
            append(relations.categories, [entry['id']], issue_id)
      if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
         append(relations.confirmation, [fields['customfield_10500']['id']], issue_id)
      append(relations.users, [fields['creator'], 'created'], issue_id)
      append(relations.users, [fields['reporter'], 'reported'], issue_id)
      if 'assignee' in fields:
         append(relations.users, [fields.get('assignee'), 'assigned'], issue_id)
      for comment in fields['comment']['comments']:
         append(relations.users, [comment.get('author'), 'comments', issue_id], comment['id'])
         append(relations.users, [comment.get('updateAuthor'), 'edits', issue_id], comment['id'])
      for change in issue['changelog']['histories']:
         append(relations.users, [change['author'], 'changes', issue_id], change['id'])
         for item in change['items']:
            if item['field'] == 'Key' and item['fromString'] is not None:
               relations.issue_keys[item['fromString']] = issue_id
      for attachment in fields['attachment']:
         data = archive.get_attachment_data(attachment)
         assert data is not None
         append(relations.users, [data.get('author'), 'attachments', issue_id], attachment)
   print('Users...')
   user_keys = list(archive.user_keys())
   total = len(user_keys)
   for i, user_key in enumerate(user_keys):
      user = archive.get_user_data(user_key)
      assert user is not None
      if i % 100 == 0:
         print(f'{i+1} / {total} - {user['name']}')
      relations.user_keys[user['name']] = user_key
      for group in user['groups']['items']:
         append(relations.groups, [group['name']], user_key)
   return relations

def main():
   archive = mojira.Archive(folder=pathlib.Path('/d/Archives/Mojira/data'))
   relations = create_relations(archive)
   print('Writing...')
   relations.save(pathlib.Path('/d/Archives/Mojira/cache'))

if __name__ == '__main__':
   main()
