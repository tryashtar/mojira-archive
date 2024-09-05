import mojira
import pathlib
import tryashtools as tat

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   client = mojira.get_client()
   fields = ['description', 'customfield_12700', 'environment']
   for ticket in tat.get_files(dump.tickets_folder, True):
      result = {}
      out_path = dump.root_folder / 'markup' / (tat.base_name(ticket) + '.json')
      if out_path.exists():
         continue
      print(tat.base_name(ticket))
      data = tat.read_json(ticket)
      for field in fields:
         if field in data['fields']:
            result[field] = render(client, data['key'], data['fields'][field])
      if 'comment' in data['fields']:
         result['comments'] = []
         for comment in data['fields']['comment']['comments']:
            result['comments'].append(render(client, data['key'], comment['body']))
      if 'changelog' in data:
         result['history'] = []
         for entry in data['changelog']['histories']:
            result['history'].append({})
            for item in entry['items']:
               if item['field'] in fields:
                  fromstr = render(client, data['key'], item['fromString'])
                  tostr = render(client, data['key'], item['toString'])
                  result['history'][-1][item['field']] = {"from":fromstr,"to":tostr}
      tat.write_json(result, out_path)

def render(client, ticket, markup):
   return client._session.post('https://bugs.mojang.com/rest/api/1.0/render', json={"rendererType":"atlassian-wiki-renderer","unrenderedMarkup":markup,"issueKey":ticket}).content.decode('utf-8')

if __name__ == '__main__':
   main()
