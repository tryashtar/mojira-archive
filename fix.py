import mojira

most_dupes = 0
archive = mojira.get_archive()
for issue in archive.tickets():
   my_dupes = 0
   for entry in issue['changelog']['histories']:
      for change in entry['items']:
         if change['field'] == 'Link' and ((change['toString'] is not None and 'duplicate' in change['toString']) or (change['fromString'] is not None and 'duplicate' in change['fromString'])):
            my_dupes += 1
   if my_dupes > most_dupes:
      most_dupes = my_dupes
      print(issue['key'], my_dupes)
