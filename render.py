import dataclasses
import typing
from jiratypes import Issue, Project, Version
import mojira
import relations
import pathlib
import datetime
import urllib.parse
import markup
import bs4
from web import HtmlFile, append_desc_item, append_row, make_desc_list, make_file, make_table, new_content_tag, relative_link, relative_path, write_html

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   project_list: HtmlFile
   project_folder: pathlib.PurePath
   issues_folder: pathlib.PurePath
   users_folder: pathlib.PurePath
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
      append_desc_item(soup, fields, 'Date', render_date(version['releaseDate']))
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
         render_date(version['releaseDate']) if 'releaseDate' in version else '',
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
      date = render_datetime(issue['fields']['created'])
      link = new_content_tag(file.page.soup, 'a', issue['key'], attrs={'href': relative_link(website.root, file.path, website.issues_folder / (issue['key'] + '.html'))})
      append_row(file.page.soup, table, [link, issue['fields']['summary'], reporter, date])
   return table

def create_issue_page(website: Website, issue: Issue) -> HtmlFile:
   key = issue['key']
   fields = issue['fields']
   summary = fields['summary']
   full_title = f'[{key}] {summary}'
   project = website.metas.projects[fields['project']]
   file = make_jira_file(website.root, website.issues_folder / (key + '.html'), full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   summary_div = soup.new_tag('div', attrs={'class': 'summary'})
   header = new_content_tag(soup, 'h1', [
      new_content_tag(soup, 'a', 'Mojira', attrs={'href': relative_link(website.root, file.path, website.project_list.path)}),
      ' / ',
      project_link(website, file, project),
      ' / ',
      issue_link(website, file, issue)
   ])
   summary_div.append(header)
   summary_div.append(new_content_tag(soup, 'h2', summary))
   content.append(summary_div)
   fields_div = soup.new_tag('div', attrs={'class': 'fields'})
   fields1 = make_desc_list(soup)
   append_desc_item(soup, fields1, 'Reporter', user_link(website, file, fields['reporter']))
   if fields['reporter'] != fields['creator']:
      append_desc_item(soup, fields1, 'Creator', user_link(website, file, fields['creator']))
   if 'assignee' in fields and fields['assignee'] is not None:
      append_desc_item(soup, fields1, 'Assigned to', user_link(website, file, fields['assignee']))
   append_desc_item(soup, fields1, 'Votes', str(fields['votes']['votes']))
   append_desc_item(soup, fields1, 'Watchers', str(fields['watches']['watchCount']))
   if fields['resolutiondate'] is not None:
      append_desc_item(soup, fields1, 'Resolved', render_datetime(fields['resolutiondate']))
   fields_div.append(new_content_tag(soup, 'div', fields1, attrs={'class': 'field-section'}))
   fields2 = make_desc_list(soup)
   if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
      append_desc_item(soup, fields2, 'Confirmation Status', fields['customfield_10500']['value'])
   append_desc_item(soup, fields2, 'Resolution', resolution_link(website, file, fields['resolution']))
   append_desc_item(soup, fields2, 'Created', render_datetime(fields['created']))
   append_desc_item(soup, fields2, 'Updated', render_datetime(fields['updated']))
   fields_div.append(new_content_tag(soup, 'div', fields2, attrs={'class': 'field-section'}))
   content.append(fields_div)
   details = make_desc_list(soup)
   if 'versions' in fields:
      versions = list(map(lambda x: project['versions'][x], fields['versions']))
      append_desc_item(soup, details, 'Affects Versions', render_version_list(website, file, project, versions))
   if 'fixVersions' in fields:
      versions = list(map(lambda x: project['versions'][x], fields['fixVersions']))
      append_desc_item(soup, details, 'Fixed Versions', render_version_list(website, file, project, versions))
   labels_list = inline_list(soup, map(lambda x: new_content_tag(soup, 'a', x, attrs={'href': relative_link(website.root, file.path, website.labels_folder / (urllib.parse.quote_plus(x) + '.html'))}), fields['labels']))
   append_desc_item(soup, details, 'Labels', '-' if len(fields['labels']) == 0 else labels_list)
   if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
      category_list = inline_list(soup, map(lambda x: field_link(website, file, website.categories_folder, x['value']), fields['customfield_11901']))
      append_desc_item(soup, details, 'Category', '-' if len(fields['customfield_11901']) == 0 else category_list)
   if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
      append_desc_item(soup, details, 'Area', field_link(website, file, website.areas_folder, fields['customfield_12800']['value']))
   if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
      append_desc_item(soup, details, 'Mojang Priority', field_link(website, file, website.priorities_folder, fields['customfield_12200']['value']))
   details_div = new_content_tag(soup, 'div', details, attrs={'class': 'details'})
   content.append(details_div)
   content.append(soup.new_tag('hr'))
   if fields['description'] is not None:
      desc = website.markup_source.get_issue_description(issue['id'])
      content.append(new_content_tag(soup, 'div', desc, attrs={'class': 'description'}))
   file.page.body.append(content)
   return file

   file.write('<hr/><div class="links">')
   link_types = {}
   issue_links = issue['fields']['issuelinks']
   for link in issue_links:
      identity = (link['type'], 'inwardIssue' in link)
      if identity not in link_types:
         link_types[identity] = []
      link_types[identity].append(link)
   for (ltype,inward),links in link_types.items():
      link_desc = (archive.link_types[ltype])['inward' if inward else 'outward']
      if len(links) <= 5:
         num = 'issue' if len(links) == 1 else 'issues'
         file.write(f'<span class="subtle">{escape(link_desc)}:</span> {len(links)} {num}<ul class="link-list">')
         for link in links:
            relevant_ticket = archive.get_issue_data(link['inwardIssue' if inward else 'outwardIssue'])
            file.write(f'<li>{render_ticket_link(relevant_ticket, depth=1)}</li>')
         file.write('</ul>')
      else:
         file.write(f'<details><summary><span class="subtle">{escape(link_desc)}:</span> {len(links)} issues</summary><ul class="link-list">')
         for link in links:
            relevant_ticket = archive.get_issue_data(link['inwardIssue' if inward else 'outwardIssue'])
            file.write(f'<li>{render_ticket_link(relevant_ticket, depth=1)}</li>')
         file.write('</ul></details>')
   file.write('</div><hr/><div class="comment-section">')
   for comment in issue['fields']['comment']['comments']:
      render_comment(archive, issue, comment, file, markup_proc)
   file.write('</div></body></html>')

def inline_list(soup: bs4.BeautifulSoup, items: typing.Iterable[bs4.Tag]) -> bs4.Tag:
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

def resolution_link(website: Website, file: HtmlFile, resolution_id: str | None) -> bs4.Tag:
   if resolution_id is None:
      name = 'Unresolved'
   else:
      name = website.metas.resolutions[resolution_id]['name']
   return field_link(website, file, website.resolutions_folder, name)

def render_datetime(date_str: str) -> str:
   return datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M')

def render_date(date_str: str) -> str:
   return datetime.date.fromisoformat(date_str).strftime('%Y-%m-%d')

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

def render_comment(archive, issue, comment, file, markup_proc):
   file.write('<div class="comment">')
   file.write(f'<details open><summary>{user_link(archive, comment.get('author'), depth=1)} - <span class="subtle">{render_datetime(comment['created'])}</span></summary><div class="comment-content">')
   rendered_text = markup.convert(markup_proc, comment['body'], issue['id'])
   file.write(rendered_text)
   file.write('</div></details></div>')

if __name__ == '__main__':
   main()
