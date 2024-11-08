import mojira
import os
import typing
import pathlib
import json

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   check(dump)

def check(dump: mojira.Dump):
   print('Users...')
   for path in dump.users_folder.iterdir():
      if not path.is_dir():
         with open(path, 'r', encoding='utf-8') as file:
            attachment = json.load(file)
            verify_avatar(dump, dump.users_avatars_folder, attachment['avatarUrls']['48x48'], attachment['key'])
   for path in (dump.users_folder / 'unknown').iterdir():
      with open(path, 'r', encoding='utf-8') as file:
         attachment = json.load(file)
         verify_avatar(dump, dump.users_avatars_folder, attachment['avatarUrls']['48x48'], attachment['key'])
   print('Projects...')
   for project in dump.projects.values():
      verify_user(project, 'lead', dump, project['key'])
      verify_avatar(dump, dump.project_avatars_folder, project['avatarUrls']['48x48'], project['key'])
   print('Tickets...')
   for ticket in dump.tickets():
      fields = ticket['fields']
      key = ticket['key']
      verify_field(fields, 'issuetype', dump.issue_types, key)
      verify_field(fields, 'resolution', dump.resolutions, key)
      verify_field(fields, 'versions', dump.projects[fields['project']]['versions'], key)
      verify_field(fields, 'fixVersions', dump.projects[fields['project']]['versions'], key)
      verify_field(fields, 'status', dump.statuses, key)
      verify_user(fields, 'creator', dump, key)
      verify_user(fields, 'reporter', dump, key)
      verify_user(fields, 'assignee', dump, key)
      for attachment in fields['attachment']:
         attach_path = dump.get_attachment_path(attachment, content=False)
         if not attach_path.exists():
            print(f'{key}: No attachment {attachment}')
      for comment in fields['comment']['comments']:
         verify_user(comment, 'author', dump, key)
         verify_user(comment, 'updateAuthor', dump, key)
      for link in fields['issuelinks']:
         verify_field(link, 'type', dump.link_types, key)
         verify_ticket(link, 'inwardIssue', dump, key)
         verify_ticket(link, 'outwardIssue', dump, key)
      for change in ticket['changelog']['histories']:
         verify_user(change, 'author', dump, key)
   print('Attachments...')
   for path in dump.attachments_folder.iterdir():
      if not path.is_dir():
         with open(path, 'r', encoding='utf-8') as file:
            attachment = json.load(file)
            key = attachment['id']
            verify_user(attachment, 'author', dump, key)
            content_path = dump.get_attachment_path(attachment['id'], content=True)
            if not content_path.exists():
               print(f'No content {attachment['id']}')
            else:
               size = os.path.getsize(content_path)
               if size != attachment['size']:
                  print(f'Attachment {attachment['id']} size mismatch: {size} / {attachment['size']}')

def verify_avatar(dump: mojira.Dump, folder: pathlib.Path, url: str, key: str):
   avatarid = dump.get_avatar_id(url)
   filepath = folder / avatarid
   if not filepath.exists():
      print(f'{key}: Missing avatar {avatarid}')
   elif os.path.getsize(filepath) == 0:
      print(f'{key}: 0-size avatar {avatarid}')

def verify_ticket(fields: dict[str, typing.Any], key: str, dump: mojira.Dump, ticket: str):
   val = fields.get(key)
   if val is not None:
      issue = dump.get_issue_path(val)
      if not issue.exists():
         print(f'{ticket}: No {key} issue: {val}')

def verify_user(fields: dict[str, typing.Any], key: str, dump: mojira.Dump, ticket: str):
   val = fields.get(key)
   if val is not None:
      user1 = dump.get_user_path(val, False)
      user2 = dump.get_user_path(val, True)
      if not user1.exists() and not user2.exists():
         print(f'{ticket}: No {key} user: {val}')

def verify_field(fields: dict[str, typing.Any], key: str, source: dict[str, typing.Any], ticket: str):
   values = fields.get(key)
   if values is not None:
      if not isinstance(values, list):
         values = [values]
      for val in values:
         if val not in source:
            print(f'{ticket}: Unknown {key}: {val}')

if __name__ == '__main__':
   main()
