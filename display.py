import bisect
import dataclasses
import datetime
import pathlib
import typing
import urllib.parse

import bs4

import markup
import markup_relations
import mojira
import relations
from jiratypes import Attachment, Comment, InwardIssueLink, Issue, NewComment, OutwardIssueLink, Project, Revision, RevisionChange, UnknownUser, User, Version
from web import append_class

@dataclasses.dataclass
class ViewPerms:
   hidden_projects: list[str]
   hidden_group_comments: list[str]
   hidden_security_levels: list[str]
   hidden_secret_comments: bool
   hidden_deleted_comments: bool
   hidden_json_data: bool

   def __init__(self, data: dict[str, typing.Any]):
      self.hidden_projects = data['hidden_projects']
      self.hidden_group_comments = data['hidden_group_comments']
      self.hidden_security_levels = data['hidden_security_levels']
      self.hidden_secret_comments = data['hidden_secret_comments']
      self.hidden_deleted_comments = data['hidden_deleted_comments']
      self.hidden_json_data = data['hidden_json_data']

   def project_visible(self, project_id: str) -> bool:
      return project_id not  in self.hidden_projects

   def group_comments_visible(self, group: str) -> bool:
      return group not in self.hidden_group_comments

   def comment_visible(self, rels: relations.UserRelations, issue_id: str, comment_id: str) -> bool:
      for group in self.hidden_group_comments:
         if comment_id in rels.groups[group]['comments'].get(issue_id, []):
            return False
      return True

   def issue_visible(self, rels: relations.FieldRelations, issue_id: str) -> bool:
      for project in self.hidden_projects:
         if issue_id in rels.metas['project'][project]:
            return False
      for security in self.hidden_security_levels:
         if issue_id in rels.fields['security'][security]['issues']:
            return False
      return True

@dataclasses.dataclass
class ValueDisplay:
   id: str | None
   name: str
   description: str | None
   icon: str | None

def meta_display(metas: mojira.ArchiveMetas, meta_id: mojira.META_TYPE, value_id: str | None) -> ValueDisplay | None:
   if meta_id == 'resolution' and value_id is None:
      return ValueDisplay(None, 'Unresolved', None, None)
   assert value_id is not None
   if value_id not in metas.metas[meta_id]:
      return None
   meta = metas.metas[meta_id][value_id]
   icon = meta['avatarUrls']['48x48'] if 'avatarUrls' in meta else None
   return ValueDisplay(value_id, meta['name'], meta['description'], icon)

def field_display(rels: relations.FieldRelations, field_id: str, value_id: str) -> ValueDisplay | None:
   if value_id not in rels.fields[field_id]:
      return None
   full_value = rels.fields[field_id][value_id]['value']
   assert full_value is not None
   if isinstance(full_value, str):
      return ValueDisplay(value_id, full_value, None, None)
   desc = full_value.get('description')
   icon = full_value.get('iconUrl')
   if 'name' in full_value:
      name = full_value['name']
   else:
      name = full_value['value']
   return ValueDisplay(value_id, name, desc, icon)

def project_detail_links(project: Project, json: pathlib.PurePath | None) -> typing.Generator[tuple[str, str]]:
   portal_num = portal_number(project['key'])
   if json is not None:
      yield ('JSON', urllib.parse.quote(str(json)))
   yield ('bugs.mojang.com', f'https://bugs.mojang.com/browse/{project['key']}')
   if portal_num is not None:
      yield ('report.bugs.mojang.com', f'https://report.bugs.mojang.com/servicedesk/customer/portal/{portal_num}')
   yield ('mojira.atlassian.net', f'https://mojira.atlassian.net/browse/{project['key']}')

def issue_detail_links(issue: Issue, project: Project | None, json: pathlib.PurePath | None) -> typing.Generator[tuple[str, str]]:
   key = issue['key']
   portal_num = portal_number(project['key']) if project is not None else None
   if json is not None:
      yield ('JSON', urllib.parse.quote(str(json)))
   yield ('mojira.dev', f'https://mojira.dev/{key}')
   yield ('bugs.mojang.com', f'https://bugs.mojang.com/browse/{key}')
   if portal_num is not None:
      yield ('report.bugs.mojang.com', f'https://report.bugs.mojang.com/servicedesk/customer/portal/{portal_num}/{key}')
   yield ('mojira.atlassian.net', f'https://mojira.atlassian.net/browse/{key}')

@dataclasses.dataclass
class HistoricValue:
   id: str
   name: str

@dataclasses.dataclass
class HistoricProjectValue:
   id: str
   name: str
   project: str

HistoricFields = typing.TypedDict('HistoricFields', {
   'labels': typing.NotRequired[list[HistoricValue]],
   'customfield_11901': typing.NotRequired[list[HistoricValue] | None],
   'issuelinks': list[HistoricValue],
   'attachments': list[HistoricValue],
   'components': list[HistoricValue],
   'versions': list[HistoricProjectValue],
   'fixVersions': list[HistoricProjectValue],
   'customfield_10500': typing.NotRequired[HistoricValue | None],
   'customfield_12800': typing.NotRequired[HistoricValue | None],
   'customfield_10501': typing.NotRequired[HistoricValue | None],
   'customfield_10402': typing.NotRequired[HistoricValue | None],
   'customfield_12301': typing.NotRequired[HistoricValue | None],
   'customfield_12400': typing.NotRequired[HistoricValue | None],
   'customfield_12900': typing.NotRequired[HistoricValue | None],
   'customfield_12200': typing.NotRequired[HistoricValue | None],
   'priority': typing.NotRequired[HistoricValue | None],
   'security': typing.NotRequired[HistoricValue | None],
   'resolution': typing.NotRequired[HistoricValue | None],
   'status': typing.NotRequired[HistoricValue],
   'customfield_11500': typing.NotRequired[str | None],
   'customfield_11801': typing.NotRequired[str | None],
   'customfield_11802': typing.NotRequired[str | None],
   'customfield_11800': typing.NotRequired[str | None],
   'customfield_11300': typing.NotRequired[str | None],
   'customfield_12201': typing.NotRequired[str | None],
   'assignee': typing.NotRequired[HistoricValue | None],
   'reporter': typing.NotRequired[HistoricValue | None],
   'key': typing.NotRequired[str],
   'summary': typing.NotRequired[str],
   'project': str,
})

@dataclasses.dataclass
class InitialData:
   fields: HistoricFields
   description_revision_id: str | None
   environment_revision_id: str | None

def get_initial_data(archive: mojira.Archive, metas: mojira.ArchiveMetas, issue: Issue, final_project: Project | None, revisions: list[Revision]) -> InitialData:
   fields = issue['fields']
   result: HistoricFields = {
      'issuelinks': [to_historic_link(archive, metas, x) for x in fields['issuelinks']],
      'attachments': [to_historic_attachment(archive, x) for x in fields['attachment']],
      'components': [HistoricValue(x['id'], x['name']) for x in fields['components']] if 'components' in fields else [],
      'versions': [to_historic_version(final_project, x) for x in fields['versions']] if 'versions' in fields and final_project is not None else [],
      'fixVersions': [to_historic_version(final_project, x) for x in fields['fixVersions']] if 'fixVersions' in fields and final_project is not None else [],
      'project': fields['project']
   }
   description_revision: str | None = None
   environment_revision: str | None = None
   for revision in revisions:
      for change in revision['items']:
         match change['field']:
            case 'labels':
               if 'labels' not in result:
                  result['labels'] = label_splitter(change['from'], change['fromString'])
            case 'Category':
               if 'customfield_11901' not in result:
                  result['customfield_11901'] = category_splitter(change['from'], change['fromString'])
            case 'Confirmation Status':
               insert_historic_field(result, 'customfield_10500', change)
            case 'Area':
               insert_historic_field(result, 'customfield_12800', change)
            case 'Game Mode':
               insert_historic_field(result, 'customfield_10501', change)
            case 'Platform' | 'Device':
               insert_historic_field(result, 'customfield_10402', change)
            case 'Realms Platform':
               insert_historic_field(result, 'customfield_12301', change)
            case 'Dungeons Platform':
               insert_historic_field(result, 'customfield_12400', change)
            case 'Legends Platform':
               insert_historic_field(result, 'customfield_12900', change)
            case 'Mojang Priority':
               insert_historic_field(result, 'customfield_12200', change)
            case 'priority':
               insert_historic_field(result, 'priority', change)
            case 'security':
               insert_historic_field(result, 'security', change)
            case 'resolution':
               insert_historic_field(result, 'resolution', change)
            case 'status':
               if 'status' not in result:
                  assert change['from'] is not None
                  assert change['fromString'] is not None
                  result['status'] = HistoricValue(change['from'], change['fromString'])
            case 'ADO' | 'VSO':
               if 'customfield_11500' not in result:
                  result['customfield_11500'] = change['fromString']
            case 'Impact':
               if 'customfield_11801' not in result:
                  result['customfield_11801'] = change['fromString']
            case 'Regression Builds':
               if 'customfield_11802' not in result:
                  result['customfield_11802'] = change['fromString']
            case 'Partner Team Reporting':
               if 'customfield_11800' not in result:
                  result['customfield_11800'] = change['fromString']
            case 'Operating System Version':
               if 'customfield_11300' not in result:
                  result['customfield_11300'] = change['fromString']
            case 'Triaged Time':
               if 'customfield_12201' not in result:
                  if change['from'] == '':
                     result['customfield_12201'] = None
                  else:
                     result['customfield_12201'] = change['from']
            case 'assignee':
               insert_historic_field(result, 'assignee', change)
            case 'reporter':
               insert_historic_field(result, 'reporter', change)
            case 'Key':
               if 'key' not in result:
                  assert change['fromString'] is not None
                  result['key'] = change['fromString']
            case 'summary':
               if 'summary' not in result:
                  assert change['fromString'] is not None
                  result['summary'] = change['fromString']
            case 'description':
               if description_revision is None:
                  description_revision = revision['id']
            case 'environment':
               if environment_revision is None:
                  environment_revision = revision['id']
            case _:
               pass
   for revision in reversed(revisions):
      project_move = get_project_move(revision)
      if project_move is not None:
         result['project'] = project_move.before
      for change in reversed(sorted(revision['items'], key=revision_order_key)):
         match change['field']:
            case 'Link':
               insert_historic_list_field(result, 'issuelinks', change, check_both=True)
            case 'Attachment':
               insert_historic_list_field(result, 'attachments', change)
            case 'Component':
               insert_historic_list_field(result, 'components', change)
            case 'Version':
               insert_historic_versions_field(result, 'versions', change)
            case 'Fix Version':
               insert_historic_versions_field(result, 'fixVersions', change)
            case _:
               pass
   if 'labels' not in result:
      result['labels'] = [HistoricValue(x, x) for x in fields['labels']]
   if 'customfield_11901' not in result and 'customfield_11901' in fields:
      if fields['customfield_11901'] is None:
         result['customfield_11901'] = None
      else:
         result['customfield_11901'] = [HistoricValue(x['id'], x['value']) for x in fields['customfield_11901']]
   if 'customfield_10500' not in result and 'customfield_10500' in fields:
      val = fields['customfield_10500']
      result['customfield_10500'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_12800' not in result and 'customfield_12800' in fields:
      val = fields['customfield_12800']
      result['customfield_12800'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_10501' not in result and 'customfield_10501' in fields:
      val = fields['customfield_10501']
      result['customfield_10501'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_10402' not in result and 'customfield_10402' in fields:
      val = fields['customfield_10402']
      result['customfield_10402'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_12301' not in result and 'customfield_12301' in fields:
      val = fields['customfield_12301']
      result['customfield_12301'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_12400' not in result and 'customfield_12400' in fields:
      val = fields['customfield_12400']
      result['customfield_12400'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_12900' not in result and 'customfield_12900' in fields:
      val = fields['customfield_12900']
      result['customfield_12900'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'customfield_12200' not in result and 'customfield_12200' in fields:
      val = fields['customfield_12200']
      result['customfield_12200'] = None if val is None else HistoricValue(val['id'], val['value'])
   if 'priority' not in result and 'priority' in fields:
      val = fields['priority']
      result['priority'] = None if val is None else HistoricValue(val['id'], val['name'])
   if 'security' not in result and 'security' in fields:
      val = fields['security']
      result['security'] = HistoricValue(fields['security']['id'], fields['security']['name'])
   if 'resolution' not in result:
      val = fields['resolution']
      if val is None:
         result['resolution'] = None
      else:
         resolution = metas.resolutions[val]
         result['resolution'] = HistoricValue(val, resolution['name'])
   if 'status' not in result:
      val = fields['status']
      status = metas.statuses[val]
      result['status']  = HistoricValue(val, status['name'])
   if 'customfield_11500' not in result and 'customfield_11500' in fields:
      result['customfield_11500'] = fields['customfield_11500']
   if 'customfield_11801' not in result and 'customfield_11801' in fields:
      result['customfield_11801'] = fields['customfield_11801']
   if 'customfield_11802' not in result and 'customfield_11802' in fields:
      result['customfield_11802'] = fields['customfield_11802']
   if 'customfield_11800' not in result and 'customfield_11800' in fields:
      result['customfield_11800'] = fields['customfield_11800']
   if 'customfield_11300' not in result and 'customfield_11300' in fields:
      result['customfield_11300'] = fields['customfield_11300']
   if 'customfield_12201' not in result and 'customfield_12201' in fields:
      result['customfield_12201'] = fields['customfield_12201']
   if 'assignee' not in result and 'assignee' in fields:
      val = fields['assignee']
      if val is None:
         result['assignee'] = None
      else:
         user_data = get_user(archive, val)
         result['assignee'] = HistoricValue(val, user_data['displayName'])
   if 'reporter' not in result:
      val = fields['reporter']
      if val is None:
         result['reporter'] = None
      else:
         user_data = get_user(archive, val)
         assert user_data is not None
         result['reporter'] = HistoricValue(val, user_data['displayName'])
   if 'key' not in result:
      result['key'] = issue['key']
   if 'summary' not in result:
      result['summary'] = fields['summary']
   return InitialData(result, description_revision, environment_revision)

def to_historic_link(archive: mojira.Archive, metas: mojira.ArchiveMetas, link: OutwardIssueLink | InwardIssueLink) -> HistoricValue:
   link_type = metas.link_types[link['type']]
   if 'inwardIssue' in link:
      dir = link_type['inward']
      issue_data = archive.get_issue_data(link['inwardIssue'])
   else:
      dir = link_type['outward']
      issue_data = archive.get_issue_data(link['outwardIssue'])
   assert issue_data is not None
   return HistoricValue(issue_data['key'], f'This issue {dir} {issue_data['key']}')

def to_historic_attachment(archive: mojira.Archive, attach_id: str) -> HistoricValue:
   attach_data = archive.get_attachment_data(attach_id)
   assert attach_data is not None
   return HistoricValue(attach_id, attach_data['filename'])

def to_historic_version(project: Project, version_id: str) -> HistoricProjectValue:
   version_data = next(x for x in project['versions'] if x['id'] == version_id)
   return HistoricProjectValue(version_id, version_data['name'], project['id'])

def label_splitter(source: str | None, string: str | None) -> list[HistoricValue]:
   assert source is None
   assert string is not None
   if string == '':
      return []
   return [HistoricValue(x, x) for x in string.split(' ')]

def category_splitter(source: str | None, string: str | None) -> list[HistoricValue]:
   if source is None or string is None or source == '' or string == '':
      return []
   source = source.removeprefix('[').removesuffix(']')
   source_list = source.split(', ')
   string_list = string.split(',')
   assert len(source_list) == len(string_list)
   return list(map(lambda x: HistoricValue(x[0], x[1]), zip(source_list, string_list)))

def insert_historic_field(fields: HistoricFields, field_id: str, change: RevisionChange):
   if field_id not in fields:
      if change['from'] is None:
         fields[field_id] = None
      else:
         assert change['fromString'] is not None
         fields[field_id] = HistoricValue(change['from'], change['fromString'])

def insert_historic_list_field(fields: HistoricFields, field_id: str, change: RevisionChange, check_both: bool=False):
   if change['to'] is not None:
      assert change['from'] is None
      assert change['toString'] is not None
      if check_both:
         filtered = [x for x in fields[field_id] if x.id != change['to'] and x.name != change['toString']]
      else:
         filtered = [x for x in fields[field_id] if x.id != change['to']]
      fields[field_id][:] = filtered
   elif change['from'] is not None:
      assert change['to'] is None
      assert change['fromString'] is not None
      fields[field_id].append(HistoricValue(change['from'], change['fromString']))

def insert_historic_versions_field(fields: HistoricFields, field_id: str, change: RevisionChange):
   if change['to'] is not None:
      assert change['from'] is None
      assert change['toString'] is not None
      fields[field_id][:] = [x for x in fields[field_id] if x.id != change['to']]
   elif change['from'] is not None:
      assert change['to'] is None
      assert change['fromString'] is not None
      fields[field_id].append(HistoricProjectValue(change['from'], change['fromString'], fields['project']))

def revision_order_key(change: RevisionChange) -> int:
   if change['field'] == 'Key':
      return 0
   if change['field'] == 'status':
      return 1
   if change['field'] == 'resolution':
      return 2
   if change['field'] in ('Version', 'Fix Version'):
      return 5 if change['to'] is None else 3
   return 6

@dataclasses.dataclass
class ProjectChange:
   before: str
   after: str

@dataclasses.dataclass
class TrackedChange:
   id: str
   change: RevisionChange
   project_move: ProjectChange | None

@dataclasses.dataclass
class MergedRevision:
   user_key: str
   start_time: datetime.datetime
   end_time: datetime.datetime
   changes: list[TrackedChange]

def get_project_move(revision: Revision) -> ProjectChange | None:
   for entry in revision['items']:
      if entry['field'] in ('project', 'Project'):
         assert entry['from'] is not None
         assert entry['to'] is not None
         return ProjectChange(entry['from'], entry['to'])
   return None

def merge_revisions(revisions: list[Revision], threshold: datetime.timedelta) -> list[MergedRevision]:
   merged_revisions: list[MergedRevision] = []
   current: MergedRevision | None = None
   for revision in revisions:
      time = datetime.datetime.fromisoformat(revision['created'])
      project_move = get_project_move(revision)
      changes = [TrackedChange(revision['id'], x, project_move) for x in revision['items']]
      merged = MergedRevision(
         user_key=revision['author'],
         start_time=time,
         end_time=time,
         changes=changes
      )
      if current is None:
         current = merged
      elif revision['author'] == current.user_key and time - current.end_time <= threshold:
         current.end_time = time
         current.changes.extend(changes)
      else:
         merged_revisions.append(current)
         current = merged
   if current is not None:
      merged_revisions.append(current)
   return merged_revisions

def get_avatar_path(archive: mojira.Archive, folder: pathlib.Path, url: str) -> pathlib.Path | None:
   avatar_id = archive.get_avatar_id(url)
   avatar_file = folder / (avatar_id + '.png')
   if avatar_file.exists():
      return avatar_file
   avatar_file = folder / (avatar_id + '.svg')
   if avatar_file.exists():
      return avatar_file
   return None

def get_issue(archive: mojira.Archive, issue_id: str) -> Issue:
   issue = archive.get_issue_data(issue_id)
   assert issue is not None
   return issue

def get_user(archive: mojira.Archive, user_key: str) -> User | UnknownUser:
   user = archive.get_user_data(user_key)
   if user is None:
      user = archive.get_unknown_user_data(user_key)
   assert user is not None
   return user

def portal_number(project_key: str) -> int | None:
   return {'MCPE': 6, 'MC': 2, 'MCL': 7, 'REALMS': 9, 'WEB': 10, 'BDS': 4, 'MCM': 11}.get(project_key)

def field_name(metas: mojira.ArchiveMetas, field_id: str) -> str:
   extras = {'components': 'Component'}
   if field_id in extras:
      return extras[field_id]
   return metas.fields[field_id]['name']

def user_role(user: User) -> tuple[str, int] | None:
   role_order: list[str] = ['bot', 'system-administrators', '4jstudios', 'java', 'developers', 'administrators', 'mojang', 'microsoft', 'staff', 'helper', 'partners']
   user_groups: list[str] = [x['name'] for x in user['groups']['items']]
   for i, entry in enumerate(role_order):
      if entry in user_groups:
         return (entry, i)
   return None

def get_link_dir(full_str: str, issue_key: str) -> str:
   assert full_str.startswith('This issue ')
   assert full_str.endswith(issue_key)
   return full_str[len('This issue '):-(len(issue_key) + 1)]

def format_number(number: int) -> str:
   return format(number, ',')

def import_fake_missing_data(archive: mojira.Archive, metas: mojira.ArchiveMetas):
   metas.fields['customfield_12400'] = {
      'id': 'customfield_12400',
      'custom': True,
      'name': 'Dungeons Platform'
   }
   metas.fields['customfield_12900'] = {
      'id': 'customfield_12900',
      'custom': True,
      'name': 'Legends Platform'
   }
   metas.projects['11901'] = {
      'id': '11901',
      'key': 'MCD',
      'name': 'Minecraft Dungeons',
      'lead': 'mattgartzke',
      'description': '<div>\r\n<p><img src="https://assets.mojang.com/bugs_minecraft_dungeons.svg" align="absmiddle" border="0" width="439"></p>\r\n<p><strong>Welcome to the Minecraft Dungeons Bug Tracker!</strong></p>\r\n\r\n<p>The Minecraft Dungeons bug tracker is no longer active for new bug reports.</p>\r\n\r\n<p>Version 1.17 was Minecraft Dungeons\' final update. Our team has now moved on to new projects that continue to explore experiences in the Minecraft universe. This means that there are no new features or content updates planned for the game.</p>\r\n\r\n<p>All online services in Minecraft Dungeons remain functional including multiplayer, cloud saves, Tower rotations, etc. </p>\r\n\r\n<p>Learn more at <a class="external-link" href="https://aka.ms/Dungeons25Million" rel="nofollow">aka.ms/Dungeons25Million</a></p>\r\n\r\n<p>You can still discuss the game on the Minecraft Discord server at <a class="external-link" href="https://discord.gg/Minecraft" rel="nofollow">discord.gg/Minecraft</a>. If you need technical support for the game or encounter server issues, please visit <a class="external-link" href="https://help.minecraft.net/" rel="nofollow">help.minecraft.net</a></p>\r\n\r\n</div>',
      'avatarUrls': {
         '48x48': 'https://bugs-legacy.mojang.com/secure/projectavatar?pid=11901&avatarId=35072'
      },
      'versions': [
         {
            'id': '19204',
            'name': 'Version #19204',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19304',
            'name': 'Version #19304',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19500',
            'name': 'Version #19500',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19526',
            'name': 'Version #19526',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19536',
            'name': 'Version #19536',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19553',
            'name': 'Version #19553',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19604',
            'name': 'Version #19604',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19622',
            'name': 'Version #19622',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19637',
            'name': 'Version #19637',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19647',
            'name': 'Version #19647',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19650',
            'name': 'Version #19650',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19710',
            'name': 'Version #19710',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19718',
            'name': 'Version #19718',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19820',
            'name': 'Version #19820',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19821',
            'name': 'Version #19821',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19834',
            'name': 'Version #19834',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19902',
            'name': 'Version #19902',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19903',
            'name': 'Version #19903',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19904',
            'name': 'Version #19904',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '19930',
            'name': 'Version #19930',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20006',
            'name': 'Version #20006',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20120',
            'name': 'Version #20120',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20223',
            'name': 'Version #20223',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20224',
            'name': 'Version #20224',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20231',
            'name': 'Version #20231',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20311',
            'name': 'Version #20311',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20506',
            'name': 'Version #20506',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20602',
            'name': 'Version #20602',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20609',
            'name': 'Version #20609',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20625',
            'name': 'Version #20625',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20802',
            'name': 'Version #20802',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20912',
            'name': 'Version #20912',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '20928',
            'name': 'Version #20928',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '21204',
            'name': 'Version #21204',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '21205',
            'name': 'Version #21205',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '21209',
            'name': 'Version #21209',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         {
            'id': '21247',
            'name': 'Version #21247',
            'projectId': 11901,
            'archived': True,
            'released': True
         }
      ]
   }
   metas.projects['12200'] = {
      'id': '12200',
      'key': 'MCLG',
      'name': 'Minecraft Legends',
      'lead': 'mega_spud',
      'description': '<div>\r\n<p><img src="https://assets.mojang.com/bugs_minecraft_legends.svg" align="absmiddle" border="0" width="439"></p>\r\n<p><strong>Welcome to the Minecraft Legends Bug Tracker!</strong></p>\r\n<p>Thank you for all of your bug reports in this project! However, the Minecraft Legends bug tracker is no longer active for new bug reports and comments.</p>\r\n<p>More information can be found at <a class="external-link" href="https://aka.ms/LegendsJanuaryUpdates" rel="nofollow">aka.ms/LegendsJanuaryUpdates</a>.</p>\r\n<p>You can still discuss the game on the Minecraft Discord server at <a class="external-link" href="https://discord.gg/Minecraft" rel="nofollow">discord.gg/Minecraft</a>. If you need technical support for the game or encounter server issues, please visit <a class="external-link" href="https://help.minecraft.net/" rel="nofollow">help.minecraft.net</a></p>\r\n</div>',
      'avatarUrls': {
         '48x48': 'https://bugs-legacy.mojang.com/secure/projectavatar?pid=12200&avatarId=86040'
      },
      'versions': [
         {
            'id': '21436',
            'name': 'Version #21436',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21444',
            'name': 'Version #21444',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21478',
            'name': 'Version #21478',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21479',
            'name': 'Version #21479',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21510',
            'name': 'Version #21510',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21511',
            'name': 'Version #21511',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21552',
            'name': 'Version #21552',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21553',
            'name': 'Version #21553',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21605',
            'name': 'Version #21605',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21606',
            'name': 'Version #21606',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21623',
            'name': 'Version #21623',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21807',
            'name': 'Version #21807',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         {
            'id': '21829',
            'name': 'Version #21829',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
      ]
   }

@dataclasses.dataclass
class RenderableComment:
   comment: Comment | NewComment
   external_issue: Issue | None
   parsed: markup.ParsedMarkup
   date: datetime.datetime
   secret: bool

@dataclasses.dataclass
class RenderableMention:
   issue: Issue
   comment: Comment | NewComment | None
   date: datetime.datetime
   parsed: markup.ParsedMarkup

@dataclasses.dataclass
class CachedValueInfo:
   display: ValueDisplay
   issues: list[str]

@dataclasses.dataclass
class CachedMetaInfo:
   id: mojira.META_TYPE
   name: str
   values: dict[str | None, CachedValueInfo]

@dataclasses.dataclass
class CachedFieldInfo:
   id: str
   name: str
   values: dict[str, CachedValueInfo]

@dataclasses.dataclass
class CachedGroupInfo:
   id: str
   users: list[str]
   comments: list[RenderableComment]

@dataclasses.dataclass
class CachedVersionInfo:
   version: Version
   affected: list[str]
   fixed: list[str]

@dataclasses.dataclass
class CachedProjectInfo:
   project: Project
   description: bs4.BeautifulSoup | None
   issues: list[str]
   versions: dict[str, CachedVersionInfo]

@dataclasses.dataclass
class CachedComment:
   issue: Issue
   comment: Comment | NewComment
   date: datetime.datetime
   body: markup.ParsedMarkup

@dataclasses.dataclass
class CachedIssue:
   issue: Issue
   initial: InitialData
   created: datetime.datetime
   linked_issues: dict[str, list[str]]

@dataclasses.dataclass
class CachedIssueMarkup:
   description: markup.ParsedMarkup | None
   environment: markup.ParsedMarkup | None
   comments: list[RenderableComment]

@dataclasses.dataclass
class CachedIssueMentions:
   mentions: list[RenderableMention]

@dataclasses.dataclass
class CachedUser:
   user: User | UnknownUser
   reported: list[str]
   created: list[str]
   assigned: list[str]
   attachments: dict[str, list[str]]
   changes: dict[str, list[str]]

@dataclasses.dataclass
class CachedUserMarkup:
   comments: list[RenderableComment]
   mentions: list[RenderableMention]

TKey = typing.TypeVar('TKey')
TVal = typing.TypeVar('TVal')
class CacheLookup[TKey, TVal]:
   getter: typing.Callable[[TKey], TVal]
   cache: dict[TKey, TVal]

   def __init__(self, getter: typing.Callable[[TKey], TVal]):
      self.getter = getter
      self.cache = {}

   def get(self, key: TKey) -> TVal:
      if key in self.cache:
         return self.cache[key]
      val = self.getter(key)
      self.cache[key] = val
      return val

class DisplayCache:
   just_issue: CacheLookup[str, Issue]
   issue_info: CacheLookup[str, CachedIssue]
   issue_markup: CacheLookup[str, CachedIssueMarkup]
   issue_mentions: CacheLookup[str, CachedIssueMentions]
   comment: CacheLookup[tuple[str, str], CachedComment]
   secret_comment: CacheLookup[str, list[CachedComment]]
   just_user: CacheLookup[str, User | UnknownUser]
   user_info: CacheLookup[str, CachedUser]
   user_markup: CacheLookup[str, CachedUserMarkup]
   attachment: CacheLookup[str, Attachment]
   metas: dict[mojira.META_TYPE, CachedMetaInfo]
   fields: dict[str, CachedFieldInfo]
   groups: dict[str, CachedGroupInfo]
   projects: dict[str, CachedProjectInfo]
   valid_issues: set[str]
   valid_users: set[str]
   all_issues: list[str]
   all_users: list[str]

   def get_issues(self, issues: list[str]) -> typing.Iterable[Issue]:
      return (self.just_issue.get(x) for x in issues)

   def __init__(self, archive: mojira.Archive, metas: mojira.ArchiveMetas, rels: relations.RelationsBundle, source: markup.MarkupSource, markup_rels: markup_relations.MarkupRelations, secret_comments: mojira.SecretComments, perms: ViewPerms):
      self.valid_issues = set(x for x in rels.keys.issue_keys.values() if perms.issue_visible(rels.fields, x))
      self.all_issues = sorted(self.valid_issues, key=lambda x: int(x))
      self.valid_users = set(rels.keys.user_keys.values())
      self.all_users = sorted(self.valid_users)

      def filter_issues(issues: list[str]) -> list[str]:
         return [x for x in issues if x in self.valid_issues]

      def filter_issue_items(items: dict[str, list[str]]) -> dict[str, list[str]]:
         return {k: v for k, v in items.items() if k in self.valid_issues}

      def filter_comments(issue_id: str, comments: list[str]) -> list[str]:
         return [x for x in comments if perms.comment_visible(rels.user, issue_id, x)]

      def filter_issue_comments(comments: dict[str, list[str]]) -> dict[str, list[str]]:
         return {k: filter_comments(k, v) for k, v in comments.items() if k in self.valid_issues}

      def just_issue_get(issue_id: str) -> Issue:
         assert issue_id in self.valid_issues
         return get_issue(archive, issue_id)
      self.just_issue = CacheLookup(just_issue_get)

      def just_user_get(user_key: str) -> User | UnknownUser:
         assert user_key in self.valid_users
         return get_user(archive, user_key)
      self.just_user = CacheLookup(just_user_get)

      def secret_comment_get(issue_id: str) -> list[CachedComment]:
         assert issue_id in self.valid_issues
         issue = just_issue_get(issue_id)
         comments = secret_comments.get(issue_id)
         cached: list[CachedComment] = []
         for comment in comments:
            body = source.get_secret_comment_body(issue_id, comment['id'])
            parsed = markup.parse_markup(body)
            date = datetime.datetime.fromisoformat(comment['created'])
            cached.append(CachedComment(issue, comment, date, parsed))
         return cached
      self.secret_comment = CacheLookup(secret_comment_get)

      def comment_get(issue_id: str, comment_id: str) -> CachedComment:
         assert issue_id in self.valid_issues
         issue = just_issue_get(issue_id)
         comment = next(x for x in issue['fields']['comment']['comments'] if x['id'] == comment_id)
         body = source.get_comment_body(issue_id, comment_id)
         parsed = markup.parse_markup(body)
         date = datetime.datetime.fromisoformat(comment['created'])
         cached = CachedComment(issue, comment, date, parsed)
         return cached
      self.comment = CacheLookup(lambda x: comment_get(x[0], x[1]))

      def get_renderable_mentions(rels: markup_relations.MarkupRelation, process: typing.Callable[[markup.ParsedMarkup]]) -> list[RenderableMention]:
         result: list[RenderableMention] = []
         for issue_id in rels['descriptions']:
            issue = issue_get(issue_id)
            markup = self.issue_markup.get(issue_id)
            if markup.description is not None:
               cloned = markup.description.clone()
               process(cloned)
               entry = RenderableMention(issue.issue, None, issue.created, cloned)
               bisect.insort_left(result, entry, key=lambda x: x.date)
         for issue_id in rels['environments']:
            issue = issue_get(issue_id)
            markup = self.issue_markup.get(issue_id)
            if markup.environment is not None:
               cloned = markup.environment.clone()
               process(cloned)
               entry = RenderableMention(issue.issue, None, issue.created, cloned)
               bisect.insort_left(result, entry, key=lambda x: x.date)
         for issue_id, comment_ids in rels['comments'].items():
            issue = just_issue_get(issue_id)
            for comment_id in comment_ids:
               info = self.comment.get((issue_id, comment_id))
               cloned = info.body.clone()
               process(cloned)
               entry = RenderableMention(issue, info.comment, info.date, cloned)
               bisect.insort_left(result, entry, key=lambda x: x.date)
         return result

      def issue_markup_get(issue_id: str) -> CachedIssueMarkup:
         issue = just_issue_get(issue_id)
         if issue['fields']['description'] is not None:
            body = source.get_issue_description(issue_id)
            desc = markup.parse_markup(body)
         else:
            desc = None
         if 'environment' in issue['fields'] and issue['fields']['environment'] is not None:
            body = source.get_issue_environment(issue_id)
            env = markup.parse_markup(body)
         else:
            env = None
         filtered_comments = filter_comments(issue_id, [x['id'] for x in issue['fields']['comment']['comments']])
         rendered_comments: list[RenderableComment] = []
         for comment_id in filtered_comments:
            cached = comment_get(issue_id, comment_id)
            entry = RenderableComment(cached.comment, None, cached.body, cached.date, secret=False)
            rendered_comments.append(entry)
         if not perms.hidden_secret_comments:
            for info in secret_comment_get(issue_id):
               entry = RenderableComment(info.comment, None, info.body, info.date, secret=True)
               bisect.insort_left(rendered_comments, entry, key=lambda x: x.date)
         return CachedIssueMarkup(desc, env, rendered_comments)
      self.issue_markup = CacheLookup(issue_markup_get)

      def issue_mentions_get(issue_id: str) -> CachedIssueMentions:
         assert issue_id in self.valid_issues
         mentions = markup_rels.issues.get(issue_id, {
            'descriptions': [],
            'environments': [],
            'comments': {}
         })
         filtered_mentions: markup_relations.MarkupRelation = {
            'descriptions': filter_issues(mentions['descriptions']),
            'environments': filter_issues(mentions['environments']),
            'comments': filter_issue_comments(mentions['comments'])
         }
         def process(tag: markup.ParsedMarkup):
            highlight_issue_mentions(tag, issue_id, rels.keys)
         rendered_mentions = get_renderable_mentions(filtered_mentions, process)
         return CachedIssueMentions(rendered_mentions)
      self.issue_mentions = CacheLookup(issue_mentions_get)

      def issue_get(issue_id: str) -> CachedIssue:
         issue = just_issue_get(issue_id)
         initial = get_initial_data(archive, metas, issue, try_project(self, issue['fields']['project']), issue['changelog']['histories'])
         date = datetime.datetime.fromisoformat(issue['fields']['created'])
         linked: dict[str, list[str]] = {}
         for link in issue['fields']['issuelinks']:
            if 'inwardIssue' in link:
               identity = metas.link_types[link['type']]['inward']
               linked_id = link['inwardIssue']
            else:
               identity = metas.link_types[link['type']]['outward']
               linked_id = link['outwardIssue']
            if linked_id in self.valid_issues:
               if identity not in linked:
                  linked[identity] = []
               linked[identity].append(linked_id)
         cached = CachedIssue(issue, initial, date, linked)
         return cached
      self.issue_info = CacheLookup(issue_get)

      def user_get(user_key: str) -> CachedUser:
         user = just_user_get(user_key)
         reported = rels.fields.metas['reporter'].get(user_key, [])
         created = rels.fields.metas['creator'].get(user_key, [])
         assigned = rels.fields.metas['assignee'].get(user_key, [])
         attachments = rels.user.attachments.get(user_key, {})
         changes = rels.user.changes.get(user_key, {})
         cached = CachedUser(
            user,
            filter_issues(reported),
            filter_issues(created),
            filter_issues(assigned),
            filter_issue_items(attachments),
            filter_issue_items(changes),
         )
         return cached
      self.user_info = CacheLookup(user_get)

      def user_markup_get(user_key: str) -> CachedUserMarkup:
         assert user_key in self.valid_users
         comments = rels.user.comments.get(user_key, {})
         filtered = filter_issue_comments(comments)
         rendered_comments: list[RenderableComment] = []
         for issue_id, comments in filtered.items():
            for comment_id in comments:
               cached = comment_get(issue_id, comment_id)
               entry = RenderableComment(cached.comment, cached.issue, cached.body, cached.date, secret=False)
               bisect.insort_left(rendered_comments, entry, key=lambda x: x.date)
         mentions = markup_rels.users.get(user_key, {
            'descriptions': [],
            'environments': [],
            'comments': {}
         })
         filtered_mentions: markup_relations.MarkupRelation = {
            'descriptions': filter_issues(mentions['descriptions']),
            'environments': filter_issues(mentions['environments']),
            'comments': filter_issue_comments(mentions['comments'])
         }
         def process(tag: markup.ParsedMarkup):
            highlight_user_mentions(tag, user_key, rels.keys)
         rendered_mentions = get_renderable_mentions(filtered_mentions, process)
         cached = CachedUserMarkup(rendered_comments, rendered_mentions)
         return cached
      self.user_markup = CacheLookup(user_markup_get)

      def attachment_get(attachment_id: str) -> Attachment:
         attachment = archive.get_attachment_data(attachment_id)
         assert attachment is not None
         return attachment
      self.attachment = CacheLookup(attachment_get)

      def project_order(info: CachedProjectInfo):
         return -len(info.issues)
      def meta_order(meta_id: mojira.META_TYPE):
         index = {'resolution': 0, 'status': 1}.get(meta_id, 2)
         return (index, meta_id)
      def field_order(info: CachedFieldInfo):
         return -sum(len(x.issues) for x in info.values.values())
      def group_order(info: CachedGroupInfo):
         return (-len(info.users), info.id)
      def meta_value_order(meta_id: mojira.META_TYPE, info: CachedValueInfo):
         if meta_id == 'resolution':
            resolution_status = 0 if info.display.id is None else 1
         elif meta_id == 'status':
            if info.display.id in ('5', '6'):
               resolution_status = 2
            elif info.display.id in ('3', '10200'):
               resolution_status = 1
            else:
               resolution_status = 0
         else:
            resolution_status = 0
         return (resolution_status, info.display.name)
      def field_value_order(info: CachedValueInfo):
         return (-len(info.issues), info.display.name)

      self.projects = {}
      for project_id, project in metas.projects.items():
         issues = rels.fields.metas['project'].get(project_id, [])
         if perms.project_visible(project_id):
            if len(project['description']) > 0:
               desc = bs4.BeautifulSoup(project['description'], 'html.parser')
            else:
               desc = None
            versions: dict[str, CachedVersionInfo] = {}
            for version in project['versions']:
               affected = rels.fields.metas['versions'].get(version['id'], [])
               fixed = rels.fields.metas['fixVersions'].get(version['id'], [])
               versions[version['id']] = CachedVersionInfo(version, filter_issues(affected), filter_issues(fixed))
            self.projects[project_id] = CachedProjectInfo(project, desc, filter_issues(issues), versions)
      sort_dict(self.projects, lambda x: project_order(x[1]))

      self.metas = {}
      for meta_id, meta in metas.metas.items():
         fname = field_name(metas, meta_id)
         self.metas[meta_id] = CachedMetaInfo(meta_id, fname, {})
         value_keys: list[str | None] = list(meta.keys())
         if meta_id == 'resolution':
            value_keys.insert(0, None)
         for value_key in value_keys:
            display = meta_display(metas, meta_id, value_key)
            assert display is not None
            issues = rels.fields.metas[meta_id].get('' if value_key is None else value_key, [])
            self.metas[meta_id].values[value_key] = CachedValueInfo(display, filter_issues(issues))
         sort_dict(self.metas[meta_id].values, lambda x: meta_value_order(typing.cast(mojira.META_TYPE, meta_id), x[1]))
      sort_dict(self.metas, lambda x: meta_order(x[0]))

      self.fields = {}
      for field_id, field in rels.fields.fields.items():
         fname = field_name(metas, field_id)
         self.fields[field_id] = CachedFieldInfo(field_id, fname, {})
         for value_key in field.keys():
            display = field_display(rels.fields, field_id, value_key)
            assert display is not None
            issues = rels.fields.fields[field_id][value_key]['issues']
            self.fields[field_id].values[value_key] = CachedValueInfo(display, filter_issues(issues))
         sort_dict(self.fields[field_id].values, lambda x: field_value_order(x[1]))
      sort_dict(self.fields, lambda x: field_order(x[1]))

      self.groups = {}
      for group, info in rels.user.groups.items():
         comments = info['comments'] if perms.group_comments_visible(group) else {}
         filtered = filter_issue_comments(comments)
         rendered_comments: list[RenderableComment] = []
         for issue_id, comments in filtered.items():
            for comment_id in comments:
               cached = comment_get(issue_id, comment_id)
               entry = RenderableComment(cached.comment, cached.issue, cached.body, cached.date, secret=False)
               bisect.insort_left(rendered_comments, entry, key=lambda x: x.date)
         self.groups[group] = CachedGroupInfo(group, info['users'], rendered_comments)
      sort_dict(self.groups, lambda x: group_order(x[1]))

K = typing.TypeVar('K')
V = typing.TypeVar('V')
def sort_dict(dictionary: dict[K, V], key: typing.Callable[[tuple[K, V]], typing.Any]):
   pairs = list(dictionary.items())
   dictionary.clear()
   for k, v in sorted(pairs, key=key):
      dictionary[k] = v

def highlight_issue_mentions(parsed: markup.ParsedMarkup, issue_id: str, keys: relations.KeyLookups):
   for entry in parsed.issues:
      if keys.try_get_issue_key(entry.key) == issue_id:
         append_class(entry.tag, 'mention')

def highlight_user_mentions(parsed: markup.ParsedMarkup, user_key: str, keys: relations.KeyLookups):
   for entry in parsed.users:
      if keys.try_get_user_key(entry.username) == user_key:
         append_class(entry.tag, 'mention')

def try_project(cache: DisplayCache, project_id: str) -> Project | None:
   if project_id in cache.projects:
      return cache.projects[project_id].project
   return None
