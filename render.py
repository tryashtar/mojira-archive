import mojira
import pathlib
import html
import datetime
import urllib.parse
import tryashtools as tat
import markup
import xml

def main():
   archive = mojira.get_archive()
   markup_proc = markup.get_process(archive)
   render(archive, pathlib.Path('/d/Archives/Mojira/render'), markup_proc)

def render(archive: mojira.Archive, out_folder: pathlib.Path, markup_proc):
   with open(out_folder / 'index.html', 'w', encoding='utf-8') as index:
      index.write('<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"/><title>Mojira Archive</title></head><body><h1>Mojira Archive</h1><table><tr><th>Project</th><th>Name</th><th>Lead</th><th>Issues</th></tr>')
      for project_id,project in archive.projects.items():
         tickets = archive.relations_cache['projects'][project_id]
         index.write(f'<tr><td>{render_project_key(project['key'])}</td><td>{escape(project['name'])}</td><td>{render_user(archive, project['lead'])}</td><td>{len(tickets)}</td></tr>')
      js = get_sorter()
      index.write(f'</table></body><script>{js}</script></html>')
   for project_id,project in archive.projects.items():
      project_key = project['key']
      print(project_key)
      tickets = archive.relations_cache['projects'][project_id]
      for ticket_id in tickets:
         ticket_data = archive.get_issue_data(ticket_id)
         file_path = out_folder / 'issues' / (ticket_data['key'] + '.html')
         with open(file_path, 'w', encoding='utf-8') as file:
            render_issue(archive, ticket_data, file, markup_proc)

def render_user(archive: mojira.Archive, user_key: str | None):
   if user_key is None:
      return '-'
   user_data = archive.get_user_data(user_key)
   if user_data is None:
      return f'{escape(user_key)}'
   username = user_data['name']
   display_name = user_data['displayName']
   avatar_url = user_data['avatarUrls']['48x48']
   avatar_id = archive.get_avatar_id(avatar_url)
   avatar_file = archive.users_avatars_folder / avatar_id
   try:
      svg = xml.etree.ElementTree.parse(avatar_file)
   except xml.etree.ElementTree.ParseError:
      svg = None
   if svg is None:
      img = f'<img src="{avatar_file}"/>'
   else:
      img = f'<object data="{avatar_file}" type="image/svg+xml"/>'
   return f'<span><span class="aui-avatar aui-avatar-small">{img}</span> <a class="user-hover user-avatar" rel="{escape(username)}" href="users/{escape(urllib.parse.quote_plus(username))}.html">{escape(display_name)}</a></span>'

def render_project_key(key: str):
   return f'<a href="issues/{key}.html">{escape(key)}</a>'

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

def user_display(dump, user_key):
   if user_key is None:
      return '-'
   user_path = dump.get_user_path(user_key)
   if not user_path.exists():
      return '-'
   data = tat.read_json(user_path)
   return data['displayName']

def date_display(date_str):
   return datetime.datetime.fromisoformat(date_str).date().isoformat()

def render_project(archive, project, file, issues):
   project_key = project['key']
   project_name = project['name']
   file.write('<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"/>')
   file.write(f'<title>[{escape(project_key)}] {escape(project_name)}</title>')
   file.write('</head><body>')
   file.write(f'<h1><a href="https://bugs.mojang.com/projects/{project_key}/summary">{escape(project_key)}</a></h1><h2>{escape(project_name)}</h2>')
   file.write('<table><tr><th>Issue</th><th>Summary</th><th>Reporter</th><th>Created</th></tr>')
   for issue in issues:
      data = tat.read_json(archive.get_issue_path(issue))
      reporter = user_display(archive, data['fields']['reporter'])
      date = date_display(data['fields']['created'])
      file.write(f'<tr><td><a href="{project['key']}/{data['key']}.html">{escape(data['key'])}</a></td><td>{escape(data['fields']['summary'])}</td><td>{reporter}</td><td>{date}</td></tr>')
   js = get_sorter()
   file.write(f'</table></body><script>{js}</script></html>')

def render_issue(archive: mojira.Archive, issue, file, markup_proc):
   key = issue['key']
   print(key)
   summary = issue['fields']['summary']
   project_key = key.split('-')[0]
   file.write('<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"/><title>')
   file.write(f'[{escape(key)}] {escape(summary)}')
   file.write('</title></head><body>')
   file.write('<div class="title"><div class="flex">')
   file.write(f'<div class="summary"><h1><a href="../{project_key}.html">{escape(project_key)}</a> / <a href="https://bugs.mojang.com/browse/{key}">{escape(key)}</a></h1><h2>{escape(summary)}</h2></div>')
   reporter = render_user(archive, issue['fields'].get('reporter'))
   creator = render_user(archive, issue['fields'].get('creator'))
   file.write('<div class="fields"><dl>')
   file.write(f'<dt>Reporter</dt><dd>{reporter}</dd>')
   if issue['fields'].get('reporter') != issue['fields'].get('creator'):
      file.write(f'<dt>Creator</dt><dd>{creator}</dd>')
   if issue['fields'].get('assignee') is not None:
      assignee = render_user(archive, issue['fields'].get('assignee'))
      file.write(f'<dt>Assignee</dt><dd>{assignee}</dd>')
   file.write('</dl></div>')
   file.write('</div></div>')
   desc = issue['fields']['description']
   if desc is not None:
      rendered_summary = markup.convert(markup_proc, desc, issue['id'])
      file.write(rendered_summary)
   file.write('</body></html>')

if __name__ == '__main__':
   main()
