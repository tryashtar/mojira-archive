import jira.client
import jira.exceptions
import pathlib
import json
import urllib.parse
import typing
import datetime

def main():
   dump = Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   refresh(dump)

class Dump:
   def __init__(self, folder: pathlib.Path):
      self.root_folder = folder
      self.attachments_folder = folder / 'attachments'
      self.tickets_folder = folder / 'tickets'
      self.users_folder = folder / 'users'
      self.project_avatars_folder = folder / 'avatars/projects'
      self.users_avatars_folder = folder / 'avatars/users'
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
   
   def save_metas(self):
      self.root_folder.mkdir(parents=True, exist_ok=True)
      self.save_meta(self.fields, self.fields_path)
      self.save_meta(self.issue_types, self.issue_types_path)
      self.save_meta(self.link_types, self.link_types_path)
      self.save_meta(self.projects, self.projects_path)
      self.save_meta(self.resolutions, self.resolutions_path)
      self.save_meta(self.statuses, self.statuses_path)
      self.save_meta(self.versions, self.versions_path)
      
   def save_project_avatars(self, client: jira.JIRA, overwrite: bool):
      for project in self.projects.values():
         self.save_avatar(client, self.project_avatars_folder, project['avatarUrls']['48x48'], overwrite)
   
   def get_avatar_id(self, url: str):
      url_obj = urllib.parse.urlparse(url)
      queries = urllib.parse.parse_qs(url_obj.query)
      avatarid = queries['avatarId'][0]
      return avatarid
   
   def save_avatar(self, client: jira.JIRA, folder: pathlib.Path, url: str, overwrite: bool):
      avatarid = self.get_avatar_id(url)
      filepath = folder / avatarid
      if overwrite or not filepath.exists():
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
      projects = client.projects(expand='description,lead,url')
      self.fields = self.key_by(client.fields(), 'id')
      project_data = [p.raw for p in projects]
      for project in project_data:
         self.simplify_user(project, 'lead')
      self.projects = self.key_by(project_data, 'id')
      self.issue_types = self.key_by([p.raw for p in client.issue_types()], 'id')
      self.resolutions = self.key_by([p.raw for p in client.resolutions()], 'id')
      self.statuses = self.key_by([p.raw for p in client.statuses()], 'id')
      self.versions = self.key_by([v.raw for p in projects for v in client.project_versions(p.key)], 'id')
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
         self.simplify_field(link, 'inwardIssue')
         self.simplify_field(link, 'outwardIssue')
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
         self.save_user_data(user_path, user_data, overwrite)
         avatar_url = user_data['avatarUrls']['48x48']
         self.save_avatar(client, self.users_avatars_folder, avatar_url, overwrite)
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
         with open(path, 'r', encoding='utf-8') as path:
            yield json.load(path)

   def ticket_names(self) -> typing.Generator[str, None, None]:
      for path in self.tickets_folder.iterdir():
         yield path.stem

def populate(dump: Dump):
   print('Connecting...')
   client = get_client()
   print('Fetching metadata...')
   dump.fetch_metas(client)
   dump.save_metas()
   dump.flush_users(client, overwrite=False)
   print('Finding last stopping point...')
   last_stop = None
   for ticket in dump.tickets():
      created = datetime.datetime.fromisoformat(ticket['fields']['created'])
      if last_stop is None or created > last_stop:
         last_stop = created
   if last_stop is None:
      query = 'ORDER BY created ASC'
   else:
      jira_date = last_stop.strftime('%Y-%m-%d %H:%M')
   # problem: saved tickets use a fixed timezone, but queries are evaluated with the client's timezone
   query = f'created >= "{jira_date}" ORDER BY created ASC'
   print(f'Query: {query}')
   dump.fetch_issues(client, query, overwrite=False)

def fetch(dump: Dump, query: str):
   client = get_client()
   dump.fetch_issues(client, query, overwrite=True)

def refresh(dump: Dump):
   print('Connecting...')
   client = get_client()
   print('Fetching metas...')
   dump.fetch_metas(client)
   dump.save_metas()
   dump.save_project_avatars(client, True)
   print('Checking issues...')
   issues = get_issues(client, 'ORDER BY updated DESC')
   for issue in issues:
      existing_date = None
      existing_path = dump.get_issue_path(issue.id)
      if existing_path.exists():
         with open(existing_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            existing_date = data['fields']['updated']
      if existing_date is None or issue.fields.updated > existing_date:
         print(f'Updated {issue.fields.updated}, last saved {existing_date}')
         dump.save_issue(client, issue, True)
      else:
         print(f'{issue.key} already up-to-date')
         #break

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
