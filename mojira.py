import jira.client
import jira.resources
import os
import typing
import tryashtools as tat

def main():
   dump_folder = '/d/Archives/Mojira/dump'
   dump(dump_folder, full=False)

def fix(dump_folder: str):
   update_cache_path = os.path.join(dump_folder, 'updated.json')
   update_cache = {}
   for project in tat.get_folders(os.path.join(dump_folder, 'projects')):
      print(os.path.basename(project))
      for file in tat.get_files(project):
         data = tat.read_json(file)
         simplify_issue(dump_folder, data, False)
         tat.write_json(data, file)
         update_cache[data['key']] = data['fields']['updated']
   tat.write_json(update_cache, update_cache_path)

def refresh(dump_folder: str):
   update_cache_path = os.path.join(dump_folder, 'updated.json')
   update_cache = tat.read_json(update_cache_path)
   site = get_client()
   issues = get_issues(site, 'ORDER BY updated DESC')
   for issue in issues:
      local_date = update_cache.get(issue.key)
      if local_date is None or issue.fields.updated > local_date:
         save_issue(dump_folder, issue, update_cache, True)
      else:
         break
   tat.write_json(update_cache, update_cache_path)

def dump(dump_folder: str, full: bool=True):
   site = get_client()
   projects = site.projects()
   
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
   
   update_cache_path = os.path.join(dump_folder, 'updated.json')
   if full or not os.path.exists(update_cache_path):
      update_cache = {}
   else:
      update_cache = tat.read_json(update_cache_path)

   for project in projects:
      issues = get_issues(site, f'project = {project.key}')
      print(project.key)
      issue_count = 0
      for issue in issues:
         if save_issue(dump_folder, issue, update_cache, full):
            issue_count += 1
      tat.write_json(update_cache, update_cache_path)
      print(f'Saved {issue_count} issues')

def save_issue(dump_folder: str, issue: jira.Issue, update_cache: dict[str, str], overwrite: bool):
   issue_path = os.path.join(dump_folder, 'projects', issue.key.split('-')[0], f'{issue.key}.json')
   saved = False
   data = issue.raw
   if overwrite or not os.path.exists(issue_path):
      print(issue.key)
      simplify_issue(dump_folder, data, overwrite)
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

def simplify_issue(dump_folder: str, issue: dict[str, typing.Any], overwrite: bool):
   fields = issue['fields']
   simplify_field(fields, 'issuetype')
   simplify_field(fields, 'project')
   simplify_field(fields, 'resolution')
   simplify_field(fields, 'versions')
   simplify_field(fields, 'fixVersions')
   simplify_field(fields, 'status')
   simplify_user(fields, 'creator', dump_folder, overwrite)
   simplify_user(fields, 'reporter', dump_folder, overwrite)
   for attachment in fields['attachment']:
      simplify_user(attachment, 'author', dump_folder, overwrite)
   for comment in fields['comment']['comments']:
      simplify_user(comment, 'author', dump_folder, overwrite)
      simplify_user(comment, 'updateAuthor', dump_folder, overwrite)
   for link in fields['issuelinks']:
      simplify_field(link, 'type')
      simplify_field(link, 'inwardIssue')
   for change in issue['changelog']['histories']:
      simplify_user(change, 'author', dump_folder, overwrite)

def simplify_user(field: dict[str, typing.Any], key: str, dump_folder: str, overwrite: bool):
   if key not in field:
      return
   user_path = os.path.join(dump_folder, 'users', field[key]['name'] + '.json')
   if overwrite or not os.path.exists(user_path):
      tat.write_json(field[key], user_path)
   simplify_field(field, key, 'name')

def simplify_field(field: dict[str, typing.Any], key: str, simple_key: str='id'):
   if key not in field:
      return
   if isinstance(field[key], dict):
      field[key] = field[key][simple_key]
   elif isinstance(field[key], list):
      for i in range(len(field[key])):
         if isinstance(field[key][i], dict):
            field[key][i] = field[key][i][simple_key]

def get_issues(site: jira.client.JIRA, query: str) -> typing.Generator[jira.Issue, None, None]:
   i = 0
   chunk_size = 100
   while True:
      chunk = site.search_issues(query, startAt=i, maxResults=chunk_size, expand='changelog')
      chunk = typing.cast(jira.client.ResultList[jira.Issue], chunk)
      i += chunk_size
      yield from chunk.iterable
      if i >= chunk.total:
         break

if __name__ == '__main__':
   main()
