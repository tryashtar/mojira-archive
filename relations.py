import pathlib
import typing
import mojira
import bisect
import json

IssueRelations = typing.TypedDict('IssueRelations', {
   'comments': list[str],
   'edits': list[str],
   'changes': list[str],
   'attachments': list[str],
})

UserRelations = typing.TypedDict('UserRelations', {
   'created': list[str],
   'reported': list[str],
   'assigned': list[str],
   'issues': dict[str, IssueRelations]
})

VersionRelations = typing.TypedDict('VersionRelations', {
   'affected': list[str],
   'fixed': list[str]
})

class Relations:
   issue_keys: dict[str, str]
   user_keys: dict[str, str]
   groups: dict[str, list[str]]
   projects: dict[str, list[str]]
   resolutions: dict[str, list[str]]
   users: dict[str, UserRelations]
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
      json.dump(data, file,separators=(',', ':'))

def append(data: dict[str, list[str]], key: str | None, value: str):
   if key is None:
      key = ''
   if key not in data:
      data[key] = []
   bisect.insort(data[key], value)

def append_user(data: dict[str, UserRelations], user: str | None, subkey: str, value: str):
   if user is None:
      user = ''
   if user not in data:
      data[user] = {
         'created': [],
         'reported': [],
         'assigned': [],
         'issues': {}
      }
   bisect.insort(data[user][subkey], value)

def append_user_issue(data: dict[str, UserRelations], user: str | None, issue: str, subkey: str, value: str):
   if user is None:
      user = ''
   if user not in data:
      data[user] = {
         'created': [],
         'reported': [],
         'assigned': [],
         'issues': {}
      }
   issues = data[user]['issues']
   if issue not in issues:
      issues[issue] = {
         'comments': [],
         'edits': [],
         'changes': [],
         'attachments': []
      }
   bisect.insort(issues[issue][subkey], value)

def append_version(data: dict[str, VersionRelations], key: str | None, subkey: str, value: str):
   if key is None:
      key = ''
   if key not in data:
      data[key] = {
         'affected': [],
         'fixed': [],
      }
   bisect.insort(data[key][subkey], value)

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
      append(relations.resolutions, fields['resolution'], issue_id)
      append(relations.projects, fields['project'], issue_id)
      if 'versions' in fields:
         for version in fields['versions']:
            append_version(relations.versions, version, 'affected', issue_id)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            append_version(relations.versions, version, 'fixed', issue_id)
      for label in fields['labels']:
         append(relations.labels, label, issue_id)
      if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
         append(relations.area, fields['customfield_12800']['id'], issue_id)
      if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
         append(relations.priority, fields['customfield_12200']['id'], issue_id)
      if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
         for entry in fields['customfield_11901']:
            append(relations.categories, entry['id'], issue_id)
      if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
         append(relations.confirmation, fields['customfield_10500']['id'], issue_id)
      append_user(relations.users, fields['creator'], 'created', issue_id)
      append_user(relations.users, fields['reporter'], 'reported', issue_id)
      if 'assignee' in fields:
         append_user(relations.users, fields['assignee'], 'assigned', issue_id)
      for comment in fields['comment']['comments']:
         append_user_issue(relations.users, comment.get('author'), issue_id, 'comments', comment['id'])
         append_user_issue(relations.users, comment.get('updateAuthor'), issue_id, 'edits', comment['id'])
      for change in issue['changelog']['histories']:
         append_user_issue(relations.users, change['author'], issue_id, 'changes', change['id'])
         for item in change['items']:
            if item['field'] == 'Key' and item['fromString'] is not None:
               relations.issue_keys[item['fromString']] = issue_id
      for attachment in fields['attachment']:
         data = archive.get_attachment_data(attachment)
         assert data is not None
         append_user_issue(relations.users, data.get('author'), issue_id, 'attachments', attachment)
   print('Users...')
   user_keys = list(archive.user_keys())
   total = len(user_keys)
   for i, user_key in enumerate(user_keys):
      user = archive.get_user_data(user_key)
      assert user is not None
      if i % 100 == 0:
         print(f'{i+1} / {total} - {user['name']}')
      relations.user_keys[user['name'].casefold()] = user_key
      for group in user['groups']['items']:
         append(relations.groups, group['name'], user_key)
   return relations

def main():
   archive = mojira.Archive(folder=pathlib.Path('/d/Archives/Mojira/data'))
   relations = create_relations(archive)
   print('Writing...')
   relations.save(pathlib.Path('/d/Archives/Mojira/relations'))

if __name__ == '__main__':
   main()
