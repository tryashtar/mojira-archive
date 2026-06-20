import dataclasses
import pathlib
import typing
import fieldinfo
from jiratypes import CustomValue, DescriptionValue, IconValue
import mojira
import bisect
import json

class KeyLookups:
   issue_keys: dict[str, str]
   user_keys: dict[str, str]

   def __init__(self):
      self.issue_keys = {}
      self.user_keys = {}

   def load(self, folder: pathlib.Path):
      self.folder = folder
      load_one(self.issue_keys, folder / 'issues.json')
      load_one(self.user_keys, folder / 'users.json')

   def save(self, folder: pathlib.Path):
      save_one(self.issue_keys, folder / 'issues.json')
      save_one(self.user_keys, folder / 'users.json')

class UserRelations:
   groups: dict[str, list[str]]
   comments: dict[str, dict[str, list[str]]]
   edits: dict[str, dict[str, list[str]]]
   changes: dict[str, dict[str, list[str]]]
   attachments: dict[str, dict[str, list[str]]]

   def __init__(self):
      self.groups = {}
      self.comments = {}
      self.edits = {}
      self.changes = {}
      self.attachments = {}

   def load(self, folder: pathlib.Path):
      self.folder = folder
      load_one(self.groups, folder / 'groups.json')
      load_one(self.comments, folder / 'comments.json')
      load_one(self.edits, folder / 'edits.json')
      load_one(self.changes, folder / 'changes.json')
      load_one(self.attachments, folder / 'attachments.json')

   def save(self, folder: pathlib.Path):
      save_one(self.groups, folder / 'groups.json')
      save_one(self.comments, folder / 'comments.json')
      save_one(self.edits, folder / 'edits.json')
      save_one(self.changes, folder / 'changes.json')
      save_one(self.attachments, folder / 'attachments.json')

FieldValue = CustomValue | DescriptionValue | IconValue | str

FieldRelation = typing.TypedDict('FieldRelation', {
   'value': FieldValue,
   'issues': list[str]
})

class FieldRelations:
   fields: dict[str, dict[str, FieldRelation]]
   metas: dict[str, dict[str, list[str]]]

   def __init__(self):
      self.fields = {}
      self.metas = {}

   def load(self, folder: pathlib.Path):
      self.fields.clear()
      self.metas.clear()
      if (folder / 'fields').exists():
         for file in (folder / 'fields').iterdir():
            data = {}
            load_one(data, file)
            self.fields[file.stem] = data
      if (folder / 'metas').exists():
         for file in (folder / 'metas').iterdir():
            data = {}
            load_one(data, file)
            self.metas[file.stem] = data

   def save(self, folder: pathlib.Path):
      for key, value in self.fields.items():
         save_one(value, folder / 'fields' / (key + '.json'))
      for key, value in self.metas.items():
         save_one(value, folder / 'metas' / (key + '.json'))

   def display_value(self, field_id: str, value_key: str) -> mojira.ValueDisplay | None:
      value_id = '' if value_key is None else value_key
      if value_id not in self.fields[field_id]:
         return None
      full_value = self.fields[field_id][value_id]['value']
      assert full_value is not None
      if isinstance(full_value, str):
         return mojira.ValueDisplay(full_value, None, None)
      desc = full_value.get('description')
      icon = full_value.get('iconUrl')
      if 'name' in full_value:
         return mojira.ValueDisplay(full_value['name'], desc, icon)
      return mojira.ValueDisplay(full_value['value'], desc, icon)

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

def append_user_action(data: dict[str, dict[str, list[str]]], user: str | None, issue: str, value: str):
   if user is None:
      user = ''
   if user not in data:
      data[user] = {}
   issues = data[user]
   if issue not in issues:
      issues[issue] = []
   bisect.insort(issues[issue], value)

def append_field(data: dict[str, dict[str, FieldRelation]], field_key: str, value: FieldValue, issue_id: str):
   if field_key not in data:
      data[field_key] = {}
   value_id = value if isinstance(value, str) else value['id']
   if value_id not in data[field_key]:
      data[field_key][value_id] = {
         'value': value,
         'issues': []
      }
   bisect.insort(data[field_key][value_id]['issues'], issue_id)

def append_meta(data: dict[str, dict[str, list[str]]], meta_key: str, value_id: str | None, issue_id: str):
   if meta_key not in data:
      data[meta_key] = {}
   value_id = '' if value_id is None else value_id
   if value_id not in data[meta_key]:
      data[meta_key][value_id] = []
   bisect.insort(data[meta_key][value_id], issue_id)

@dataclasses.dataclass
class RelationsBundle:
   keys: KeyLookups
   user: UserRelations
   fields: FieldRelations

   def load(self, folder: pathlib.Path):
      self.keys.load(folder / 'keys')
      self.user.load(folder / 'user')
      self.fields.load(folder)

   def save(self, folder: pathlib.Path):
      self.keys.save(folder / 'keys')
      self.user.save(folder / 'user')
      self.fields.save(folder)

def create_relations(archive: mojira.Archive, fields_info: fieldinfo.FieldsInfo) -> RelationsBundle:
   key_rel = KeyLookups()
   user_rel = UserRelations()
   field_rel = FieldRelations()
   print('Tickets...')
   issue_ids = list(archive.issue_ids())
   total = len(issue_ids)
   for i, issue_id in enumerate(issue_ids):
      issue = archive.get_issue_data(issue_id)
      assert issue is not None
      if i % 100 == 0:
         print(f'{i + 1} / {total} - {issue['key']}')
      key_rel.issue_keys[issue['key']] = issue_id
      fields = issue['fields']
      for field_key, field_info in fields_info.field_map.items():
         if field_key in fields:
            raw_val = fields[field_key]
            if isinstance(field_info.field_type, fieldinfo.CustomField):
               if raw_val is not None:
                  assert isinstance(raw_val, dict)
                  full_val = field_info.field_type.get_value(raw_val)
                  append_field(field_rel.fields, field_key, full_val, issue_id)
            elif isinstance(field_info.field_type, fieldinfo.CustomListField):
               if raw_val is not None:
                  assert isinstance(raw_val, list)
                  full_val = field_info.field_type.get_value(raw_val)
                  for val in full_val:
                     append_field(field_rel.fields, field_key, val, issue_id)
            elif isinstance(field_info.field_type, fieldinfo.DiscreteField):
               if raw_val is not None:
                  assert isinstance(raw_val, dict)
                  full_val = field_info.field_type.get_value(raw_val)
                  append_field(field_rel.fields, field_key, full_val, issue_id)
            elif isinstance(field_info.field_type, fieldinfo.DiscreteListField):
               if raw_val is not None:
                  assert isinstance(raw_val, list)
                  full_val = field_info.field_type.get_value(raw_val)
                  for val in full_val:
                     append_field(field_rel.fields, field_key, val, issue_id)
            elif isinstance(field_info.field_type, fieldinfo.LabelField):
               if raw_val is not None:
                  assert isinstance(raw_val, list)
                  full_val = field_info.field_type.get_value(raw_val)
                  for val in full_val:
                     append_field(field_rel.fields, field_key, val, issue_id)
            elif isinstance(field_info.field_type, fieldinfo.MetaField):
               assert isinstance(raw_val, str | None)
               full_val = field_info.field_type.get_value(raw_val)
               append_meta(field_rel.metas, field_key, full_val, issue_id)
            elif isinstance(field_info.field_type, fieldinfo.MetaListField):
               if raw_val is not None:
                  assert isinstance(raw_val, list)
                  full_val = field_info.field_type.get_value(raw_val)
                  for val in full_val:
                     append_meta(field_rel.metas, field_key, val, issue_id)
      for comment in fields['comment']['comments']:
         append_user_action(user_rel.comments, comment.get('author'), issue_id, comment['id'])
         append_user_action(user_rel.edits, comment.get('updateAuthor'), issue_id, comment['id'])
      for change in issue['changelog']['histories']:
         append_user_action(user_rel.changes, change['author'], issue_id, change['id'])
         for item in change['items']:
            if item['field'] == 'Key' and item['fromString'] is not None:
               key_rel.issue_keys[item['fromString']] = issue_id
      for attachment in fields['attachment']:
         data = archive.get_attachment_data(attachment)
         assert data is not None
         append_user_action(user_rel.attachments, data.get('author'), issue_id, attachment)
   print('Users...')
   user_keys = list(archive.user_keys())
   total = len(user_keys)
   for i, user_key in enumerate(user_keys):
      user = archive.get_user_data(user_key)
      assert user is not None
      if i % 100 == 0:
         print(f'{i + 1} / {total} - {user['name']}')
      key_rel.user_keys[user['name'].casefold()] = user_key
      for group in user['groups']['items']:
         append(user_rel.groups, group['name'], user_key)
   return RelationsBundle(
      keys=key_rel,
      user=user_rel,
      fields=field_rel
   )

def main():
   root = pathlib.Path('/d/Archives/Mojira')
   archive = mojira.Archive(folder=root / 'data')
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   with open(root / 'extra_field_info.json', 'r', encoding='utf-8') as file:
      extra_info: fieldinfo.ExtraFieldInfo = json.load(file)
   fields_info = fieldinfo.FieldsInfo(metas.fields, extra_info)
   relations = create_relations(archive, fields_info)
   print('Writing...')
   relations.save(root / 'relations')

if __name__ == '__main__':
   main()
