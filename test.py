import tryashtools as tat

for file in tat.get_files('/d/Archives/Mojira/dump/tickets/BDS/'):
   data = tat.read_json(file)
   if data['fields'].get('assignee') is not None:
      data['fields']['assignee'] = data['fields']['assignee']['key']
      tat.write_json(data, file)

