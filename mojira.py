import jira.client
import requests
import os
import typing
import tryashtools as tat

def main():
   dump()

def fix():
   userpath = '/d/Archives/Mojira/dump/users.json'
   users = tat.read_json(userpath)
   for project in tat.get_folders('/d/Archives/Mojira/dump'):
      for file in tat.get_files(project):
         data = tat.read_json(file)
         simplify_issue(data, users)
         tat.write_json(data, file)
   tat.write_json(users, userpath)

def dump():
   key = tat.read_text('/d/Documents/Sensitive/mojira key.txt')
   site = jira.client.JIRA('https://bugs.mojang.com', token_auth=key)
   users = []
   fields = site.fields()
   projects = site.projects()
   issue_types = site.issue_types()
   resolutions = site.resolutions()
   statuses = site.statuses()
   link_types = site.issue_link_types()
   versions = [v for p in projects for v in site.project_versions(p.key)]
   tat.write_json(fields, '/d/Archives/Mojira/dump/fields.json')
   tat.write_json([p.raw for p in projects], '/d/Archives/Mojira/dump/projects.json')
   tat.write_json([p.raw for p in issue_types], '/d/Archives/Mojira/dump/issue_types.json')
   tat.write_json([p.raw for p in resolutions], '/d/Archives/Mojira/dump/resolutions.json')
   tat.write_json([p.raw for p in statuses], '/d/Archives/Mojira/dump/statuses.json')
   tat.write_json([p.raw for p in versions], '/d/Archives/Mojira/dump/versions.json')
   tat.write_json([p.raw for p in link_types], '/d/Archives/Mojira/dump/link_types.json')
   for project in projects:
      issues = get_issues(site, project)
      print(project.key)
      issue_count = 0
      for issue in issues:
         print(issue.key)
         path = f'/d/Archives/Mojira/dump/projects/{project.key}/{issue.key}.json'
         data = issue.raw
         simplify_issue(data, users)
         tat.write_json(data, path)
         for attachment in data['fields']['attachment']:
            print(attachment['filename'])
            url = attachment['content']
            num = attachment['id']
            response = requests.get(url, stream=True)
            path = f'/d/Archives/Mojira/dump/attachments/{num}'
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as file:
               file.write(response.content)
         issue_count += 1
      print(issue_count)
      tat.write_json(users, '/d/Archives/Mojira/dump/users.json')

def simplify_issue(issue: dict[str, typing.Any], users: list[dict[str, typing.Any]]):
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
   found = False
   for i in range(len(users)):
      if users[i]['name'] == field[key]['name']:
         users[i] = field[key]
         found = True
         break
   if not found:
      users.append(field[key])
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
