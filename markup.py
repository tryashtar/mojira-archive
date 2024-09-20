import mojira
import tryashtools as tat
import regex
import html

def main():
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests()

class RenderMode:
   def __init__(self):
      self.phrases = True
      self.macros = True
      self.paragraphs = True
      self.linebreaks = True

class RenderContext:
   def __init__(self):
      self.rendered_content = {}
      self.rendered_index = 0
      self.mode_stack = [RenderMode()]
   def get_mode(self):
      return self.mode_stack[-1]
   def push_mode(self, mode: RenderMode):
      self.mode_stack.append(mode)
   def pop_mode(self):
      self.mode_stack.pop()
   def add_rendered(self, text: str, marker: str):
      self.rendered_index += 1
      self.rendered_content[id] = text
      return marker + str(self.rendered_index) + marker

def convert(markup: str, context: RenderContext):
   if len(markup) == 0 or markup.isspace():
      return '&nbsp;'
   return render(markup, context)

def render(markup: str, context: RenderContext):
   if len(markup) == 0:
      return ''
   markup = component_macros(markup, context)
   markup = component_block(markup, context)
   #markup = component_link(markup)
   #markup = component_url(markup)
   #markup = component_camel_link(markup)
   #markup = component_image(markup)
   #markup = component_issue_link(markup)
   #markup = component_backslash_escape(markup)
   #markup = component_html_escape(markup)
   #markup = component_dash(markup)
   #markup = component_emoticon(markup)
   #markup = component_object(markup)
   markup = component_phrase(markup, context, '\\?\\?', '\\?\\?', 'cite')
   markup = component_phrase(markup, context, '\\*', '\\*', 'b')
   markup = component_phrase(markup, context, '\\^', '\\^', 'sup')
   markup = component_phrase(markup, context, '~', '~', 'sub')
   markup = component_phrase(markup, context, '_', '_', 'em')
   markup = component_phrase(markup, context, '-', '-', 'del')
   markup = component_phrase(markup, context, '\\+', '\\+', 'ins')
   markup = component_phrase(markup, context, '\\{\\{', "\\}\\}", 'tt')
   markup = component_force_newline(markup, context)
   markup = component_newline(markup, context)
   #markup = component_token(markup)
   return markup

def component_macros(markup: str, context: RenderContext):
   if not context.get_mode().macros or '{' not in markup:
      return markup
   output = ''
   last_start = 0
   in_escape = False
   i = 0
   while i < len(markup):
      c = markup[i]
      if in_escape:
         in_escape = False
      else:
         if c == '\\':
            in_escape = True
         elif c == '{':
            if len(markup) > i + 1 and markup[i + 1] in '{*?^_-+~':
               i += 1
            elif not markup.isspace() and i > 0 and markup[i - 1] == '$':
               i += 1
            else:
               output += markup[last_start:i]
               last_start = i + 1 # why is this here?
               (i, more) = handle_potential_macro(markup, context, i)
               output += more
               last_start = i + 1
      i += 1
   if last_start < len(markup):
      output += markup[last_start:]
   return output

def handle_potential_macro(markup: str, context: RenderContext, index: int):
   out = ''
   start_tag = make_macro_tag(markup, index)
   if start_tag is None:
      out += '{'
      return (index, out)
   macro_name = start_tag['command'].lower()
   # we may want to store a dict for these with their relevant values
   if macro_name not in ['anchor', 'code', 'quote', 'noformat', 'panel', 'color', 'loremipsum'] or macro_name in ['quote', 'code', 'noformat', 'panel', 'color']:
      set_end_tag(markup, start_tag)
   if 'end_tag' in start_tag:
      end_tag = start_tag['end_tag']
      body = markup[(start_tag['index'] + len(start_tag['original']) - 1):end_tag['index']]
      if body == '\n' and start_tag['newlines'][1] and end_tag['newlines'][0]:
         end_tag['newlines'][0] = False
      out += handle_macro(body, context, start_tag)
      index = end_tag['index'] + len(end_tag['original']) - 1
   else:
      out += handle_macro('', context, start_tag)
      index = start_tag['index'] + len(start_tag['original']) - 1
   return (index, out)
      
def set_end_tag(markup: str, start_tag):
   in_escape = False
   i = start_tag['index']
   while i < len(markup):
      c = markup[i]
      if in_escape:
         in_escape = False
      elif c == '\\':
         in_escape = True
      elif c == '{':
         if len(markup) > 0 and markup[i - 1] == '$':
            end_tag = make_macro_tag(markup, i)
            if end_tag is not None and end_tag['command'] == start_tag['command'] and len(end_tag['args']) != 0:
               start_tag['end_tag'] = end_tag
               return
      i += 1

def handle_macro(body: str, context: RenderContext, start_tag):
   out = ''
   macro_name = start_tag['command'].lower()
   params = make_params(start_tag['args'])
   if macro_name in ['anchor', 'code', 'quote', 'noformat', 'panel', 'color', 'loremipsum']:
      rendered_body = body
      mode = {'anchor':'inline','code':'all','quote':'all','noformat':'html_escape','panel':'all','color':'inline+macros','loremipsum':'none'}
      if mode[macro_name] != 'none':
         # need to convert from these strings to RenderMode bools
         context.push_mode(RenderMode(mode[macro_name]))
         rendered_body = render(body, context)
         context.pop_mode()
      if macro_name == 'anchor':
         (success, result) = macro_anchor(rendered_body, context, params)
         # may want to store these weirdo strings somewhere
         marker = 'inltokxyzkdtnhgnsbdfinltok'
      elif macro_name == 'code':
         # implement all of these
         (success, result) = macro_code(rendered_body, context, params)
         marker = 'blktokxyzkdtnhgnsbdfblktok'
      elif macro_name == 'quote':
         (success, result) = macro_quote(rendered_body, context, params)
         marker = 'ibltokxyzkdtnhgnsbdfibltok'
      elif macro_name == 'noformat':
         (success, result) = macro_noformat(rendered_body, context, params)
         if params.get('nopanel') == 'true':
            marker = 'inltokxyzkdtnhgnsbdfinltok'
         else:
            marker = 'blktokxyzkdtnhgnsbdfblktok'
      elif macro_name == 'panel':
         (success, result) = macro_panel(rendered_body, context, params)
         marker = 'ibltokxyzkdtnhgnsbdfibltok'
      elif macro_name == 'color':
         (success, result) = macro_color(rendered_body, context, params)
         marker = 'inltokxyzkdtnhgnsbdfinltok'
      elif macro_name == 'loremipsum':
         (success, result) = macro_lorem(rendered_body, context, params)
         marker = 'ibltokxyzkdtnhgnsbdfibltok'
      if success:
         out += context.add_rendered(result, marker)
      else:
         # 'exception' handler
         pass
   else:
      rendered_body = render(body, context)
      error_text = 'Unknown macro: {' + start_tag['command'] + '}'
      # figure out what html escape is supposed to be doing
      error_full = '<div class="error"><span class="error">' + html_escape(error_text) + '</span> ' + rendered_body + '</div>'
   return out

def macro_anchor(body: str, context: RenderContext, params: dict[str, str]):
   link = params.get('0', '')
   if link == '':
      return ''
   anchor = ...
   return '<a name="' + anchor + '">' + body + '</a>'

def macro_color(body: str, context: RenderContext, params: dict[str, str]):
   color = trim(params.get('0', ''))
   if len(color) == 0 or color.isspace() or regex.fullmatch("\\w+", color) or regex.fullmatch("^#([\\da-fA-F]){3}$", color) or regex.fullmatch("^#([\\da-fA-F]){6}$", color) or regex.fullmatch("^#rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)$", color) or regex.fullmatch("^#rgb\\((\\d+)%,\\s*(\\d+)%,\\s*(\\d+)%\\)$", color):
      return (True, '<font color="' + color + '">' + body + '</font>')
   return (False, 'Color value is invalid')

def html_escape(text: str):
   pass

def make_params(args: str):
   result = {}
   result[': = | RAW | = :'] = args
   if len(args) == 0:
      return result
   params = regex.split('\\|', args)
   for i in range(len(params)):
      param = params[i]
      if '=' in param:
         index = param.index('=')
         if index == len(param) - 1:
            result[trim(param[:index])] = ''
         else:
            result[trim(param[:index])] = trim(param[(index + 1):])
      else:
         result[str(i)] = param
   return result

def make_macro_tag(markup: str, index: int):
   if markup[index] != '{' or index + 3 > len(markup):
      return None
   in_command = True
   escape_next = False
   command = ''
   args = ''
   i = index + 1
   while i < len(markup):
      c = markup[i]
      if escape_next:
         escape_next = False
      else:
         if c == '}':
            if len(command) == 0 or command.isspace() or command.startswith('$'):
               return None
            original = markup[index:i+1]
            if even_brackets(markup, i):
               return None
            newline_before = index > 0 and markup[index - 1] == '\n'
            newline_after = index + 1 < len(markup) and markup[i +1] == '\n'
            # we may want to make this a real object
            return {'original':original,'index':index,'command':command,'args':args,'newlines':[newline_before, newline_after]}
         elif c in ('\n','\r','\\'):
            escape_next = True
            i += 1
            continue
         elif c == '{':
            return None
         elif c == ':':
            if in_command:
               in_command = False
            else:
               args += ':'
            i += 1
            continue
      if in_command:
         command += c
      else:
         args += c
      i += 1
   return None

def even_brackets(text: str, index: int):
   j = 0
   while index + j < len(text):
      if text[index + j] != '}':
         return j % 2 == 0
      j += 1
   return False

def component_block(markup: str, context: RenderContext):
   if not context.get_mode().paragraphs:
      return markup
   single_line = regex.compile('\\s*[\\p{Alnum}&&[^PLhb]][^\n]*')
   token_pattern = regex.compile('blktokxyzkdtnhgnsbdfblktok\\d+blktokxyzkdtnhgnsbdfblktok')
   if single_line.fullmatch(markup) and token_pattern.search(markup) is None:
      pass

def block_paragraph(paragraph: str, first: bool, context: RenderContext):
   # need to conver this to proper bools mode
   context.push_mode('inline')
   inner = render(paragraph, context)
   context.pop_mode()

def component_phrase(markup: str, context: RenderContext, start_delim: str, end_delim: str, tag_name: str):
   if not context.get_mode().phrases:
      return markup
   pattern = regex.compile('(?:(?:((?<![\\p{L}\\p{Nd}\\\\])|(?<=inltokxyzkdtnhgnsbdfinltok))' + start_delim + ')|\\{' + start_delim + '\\})([^\\s' + start_delim + ']((?!' + end_delim + ')[\\p{L}\\p{Nd}\\p{Z}\\p{S}\\p{M}\\p{P}]*?[^\\s' + end_delim + '])??)(?<!\\\\)(?:(?:' + end_delim + '((?![\\p{L}\\p{Nd}])|(?=inltokxyzkdtnhgnsbdfinltok)))|\\{' + end_delim + '\\})')
   replacement = f'<{tag_name}>\\2</{tag_name}>'
   start_delim = regex.sub('\\\\', '', start_delim)
   end_delim = regex.sub('\\\\', '', end_delim)
   if start_delim not in markup or end_delim not in markup:
      return markup
   markup = pattern.sub(replacement, markup)
   return markup

def component_force_newline(markup: str, context: RenderContext):
   if not context.get_mode().linebreaks:
      return markup
   if '\\\\' in markup:
      markup = regex.sub('(?<!\\\\)\\\\{2}(?!\\S*\\\\)', '<br class="atl-forced-newline" />', markup)
   return markup

def component_newline(markup: str, context: RenderContext):
   if not context.get_mode().linebreaks or '\n' not in markup:
      return markup
   pattern = regex.compile('blktokxyzkdtnhgnsbdfblktok\\d+blktokxyzkdtnhgnsbdfblktok.*')
   output = ''
   lines = markup.splitlines()
   for i in range(len(lines)):
      line = lines[i]
      output += line
      if i < len(lines):
         next_line = lines[i + 1]
         if trim(next_line).startswith('<br') or trim(line).endswith('<br class="atl-forced-newline" />') or pattern.fullmatch(next_line) is not None:
            output += '\n'
         else:
            output += '<br/>'
   return output

def trim(text: str):
   return text.strip(''.join(map(chr, range(0, 0x20 + 1))))

def component_token(markup: str):
   pass

def check_tests():
   tests = tat.read_json('tests.json')
   failed = 0
   passed = 0
   context = RenderContext()
   for test in tests:
      in_text = test['in']
      out_text = convert(in_text, context)
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
