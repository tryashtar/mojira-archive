import mojira
import os
import typing
import pathlib

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   check(dump)

def check(dump: mojira.Dump):
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
            else:
               size = os.path.getsize(attach_path)
               if size != attachment['size']:
                  print(f'{key}: Attachment size mismatch {attachment['id']}: {size} / {attachment['size']}')
         for comment in fields['comment']['comments']:
            verify_user(comment, 'author', dump, key)
            verify_user(comment, 'updateAuthor', dump, key)
         for link in fields['issuelinks']:
            verify_field(link, 'type', dump.link_types, key)
         for change in ticket['changelog']['histories']:
            verify_user(change, 'author', dump, key)

def verify_user(fields: dict[str, typing.Any], key: str, dump: mojira.Dump, ticket: str):
   val = fields.get(key)
   if val is not None:
      user1 = dump.get_user_path(val, False)
      user2 = dump.get_user_path(val, True)
      if not user1.exists() and not user2.exists():
         print(f'{ticket}: No user {val}')

def verify_field(fields: dict[str, typing.Any], key: str, source: dict[str, typing.Any], ticket: str):
   values = fields.get(key)
   if values is not None:
      if not isinstance(values, list):
         values = [values]
      for val in values:
         if val not in source:
            print(f'{ticket}: Unknown {key} {val}')

if __name__ == '__main__':
   main()
