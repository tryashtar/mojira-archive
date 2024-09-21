import mojira
import tryashtools as tat
import regex
import html
import typing

def main():
   print('Updating...')
   update_tests()
   print('Checking...')
   check_tests()

INLINE_TOKEN = 'inltokxyzkdtnhgnsbdfinltok'
BLOCK_TOKEN = 'blktokxyzkdtnhgnsbdfblktok'
INLINE_BLOCK_TOKEN = 'ibltokxyzkdtnhgnsbdfibltok'

class RenderMode:
   ALL: 'RenderMode'
   NONE: 'RenderMode'
   INLINE: 'RenderMode'
   def __init__(self, source: dict[str, bool] | None=None, rest=False):
      source = source or {}
      self.phrases = source.get('phrases', rest)
      self.macros = source.get('macros', rest)
      self.paragraphs = source.get('paragraphs', rest)
      self.linebreaks = source.get('linebreaks', rest)
      self.html_escape = source.get('html_escape', rest)
      self.first_paragraph = source.get('first_paragraph', rest)
      self.links = source.get('links', rest)
   
   def intersect(self, other: 'RenderMode'):
      return self.combine(other, lambda x, y: x and y)
   
   def union(self, other: 'RenderMode'):
      return self.combine(other, lambda x, y: x or y)
   
   def combine(self, other: 'RenderMode', op: typing.Callable[[bool, bool], bool]):
      result = RenderMode()
      result.phrases = op(self.phrases, other.phrases)
      result.macros = op(self.macros, other.macros)
      result.paragraphs = op(self.paragraphs, other.paragraphs)
      result.linebreaks = op(self.linebreaks, other.linebreaks)
      result.html_escape = op(self.html_escape, other.html_escape)
      result.first_paragraph = op(self.first_paragraph, other.first_paragraph)
      result.links = op(self.links, other.links)
      return result
   
RenderMode.ALL = RenderMode(rest=True)
RenderMode.NONE = RenderMode(rest=False)
RenderMode.INLINE = RenderMode(rest=False,source={'phrases':True,'linebreaks':True,'html_escape':True,'links':True})

class RenderContext:
   def __init__(self):
      self.rendered_content = {}
      self.rendered_index = 0
      self.mode_stack = [RenderMode.ALL]
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

class MacroResult:
   def __init__(self, success: bool, result: str, marker: str):
      self.success = success
      self.result = result
      self.marker = marker

class MacroDef:
   def __init__(self, mode: RenderMode | None, body: bool, execute: typing.Callable[[str, RenderContext, dict[str,str]], MacroResult]):
      self.mode = mode
      self.body = body
      self.execute = execute

def macro_anchor(body: str, context: RenderContext, params: dict[str, str]):
   link = params.get('0', '')
   if link == '':
      return MacroResult(True, '', INLINE_TOKEN)
   anchor = summarize(strip_tokens(trim(link)))
   anchor = anchor.replace(' ', '')
   anchor = url_encode(anchor)
   return MacroResult(True, '<a name="' + anchor + '">' + body + '</a>', INLINE_TOKEN)

def summarize(content: str):
   if len(content) == 0:
      return ''
   content = strip_markup(content)
   if 'http://' in content:
      index = content.index('http://')
      if index > 0:
         content = content[:index]
   return summarize_without(content)

def summarize_without(content: str):
   if len(content) == 0:
      return ''

def strip_tokens(text: str):
   pass

def url_encode(text: str):
   pass

def macro_color(body: str, _context: RenderContext, params: dict[str, str]):
   color = trim(params.get('0', ''))
   if len(color) == 0 or color.isspace() or regex.fullmatch(r'\w+', color) or regex.fullmatch(r'^#([\da-fA-F]){3}$', color) or regex.fullmatch(r'^#([\da-fA-F]){6}$', color) or regex.fullmatch(r'^#rgb\((\d+),\s*(\d+),\s*(\d+)\)$', color) or regex.fullmatch(r'^#rgb\((\d+)%,\s*(\d+)%,\s*(\d+)%\)$', color):
      return MacroResult(True, '<font color="' + color + '">' + body + '</font>', INLINE_TOKEN)
   return MacroResult(False, 'Color value is invalid', INLINE_TOKEN)

def macro_quote(body: str, _context: RenderContext, _params: dict[str, str]):
   return MacroResult(True, '<blockquote>' + body + '</blockquote>', INLINE_BLOCK_TOKEN)

def macro_lorem(_body: str, _context: RenderContext, params: dict[str, str]):
   parastr = params.get('paragraphs')
   if parastr is None:
      parastr = params.get('0', '')
   try:
      paragraphs = int(parastr)
   except ValueError:
      try:
         paragraphs = int(float(parastr))
      except ValueError:
         paragraphs = 0
   if paragraphs <= 0:
      paragraphs = 3
   lines = tat.read_lines('lorem.txt')
   paragraphs = min(paragraphs, len(lines))
   result = ''
   for i in range(paragraphs):
      result += '<p>' + lines[i] + '</p>\n'
   return MacroResult(True, result, INLINE_BLOCK_TOKEN)

# finish these
def macro_code(body: str, context: RenderContext, params: dict[str, str]):
   return MacroResult(True, 'TEMP', BLOCK_TOKEN)

def macro_noformat(body: str, context: RenderContext, params: dict[str, str]):
   if params.get('nopanel') == 'true':
      marker = INLINE_TOKEN
   else:
      marker = BLOCK_TOKEN
   return MacroResult(True, 'TEMP', marker)

def macro_panel(body: str, context: RenderContext, params: dict[str, str]):
   return MacroResult(True, 'TEMP', INLINE_BLOCK_TOKEN)

MACROS = {
   'anchor': MacroDef(RenderMode.INLINE, False, macro_anchor),
   'code': MacroDef(RenderMode.ALL, True, macro_code),
   'quote': MacroDef(RenderMode.ALL, True, macro_quote),
   'noformat': MacroDef(RenderMode(source={'html_escape':True},rest=False), True, macro_noformat),
   'panel': MacroDef(RenderMode.ALL, True, macro_panel),
   'color': MacroDef(RenderMode.INLINE.union(RenderMode(source={'macros':True},rest=False)), True, macro_color),
   'loremipsum': MacroDef(None, False, macro_lorem)
}

def convert(markup: str, context: RenderContext):
   if len(markup) == 0 or markup.isspace():
      return '&nbsp;'
   return render(markup, context)

def render(markup: str, context: RenderContext):
   if len(markup) == 0:
      return ''
   markup = component_macros(markup, context)
   markup = component_block(markup, context)
   markup = component_link(markup, context)
   #markup = component_url(markup, context)
   #markup = component_camel_link(markup, context)
   #markup = component_image(markup, context)
   #markup = component_issue_link(markup, context)
   #markup = component_backslash_escape(markup, context)
   #markup = component_html_escape(markup, context)
   markup = component_dash(markup, context)
   #markup = component_emoticon(markup, context)
   #markup = component_object(markup, context)
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
   #markup = component_token(markup, context)
   return markup

def component_link(markup: str, context: RenderContext):
   if not context.get_mode().links:
      return markup
   if len(markup) < 3:
      return markup
   return 'TEMP' # finish

class MacroTag:
   def __init__(self, original: str, index: int, command: str, args: str, newline_before: bool, newline_after: bool):
      self.original = original
      self.start_index = index
      self.command = command
      self.args = args
      self.newline_before = newline_before
      self.newline_after = newline_after
      self.end_index = index + len(original) - 1
      self.macro_name = command.lower()
      self.end_tag: MacroTag | None = None

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
      elif c == '\\':
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
   if start_tag.macro_name not in MACROS or MACROS[start_tag.macro_name].body:
      set_end_tag(markup, start_tag)
   if start_tag.end_tag is not None:
      end_tag = start_tag.end_tag
      body = markup[(start_tag.end_index):(end_tag.start_index)]
      if body == '\n' and start_tag.newline_after and end_tag.newline_before:
         end_tag.newline_before = False
      out += handle_macro(body, context, start_tag)
      index = end_tag.end_index
   else:
      out += handle_macro('', context, start_tag)
      index = start_tag.end_index
   return (index, out)
      
def set_end_tag(markup: str, start_tag: MacroTag):
   in_escape = False
   i = start_tag.start_index
   while i < len(markup):
      c = markup[i]
      if in_escape:
         in_escape = False
      elif c == '\\':
         in_escape = True
      elif c == '{':
         if len(markup) > 0 and markup[i - 1] != '$':
            end_tag = make_macro_tag(markup, i)
            if end_tag is not None and end_tag.command == start_tag.command and len(end_tag.args) != 0:
               start_tag.end_tag = end_tag
               return
      i += 1

def macro_error(context: RenderContext, message: str, body: str):
   rendered_body = render(body, context)
   added = context.add_rendered(rendered_body, BLOCK_TOKEN)
   full_error = '<div class="error"><span class="error">' + html_escape(message) + '</span> ' + added + '</div>'
   return context.add_rendered(full_error, BLOCK_TOKEN)

def handle_macro(body: str, context: RenderContext, start_tag: MacroTag):
   out = ''
   macro_name = start_tag.macro_name
   params = make_params(start_tag.args)
   if macro_name in MACROS:
      rendered_body = body
      mode = MACROS[macro_name].mode
      if mode is not None:
         context.push_mode(mode)
         rendered_body = render(body, context)
         context.pop_mode()
      output = MACROS[macro_name].execute(rendered_body, context, params)
      if output.success:
         out += context.add_rendered(output.result, output.marker)
      else:
         error_text = start_tag.command + ': ' + output.result
         out += macro_error(context, error_text, body)
   else:
      error_text = 'Unknown macro: {' + start_tag.command + '}'
      out += macro_error(context, error_text, body)
   return out

def html_escape(text: str):
   return 'TEMP'

def make_params(args: str):
   result = {}
   result[': = | RAW | = :'] = args
   if len(args) == 0:
      return result
   params = regex.split(r'\|', args)
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
      elif c == '}':
         if len(command) == 0 or command.isspace() or command.startswith('$'):
            return None
         original = markup[index:i+1]
         if even_brackets(markup, i):
            return None
         newline_before = index > 0 and markup[index - 1] == '\n'
         newline_after = i + 1 < len(markup) and markup[i + 1] == '\n'
         return MacroTag(original, index, command, args, newline_before, newline_after)
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
   token_pattern1 = regex.compile(BLOCK_TOKEN + r'\d+' + BLOCK_TOKEN)
   token_pattern2 = regex.compile(INLINE_BLOCK_TOKEN + r'\d+' + INLINE_BLOCK_TOKEN)
   if single_line.fullmatch(markup) and token_pattern1.search(markup) is None and token_pattern2.search(markup) is None:
      paragraph = block_paragraph(markup, True, context)
      return context.add_rendered(paragraph, BLOCK_TOKEN)
   lines = markup.splitlines()
   rendered_lines = []
   paragraph = []
   first_paragraph = True
   i = 0
   while i < len(lines):
      line = lines[i]
      if first_paragraph and len(paragraph) == 0 and not context.get_mode().first_paragraph and len(trim(line)) == 0:
         first_paragraph = False
      else:
         rendered = None
         if regex.fullmatch(r'(\s*' + BLOCK_TOKEN + r'\d+' + BLOCK_TOKEN + r')+\s*', line) or regex.fullmatch(r'(\s*' + INLINE_BLOCK_TOKEN + r'\d+' + INLINE_BLOCK_TOKEN + r')+\s*', line):
            rendered = line
         elif not regex.fullmatch('\\s*[\\p{Alnum}&&[^PLhb]][^\n]*', markup):
            rendered = block_blank(line, context)
            if rendered is None:
               rendered = block_heading(line, context)
            if rendered is None:
               rendered = block_quote(line, context)
            if rendered is None:
               rendered = block_rule(line, context)
            if rendered is None:
               rendered = block_list(line, context)
            if rendered is None:
               rendered = block_table(line, context)
         if rendered is None:
            pass
         #for (String linePortion : BlockRendererComponent.splitLineByBlockTokens(nextLine)) {
         #           if (!TokenType.BLOCK.getTokenPattern().matcher(linePortion).matches()) {
         #               paragraph.add(linePortion);
         #               continue;
         #           }
         #           this.flushParagraph(renderedLines, paragraph, context, firstPara);
         #           renderedLines.add(linePortion);
         #           firstPara = false;
         #       }
         else:
            pass
            #this.flushParagraph(renderedLines, paragraph, context, firstPara);
            #renderedLines.add(rendered);
            #firstPara = false;
      i += 1
   #this.flushParagraph(renderedLines, paragraph, context, firstPara);
   combined = '\n'.join(rendered_lines)
   return context.add_rendered(combined, BLOCK_TOKEN)

def block_blank(line: str, _context: RenderContext):
   if line.isspace():
      return ''
   return None

def block_heading(line: str, context: RenderContext):
   match = regex.fullmatch(r'\s*h([1-6])\.\s*(.*)', line)
   if match is None:
      return None
   level = match.group(1)
   body = match.group(2)
   # finish this

# finish these
def block_quote(line: str, context: RenderContext):
   return None

def block_rule(line: str, _context: RenderContext):
   if regex.fullmatch(r'\s*-{4,5}\s*', line):
      return '<hr />'
   return None

def block_list(line: str, context: RenderContext):
   return None

def block_table(line: str, context: RenderContext):
   return None


def block_paragraph(paragraph: str, first: bool, context: RenderContext):
   context.push_mode(context.get_mode().intersect(RenderMode.INLINE))
   inner = render(paragraph, context)
   context.pop_mode()
   if first and not context.get_mode().first_paragraph:
      return inner
   return '<p>' + inner + '</p>'

def component_dash(markup: str, context: RenderContext):
   if not context.get_mode().phrases:
      return markup
   return 'TEMP' # finish this

def component_phrase(markup: str, context: RenderContext, start_delim: str, end_delim: str, tag_name: str):
   if not context.get_mode().phrases:
      return markup
   pattern = regex.compile(r'(?:(?:((?<![\p{L}\p{Nd}\\])|(?<=' + INLINE_TOKEN + r'))' + start_delim + r')|\{' + start_delim + r'\})([^\s' + start_delim + r']((?!' + end_delim + r')[\p{L}\p{Nd}\p{Z}\p{S}\p{M}\p{P}]*?[^\s' + end_delim + r'])??)(?<!\\)(?:(?:' + end_delim + r'((?![\p{L}\p{Nd}])|(?=' + INLINE_TOKEN + r')))|\{' + end_delim + r'\})')
   replacement = f'<{tag_name}>\\2</{tag_name}>'
   start_delim = regex.sub(r'\\', '', start_delim)
   end_delim = regex.sub(r'\\', '', end_delim)
   if start_delim not in markup or end_delim not in markup:
      return markup
   markup = pattern.sub(replacement, markup)
   return markup

def component_force_newline(markup: str, context: RenderContext):
   if not context.get_mode().linebreaks:
      return markup
   if r'\\' in markup:
      markup = regex.sub(r'(?<!\\)\\{2}(?!\S*\\)', '<br class="atl-forced-newline" />', markup)
   return markup

def component_newline(markup: str, context: RenderContext):
   if not context.get_mode().linebreaks or '\n' not in markup:
      return markup
   pattern = regex.compile(BLOCK_TOKEN + r'\d+' + BLOCK_TOKEN + r'.*')
   output = ''
   lines = markup.splitlines()
   for i in range(len(lines)):
      line = lines[i]
      output += line
      if i + 1 < len(lines):
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
      tat.write_text(f'<!DOCTYPE html><html><head><link rel="stylesheet" href="wiki.css"></head><div style="background-color:#DDD;display:inline-block">\n\n<pre>{html.escape(test['in'])}</pre>\n\n</div><br/><br/><div class="wiki-edit" style="background-color:#CCC;display:inline-block"><div class="wiki-edit-content">\n\n{test['out']}\n\n</div></div></html>', f'markup-tests/{i}.html')
      test['index'] = i
      i += 1
   if client is not None:
      tat.write_json(tests, 'tests.json')

if __name__ == '__main__':
   main()
