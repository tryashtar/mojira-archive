import dataclasses
import pathlib
import typing
from jiratypes import Field
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

class KeyLookups:
   issue_keys: dict[str, str]
   user_keys: dict[str, str]

   def __init__(self):
      self.issue_keys = {}
      self.user_keys = {}

   def load(self, folder: pathlib.Path):
      self.folder = folder
      load_one(self.issue_keys, folder / 'issue_keys.json')
      load_one(self.user_keys, folder / 'user_keys.json')

   def save(self, folder: pathlib.Path):
      save_one(self.issue_keys, folder / 'issue_keys.json')
      save_one(self.user_keys, folder / 'user_keys.json')

class MainRelations:
   groups: dict[str, list[str]]
   users: dict[str, UserRelations]
   versions: dict[str, VersionRelations]

   def __init__(self):
      self.groups = {}
      self.users = {}
      self.versions = {}

   def load(self, folder: pathlib.Path):
      self.folder = folder
      load_one(self.groups, folder / 'groups.json')
      load_one(self.users, folder / 'users.json')
      load_one(self.versions, folder / 'versions.json')

   def save(self, folder: pathlib.Path):
      save_one(self.groups, folder / 'groups.json')
      save_one(self.users, folder / 'users.json')
      save_one(self.versions, folder / 'versions.json')

EnumValue = typing.TypedDict('EnumValue', {
   'name': str,
   'issues': list[str]
})

DescriptionEnumValue = typing.TypedDict('DescriptionEnumValue', {
   'name': str,
   'description': str | None,
   'issues': list[str]
})

IconEnumValue = typing.TypedDict('IconEnumValue', {
   'name': str,
   'icon': str,
   'issues': list[str]
})

class FieldRelations:
   enum_fields: dict[str, dict[str, EnumValue]]
   description_enum_fields: dict[str, dict[str, DescriptionEnumValue]]
   icon_enum_fields: dict[str, dict[str, IconEnumValue]]
   item_fields: dict[str, dict[str, list[str]]]
   labels: dict[str, dict[str, list[str]]]

   def __init__(self):
      self.enum_fields = {}
      self.description_enum_fields = {}
      self.icon_enum_fields = {}
      self.item_fields = {}
      self.labels = {}

   def load(self, folder: pathlib.Path):
      self.enum_fields.clear()
      self.description_enum_fields.clear()
      self.icon_enum_fields.clear()
      self.item_fields.clear()
      self.labels.clear()
      if (folder / 'enum').exists():
         for file in (folder / 'enum').iterdir():
            data = {}
            load_one(data, file)
            self.enum_fields[file.stem] = data
      if (folder / 'description').exists():
         for file in (folder / 'description').iterdir():
            data = {}
            load_one(data, file)
            self.description_enum_fields[file.stem] = data
      if (folder / 'icon').exists():
         for file in (folder / 'icon').iterdir():
            data = {}
            load_one(data, file)
            self.icon_enum_fields[file.stem] = data
      if (folder / 'item').exists():
         for file in (folder / 'item').iterdir():
            data = {}
            load_one(data, file)
            self.item_fields[file.stem] = data
      if (folder / 'label').exists():
         for file in (folder / 'label').iterdir():
            data = {}
            load_one(data, file)
            self.labels[file.stem] = data

   def save(self, folder: pathlib.Path):
      for key, value in self.enum_fields.items():
         save_one(value, folder / 'enum' / (key + '.json'))
      for key, value in self.description_enum_fields.items():
         save_one(value, folder / 'description' / (key + '.json'))
      for key, value in self.icon_enum_fields.items():
         save_one(value, folder / 'icon' / (key + '.json'))
      for key, value in self.item_fields.items():
         save_one(value, folder / 'item' / (key + '.json'))
      for key, value in self.labels.items():
         save_one(value, folder / 'label' / (key + '.json'))

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

def append_enum(data: dict[str, dict[str, EnumValue]], field_key: str, value_id: str, value_str: str, issue_id: str):
   if field_key not in data:
      data[field_key] = {}
   if value_id not in data[field_key]:
      data[field_key][value_id] = {
         'name': value_str,
         'issues': []
      }
   bisect.insort(data[field_key][value_id]['issues'], issue_id)

def append_desc_enum(data: dict[str, dict[str, DescriptionEnumValue]], field_key: str, value_id: str, value_str: str, description: str | None, issue_id: str):
   if field_key not in data:
      data[field_key] = {}
   if value_id not in data[field_key]:
      data[field_key][value_id] = {
         'name': value_str,
         'description': description,
         'issues': []
      }
   bisect.insort(data[field_key][value_id]['issues'], issue_id)

def append_icon_enum(data: dict[str, dict[str, IconEnumValue]], field_key: str, value_id: str, value_str: str, icon: str, issue_id: str):
   if field_key not in data:
      data[field_key] = {}
   if value_id not in data[field_key]:
      data[field_key][value_id] = {
         'name': value_str,
         'icon': icon,
         'issues': []
      }
   bisect.insort(data[field_key][value_id]['issues'], issue_id)

def append_field(data: dict[str, dict[str, list[str]]], field_key: str | None, value_id: str, issue_id: str):
   if field_key is None:
      field_key = ''
   if field_key not in data:
      data[field_key] = {}
   if value_id not in data[field_key]:
      data[field_key][value_id] = []
   bisect.insort(data[field_key][value_id], issue_id)

@dataclasses.dataclass
class RelationsBundle:
   keys: KeyLookups
   main: MainRelations
   fields: FieldRelations

   def load(self, folder: pathlib.Path):
      self.keys.load(folder)
      self.main.load(folder)
      self.fields.load(folder)

   def save(self, folder: pathlib.Path):
      self.keys.save(folder)
      self.main.save(folder)
      self.fields.save(folder)

FIELD_TYPE = typing.Literal['enum', 'enum_list', 'labels', 'jira_enum', 'jira_enum_list', 'jira_enum_icon', 'item', 'unknown']

def field_type(field: Field) -> FIELD_TYPE:
   if 'schema' in field:
      if field['schema']['type'] == 'option':
         return 'enum'
      if field['schema']['type'] == 'array' and 'items' in field['schema'] and field['schema']['items'] == 'option':
         return 'enum_list'
      if 'system' in field['schema'] and field['schema']['system'] == 'labels':
         return 'labels'
      if field['schema']['type'] == 'securitylevel':
         return 'jira_enum'
      if 'system' in field['schema'] and field['schema']['system'] == 'components':
         return 'jira_enum_list'
      if field['schema']['type'] == 'priority':
         return 'jira_enum_icon'
      if field['schema']['type'] in ('resolution', 'project', 'status'):
         return 'item'
   return 'unknown'

def create_relations(archive: mojira.Archive, metas: mojira.ArchiveMetas) -> RelationsBundle:
   key_rel = KeyLookups()
   main_rel = MainRelations()
   field_rel = FieldRelations()
   print('Metas...')
   ftypes: dict[str, FIELD_TYPE] = {}
   ftypes['customfield_12400'] = 'enum'
   ftypes['customfield_12900'] = 'enum'
   for key, field in metas.fields.items():
      ftype = field_type(field)
      ftypes[key] = ftype
   print('Tickets...')
   issue_ids = list(archive.issue_ids())
   total = len(issue_ids)
   for i, issue_id in enumerate(issue_ids):
      issue = archive.get_issue_data(issue_id)
      assert issue is not None
      if i % 100 == 0:
         print(f'{i+1} / {total} - {issue['key']}')
      key_rel.issue_keys[issue['key']] = issue_id
      fields = issue['fields']
      for field_key, field_val in fields.items():
         ftype = ftypes[field_key]
         match ftype:
            case 'enum':
               if field_val is not None:
                  append_enum(field_rel.enum_fields, field_key, field_val['id'], field_val['value'], issue_id)
            case 'enum_list':
               if field_val is not None:
                  for entry in field_val:
                     append_enum(field_rel.enum_fields, field_key, entry['id'], entry['value'], issue_id)
            case 'labels':
               for entry in field_val:
                  append_field(field_rel.labels, field_key, entry, issue_id)
            case 'jira_enum':
               if field_val is not None:
                  append_desc_enum(field_rel.description_enum_fields, field_key, field_val['id'], field_val['name'], field_val['description'] if 'description' in field_val else None, issue_id)
            case 'jira_enum_list':
               if field_val is not None:
                  for entry in field_val:
                     append_desc_enum(field_rel.description_enum_fields, field_key, entry['id'], entry['name'], entry['description'] if 'description' in entry else None, issue_id)
            case 'jira_enum_icon':
               if field_val is not None:
                  append_icon_enum(field_rel.icon_enum_fields, field_key, field_val['id'], field_val['name'], field_val['iconUrl'], issue_id)
            case 'item':
               append_field(field_rel.item_fields, field_key, field_val, issue_id)
            case 'unknown':
               continue
      if 'versions' in fields:
         for version in fields['versions']:
            append_version(main_rel.versions, version, 'affected', issue_id)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            append_version(main_rel.versions, version, 'fixed', issue_id)
      append_user(main_rel.users, fields['creator'], 'created', issue_id)
      append_user(main_rel.users, fields['reporter'], 'reported', issue_id)
      if 'assignee' in fields:
         append_user(main_rel.users, fields['assignee'], 'assigned', issue_id)
      for comment in fields['comment']['comments']:
         append_user_issue(main_rel.users, comment.get('author'), issue_id, 'comments', comment['id'])
         append_user_issue(main_rel.users, comment.get('updateAuthor'), issue_id, 'edits', comment['id'])
      for change in issue['changelog']['histories']:
         append_user_issue(main_rel.users, change['author'], issue_id, 'changes', change['id'])
         for item in change['items']:
            if item['field'] == 'Key' and item['fromString'] is not None:
               key_rel.issue_keys[item['fromString']] = issue_id
      for attachment in fields['attachment']:
         data = archive.get_attachment_data(attachment)
         assert data is not None
         append_user_issue(main_rel.users, data.get('author'), issue_id, 'attachments', attachment)
   print('Users...')
   user_keys = list(archive.user_keys())
   total = len(user_keys)
   for i, user_key in enumerate(user_keys):
      user = archive.get_user_data(user_key)
      assert user is not None
      if i % 100 == 0:
         print(f'{i+1} / {total} - {user['name']}')
      key_rel.user_keys[user['name'].casefold()] = user_key
      for group in user['groups']['items']:
         append(main_rel.groups, group['name'], user_key)
   return RelationsBundle(
      keys=key_rel,
      main=main_rel,
      fields=field_rel
   )

def main():
   archive = mojira.Archive(folder=pathlib.Path('/d/Archives/Mojira/data'))
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   relations = create_relations(archive, metas)
   print('Writing...')
   relations.save(pathlib.Path('/d/Archives/Mojira/relations'))

if __name__ == '__main__':
   main()
