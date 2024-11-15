import bisect
import os

import jira.client
import jira.exceptions
import pathlib
import json
import urllib.parse
import typing
import orjson

def main():
   archive = get_archive()
   refresh(archive, dry=True)

def get_root():
   return pathlib.Path('/d/Archives/Mojira')

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
         'versions': self.load_or(self.caches_folder / 'versions.json', {})
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

   def save_caches(self, dry: bool):
      if dry:
         return
      with open(self.caches_folder / 'issue_keys.json', 'wb') as file:
         file.write(orjson.dumps(self.ids_cache['issues']))
      with open(self.caches_folder / 'user_keys.json', 'wb') as file:
         file.write(orjson.dumps(self.ids_cache['users']))
      with open(self.caches_folder / 'groups.json', 'wb') as file:
         file.write(orjson.dumps(self.relations_cache['groups']))
      with open(self.caches_folder / 'projects.json', 'wb') as file:
         file.write(orjson.dumps(self.relations_cache['projects']))
      with open(self.caches_folder / 'resolutions.json', 'wb') as file:
         file.write(orjson.dumps(self.relations_cache['resolutions']))
      with open(self.caches_folder / 'users.json', 'wb') as file:
         file.write(orjson.dumps(self.relations_cache['users']))
      with open(self.caches_folder / 'versions.json', 'wb') as file:
         file.write(orjson.dumps(self.relations_cache['versions']))
      with open(self.caches_folder / 'renders.json', 'wb') as file:
         file.write(orjson.dumps(self.render_cache))

   def save_project_avatars(self, client: jira.JIRA, dry: bool):
      for project in self.projects.values():
         self.save_avatar(client, self.project_avatars_folder, project['avatarUrls']['48x48'], dry)
   
   def get_avatar_id(self, url: str):
      url_obj = urllib.parse.urlparse(url)
      queries = urllib.parse.parse_qs(url_obj.query)
      avatarid = queries['avatarId'][0]
      return avatarid
   
   def save_avatar(self, client: jira.JIRA, folder: pathlib.Path, url: str, dry: bool):
      avatarid = self.get_avatar_id(url)
      response = client._session.get(url)
      data = response.content
      if data.startswith(b'<svg') or data.startswith(b'<?xml'):
         filepath = folder / (avatarid + '.svg')
      elif data.startswith(b'\x89PNG\x0d\x0a\x1a\x0a'):
         filepath = folder / (avatarid + '.png')
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
   
   def get_attachment_path(self, attach_id: str) -> pathlib.Path:
      return self.attachments_folder / (attach_id + '.json')
   
   def get_attachment_content_path(self, attach_id: str, file_name: str) -> pathlib.Path:
      extension = os.path.splitext(file_name)[1]
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
               os.remove(unknown_path)
            if not write_path.exists():
               print(f'\tNew user: {user_data['name']} ({user_data['key']})')
            elif user_data != old_data:
               print(f'\tUpdate user: {user_data['name']} ({user_data['key']})')
            old_name = None if old_data is None else old_data['name']
            new_name = user_data['name']
            if old_data is None or old_name != new_name:
               print(f'\t\tUsername: {old_name} -> {new_name}')
               self.ids_cache['users'][new_name] = user_data['key']
               if old_name is not None:
                  self.ids_cache['users'].pop(old_name, None)
            old_groups = self.key_by([] if old_data is None else old_data['groups']['items'], 'name').keys()
            new_groups = self.key_by(user_data['groups']['items'], 'name').keys()
            added_groups = new_groups - old_groups
            removed_groups = old_groups - new_groups
            if len(added_groups) > 0:
               print(f'\t\tGroups: Added {added_groups}')
               for name in added_groups:
                  self.relation_cache_add(['groups', name], user_data['key'])
            if len(removed_groups) > 0:
               print(f'\t\tGroups: Removed {removed_groups}')
               for name in removed_groups:
                  self.relation_cache_remove(['groups', name], user_data['key'])
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

   def relation_cache_navigate(self, path):
      block = self.relations_cache
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

   def relation_cache_add(self, path, value):
      dest = self.relation_cache_navigate(path)
      index = bisect.bisect_left(dest, value)
      if index >= len(dest) or dest[index] != value:
         bisect.insort(dest, value)

   def relation_cache_remove(self, path, value):
      dest = self.relation_cache_navigate(path)
      index = bisect.bisect_left(dest, value)
      if index < len(dest) and dest[index] == value:
         del dest[index]

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
               self.relation_cache_add(['users', attachment.raw['author'], 'attachments', issue.id], attachment.id)
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

         def navigate_dict(dictionary: dict, path: list[str]):
            for entry in path:
               dictionary = dictionary.get(entry)
               if dictionary is None:
                  return None
            return dictionary

         def update_cache(value_path: list[str], name: str, insert_path: typing.Callable[[typing.Any], list[str]], insert: str):
            old_value = None if existing_data is None else navigate_dict(existing_data, value_path)
            new_value = navigate_dict(data, value_path)
            if existing_data is None or old_value != new_value:
               print(f'\t{name}: {old_value} -> {new_value}')
               self.relation_cache_remove(insert_path(old_value), insert)
               self.relation_cache_add(insert_path(new_value), insert)

         def update_cache_list(value_path: list[str], name: str, insert_path: typing.Callable[[typing.Any], list[str]], insert: str):
            old_values = None if existing_data is None else navigate_dict(existing_data, value_path)
            new_values = navigate_dict(data, value_path)
            old_values = set([] if old_values is None else old_values)
            new_values = set([] if new_values is None else new_values)
            added = new_values - old_values
            removed = old_values - new_values
            if len(added) > 0:
               print(f'\t{name}: Added {added}')
               for val in added:
                  self.relation_cache_add(insert_path(val), insert)
            if len(removed) > 0:
               print(f'\t{name}: Removed {removed}')
               for val in removed:
                  self.relation_cache_remove(insert_path(val), insert)

         old_key = None if existing_data is None else existing_data['key']
         new_key = data['key']
         if existing_data is None or old_key != new_key:
            print(f'\tKey: {old_key} -> {new_key}')
            self.ids_cache['issues'][new_key] = issue.id
            if old_key is not None:
               self.ids_cache['issues'].pop(old_key, None)
         update_cache(['fields', 'resolution'], 'Resolution', lambda x: ['resolutions', x], issue.id)
         update_cache(['fields', 'project'], 'Project', lambda x: ['projects', x], issue.id)
         update_cache(['fields', 'creator'], 'Creator', lambda x: ['created', x], issue.id)
         update_cache(['fields', 'reporter'], 'Reporter', lambda x: ['reported', x], issue.id)
         update_cache(['fields', 'assignee'], 'Assignee', lambda x: ['assigned', x], issue.id)
         update_cache_list(['fields', 'versions'], 'Affected', lambda x: ['affected', x], issue.id)
         update_cache_list(['fields', 'fixVersions'], 'Fixed', lambda x: ['fixed', x], issue.id)
         old_comments = self.key_by([] if existing_data is None else navigate_dict(existing_data, ['fields', 'comment', 'comments']), 'id')
         new_comments = self.key_by(navigate_dict(data, ['fields', 'comment', 'comments']), 'id')
         added_comments = new_comments.keys() - old_comments.keys()
         removed_comments = old_comments.keys() - new_comments.keys()
         shared_comments = set.intersection(set(new_comments.keys()), set(old_comments.keys()))
         if len(added_comments) > 0:
            print(f'\tComments: Added {added_comments}')
            for key in added_comments:
               comment = new_comments[key]
               self.relation_cache_add(['users', comment.get('author'), 'comments', issue.id], key)
               self.relation_cache_add(['users', comment.get('updateAuthor'), 'edits', issue.id], key)
         if len(removed_comments) > 0:
            print(f'\tComments: Removed {removed_comments}')
            for key in removed_comments:
               comment = old_comments[key]
               self.relation_cache_remove(['users', comment.get('author'), 'comments', issue.id], key)
               self.relation_cache_remove(['users', comment.get('updateAuthor'), 'edits', issue.id], key)
         for key in shared_comments:
            old_comment = old_comments[key]
            new_comment = old_comments[key]
            # possibly impossible for author to change, updateAuthor can though
            if old_comment.get('author') != new_comment.get('author'):
               print(f'\tComment {key} author: {old_comment.get('author')} -> {new_comment.get('author')}')
               self.relation_cache_add(['users', new_comment.get('author'), 'comments', issue.id], key)
               self.relation_cache_remove(['users', old_comment.get('author'), 'comments', issue.id], key)
            if old_comment.get('updateAuthor') != new_comment.get('updateAuthor'):
               print(f'\tComment {key} author: {old_comment.get('updateAuthor')} -> {new_comment.get('updateAuthor')}')
               self.relation_cache_add(['users', new_comment.get('updateAuthor'), 'edits', issue.id], key)
               self.relation_cache_remove(['users', old_comment.get('updateAuthor'), 'edits', issue.id], key)
         # assume history is append-only (entries are never removed or modified)
         old_history = self.key_by([] if existing_data is None else navigate_dict(existing_data, ['changelog', 'histories']), 'id')
         new_history = self.key_by(navigate_dict(data, ['changelog', 'histories']), 'id')
         added_history = new_history.keys() - old_history.keys()
         if len(added_history) > 0:
            print(f'\tHistory: Added {added_history}')
            for key in added_history:
               change = new_history[key]
               self.relation_cache_add(['users', change['author'], 'changes', issue.id], key)
               for item in change['items']:
                  if item['field'] == 'Key':
                     self.ids_cache['issues'][item['fromString']] = issue.id
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
   print('Fetching metas...')
   css = client._session.get('https://launchermeta.mojang.com/mc/jira/mojira.css')
   if not dry:
      with open(dump.dump_folder / 'assets/mojira.css', 'wb') as css_file:
         css_file.write(css.content)
   dump.fetch_metas(client)
   dump.save_metas(dry=dry)
   dump.save_project_avatars(client, dry=dry)
   print('Checking issues...')
   issues = get_issues(client, 'ORDER BY updated DESC')
   for issue in issues:
      result = dump.update_issue(client, issue, dry=dry)
      dump.save_caches(dry=dry)
      if not result:
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
