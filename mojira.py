import jira.client
import jira.exceptions
import pathlib
import json
import urllib.parse
import urllib.request
import typing

def main():
   archive = get_archive()
   refresh(archive, dry=False)

def get_root():
   return pathlib.Path('/d/Archives/Mojira/NEW')

def get_archive():
   return Archive(get_root())

class Archive:
   def __init__(self, folder: pathlib.Path):
      self.root_folder = folder
      self.dump_folder = folder / 'dump'
      self.attachments_folder = self.dump_folder / 'attachments'
      self.attachments_content_folder = self.attachments_folder / 'content'
      self.tickets_folder = self.dump_folder / 'tickets'
      self.users_folder = self.dump_folder / 'users'
      self.unknown_users_folder = self.users_folder / 'unknown'
      self.project_avatars_folder = self.dump_folder / 'avatars/projects'
      self.users_avatars_folder = self.dump_folder / 'avatars/users'
      self.new_users = {}
      self.seen_users = set()

      self.fields_path = self.dump_folder / 'fields.json'
      self.fields = self.load_meta(self.fields_path)
      self.issue_types_path = self.dump_folder / 'issue_types.json'
      self.issue_types = self.load_meta(self.issue_types_path)
      self.link_types_path = self.dump_folder / 'link_types.json'
      self.link_types = self.load_meta(self.link_types_path)
      self.projects_path = self.dump_folder / 'projects.json'
      self.projects = self.load_meta(self.projects_path)
      for project in self.projects.values():
         project['versions'] = self.key_by(project['versions'], 'id')
      self.resolutions_path = self.dump_folder / 'resolutions.json'
      self.resolutions = self.load_meta(self.resolutions_path)
      self.statuses_path = self.dump_folder / 'statuses.json'
      self.statuses = self.load_meta(self.statuses_path)

      self.caches_folder = self.root_folder / 'caches'
      self.ids_cache = {
         'issues': self.load_or(self.caches_folder / 'issue_keys.json', {}),
         'users': self.load_or(self.caches_folder / 'user_keys.json', {})
      }
      self.relations_cache = {
         'groups': self.load_or(self.caches_folder / 'groups.json', {}),
         'projects': self.load_or(self.caches_folder / 'projects.json', {}),
         'resolutions': self.load_or(self.caches_folder / 'resolutions.json', {}),
         'users': self.load_or(self.caches_folder / 'users.json', {}),
         'versions': self.load_or(self.caches_folder / 'versions.json', {}),
         'labels': self.load_or(self.caches_folder / 'labels.json', {}),
         'categories': self.load_or(self.caches_folder / 'categories.json', {}),
         'confirmation': self.load_or(self.caches_folder / 'confirmation.json', {}),
         'priority': self.load_or(self.caches_folder / 'priority.json', {}),
         'area': self.load_or(self.caches_folder / 'area.json', {})
      }
      self.render_cache = self.load_or(self.caches_folder / 'renders.json', {})

   def save_metas(self, dry: bool):
      if dry:
         return
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

   def save_project_avatars(self, client: jira.JIRA, dry: bool):
      for project in self.projects.values():
         self.save_avatar(client, self.project_avatars_folder, project['avatarUrls']['48x48'], dry)

   def get_avatar_id(self, url: str):
      if '/universal_avatar/' in url:
         return url.split('/')[-1]
      if 'atl-paas.net' in url:
         return url.split('/')[-2]
      url_obj = urllib.parse.urlparse(url)
      if 'gravatar.com' in url:
         return url_obj.path.split('/')[-1]
      queries = urllib.parse.parse_qs(url_obj.query)
      avatarid = queries['avatarId'][0]
      return avatarid

   def save_avatar(self, client: jira.JIRA, folder: pathlib.Path, url: str, dry: bool):
      if url.startswith('avatar-management'):
         url = 'https://' + url
      avatarid = self.get_avatar_id(url)
      svgpath = folder / (avatarid + '.svg')
      pngpath = folder / (avatarid + '.png')
      jpgpath = folder / (avatarid + '.jpg')
      if svgpath.exists() or pngpath.exists() or jpgpath.exists():
         return
      print(f'Saving avatar {url}')
      assert client._session is not None
      response = client._session.get(url)
      data = response.content
      if data.startswith(b'<svg') or data.startswith(b'<?xml'):
         filepath = svgpath
      elif data.startswith(b'\x89PNG\x0d\x0a\x1a\x0a'):
         filepath = pngpath
      elif data.startswith(b'\xff\xd8'):
         filepath = jpgpath
      else:
         raise ValueError(data)
      if not filepath.exists():
         print('\tAvatar: ' + avatarid)
         if not dry:
            folder.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'wb') as file:
               file.write(data)

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

   def fetch_issues(self, client: jira.JIRA, query: str, dry: bool):
      if not dry:
         self.attachments_folder.mkdir(parents=True, exist_ok=True)
         self.tickets_folder.mkdir(parents=True, exist_ok=True)
      for issue in get_issues(client, query):
         self.update_issue(client, issue, dry=dry)

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
      user_key = field[key]['accountId']
      if user_key not in self.seen_users:
         self.new_users[user_key] = field[key]
      self.simplify_field(field, key, 'accountId')

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
      return self.attachments_folder / (attach_id + '.json')

   def get_attachment_content_path(self, attach_id: str, file_name: str) -> pathlib.Path:
      extension = pathlib.PurePath(file_name).suffix
      return self.attachments_content_folder / (attach_id + extension)

   def get_issue_data(self, issue_id: str):
      path = self.get_issue_path(issue_id)
      if not path.exists():
         return None
      with open(path, 'r', encoding='utf-8') as file:
         return json.load(file)

   def get_user_data(self, user_key: str):
      known = self.get_user_path(user_key, unknown=False)
      unknown = self.get_user_path(user_key, unknown=False)
      if known.exists():
         with open(known, 'r', encoding='utf-8') as file:
            return json.load(file)
      elif unknown.exists():
         with open(known, 'r', encoding='utf-8') as file:
            return json.load(file)
      return None

   def get_issue_path(self, issue_id: str) -> pathlib.Path:
      return self.tickets_folder / (issue_id + '.json')

   def get_user_path(self, key: str, unknown=False) -> pathlib.Path:
      base_folder = self.unknown_users_folder if unknown else self.users_folder
      return base_folder / (urllib.parse.quote_plus(key) + '.json')

   def flush_users(self, client: jira.JIRA, dry: bool):
      for key,value in self.new_users.items():
         known_path = self.get_user_path(key, unknown=False)
         unknown_path = self.get_user_path(key, unknown=True)
         write_path = known_path
         try:
            user_data = get_user(client, key, expand='groups').raw
         except jira.exceptions.JIRAError as exc:
            if exc.text == f'The user with the key \'{key}\' does not exist':
               user_data = value
               write_path = unknown_path
            else:
               raise
         if user_data is not None:
            old_data = None
            if known_path.exists():
               with open(known_path, 'r', encoding='utf-8') as file:
                  old_data = json.load(file)
            elif unknown_path.exists():
               with open(unknown_path, 'r', encoding='utf-8') as file:
                  old_data = json.load(file)
            if not dry and unknown_path.exists():
               unknown_path.unlink()
            if not write_path.exists():
               print(f'\tNew user: {user_data['displayName']} ({user_data['accountId']})')
            elif user_data != old_data:
               print(f'\tUpdate user: {user_data['displayName']} ({user_data['accountId']})')
            if not dry:
               self.users_folder.mkdir(parents=True, exist_ok=True)
               with open(write_path, 'w', encoding='utf-8') as file:
                  json.dump(user_data, file, indent=3)
            avatar_url = user_data['avatarUrls']['48x48']
            self.save_avatar(client, self.users_avatars_folder, avatar_url, dry=dry)
         self.seen_users.add(key)
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

   def tickets(self) -> typing.Generator[dict[str, typing.Any], None, None]:
      for path in self.tickets_folder.iterdir():
         with open(path, 'r', encoding='utf-8') as file:
            yield json.load(file)

   def ticket_names(self) -> typing.Generator[str, None, None]:
      for path in self.tickets_folder.iterdir():
         yield path.stem

   def update_issue(self, client: jira.JIRA, issue: jira.Issue, dry: bool):
      existing_data = None
      issue_path = self.get_issue_path(issue.id)
      if issue_path.exists():
         with open(issue_path, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
      if existing_data is None or issue.fields.updated > existing_data['fields']['updated']:
         if existing_data is None:
            print(f'New ticket {issue.key} ({issue.id})')
            print(f'\tDate: {issue.fields.updated}')
         else:
            print(f'Updated ticket {issue.key} ({issue.id})')
            print(f'\tDate: {existing_data['fields']['updated']} -> {issue.fields.updated}')
         data = issue.raw
         self.simplify_issue(data)
         self.flush_users(client, dry=dry)
         for attachment in issue.fields.attachment:
            attach_path = self.get_attachment_path(attachment.id)
            # attachments never change
            if not attach_path.exists():
               print(f'\tNew attachment: {attachment.filename} ({attachment.id})')
               if not dry:
                  attach_content = self.get_attachment_content_path(attachment.id, attachment.filename)
                  with open(attach_content, 'wb') as file:
                     for content in attachment.iter_content():
                        file.write(content)
                  with open(attach_path, 'w', encoding='utf-8') as file:
                     attachment_data = attachment.raw
                     json.dump(attachment_data, file, indent=3)
         if not dry:
            with open(issue_path, 'w', encoding='utf-8') as file:
               json.dump(data, file, indent=3)
         return True
      else:
         print(f'Ticket {issue.key} ({issue.id}) already up-to-date')
         return False

def fetch_issues(dump: Archive, query: str, dry: bool):
   print('Connecting...')
   client = get_client()
   print('Fetching issues...')
   dump.fetch_issues(client, query, dry=dry)

def fetch_users(dump: Archive, users: list[str], dry: bool):
   print('Connecting...')
   client = get_client()
   print('Fetching users...')
   for user in users:
      dump.new_users[user] = None
   dump.flush_users(client, dry=dry)

def refresh(dump: Archive, dry: bool):
   print('Connecting...')
   client = get_client()
   while True:
         print('Fetching metas...')
         if not dry:
            urllib.request.urlretrieve('https://launchermeta.mojang.com/mc/jira/mojira.css', dump.dump_folder / 'assets/mojira.css')
         dump.fetch_metas(client)
         dump.save_metas(dry=dry)
         dump.save_project_avatars(client, dry=dry)
         print('Checking issues...')
         issues = get_issues(client, 'ORDER BY updated DESC')
         for i,issue in enumerate(issues):
            result = dump.update_issue(client, issue, dry=dry)
            if not result:
               pass

def get_client() -> jira.JIRA:
   with open('/d/Documents/Sensitive/new mojira key.txt', 'r', encoding='utf-8') as file:
      email,password = file.read().splitlines()
   client = jira.JIRA('https://mojira.atlassian.net', basic_auth=(email, password))
   return client

def get_user(client: jira.JIRA, key: str, expand: str | None) -> jira.User:
   assert client._session is not None
   user = jira.User(
      client._options,
      client._session,
      _query_param="accountId"
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
