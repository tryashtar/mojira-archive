import dataclasses
import typing
from jiratypes import Attachment, Comment, Issue, IssueLink, Project, Revision, Version
import mojira
import relations
import pathlib
import datetime
import urllib.parse
import markup
import bs4
import re
import bisect
from web import HtmlFile, append_desc_item, append_row, html_to_text, make_desc_list, make_file, make_table, new_content_tag, relative_link, relative_path, write_html

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   project_list: HtmlFile
   project_folder: pathlib.PurePath
   issues_folder: pathlib.PurePath
   users_folder: pathlib.PurePath
   confirmation_folder: pathlib.PurePath
   labels_folder: pathlib.PurePath
   categories_folder: pathlib.PurePath
   areas_folder: pathlib.PurePath
   priorities_folder: pathlib.PurePath
   resolutions_folder: pathlib.PurePath
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
      confirmation_folder=pathlib.PurePath('web/fields/confirmations'),
      labels_folder=pathlib.PurePath('web/fields/labels'),
      resolutions_folder=pathlib.PurePath('web/fields/resolutions'),
      categories_folder=pathlib.PurePath('web/fields/categories'),
      areas_folder=pathlib.PurePath('web/fields/areas'),
      priorities_folder=pathlib.PurePath('web/fields/priorities'),
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
   return link

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

def render_issue_revisions(website: Website, file: HtmlFile, issue: Issue, revisions: list[Revision]) -> bs4.Tag:
   soup = file.page.soup
   revisions_list: list[bs4.Tag] = []
   labels: list[str] | None = None
   categories: list[str] | None = None
   for revision in revisions:
      history_items: list[bs4.Tag] = []
      versions_added: list[tuple[str, str]] = []
      versions_removed: list[tuple[str, str]] = []
      fix_versions_added: list[tuple[str, str]] = []
      fix_versions_removed: list[tuple[str, str]] = []
      for item in revision['items']:
         match item['field']:
            case 'labels':
               if labels is None:
                  labels = item['fromString'].split(' ') if item['fromString'] is not None else []
               new_labels = item['toString'].split(' ') if item['toString'] is not None else []
               added_labels = set(new_labels) - set(labels)
               removed_labels = set(labels) - set(new_labels)
               if len(added_labels) > 0:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Added labels: ',
                     labels_list(website, file, added_labels)
                  ]))
               if len(removed_labels) > 0:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Removed labels: ',
                     labels_list(website, file, removed_labels)
                  ]))
               labels = new_labels
            case 'Category':
               if categories is None:
                  categories = item['fromString'].split(',') if item['fromString'] is not None else []
               new_cats = item['toString'].split(',') if item['toString'] is not None else []
               added_cats = set(new_cats) - set(categories)
               removed_cats = set(categories) - set(new_cats)
               if len(added_cats) > 0:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Added Category: ',
                     labels_list(website, file, added_cats)
                  ]))
               if len(removed_cats) > 0:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Removed Category: ',
                     labels_list(website, file, removed_cats)
                  ]))
               categories = new_cats
            case 'Confirmation Status':
               history_items.append(new_content_tag(soup, 'p', [
                  'Confirmation Status: ',
                  field_link(website, file, website.confirmation_folder, item['fromString']),
                  ' → ',
                  field_link(website, file, website.confirmation_folder, item['toString'])
               ]))
            case 'Area':
               if item['to'] is not None and item['from'] is not None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Area: ',
                     field_link(website, file, website.areas_folder, item['fromString']),
                     ' → ',
                     field_link(website, file, website.areas_folder, item['toString'])
                  ]))
               elif item['to'] is None and item['from'] is not None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Removed Area: ',
                     field_link(website, file, website.areas_folder, item['fromString'])
                  ]))
               elif item['from'] is None and item['from'] is None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Added Area: ',
                     field_link(website, file, website.areas_folder, item['toString'])
                  ]))
            case 'Mojang Priority':
               if item['to'] is not None and item['from'] is not None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Mojang Priority: ',
                     field_link(website, file, website.priorities_folder, item['fromString']),
                     ' → ',
                     field_link(website, file, website.priorities_folder, item['toString'])
                  ]))
               elif item['to'] is None and item['from'] is not None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Removed Mojang Priority: ',
                     field_link(website, file, website.priorities_folder, item['fromString'])
                  ]))
               elif item['from'] is None and item['from'] is None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Added Mojang Priority: ',
                     field_link(website, file, website.priorities_folder, item['toString'])
                  ]))
            case 'resolution':
               history_items.append(new_content_tag(soup, 'p', [
                  'Resolution: ',
                  resolution_link(website, file, item['from']),
                  ' → ',
                  resolution_link(website, file, item['to']),
               ]))
            case 'security':
               history_items.append(new_content_tag(soup, 'p', [
                  'Security Level: ',
                  new_content_tag(soup, 'span', attrs={'class': 'status-badge'}, content=item['fromString']),
                  ' → ',
                  new_content_tag(soup, 'span', attrs={'class': 'status-badge'}, content=item['toString'])
               ]))
            case 'Link':
               if item['to'] is not None:
                  link_dir = item['toString'][len('This issue '):-(len(item['to']) + 1)]
                  relevant_issue = website.archive.get_issue_data(website.relations.issue_keys[item['to']])
                  history_items.append(new_content_tag(soup, 'p', [
                     'Added a link: ',
                     link_dir,
                     ' ',
                     issue_link(website, file, relevant_issue, with_summary=True)
                  ]))
               if item['from'] is not None:
                  link_dir = item['fromString'][len('This issue '):-(len(item['from']) + 1)]
                  relevant_issue = website.archive.get_issue_data(website.relations.issue_keys[item['from']])
                  history_items.append(new_content_tag(soup, 'p', [
                     'Removed a link: ',
                     link_dir,
                     ' ',
                     issue_link(website, file, relevant_issue, with_summary=True)
                  ]))
            case 'Version':
               if item['to'] is not None:
                  versions_added.append((item['to'], item['toString']))
               if item['from'] is not None:
                  versions_removed.append((item['from'], item['fromString']))
            case 'Fix Version':
               if item['to'] is not None:
                  fix_versions_added.append((item['to'], item['toString']))
               if item['from'] is not None:
                  fix_versions_removed.append((item['from'], item['fromString']))
            case 'assignee':
               if item['to'] is not None and item['from'] is not None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Assignee: ',
                     user_link(website, file, item['from']),
                     ' → ',
                     user_link(website, file, item['to'])
                  ]))
               elif item['to'] is None and item['from'] is not None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Removed assignee: ',
                     user_link(website, file, item['from'])
                  ]))
               elif item['from'] is None and item['from'] is None:
                  history_items.append(new_content_tag(soup, 'p', [
                     'Added assignee: ',
                     user_link(website, file, item['to'])
                  ]))
            case 'reporter':
               history_items.append(new_content_tag(soup, 'p', [
                  'Reporter: ',
                  user_link(website, file, item['from']),
                  ' → ',
                  user_link(website, file, item['to'])
               ]))
            case 'status' | 'Linked' | 'RemoteIssueLink' | 'CHK' | 'Pinned' | 'Workflow':
               pass
            case _:
               print(item['field'])
               history_items.append(new_content_tag(soup, 'p', item['field']))
      project = website.metas.projects[issue['fields']['project']]
      if len(versions_added) > 0:
         history_items.append(new_content_tag(soup, 'p', [
            'Added affects versions: ',
            inline_list(file.page.soup, map(lambda x: version_link(website, file, project, project['versions'][x[0]]) if x[0] in project['versions'] else x[1], versions_added))
         ]))
      if len(versions_removed) > 0:
         history_items.append(new_content_tag(soup, 'p', [
            'Removed affects versions: ',
            inline_list(file.page.soup, map(lambda x: version_link(website, file, project, project['versions'][x[0]]) if x[0] in project['versions'] else x[1], versions_removed))
         ]))
      if len(fix_versions_added) > 0:
         history_items.append(new_content_tag(soup, 'p', [
            'Added fixed versions: ',
            inline_list(file.page.soup, map(lambda x: version_link(website, file, project, project['versions'][x[0]]) if x[0] in project['versions'] else x[1], fix_versions_added))
         ]))
      if len(fix_versions_removed) > 0:
         history_items.append(new_content_tag(soup, 'p', [
            'Removed fixed versions: ',
            inline_list(file.page.soup, map(lambda x: version_link(website, file, project, project['versions'][x[0]]) if x[0] in project['versions'] else x[1], fix_versions_removed))
         ]))
      if len(history_items) > 0:
         revisions_list.append(new_content_tag(soup, 'div', attrs={'class': 'history-entry'}, content=[
            user_link(website, file, revision['author']),
            render_datetime(soup, revision['created']),
            new_content_tag(soup, 'div', attrs={'class': 'history-entry-items'}, content=history_items)
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

def render_issue_comments(website: Website, file: HtmlFile, comments: list[tuple[Comment, bs4.BeautifulSoup]]) -> bs4.Tag:
   soup = file.page.soup
   comments_list: list[bs4.Tag] = []
   def comment_author(user_key: str) -> bs4.Tag:
      user_tag = user_link(website, file, user_key)
      user_text = user_tag if 'username' in user_tag.attrs['class'] else user_tag.find(class_='username')
      assert user_text is not None
      user_text.attrs['class'] = 'username comment-author'
      return user_tag
   def comment_time(date_str: str) -> bs4.Tag:
      tag = render_datetime(soup, date_str)
      return new_content_tag(soup, 'a', attrs={'class': 'comment-time', 'href': f'#comment-id-{entry['id']}'}, content=tag)
   for entry, body in comments:
      header = soup.new_tag('div', attrs={'class': 'comment-header'})
      header1tags: list[bs4.Tag | str] = []
      header2tags: list[bs4.Tag | str] = []
      if 'author' in entry:
         header1tags.append(comment_author(entry['author']))
      header1tags.append(' ')
      header1tags.append(comment_time(entry['created']))
      if 'updateAuthor' in entry and ('author' not in entry or entry['updateAuthor'] != entry['author']):
         header2tags.append(comment_author(entry['updateAuthor']))
      if entry['updated'] != entry['created']:
         if len(header2tags) > 0:
            header2tags.append(' ')
         header2tags.append(new_content_tag(soup, 'span', 'edited ', attrs={'class': 'comment-time'}))
         header2tags.append(comment_time(entry['updated']))
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

def render_issue_attachments(website: Website, file: HtmlFile, attachments: list[str]) -> bs4.Tag:
   soup = file.page.soup
   attach_list: list[bs4.Tag] = []
   for entry in attachments:
      attach_info = website.archive.get_attachment_data(entry)
      assert attach_info is not None
      preview = attachment_preview(website, file, attach_info)
      if preview is None:
         continue
      attach_div = new_content_tag(soup, 'div', attrs={'class': 'attachment'}, content=[
         preview,
         new_content_tag(soup, 'p', content=attach_info['filename'])
      ])
      attach_list.append(attach_div)
      if 'author' in attach_info:
         attach_div.append(
            new_content_tag(soup, 'p', content=user_link(website, file, attach_info['author']))
         )
      attach_div.append(
         new_content_tag(soup, 'p', content=render_datetime(soup, attach_info['created']))
      )
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
      new_content_tag(soup, 'label', 'Status:'),
      resolution_link(website, file, fields['resolution'])
   )
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Reporter:'),
      user_link(website, file, fields['reporter'])
   )
   if fields['reporter'] != fields['creator']:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Creator:'),
         user_link(website, file, fields['creator'])
      )
   if 'assignee' in fields and fields['assignee'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Assignee:'),
         user_link(website, file, fields['assignee'])
      )
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Created:'),
      render_datetime(soup, fields['created'])
   )
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Updated:'),
      render_datetime(soup, fields['updated'])
   )
   if 'customfield_12201'in fields and fields['customfield_12201'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Triaged:'),
         render_datetime(soup, fields['customfield_12201'])
      )
   if fields['resolutiondate'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Resolved:'),
         render_datetime(soup, fields['resolutiondate'])
      )
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Votes:'),
      new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(fields['votes']['votes']))
   )
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Watchers:'),
      new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(fields['watches']['watchCount']))
   )
   if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Confirmation Status:'),
         field_link(website, file, website.confirmation_folder, fields['customfield_10500']['value'])
      )
   if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Mojang Priority:'),
         field_link(website, file, website.priorities_folder, fields['customfield_12200']['value'])
      )
   if 'customfield_11500' in fields and fields['customfield_11500'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'ADO:'),
         fields['customfield_11500']
      )
   if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Area:'),
         field_link(website, file, website.areas_folder, fields['customfield_12800']['value'])
      )
   if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
      category_list = inline_list(soup, map(lambda x: field_link(website, file, website.categories_folder, x['value']), fields['customfield_11901']))
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Category:'),
         category_list
      )
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Labels:'),
      labels_list(website, file, fields['labels'])
   )
   if 'versions' in fields:
      versions = list(map(lambda x: project['versions'][x], fields['versions']))
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Affects Versions:'),
         render_version_list(website, file, project, versions)
      )
   if 'fixVersions' in fields:
      versions = list(map(lambda x: project['versions'][x], fields['fixVersions']))
      append_desc_item(soup, issue_details,
         new_content_tag(soup, 'label', 'Fix Versions:'),
         render_version_list(website, file, project, versions)
      )
   data_link = relative_path(website.root, file.path, website.archive.get_issue_path(issue['id']))
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Links:'),
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
   labels_list = inline_list(file.page.soup, map(lambda x: new_content_tag(file.page.soup, 'a', x, attrs={'class': 'status-badge', 'href': relative_link(website.root, file.path, website.labels_folder / (urllib.parse.quote_plus(x) + '.html'))}), labels))
   labels_list.attrs['class'] = 'labels-list'
   return labels_list

def attachment_preview(website: Website, file: HtmlFile, attachment: Attachment) -> bs4.Tag | None:
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   link = relative_link(website.root, file.path, attach_path)
   if attachment['mimeType'].startswith('image/'):
      return new_content_tag(file.page.soup, 'a', attrs={'href': link}, content=[
         file.page.soup.new_tag('img', attrs={'src': link, 'alt': attachment['filename'], 'loading': 'lazy'})
      ])
   if attachment['mimeType'].startswith('video/'):
      return file.page.soup.new_tag('video', attrs={'src': link, 'alt': attachment['filename'], 'loading': 'lazy'})
   return None

def inline_list(soup: bs4.BeautifulSoup, items: typing.Iterator[bs4.Tag]) -> bs4.Tag:
   span = soup.new_tag('span')
   try:
      first = next(items)
   except StopIteration:
      return span
   span.append(first)
   for item in items:
      span.append(' ')
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
      tag = field_link(website, file, website.resolutions_folder, 'Unresolved')
      return tag
   else:
      name = website.metas.resolutions[resolution_id]['name']
      tag = field_link(website, file, website.resolutions_folder, name)
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
