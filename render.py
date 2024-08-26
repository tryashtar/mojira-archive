import mojira
import html
import os
import tryashtools as tat

def render(dump_folder: str, out_folder: str):
   projects = tat.read_json(os.path.join(dump_folder, 'projects.json'))
   with open(os.path.join(out_folder, 'index.html'), 'w', encoding='utf-8') as index:
      index.write('<!DOCTYPE html><html><head><title>Mojira - Archive</title></head><style>a{text-decoration:none;}a:hover{text-decoration:underline;}th{cursor:pointer;}table,th,td{border:1px solid black; border-collapse:collapse;}body{font-family:verdana,sans-serif;margin:20px;}th,td{padding-left:10px;padding-right:10px;}</style><body><h1>Mojira - Archive</h1><table><tr><th>Project</th><th>Name</th><th>Lead</th><th>Issues</th></tr>')
      for project in projects:
         issues = list(tat.get_files(os.path.join(dump_folder, 'tickets', project['key'])))
         index.write(f'<tr><td><a href="issues/{project['key']}.html">{escape(project['key'])}</a></td><td>{escape(project['name'])}</td><td>{escape(project['lead'])}</td><td>{len(issues)}</td></tr>')
      js = '''const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;
const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
    v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
    )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));
document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {
    const table = th.closest('table');
    Array.from(table.querySelectorAll('tr:nth-child(n+2)'))
        .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
        .forEach(tr => table.appendChild(tr) );
})));'''
      index.write(f'</table></body><script>{js}</script></html>')
   for project in projects:
      issues = tat.get_files(os.path.join(dump_folder, 'tickets', project['key']))
      with open(os.path.join(out_folder, 'issues', project['key'] + '.html'), 'w', encoding='utf-8') as file:
         render_project(project, file, issues)

def escape(text):
   return html.escape(text).replace('\n','<br/>')

def render_project(project, file, issues):
   file.write('<!DOCTYPE html><html><head><title>Mojira - '+project['key']+'</title></head><style>a{text-decoration:none;}a:hover{text-decoration:underline;}th{cursor:pointer;}table,th,td{border:1px solid black; border-collapse:collapse;}body{font-family:verdana,sans-serif;margin:20px;}th,td{padding-left:10px;padding-right:10px;}</style><body><h1>Mojira - '+project['key']+'</h1><table><tr><th>Issue</th><th>Summary</th><th>Subreddit</th><th>Date</th></tr>')
   for issue in issues:
      data = tat.read_json(issue)
      file.write(f'<tr><td><a href="{project['key']}/{data['key']}.html">{escape(data['key'])}</a></td><td>{escape(data['fields']['summary'])}</td><td></td><td></td></tr>')
   js = '''const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;
const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
    v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
    )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));
document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {
    const table = th.closest('table');
    Array.from(table.querySelectorAll('tr:nth-child(n+2)'))
        .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
        .forEach(tr => table.appendChild(tr) );
})));'''
   file.write(f'</table></body><script>{js}</script></html>')
