import pathlib
import typing
import jira
import jira.exceptions
import json
import urllib.request
import urllib.parse
from jiratypes import Field, Issue, IssueType, LinkType, Project, Resolution, Status, User
from mojira import Archive, ArchiveMetas, key_by
import dotenv
import os

def main():
   dotenv.load_dotenv()
   archive = Archive(pathlib.Path(os.environ['ARCHIVE_DATA']))
   metas = ArchiveMetas()
   users = FetchedUsers()
   key = os.environ['JIRA_KEY']
   print('Connecting...')
   client = jira.JIRA(os.environ['JIRA_URL'], token_auth=key)
   print('Fetching metas...')
   urllib.request.urlretrieve('https://launchermeta.mojang.com/mc/jira/mojira.css', archive.folder / 'assets/mojira.css')
   fetch_metas(metas, users, client)
   flush_users(archive, users, client, dry=False)
   metas.save(archive.folder)
   save_project_avatars(archive, metas, client, dry=False)
   print('Checking issues...')
   issues = fetch_issues(client, 'ORDER BY updated DESC')
   for issue in issues:
      updated = update_issue(archive, users, issue, dry=False)
      flush_users(archive, users, client, dry=False)
      if not updated:
         break

class FetchedUsers:
   new_users: dict[str, dict[str, typing.Any]]

   def __init__(self):
      self.new_users = {}

def fetch_metas(metas: ArchiveMetas, users: FetchedUsers, client: jira.JIRA):
   for field in client.fields():
      metas.import_field(typing.cast(Field, field))
   for issue_type in client.issue_types():
      metas.import_issue_type(typing.cast(IssueType, issue_type.raw))
   for link_type in client.issue_link_types():
      metas.import_link_type(typing.cast(LinkType, link_type.raw))
   for resolution in client.resolutions():
      metas.import_resolution(typing.cast(Resolution, resolution.raw))
   for status in client.statuses():
      metas.import_status(typing.cast(Status, status.raw))
   for entry in client.projects():
      project = client.project(entry.id, expand='description,lead,url').raw
      simplify_user(users, project, 'lead')
      project['versions'] = key_by(project['versions'], 'id')
      assert project is Project
      metas.import_project(project)

def flush_users(archive: Archive, users: FetchedUsers, client: jira.JIRA, dry: bool):
   for key, value in users.new_users.items():
      full_data: User | None = None
      try:
         fetched = fetch_user(client, key, expand='groups').raw
         full_data = typing.cast(User, fetched)
      except jira.exceptions.JIRAError as exc:
         if not exc.text == f'The user with the key \'{key}\' does not exist':
            raise
      if full_data is not None:
         existing = archive.get_user_data(full_data['key'])
         if existing is None:
            print(f'New user: {full_data['displayName']} ({full_data['key']})')
         else:
            print(f'Update user: {full_data['displayName']} ({full_data['key']})')
         archive.import_user(full_data)
         avatar_url = full_data['avatarUrls']['48x48']
         save_avatar(archive, client, archive.users_avatars_folder, avatar_url, dry=dry)
      else:
         existing = archive.get_unknown_user_data(key)
         if existing is None:
            print(f'New unknown user: {key}')
         else:
            print(f'Update unknown user: {key})')
         archive.import_unknown_user(key, value)
   users.new_users.clear()

def update_issue(archive: Archive, users: FetchedUsers, issue: jira.Issue, dry: bool) -> bool:
   existing = archive.get_issue_data(issue.key)
   if existing is not None and issue.fields.updated <= existing['fields']['updated']:
      print(f'Ticket {issue.key} ({issue.id}) already up-to-date')
      return False
   if existing is None:
      print(f'New ticket {issue.key} ({issue.id})')
      print(f'\tDate: {issue.fields.updated}')
   else:
      print(f'Updated ticket {issue.key} ({issue.id})')
      print(f'\tDate: {existing['fields']['updated']} -> {issue.fields.updated}')
   data = issue.raw
   simplify_issue(users, data)
   for attachment in issue.fields.attachment:
      attach_path = archive.get_attachment_data_path(attachment.id)
      # attachments never change
      if not attach_path.exists():
         print(f'\tNew attachment: {attachment.filename} ({attachment.id})')
         if not dry:
            attach_content = archive.get_attachment_content_path(attachment.id, attachment.filename)
            with open(attach_content, 'wb') as file:
               for content in attachment.iter_content():
                  file.write(content)
            with open(attach_path, 'w', encoding='utf-8') as file:
               attachment_data = attachment.raw
               json.dump(attachment_data, file, indent=3)
   if not dry:
      archive.import_issue(typing.cast(Issue, data))
   return True

def save_project_avatars(archive: Archive, metas: ArchiveMetas, client: jira.JIRA, dry: bool):
   for project in metas.projects.values():
      save_avatar(archive, client, archive.project_avatars_folder, project['avatarUrls']['48x48'], dry)

def save_avatar(archive: Archive, client: jira.JIRA, folder: pathlib.Path, url: str, dry: bool):
   if url.startswith('avatar-management'):
      url = 'https://' + url
   avatarid = archive.get_avatar_id(url)
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

def simplify_issue(users: FetchedUsers, issue: dict[str, typing.Any]):
   fields = issue['fields']
   simplify_field(fields, 'issuetype')
   simplify_field(fields, 'project')
   simplify_field(fields, 'resolution')
   simplify_field(fields, 'versions')
   simplify_field(fields, 'fixVersions')
   simplify_field(fields, 'status')
   simplify_user(users, fields, 'creator')
   simplify_user(users, fields, 'reporter')
   simplify_user(users, fields, 'assignee')
   for attachment in fields['attachment']:
      simplify_user(users, attachment, 'author')
   simplify_field(fields, 'attachment')
   for comment in fields['comment']['comments']:
      simplify_user(users, comment, 'author')
      simplify_user(users, comment, 'updateAuthor')
   for link in fields['issuelinks']:
      simplify_field(link, 'type')
      simplify_field(link, 'inwardIssue')
      simplify_field(link, 'outwardIssue')
   for change in issue['changelog']['histories']:
      simplify_user(users, change, 'author')

def simplify_user(users: FetchedUsers, field: dict[str, typing.Any], key: str):
   if field.get(key) is None:
      return
   user_key = field[key]['key']
   users.new_users[user_key] = field[key]
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

def fetch_user(client: jira.JIRA, key: str, expand: str | None) -> jira.User:
   assert client._session is not None
   user = jira.User(
      client._options,
      client._session,
      _query_param='key'
   )
   params = {}
   if expand is not None:
      params['expand'] = expand
   user.find(urllib.parse.quote_plus(key), params=params)
   return user

def fetch_issues(client: jira.JIRA, query: str) -> typing.Generator[jira.Issue]:
   i = 0
   chunk_size = 100
   while True:
      chunk = client.search_issues(query, startAt=i, maxResults=chunk_size, expand='changelog')
      i += chunk_size
      yield from chunk.iterable
      if i >= chunk.total:
         break

if __name__ == '__main__':
   main()
