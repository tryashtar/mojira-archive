import bisect
import dataclasses
import json
import os
import pathlib
import typing

import dotenv

import mojira
from jiratypes import CustomValue, DescriptionValue, IconValue


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

   def get_user_key(self, username: str) -> str:
      return self.user_keys[username.casefold()]

   def try_get_user_key(self, username: str) -> str | None:
      return self.user_keys.get(username.casefold())

   def get_issue_key(self, issue_id: str) -> str:
      return self.issue_keys[issue_id]

   def try_get_issue_key(self, issue_id: str) -> str | None:
      return self.issue_keys.get(issue_id)

GroupRelation = typing.TypedDict('GroupRelation', {
   'users': list[str],
   'comments': dict[str, list[str]]
})

class UserRelations:
   groups: dict[str, GroupRelation]
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

   def load(self, fields: pathlib.Path, metas: pathlib.Path):
      self.fields.clear()
      self.metas.clear()
      if fields.exists():
         for file in fields.iterdir():
            data = {}
            load_one(data, file)
            self.fields[file.stem] = data
      if metas.exists():
         for file in metas.iterdir():
            data = {}
            load_one(data, file)
            self.metas[file.stem] = data

   def save(self, fields: pathlib.Path, metas: pathlib.Path):
      for key, value in self.fields.items():
         save_one(value, fields / (key + '.json'))
      for key, value in self.metas.items():
         save_one(value, metas / (key + '.json'))

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

def append_group_user(data: dict[str, GroupRelation], group: str, user: str):
   if group not in data:
      data[group] = {
         'users': [],
         'comments': {}
      }
   bisect.insort(data[group]['users'], user)

def append_group_comment(data: dict[str, GroupRelation], group: str, issue: str, comment: str):
   if group not in data:
      data[group] = {
         'users': [],
         'comments': {}
      }
   if issue not in data[group]['comments']:
      data[group]['comments'][issue] = []
   bisect.insort(data[group]['comments'][issue], comment)

def append_user_action(data: dict[str, dict[str, list[str]]], user: str | None, issue: str, value: str):
   if user is None:
      user = ''
   if user not in data:
      data[user] = {}
   issues = data[user]
   if issue not in issues:
      issues[issue] = []
   bisect.insort(issues[issue], value, key=int)

def append_field(data: dict[str, dict[str, FieldRelation]], field_key: str, value: FieldValue, issue_id: str):
   if field_key not in data:
      data[field_key] = {}
   value_id = value if isinstance(value, str) else value['id']
   if value_id not in data[field_key]:
      data[field_key][value_id] = {
         'value': value,
         'issues': []
      }
   bisect.insort(data[field_key][value_id]['issues'], issue_id, key=int)

def append_meta(data: dict[str, dict[str, list[str]]], meta_key: str, value_id: str | None, issue_id: str):
   if meta_key not in data:
      data[meta_key] = {}
   value_id = '' if value_id is None else value_id
   if value_id not in data[meta_key]:
      data[meta_key][value_id] = []
   bisect.insort(data[meta_key][value_id], issue_id, key=int)

@dataclasses.dataclass
class RelationsBundle:
   keys: KeyLookups
   user: UserRelations
   fields: FieldRelations

   def load(self, folder: pathlib.Path):
      self.keys.load(folder / 'keys')
      self.user.load(folder / 'user')
      self.fields.load(folder / 'fields', folder / 'metas')

   def save(self, folder: pathlib.Path):
      self.keys.save(folder / 'keys')
      self.user.save(folder / 'user')
      self.fields.save(folder / 'fields', folder / 'metas')

def create_relations(archive: mojira.Archive) -> RelationsBundle:
   key_rel = KeyLookups()
   user_rel = UserRelations()
   field_rel = FieldRelations()
   issue_ids = list(archive.issue_ids())
   for issue_id in issue_ids:
      issue = archive.get_issue_data(issue_id)
      assert issue is not None
      key_rel.issue_keys[issue['key']] = issue_id
      fields = issue['fields']
      append_meta(field_rel.metas, 'resolution', fields['resolution'], issue_id)
      append_meta(field_rel.metas, 'issuetype', fields['issuetype'], issue_id)
      append_meta(field_rel.metas, 'project', fields['project'], issue_id)
      append_meta(field_rel.metas, 'status', fields['status'], issue_id)
      append_meta(field_rel.metas, 'creator', fields['creator'], issue_id)
      append_meta(field_rel.metas, 'reporter', fields['reporter'], issue_id)
      if 'assignee' in fields:
         append_meta(field_rel.metas, 'assignee', fields['assignee'], issue_id)
      if 'versions' in fields:
         for val in fields['versions']:
            append_meta(field_rel.metas, 'versions', val, issue_id)
      if 'fixVersions' in fields:
         for val in fields['fixVersions']:
            append_meta(field_rel.metas, 'fixVersions', val, issue_id)
      if 'security' in fields:
         append_field(field_rel.fields, 'security', fields['security'], issue_id)
      if 'priority' in fields and fields['priority'] is not None:
         append_field(field_rel.fields, 'priority', fields['priority'], issue_id)
      if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
         append_field(field_rel.fields, 'customfield_12800', fields['customfield_12800'], issue_id)
      if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
         append_field(field_rel.fields, 'customfield_12200', fields['customfield_12200'], issue_id)
      if 'customfield_10402' in fields and fields['customfield_10402'] is not None:
         append_field(field_rel.fields, 'customfield_10402', fields['customfield_10402'], issue_id)
      if 'customfield_12301' in fields and fields['customfield_12301'] is not None:
         append_field(field_rel.fields, 'customfield_12301', fields['customfield_12301'], issue_id)
      if 'customfield_12400' in fields and fields['customfield_12400'] is not None:
         append_field(field_rel.fields, 'customfield_12400', fields['customfield_12400'], issue_id)
      if 'customfield_12900' in fields and fields['customfield_12900'] is not None:
         append_field(field_rel.fields, 'customfield_12900', fields['customfield_12900'], issue_id)
      if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
         append_field(field_rel.fields, 'customfield_10500', fields['customfield_10500'], issue_id)
      if 'customfield_10501' in fields and fields['customfield_10501'] is not None:
         append_field(field_rel.fields, 'customfield_10501', fields['customfield_10501'], issue_id)
      for val in fields['labels']:
         append_field(field_rel.fields, 'labels', val, issue_id)
      if 'components' in fields:
         for val in fields['components']:
            append_field(field_rel.fields, 'components', val, issue_id)
      if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
         for val in fields['customfield_11901']:
            append_field(field_rel.fields, 'customfield_11901', val, issue_id)
      for comment in fields['comment']['comments']:
         append_user_action(user_rel.comments, comment.get('author'), issue_id, comment['id'])
         append_user_action(user_rel.edits, comment.get('updateAuthor'), issue_id, comment['id'])
         if 'visibility' in comment and comment['visibility']['type'] == 'group':
            append_group_comment(user_rel.groups, comment['visibility']['value'], issue_id, comment['id'])
      for change in issue['changelog']['histories']:
         append_user_action(user_rel.changes, change['author'], issue_id, change['id'])
         for item in change['items']:
            if item['field'] == 'Key' and item['fromString'] is not None:
               key_rel.issue_keys[item['fromString']] = issue_id
      for attachment in fields['attachment']:
         data = archive.get_attachment_data(attachment)
         assert data is not None
         append_user_action(user_rel.attachments, data.get('author'), issue_id, attachment)
   for user_key in archive.user_keys():
      user = archive.get_user_data(user_key)
      assert user is not None
      key_rel.user_keys[user['name'].casefold()] = user_key
      for group in user['groups']['items']:
         append_group_user(user_rel.groups, group['name'], user_key)
   for user_key in archive.unknown_user_keys():
      user = archive.get_unknown_user_data(user_key)
      assert user is not None
      key_rel.user_keys[user['name'].casefold()] = user_key
   return RelationsBundle(
      keys=key_rel,
      user=user_rel,
      fields=field_rel
   )

def main():
   dotenv.load_dotenv()
   archive = mojira.Archive(pathlib.Path(os.environ['ARCHIVE_DATA']))
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   relations = create_relations(archive)
   print('Writing...')
   relations.save(pathlib.Path(os.environ['ARCHIVE_RELATIONS']))

if __name__ == '__main__':
   main()
