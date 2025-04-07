# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tryashtools",
#     "jira",
#     "pyyaml"
# ]
# [tool.uv.sources]
# tryashtools = { git = "https://github.com/tryashtar/tryashtools" }
# ///
import jira.client
import mojira
import tryashtools as tat
import re

credentials = tat.read_lines('/d/Documents/Sensitive/mojira key.txt')
client = jira.JIRA('https://mojira-sandbox-381.atlassian.net', basic_auth=(credentials[0], credentials[1]))

dump = mojira.get_archive()
ticket_ids = tat.read_json('/d/Archives/Mojira/caches/issue_keys.json')

print('Starting')
results = {}
for i,ticket in enumerate(mojira.get_issues(client, 'ORDER BY created ASC')):
   if i % 1000 == 0:
      print(i)
   downloaded_id = ticket_ids.get(ticket.key)
   if downloaded_id is None:
      print(f'Missing ticket {ticket.key}')
      continue
   downloaded_data = dump.get_issue_data(downloaded_id)
   if downloaded_data is None:
      print(f'Weird missing ticket {ticket.key}')
      continue
   for comment in ticket.fields.comment.comments:
      if re.match(r'(\[\^.*?\]\r?\n?)+', comment.body) is not None:
         continue
      found_body = False
      for potential in downloaded_data['fields']['comment']['comments']:
         if comment.body == potential['body']:
            found_body = True
            break
      if not found_body:
         print(f'Missing comment {ticket.key}: {comment.body}')
         if ticket.key not in results:
            results[ticket.key] = []
         results[ticket.key].append(comment.raw)
tat.write_json(results, '/d/Archives/Mojira/dump/secret_comments.json')
