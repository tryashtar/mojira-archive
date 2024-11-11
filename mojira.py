import bisect

import jira.client
import jira.exceptions
import pathlib
import json
import urllib.parse
import typing
import tryashtools as tat

def main():
   caches = get_caches()
   dump = get_dump()
   refresh(dump, caches)

def get_root():
   return pathlib.Path('/d/Archives/Mojira')

def cache_paths():
   root = get_root()
   ids = root / 'ids.json'
   relations = root / 'relations.json'
   renders = root / 'renders.json'
   return {'ids':ids,'relations':relations,'renders':renders}

def get_caches():
   paths = cache_paths()
   ids = tat.read_json(paths['ids']) if paths['ids'].exists() else {'issues':{},'users':{}}
   relations = tat.read_json(paths['relations']) if paths['relations'].exists() else {}
   renders = tat.read_json(paths['renders']) if paths['renders'].exists() else {}
   return {'ids':ids,'relations':relations,'renders':renders}

def write_caches(caches):
   paths = cache_paths()
   tat.write_json(caches['ids'], paths['ids'], mini=True)
   tat.write_json(caches['relations'], paths['relations'], mini=True)
   tat.write_json(caches['renders'], paths['renders'], mini=True)

def get_dump():
   return Dump(get_root() / 'dump')

class Dump:
   def __init__(self, folder: pathlib.Path):
      self.root_folder = folder
      self.attachments_folder = folder / 'attachments'
      self.tickets_folder = folder / 'tickets'
      self.users_folder = folder / 'users'
      self.project_avatars_folder = folder / 'avatars/projects'
      self.users_avatars_folder = folder / 'avatars/users'
      self.new_users = {}
      self.seen_users = set()
      
      self.fields_path = folder / 'fields.json'
      self.fields = self.load_meta(self.fields_path)
      self.issue_types_path = folder / 'issue_types.json'
      self.issue_types = self.load_meta(self.issue_types_path)
      self.link_types_path = folder / 'link_types.json'
      self.link_types = self.load_meta(self.link_types_path)
      self.projects_path = folder / 'projects.json'
      self.projects = self.load_meta(self.projects_path)
      for project in self.projects.values():
         project['versions'] = self.key_by(project['versions'], 'id')
      self.resolutions_path = folder / 'resolutions.json'
      self.resolutions = self.load_meta(self.resolutions_path)
      self.statuses_path = folder / 'statuses.json'
      self.statuses = self.load_meta(self.statuses_path)
   
   def save_metas(self):
      self.root_folder.mkdir(parents=True, exist_ok=True)
      self.save_meta(self.fields, self.fields_path)
      self.save_meta(self.issue_types, self.issue_types_path)
      self.save_meta(self.link_types, self.link_types_path)
      for project in self.projects.values():
         project['versions'] = list(project['versions'].values())
      self.save_meta(self.projects, self.projects_path)
      for project in self.projects.values():
         project['versions'] = self.key_by(project['versions'], 'id')
      self.save_meta(self.resolutions, self.resolutions_path)
      self.save_meta(self.statuses, self.statuses_path)
      
   def save_project_avatars(self, client: jira.JIRA):
      for project in self.projects.values():
         self.save_avatar(client, self.project_avatars_folder, project['avatarUrls']['48x48'])
   
   def get_avatar_id(self, url: str):
      url_obj = urllib.parse.urlparse(url)
      queries = urllib.parse.parse_qs(url_obj.query)
      avatarid = queries['avatarId'][0]
      return avatarid
   
   def save_avatar(self, client: jira.JIRA, folder: pathlib.Path, url: str):
      avatarid = self.get_avatar_id(url)
      filepath = folder / avatarid
      if not filepath.exists():
         print('\t' + avatarid)
         folder.mkdir(parents=True, exist_ok=True)
         response = client._session.get(url)
         with open(filepath, 'wb') as file:
            file.write(response.content)
   
   def load_meta(self, path: pathlib.Path) -> dict[str, typing.Any]:
      data = self.load_or(path, {})
      data = self.key_by(data, 'id')
      return data
   
   def save_meta(self, data: dict[str, typing.Any], path: pathlib.Path):
      with open(path, 'w', encoding='utf-8') as file:
         json.dump(list(data.values()), file, indent=3)
   
   def fetch_metas(self, client: jira.JIRA):
      projects = [client.project(x.id, expand='description,lead,url') for x in client.projects()]
      self.fields = self.key_by(client.fields(), 'id')
      project_data = [p.raw for p in projects]
      for project in project_data:
         self.simplify_user(project, 'lead')
      self.projects = self.key_by(project_data, 'id')
      for project in self.projects.values():
         project['versions'] = self.key_by(project['versions'], 'id')
      self.issue_types = self.key_by([p.raw for p in client.issue_types()], 'id')
      self.resolutions = self.key_by([p.raw for p in client.resolutions()], 'id')
      self.statuses = self.key_by([p.raw for p in client.statuses()], 'id')
      self.link_types = self.key_by([p.raw for p in client.issue_link_types()], 'id')
   
   def fetch_issues(self, client: jira.JIRA, query: str, overwrite: bool):
      self.attachments_folder.mkdir(parents=True, exist_ok=True)
      self.tickets_folder.mkdir(parents=True, exist_ok=True)
      for issue in get_issues(client, query):
         self.save_issue(client, issue, overwrite)
                     
   def save_issue(self, client: jira.JIRA, issue: jira.Issue, overwrite: bool):
      issue_path = self.get_issue_path(issue.id)
      data = issue.raw
      if overwrite or not issue_path.exists():
         print(f'{issue.key} / {issue.id}')
         self.simplify_issue(data)
         self.flush_users(client, overwrite)
      for attachment in issue.fields.attachment:
         attach_path = self.get_attachment_path(attachment.id, content=False)
         attach_content = self.get_attachment_path(attachment.id, content=True)
         if not attach_path.exists():
            print('\t' + attachment.filename)
            with open(attach_content, 'wb') as file:
               for content in attachment.iter_content():
                  file.write(content)
            with open(attach_path, 'w', encoding='utf-8') as file:
               attachment_data = attachment.raw
               json.dump(attachment_data, file, indent=3)
      with open(issue_path, 'w', encoding='utf-8') as file:
         json.dump(data, file, indent=3)
   
   def simplify_issue(self, issue: dict[str, typing.Any]):
      fields = issue['fields']
      self.simplify_field(fields, 'issuetype')
      self.simplify_field(fields, 'project')
      self.simplify_field(fields, 'resolution')
      self.simplify_field(fields, 'versions')
      self.simplify_field(fields, 'fixVersions')
      self.simplify_field(fields, 'status')
      self.simplify_user(fields, 'creator')
      self.simplify_user(fields, 'reporter')
      self.simplify_user(fields, 'assignee')
      for attachment in fields['attachment']:
         self.simplify_user(attachment, 'author')
      self.simplify_field(fields, 'attachment')
      for comment in fields['comment']['comments']:
         self.simplify_user(comment, 'author')
         self.simplify_user(comment, 'updateAuthor')
      for link in fields['issuelinks']:
         self.simplify_field(link, 'type')
         self.simplify_field(link, 'inwardIssue')
         self.simplify_field(link, 'outwardIssue')
      for change in issue['changelog']['histories']:
         self.simplify_user(change, 'author')

   def simplify_user(self, field: dict[str, typing.Any], key: str):
      if field.get(key) is None:
         return
      user_key = field[key]['key']
      if user_key not in self.seen_users:
         self.new_users[user_key] = field[key]
      self.simplify_field(field, key, 'key')

   def simplify_field(self, field: dict[str, typing.Any], key: str, simple_key: str='id'):
      if key not in field:
         return
      if isinstance(field[key], dict):
         field[key] = field[key][simple_key]
      elif isinstance(field[key], list):
         for i in range(len(field[key])):
            if isinstance(field[key][i], dict):
               field[key][i] = field[key][i][simple_key]
   
   def get_attachment_path(self, attach_id: str, content=False) -> pathlib.Path:
      if content:
         return self.attachments_folder / 'content' / attach_id
      return self.attachments_folder / (attach_id + '.json')
   
   def get_issue_path(self, issue_id: str) -> pathlib.Path:
      return self.tickets_folder / (issue_id + '.json')
   
   def get_user_path(self, key: str, unknown=False) -> pathlib.Path:
      if unknown:
         return self.users_folder / 'unknown' / (urllib.parse.quote_plus(key) + '.json')   
      return self.users_folder / (urllib.parse.quote_plus(key) + '.json')
   
   def flush_users(self, client: jira.JIRA, overwrite: bool):
      self.users_folder.mkdir(parents=True, exist_ok=True)
      for key,value in self.new_users.items():
         user_path = self.get_user_path(key, unknown=False)
         try:
            user_data = get_user(client, key, expand='groups').raw
         except jira.exceptions.JIRAError as exc:
            if exc.text == f'The user with the key \'{key}\' does not exist':
               user_path = self.get_user_path(key, unknown=True)
               user_data = value
            else:
               raise
         if user_data is not None:
            self.save_user_data(user_path, user_data, overwrite)
            avatar_url = user_data['avatarUrls']['48x48']
            self.save_avatar(client, self.users_avatars_folder, avatar_url)
         self.seen_users.add(key)
      self.new_users = {}
   
   def save_user_data(self, path: pathlib.Path, data: dict[str, typing.Any], overwrite: bool):
      if overwrite or not path.exists():
         print('\t' + data['name'])
         with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=3)
   
   def key_by(self, items: list[dict[str, typing.Any]], key: str) -> dict[str, dict[str, typing.Any]]:
      result = {}
      for item in items:
         result[item[key]] = item
      return result

   def load_or(self, path: pathlib.Path, default: typing.Any) -> typing.Any:
      if path.exists():
         with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
      return default

   def tickets(self) -> typing.Generator[dict[str, typing.Any], None, None]:
      for path in self.tickets_folder.iterdir():
         with open(path, 'r', encoding='utf-8') as file:
            yield json.load(file)

   def ticket_names(self) -> typing.Generator[str, None, None]:
      for path in self.tickets_folder.iterdir():
         yield path.stem

def fetch_issues(dump: Dump, query: str):
   print('Connecting...')
   client = get_client()
   print('Fetching issues...')
   dump.fetch_issues(client, query, overwrite=True)
   
def fetch_users(dump: Dump, users: list[str]):
   print('Connecting...')
   client = get_client()
   print('Fetching users...')
   for user in users:
      dump.new_users[user] = None
   dump.flush_users(client, overwrite=True)

def refresh(dump: Dump, caches):
   print('Connecting...')
   client = get_client()
   print('Fetching metas...')
   dump.fetch_metas(client)
   dump.save_metas()
   dump.save_project_avatars(client)
   print('Checking issues...')
   issues = get_issues(client, 'ORDER BY updated DESC')
   for issue in issues:
      existing_data = None
      existing_path = dump.get_issue_path(issue.id)
      if existing_path.exists():
         with open(existing_path, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
      if existing_data is None or issue.fields.updated > existing_data['fields']['updated']:
         print(f'Updated {issue.fields.updated}, last saved {existing_data['fields']['updated']}')
         dump.save_issue(client, issue, True)
         update_caches(caches, existing_data, issue.raw)
         write_caches(caches)
      else:
         print(f'{issue.key} already up-to-date')
         break

def update_caches(caches, old_data, new_data):
   def navigate(path):
      block = caches['relations']
      for i,entry in enumerate(path):
         if entry is None:
            entry = ''
         if entry not in block:
            if i == len(path) - 1:
               block[entry] = []
            else:
               block[entry] = {}
         block = block[entry]
         if i == len(path) - 1:
            return block
   def add(path, value):
      dest = navigate(path)
      index = bisect.bisect_left(dest, value)
      if index >= len(dest) or dest[index] != value:
         bisect.insort(dest, value)
   def remove(path, value):
      dest = navigate(path)
      index = bisect.bisect_left(dest, value)
      if index < len(dest) and dest[index] == value:
         del dest[index]

   for (source, fn) in [(old_data, remove), (new_data, add)]:
      if source is None:
         continue
      ticket_id = source['id']
      if source is old_data:
         caches['ids']['issues'].pop(source['key'], None)
      elif source is new_data:
         caches['ids']['issues'][source['key']] = ticket_id
      fields = source['fields']
      fn(['resolutions', fields['resolution']], ticket_id)
      if 'versions' in fields:
         for version in fields['versions']:
            fn(['versions', version, 'affected'], ticket_id)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            fn(['versions', version, 'fixed'], ticket_id)
      fn(['users', fields['creator'], 'created'], ticket_id)
      fn(['users', fields['reporter'], 'reported'], ticket_id)
      if 'assignee' in fields:
         fn(['users', fields['assignee'], 'assigned'], ticket_id)
      for comment in fields['comment']['comments']:
         fn(['users', comment.get('author'), 'comments', ticket_id], comment['id'])
         fn(['users', comment.get('updateAuthor'), 'edits', ticket_id], comment['id'])
      for change in source['changelog']['histories']:
         fn(['users', change['author'], 'changes', ticket_id], change['id'])
         for item in change['items']:
            if item['field'] == 'Key':
               if source is old_data:
                  caches['ids']['issues'].pop(item['fromString'], None)
               elif source is new_data:
                  caches['ids']['issues'][item['fromString']] = ticket_id

def get_client() -> jira.JIRA:
   with open('/d/Documents/Sensitive/mojira key.txt', 'r', encoding='utf-8') as file:
      key = file.read()
   client = jira.JIRA('https://bugs.mojang.com', token_auth=key)
   return client

def get_user(client: jira.JIRA, key: str, expand: str | None) -> jira.User:
   user = jira.User(
      client._options,
      client._session,
      _query_param="key"
   )
   params = {}
   if expand is not None:
      params["expand"] = expand
   user.find(urllib.parse.quote_plus(key), params=params)
   return user

def get_issues(client: jira.JIRA, query: str) -> typing.Generator[jira.Issue, None, None]:
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
