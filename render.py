import dataclasses
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
   resolutions_folder: pathlib.PurePath
   archive: mojira.Archive
   metas: mojira.ArchiveMetas
   relations: relations.Relations
   markup_folder: pathlib.Path

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
   website = Website(
      root=root,
      project_list=make_jira_file(root, pathlib.PurePath('web/index.html'), 'Mojira Archive'),
      project_folder=pathlib.PurePath('web/projects'),
      issues_folder=pathlib.PurePath('web/issues'),
      users_folder=pathlib.PurePath('web/users'),
      resolutions_folder=pathlib.PurePath('web/resolutions'),
      archive=archive,
      metas=metas,
      relations=rels,
      markup_folder=root / 'markup'
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
      issues = create_project_issues_page(website, project)
      save_file(website, issues)
   for project_id, project in metas.projects.items():
      project_key = project['key']
      print(project_key)
      issues = rels.projects[project_id]
      for issue_id in issues:
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
   table = make_table(soup, ['Project', 'Name', 'Issues', 'Versions'])
   for project_id, project in website.metas.projects.items():
      issues = website.relations.projects[project_id]
      versions = project['versions']
      project_key = project_link(website, file, project)
      append_row(soup, table, [
         project_key,
         project['name'],
         new_content_tag(soup, 'a', str(len(issues)), attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'issues.html')}),
         new_content_tag(soup, 'a', str(len(versions)), attrs={'href': relative_link(website.root, file.path, website.project_folder / project['key'] / 'versions.html')}),
      ])
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
   table = make_table(soup, ['Name', 'Description', 'Date', 'Affected Issues', 'Fixed Issues'])
   versions = project['versions']
   for version_key, version in versions.items():
      rel_ver = website.relations.versions.get(version_key, {})
      append_row(soup, table, [
         version['name'],
         version['description'] if 'description' in version else '',
         render_date(version['releaseDate']) if 'releaseDate' in version else '',
         str(len(rel_ver['affected'])) if 'affected' in rel_ver else '',
         str(len(rel_ver['fixed'])) if 'fixed' in rel_ver else '',
      ])
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
   table = make_table(soup, ['Issue', 'Summary', 'Reporter', 'Created'])
   issues = website.relations.projects[project['id']]
   for i, issue_key in enumerate(issues):
      if i % 1000 == 0 or i == len(issues) - 1:
         print(f'{i + 1} / {len(issues)}')
      issue = website.archive.get_issue_data(issue_key)
      assert issue is not None
      reporter = user_link(website, file, issue['fields']['reporter'])
      date = render_datetime(issue['fields']['created'])
      link = new_content_tag(soup, 'a', issue['key'], attrs={'href': relative_link(website.root, file.path, website.issues_folder / (issue['key'] + '.html'))})
      append_row(soup, table, [link, issue['fields']['summary'], reporter, date])
   content.append(table)
   file.page.body.append(content)
   return file

def create_issue_page(website: Website, issue: Issue):
   key = issue['key']
   fields = issue['fields']
   summary = fields['summary']
   full_title = f'[{key}] {summary}'
   file = make_jira_file(website.root, website.issues_folder / (key + '.html'), full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   summary_div = soup.new_tag('div', attrs={'class': 'summary'})
   header = new_content_tag(soup, 'h1', [
      new_content_tag(soup, 'a', 'Mojira', attrs={'href': relative_link(website.root, file.path, website.project_list.path)}),
      ' / ',
      project_link(website, file, website.metas.projects[fields['project']]),
      ' / ',
      new_content_tag(soup, 'a', key, attrs={'href': f'https://bugs.mojang.com/browse/{key}'})
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
   if 'versions' in issue['fields']:
      append_desc_item(soup, details, 'Affects Versions', render_version_list())
   if 'fixVersions' in issue['fields']:
      append_desc_item(soup, details, 'Fixed Versions', render_version_list())

   details_div = new_content_tag(soup, 'div', fields2, attrs={'class': 'details'})
   content.append(details_div)
   file.page.body.append(content)
   return file

   file.write('<div class="details"><dl>')
   if 'versions' in issue['fields']:
      version_list = render_version_list(archive, archive.projects[issue['fields']['project']], issue['fields']['versions'], depth=1)
      file.write(f'<dt>Affects Versions</dt><dd>{version_list}</dd>')
   if 'fixVersions' in issue['fields']:
      fixed_list = render_version_list(archive, archive.projects[issue['fields']['project']], issue['fields']['fixVersions'], depth=1)
      file.write(f'<dt>Fixed Versions</dt><dd>{fixed_list}</dd>')
   file.write(f'<dt>Labels</dt><dd>{'-' if len(issue['fields']['labels']) == 0 else ', '.join([f'<a href="../labels/{escape(x)}.html"><code>{escape(x)}</code></a>' for x in issue['fields']['labels']])}</dd>')
   if issue['fields'].get('customfield_11901') is not None:
      file.write(f'<dt>Category</dt><dd>{'-' if len(issue['fields']['customfield_11901']) == 0 else ', '.join([f'<a href="../category/{escape(x['value'])}.html">{escape(x['value'])}</a>' for x in issue['fields']['customfield_11901']])}</dd>')
   if issue['fields'].get('customfield_12800') is not None:
      area_val = issue['fields']['customfield_12800']['value']
      file.write(f'<dt>Area</dt><dd><a href="../area/{area_val}.html">{escape(area_val)}</a></dd>')
   if issue['fields'].get('customfield_12200') is not None:
      prio_val = issue['fields']['customfield_12200']['value']
      file.write(f'<dt>Mojang Priority</dt><dd><a href="../priority/{prio_val}.html">{escape(prio_val)}</a></dd>')
   file.write('</dl></div><hr/>')
   desc = issue['fields']['description']
   if desc is not None:
      rendered_summary = markup.convert(markup_proc, desc, issue['id'])
      file.write(f'<div class="description">{rendered_summary}</div>')
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

def resolution_link(website: Website, file: HtmlFile, resolution: str | None) -> bs4.Tag:
   if resolution is None:
      resid = '0'
      resname = 'Unresolved'
   else:
      resolution_obj = website.metas.resolutions[resolution]
      resid = resolution_obj['id']
      resname = resolution_obj['name']
   return new_content_tag(file.page.soup, 'a', resname, attrs={'href': relative_link(website.root, file.path, website.resolutions_folder / (resid + '.html'))})

def render_datetime(date_str: str) -> str:
   return datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M')

def render_date(date_str: str) -> str:
   return datetime.date.fromisoformat(date_str).strftime('%Y-%m-%d')


def render_version_list(archive: mojira.Archive, project: Project, versions: list[str], depth: int) -> bs4.Tag | str:
   version_objs = map(lambda x: project['versions'][x], versions)
   version_objs = sorted(version_objs, key=lambda x: int(x['id']))
   version_objs = list(version_objs)
   if len(version_objs) == 0:
      return '-'
   if len(version_objs) == 1:
      return render_version(version_objs[0], depth=depth)
   if len(version_objs) <= 4:
      return ', '.join([render_version(x, depth=depth) for x in version_objs])
   first_version = version_objs[0]
   last_version = version_objs[-1]
   return f'<details><summary>{render_version(first_version, depth=depth)} - {render_version(last_version, depth=depth)} ({len(version_objs)} versions)</summary>{', '.join([render_version(x, depth=depth) for x in version_objs])}</details>'

def render_version(version, depth: int):
   depth_str = '../' * depth
   return f'<a href="{depth_str}versions/{escape(version['name'])}.html">{escape(version['name'])}</a>'

def render_comment(archive, issue, comment, file, markup_proc):
   file.write('<div class="comment">')
   file.write(f'<details open><summary>{user_link(archive, comment.get('author'), depth=1)} - <span class="subtle">{render_datetime(comment['created'])}</span></summary><div class="comment-content">')
   rendered_text = markup.convert(markup_proc, comment['body'], issue['id'])
   file.write(rendered_text)
   file.write('</div></details></div>')

if __name__ == '__main__':
   main()
