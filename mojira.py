import jira.client
import jira.exceptions
import pathlib
import json
import urllib.parse
import typing

def main():
   dump = Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   populate(dump)
   dump.save()

class Dump:
   def __init__(self, folder: pathlib.Path):
      self.root_folder = folder
      self.attachments_folder = folder / 'attachments'
      self.tickets_folder = folder / 'tickets'
      self.users_folder = folder / 'users'
      self.unknown_users_path = folder / 'unknown_users.json'
      self.unknown_users = self.load_or(self.unknown_users_path, {})
      self.new_users = {}
      
      self.fields_path = folder / 'fields.json'
      self.fields = self.load_meta(self.fields_path)
      self.issue_types_path = folder / 'issue_types.json'
      self.issue_types = self.load_meta(self.issue_types_path)
      self.link_types_path = folder / 'link_types.json'
      self.link_types = self.load_meta(self.link_types_path)
      self.projects_path = folder / 'projects.json'
      self.projects = self.load_meta(self.projects_path)
      self.resolutions_path = folder / 'resolutions.json'
      self.resolutions = self.load_meta(self.resolutions_path)
      self.statuses_path = folder / 'statuses.json'
      self.statuses = self.load_meta(self.statuses_path)
      self.versions_path = folder / 'versions.json'
      self.versions = self.load_meta(self.versions_path)
   
   def save(self):
      self.root_folder.mkdir(parents=True, exist_ok=True)
      if self.fields is not None:
         self.save_meta(self.fields, self.fields_path)
      if self.issue_types is not None:
         self.save_meta(self.issue_types, self.issue_types_path)
      if self.link_types is not None:
         self.save_meta(self.link_types, self.link_types_path)
      if self.projects is not None:
         self.save_meta(self.projects, self.projects_path)
      if self.resolutions is not None:
         self.save_meta(self.resolutions, self.resolutions_path)
      if self.statuses is not None:
         self.save_meta(self.statuses, self.statuses_path)
      if self.versions is not None:
         self.save_meta(self.versions, self.versions_path)
      with open(self.unknown_users_path, 'w', encoding='utf-8') as file:
         json.dump(self.unknown_users, file, indent=3)
   
   def load_meta(self, path: pathlib.Path) -> dict[str, typing.Any] | None:
      data = self.load_or(path, None)
      if data is not None:
         data = self.key_by(data, 'id')
      return data
   
   def save_meta(self, data: dict[str, typing.Any], path: pathlib.Path):
      with open(path, 'w', encoding='utf-8') as file:
         json.dump(list(data.values()), file, indent=3)
   
   def fetch_metas(self, client: jira.JIRA, overwrite: bool):
      if overwrite or self.fields is None:
         self.fields = self.key_by(client.fields(), 'id')
      if overwrite or self.projects is None:
         data = [p.raw for p in client.projects(expand='description,lead,url')]
         for project in data:
            self.simplify_user(project, 'lead')
         self.projects = self.key_by(data, 'id')
      if overwrite or self.issue_types is None:
         data = [p.raw for p in client.issue_types()]
         self.issue_types = self.key_by(data, 'id')
      if overwrite or self.resolutions is None:
         data = [p.raw for p in client.resolutions()]
         self.resolutions = self.key_by(data, 'id')
      if overwrite or self.statuses is None:
         data = [p.raw for p in client.statuses()]
         self.statuses = self.key_by(data, 'id')
      if overwrite or self.versions is None:
         projects = client.projects()
         data = [v.raw for p in projects for v in client.project_versions(p.key)]
         self.versions = self.key_by(data, 'id')
      if overwrite or self.link_types is None:
         data = [p.raw for p in client.issue_link_types()]
         self.link_types = self.key_by(data, 'id')
      self.flush_users(client, overwrite)
   
   def fetch_issues(self, client: jira.JIRA, query: str, overwrite: bool):
      self.attachments_folder.mkdir(parents=True, exist_ok=True)
      for issue in get_issues(client, query):
         self.save_issue(client, issue, overwrite)
                     
   def save_issue(self, client: jira.JIRA, issue: jira.Issue, overwrite: bool):
      issue_path = self.get_issue_path(issue.key)
      issue_path.parent.mkdir(parents=True, exist_ok=True)
      data = issue.raw
      if overwrite or not issue_path.exists():
         print(issue.key)
         self.simplify_issue(data)
         self.flush_users(client, overwrite)
      for attachment in issue.fields.attachment:
         attach_path = self.get_attachment_path(attachment.id)
         if overwrite or not attach_path.exists():
            print('\t' + attachment.filename)
            with open(attach_path, 'wb') as file:
               for content in attachment.iter_content():
                  file.write(content)
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
      for comment in fields['comment']['comments']:
         self.simplify_user(comment, 'author')
         self.simplify_user(comment, 'updateAuthor')
      for link in fields['issuelinks']:
         self.simplify_field(link, 'type')
         self.simplify_field(link, 'inwardIssue', 'key')
         self.simplify_field(link, 'outwardIssue', 'key')
      for change in issue['changelog']['histories']:
         self.simplify_user(change, 'author')

   def simplify_user(self, field: dict[str, typing.Any], key: str):
      if field.get(key) is None:
         return
      self.new_users[field[key]['key']] = field[key]
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
   
   def get_attachment_path(self, attach_id: str) -> pathlib.Path:
      return self.attachments_folder / attach_id
   
   def get_issue_path(self, key: str) -> pathlib.Path:
      return self.tickets_folder / key.split('-')[0] / (key + '.json')
   
   def get_user_path(self, key: str) -> pathlib.Path:
      return self.users_folder / (urllib.parse.quote_plus(key) + '.json')
   
   def flush_users(self, client: jira.JIRA, overwrite: bool):
      self.users_folder.mkdir(parents=True, exist_ok=True)
      for key,value in self.new_users.items():
         user_path = self.get_user_path(key)
         if overwrite or not user_path.exists():
            try:
               user = get_user(client, key, expand='groups')
            except jira.exceptions.JIRAError as exc:
               if exc.text == f'The user with the key \'{key}\' does not exist':
                  self.unknown_users[key] = value
                  continue
               raise
            print('\t' + user.raw['name'])
            user_path.parent.mkdir(parents=True, exist_ok=True)
            with open(user_path, 'w', encoding='utf-8') as file:
               json.dump(user.raw, file, indent=3)
      self.new_users = {}
         
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

   def tickets(self, project_key: str) -> typing.Generator[dict[str, typing.Any], None, None]:
      for path in (self.tickets_folder / project_key).iterdir():
         with open(path, 'r', encoding='utf-8') as path:
            yield json.load(path)

   def ticket_names(self, project_key: str) -> typing.Generator[str, None, None]:
      for path in (self.tickets_folder / project_key).iterdir():
         yield path.stem

def populate(dump: Dump):
   print('Connecting...')
   client = get_client()
   print('Fetching metadata...')
   dump.fetch_metas(client, overwrite=False)
   for project in dump.projects.values():
      key = project['key']
      print(key + ':')
      last_ticket = max(map(lambda x: int(x.removeprefix(key + '-')), dump.ticket_names(key)), default=None)
      if last_ticket is None:
         query = f'project = {key} ORDER BY key ASC'
      else:
         query = f'project = {key} AND key > {key}-{last_ticket} ORDER BY key ASC'
      dump.fetch_issues(client, query, overwrite=False)

def fetch(dump: Dump, query: str):
   client = get_client()
   dump.fetch_issues(client, query, overwrite=True)

def check(dump: Dump):
   for project in dump.projects.values():
      print(f'Checking {project['key']}...')
      verify_user(project, 'lead', dump, project['key'])
      for ticket in dump.tickets(project['key']):
         fields = ticket['fields']
         key = ticket['key']
         if dump.projects[fields['project']] != project:
            print(f'Mismatch project: {key}')
         verify_field(fields, 'issuetype', dump.issue_types, key)
         verify_field(fields, 'resolution', dump.resolutions, key)
         verify_field(fields, 'versions', dump.versions, key)
         verify_field(fields, 'fixVersions', dump.versions, key)
         verify_field(fields, 'status', dump.statuses, key)
         verify_user(fields, 'creator', dump, key)
         verify_user(fields, 'reporter', dump, key)
         verify_user(fields, 'assignee', dump, key)
         for attachment in fields['attachment']:
            verify_user(attachment, 'author', dump, key)
            attach_path = dump.get_attachment_path(attachment['id'])
            if not attach_path.exists():
               print(f'{key}: No attachment {attachment['id']}')
         for comment in fields['comment']['comments']:
            verify_user(comment, 'author', dump, key)
            verify_user(comment, 'updateAuthor', dump, key)
         for link in fields['issuelinks']:
            verify_field(link, 'type', dump.link_types, key)
         for change in ticket['changelog']['histories']:
            verify_user(change, 'author', dump, key)

def verify_user(fields: dict[str, typing.Any], key: str, dump: Dump, ticket: str):
   val = fields.get(key)
   if val is not None:
      user = dump.get_user_path(val)
      if not user.exists() and not val in dump.unknown_users:
         print(f'{ticket}: No user {val}')

def verify_field(fields: dict[str, typing.Any], key: str, source: dict[str, typing.Any], ticket: str):
   values = fields.get(key)
   if values is not None:
      if not isinstance(values, list):
         values = [values]
      for val in values:
         if val not in source:
            print(f'{ticket}: Unknown {key}')

def refresh(dump: Dump):
   client = get_client()
   issues = get_issues(client, 'ORDER BY updated DESC')
   for issue in issues:
      existing_date = None
      existing_path = dump.get_issue_path(issue.key)
      if existing_path.exists():
         existing_date = tat.read_json(existing_path)['fields']['updated']
      if existing_date is None or issue.fields.updated > existing_date:
         dump.save_issue(client, issue, True)
      else:
         break

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
