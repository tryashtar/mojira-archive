import json
import pathlib
import typing
import dataclasses
from jiratypes import DescriptionValue, CustomValue, Field, FieldSchema, IconValue, Issue, IssueFields
import mojira

PartialDiscreteValue = typing.TypedDict('PartialDiscreteValue', {
   'id': str,
   'name': str
})

@dataclasses.dataclass
class CustomField:
   def get_value(self, data: dict) -> CustomValue:
      return typing.cast(CustomValue, data)
   def get_revision_value(self, source: str | None, string: str | None) -> PartialDiscreteValue | None:
      if source is None:
         return None
      assert string is not None
      return {'id': source, 'name': string}

@dataclasses.dataclass
class CustomListField:
   def get_value(self, data: list) -> list[CustomValue]:
      return typing.cast(list[CustomValue], data)
   def get_revision_value(self, source: str | None, string: str | None) -> list[PartialDiscreteValue] | None:
      if source is None or string is None:
         return None
      if source == '' or string == '':
         return []
      source = source.removeprefix('[').removesuffix(']')
      source_list = source.split(', ')
      string_list = string.split(',')
      assert len(source_list) == len(string_list)
      result: list[PartialDiscreteValue] = list(({'id': x, 'name': y} for x, y in zip(source_list, string_list)))
      return result

@dataclasses.dataclass
class DiscreteField:
   def get_value(self, data: dict) -> DescriptionValue | IconValue:
      return typing.cast(DescriptionValue | IconValue, data)
   def get_revision_value(self, source: str | None, string: str | None) -> PartialDiscreteValue | None:
      if source is None:
         return None
      assert string is not None
      return {'id': source, 'name': string}

@dataclasses.dataclass
class DiscreteListField:
   def get_value(self, data: list) -> list[DescriptionValue | IconValue]:
      return typing.cast(list[DescriptionValue | IconValue], data)
   def get_revision_value(self, source: str | None, string: str | None) -> PartialDiscreteValue | None:
      if source is None:
         return None
      assert string is not None
      return {'id': source, 'name': string}

@dataclasses.dataclass
class LabelField:
   def get_value(self, data: list) -> list[str]:
      return typing.cast(list[str], data)
   def get_revision_value(self, source: str | None, string: str | None) -> list[str]:
      assert source is None
      assert string is not None
      return string.split(' ')

@dataclasses.dataclass
class MetaField:
   def get_value(self, data: str | None) -> str | None:
      return data
   def get_revision_value(self, source: str | None, string: str | None) -> PartialDiscreteValue | None:
      if source is None:
         return None
      assert string is not None
      return {'id': source, 'name': string}

@dataclasses.dataclass
class MetaListField:
   def get_value(self, data: list) -> list[str]:
      return typing.cast(list[str], data)

@dataclasses.dataclass
class OtherField:
   pass

FieldType = CustomField | CustomListField | DiscreteField | DiscreteListField | LabelField | MetaField | MetaListField | OtherField

def field_type(schema: FieldSchema) -> FieldType:
   meta_like = ['issuetype', 'project', 'resolution', 'status', 'version', 'user']
   discrete_like = ['priority', 'securitylevel', 'component']
   if schema['type'] == 'array':
      assert 'items' in schema
      if schema['items'] == 'option':
         return CustomListField()
      if schema['items'] in meta_like:
         return MetaListField()
      if schema['items'] in discrete_like:
         return DiscreteListField()
      if schema['items'] == 'string':
         return LabelField()
   if schema['type'] == 'option':
      return CustomField()
   if schema['type'] in meta_like:
      return MetaField()
   if schema['type'] in discrete_like:
      return DiscreteField()
   return OtherField()

@dataclasses.dataclass
class FieldInfo:
   key: str
   name: str
   field_type: FieldType

ExtraFieldInfo = typing.TypedDict('ExtraFieldInfo', {
   'deleted_revision_fields': list[str],
   'extra_custom_fields': dict[str, str],
   'revision_aliases': dict[str, str]
})

RevisionInfo = FieldInfo | None

class FieldsInfo:
   field_map: dict[str, FieldInfo]
   revision_map: dict[str, RevisionInfo]

   def __init__(self, fields: dict[str, Field], extra: ExtraFieldInfo):
      self.field_map = {}
      self.revision_map = {}
      for key, value in fields.items():
         if 'schema' in value:
            info = FieldInfo(key, value['name'], field_type(value['schema']))
            self.field_map[key] = info
            if value['custom']:
               self.revision_map[value['name']] = info
            if 'system' in value['schema']:
               self.revision_map[key] = info
      for entry in extra['deleted_revision_fields']:
         self.revision_map[entry] = None
      for key, value in extra['extra_custom_fields'].items():
         info = FieldInfo(key, value, CustomField())
         self.field_map[key] = info
         self.revision_map[value] = info
      for key, value in extra['revision_aliases'].items():
         self.revision_map[key] = self.field_map[value]

def get_issue_at_creation(issue: Issue, info: FieldsInfo) -> Issue:
   original_key = issue['key']
   original_fields: dict = {}
   for key, value in issue['fields'].items():
      original_fields[key] = value
   for revision in reversed(issue['changelog']['histories']):
      for change in reversed(revision['items']):
         if change['field'] == 'Key':
            assert change['fromString'] is not None
            original_key = change['fromString']
         else:
            field = info.revision_map[change['field']]
            if field is not None:
               original_fields[field.key] = field.apply_revision(change)
   final_fields = typing.cast(IssueFields, original_fields)
   final_fields['comment'] = {
      'comments': [],
      'total': 0
   }
   final_fields['votes'] = {
      'hasVoted': False,
      'votes': 0
   }
   final_fields['watches'] = {
      'isWatching': False,
      'watchCount': 0
   }
   final_fields['updated'] = issue['fields']['created']
   final_fields['resolutiondate'] = None
   assert final_fields['reporter'] == final_fields['creator']
   assert 'assignee' not in final_fields or final_fields['assignee'] is None
   assert 'fixVersions' not in final_fields or len(final_fields['fixVersions']) == 0
   assert len(final_fields['issuelinks']) == 0
   assert final_fields['resolution'] is None
   assert final_fields['status'] == '1'
   return {
      'id': issue['id'],
      'key': original_key,
      'fields': final_fields,
      'changelog': {
         'histories': [],
         'total': 0
      }
   }

def main():
   root = pathlib.Path('/d/Archives/Mojira')
   archive = mojira.Archive(root / 'data')
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   with open(root / 'extra_field_info.json', 'r', encoding='utf-8') as file:
      extra_info: ExtraFieldInfo = json.load(file)
   fields = FieldsInfo(metas.fields, extra_info)
   for issue in archive.issues():
      get_issue_at_creation(issue, fields)

if __name__ == '__main__':
   main()
