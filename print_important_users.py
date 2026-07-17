import pathlib
import os

import dotenv

import mojira
import relations

dotenv.load_dotenv()
archive = mojira.Archive(folder=pathlib.Path(os.environ['ARCHIVE_DATA']))
user_rels = relations.UserRelations()
field_rels = relations.FieldRelations()
rels_path = pathlib.Path(os.environ['ARCHIVE_RELATIONS'])
user_rels.load( rels_path / 'user')
field_rels.load(rels_path / 'fields', rels_path / 'metas')

all_users = set([*user_rels.attachments.keys(), *user_rels.changes.keys(), *user_rels.comments.keys(), *user_rels.edits.keys(), *field_rels.metas['reporter'].keys(), *field_rels.metas['creator'].keys(), *field_rels.metas['assignee'].keys()])
all_users.remove('')
results: list[tuple[str, int]] = []
for user in all_users:
   actions = 0
   actions += sum(len(x) for x in user_rels.attachments.get(user, {}).values())
   actions += sum(len(x) for x in user_rels.changes.get(user, {}).values())
   actions += sum(len(x) for x in user_rels.comments.get(user, {}).values())
   actions += sum(len(x) for x in user_rels.edits.get(user, {}).values())
   actions += len(field_rels.metas['reporter'].get(user, []))
   actions += len(field_rels.metas['creator'].get(user, []))
   actions += len(field_rels.metas['assignee'].get(user, []))
   results.append((user, actions))
results.sort(key=lambda x: x[1], reverse=True)
for i, (user, actions) in enumerate(results[:500]):
   print(f'{i+1:<4}{actions:<7}{user}')
   user_data = archive.get_user_data(user)
   assert user_data is not None
   if 'ownerId' not in user_data['avatarUrls']['48x48']:
      print('\tno pfp')
      reported = field_rels.metas['reporter'].get(user, [])
      if len(reported) > 0:
         issue = archive.get_issue_data(reported[0])
         assert issue is not None
         print('\t' + issue['key'])
      assigned = field_rels.metas['assignee'].get(user, [])
      if len(assigned) > 0:
         issue = archive.get_issue_data(assigned[0])
         assert issue is not None
         print('\t' + issue['key'])
