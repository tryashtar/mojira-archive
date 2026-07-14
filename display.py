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
from jiratypes import Comment, InwardIssueLink, Issue, NewComment, OutwardIssueLink, Project, Revision, RevisionChange, User
from web import append_class

@dataclasses.dataclass
class ViewPerms:
   hidden_projects: list[str]
   hidden_group_comments: list[str]
   hidden_security_levels: list[str]
   hidden_secret_comments: bool
   hidden_deleted_comments: bool
   hidden_json_data: bool

   def project_visible(self, project_id: str) -> bool:
      return project_id not  in self.hidden_projects

   def group_comments_visible(self, group: str) -> bool:
      return group not in self.hidden_group_comments

   def field_visible(self, field_id: str, value_key: str) -> bool:
      if field_id == 'security' and value_key in self.hidden_security_levels:
         return False
      return True

   def comment_visible(self, comment: Comment) -> bool:
      if 'visibility' not in comment:
         return True
      if comment['visibility']['type'] != 'group':
         return True
      return comment['visibility']['value'] not in self.hidden_group_comments

   def issue_visible(self, rels: relations.FieldRelations, issue_id: str) -> bool:
      for project in self.hidden_projects:
         if issue_id in rels.metas['project'][project]:
            return False
      for security in self.hidden_security_levels:
         if issue_id in rels.fields['security'][security]:
            return False
      return True

   def filter_projects(self, projects: typing.Iterable[Project]) -> typing.Iterable[Project]:
      return filter(lambda x: self.project_visible(x['id']), projects)

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
      return ValueDisplay(value_id, full_value['name'], desc, icon)
   return ValueDisplay(value_id, full_value['value'], desc, icon)

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
class RenderableComment:
   comment: Comment | NewComment
   external_issue: Issue | None
   rendered_body: bs4.BeautifulSoup
   date: datetime.datetime
   secret: bool

def get_renderable_issue_comments(source: markup.MarkupSource, secrets: mojira.SecretComments, issue: Issue, include_secrets: bool) -> list[RenderableComment]:
   result: list[RenderableComment] = []
   for comment in issue['fields']['comment']['comments']:
      body = source.get_comment_body(issue['id'], comment['id'])
      result.append(RenderableComment(comment, None, body, datetime.datetime.fromisoformat(comment['created']), secret=False))
   if include_secrets:
      for comment in secrets.get(issue['id']):
         body = source.get_secret_comment_body(issue['id'], comment['id'])
         bisect.insort_left(result, RenderableComment(comment, None, body, datetime.datetime.fromisoformat(comment['created']), secret=True), key=lambda x: x.date)
   return result

def get_renderable_user_comments(archive: mojira.Archive, source: markup.MarkupSource, fields: relations.FieldRelations, perms: ViewPerms, comment_dict: dict[str, list[str]]) -> list[RenderableComment]:
   result: list[RenderableComment] = []
   for issue_id, comments in comment_dict.items():
      if not perms.issue_visible(fields, issue_id):
         continue
      issue = get_issue(archive, issue_id)
      for comment_id in comments:
         comment = next(filter(lambda x: x['id'] == comment_id, issue['fields']['comment']['comments']))
         if not perms.comment_visible(comment):
            continue
         body = source.get_comment_body(issue_id, comment_id)
         bisect.insort_left(result, RenderableComment(comment, issue, body, datetime.datetime.fromisoformat(comment['created']), secret=False), key=lambda x: x.date)
   return result

@dataclasses.dataclass
class RenderableMention:
   issue: Issue
   comment: Comment | None
   date: datetime.datetime
   rendered_body: bs4.BeautifulSoup
   parsed: markup.ParsedMarkup

def highlight_issue_mentions(tag: bs4.BeautifulSoup, issue_id: str, keys: relations.KeyLookups) -> markup.ParsedMarkup:
   parsed = markup.parse_markup(tag)
   for entry in parsed.issues:
      if keys.try_get_issue_key(entry.key) == issue_id:
         append_class(entry.tag, 'mention')
   return parsed

def highlight_user_mentions(tag: bs4.BeautifulSoup, user_key: str, keys: relations.KeyLookups) -> markup.ParsedMarkup:
   parsed = markup.parse_markup(tag)
   for entry in parsed.users:
      if keys.try_get_user_key(entry.username) == user_key:
         append_class(entry.tag, 'mention')
   return parsed

def get_renderable_mentions(archive: mojira.Archive, source: markup.MarkupSource, rels: markup_relations.MarkupRelation, fields: relations.FieldRelations, perms: ViewPerms, parser: typing.Callable[[bs4.BeautifulSoup], markup.ParsedMarkup]) -> list[RenderableMention]:
   result: list[RenderableMention] = []
   for issue_id in rels['descriptions']:
      if not perms.issue_visible(fields, issue_id):
         continue
      subissue = archive.get_issue_data(issue_id)
      assert subissue is not None
      desc = source.get_issue_description(issue_id)
      parsed = parser(desc)
      bisect.insort_left(result, RenderableMention(subissue, None, datetime.datetime.fromisoformat(subissue['fields']['created']), desc, parsed), key=lambda x: x.date)
   for issue_id in rels['environments']:
      if not perms.issue_visible(fields, issue_id):
         continue
      subissue = archive.get_issue_data(issue_id)
      assert subissue is not None
      env = source.get_issue_environment(issue_id)
      parsed = parser(env)
      bisect.insort_left(result, RenderableMention(subissue, None, datetime.datetime.fromisoformat(subissue['fields']['created']), env, parsed), key=lambda x: x.date)
   for issue_id, comment_ids in rels['comments'].items():
      if not perms.issue_visible(fields, issue_id):
         continue
      subissue = archive.get_issue_data(issue_id)
      assert subissue is not None
      for comment_id in comment_ids:
         comment = next(filter(lambda x: x['id'] == comment_id, subissue['fields']['comment']['comments']))
         if not perms.comment_visible(comment):
            continue
         body = source.get_comment_body(issue_id, comment_id)
         parsed = parser(body)
         bisect.insort_left(result, RenderableMention(subissue, comment, datetime.datetime.fromisoformat(comment['created']), body, parsed), key=lambda x: x.date)
   return result

def get_renderable_issue_mentions(archive: mojira.Archive, source: markup.MarkupSource, rels: markup_relations.MarkupRelation, fields: relations.FieldRelations, perms: ViewPerms, keys: relations.KeyLookups, issue_id: str) -> list[RenderableMention]:
   def parser(tag: bs4.BeautifulSoup) -> markup.ParsedMarkup:
      return highlight_issue_mentions(tag, issue_id, keys)
   return get_renderable_mentions(archive, source, rels, fields, perms, parser)

def get_renderable_user_mentions(archive: mojira.Archive, source: markup.MarkupSource, rels: markup_relations.MarkupRelation, fields: relations.FieldRelations, perms: ViewPerms, keys: relations.KeyLookups, user_key: str) -> list[RenderableMention]:
   def parser(tag: bs4.BeautifulSoup) -> markup.ParsedMarkup:
      return highlight_user_mentions(tag, user_key, keys)
   return get_renderable_mentions(archive, source, rels, fields, perms, parser)

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

def get_initial_data(archive: mojira.Archive, metas: mojira.ArchiveMetas, issue: Issue, revisions: list[Revision]) -> InitialData:
   fields = issue['fields']
   final_project = try_project(metas, fields['project'])
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
      for change in reversed(sorted(revision['items'], key=backwards_revision_order_key)):
         match change['field']:
            case 'project' | 'Project':
               assert change['from'] is not None
               result['project'] = change['from']
            case 'Link':
               insert_historic_list_field(result, 'attachments', change, check_both=True)
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
         user_data = archive.get_user_data(val)
         assert user_data is not None
         result['assignee'] = HistoricValue(val, user_data['displayName'])
   if 'reporter' not in result:
      val = fields['reporter']
      if val is None:
         result['reporter'] = None
      else:
         user_data = archive.get_user_data(val)
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
   version_data = project['versions'][version_id]
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

def backwards_revision_order_key(change: RevisionChange) -> int:
   if change['field'] == 'Key':
      return 0
   if change['field'] == 'status':
      return 1
   if change['field'] == 'resolution':
      return 2
   if change['field'] in ('Version', 'Fix Version'):
      return 3 if change['to'] is None else 5
   if change['field'] in ('project', 'Project'):
      return 4
   return 6

def forwards_revision_order_key(change: RevisionChange) -> int:
   if change['field'] == 'Key':
      return 0
   if change['field'] == 'status':
      return 1
   if change['field'] == 'resolution':
      return 2
   if change['field'] in ('Version', 'Fix Version'):
      return 5 if change['to'] is None else 3
   if change['field'] in ('project', 'Project'):
      return 4
   return 6

@dataclasses.dataclass
class MergedRevision:
   user_key: str
   start_time: datetime.datetime
   end_time: datetime.datetime
   changes: list[tuple[str, RevisionChange]]

def merge_revisions(revisions: list[Revision], threshold: datetime.timedelta) -> list[MergedRevision]:
   merged_revisions: list[MergedRevision] = []
   current: MergedRevision | None = None
   for revision in revisions:
      time = datetime.datetime.fromisoformat(revision['created'])
      merged = MergedRevision(
         user_key=revision['author'],
         start_time=time,
         end_time=time,
         changes=[(revision['id'], x) for x in revision['items']]
      )
      if current is None:
         current = merged
      elif revision['author'] == current.user_key and time - current.end_time <= threshold:
         current.end_time = time
         current.changes.extend((revision['id'], x) for x in revision['items'])
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

def try_project(metas: mojira.ArchiveMetas, project_id: str) -> Project | None:
   if project_id in metas.projects:
      return metas.projects[project_id]
   return None

def get_issue(archive: mojira.Archive, issue_id: str) -> Issue:
   issue = archive.get_issue_data(issue_id)
   assert issue is not None
   return issue

def get_user(archive: mojira.Archive, user_key: str) -> User:
   user = archive.get_user_data(user_key)
   assert user is not None
   return user

def sorted_projects(metas: mojira.ArchiveMetas, rels: relations.FieldRelations, perms: ViewPerms) -> list[Project]:
   filtered = perms.filter_projects(metas.projects.values())
   return sorted(filtered, key=lambda x: len(rels.metas['project'][x['id']]), reverse=True)

def sorted_meta_values(metas: mojira.ArchiveMetas, meta_id: mojira.META_TYPE) -> list[ValueDisplay]:
   def order_key(display: ValueDisplay):
      resolved = (meta_id == 'resolution' and display.id is not None) or (meta_id == 'status' and display.id in ('5', '6'))
      return (resolved, display.name)
   value_ids: list[str | None] = [x['id'] for x in metas.metas[meta_id].values()]
   if meta_id == 'resolution':
      value_ids.insert(0, None)
   displays: list[ValueDisplay] = []
   for value_id in value_ids:
      display = meta_display(metas, meta_id, value_id)
      assert display is not None
      bisect.insort_left(displays, display, key=order_key)
   return displays

def sorted_field_values(rels: relations.FieldRelations, perms: ViewPerms, field_id: str) -> list[ValueDisplay]:
   def order_key(display: ValueDisplay):
      relation = rels.fields[field_id]['' if display.id is None else display.id]
      return (-len(relation['issues']), display.name)
   values = rels.fields[field_id].values()
   displays: list[ValueDisplay] = []
   for value in values:
      value_id = value['value'] if isinstance(value['value'], str) else value['value']['id']
      if not perms.field_visible(field_id, value_id):
         continue
      display = field_display(rels, field_id, value_id)
      assert display is not None
      bisect.insort_left(displays, display, key=order_key)
   return displays

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
      'versions': {
         '19204': {
            'id': '19204',
            'name': 'Version #19204',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19304': {
            'id': '19304',
            'name': 'Version #19304',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19500': {
            'id': '19500',
            'name': 'Version #19500',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19526': {
            'id': '19526',
            'name': 'Version #19526',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19536': {
            'id': '19536',
            'name': 'Version #19536',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19553': {
            'id': '19553',
            'name': 'Version #19553',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19604': {
            'id': '19604',
            'name': 'Version #19604',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19622': {
            'id': '19622',
            'name': 'Version #19622',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19637': {
            'id': '19637',
            'name': 'Version #19637',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19647': {
            'id': '19647',
            'name': 'Version #19647',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19650': {
            'id': '19650',
            'name': 'Version #19650',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19710': {
            'id': '19710',
            'name': 'Version #19710',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19718': {
            'id': '19718',
            'name': 'Version #19718',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19820': {
            'id': '19820',
            'name': 'Version #19820',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19821': {
            'id': '19821',
            'name': 'Version #19821',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19834': {
            'id': '19834',
            'name': 'Version #19834',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19902': {
            'id': '19902',
            'name': 'Version #19902',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19903': {
            'id': '19903',
            'name': 'Version #19903',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19904': {
            'id': '19904',
            'name': 'Version #19904',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '19930': {
            'id': '19930',
            'name': 'Version #19930',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20006': {
            'id': '20006',
            'name': 'Version #20006',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20120': {
            'id': '20120',
            'name': 'Version #20120',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20223': {
            'id': '20223',
            'name': 'Version #20223',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20224': {
            'id': '20224',
            'name': 'Version #20224',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20231': {
            'id': '20231',
            'name': 'Version #20231',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20311': {
            'id': '20311',
            'name': 'Version #20311',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20506': {
            'id': '20506',
            'name': 'Version #20506',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20602': {
            'id': '20602',
            'name': 'Version #20602',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20609': {
            'id': '20609',
            'name': 'Version #20609',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20625': {
            'id': '20625',
            'name': 'Version #20625',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20802': {
            'id': '20802',
            'name': 'Version #20802',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20912': {
            'id': '20912',
            'name': 'Version #20912',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '20928': {
            'id': '20928',
            'name': 'Version #20928',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '21204': {
            'id': '21204',
            'name': 'Version #21204',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '21205': {
            'id': '21205',
            'name': 'Version #21205',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '21209': {
            'id': '21209',
            'name': 'Version #21209',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
         '21247': {
            'id': '21247',
            'name': 'Version #21247',
            'projectId': 11901,
            'archived': True,
            'released': True
         },
      }
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
      'versions': {
         '21436': {
            'id': '21436',
            'name': 'Version #21436',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21444': {
            'id': '21444',
            'name': 'Version #21444',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21478': {
            'id': '21478',
            'name': 'Version #21478',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21479': {
            'id': '21479',
            'name': 'Version #21479',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21510': {
            'id': '21510',
            'name': 'Version #21510',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21511': {
            'id': '21511',
            'name': 'Version #21511',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21552': {
            'id': '21552',
            'name': 'Version #21552',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21553': {
            'id': '21553',
            'name': 'Version #21553',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21605': {
            'id': '21605',
            'name': 'Version #21605',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21606': {
            'id': '21606',
            'name': 'Version #21606',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21623': {
            'id': '21623',
            'name': 'Version #21623',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21807': {
            'id': '21807',
            'name': 'Version #21807',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
         '21829': {
            'id': '21829',
            'name': 'Version #21829',
            'projectId': 12200,
            'archived': True,
            'released': True
         },
      }
   }
