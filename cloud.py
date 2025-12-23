import jira
import mojira
import re
import json

with open('/d/Documents/Sensitive/mojira key.txt', 'r', encoding='utf-8') as file:
   credentials = [x.rstrip('\n') for x in file.readlines()]
client = jira.JIRA('https://mojira-sandbox-381.atlassian.net', basic_auth=(credentials[0], credentials[1]))

dump = mojira.get_archive()
with open('/d/Archives/Mojira/caches/issue_keys.json', 'r', encoding='utf-8') as file:
   ticket_ids = json.load(file)

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
with open('/d/Archives/Mojira/dump/secret_comments.json', 'w', encoding='utf-8') as file:
   json.dump(results, file)
