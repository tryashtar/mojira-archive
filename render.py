import mojira
import pathlib
import html
import datetime
import urllib.parse
import tryashtools as tat
import markup

def main():
   archive = mojira.get_archive()
   out_folder = pathlib.Path('/d/Archives/Mojira/render')
   with open(out_folder / 'index.html', 'w', encoding='utf-8') as index:
      render_index(archive, index)
   with open(out_folder / 'projects/MC.html', 'w', encoding='utf-8') as file:
      render_project(archive, archive.projects['10400'], file)
   markup_proc = markup.get_process(archive)
   with open(out_folder / 'issues/MC-4.html', 'w', encoding='utf-8') as file:
      render_issue(archive, archive.get_issue_data('11242'), file, markup_proc)
   print('Now the rest')
   render(archive, out_folder, markup_proc)

def render(archive: mojira.Archive, out_folder: pathlib.Path, markup_proc):
   with open(out_folder / 'index.html', 'w', encoding='utf-8') as index:
      render_index(archive, index)
   for project_id,project in archive.projects.items():
      project_key = project['key']
      print(project_key)
      file_path = out_folder / 'projects' / (project_key + '.html')
      with open(file_path, 'w', encoding='utf-8') as file:
         render_project(archive, project, file)
   for project_id,project in archive.projects.items():
      project_key = project['key']
      print(project_key)
      tickets = archive.relations_cache['projects'][project_id]
      for ticket_id in tickets:
         ticket_data = archive.get_issue_data(ticket_id)
         file_path = out_folder / 'issues' / (ticket_data['key'] + '.html')
         with open(file_path, 'w', encoding='utf-8') as file:
            render_issue(archive, ticket_data, file, markup_proc)

def render_index(archive: mojira.Archive, file):
   file.write('<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"/><link rel="stylesheet" href="../dump/assets/mojira.css"/><title>Mojira Archive</title></head><body><h1>Mojira Archive</h1><table><tr><th>Project</th><th>Name</th><th>Issues</th><th>Versions</th></tr>')
   for project_id,project in archive.projects.items():
      tickets = archive.relations_cache['projects'][project_id]
      versions = project['versions']
      file.write(f'<tr><td>{render_project_key(archive, project, depth=0)}</td><td>{escape(project['name'])}</td><td>{len(tickets)}</td><td>{len(versions)}</td></tr>')
   js = get_sorter()
   file.write(f'</table></body><script>{js}</script></html>')

def render_user(archive: mojira.Archive, user_key: str | None, depth: int):
   if user_key is None:
      return '-'
   user_data = archive.get_user_data(user_key)
   if user_data is None:
      return f'{escape(user_key)}'
   username = user_data['name']
   display_name = user_data['displayName']
   avatar_url = user_data['avatarUrls']['48x48']
   avatar_path = get_avatar_path(archive, archive.users_avatars_folder, avatar_url)
   if avatar_path is not None:
      img = f'<img src="{avatar_path}"/>'
   else:
      img = ''
   depth_str = '../' * depth
   return f'<a class="user-hover" rel="{escape(username)}" href="{depth_str}users/{escape(urllib.parse.quote_plus(username))}.html"><span class="username"><span class="aui-avatar aui-avatar-small">{img}</span>{escape(display_name)}</span></a>'

def get_avatar_path(archive: mojira.Archive, folder: pathlib.Path, url: str):
   avatar_id = archive.get_avatar_id(url)
   avatar_file = folder / (avatar_id + '.png')
   if avatar_file.exists():
      return avatar_file
   avatar_file = folder / (avatar_id + '.svg')
   if avatar_file.exists():
      return avatar_file
   return None

def render_project_key(archive: mojira.Archive, project, depth: int):
   key = project['key']
   avatar_url = project['avatarUrls']['48x48']
   avatar_path = get_avatar_path(archive, archive.project_avatars_folder, avatar_url)
   if avatar_path is not None:
      img = f'<img src="{avatar_path}"/>'
   else:
      img = ''
   depth_str = '../' * depth
   return f'<a href="{depth_str}projects/{key}.html"><span class="project-key"><span class="project-avatar">{img}</span>{escape(key)}</span></a>'

def get_sorter():
   return '''const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;
const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
    v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
    )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));
document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {
    const table = th.closest('table');
    Array.from(table.querySelectorAll('tr:nth-child(n+2)'))
        .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
        .forEach(tr => table.appendChild(tr) );
})));'''

def escape(text):
   return html.escape(text).replace('\n','<br/>')

def render_date(date_str):
   return datetime.datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M')

def render_project(archive, project, file):
   project_key = project['key']
   project_name = project['name']
   file.write('<!DOCTYPE html><html><head><link rel="stylesheet" href="../style.css"/><link rel="stylesheet" href="../../dump/assets/mojira.css"/>')
   file.write(f'<title>[{escape(project_key)}] {escape(project_name)}</title>')
   file.write('</head><body>')
   file.write(f'<h1><a href="../index.html">Projects</a> / <a href="https://bugs.mojang.com/projects/{project_key}/summary">{escape(project_key)}</a></h1><h2>{escape(project_name)}</h2>')
   file.write(f'{render_user(archive, project['lead'], depth=1)}')
   file.write(f'<div class="project-desc">{project['description']}</div>')
   file.write('<table><tr><th>Issue</th><th>Summary</th><th>Reporter</th><th>Created</th></tr>')
   #for issue in issues:
   #   data = tat.read_json(archive.get_issue_path(issue))
   #   reporter = user_display(archive, data['fields']['reporter'])
   #   date = date_display(data['fields']['created'])
   #   file.write(f'<tr><td><a href="{project['key']}/{data['key']}.html">{escape(data['key'])}</a></td><td>{escape(data['fields']['summary'])}</td><td>{reporter}</td><td>{date}</td></tr>')
   js = get_sorter()
   file.write(f'</table></body><script>{js}</script></html>')

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
   file.write('<!DOCTYPE html><html><head><link rel="stylesheet" href="../style.css"/><link rel="stylesheet" href="../../dump/assets/mojira.css"/><title>')
   file.write(f'[{escape(key)}] {escape(summary)}')
   file.write('</title></head><body class="flush">')
   file.write('<div class="title"><div class="flex">')
   file.write(f'<div class="summary"><h1>{render_project_key(archive, archive.projects[issue['fields']['project']], depth=1)} / <a href="https://bugs.mojang.com/browse/{key}">{escape(key)}</a></h1><h2>{escape(summary)}</h2></div>')
   reporter = render_user(archive, issue['fields'].get('reporter'), depth=1)
   creator = render_user(archive, issue['fields'].get('creator'), depth=1)
   file.write('<div class="fields"><div class="field-section"><dl>')
   file.write(f'<dt>Reporter</dt><dd>{reporter}</dd>')
   if issue['fields'].get('reporter') != issue['fields'].get('creator'):
      file.write(f'<dt>Creator</dt><dd>{creator}</dd>')
   if issue['fields'].get('assignee') is not None:
      assignee = render_user(archive, issue['fields'].get('assignee'), depth=1)
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
   version_list = render_version_list(archive, archive.projects[issue['fields']['project']], issue['fields']['versions'], depth=1)
   fixed_list = render_version_list(archive, archive.projects[issue['fields']['project']], issue['fields']['fixVersions'], depth=1)
   file.write(f'<dt>Affects Versions</dt><dd>{version_list}</dd>')
   file.write(f'<dt>Fixed Versions</dt><dd>{fixed_list}</dd>')
   file.write(f'<dt>Labels</dt><dd>{'-' if len(issue['fields']['labels']) == 1 else ', '.join([f'<a href="../labels/{escape(x)}.html"><code>{escape(x)}</code></a>' for x in issue['fields']['labels']])}</dd>')
   if issue['fields'].get('customfield_11901') is not None:
      file.write(f'<dt>Category</dt><dd>{'-' if len(issue['fields']['customfield_11901']) == 1 else ', '.join([f'<a href="../category/{escape(x['value'])}.html">{escape(x['value'])}</a>' for x in issue['fields']['customfield_11901']])}</dd>')
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
   file.write(f'<details open><summary>{render_user(archive, comment.get('author'), depth=1)} - <span class="subtle">{render_date(comment['created'])}</span></summary><div class="comment-content">')
   rendered_text = markup.convert(markup_proc, comment['body'], issue['id'])
   file.write(rendered_text)
   file.write('</div></details></div>')

if __name__ == '__main__':
   main()
