import dataclasses
import typing
from jiratypes import Attachment, Issue, Project, Version
import mojira
import relations
import pathlib
import datetime
import urllib.parse
import markup
import bs4
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
   print('Starting...')
   root = pathlib.Path('/d/Archives/Mojira')
   archive = mojira.Archive(folder=root / 'data')
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   rels = relations.Relations()
   rels.load(root / 'relations')
   markup_source = markup.MarkupSource(root / 'markup')
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
      markup_source=markup_source
   )

   file = create_issue_page(website, archive.get_issue_data(rels.issue_keys['MC-4']))
   save_file(website, file)
   return

   print('Rendering...')
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
   project = website.metas.projects[fields['project']]

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
   issue_body = soup.new_tag('main', attrs={'class': 'issue-body'})
   issue_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-split'}, content=[
      issue_body,
      issue_details
   ]))
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
   labels_list = inline_list(soup, map(lambda x: new_content_tag(soup, 'a', x, attrs={'href': relative_link(website.root, file.path, website.labels_folder / (urllib.parse.quote_plus(x) + '.html'))}), fields['labels']))
   append_desc_item(soup, issue_details,
      new_content_tag(soup, 'label', 'Labels:'),
      labels_list
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
   if fields['description'] is not None:
      desc = website.markup_source.get_issue_description(issue['id'])
      desc_text = html_to_text(desc)
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-description'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=desc)
      ]))
      file.page.head.append(soup.new_tag('meta', attrs={'name': 'description', 'content': desc_text}))
      file.page.head.append(soup.new_tag('meta', attrs={'property': 'og:description', 'content': desc_text}))
      file.page.head.append(soup.new_tag('meta', attrs={'property': 'twitter:description', 'content': desc_text}))
   if 'environment' in fields and fields['environment'] is not None:
      env = website.markup_source.get_issue_environment(issue['id'])
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-environment-section issue-body'}, content=[
         new_content_tag(soup, 'h2', 'Environment'),
         new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=env)
      ]))
   link_types: dict[str, list[Issue]] = {}
   for link in issue['fields']['issuelinks']:
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
   if len(link_types) > 0:
      issue_comments = new_content_tag(soup, 'div', attrs={'class': 'issue-link-section issue-body'}, content=[
         new_content_tag(soup, 'h2', 'Linked Issues')
      ])
      issue_body.append(issue_comments)
      for link_desc, issues in link_types.items():
         link_block = new_content_tag(soup, 'div', attrs={'class': 'issue-links-category'}, content=[
            new_content_tag(soup, 'h3', attrs={'class': 'issue-link-type'}, content=[
               link_desc,
               new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issues)))
            ])
         ])
         issue_comments.append(link_block)
         link_list = soup.new_tag('div', attrs={'class': 'issue-links-list'})
         link_block.append(link_list)
         for linked_issue in issues:
            link_list.append(big_issue_link(website, file, linked_issue))
   if len(issue['fields']['attachment']) > 0:
      issue_attaches = new_content_tag(soup, 'div', attrs={'class': 'issue-attachment-section issue-body'}, content=[
         new_content_tag(soup, 'h2', [
            'Attachments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issue['fields']['attachment'])))
         ])
      ])
      issue_body.append(issue_attaches)
      attach_list = soup.new_tag('div', attrs={'class': 'attachments'})
      issue_body.append(attach_list)
      for entry in issue['fields']['attachment']:
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
   if len(issue['fields']['comment']['comments']) > 0:
      issue_comments = new_content_tag(soup, 'div', attrs={'class': 'issue-comment-section issue-body'}, content=[
         new_content_tag(soup, 'h2', [
            'Comments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issue['fields']['comment']['comments'])))
         ])
      ])
      issue_body.append(issue_comments)
      for entry in issue['fields']['comment']['comments']:
         header = soup.new_tag('div', attrs={'class': 'comment-head'})
         if 'author' in entry:
            header.append(user_link(website, file, entry['author']))
         header.append(render_datetime(soup, entry['created']))
         if 'updateAuthor' in entry and ('author' not in entry or entry['updateAuthor'] != entry['author']):
            header.append(user_link(website, file, entry['updateAuthor']))
         if entry['updated'] != entry['created']:
            header.append(render_datetime(soup, entry['updated']))
         comment_div = new_content_tag(soup, 'div', attrs={'class': 'comment'}, content=[
            soup.new_tag('div', attrs={'class': 'anchor', 'id': f'comment-id-{entry['id']}'}),
            header
         ])
         body = website.markup_source.get_comment_body(issue['id'], entry['id'])
         comment_div.append(new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=[
            new_content_tag(soup, 'div', attrs={'class': 'adf'}, content=body)
         ]))
         issue_comments.append(comment_div)
   return file

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
      span.append(', ')
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

def issue_link(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   key = issue['key']
   linkpart = new_content_tag(file.page.soup, 'a', key, attrs={'href': relative_link(website.root, file.path, website.issues_folder / (key + '.html'))})
   if issue['fields']['resolution'] is not None:
      linkpart.attrs['class'] = 'resolved'
   return new_content_tag(file.page.soup, 'span', [linkpart, ' ', issue['fields']['summary']])

def user_link(website: Website, file: HtmlFile, user_key: str | None) -> str | bs4.Tag:
   if user_key is None:
      return '-'
   user_data = website.archive.get_user_data(user_key)
   if user_data is None:
      return user_key
   display_name = user_data['displayName']
   avatar_url = user_data['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.users_avatars_folder, avatar_url)
   img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy'})
   if avatar_path is not None:
      img['src'] = str(relative_path(website.root, file.path, avatar_path))
   return new_content_tag(file.page.soup, 'a', [
      new_content_tag(file.page.soup, 'span', [
         new_content_tag(file.page.soup, 'span', [
            img
         ], attrs={'class': 'aui-avatar aui-avatar-small'}),
         display_name
      ], attrs={'class':'username'})
   ], attrs={'class':'user-hover', 'rel': user_data['name'], 'href': relative_link(website.root, file.path, website.users_folder / (urllib.parse.quote_plus(user_key) + '.html'))})

def field_link(website: Website, file: HtmlFile, folder: pathlib.PurePath, value: str) -> bs4.Tag:
   return new_content_tag(file.page.soup, 'a', value, attrs={'href': relative_link(website.root, file.path, folder / (urllib.parse.quote_plus(value) + '.html'))})

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
      name = 'Unresolved'
      cls = 'status-badge'
   else:
      name = website.metas.resolutions[resolution_id]['name']
      cls = 'status-badge issue-resolved'
   result = field_link(website, file, website.resolutions_folder, name)
   result.attrs['class'] = cls
   return result

def render_datetime(soup: bs4.BeautifulSoup, date_str: str) -> bs4.Tag:
   formatted = datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d, %I:%M %p')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': date_str})

def render_date(soup: bs4.BeautifulSoup, date_str: str) -> bs4.Tag:
   formatted = datetime.date.fromisoformat(date_str).strftime('%Y-%m-%d')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': date_str})

def render_version_list(website: Website, file: HtmlFile, project: Project, versions: list[Version]) -> bs4.Tag | str:
   if len(versions) == 0:
      return '-'
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
   return new_content_tag(file.page.soup, 'a', version['name'], attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'versions' / (urllib.parse.quote_plus(version['name']) + '.html'))})

if __name__ == '__main__':
   main()
