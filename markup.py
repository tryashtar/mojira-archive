import mojira
import tryashtools as tat
import io
import html

def main():
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests()

def convert(text):
   if text.isspace():
      return '&nbsp;'
   parser = MarkupParser(text)
   return parser.parse()

class MarkupParser:
   def __init__(self, text):
      self.stream = io.StringIO(text)
      self.list_stack = ''
      self.formats = set()

   def peek(self, size=1):
      pos = self.stream.tell()
      result = self.stream.read(size)
      self.stream.seek(pos)
      return result

   def read_whitespace(self):
      return self.read_while(lambda x: x.isspace())

   def read_while(self, predicate):
      result = ''
      while True:
         ch = self.peek()
         if ch != '\n' and ch != '' and predicate(ch):
            result += ch
            self.stream.read(1)
            continue
         return result
   
   def parse(self):
      output = io.StringIO('')
      while self.peek() != '':
         self.fresh_line(output)
      self.handle_list(output, '')
      return output.getvalue()
   
   def peek_list_start(self):
      pos = self.stream.tell()
      list_start = self.read_while(lambda x: x in ['*','-','#'])
      after_space = self.read_whitespace()
      if len(list_start) > 0 and len(after_space) > 0:
         result = (list_start, self.stream.tell())
      else:
         result = ('', pos)
      self.stream.seek(pos)
      return result
   
   def handle_list(self, output, list_start):
      index = 0
      for i in range(min(len(self.list_stack), len(list_start))):
         index = i + 1
         current_char = self.list_stack[i]
         next_char = list_start[i]
         if current_char != next_char:
            break
      for ch in self.list_stack[index:]:
         if ch in ['*', '-']:
            output.write('\n</ul>')
         elif ch == '#':
            output.write('\n</ol>')
      if len(self.list_stack) > 0 and len(list_start) == 0:
         output.write('\n')
      for ch in list_start[index:]:
         if ch == '*':
            output.write('<ul>')
         elif ch == '-':
            output.write('<ul class="alternate" type="square">')
         elif ch == '#':
            output.write('<ol>')
      self.list_stack = list_start
   
   def try_list(self, output):
      (list_start, pos) = self.peek_list_start()
      self.handle_list(output, list_start)
      self.stream.seek(pos)
      if len(list_start) > 0:
         output.write('\n')
         output.write('\t' * len(list_start))
         output.write('<li>')
         if not self.try_header(output):
            text = self.read_normal()
            output.write(text)
         output.write('</li>')
         return True
      return False
   
   def try_header(self, output):
      header = self.peek(3)
      if header in ['h1.', 'h2.', 'h3.', 'h4.', 'h5.', 'h6.']:
         output.write('<' + header[:2] + '>')
         self.stream.read(3)
         self.read_whitespace()
         text = self.read_normal()
         output.write('<a name="')
         output.write(text.replace(' ',''))
         output.write('"></a>')
         output.write(text)
         output.write('</' + header[:2] + '>')
         return True
      return False
   
   def fresh_line(self, output):
      whitespace = self.read_whitespace()
      
      if self.try_list(output):
         return
      
      if self.try_header(output):
         return
      
      text = self.read_normal()
      output.write('<p>')
      output.write(whitespace)
      output.write(text)
      output.write('</p>')
   
   def read_normal(self):
      result = ''
      if self.peek() == '{':
         return self.read_block()
      return result
   
   def read_block(self):
      self.stream.read(1)
      block_type = self.read_while(lambda x: x != '}')
      self.stream.read(1)

def check_tests():
   tests = tat.read_json('tests.json')
   failed = 0
   passed = 0
   for test in tests:
      in_text = test['in']
      out_text = convert(in_text)
      expected_text = test['out']
      if out_text != expected_text:
         failed += 1
         print(f'\033[91m❎ Test {test['index']} failed!')
         print(f'\033[91m\tInput:     {repr(in_text)}')
         print(f'\033[91m\tExpected:  {repr(expected_text)}')
         print(f'\033[91m\tGot:       {repr(out_text)}')
      else:
         passed += 1
         print(f'\033[92m✅ Test {test['index']} passed!')
         print(f'\033[92m\tInput:     {repr(in_text)}')
         print(f'\033[92m\tOutput:    {repr(out_text)}')
   print()
   if passed > 0:
      print(f'\033[92m{passed} tests passed')
   if failed > 0:
      print(f'\033[91m{failed} tests failed')

def update_tests():
   client = None
   tests = tat.read_json('tests.json')
   i = 0
   for test in tests:
      if 'out' not in test:
         print(test['in'])
         if client is None:
            client = mojira.get_client()
         result = client._session.post('https://bugs.mojang.com/rest/api/1.0/render', json={"rendererType":"atlassian-wiki-renderer","unrenderedMarkup":test['in'],"issueKey":"MC-1"})
         test['out'] = result.content.decode('utf-8')
      tat.write_text(f'<!DOCTYPE html><html><div style="background-color:#DDD;display:inline-block">\n\n<pre>{html.escape(test['in'])}</pre>\n\n</div><br/><br/><div style="background-color:#CCC;display:inline-block">\n\n{test['out']}\n\n</div></html>', f'markup-tests/{i}.html')
      test['index'] = i
      i += 1
   if client is not None:
      tat.write_json(tests, 'tests.json')

if __name__ == '__main__':
   main()
