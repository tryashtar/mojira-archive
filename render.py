import dataclasses
import typing
from jiratypes import Attachment, Comment, Issue, IssueLink, Project, Revision, RevisionChange, Version
import mojira
import relations
import pathlib
import datetime
import urllib.parse
import markup
import bs4
import re
import bisect
import xmldiff.main
import xmldiff.formatting
import lxml.html.soupparser
from web import HtmlFile, append_desc_item, append_row, html_find_replace, html_to_text, make_desc_list, make_file, make_table, new_content_tag, relative_link, relative_path, write_html

@dataclasses.dataclass
class FieldFolders:
   confirmation_status: pathlib.PurePath
   labels: pathlib.PurePath
   category: pathlib.PurePath
   area: pathlib.PurePath
   mojang_priority: pathlib.PurePath
   resolution: pathlib.PurePath
   security: pathlib.PurePath

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   project_list: HtmlFile
   project_folder: pathlib.PurePath
   issues_folder: pathlib.PurePath
   users_folder: pathlib.PurePath
   field_folders: FieldFolders
   archive: mojira.Archive
   metas: mojira.ArchiveMetas
   relations: relations.Relations
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
   rels = relations.Relations()
   rels.load(root / 'relations')
   markup_source = markup.MarkupSource(root / 'markup')
   secret_comments = mojira.SecretComments(root / 'secret_comments.json')
   website = Website(
      root=root,
      project_list=make_jira_file(root, pathlib.PurePath('web/index.html'), 'Mojira Archive'),
      project_folder=pathlib.PurePath('web/projects'),
      issues_folder=pathlib.PurePath('web/issues'),
      users_folder=pathlib.PurePath('web/users'),
      field_folders=FieldFolders(
         confirmation_status=pathlib.PurePath('web/fields/confirmation_status'),
         labels=pathlib.PurePath('web/fields/label'),
         resolution=pathlib.PurePath('web/fields/resolution'),
         category=pathlib.PurePath('web/fields/category'),
         area=pathlib.PurePath('web/fields/area'),
         mojang_priority=pathlib.PurePath('web/fields/mojang_priority'),
         security=pathlib.PurePath('web/fields/security'),
      ),
      archive=archive,
      metas=metas,
      relations=rels,
      markup_source=markup_source,
      secret_comments=secret_comments
   )
   print('Rendering...')

   file = create_issue_page(website, archive.get_issue_data(rels.issue_keys['MC-4']))
   save_file(website, file)
   file = create_issue_page(website, archive.get_issue_data(rels.issue_keys['MC-1691']))
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
   for tag in html.find_all(class_='issue-link'):
      tag.attrs['class'] = 'inline-issue-link'
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
      user_key = website.relations.user_keys.get(normalized, normalized)
      return relative_link(website.root, file.path, website.users_folder / (urllib.parse.quote_plus(user_key) + '.html'))
   assert False

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
   issues = website.relations.projects[project['id']]
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
   table = render_issues_table(website, file, website.relations.projects[project['id']])
   content.append(table)
   file.page.body.append(content)
   return file

def create_version_page(website: Website, project: Project, version: Version) -> HtmlFile:
   full_title = f'[{project['key']}] {version['name']}'
   rels = website.relations.versions.get(version['id'], {'affected':[], 'fixed':[]})
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
      append_desc_item(soup, fields, 'Date', render_date(soup, version['releaseDate']))
   append_desc_item(soup, fields, 'Status', 'Archived' if version['archived'] else ('Active' if version['released'] else 'Unreleased'))
   append_desc_item(soup, fields, 'Affected Issues', str(len(rels['affected'])))
   append_desc_item(soup, fields, 'Fixed Issues', str(len(rels['fixed'])))
   content.append(fields)
   affected_table = render_issues_table(website, file, rels['affected'])
   content.append('Affected:')
   content.append(affected_table)
   fixes_table = render_issues_table(website, file, rels['fixed'])
   content.append('Fixes:')
   content.append(fixes_table)
   file.page.body.append(content)
   return file

def render_projects_table(website: Website, file: HtmlFile, projects: typing.Iterable[Project]) -> bs4.Tag:
   table = make_table(file.page.soup, ['Project', 'Name', 'Issues', 'Versions'])
   table.attrs['class'] = 'projects-table sortable'
   for project in projects:
      issues = website.relations.projects[project['id']]
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
      rel_ver = website.relations.versions.get(version['id'], {'affected':[], 'fixed':[]})
      append_row(file.page.soup, table, [
         version_link(website, file, project, version),
         version['description'] if 'description' in version else '',
         render_date(file.page.soup, version['releaseDate']) if 'releaseDate' in version else '',
         str(len(rel_ver['affected'])),
         str(len(rel_ver['fixed'])),
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
      date = render_datetime(file.page.soup, issue['fields']['created'])
      link = new_content_tag(file.page.soup, 'a', issue['key'], attrs={'href': relative_link(website.root, file.path, website.issues_folder / (issue['key'] + '.html'))})
      append_row(file.page.soup, table, [link, issue['fields']['summary'], reporter, date])
   return table

def make_generic_header(website: Website, file: HtmlFile) -> bs4.Tag:
   header = new_content_tag(file.page.soup, 'header', [
      new_content_tag(file.page.soup, 'a', 'Mojira Archive', attrs={'class': 'header-main', 'href': relative_link(website.root, file.path, website.project_list.path)})
   ])
   return header

def bug_icon(website: Website, file: HtmlFile) -> bs4.Tag:
   return file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/icon/bug.svg'))})

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
   issue_div = soup.new_tag('div', attrs={'id': 'issue', 'class': 'issue'})
   content.append(issue_div)
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-top'}, content=[
      new_content_tag(soup, 'div', attrs={'class': 'issue-title'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'issue-key', 'data-copy': key}, content=[
            bug_icon(website, file),
            new_content_tag(soup, 'span', key)
         ]),
         new_content_tag(soup, 'h1', attrs={'class': 'issue-summary'}, content=summary)
      ])
   ]))
   issue_body = render_issue_body(website, file, issue)
   issue_details = render_issue_details(website, file, issue)
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-split'}, content=[
      issue_body,
      issue_details
   ]))
   link_section = render_issue_links(website, file, issue['fields']['issuelinks'])
   if link_section is not None:
      issue_body.append(link_section)
   if len(issue['fields']['attachment']) > 0:
      attach_section = render_issue_attachments(website, file, issue['fields']['attachment'])
      issue_body.append(attach_section)
   if len(issue['fields']['comment']['comments']) > 0:
      all_comments: list[tuple[Comment, bs4.BeautifulSoup]] = []
      for comment in issue['fields']['comment']['comments']:
         body = website.markup_source.get_comment_body(issue['id'], comment['id'])
         fix_markup(website, file, body)
         all_comments.append((comment, body))
      for comment in website.secret_comments.get(issue['id']):
         converted_comment: Comment = {
            'id': comment['id'],
            'author': comment['author']['displayName'],
            'updateAuthor': comment['author']['displayName'],
            'body': comment['body'],
            'created': comment['created'],
            'updated': comment['updated'],
            'visibility': {
               'type': 'secret',
               'value': 'secret'
            }
         }
         body = website.markup_source.get_secret_comment_body(issue['id'], comment['id'])
         fix_markup(website, file, body)
         bisect.insort_left(all_comments, (converted_comment, body), key=lambda x: datetime.datetime.fromisoformat(x[0]['created']))
      comment_section = render_issue_comments(website, file, all_comments)
      issue_body.append(comment_section)
   if len(issue['changelog']['histories']) > 0:
      attach_section = render_issue_revisions(website, file, issue, issue['changelog']['histories'])
      issue_body.append(attach_section)
   return file

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
   return issue_body

class TrackedMultiSetRevision:
   def __init__(self, name: str, creator: typing.Callable[[list[tuple[str, str]]], bs4.Tag]):
      self.added: list[tuple[str, str]] = []
      self.removed: list[tuple[str, str]] = []
      self.name = name
      self.creator = creator

   def handle(self, soup: bs4.BeautifulSoup) -> typing.Generator[bs4.Tag]:
      if len(self.added) > 0:
         yield new_content_tag(soup, 'p', [
            f'Added {self.name}: ',
            self.creator(self.added)
         ])
      if len(self.removed) > 0:
         yield new_content_tag(soup, 'p', [
            f'Removed {self.name}: ',
            self.creator(self.added)
         ])

def revision_import_multi(versions: TrackedMultiSetRevision, entry: RevisionChange):
   if entry['to'] is not None:
      assert entry['toString'] is not None
      versions.added.append((entry['to'], entry['toString']))
   if entry['from'] is not None:
      assert entry['fromString'] is not None
      versions.removed.append((entry['from'], entry['fromString']))

class TrackedMultiValueRevision:
   def __init__(self, name: str, separator: str, creator: typing.Callable[[set[str]], bs4.Tag]):
      self.previous: list[str] | None = None
      self.name = name
      self.separator = separator
      self.creator = creator

   def handle(self, soup: bs4.BeautifulSoup, revision: RevisionChange) -> typing.Generator[bs4.Tag]:
      if self.previous is None:
         self.previous = revision['fromString'].split(self.separator) if revision['fromString'] is not None else []
      new_values = revision['toString'].split(self.separator) if revision['toString'] is not None else []
      added_values = set(new_values) - set(self.previous)
      removed_values = set(self.previous) - set(new_values)
      if len(added_values) > 0:
         yield new_content_tag(soup, 'p', [
            f'Added {self.name}: ',
            self.creator(added_values)
         ])
      if len(removed_values) > 0:
         yield new_content_tag(soup, 'p', [
            f'Removed {self.name}: ',
            self.creator(removed_values)
         ])
      self.previous = new_values

def revision_always_set(soup: bs4.BeautifulSoup, revision: RevisionChange, label: str, creator: typing.Callable[[str], bs4.Tag]) -> bs4.Tag:
   assert revision['fromString'] is not None
   assert revision['toString'] is not None
   return new_content_tag(soup, 'p', [
      f'{label}: ',
      creator(revision['fromString']),
      ' → ',
      creator(revision['toString'])
   ])

def revision_always_set_source(soup: bs4.BeautifulSoup, revision: RevisionChange, label: str, creator: typing.Callable[[str | None], bs4.Tag]) -> bs4.Tag:
   return new_content_tag(soup, 'p', [
      f'{label}: ',
      creator(revision['from']),
      ' → ',
      creator(revision['to'])
   ])

def revision_optional(soup: bs4.BeautifulSoup, revision: RevisionChange, label: str, creator: typing.Callable[[str], bs4.Tag]) -> typing.Generator[bs4.Tag]:
   if revision['to'] is not None and revision['from'] is not None:
      assert revision['fromString'] is not None
      assert revision['toString'] is not None
      yield new_content_tag(soup, 'p', [
         f'{label}: ',
         creator(revision['fromString']),
         ' → ',
         creator(revision['toString'])
      ])
   elif revision['to'] is None and revision['from'] is not None:
      assert revision['fromString'] is not None
      yield new_content_tag(soup, 'p', [
         f'Removed {label}: ',
         creator(revision['fromString'])
      ])
   elif revision['from'] is None and revision['to'] is not None:
      assert revision['toString'] is not None
      yield new_content_tag(soup, 'p', [
         f'Added {label}: ',
         creator(revision['toString'])
      ])

def revision_optional_source(soup: bs4.BeautifulSoup, revision: RevisionChange, label: str, creator: typing.Callable[[str], bs4.Tag]) -> typing.Generator[bs4.Tag]:
   if revision['to'] is not None and revision['from'] is not None:
      yield new_content_tag(soup, 'p', [
         f'{label}: ',
         creator(revision['from']),
         ' → ',
         creator(revision['to'])
      ])
   elif revision['to'] is None and revision['from'] is not None:
      yield new_content_tag(soup, 'p', [
         f'Removed {label}: ',
         creator(revision['from'])
      ])
   elif revision['from'] is None and revision['to'] is not None:
      yield new_content_tag(soup, 'p', [
         f'Added {label}: ',
         creator(revision['to'])
      ])

CONTROL_MAP = {chr(i): f'___SUB_CTRL_CHR_{i}' for i in list(range(32)) + [127]}
CONTROL_MAP_REV = {v: k for k, v in CONTROL_MAP.items()}

def revision_html_diff(soup: bs4.BeautifulSoup, label: str, before: bs4.Tag | None, after: bs4.Tag | None, panel_class: str) -> typing.Generator[bs4.Tag]:
   if before is not None and after is not None:
      html_find_replace(before, CONTROL_MAP)
      html_find_replace(after, CONTROL_MAP)
      # convert_tree strips off the top-level tag, so wrap it beforehand
      # diff_trees also works best with a top-level tag, so wrap it another tag too
      before_xml = lxml.html.soupparser.convert_tree(
         new_content_tag(soup, 'html', new_content_tag(soup, 'body', before))
      )[0]
      after_xml = lxml.html.soupparser.convert_tree(
         new_content_tag(soup, 'html', new_content_tag(soup, 'body', after))
      )[0]
      diff = xmldiff.main.diff_trees(before_xml, after_xml,
         diff_options={'fast_match': True}, # without fast_match, I tend to get lots of nodes moving around
         formatter=xmldiff.formatting.XMLFormatter()
      )
      # have to use lxml parser to expand self-closing XML tags that aren't valid HTML
      # but it wraps the output in <html><body>...</body></html>, so unwrap the original root
      before_diff = bs4.BeautifulSoup(diff, 'lxml').find('body')
      after_diff = bs4.BeautifulSoup(diff, 'lxml').find('body')
      assert before_diff is not None
      assert after_diff is not None
      html_find_replace(before_diff, CONTROL_MAP_REV)
      html_find_replace(after_diff, CONTROL_MAP_REV)
      has_insertions = False
      has_deletions = False
      for tag in before_diff.find_all('diff:insert'):
         tag.extract()
      for tag in before_diff.find_all(attrs={'diff:insert': True}):
         tag.extract()
      if after_diff.find('diff:insert') is not None or after_diff.find(attrs={'diff:insert': True}):
         has_insertions = True
      for tag in after_diff.find_all('diff:delete'):
         tag.extract()
      for tag in after_diff.find_all(attrs={'diff:delete': True}):
         tag.extract()
      if before_diff.find('diff:delete') is not None or before_diff.find(attrs={'diff:delete': True}):
         has_deletions = True
      if has_insertions and has_deletions:
         yield new_content_tag(soup, 'p', [
            f'Changed {label}: ',
            new_content_tag(soup, 'div', attrs={'class': panel_class}, content=[before_diff, after_diff])
         ])
      elif has_insertions:
         yield new_content_tag(soup, 'p', [
            f'Changed {label}: ',
            soup.new_tag('br'),
            after_diff
         ])
      elif has_deletions:
         yield new_content_tag(soup, 'p', [
            f'Changed {label}: ',
            soup.new_tag('br'),
            before_diff
         ])
   elif before is not None and after is None:
      yield new_content_tag(soup, 'p', [
         f'Removed {label}: ',
         soup.new_tag('br'),
         before
      ])
   elif after is not None and before is None:
      yield new_content_tag(soup, 'p', [
         f'Added {label}: ',
         soup.new_tag('br'),
         after
      ])

def render_issue_revisions(website: Website, file: HtmlFile, issue: Issue, revisions: list[Revision]) -> bs4.Tag:
   soup = file.page.soup
   project = website.metas.projects[issue['fields']['project']]
   revisions_list: list[bs4.Tag] = []
   labels = TrackedMultiValueRevision('labels', ' ', lambda x: labels_list(website, file, x))
   categories = TrackedMultiValueRevision('Category', ',', lambda x: inline_list(soup, map(lambda y: field_link(website, file, website.field_folders.category, y), x)))
   for revision in revisions:
      history_items: list[bs4.Tag] = []
      def version_creator(versions: list[tuple[str, str]]) -> bs4.Tag:
         def render_version(version_id: str, version_name: str) -> bs4.Tag:
            if version_id in project['versions']:
               return version_link(website, file, project, project['versions'][version_id])
            return new_content_tag(file.page.soup, 'span', version_name, attrs={'class': 'status-badge'})
         return inline_list(file.page.soup, map(lambda x: render_version(x[0], x[1]), versions))
      affected_versions = TrackedMultiSetRevision('affects versions', version_creator)
      fixed_versions = TrackedMultiSetRevision('fixed versions', version_creator)
      for item in revision['items']:
         match item['field']:
            case 'labels':
               for tag in labels.handle(soup, item):
                  history_items.append(tag)
            case 'Category':
               for tag in categories.handle(soup, item):
                  history_items.append(tag)
            case 'Confirmation Status':
               def creator(x: str): return field_link(website, file, website.field_folders.confirmation_status, x)
               for tag in revision_optional(soup, item, 'Confirmation Status', creator):
                  history_items.append(tag)
            case 'Area':
               def creator(x: str): return field_link(website, file, website.field_folders.area, x)
               for tag in revision_optional(soup, item, 'Area', creator):
                  history_items.append(tag)
            case 'Mojang Priority':
               def creator(x: str): return field_link(website, file, website.field_folders.mojang_priority, x)
               for tag in revision_optional(soup, item, 'Mojang Priority', creator):
                  history_items.append(tag)
            case 'resolution':
               def res_creator(x: str | None): return resolution_link(website, file, x)
               history_items.append(revision_always_set_source(soup, item, 'Resolution', res_creator))
            case 'security':
               def creator(x: str): return field_link(website, file, website.field_folders.security, x)
               for tag in revision_optional(soup, item, 'Security Level', creator):
                  history_items.append(tag)
            case 'summary':
               assert item['fromString'] is not None
               assert item['toString'] is not None
               before = new_content_tag(soup, 'span', item['fromString'])
               after = new_content_tag(soup, 'span', item['toString'])
               for tag in revision_html_diff(soup, 'summary', before, after, 'diff-panel-top'):
                  history_items.append(tag)
            case 'description':
               before, after = website.markup_source.get_issue_description_revision(issue['id'], revision['id'])
               if before is not None:
                  fix_markup(website, file, before)
                  before = new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=before)
               if after is not None:
                  fix_markup(website, file, after)
                  after = new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=after)
               for tag in revision_html_diff(soup, 'description', before, after, 'diff-panel-side'):
                  history_items.append(tag)
            case 'environment':
               before, after = website.markup_source.get_issue_environment_revision(issue['id'], revision['id'])
               if before is not None:
                  fix_markup(website, file, before)
                  before = new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=before)
               if after is not None:
                  fix_markup(website, file, after)
                  after = new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=after)
               for tag in revision_html_diff(soup, 'environment', before, after, 'diff-panel-side'):
                  history_items.append(tag)
            case 'Link':
               def link_creator(full: str, ticket: str, label: str):
                  link_dir = full[len('This issue '):-(len(ticket) + 1)]
                  if ticket in website.relations.issue_keys:
                     relevant_issue = website.archive.get_issue_data(website.relations.issue_keys[ticket])
                     assert relevant_issue is not None
                     return new_content_tag(soup, 'p', [
                        f'{label} {link_dir} link: ',
                        soup.new_tag('br'),
                        new_content_tag(soup, 'span', big_issue_link(website, file, relevant_issue))
                     ])
                  else:
                     return new_content_tag(soup, 'p', [
                        f'{label} {link_dir} link: {ticket}'
                     ])
               if item['to'] is not None:
                  assert item['toString'] is not None
                  history_items.append(link_creator(item['toString'], item['to'], 'Added'))
               if item['from'] is not None:
                  assert item['fromString'] is not None
                  history_items.append(link_creator(item['fromString'], item['from'], 'Removed'))
            case 'Attachment':
               def attach_creator(attach_id: str, filename: str, label: str):
                  attachment = website.archive.get_attachment_data(attach_id)
                  if attachment is not None:
                     return new_content_tag(soup, 'p', [
                        f'{label} attachment: ',
                        soup.new_tag('br'),
                        render_attachment(website, file, attachment, include_upload=False)
                     ])
                  broken = soup.new_tag('img', attrs={'class': 'broken-image', 'width': '32', 'height': '32', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/images/icons/attach/noimage.svg'))})
                  return new_content_tag(soup, 'p', [
                     f'{label} attachment: ',
                     new_content_tag(soup, 'span', [broken, filename])
                  ])
               if item['to'] is not None:
                  assert item['toString'] is not None
                  history_items.append(attach_creator(item['to'], item['toString'], 'Added'))
               if item['from'] is not None:
                  assert item['fromString'] is not None
                  history_items.append(attach_creator(item['from'], item['fromString'], 'Removed'))
            case 'Comment':
               assert item['from'] is not None
               assert item['to'] is None
               if UNKNOWN_COMMENT_RE.match(item['from']) is None:
                  comment = website.markup_source.get_deleted_comment_body(issue['id'], revision['id'])
                  fix_markup(website, file, comment)
                  history_items.append(new_content_tag(soup, 'p', [
                     'Deleted comment: ',
                     soup.new_tag('br'),
                     new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=comment)
                  ]))
            case 'Version':
               revision_import_multi(affected_versions, item)
            case 'Fix Version':
               revision_import_multi(affected_versions, item)
            case 'assignee':
               def creator(x: str): return user_link(website, file, x)
               for tag in revision_optional_source(soup, item, 'Assignee', creator):
                  history_items.append(tag)
            case 'reporter':
               def rep_creator(x: str | None): return user_link(website, file, x)
               history_items.append(revision_always_set_source(soup, item, 'Reporter', rep_creator))
            case 'status' | 'Linked' | 'RemoteIssueLink' | 'CHK' | 'Pinned' | 'Workflow':
               pass
            case _:
               print(item['field'])
               history_items.append(new_content_tag(soup, 'p', item['field']))
      for tag in affected_versions.handle(soup):
         history_items.append(tag)
      for tag in fixed_versions.handle(soup):
         history_items.append(tag)
      if len(history_items) > 0:
         date_tag = render_datetime(soup, revision['created'])
         date_tag.attrs['class'] = 'comment-time'
         revisions_list.append(new_content_tag(soup, 'div', attrs={'class': 'history-entry'}, content=[
            new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=[
               comment_author(website, file, revision['author']),
               ' ',
               date_tag
            ]),
            new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=history_items)
         ]))
   issue_revisions = new_content_tag(soup, 'details', attrs={'class': 'issue-body'}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'History',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(revisions)))
         ])
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'issue-history-section issue-body'}, content=revisions_list)
   ])
   return issue_revisions

def comment_author(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   user_tag = user_link(website, file, user_key)
   user_text = user_tag if 'username' in user_tag.attrs['class'] else user_tag.find(class_='username')
   assert user_text is not None
   user_text.attrs['class'] = 'username comment-author'
   return user_tag

def comment_time(soup: bs4.BeautifulSoup, id: str, date_str: str) -> bs4.Tag:
   tag = render_datetime(soup, date_str)
   return new_content_tag(soup, 'a', attrs={'class': 'comment-time', 'href': f'#comment-id-{id}'}, content=tag)

def render_issue_comments(website: Website, file: HtmlFile, comments: list[tuple[Comment, bs4.BeautifulSoup]]) -> bs4.Tag:
   soup = file.page.soup
   comments_list: list[bs4.Tag] = []
   for entry, body in comments:
      header = soup.new_tag('div', attrs={'class': 'comment-header'})
      header1tags: list[bs4.Tag | str] = []
      header2tags: list[bs4.Tag | str] = []
      if 'author' in entry:
         header1tags.append(comment_author(website, file, entry['author']))
      header1tags.append(' ')
      header1tags.append(comment_time(soup, entry['id'], entry['created']))
      if 'updateAuthor' in entry and ('author' not in entry or entry['updateAuthor'] != entry['author']):
         header2tags.append(comment_author(website, file, entry['updateAuthor']))
      if entry['updated'] != entry['created']:
         if len(header2tags) > 0:
            header2tags.append(' ')
         header2tags.append(new_content_tag(soup, 'span', 'edited ', attrs={'class': 'comment-time'}))
         header2tags.append(comment_time(soup, entry['id'], entry['updated']))
      header.append(new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=header1tags))
      if len(header2tags) > 0:
         header.append(new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=header2tags))
      if 'visibility' in entry:
         header.append(new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=[
            new_content_tag(soup, 'span', attrs={'class': 'comment-visibility'}, content=[
               soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': str(relative_path(website.root, file.path, website.root / 'data/assets/icon/locked.png'))}),
               ' Restricted to ',
               new_content_tag(soup, 'span', attrs={'class': 'comment-visibility-name'}, content=entry['visibility']['value'])
            ])
         ]))
      comment_div = new_content_tag(soup, 'div', attrs={'class': 'comment'}, content=[
         soup.new_tag('div', attrs={'class': 'anchor', 'id': f'comment-id-{entry['id']}'}),
         header
      ])
      comment_div.append(new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=body)
      ]))
      comments_list.append(comment_div)
   issue_comments = new_content_tag(soup, 'details', attrs={'class': 'issue-body', 'open': ''}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'Comments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(comments)))
         ])
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'issue-comment-section issue-body'}, content=comments_list)
   ])
   return issue_comments

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
      date_tag = render_datetime(soup, attachment['created'])
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
         assert False
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

def render_issue_details(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   fields = issue['fields']
   soup = file.page.soup
   project = website.metas.projects[fields['project']]
   issue_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   append_desc_item(soup, issue_details,
      'Status:',
      resolution_link(website, file, fields['resolution'])
   )
   append_desc_item(soup, issue_details,
      'Reporter:',
      user_link(website, file, fields['reporter'])
   )
   if fields['reporter'] != fields['creator']:
      append_desc_item(soup, issue_details,
         'Creator:',
         user_link(website, file, fields['creator'])
      )
   if 'assignee' in fields and fields['assignee'] is not None:
      append_desc_item(soup, issue_details,
         'Assignee:',
         user_link(website, file, fields['assignee'])
      )
   append_desc_item(soup, issue_details,
      'Created:',
      render_datetime(soup, fields['created'])
   )
   append_desc_item(soup, issue_details,
      'Updated:',
      render_datetime(soup, fields['updated'])
   )
   if 'customfield_12201'in fields and fields['customfield_12201'] is not None:
      append_desc_item(soup, issue_details,
         'Triaged:',
         render_datetime(soup, fields['customfield_12201'])
      )
   if fields['resolutiondate'] is not None:
      append_desc_item(soup, issue_details,
         'Resolved:',
         render_datetime(soup, fields['resolutiondate'])
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
         field_link(website, file, website.field_folders.confirmation_status, fields['customfield_10500']['value'])
      )
   if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
      append_desc_item(soup, issue_details,
         'Mojang Priority:',
         field_link(website, file, website.field_folders.mojang_priority, fields['customfield_12200']['value'])
      )
   if 'customfield_11500' in fields and fields['customfield_11500'] is not None:
      append_desc_item(soup, issue_details,
         'ADO:',
         fields['customfield_11500']
      )
   if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
      append_desc_item(soup, issue_details,
         'Area:',
         field_link(website, file, website.field_folders.area, fields['customfield_12800']['value'])
      )
   if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
      category_list = inline_list(soup, map(lambda x: field_link(website, file, website.field_folders.category, x['value']), fields['customfield_11901']))
      append_desc_item(soup, issue_details,
         'Category:',
         category_list
      )
   append_desc_item(soup, issue_details,
      'Labels:',
      labels_list(website, file, fields['labels'])
   )
   if 'versions' in fields:
      versions = list(map(lambda x: project['versions'][x], fields['versions']))
      append_desc_item(soup, issue_details,
         'Affects Versions:',
         render_version_list(website, file, project, versions)
      )
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

def labels_list(website: Website, file: HtmlFile, labels: typing.Iterable[str]) -> bs4.Tag:
   labels_list = inline_list(file.page.soup, map(lambda x: field_link(website, file, website.field_folders.labels, x), labels))
   labels_list.attrs['class'] = 'labels-list'
   return labels_list

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

def inline_list(soup: bs4.BeautifulSoup, items: typing.Iterator[bs4.Tag], separator: str = ' ') -> bs4.Tag:
   span = soup.new_tag('span')
   try:
      first = next(items)
   except StopIteration:
      return span
   span.append(first)
   for item in items:
      span.append(separator)
      span.append(item)
   return span

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
   linkpart = new_content_tag(file.page.soup, 'a', key, attrs={'href': relative_link(website.root, file.path, website.issues_folder / (key + '.html'))})
   if issue['fields']['resolution'] is not None:
      linkpart.attrs['class'] = 'resolved'
   if with_summary:
      return new_content_tag(file.page.soup, 'span', [linkpart, ' ', issue['fields']['summary']])
   else:
      return new_content_tag(file.page.soup, 'span', [linkpart])

def user_link(website: Website, file: HtmlFile, user_key: str | None) -> bs4.Tag:
   if user_key is None:
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'username'}, content='-')
   user_data = website.archive.get_user_data(user_key)
   if user_data is None:
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'username'}, content=user_key)
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

def field_link(website: Website, file: HtmlFile, folder: pathlib.PurePath, value: str) -> bs4.Tag:
   link = relative_link(website.root, file.path, folder / (urllib.parse.quote_plus(value) + '.html'))
   return new_content_tag(file.page.soup, 'a', value, attrs={'class': 'status-badge', 'href': link})

def merged_status(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   if issue['fields']['resolution'] is not None:
      name = website.metas.resolutions[issue['fields']['resolution']]['name']
      result = new_content_tag(file.page.soup, 'span', name)
   elif 'customfield_12200' in issue['fields'] and issue['fields']['customfield_12200'] is not None:
      result = new_content_tag(file.page.soup, 'span', issue['fields']['customfield_12200']['value'])
   elif 'customfield_10500' in issue['fields'] and issue['fields']['customfield_10500'] is not None:
      result = new_content_tag(file.page.soup, 'span', issue['fields']['customfield_10500']['value'])
   else:
      result = new_content_tag(file.page.soup, 'span', 'Unresolved')
   result.attrs['class'] = 'status-badge'
   return result

def resolution_link(website: Website, file: HtmlFile, resolution_id: str | None) -> bs4.Tag:
   if resolution_id is None:
      tag = field_link(website, file, website.field_folders.resolution, 'Unresolved')
      return tag
   else:
      name = website.metas.resolutions[resolution_id]['name']
      tag = field_link(website, file, website.field_folders.resolution, name)
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-resolved'}, content=tag)

def render_datetime(soup: bs4.BeautifulSoup, date_str: str) -> bs4.Tag:
   formatted = datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d, %I:%M:%S %p')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': date_str})

def render_date(soup: bs4.BeautifulSoup, date_str: str) -> bs4.Tag:
   formatted = datetime.date.fromisoformat(date_str).strftime('%Y-%m-%d')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': date_str})

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
   return new_content_tag(file.page.soup, 'a', version['name'], attrs={'class': 'status-badge', 'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'versions' / (urllib.parse.quote_plus(version['name']) + '.html'))})

if __name__ == '__main__':
   main()
