import dataclasses
from jiratypes import Project
import mojira
import pathlib
import datetime
import urllib.parse
import markup
from web import HtmlFile, append_row, make_file, make_table, new_content_tag, relative_link, relative_path, write_html

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   project_list: HtmlFile
   project_folder: pathlib.PurePath
   ticket_folder: pathlib.PurePath
   user_folder: pathlib.PurePath
   archive: mojira.Archive
   metas: mojira.ArchiveMetas

def make_jira_file(root: pathlib.Path, path: pathlib.PurePath, title: str) -> HtmlFile:
   file = make_file(path, title)
   file.page.head.append(file.page.soup.new_tag('link', rel='icon', type='image/x-icon', href=relative_link(root, file.path, pathlib.PurePath('dump/assets/favicon.ico'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('dump/assets/mojira.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('render/style.css'))))
   file.page.head.append(file.page.soup.new_tag('script', src=relative_link(root, file.path, pathlib.PurePath('render/script.js'))))
   return file

def save_file(website: Website, file: HtmlFile):
   write_html(website.root / file.path, file.page)

def main():
   print('Starting...')
   root = pathlib.Path('/d/Archives/Mojira')
   archive = mojira.Archive(folder=root / 'data')
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   website = Website(
      root=root,
      project_list=make_jira_file(root, pathlib.PurePath('render/index.html'), 'Mojira Archive'),
      project_folder=pathlib.PurePath('render/projects'),
      ticket_folder=pathlib.PurePath('render/issues'),
      user_folder=pathlib.PurePath('render/users'),
      archive=archive,
      metas=metas
   )
   print('Rendering...')
   make_projects(website, website.project_list)
   save_file(website, website.project_list)
   for project_id, project in metas.projects.items():
      project_key = project['key']
      print(project_key)
      file = create_project_page(website, project)
      save_file(website, file)
   for project_id, project in archive.projects.items():
      project_key = project['key']
      print(project_key)
      tickets = archive.relations_cache['projects'][project_id]
      for ticket_id in tickets:
         ticket_data = archive.get_issue_data(ticket_id)
         assert ticket_data is not None
         file = create_issue_page(website, ticket)
         save_file(website, file)

def make_projects(website: Website, file: HtmlFile):
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   content.append(new_content_tag(soup, 'div', [
      new_content_tag(soup, 'h1', 'Mojira Archive')
   ], attrs={'class': 'title'}))
   table = make_table(soup, ['Project', 'Name', 'Issues', 'Versions'])
   for project_id, project in website.archive.projects.items():
      tickets = website.archive.relations_cache['projects'][project_id]
      versions = project['versions']
      project_key = project_link(website, file, project)
      append_row(soup, table, [project_key, project['name'], str(len(tickets)), str(len(versions))])
   content.append(table)
   file.page.body.append(content)

def create_project_page(website: Website, project: Project):
   project_key = project['key']
   project_name = project['name']
   full_title = f'[{project_key}] {project_name}'
   file = make_jira_file(website.root, website.project_folder / (project_key + '.html'), full_title)
   soup = file.page.soup
   content = soup.new_tag('div', attrs={'class': 'content'})
   content.append(new_content_tag(soup, 'div', [
      new_content_tag(soup, 'h1', [
         new_content_tag(soup, 'a', 'Projects', attrs={'href': relative_link(website.root, file.path, website.project_list.path)}),
         ' / ',
         new_content_tag(soup, 'a', project_key, attrs={'href': f'https://bugs.mojang.com/projects/{project_key}/summary'}),
      ])
   ], attrs={'class': 'title'}))
   lead = user_link(website, file, project['lead'])
   content.append(lead)
   desc = new_content_tag(soup, 'div', [project['description']], attrs={'class': 'project-desc'})
   content.append(desc)
   table = make_table(soup, ['Issues', 'Summary', 'Reporter', 'Created'])
   project_tickets = website.archive.relations_cache['projects'][project['id']]
   for i, issue_key in enumerate(project_tickets):
      if i % 1000 == 0 or i == len(project_tickets) - 1:
         print(f'{i + 1} / {len(project_tickets)}')
      data = website.archive.get_issue_data(issue_key)
      assert data is not None
      reporter = user_link(website, file, data['fields']['reporter'])
      date = render_date(data['fields']['created'])
      link = new_content_tag(soup, 'a', data['key'], attrs={'href': relative_link(website.root, file.path, website.ticket_folder / (data['key'] + '.html'))})
      append_row(soup, table, [link, data['fields']['summary'], reporter, date])
   content.append(table)
   file.page.body.append(content)
   return file

def get_avatar_path(archive: mojira.Archive, folder: pathlib.Path, url: str):
   avatar_id = archive.get_avatar_id(url)
   avatar_file = folder / (avatar_id + '.png')
   if avatar_file.exists():
      return avatar_file
   avatar_file = folder / (avatar_id + '.svg')
   if avatar_file.exists():
      return avatar_file
   return None

def project_link(website: Website, file: HtmlFile, project: Project):
   key = project['key']
   avatar_url = project['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.project_avatars_folder, avatar_url)
   return new_content_tag(file.page.soup, 'a', [
      new_content_tag(file.page.soup, 'span', [
         new_content_tag(file.page.soup, 'span', [
            file.page.soup.new_tag('img', attrs={'src': str(relative_path(website.root, file.path, avatar_path)), 'width': '32', 'height': '32'})
         ], attrs={'class': 'project-avatar'}),
         key
      ], attrs={'class':'project-key'})
   ], attrs={'href': relative_link(website.root, file.path, website.project_folder / (key + '.html'))})

def user_link(website: Website, file: HtmlFile, user_key: str | None):
   if user_key is None:
      return '-'
   user_data = website.archive.get_user_data(user_key)
   if user_data is None:
      return user_key
   display_name = user_data['displayName']
   avatar_url = user_data['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.users_avatars_folder, avatar_url)
   return new_content_tag(file.page.soup, 'a', [
      new_content_tag(file.page.soup, 'span', [
         new_content_tag(file.page.soup, 'span', [
            file.page.soup.new_tag('img', attrs={'src': str(relative_path(website.root, file.path, avatar_path)), 'width': '16', 'height': '16'})
         ], attrs={'class': 'aui-avatar aui-avatar-small'}),
         display_name
      ], attrs={'class':'username'})
   ], attrs={'class':'user-hover', 'href': relative_link(website.root, file.path, website.user_folder / (urllib.parse.quote_plus(user_key) + '.html'))})

def render_date(date_str: str):
   return datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M')

def render_resolution(archive: mojira.Archive, resolution, depth: int):
   if resolution is None:
      resid = '0'
      resname = 'Unresolved'
   else:
      resolution_obj = archive.resolutions[resolution]
      resid = resolution_obj['id']
      resname = resolution_obj['name']
   depth_str = '../' * depth
   return f'<a href="{depth_str}resolutions/{resid}.html">{escape(resname)}</a>'

def render_version_list(archive: mojira.Archive, project, versions, depth: int):
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

def render_ticket_link(ticket, depth: int):
   depth_str = '../' * depth
   linkpart = f'<a href="{depth_str}issues/{ticket['key']}.html">{ticket['key']}</a>'
   summarypart = ticket['fields']['summary']
   if ticket['fields']['resolution'] is not None:
      return f'<s>{linkpart}</s> {summarypart}'
   else:
      return f'{linkpart} {summarypart}'

def render_issue(archive: mojira.Archive, issue, file, markup_proc):
   key = issue['key']
   print(key)
   summary = issue['fields']['summary']
   file.write('<!DOCTYPE html><html><head><meta content="width=device-width, initial-scale=1.0" name="viewport"/><link rel="stylesheet" href="../style.css"/><link rel="stylesheet" href="../../dump/assets/mojira.css"/><title>')
   file.write(f'[{escape(key)}] {escape(summary)}')
   file.write('</title></head><body class="flush">')
   file.write('<div class="title"><div class="flex">')
   file.write(f'<div class="summary"><h1>{project_link(archive, archive.projects[issue['fields']['project']], depth=1)} / <a href="https://bugs.mojang.com/browse/{key}">{escape(key)}</a></h1><h2>{escape(summary)}</h2></div>')
   reporter = user_link(archive, issue['fields'].get('reporter'), depth=1)
   creator = user_link(archive, issue['fields'].get('creator'), depth=1)
   file.write('<div class="fields"><div class="field-section"><dl>')
   file.write(f'<dt>Reporter</dt><dd>{reporter}</dd>')
   if issue['fields'].get('reporter') != issue['fields'].get('creator'):
      file.write(f'<dt>Creator</dt><dd>{creator}</dd>')
   if issue['fields'].get('assignee') is not None:
      assignee = user_link(archive, issue['fields'].get('assignee'), depth=1)
      file.write(f'<dt>Assignee</dt><dd>{assignee}</dd>')
   file.write(f'<dt>Votes</dt><dd>{issue['fields']['votes']['votes']}</dd>')
   file.write(f'<dt>Watchers</dt><dd>{issue['fields']['watches']['watchCount']}</dd>')
   if issue['fields']['resolutiondate'] is not None:
      file.write(f'<dt>Resolved</dt><dd>{render_date(issue['fields']['resolutiondate'])}</dd>')
   file.write('</div>')
   file.write('<div class="field-section"><dl>')
   if issue['fields'].get('customfield_10500') is not None:
      file.write(f'<dt>Confirmation Status</dt><dd>{escape(issue['fields']['customfield_10500']['value'])}</dd>')
   file.write(f'<dt>Resolution</dt><dd>{render_resolution(archive, issue['fields']['resolution'], depth=1)}</dd>')
   file.write(f'<dt>Created</dt><dd>{render_date(issue['fields']['created'])}</dd>')
   file.write(f'<dt>Updated</dt><dd>{render_date(issue['fields']['updated'])}</dd>')
   file.write('</dl></div>')
   file.write('</div></div></div>')
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

def render_comment(archive, issue, comment, file, markup_proc):
   file.write('<div class="comment">')
   file.write(f'<details open><summary>{user_link(archive, comment.get('author'), depth=1)} - <span class="subtle">{render_date(comment['created'])}</span></summary><div class="comment-content">')
   rendered_text = markup.convert(markup_proc, comment['body'], issue['id'])
   file.write(rendered_text)
   file.write('</div></details></div>')

if __name__ == '__main__':
   main()
