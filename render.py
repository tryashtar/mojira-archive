import mojira
import pathlib
import html
import datetime
import urllib.parse
import tryashtools as tat

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   render(dump, pathlib.Path('/d/Archives/Mojira/render'))

def render(dump: mojira.Dump, out_folder: pathlib.Path):
   with open(out_folder / 'index.html', 'w', encoding='utf-8') as index:
      index.write('<!DOCTYPE html><html><head><title>Mojira Archive</title></head><style>a{text-decoration:none;}a:hover{text-decoration:underline;}th{cursor:pointer;}table,th,td{border:1px solid black; border-collapse:collapse;}body{font-family:verdana,sans-serif;margin:20px;}th,td{padding-left:10px;padding-right:10px;}</style><body><h1>Mojira Archive</h1><table><tr><th>Project</th><th>Name</th><th>Lead</th><th>Issues</th></tr>')
      for project in dump.projects.values():
         issues = list(dump.ticket_names(project['key']))
         index.write(f'<tr><td><a href="issues/{project['key']}.html">{escape(project['key'])}</a></td><td>{escape(project['name'])}</td><td>{escape(project['lead'])}</td><td>{len(issues)}</td></tr>')
      js = get_sorter()
      index.write(f'</table></body><script>{js}</script></html>')
   for project in dump.projects.values():
      key = project['key']
      print(key)
      issues = sorted(dump.ticket_names(key), key=lambda x: int(x.removeprefix(key + '-')))
      project_path = out_folder / 'issues' / (key + '.html')
      with open(project_path, 'w', encoding='utf-8') as file:
         render_project(dump, project, file, issues)
   for project in dump.projects.values():
      key = project['key']
      issues = sorted(dump.ticket_names(key), key=lambda x: int(x.removeprefix(key + '-')))
      for issue in issues:
         print(issue)
         data = tat.read_json(dump.get_issue_path(issue))
         issue_path = out_folder / 'issues' / key / (data['key'] + '.html')
         issue_path.parent.mkdir(parents=True, exist_ok=True)
         with open(issue_path, 'w', encoding='utf-8') as file:
            render_issue(dump, data, file)

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

def render_project(dump, project, file, issues):
   project_key = project['key']
   project_name = project['name']
   file.write('<!DOCTYPE html><html><head>')
   file.write(f'<title>[{escape(project_key)}] {escape(project_name)}</title>')
   file.write('</head><style>a{text-decoration:none;}a:hover{text-decoration:underline;}th{cursor:pointer;}table,th,td{border:1px solid black; border-collapse:collapse;}body{font-family:verdana,sans-serif;margin:20px;}th,td{padding-left:10px;padding-right:10px;}</style><body>')
   file.write(f'<h1><a href="https://bugs.mojang.com/projects/{project_key}/summary">{escape(project_key)}</a></h1><h2>{escape(project_name)}</h2>')
   file.write('<table><tr><th>Issue</th><th>Summary</th><th>Reporter</th><th>Created</th></tr>')
   for issue in issues:
      data = tat.read_json(dump.get_issue_path(issue))
      reporter = user_display(dump, data['fields']['reporter'])
      date = date_display(data['fields']['created'])
      file.write(f'<tr><td><a href="{project['key']}/{data['key']}.html">{escape(data['key'])}</a></td><td>{escape(data['fields']['summary'])}</td><td>{reporter}</td><td>{date}</td></tr>')
   js = get_sorter()
   file.write(f'</table></body><script>{js}</script></html>')

def render_issue(dump: mojira.Dump, issue, file):
   key = issue['key']
   summary = issue['fields']['summary']
   project_key = key.split('-')[0]
   file.write('<!DOCTYPE html><html><head><title>')
   file.write(f'[{escape(key)}] {escape(summary)}')
   file.write('</title><style>body{font-family:verdana,sans-serif;margin:0 0 20px 0;font-size:14px}a{text-decoration:none}a:hover{text-decoration:underline}pre{word-wrap:break-word;white-space:pre-wrap;margin:5px 0;padding:1px 10px 1px 15px;background-color:#f6f6f6;border-left:3px solid #f00}.info{color:gray;font-size:11px}div.flex{display:flex;justify-content:space-between}div.title{background-color:#e0edfb;padding:10px}h1{font-size:22px;font-weight:normal;margin:5px 0}h2{font-size:20px;font-weight:normal;margin:5px 0}.comment{word-wrap:break-word;display:flex;padding-top:5px;margin-left:10px}.subcomment{padding-left:15px;border-left:1px solid #dfdfdf}div.comment-content{display:inline-block;max-width:1000px;padding-left:10px;padding-right:10px}blockquote{margin:5px 0;padding:1px 10px 1px 15px;background-color:#f6f6f6;border-left:3px solid #00f}div.md *{margin:5px 0}div.comment-section{margin-right:20px}img,video,iframe{max-width:1500px;max-height:500px}.highlighted{background-color:#ffecb6}div.saved-comments{margin-left:10px}.md-spoiler-text{background-color:#000}.md-spoiler-text:hover{background-color:#ddd}button{margin:3px}.navigate{width:75px;height:40px}.jump{width:30px;height:30px}button.current{background-color:#ffecb6}dl{display:grid;grid-template-columns:max-content auto}dt{grid-column-start:1}dd{grid-column-start:2}</style></head><body>')
   file.write('<div class="title"><div class="flex">')
   file.write(f'<div class="summary"><h1><a href="../{project_key}.html">{escape(project_key)}</a> / <a href="https://bugs.mojang.com/browse/{key}">{escape(key)}</a></h1><h2>{escape(summary)}</h2></div>')
   reporter = get_user_display(dump, issue['fields'].get('reporter'))
   creator = get_user_display(dump, issue['fields'].get('creator'))
   file.write('<div class="fields"><dl>')
   file.write(f'<dt>Reporter</dt><dd>{reporter}</dd>')
   if issue['fields'].get('reporter') != issue['fields'].get('creator'):
      file.write(f'<dt>Creator</dt><dd>{creator}</dd>')
   if issue['fields'].get('assignee') is not None:
      assignee = get_user_display(dump, issue['fields'].get('assignee'))
      file.write(f'<dt>Assignee</dt><dd>{assignee}</dd>')
   file.write('</dl></div>')
   file.write('</div></div>')
   file.write('</body></html>')

def get_user_display(dump: mojira.Dump, key):
   if key is None:
      return '-'
   path = dump.get_user_path(key)
   if path.exists():
      data = tat.read_json(path)
      display = data['displayName']
      return f'<a href="../../users/{urllib.parse.quote_plus(key)}.html">{escape(display)}</a>'
   return f'MISSING: {key}'

if __name__ == '__main__':
   main()
