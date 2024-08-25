import jira.client
import requests
import os
import typing
import tryashtools as tat

def main():
   dump_folder = '/d/Archives/Mojira/dump'
   dump(dump_folder, full=False)

def fix(dump_folder):
   userpath = os.path.join(dump_folder, 'users.json')
   users = tat.read_json(userpath)
   for project in tat.get_folders(os.path.join(dump_folder, 'projects')):
      for file in tat.get_files(project):
         data = tat.read_json(file)
         simplify_issue(data, users)
         tat.write_json(data, file)
   tat.write_json(users, userpath)

def dump(dump_folder, full=True):
   key = tat.read_text('/d/Documents/Sensitive/mojira key.txt')
   site = jira.client.JIRA('https://bugs.mojang.com', token_auth=key)
   projects = site.projects()
   
   users_path = os.path.join(dump_folder, 'users.json')
   fields_path = os.path.join(dump_folder, 'fields.json')
   projects_path = os.path.join(dump_folder, 'projects.json')
   issue_types_path = os.path.join(dump_folder, 'issue_types.json')
   resolutions_path = os.path.join(dump_folder, 'resolutions.json')
   statuses_path = os.path.join(dump_folder, 'statuses.json')
   versions_path = os.path.join(dump_folder, 'versions.json')
   link_types_path = os.path.join(dump_folder, 'link_types.json')
   if full or not os.path.exists(fields_path):
      fields = site.fields()
      tat.write_json(fields, fields_path)
   if full or not os.path.exists(projects_path):
      tat.write_json([p.raw for p in projects], projects_path)
   if full or not os.path.exists(issue_types_path):
      issue_types = site.issue_types()
      tat.write_json([p.raw for p in issue_types], issue_types_path)
   if full or not os.path.exists(resolutions_path):
      resolutions = site.resolutions()
      tat.write_json([p.raw for p in resolutions], resolutions_path)
   if full or not os.path.exists(statuses_path):
      statuses = site.statuses()
      tat.write_json([p.raw for p in statuses], statuses_path)
   if full or not os.path.exists(versions_path):
      versions = [v for p in projects for v in site.project_versions(p.key)]
      tat.write_json([p.raw for p in versions], versions_path)
   if full or not os.path.exists(link_types_path):
      link_types = site.issue_link_types()
      tat.write_json([p.raw for p in link_types], link_types_path)
   
   if not full and os.path.exists(users_path):
      users = {'list':tat.read_json(users_path),'indices':{}}
   else:
      users = {'list':[],'indices':{}}
   for i in range(len(users['list'])):
      users['indices'][users['list'][i]['name']] = i

   for project in projects:
      issues = get_issues(site, project)
      print(project.key)
      issue_count = 0
      for issue in issues:
         issue_path = os.path.join(dump_folder, 'projects', project.key, f'{issue.key}.json')
         if full or not os.path.exists(issue_path):
            print(issue.key)
            data = issue.raw
            simplify_issue(data, users)
            tat.write_json(data, issue_path)
            for attachment in data['fields']['attachment']:
               attach_path = os.path.join(dump_folder, 'attachments', attachment['id'])
               if full or not os.path.exists(attach_path):
                  print('\t' + attachment['filename'])
                  response = requests.get(attachment['content'], stream=True, timeout=20)
                  os.makedirs(os.path.dirname(attach_path), exist_ok=True)
                  with open(attach_path, 'wb') as file:
                     file.write(response.content)
            issue_count += 1
            if not full:
               tat.write_json(users['list'], users_path)
      print(f'Downloaded {issue_count} issues')
      tat.write_json(users['list'], users_path)

def simplify_issue(issue: dict[str, typing.Any], users):
   fields = issue['fields']
   simplify_field(fields, 'issuetype')
   simplify_field(fields, 'project')
   simplify_field(fields, 'resolution')
   simplify_field(fields, 'versions')
   simplify_field(fields, 'fixVersions')
   simplify_field(fields, 'status')
   simplify_user(fields, 'creator', users)
   simplify_user(fields, 'reporter', users)
   for attachment in fields['attachment']:
      simplify_user(attachment, 'author', users)
   for comment in fields['comment']['comments']:
      simplify_user(comment, 'author', users)
      simplify_user(comment, 'updateAuthor', users)
   for link in fields['issuelinks']:
      simplify_field(link, 'type')
      simplify_field(link, 'inwardIssue')
   for change in issue['changelog']['histories']:
      simplify_user(change, 'author', users)

def simplify_user(field, key, users):
   if key not in field:
      return
   username = field[key]['name']
   index = users['indices'].get(username)
   if index is None:
      users['indices'][username] = len(users['list'])
      users['list'].append(field[key])
   else:
      users['list'][index] = field[key]
   simplify_field(field, key, 'name')

def simplify_field(field, key, simple_key='id'):
   if key not in field:
      return
   if isinstance(field[key], dict):
      field[key] = field[key][simple_key]
   elif isinstance(field[key], list):
      for i in range(len(field[key])):
         if isinstance(field[key][i], dict):
            field[key][i] = field[key][i][simple_key]

def get_issues(site: jira.client.JIRA, project: jira.Project) -> typing.Generator[jira.Issue, None, None]:
   i = 0
   chunk_size = 100
   while True:
      chunk = site.search_issues(f'project = {project.key}', startAt=i, maxResults=chunk_size, expand='changelog')
      chunk = typing.cast(jira.client.ResultList[jira.Issue], chunk)
      i += chunk_size
      yield from chunk.iterable
      if i >= chunk.total:
         break

if __name__ == '__main__':
   main()
