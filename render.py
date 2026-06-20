import dataclasses
import json
import typing
import fieldinfo
from jiratypes import Attachment, Comment, Issue, IssueLink, NewAuthor, NewComment, Project, Revision, RevisionChange, Version
import mojira
import relations
import pathlib
import datetime
import urllib.parse
import markup
import bs4
import re
import bisect
import copy
from web import HtmlFile, append_desc_item, append_row, html_diff, html_to_text, inline_list, make_desc_list, make_file, make_table, new_content_tag, relative_link, relative_path, render_date, render_date_range, render_datetime, render_time, same_day, write_html

@dataclasses.dataclass
class FieldPage:
   page: HtmlFile
   values_folder: pathlib.PurePath

   def get_value_path(self, value_name: str) -> pathlib.PurePath:
      return self.values_folder / (urllib.parse.quote_plus(value_name) + '.html')

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   project_list: HtmlFile
   project_folder: pathlib.PurePath
   issues_folder: pathlib.PurePath
   users_folder: pathlib.PurePath
   field_pages: dict[str, FieldPage]
   archive: mojira.Archive
   metas: mojira.ArchiveMetas
   field_info: fieldinfo.FieldsInfo
   relations: relations.RelationsBundle
   markup_source: markup.MarkupSource
   secret_comments: mojira.SecretComments

def make_jira_file(root: pathlib.Path, path: pathlib.PurePath, title: str) -> HtmlFile:
   file = make_file(path, title)
   file.page.head.append(file.page.soup.new_tag('link', rel='icon', type='image/x-icon', href=relative_link(root, file.path, pathlib.PurePath('data/assets/favicon.ico'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/misode-reset.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/misode-style.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('data/assets/mojira.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/style.css'))))
   file.page.head.append(file.page.soup.new_tag('script', src=relative_link(root, file.path, pathlib.PurePath('web/script.js'))))
   return file

def save_file(website: Website, file: HtmlFile):
   write_html(website.root / file.path, file.page)

def main():
   print('Loading...')
   root = pathlib.Path('/d/Archives/Mojira')
   archive = mojira.Archive(folder=root / 'data')
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   rels = relations.RelationsBundle(
      keys=relations.KeyLookups(),
      user=relations.UserRelations(),
      fields=relations.FieldRelations()
   )
   rels.load(root / 'relations')
   with open(root / 'extra_field_info.json', 'r', encoding='utf-8') as file:
      extra_info: fieldinfo.ExtraFieldInfo = json.load(file)
   fields = fieldinfo.FieldsInfo(metas.fields, extra_info)
   markup_source = markup.MarkupSource(root / 'markup')
   secret_comments = mojira.SecretComments(root / 'secret_comments.json')
   website = Website(
      root=root,
      project_list=make_jira_file(root, pathlib.PurePath('web/index.html'), 'Mojira Archive'),
      project_folder=pathlib.PurePath('web/projects'),
      issues_folder=pathlib.PurePath('web/issues'),
      users_folder=pathlib.PurePath('web/users'),
      field_pages={},
      archive=archive,
      metas=metas,
      relations=rels,
      field_info=fields,
      markup_source=markup_source,
      secret_comments=secret_comments
   )
   for key in [*rels.fields.fields.keys(), *rels.fields.metas.keys()]:
      field_name = fields.field_map[key].name
      id_name = urllib.parse.quote_plus(field_name)
      website.field_pages[key] = FieldPage(
         make_jira_file(root, pathlib.PurePath('web/fields') / (id_name + '.html'), field_name),
         pathlib.PurePath('web/fields') / id_name
      )
   print('Rendering...')

   for test in ['MC-4', 'MC-1691', 'MCPE-33270', 'MC-151343', 'MC-93468', 'WEB-1234', 'TRASH-59584', 'MC-162518', 'MCPE-108785', 'MC-272351', 'MCL-12040', 'MCL-24276', 'TRASH-35765']:
      file = create_issue_page(website, archive.get_issue_data(rels.keys.issue_keys[test]))
      save_file(website, file)
   return

   make_project_list(website, website.project_list)
   save_file(website, website.project_list)
   for project_id, project in metas.projects.items():
      project_key = project['key']
      print(project_key)
      home = create_project_home_page(website, project)
      save_file(website, home)
      versions = create_project_versions_page(website, project)
      save_file(website, versions)
      for version in project['versions'].values():
         print(version['name'])
         page = create_version_page(website, project, version)
         save_file(website, page)
      issues = create_project_issues_page(website, project)
      save_file(website, issues)
   for project_id, project in metas.projects.items():
      project_key = project['key']
      print(project_key)
      issues = rels.projects[project_id]
      for i, issue_id in enumerate(issues):
         if len(issues) >= 1000 and (i % 1000 == 0 or i == len(issues) - 1):
            print(f'{i + 1} / {len(issues)}')
         issue = archive.get_issue_data(issue_id)
         assert issue is not None
         file = create_issue_page(website, issue)
         save_file(website, file)

def fix_markup(website: Website, file: HtmlFile, html: bs4.BeautifulSoup):
   # jira emits issue-link class, but misode uses that for linked issues
   # so we have to change it to inline-issue-link
   for tag in html.find_all(class_='issue-link'):
      tag.attrs['class'] = 'inline-issue-link'
   # our markup is generated with '.' as the site root, but otherwise normal jira paths
   # we detect and correct these to point to our own resources
   for tag in html.find_all(name='a', attrs={'href': True}):
      current_link = tag['href']
      if isinstance(current_link, str) and current_link.startswith('./'):
         tag['href'] = fix_markup_link(website, file, current_link)
   for tag in html.find_all(name='img', attrs={'src': True}):
      current_link = tag['src']
      if isinstance(current_link, str) and current_link.startswith('./'):
         tag['src'] = fix_markup_link(website, file, current_link)

BROWSE_RE = re.compile(r'^./browse/([A-Z]+-[0-9]+)$')
ATTACH_RE = re.compile(r'^./secure/attachment/([0-9]+)/(.+)$')
THUMBNAIL_RE = re.compile(r'^./secure/thumbnail/([0-9]+)/(.+)$')
ICON_RE = re.compile(r'^./images/(.+)$')
USER_RE = re.compile(r'^./secure/ViewProfile\.jspa\?name=(.+)$')
UNKNOWN_COMMENT_RE = re.compile(r'A comment with security level \'[a-z]+\' was removed\.' + '\u00a0?$')

def fix_markup_link(website: Website, file: HtmlFile, link: str) -> str:
   if (match := BROWSE_RE.match(link)) is not None:
      key = match.group(1)
      return relative_link(website.root, file.path, website.issues_folder / (key + '.html'))
   if (match := ATTACH_RE.match(link)) is not None or (match := THUMBNAIL_RE.match(link)) is not None:
      attach_id, attach_name = match.group(1, 2)
      path = relative_path(website.root, file.path, website.archive.get_attachment_content_path(attach_id, attach_name))
      return urllib.parse.quote(str(path))
   if (match := ICON_RE.match(link)) is not None:
      icon_path = match.group(1)
      path = relative_path(website.root, file.path, website.archive.folder / 'assets/images' / icon_path)
      return urllib.parse.quote(str(path))
   if (match := USER_RE.match(link)) is not None:
      username = urllib.parse.unquote_plus(match.group(1))
      normalized = username.casefold()
      user_key = website.relations.keys.user_keys.get(normalized, normalized)
      return relative_link(website.root, file.path, website.users_folder / (urllib.parse.quote_plus(user_key) + '.html'))
   raise ValueError()

def make_project_list(website: Website, file: HtmlFile):
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   content.append(new_content_tag(soup, 'div', [
      new_content_tag(soup, 'h1', 'Mojira Archive')
   ], attrs={'class': 'title'}))
   table = render_projects_table(website, file, website.metas.projects.values())
   content.append(table)
   file.page.body.append(content)

def render_project_title(soup: bs4.BeautifulSoup, website: Website, file: HtmlFile, project: Project):
   return new_content_tag(soup, 'div', [
      new_content_tag(soup, 'h1', [
         new_content_tag(soup, 'a', 'Mojira', attrs={'href': relative_link(website.root, file.path, website.project_list.path)}),
         ' / ',
         project_link(website, file, project)
      ])
   ], attrs={'class': 'title'})

def create_project_home_page(website: Website, project: Project) -> HtmlFile:
   key = project['key']
   project_name = project['name']
   full_title = f'[{key}] {project_name}'
   file = make_jira_file(website.root, website.project_folder / key / 'index.html', full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   content.append(render_project_title(soup, website, file, project))
   issues = website.relations.fields.fields['project'][project['id']]['issues']
   versions = project['versions']
   fields = make_desc_list(soup)
   append_desc_item(soup, fields, 'Name', project_name)
   append_desc_item(soup, fields, 'Project Lead', user_link(website, file, project['lead']))
   append_desc_item(soup, fields, 'Issues', new_content_tag(soup, 'a', str(len(issues)), attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'issues.html')}))
   append_desc_item(soup, fields, 'Versions', new_content_tag(soup, 'a', str(len(versions)), attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'versions.html')}))
   append_desc_item(soup, fields, 'External Link', new_content_tag(soup, 'a', key, attrs={'href': f'https://bugs.mojang.com/projects/{key}/summary'}))
   content.append(fields)
   if len(project['description']) > 0:
      desc = bs4.BeautifulSoup(project['description'], 'html.parser')
      desc = new_content_tag(soup, 'div', desc, attrs={'class': 'project-desc'})
      content.append(desc)
   file.page.body.append(content)
   return file

def create_project_versions_page(website: Website, project: Project) -> HtmlFile:
   key = project['key']
   project_name = project['name']
   full_title = f'[{key}] {project_name}'
   file = make_jira_file(website.root, website.project_folder / key / 'versions.html', full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   content.append(render_project_title(soup, website, file, project))
   table = render_versions_table(website, file, project, project['versions'].values())
   content.append(table)
   file.page.body.append(content)
   return file

def create_project_issues_page(website: Website, project: Project) -> HtmlFile:
   key = project['key']
   project_name = project['name']
   full_title = f'[{key}] {project_name}'
   file = make_jira_file(website.root, website.project_folder / key / 'issues.html', full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   content.append(render_project_title(soup, website, file, project))
   table = render_issues_table(website, file, website.relations.fields.fields['project'][project['id']]['issues'])
   content.append(table)
   file.page.body.append(content)
   return file

def create_version_page(website: Website, project: Project, version: Version) -> HtmlFile:
   full_title = f'[{project['key']}] {version['name']}'
   affected_issues = website.relations.fields.metas['versions'][version['id']]
   fixed_issues = website.relations.fields.metas['fixVersions'][version['id']]
   file = make_jira_file(website.root, website.project_folder / project['key'] / 'versions' / (urllib.parse.quote_plus(version['name']) + '.html'), full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   header = new_content_tag(soup, 'h1', [
      new_content_tag(soup, 'a', 'Mojira', attrs={'href': relative_link(website.root, file.path, website.project_list.path)}),
      ' / ',
      project_link(website, file, project),
      ' / ',
      version_link(website, file, project, version)
   ])
   content.append(header)
   fields = make_desc_list(soup)
   if 'description' in version:
      append_desc_item(soup, fields, 'Description', version['description'])
   if 'releaseDate' in version:
      append_desc_item(soup, fields, 'Date', render_date(soup, datetime.datetime.fromisoformat(version['releaseDate'])))
   append_desc_item(soup, fields, 'Status', 'Archived' if version['archived'] else ('Active' if version['released'] else 'Unreleased'))
   append_desc_item(soup, fields, 'Affected Issues', str(len(affected_issues)))
   append_desc_item(soup, fields, 'Fixed Issues', str(len(fixed_issues)))
   content.append(fields)
   affected_table = render_issues_table(website, file, affected_issues)
   content.append('Affected:')
   content.append(affected_table)
   fixes_table = render_issues_table(website, file, fixed_issues)
   content.append('Fixes:')
   content.append(fixes_table)
   file.page.body.append(content)
   return file

def render_projects_table(website: Website, file: HtmlFile, projects: typing.Iterable[Project]) -> bs4.Tag:
   table = make_table(file.page.soup, ['Project', 'Name', 'Issues', 'Versions'])
   table.attrs['class'] = 'projects-table sortable'
   for project in projects:
      issues = website.relations.fields.fields['project'][project['id']]['issues']
      versions = project['versions']
      project_key = project_link(website, file, project)
      append_row(file.page.soup, table, [
         project_key,
         project['name'],
         new_content_tag(file.page.soup, 'a', str(len(issues)), attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'issues.html')}),
         new_content_tag(file.page.soup, 'a', str(len(versions)), attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'versions.html')}),
      ])
   return table

def render_versions_table(website: Website, file: HtmlFile, project: Project, versions: typing.Iterable[Version]) -> bs4.Tag:
   table = make_table(file.page.soup, ['Name', 'Description', 'Date', 'Affected Issues', 'Fixed Issues'])
   table.attrs['class'] = 'versions-table sortable'
   for version in versions:
      affected_issues = website.relations.fields.metas['versions'][version['id']]
      fixed_issues = website.relations.fields.metas['fixVersions'][version['id']]
      append_row(file.page.soup, table, [
         version_link(website, file, project, version),
         version['description'] if 'description' in version else '',
         render_date(file.page.soup, datetime.datetime.fromisoformat(version['releaseDate'])) if 'releaseDate' in version else '',
         str(len(affected_issues)),
         str(len(fixed_issues)),
      ])
   return table

def render_issues_table(website: Website, file: HtmlFile, issues: list[str]) -> bs4.Tag:
   table = make_table(file.page.soup, ['Issue', 'Summary', 'Reporter', 'Created'])
   table.attrs['class'] = 'issues-table sortable'
   for i, issue_key in enumerate(issues):
      if len(issues) >= 1000 and (i % 1000 == 0 or i == len(issues) - 1):
         print(f'{i + 1} / {len(issues)}')
      issue = website.archive.get_issue_data(issue_key)
      assert issue is not None
      reporter = user_link(website, file, issue['fields']['reporter'])
      date = render_datetime(file.page.soup, datetime.datetime.fromisoformat(issue['fields']['created']))
      link = new_content_tag(file.page.soup, 'a', issue['key'], attrs={'href': relative_link(website.root, file.path, website.issues_folder / (issue['key'] + '.html'))})
      append_row(file.page.soup, table, [link, issue['fields']['summary'], reporter, date])
   return table

def make_generic_header(website: Website, file: HtmlFile) -> bs4.Tag:
   header = new_content_tag(file.page.soup, 'header', [
      new_content_tag(file.page.soup, 'a', 'Mojira Archive', attrs={'class': 'header-main', 'href': relative_link(website.root, file.path, website.project_list.path)})
   ])
   return header

def make_generic_footer(website: Website, file: HtmlFile) -> bs4.Tag:
   footer = new_content_tag(file.page.soup, 'footer', [
      new_content_tag(file.page.soup, 'p', [
         'Pre-migration archive of ',
         new_content_tag(file.page.soup, 'a', attrs={'href': 'https://bugs.mojang.com'}, content='bugs.mojang.com'),
         ' by ',
         new_content_tag(file.page.soup, 'a', attrs={'href': 'https://github.com/tryashtar'}, content='tryashtar'),
         '. For Mojira volunteer use only!'
      ])
   ])
   return footer

def bug_icon(website: Website, file: HtmlFile) -> bs4.Tag:
   return file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/issuetypes/bug.svg'))})

def create_issue_page(website: Website, issue: Issue) -> HtmlFile:
   key = issue['key']
   fields = issue['fields']
   summary = fields['summary']
   full_title = f'[{key}] {summary}'

   file = make_jira_file(website.root, website.issues_folder / (key + '.html'), full_title)
   soup = file.page.soup
   file.page.head.append(soup.new_tag('meta', attrs={'name': 'title', 'content': full_title}))
   file.page.head.append(soup.new_tag('meta', attrs={'property': 'og:title', 'content': full_title}))
   file.page.head.append(soup.new_tag('meta', attrs={'property': 'twitter:title', 'content': full_title}))

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   issue_div = render_issue_content(website, file, issue, full=True)
   issue_div.attrs['id'] = 'issue'
   content.append(issue_div)

   tabbed_content = soup.new_tag('div', attrs={'class': 'issue-tabs-content'})
   all_comments: list[RenderableComment] = []
   if len(issue['fields']['comment']['comments']) > 0:
      for comment in issue['fields']['comment']['comments']:
         body = website.markup_source.get_comment_body(issue['id'], comment['id'])
         fix_markup(website, file, body)
         all_comments.append(RenderableComment(comment, body, secret=False))
      for comment in website.secret_comments.get(issue['id']):
         body = website.markup_source.get_secret_comment_body(issue['id'], comment['id'])
         fix_markup(website, file, body)
         bisect.insort_left(all_comments, RenderableComment(comment, body, secret=True), key=lambda x: datetime.datetime.fromisoformat(x.comment['created']))
      comment_section = render_issue_comments(website, file, all_comments)
      tabbed_content.append(new_content_tag(soup, 'div', attrs={'id': 'issue-tab-content-comments', 'class': 'issue-tab-content'}, content=comment_section))
   history_section = render_issue_revisions(website, file, issue, issue['changelog']['histories'])
   tabbed_content.append(new_content_tag(soup, 'div', attrs={'id': 'issue-tab-content-history', 'class': 'issue-tab-content'}, content=history_section))
   issue_div.append(
      new_content_tag(soup, 'div', attrs={'class': 'issue-tabs'}, content=[
         soup.new_tag('input', attrs={'type': 'radio', 'name': 'issue-tabs', 'id': 'issue-tab-comments', 'checked': ''}),
         new_content_tag(soup, 'label', attrs={'for': 'issue-tab-comments'}, content=[
            'Comments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(all_comments)))
         ]),
         soup.new_tag('input', attrs={'type': 'radio', 'name': 'issue-tabs', 'id': 'issue-tab-history'}),
         new_content_tag(soup, 'label', attrs={'for': 'issue-tab-history'}, content=[
            'History',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issue['changelog']['histories'])))
         ]),
         tabbed_content
      ])
   )
   return file

def render_issue_content(website: Website, file: HtmlFile, issue: Issue, full: bool) -> bs4.Tag:
   soup = file.page.soup
   issue_div = soup.new_tag('div', attrs={'class': 'issue'})
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-top'}, content=[
      new_content_tag(soup, 'div', attrs={'class': 'issue-title'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'issue-key', 'data-copy': issue['key']}, content=[
            bug_icon(website, file),
            new_content_tag(soup, 'span', issue['key'])
         ]),
         new_content_tag(soup, 'h1', attrs={'class': 'issue-summary'}, content=issue['fields']['summary'])
      ])
   ]))
   issue_body = render_issue_body(website, file, issue)
   issue_details = render_issue_details(website, file, issue, full=full)
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-split'}, content=[
      issue_body,
      issue_details
   ]))
   if full:
      link_section = render_issue_links(website, file, issue['fields']['issuelinks'])
      if link_section is not None:
         issue_body.append(link_section)
      if len(issue['fields']['attachment']) > 0:
         attach_section = render_issue_attachments(website, file, issue['fields']['attachment'])
         issue_body.append(attach_section)
   return issue_div

def render_issue_body(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   soup = file.page.soup
   fields = issue['fields']
   issue_body = soup.new_tag('main', attrs={'class': 'issue-body'})
   if fields['description'] is not None:
      desc = website.markup_source.get_issue_description(issue['id'])
      fix_markup(website, file, desc)
      desc_text = html_to_text(desc)
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-description'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=desc)
      ]))
      file.page.head.append(soup.new_tag('meta', attrs={'name': 'description', 'content': desc_text}))
      file.page.head.append(soup.new_tag('meta', attrs={'property': 'og:description', 'content': desc_text}))
      file.page.head.append(soup.new_tag('meta', attrs={'property': 'twitter:description', 'content': desc_text}))
   if 'environment' in fields and fields['environment'] is not None:
      env = website.markup_source.get_issue_environment(issue['id'])
      fix_markup(website, file, env)
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-environment-section issue-body'}, content=[
         new_content_tag(soup, 'h2', 'Environment'),
         new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=env)
      ]))
   if 'customfield_11801' in fields and fields['customfield_11801'] is not None:
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-impact-section issue-body'}, content=[
         new_content_tag(soup, 'h2', 'Impact'),
         new_content_tag(soup, 'p', content=fields['customfield_11801'])
      ]))
   return issue_body

class TrackedMultiSetRevision:
   def __init__(self, name: str, creator: typing.Callable[[list[tuple[str, str]]], bs4.Tag], inline: bool):
      self.added: list[tuple[str, str]] = []
      self.removed: list[tuple[str, str]] = []
      self.name = name
      self.creator = creator
      self.inline = inline

   def import_change(self, entry: RevisionChange):
      if entry['to'] is not None:
         assert entry['toString'] is not None
         self.added.append((entry['to'], entry['toString']))
      if entry['from'] is not None:
         assert entry['fromString'] is not None
         self.removed.append((entry['from'], entry['fromString']))

   def handle(self, soup: bs4.BeautifulSoup) -> typing.Generator[bs4.Tag]:
      if len(self.added) > 0:
         label = new_content_tag(soup, 'span', f'Added {self.name}: ', attrs={'class': 'history-label'})
         contents = self.creator(self.added)
         if self.inline:
            yield new_content_tag(soup, 'p', [label, contents])
         else:
            yield new_content_tag(soup, 'p', label)
            yield contents
      if len(self.removed) > 0:
         label = new_content_tag(soup, 'span', f'Removed {self.name}: ', attrs={'class': 'history-label'})
         contents = self.creator(self.removed)
         if self.inline:
            yield new_content_tag(soup, 'p', [label, contents])
         else:
            yield new_content_tag(soup, 'p', label)
            yield contents

class TrackedMultiValueRevision:
   def __init__(self, name: str, splitter: typing.Callable[[str | None, str | None], list[tuple[str, str]]], creator: typing.Callable[[list[tuple[str, str]]], bs4.Tag]):
      self.previous: list[tuple[str, str]] | None = None
      self.name = name
      self.splitter = splitter
      self.creator = creator

   def handle(self, soup: bs4.BeautifulSoup, revision: RevisionChange) -> typing.Generator[bs4.Tag]:
      if self.previous is None:
         self.previous = self.splitter(revision['from'], revision['fromString'])
      new_values = self.splitter(revision['to'], revision['toString'])
      added_values = [x for x in new_values if x not in self.previous]
      removed_values = [x for x in self.previous if x not in new_values]
      if len(added_values) > 0:
         yield new_content_tag(soup, 'p', [
            new_content_tag(soup, 'span', f'Added {self.name}: ', attrs={'class': 'history-label'}),
            self.creator(added_values)
         ])
      if len(removed_values) > 0:
         yield new_content_tag(soup, 'p', [
            new_content_tag(soup, 'span', f'Removed {self.name}: ', attrs={'class': 'history-label'}),
            self.creator(removed_values)
         ])
      self.previous = new_values

def revision_from_to(soup: bs4.BeautifulSoup, label: str, old_tag: bs4.Tag, new_tag: bs4.Tag) -> bs4.Tag:
   return new_content_tag(soup, 'p', [
      new_content_tag(soup, 'span', f'Changed {label}: ', attrs={'class': 'history-label'}),
      old_tag,
      new_content_tag(soup, 'span', ' → ', attrs={'class': 'history-label'}),
      new_tag
   ])

def revision_change(soup: bs4.BeautifulSoup, label: str, old_tag: bs4.Tag | None, new_tag: bs4.Tag | None) -> typing.Generator[bs4.Tag]:
   if old_tag is not None and new_tag is not None:
      yield revision_from_to(soup, label, old_tag, new_tag)
   elif new_tag is None and old_tag is not None:
      yield new_content_tag(soup, 'p', [
         new_content_tag(soup, 'span', f'Removed {label}: ', attrs={'class': 'history-label'}),
         old_tag
      ])
   elif old_tag is None and new_tag is not None:
      yield new_content_tag(soup, 'p', [
         new_content_tag(soup, 'span', f'Added {label}: ', attrs={'class': 'history-label'}),
         new_tag
      ])

def revision_html_diff(soup: bs4.BeautifulSoup, label: str, before: bs4.Tag | None, after: bs4.Tag | None, panel_class: str) -> typing.Generator[bs4.Tag]:
   if before is not None and after is not None:
      diff = html_diff(soup, before, after)
      has_insertions = diff.find('diff:insert') is not None or diff.find(attrs={'diff:insert': True})
      has_deletions = diff.find('diff:delete') is not None or diff.find(attrs={'diff:delete': True})
      if has_insertions and has_deletions:
         before_diff = copy.deepcopy(diff)
         after_diff = copy.deepcopy(diff)
         for tag in before_diff.find_all('diff:insert'):
            tag.extract()
         for tag in before_diff.find_all(attrs={'diff:insert': True}):
            tag.extract()
         for tag in after_diff.find_all('diff:delete'):
            tag.extract()
         for tag in after_diff.find_all(attrs={'diff:delete': True}):
            tag.extract()
         yield new_content_tag(soup, 'p', f'Changed {label}: ', attrs={'class': 'history-label'})
         yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
               new_content_tag(soup, 'div', attrs={'class': panel_class}, content=[before_diff, after_diff])
            ])
      elif has_insertions:
         yield new_content_tag(soup, 'p', f'Changed {label}: ', attrs={'class': 'history-label'})
         yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=diff)
      elif has_deletions:
         yield new_content_tag(soup, 'p', f'Changed {label}: ', attrs={'class': 'history-label'})
         yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=diff)
   elif before is not None and after is None:
      yield new_content_tag(soup, 'p', f'Removed {label}: ', attrs={'class': 'history-label'})
      yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=before)
   elif after is not None and before is None:
      yield new_content_tag(soup, 'p', f'Added {label}: ', attrs={'class': 'history-label'})
      yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=after)

@dataclasses.dataclass
class MergedRevision:
   user_key: str
   start_time: datetime.datetime
   end_time: datetime.datetime
   changes: list[tuple[str, RevisionChange]]

def merge_revisions(revisions: list[Revision]) -> list[MergedRevision]:
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
      elif revision['author'] == current.user_key and time - current.end_time <= datetime.timedelta(minutes=10):
         current.end_time = time
         current.changes.extend((revision['id'], x) for x in revision['items'])
      else:
         merged_revisions.append(current)
         current = merged
   if current is not None:
      merged_revisions.append(current)
   return merged_revisions

def render_issue_revisions(website: Website, file: HtmlFile, issue: Issue, revisions: list[Revision]) -> bs4.Tag:
   soup = file.page.soup
   project = website.metas.projects[issue['fields']['project']]

   # revisions can include references to versions, attachments, issues, or fields that no longer exist
   # we still display them, just without full data or links
   def render_version(version_id: str, version_name: str) -> bs4.Tag:
      if version_id in project['versions']:
         return version_link(website, file, project, project['versions'][version_id])
      return new_content_tag(file.page.soup, 'span', version_name, attrs={'class': 'status-badge'})

   def render_version_list(versions: list[tuple[str, str]]) -> bs4.Tag:
      return inline_list(file.page.soup, map(lambda x: render_version(x[0], x[1]), versions))

   def render_attach(attach_id: str, filename: str) -> bs4.Tag:
      attachment = website.archive.get_attachment_data(attach_id)
      if attachment is not None:
         return render_attachment(website, file, attachment, include_upload=False)
      broken = soup.new_tag('img', attrs={'width': '32', 'height': '32', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/attach/noimage.svg'))})
      return new_content_tag(soup, 'div', attrs={'class': 'broken-attachment'}, content=[broken, filename])

   def render_attach_list(attaches: list[tuple[str, str]]) -> bs4.Tag:
      return new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'attachments'}, content=list(
            map(lambda x: render_attach(x[0], x[1]), attaches)
         ))
      ])

   def render_link(ticket: str) -> bs4.Tag:
      if ticket in website.relations.keys.issue_keys:
         relevant_issue = website.archive.get_issue_data(website.relations.keys.issue_keys[ticket])
         assert relevant_issue is not None
         # wrap in a div so Misode's CSS includes the top border
         return new_content_tag(soup, 'div', big_issue_link(website, file, relevant_issue))
      else:
         return new_content_tag(soup, 'div', issue_key(website, file, ticket))

   def render_link_list(links: list[tuple[str, str]]) -> bs4.Tag:
      link_dict: dict[str, list[bs4.Tag]] = {}
      for ticket, full in links:
         link_dir = full[len('This issue '):-(len(ticket) + 1)]
         if link_dir not in link_dict:
            link_dict[link_dir] = []
         link_dict[link_dir].append(render_link(ticket))
      result = soup.new_tag('blockquote', attrs={'class': 'history-quote'})
      for dir, tags in link_dict.items():
         result.append(new_content_tag(soup, 'p', dir))
         result.extend(tags)
      return result

   def render_field(field_id: str, value: fieldinfo.NameValue) -> bs4.Tag:
      if value['id'] in website.relations.fields.fields[field_id]:
         value_def = website.relations.fields.fields[field_id][value['id']]['value']
         return field_link(website, file, field_id, value_def)
      else:
         return new_content_tag(file.page.soup, 'span', value_name, attrs={'class': 'status-badge'})

   def render_field_list(field_id: str, values: list[tuple[str, str]]) -> bs4.Tag:
      return inline_list(file.page.soup, map(lambda x: render_field(field_id, x[0], x[1]), values))

   def label_splitter(source: str | None, string: str | None) -> list[tuple[str, str]]:
      assert source is None
      assert string is not None
      if string == '':
         return []
      return [(x, x) for x in string.split(' ')]

   def category_splitter(source: str | None, string: str | None) -> list[tuple[str, str]]:
      if source is None or string is None or source == '' or string == '':
         return []
      source = source.removeprefix('[').removesuffix(']')
      source_list = source.split(', ')
      string_list = string.split(',')
      assert len(source_list) == len(string_list)
      return list(zip(source_list, string_list))

   def handle_field(revision: RevisionChange, label: str, field_id: str) -> typing.Iterator[bs4.Tag]:
      if revision['from'] is not None:
         assert revision['fromString'] is not None
         old_tag = render_field(field_id, revision['from'], revision['fromString'])
      else:
         old_tag = None
      if revision['to'] is not None:
         assert revision['toString'] is not None
         new_tag = render_field(field_id, revision['to'], revision['toString'])
      else:
         new_tag = None
      return revision_change(soup, label, old_tag, new_tag)

   def handle_text(revision: RevisionChange, label: str) -> typing.Iterator[bs4.Tag]:
      assert revision['from'] is None
      assert revision['to'] is None
      old_val = revision['fromString']
      new_val = revision['toString']
      if old_val == '':
         old_val = None
      if new_val == '':
         new_val = None
      old_tag = None if old_val is None else new_content_tag(soup, 'span', old_val)
      new_tag = None if new_val is None else new_content_tag(soup, 'span', new_val)
      return revision_change(soup, label, old_tag, new_tag)

   def handle_large_diff(before: bs4.BeautifulSoup | None, after: bs4.BeautifulSoup | None, label: str) -> typing.Iterator[bs4.Tag]:
      if before is not None:
         fix_markup(website, file, before)
         before_tag = new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=before)
      else:
         before_tag = None
      if after is not None:
         fix_markup(website, file, after)
         after_tag = new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=after)
      else:
         after_tag = None
      return revision_html_diff(soup, label, before_tag, after_tag, 'diff-panel-side')

   revisions_list: list[bs4.Tag] = []
   date_tag = render_datetime(soup, datetime.datetime.fromisoformat(issue['fields']['created']))
   date_tag.attrs['class'] = 'comment-time'
   revisions_list.append(new_content_tag(soup, 'div', attrs={'class': 'history-entry'}, content=[
      new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=[
         comment_author(website, file, issue['fields']['creator']),
         ' ',
         date_tag
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=[
         new_content_tag(soup, 'p', 'Created issue:', attrs={'class': 'history-label'}),
         new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
            render_issue_content(website, file, issue, full=False)
         ])
      ])
   ]))
   labels = TrackedMultiValueRevision('labels', label_splitter, lambda x: render_field_list('labels', x))
   categories = TrackedMultiValueRevision('Category', category_splitter, lambda x: render_field_list('customfield_11901', x))
   merged = merge_revisions(revisions)
   for entry in merged:
      continue
      history_items: list[bs4.Tag] = []
      affected_versions = TrackedMultiSetRevision('affects versions', render_version_list, inline=True)
      fixed_versions = TrackedMultiSetRevision('fixed versions', render_version_list, inline=True)
      attachments = TrackedMultiSetRevision('attachments', render_attach_list, inline=False)
      links = TrackedMultiSetRevision('links', render_link_list, inline=False)
      components = TrackedMultiSetRevision('component', lambda x: render_field_list('component', x), inline=False)
      for rev_id, item in entry.changes:
         new_tags: typing.Iterator[bs4.Tag] | None = None
         match item['field']:
            # tracked changes
            case 'labels': # source always null, string always 'id id'
               new_tags = labels.handle(soup, item)
            case 'Category': # source/string are either null or '[id, id]'/'Name,Name'
               new_tags = categories.handle(soup, item)
            # special batched changes
            case 'Link': # source/string are either null or 'key'/'This issue ...'
               links.import_change(item)
            case 'Attachment': # source/string are either null or 'id'/'filename'
               attachments.import_change(item)
            # other batched changes
            # source/string are either null or 'id'/'Name'
            case 'Component':
               components.import_change(item)
            case 'Version':
               affected_versions.import_change(item)
            case 'Fix Version':
               fixed_versions.import_change(item)
            # custom enum field changes
            # source/string are either null/null, null/empty, or 'id'/'Name'
            case 'Confirmation Status':
               new_tags = handle_field(item, 'Confirmation Status', 'customfield_10500')
            case 'Area':
               new_tags = handle_field(item, 'Area', 'customfield_12800')
            case 'Game Mode':
               new_tags = handle_field(item, 'Game Mode', 'customfield_10501')
            case 'Platform' | 'Device': # field was renamed at some point, but old name persists in history
               new_tags = handle_field(item, 'Platform', 'customfield_10402')
            case 'Realms Platform':
               new_tags = handle_field(item, 'Platform', 'customfield_12301')
            case 'Dungeons Platform':
               new_tags = handle_field(item, 'Platform', 'customfield_12400')
            case 'Legends Platform':
               new_tags = handle_field(item, 'Platform', 'customfield_12900')
            case 'Mojang Priority':
               new_tags = handle_field(item, 'Mojang Priority', 'customfield_12200')
            # builtin enum field changes
            # source/string are either null or 'id'/'Name'
            case 'priority':
               new_tags = handle_field(item, 'Priority', 'priority')
            case 'security':
               new_tags = handle_field(item, 'Security Level', 'security')
            case 'resolution':
               fake_item: RevisionChange = {
                  'field': 'resolution',
                  'from': '0' if item['from'] is None else item['from'],
                  'fromString': 'Unresolved' if item['fromString'] is None else item['fromString'],
                  'to': '0' if item['to'] is None else item['to'],
                  'toString': 'Unresolved' if item['toString'] is None else item['toString'],
               }
               new_tags = handle_field(fake_item, 'Resolution', 'resolution')
            # text field changes
            # source always null, string either null or empty or text
            case 'ADO' | 'VSO': # field was renamed at some point, but old name persists in history
               new_tags = handle_text(item, 'ADO')
            case 'Regression Builds':
               new_tags = handle_text(item, 'Regression Builds')
            case 'Partner Team Reporting':
               new_tags = handle_text(item, 'Partner Team')
            case 'Operating System Version':
               new_tags = handle_text(item, 'OS Version')
            # other simple changes
            case 'Triaged Time': # source/string are either null or 'date'/'Display'
               old_tag = None if item['from'] is None else render_date(soup, datetime.datetime.fromisoformat(item['from']))
               new_tag = None if item['to'] is None else render_date(soup, datetime.datetime.fromisoformat(item['to']))
               new_tags = revision_change(soup, 'Triaged Time', old_tag, new_tag)
            case 'assignee': # source/string are either null or 'key'/'Name'
               old_tag = None if item['from'] is None else user_link(website, file, item['from'])
               new_tag = None if item['to'] is None else user_link(website, file, item['to'])
               new_tags = revision_change(soup, 'Assignee', old_tag, new_tag)
            case 'reporter': # source/string are always 'key'/'Name'
               assert item['from'] is not None
               assert item['to'] is not None
               old_tag = user_link(website, file, item['from'])
               new_tag = user_link(website, file, item['to'])
               new_tags = revision_change(soup, 'Assignee', old_tag, new_tag)
            case 'Key': # source always null, string always 'key'
               assert item['fromString'] is not None
               assert item['toString'] is not None
               old_tag = issue_key(website, file, item['fromString'])
               new_tag = issue_key(website, file, item['toString'])
               new_tags = revision_change(soup, 'Key', old_tag, new_tag)
            # html or markup changes
            case 'summary': # source always null, string always text
               assert item['fromString'] is not None
               assert item['toString'] is not None
               before = new_content_tag(soup, 'span', item['fromString'])
               after = new_content_tag(soup, 'span', item['toString'])
               new_tags = revision_html_diff(soup, 'summary', before, after, 'diff-panel-top')
            case 'description': # source always null, string either null or text
               before, after = website.markup_source.get_issue_description_revision(issue['id'], rev_id)
               new_tags = handle_large_diff(before, after, 'description')
            case 'environment': # source always null, string either null or text
               before, after = website.markup_source.get_issue_environment_revision(issue['id'], rev_id)
               new_tags = handle_large_diff(before, after, 'environment')
            case 'Comment': # from always text, all the rest always null
               assert item['from'] is not None
               assert item['to'] is None
               if UNKNOWN_COMMENT_RE.match(item['from']) is None:
                  comment = website.markup_source.get_deleted_comment_body(issue['id'], rev_id)
                  fix_markup(website, file, comment)
                  new_tags = iter([
                     new_content_tag(soup, 'p', 'Deleted comment: ', attrs={'class': 'history-label'}),
                     new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
                           new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=comment)
                        ])
                  ])
            case (
               'status' # redundant with resolution
               | 'project' | 'Project' # redundant with Key
               | 'RemoteIssueLink' # unfortunately these were not preserved in the archive
               | 'CHK' | 'Linked' | 'Pinned' # pointless fields
               | 'Workflow' # noise
               | 'Console' | 'Description' | 'Flagged' | 'Original story points' # only used in one test ticket
               | 'issuetype' # only relevant to MCAPI which sadly was not preserved
               | 'Affected Platforms' # old field that was only ever removed from tickets
            ):
               pass
            case _:
               raise ValueError()
         if new_tags is not None:
            history_items.extend(new_tags)
      for tag in components.handle(soup):
         history_items.append(tag)
      for tag in affected_versions.handle(soup):
         history_items.append(tag)
      for tag in fixed_versions.handle(soup):
         history_items.append(tag)
      for tag in attachments.handle(soup):
         history_items.append(tag)
      for tag in links.handle(soup):
         history_items.append(tag)
      if len(history_items) > 0:
         date_tag = render_date_range(soup, entry.start_time, entry.end_time)
         date_tag.attrs['class'] = 'comment-time'
         revisions_list.append(new_content_tag(soup, 'div', attrs={'class': 'history-entry'}, content=[
            new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=[
               comment_author(website, file, entry.user_key),
               ' ',
               date_tag
            ]),
            new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=history_items)
         ]))
   return new_content_tag(soup, 'div', attrs={'class': 'issue-history-section issue-body'}, content=revisions_list)

def comment_author(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   user_tag = user_link(website, file, user_key)
   user_text = user_tag if 'username' in user_tag.attrs['class'] else user_tag.find(class_='username')
   assert user_text is not None
   user_text.attrs['class'] = 'username comment-author'
   return user_tag

@dataclasses.dataclass
class RenderableComment:
   comment: Comment | NewComment
   rendered_body: bs4.BeautifulSoup
   secret: bool

def render_author_key_or_dict(website: Website, file: HtmlFile, author: str | NewAuthor) -> bs4.Tag:
   if isinstance(author, dict):
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'username comment-author'}, content=author['displayName'])
   else:
      return comment_author(website, file, author)

def comment_authorship(website: Website, file: HtmlFile, comment: Comment | NewComment, secret: bool) -> bs4.Tag:
   soup = file.page.soup
   div = soup.new_tag('div', attrs={'class': 'comment-head'})
   created_time = datetime.datetime.fromisoformat(comment['created'])
   updated_time = datetime.datetime.fromisoformat(comment['updated'])
   if 'author' in comment:
      div.append(render_author_key_or_dict(website, file, comment['author']))
      div.append(' ')
   # apply the comment-time class to the entire span and the link specifically so they both turn gray
   time_part = new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=[
      new_content_tag(soup, 'a', attrs={'class': 'comment-time', 'href': f'#comment-id-{comment['id']}'}, content=[
         render_datetime(soup, created_time)
      ])
   ])
   has_update_author = 'updateAuthor' in comment and ('author' not in comment or comment['updateAuthor'] != comment['author'])
   has_update = comment['updated'] != comment['created']
   if has_update_author or has_update:
      time_part.append(' • edited ')
   if has_update_author:
      assert 'updateAuthor' in comment
      time_part.append(render_author_key_or_dict(website, file, comment['updateAuthor']))
      if has_update:
         time_part.append(' ')
   if has_update:
      if same_day(created_time, updated_time):
         inner_time = render_time(soup, updated_time)
      else:
        inner_time = render_datetime(soup, updated_time)
      time_part.append(inner_time)
   if 'visibility' in comment:
      time_part.extend([
         ' • ',
         soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/ic_locked.png'))}),
         ' Restricted to ',
         new_content_tag(soup, 'span', attrs={'class': 'comment-visibility-name'}, content=comment['visibility']['value'])
      ])
   if secret:
      time_part.extend([
         ' • ',
         soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/ic_locked.png'))}),
         ' Secret comment',
      ])
   div.append(time_part)
   return div

def render_issue_comments(website: Website, file: HtmlFile, comments: list[RenderableComment]) -> bs4.Tag:
   soup = file.page.soup
   comments_list: list[bs4.Tag] = []
   for entry in comments:
      comment_div = new_content_tag(soup, 'div', attrs={'class': 'comment'}, content=[
         soup.new_tag('div', attrs={'class': 'anchor', 'id': f'comment-id-{entry.comment['id']}'}),
         comment_authorship(website, file, entry.comment, entry.secret)
      ])
      comment_div.append(new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=entry.rendered_body)
      ]))
      comments_list.append(comment_div)
   return new_content_tag(soup, 'div', attrs={'class': 'issue-comment-section issue-body'}, content=comments_list)

def render_attachment(website: Website, file: HtmlFile, attachment: Attachment, include_upload: bool) -> bs4.Tag:
   soup = file.page.soup
   preview = attachment_preview(website, file, attachment)
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   link = relative_link(website.root, file.path, attach_path)
   details_div = soup.new_tag('div', attrs={'class': 'attachment-details'})
   attach_div = soup.new_tag('div', attrs={'class': 'attachment-block'})
   attach_div.append(preview)
   attach_div.append(details_div)
   details_div.append(new_content_tag(soup, 'a', attrs={'href': link}, content=attachment['filename']))
   if include_upload:
      if 'author' in attachment:
         details_div.append(
            new_content_tag(soup, 'p', content=comment_author(website, file, attachment['author']))
         )
      date_tag = render_datetime(soup, datetime.datetime.fromisoformat(attachment['created']))
      date_tag.attrs['class'] = 'comment-time'
      details_div.append(
         new_content_tag(soup, 'p', content=date_tag)
      )
   return attach_div

def render_issue_attachments(website: Website, file: HtmlFile, attachments: list[str]) -> bs4.Tag:
   soup = file.page.soup
   attach_list: list[bs4.Tag] = []
   for entry in attachments:
      attach_info = website.archive.get_attachment_data(entry)
      assert attach_info is not None
      attach_div = render_attachment(website, file, attach_info, include_upload=True)
      attach_list.append(attach_div)
   issue_attaches = new_content_tag(soup, 'details', attrs={'class': 'issue-body', 'open': ''}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'Attachments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(attachments)))
         ])
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'attachments'}, content=attach_list)
   ])
   return issue_attaches

def render_issue_links(website: Website, file: HtmlFile, links: list[IssueLink]) -> bs4.Tag | None:
   soup = file.page.soup
   link_types: dict[str, list[Issue]] = {}
   for link in links:
      if 'inwardIssue' in link:
         identity = website.metas.link_types[link['type']]['inward']
         linked_issue = link['inwardIssue']
      elif 'outwardIssue' in link:
         identity = website.metas.link_types[link['type']]['outward']
         linked_issue = link['outwardIssue']
      else:
         raise ValueError()
      if identity not in link_types:
         link_types[identity] = []
      linked_data = website.archive.get_issue_data(linked_issue)
      assert linked_data is not None
      link_types[identity].append(linked_data)
   if len(link_types) == 0:
      return None
   link_lists: list[bs4.Tag] = []
   for link_desc, issues in link_types.items():
      link_list: list[bs4.Tag] = []
      for linked_issue in issues:
         link_list.append(big_issue_link(website, file, linked_issue))
      link_block = new_content_tag(soup, 'details', attrs={'open': ''}, content=[
         new_content_tag(soup, 'summary', attrs={'class': 'issue-link-type'}, content=[
            new_content_tag(soup, 'h3', content=[
               link_desc,
               new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issues)))
            ]),
         ]),
         new_content_tag(soup, 'div', attrs={'class': 'issue-links-category'}, content=link_list)
      ])
      link_lists.append(link_block)
   link_section = new_content_tag(soup, 'details', attrs={'class': 'issue-body', 'open': ''}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'Linked Issues'
         ])
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'issue-link-section issue-body'}, content=link_lists)
   ])
   return link_section

def render_issue_details(website: Website, file: HtmlFile, issue: Issue, full: bool) -> bs4.Tag:
   fields = issue['fields']
   soup = file.page.soup
   project = website.metas.projects[fields['project']]
   issue_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   append_desc_item(soup, issue_details,
      'Status:',
      meta_link(website, file, 'resolution', fields['resolution'])
   )
   if 'security' in fields:
      append_desc_item(soup, issue_details,
         'Security:',
         field_link(website, file, 'security', fields['security']['id'])
      )
   if full:
      append_desc_item(soup, issue_details,
         'Reporter:',
         user_link(website, file, fields['reporter'])
      )
      if fields['reporter'] != fields['creator']:
         append_desc_item(soup, issue_details,
            'Creator:',
            user_link(website, file, fields['creator'])
         )
   if 'customfield_11800' in fields and fields['customfield_11800'] is not None:
      append_desc_item(soup, issue_details,
         'Partner Team:',
         fields['customfield_11800']
      )
   if full:
      if 'assignee' in fields and fields['assignee'] is not None:
         append_desc_item(soup, issue_details,
            'Assignee:',
            user_link(website, file, fields['assignee'])
         )
      append_desc_item(soup, issue_details,
         'Created:',
         render_datetime(soup, datetime.datetime.fromisoformat(fields['created']))
      )
      append_desc_item(soup, issue_details,
         'Updated:',
         render_datetime(soup, datetime.datetime.fromisoformat(fields['updated']))
      )
      if 'customfield_12201'in fields and fields['customfield_12201'] is not None:
         append_desc_item(soup, issue_details,
            'Triaged:',
            render_datetime(soup, datetime.datetime.fromisoformat(fields['customfield_12201']))
         )
      if fields['resolutiondate'] is not None:
         append_desc_item(soup, issue_details,
            'Resolved:',
            render_datetime(soup, datetime.datetime.fromisoformat(fields['resolutiondate']))
         )
      append_desc_item(soup, issue_details,
         'Votes:',
         new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(fields['votes']['votes']))
      )
      append_desc_item(soup, issue_details,
         'Watchers:',
         new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(fields['watches']['watchCount']))
      )
   if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
      append_desc_item(soup, issue_details,
         'Confirmation Status:',
         field_link(website, file, 'customfield_10500', fields['customfield_10500']['id'])
      )
   if 'priority' in fields and fields['priority'] is not None:
      append_desc_item(soup, issue_details,
         'Priority:',
         field_link(website, file, 'priority', fields['priority']['id'])
      )
   if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
      append_desc_item(soup, issue_details,
         'Mojang Priority:',
         field_link(website, file, 'customfield_12200', fields['customfield_12200']['id'])
      )
   if 'customfield_11500' in fields and fields['customfield_11500'] is not None:
      append_desc_item(soup, issue_details,
         'ADO:',
         fields['customfield_11500']
      )
   if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
      append_desc_item(soup, issue_details,
         'Area:',
         field_link(website, file, 'customfield_12800', fields['customfield_12800']['id'])
      )
   if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
      category_list = inline_list(soup, map(lambda x: field_link(website, file, 'customfield_11901', x['id']), fields['customfield_11901']))
      append_desc_item(soup, issue_details,
         'Category:',
         category_list
      )
   if 'components' in fields and len(fields['components']) > 0:
      component_list = inline_list(soup, map(lambda x: field_link(website, file, 'components', x['id']), fields['components']))
      append_desc_item(soup, issue_details,
         'Component:',
         component_list
      )
   if 'customfield_10501' in fields and fields['customfield_10501'] is not None:
      append_desc_item(soup, issue_details,
         'Game Mode:',
         field_link(website, file, 'customfield_10501', fields['customfield_10501']['id'])
      )
   if 'customfield_10402' in fields and fields['customfield_10402'] is not None:
      append_desc_item(soup, issue_details,
         'Platform:',
         field_link(website, file, 'customfield_10402', fields['customfield_10402']['id'])
      )
   if 'customfield_12301' in fields and fields['customfield_12301'] is not None:
      append_desc_item(soup, issue_details,
         'Platform:',
         field_link(website, file, 'customfield_12301', fields['customfield_12301']['id'])
      )
   if 'customfield_12400' in fields and fields['customfield_12400'] is not None:
      append_desc_item(soup, issue_details,
         'Platform:',
         field_link(website, file, 'customfield_12400', fields['customfield_12400']['id'])
      )
   if 'customfield_12900' in fields and fields['customfield_12900'] is not None:
      append_desc_item(soup, issue_details,
         'Platform:',
         field_link(website, file, 'customfield_12400', fields['customfield_12900']['id'])
      )
   if 'customfield_11300' in fields and fields['customfield_11300'] is not None:
      append_desc_item(soup, issue_details,
         'OS Version:',
         fields['customfield_11300']
      )
   append_desc_item(soup, issue_details,
      'Labels:',
      inline_list(soup, map(lambda x: field_link(website, file, 'labels', x), fields['labels']))
   )
   if 'versions' in fields:
      versions = list(map(lambda x: project['versions'][x], fields['versions']))
      append_desc_item(soup, issue_details,
         'Affects Versions:',
         render_version_list(website, file, project, versions)
      )
   if 'customfield_11802' in fields and fields['customfield_11802'] is not None:
      append_desc_item(soup, issue_details,
         'Regression Builds:',
         fields['customfield_11802']
      )
   if full:
      if 'fixVersions' in fields:
         versions = list(map(lambda x: project['versions'][x], fields['fixVersions']))
         append_desc_item(soup, issue_details,
            'Fix Versions:',
            render_version_list(website, file, project, versions)
         )
      data_link = relative_path(website.root, file.path, website.archive.get_issue_path(issue['id']))
      append_desc_item(soup, issue_details,
         'Links:',
         new_content_tag(soup, 'ul', content=[
            new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': urllib.parse.quote(str(data_link))}, content='JSON')),
            new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://mojira.dev/{issue['key']}'}, content='mojira.dev')),
            new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://bugs.mojang.com/browse/{issue['key']}'}, content='bugs.mojang.com')),
            new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://report.bugs.mojang.com/servicedesk/customer/portal/2/{issue['key']}'}, content='report.bugs.mojang.com')),
            new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://mojira.atlassian.net/browse/{issue['key']}'}, content='mojira.atlassian.net')),
         ])
      )
   return issue_details

def attachment_preview(website: Website, file: HtmlFile, attachment: Attachment) -> bs4.Tag:
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   link = relative_link(website.root, file.path, attach_path)
   if attachment['mimeType'].startswith('image/'):
      return file.page.soup.new_tag('img', attrs={'class': 'attachment-img', 'src': link, 'alt': attachment['filename'], 'loading': 'lazy'})
   if attachment['mimeType'].startswith('video/'):
      return new_content_tag(file.page.soup, 'video', attrs={'class': 'attachment-img', 'alt': attachment['filename'], 'loading': 'lazy', 'controls': ''}, content=[file.page.soup.new_tag('source', attrs={'src': link})])
   if attachment['mimeType'] == 'application/zip':
      return file.page.soup.new_tag('img', attrs={'class': 'attachment-icon', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/attach/zip.gif'))})
   if attachment['mimeType'] == 'text/plain':
      return file.page.soup.new_tag('img', attrs={'class': 'attachment-icon', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/attach/text.gif'))})
   return file.page.soup.new_tag('img', attrs={'class': 'attachment-icon', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/attach/file.gif'))})

def get_avatar_path(archive: mojira.Archive, folder: pathlib.Path, url: str) -> pathlib.Path | None:
   avatar_id = archive.get_avatar_id(url)
   avatar_file = folder / (avatar_id + '.png')
   if avatar_file.exists():
      return avatar_file
   avatar_file = folder / (avatar_id + '.svg')
   if avatar_file.exists():
      return avatar_file
   return None

def project_link(website: Website, file: HtmlFile, project: Project) -> bs4.Tag:
   key = project['key']
   avatar_url = project['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.project_avatars_folder, avatar_url)
   img = file.page.soup.new_tag('img', attrs={'width': '32', 'height': '32'})
   if avatar_path is not None:
      img.attrs['src'] = str(relative_path(website.root, file.path, avatar_path))
   return new_content_tag(file.page.soup, 'a', [
      new_content_tag(file.page.soup, 'span', [
         new_content_tag(file.page.soup, 'span', [
            img
         ], attrs={'class': 'project-avatar'}),
         key
      ], attrs={'class':'project-key'})
   ], attrs={'href': relative_link(website.root, file.path, website.project_folder / key / 'index.html')})

def big_issue_link(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   cls = 'issue-link' if issue['fields']['resolution'] is None else 'issue-link issue-resolved'
   link = relative_link(website.root, file.path, website.issues_folder / (issue['key'] + '.html'))
   return new_content_tag(file.page.soup, 'a', attrs={'class': cls, 'href': link}, content=[
      bug_icon(website, file),
      new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-link-key'}, content=issue['key']),
      new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-link-summary', 'title': issue['fields']['summary']}, content=issue['fields']['summary']),
      merged_status(website, file, issue)
   ])

def issue_link(website: Website, file: HtmlFile, issue: Issue, with_summary: bool) -> bs4.Tag:
   key = issue['key']
   linkpart = new_content_tag(file.page.soup, 'a', key, attrs={'class': 'issue-link-key', 'href': relative_link(website.root, file.path, website.issues_folder / (key + '.html'))})
   if with_summary:
      tag = new_content_tag(file.page.soup, 'span', [bug_icon(website, file), linkpart, ' ', issue['fields']['summary']])
   else:
      tag = new_content_tag(file.page.soup, 'span', [bug_icon(website, file), linkpart])
   if issue['fields']['resolution'] is not None:
      tag.attrs['class'] = 'small-issue-link issue-resolved'
   else:
      tag.attrs['class'] = 'small-issue-link'
   return tag

def issue_key(website: Website, file: HtmlFile, issue_key: str) -> bs4.Tag:
   linkpart = new_content_tag(file.page.soup, 'span', issue_key, attrs={'class': 'issue-link-key'})
   tag = new_content_tag(file.page.soup, 'span', [bug_icon(website, file), linkpart], attrs={'class': 'small-issue-link'})
   return tag

def user_link(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   user_data = website.archive.get_user_data(user_key)
   if user_data is None:
      user_data = website.archive.get_unknown_user_data(user_key)
      assert user_data is not None
      display_name = user_data['name']
   else:
      display_name = user_data['displayName']
   avatar_url = user_data['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.users_avatars_folder, avatar_url)
   img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy', 'class': 'avatar'})
   if avatar_path is not None:
      img['src'] = str(relative_path(website.root, file.path, avatar_path))
   link_url = relative_link(website.root, file.path, website.users_folder / (urllib.parse.quote_plus(user_key) + '.html'))
   return new_content_tag(file.page.soup, 'span', attrs={'class': 'user-reference'}, content=[
      new_content_tag(file.page.soup, 'span', attrs={'class': 'aui-avatar aui-avatar-small'}, content=img),
      ' ',
      new_content_tag(file.page.soup, 'a', attrs={'class':'user-hover user-link', 'rel': user_data['name'], 'href': link_url}, content=[
         new_content_tag(file.page.soup, 'span', attrs={'class': 'username'}, content=display_name),
      ])
   ])

def mojang_priority_icon(website: Website, file: HtmlFile, value: str) -> bs4.Tag:
   prio = {'Trivial': 'trivial', 'Low': 'low', 'Normal': 'medium', 'Important': 'high', 'Very Important': 'major'}[value]
   img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / f'data/assets/images/icons/priorities/{prio}.svg'))})
   return img

def priority_icon(website: Website, file: HtmlFile, value: str) -> bs4.Tag:
   prio = {'Low': 'trivial', 'Normal': 'minor', 'Important': 'major', 'Blocker': 'blocker', 'Critical': 'critical'}[value]
   img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / f'data/assets/images/icons/priorities/{prio}.svg'))})
   return img

def meta_link(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value_key: str | None) -> bs4.Tag:
   display = website.metas.display_value(meta_id, value_key)
   assert display is not None
   link = relative_link(website.root, file.path, website.field_pages[meta_id].get_value_path(display.name))
   content: list[bs4.Tag | str] = [display.name]
   cls = f'status-badge field-value-{meta_id}'
   tag = new_content_tag(file.page.soup, 'a', content, attrs={'class': cls, 'href': link})
   if display.description is not None:
      tag.attrs['title'] = display.description
   if meta_id == 'resolution' and value_key is not None:
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-resolved'}, content=tag)
   return tag

def field_link(website: Website, file: HtmlFile, field_id: str, value_key: str) -> bs4.Tag:
   field_name_str = website.metas.fields[field_id]['name'].lower().replace(' ', '-')
   display = website.relations.fields.display_value(field_id, value_key)
   assert display is not None
   link = relative_link(website.root, file.path, website.field_pages[field_id].get_value_path(display.name))
   content: list[bs4.Tag | str] = [display.name]
   cls = f'status-badge field-value-{field_name_str}'
   if field_id == 'priority':
      content.insert(0, priority_icon(website, file, display.name))
      cls += ' priority-badge'
   elif field_id == 'customfield_12200':
      content.insert(0, mojang_priority_icon(website, file, display.name))
      cls += ' priority-badge'
   tag = new_content_tag(file.page.soup, 'a', content, attrs={'class': cls, 'href': link})
   if display.description is not None:
      tag.attrs['title'] = display.description
   return tag

def merged_status(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   cls = 'status-badge'
   if issue['fields']['resolution'] is not None:
      name = website.metas.resolutions[issue['fields']['resolution']]['name']
      result = new_content_tag(file.page.soup, 'span', name)
   elif 'customfield_12200' in issue['fields'] and issue['fields']['customfield_12200'] is not None:
      img = mojang_priority_icon(website, file, issue['fields']['customfield_12200']['value'])
      result = new_content_tag(file.page.soup, 'span', [img, issue['fields']['customfield_12200']['value']])
      cls += ' priority-badge'
   elif 'customfield_10500' in issue['fields'] and issue['fields']['customfield_10500'] is not None:
      result = new_content_tag(file.page.soup, 'span', issue['fields']['customfield_10500']['value'])
   else:
      result = new_content_tag(file.page.soup, 'span', 'Unresolved')
   result.attrs['class'] = cls
   return result

def render_version_list(website: Website, file: HtmlFile, project: Project, versions: list[Version]) -> bs4.Tag | str:
   if len(versions) == 0:
      return ''
   if len(versions) == 1:
      return version_link(website, file, project, versions[0])
   span = inline_list(file.page.soup, map(lambda x: version_link(website, file, project, x), versions))
   if len(versions) <= 4:
      return span
   return new_content_tag(file.page.soup, 'details', [
      new_content_tag(file.page.soup, 'summary', [
         version_link(website, file, project, versions[0]),
         ' - ',
         version_link(website, file, project, versions[-1]),
      ]),
      span
   ])

def version_link(website: Website, file: HtmlFile, project: Project, version: Version) -> bs4.Tag:
   name = version['name']
   name = name.removeprefix('Minecraft ').removeprefix('Snapshot ')
   name = name.replace(' Pre-Release ', '-pre').replace(' Pre-release ', '-pre').replace(' Release Candidate ', '-rc')
   return new_content_tag(file.page.soup, 'a', name, attrs={'class': 'status-badge', 'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'versions' / (urllib.parse.quote_plus(version['name']) + '.html'))})

if __name__ == '__main__':
   main()
