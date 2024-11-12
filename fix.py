import tryashtools as tat

file = '/d/Archives/Mojira/relations.json'
data = tat.read_json(file)
for user in data['users']:
   user_data = data['users'][user]
   if 'attachments' in user_data:
      print(user)
      user_data['attachments'] = list(sorted(user_data['attachments'].keys()))
tat.write_json(data, file)
