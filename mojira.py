import jira.client
import jira.resources
import os
import urllib.parse
import typing
import tryashtools as tat

def main():
   dump_folder = '/d/Archives/Mojira/dump'
   dump(dump_folder, full=False)

def print_user_keys(dump_folder: str):
   for file in tat.get_files(os.path.join(dump_folder, 'users')):
      data = tat.read_json(file)
      print(data['key'])

def fix(dump_folder: str):
   client = get_client()
   update_cache_path = os.path.join(dump_folder, 'updated.json')
   update_cache = {}
   for project in tat.get_folders(os.path.join(dump_folder, 'tickets')):
      print(os.path.basename(project))
      for file in tat.get_files(project):
         data = tat.read_json(file)
         found_users = simplify_issue(data)
         handle_found_users(dump_folder, client, found_users, False)
         tat.write_json(data, file)
         update_cache[data['key']] = data['fields']['updated']
   tat.write_json(update_cache, update_cache_path)

def refresh(dump_folder: str):
   client = get_client()
   update_cache_path = os.path.join(dump_folder, 'updated.json')
   update_cache = tat.read_json(update_cache_path)
   issues = get_issues(client, 'ORDER BY updated DESC')
   for issue in issues:
      local_date = update_cache.get(issue.key)
      if local_date is None or issue.fields.updated > local_date:
         save_issue(dump_folder, client, issue, update_cache, True)
      else:
         break
   tat.write_json(update_cache, update_cache_path)

def dump(dump_folder: str, full: bool=True):
   client = get_client()
   projects = client.projects(expand='description,lead,url')
      
   fields_path = os.path.join(dump_folder, 'fields.json')
   projects_path = os.path.join(dump_folder, 'projects.json')
   issue_types_path = os.path.join(dump_folder, 'issue_types.json')
   resolutions_path = os.path.join(dump_folder, 'resolutions.json')
   statuses_path = os.path.join(dump_folder, 'statuses.json')
   versions_path = os.path.join(dump_folder, 'versions.json')
   link_types_path = os.path.join(dump_folder, 'link_types.json')
   if full or not os.path.exists(fields_path):
      fields = client.fields()
      tat.write_json(fields, fields_path)
   if full or not os.path.exists(projects_path):
      found_users = set()
      projects_data = [p.raw for p in projects]
      for project in projects_data:
         simplify_user(project, 'lead', found_users)
      handle_found_users(dump_folder, client, found_users, full)
      tat.write_json(projects_data, projects_path)
   if full or not os.path.exists(issue_types_path):
      issue_types = client.issue_types()
      tat.write_json([p.raw for p in issue_types], issue_types_path)
   if full or not os.path.exists(resolutions_path):
      resolutions = client.resolutions()
      tat.write_json([p.raw for p in resolutions], resolutions_path)
   if full or not os.path.exists(statuses_path):
      statuses = client.statuses()
      tat.write_json([p.raw for p in statuses], statuses_path)
   if full or not os.path.exists(versions_path):
      versions = [v for p in projects for v in client.project_versions(p.key)]
      tat.write_json([p.raw for p in versions], versions_path)
   if full or not os.path.exists(link_types_path):
      link_types = client.issue_link_types()
      tat.write_json([p.raw for p in link_types], link_types_path)
   
   update_cache_path = os.path.join(dump_folder, 'updated.json')
   if full or not os.path.exists(update_cache_path):
      update_cache = {}
   else:
      update_cache = tat.read_json(update_cache_path)

   for project in projects:
      last_key = update_cache.get(project.key)
      if full or last_key is None:
         query = f'project = {project.key} ORDER BY key ASC'
      else:
         query = f'project = {project.key} AND key > {last_key} ORDER BY key ASC'
      issues = get_issues(client, query)
      print(project.key)
      issue_count = 0
      for issue in issues:
         if save_issue(dump_folder, client, issue, update_cache, full):
            issue_count += 1
            update_cache[project.key] = issue.key
            tat.write_json(update_cache, update_cache_path)
      print(f'Saved {issue_count} issues')

def handle_found_users(dump_folder: str, client: jira.JIRA, users: set[str], overwrite: bool):
   for key in users:
      user_path = os.path.join(dump_folder, 'users', key + '.json')
      if overwrite or not os.path.exists(user_path):
         user_data = get_user(client, key, expand='groups')
         print('\t' + user_data.raw['name'])
         tat.write_json(user_data.raw, user_path)

def get_user(client: jira.JIRA, key: str, expand: str | None):
   user = jira.User(
      client._options,
      client._session,
      _query_param="key"
   )
   params = {}
   if expand is not None:
      params["expand"] = expand
   user.find(urllib.parse.quote(key), params=params)
   return user

def save_issue(dump_folder: str, client: jira.JIRA, issue: jira.Issue, update_cache: dict[str, str], overwrite: bool):
   issue_path = os.path.join(dump_folder, 'tickets', issue.key.split('-')[0], f'{issue.key}.json')
   saved = False
   data = issue.raw
   if overwrite or not os.path.exists(issue_path):
      print(issue.key)
      found_users = simplify_issue(data)
      handle_found_users(dump_folder, client, found_users, overwrite)
      tat.write_json(data, issue_path)
      saved = True
   for attachment in issue.fields.attachment:
      save_attachment(dump_folder, attachment, overwrite)
   update_cache[issue.key] = issue.fields.updated
   return saved

def save_attachment(dump_folder: str, attachment: jira.resources.Attachment, overwrite: bool):
   attach_path = os.path.join(dump_folder, 'attachments', attachment.id)
   if overwrite or not os.path.exists(attach_path):
      print('\t' + attachment.filename)
      os.makedirs(os.path.dirname(attach_path), exist_ok=True)
      with open(attach_path, 'wb') as file:
         for data in attachment.iter_content():
            file.write(data)

def get_client():
   key = tat.read_text('/d/Documents/Sensitive/mojira key.txt')
   client = jira.client.JIRA('https://bugs.mojang.com', token_auth=key)
   return client

def simplify_issue(issue: dict[str, typing.Any]):
   found_users = set()
   fields = issue['fields']
   simplify_field(fields, 'issuetype')
   simplify_field(fields, 'project')
   simplify_field(fields, 'resolution')
   simplify_field(fields, 'versions')
   simplify_field(fields, 'fixVersions')
   simplify_field(fields, 'status')
   simplify_user(fields, 'creator', found_users)
   simplify_user(fields, 'reporter', found_users)
   for attachment in fields['attachment']:
      simplify_user(attachment, 'author', found_users)
   for comment in fields['comment']['comments']:
      simplify_user(comment, 'author', found_users)
      simplify_user(comment, 'updateAuthor', found_users)
   for link in fields['issuelinks']:
      simplify_field(link, 'type')
      simplify_field(link, 'inwardIssue')
   for change in issue['changelog']['histories']:
      simplify_user(change, 'author', found_users)
   return found_users

def simplify_user(field: dict[str, typing.Any], key: str, found_users: set[str]):
   if key not in field:
      return
   found_users.add(field[key]['key'])
   simplify_field(field, key, 'key')

def simplify_field(field: dict[str, typing.Any], key: str, simple_key: str='id'):
   if key not in field:
      return
   if isinstance(field[key], dict):
      field[key] = field[key][simple_key]
   elif isinstance(field[key], list):
      for i in range(len(field[key])):
         if isinstance(field[key][i], dict):
            field[key][i] = field[key][i][simple_key]

def get_issues(client: jira.client.JIRA, query: str) -> typing.Generator[jira.Issue, None, None]:
   i = 0
   chunk_size = 100
   while True:
      chunk = client.search_issues(query, startAt=i, maxResults=chunk_size, expand='changelog')
      chunk = typing.cast(jira.client.ResultList[jira.Issue], chunk)
      i += chunk_size
      yield from chunk.iterable
      if i >= chunk.total:
         break

if __name__ == '__main__':
   main()
