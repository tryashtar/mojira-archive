import dataclasses
import datetime
import re
import typing
import bs4
import bs4.element
import pathlib
import urllib.parse
import lxml.html.soupparser
import lxml.etree
import xmldiff.main
import xmldiff.formatting

@dataclasses.dataclass
class Page:
   soup: bs4.BeautifulSoup
   root: bs4.Tag
   head: bs4.Tag
   body: bs4.Tag

@dataclasses.dataclass
class HtmlFile:
   path: pathlib.PurePath
   page: Page = dataclasses.field(repr=False)

def relative_link(root: pathlib.Path, file: pathlib.PurePath, link: pathlib.PurePath) -> str:
   return urllib.parse.quote(str(relative_path(root, file, root / link)))

def relative_path(root: pathlib.Path, file: pathlib.PurePath, link: pathlib.Path) -> pathlib.PurePath:
   return link.relative_to((root / file).parent, walk_up=True)

def write_html(path: pathlib.Path, page: Page):
   path.parent.mkdir(parents=True, exist_ok=True)
   with open(path, 'w', encoding='utf-8') as file:
      file.write('<!DOCTYPE html>\n')
      file.write(str(page.soup))

def add_metadata(file: HtmlFile, title: str | None, description: str | None, image: str | None):
   if title is not None:
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'name': 'title', 'content': title}))
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'property': 'og:title', 'content': title}))
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'property': 'twitter:title', 'content': title}))
   if description is not None:
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'name': 'description', 'content': description}))
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'property': 'og:description', 'content': description}))
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'property': 'twitter:description', 'content': description}))
   if image is not None:
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'property': 'og:image', 'content': image}))
      file.page.head.append(file.page.soup.new_tag('meta', attrs={'property': 'twitter:image', 'content': image}))

def append_desc_item(soup: bs4.BeautifulSoup, desc_list: bs4.Tag, name: str | bs4.Tag, value: str | bs4.Tag):
   desc_list.append(new_content_tag(soup, 'dt', new_content_tag(soup, 'label', name)))
   desc_list.append(new_content_tag(soup, 'dd', value))

def make_table(soup: bs4.BeautifulSoup, headings: list[bs4.Tag | str]) -> bs4.Tag:
   table = soup.new_tag('table')
   thead = soup.new_tag('thead')
   head_row = soup.new_tag('tr')
   for head in headings:
      if isinstance(head, bs4.Tag) and head.name == 'th':
         head_row.append(head)
      else:
         head_row.append(new_content_tag(soup, 'th', head))
   thead.append(head_row)
   table.append(thead)
   tbody = soup.new_tag('tbody')
   table.append(tbody)
   return table

def append_row(soup: bs4.BeautifulSoup, table: bs4.Tag, entries: list[bs4.Tag | str | list[bs4.Tag | str]]) -> bs4.Tag:
   tbody = table.find('tbody')
   assert tbody is not None
   row = soup.new_tag('tr')
   for entry in entries:
      if isinstance(entry, bs4.Tag) and entry.name == 'td':
         row.append(entry)
      else:
         row.append(new_content_tag(soup, 'td', entry))
   tbody.append(row)
   return row

def new_content_tag(soup: bs4.BeautifulSoup, name: str, content: str | bs4.Tag | typing.Iterable[str | bs4.Tag], attrs: dict[str, str] | None=None) -> bs4.Tag:
   tag = soup.new_tag(name, attrs=attrs)
   if isinstance(content, bs4.Tag) or isinstance(content, str):
      tag.append(content)
   else:
      for entry in content:
         tag.append(entry)
   return tag

def make_file(path: pathlib.PurePath, title: str) -> HtmlFile:
   soup = bs4.BeautifulSoup(features='html')
   html = soup.new_tag('html', lang='en')
   soup.append(html)
   head = new_content_tag(soup, 'head', [
      soup.new_tag('meta', charset='utf-8'),
      soup.new_tag('meta', attrs={'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}),
   ])
   html.append(head)
   head.append(new_content_tag(soup, 'title', title))
   body = new_content_tag(soup, 'body', [])
   html.append(body)
   file = HtmlFile(path, Page(soup, html, head, body))
   return file

def is_hidden(tag: bs4.element.PageElement) -> bool:
   parent_tags = (t for t in tag.parents if type(t) is bs4.element.Tag)
   for parent_tag in parent_tags:
      if (parent_tag.name in ('area', 'base', 'basefont', 'datalist', 'head', 'link',
                               'meta', 'noembed', 'noframes', 'param', 'rp', 'script',
                               'source', 'style', 'template', 'track', 'title', 'noscript') or
            parent_tag.has_attr('hidden') or
            (parent_tag.name == 'input' and parent_tag.get('type') == 'hidden')):
               return True
   return False

def map_find_replace(text: str, mapping: dict[str, str]) -> str:
   pattern = re.compile('|'.join(map(re.escape, mapping.keys())))
   return pattern.sub(lambda x: mapping[x.group(0)], text)

def html_find_replace(soup: bs4.Tag, mapping: dict[str, str]):
   for tag in soup.find_all(string=True):
      if isinstance(tag, bs4.element.NavigableString):
         tag.replace_with(map_find_replace(tag.text, mapping))

def html_to_text(soup: bs4.Tag) -> str:
   text: list[str] = []
   for element in soup.descendants:
      if type(element) is bs4.element.NavigableString:
         if is_hidden(element):
            continue
         content = element.string.split()
         if len(content) == 0:
            continue
         string = ' '.join(content)
         if element.parent is not None and element.parent.name == 'p':
            string = '\n' + string
         text.append(string)
   doc = '\n'.join(text)
   return doc

CONTROL_MAP = {chr(i): f'___SUB_CTRL_CHR_{i:04x}___' for i in list(range(32)) + [127] if i not in (9, 10, 13)}
CONTROL_MAP_REV = {v: k for k, v in CONTROL_MAP.items()}

def wrap_text_nodes(root: lxml.etree.Element):
   for child in list(root):
      wrap_text_nodes(child)
   if not isinstance(root.tag, str):
      return
   if len(root) > 0 and root.text is not None and len(root.text.strip()) > 0:
      span = lxml.etree.Element('span')
      span.text = root.text
      root.text = None
      root.insert(0, span)
   for child in list(root):
      if child.tail is not None and len(child.tail.strip()) > 0:
         span = lxml.etree.Element('span')
         span.text = child.tail
         child.tail = None
         root.insert(root.index(child) + 1, span)

def html_diff(soup: bs4.BeautifulSoup, before: bs4.Tag, after: bs4.Tag) -> bs4.Tag:
   # xml throws if the tree has control characters
   # but I want to preserve them, so replace them with substitutes then replace back after
   html_find_replace(before, CONTROL_MAP)
   html_find_replace(after, CONTROL_MAP)
   # convert_tree strips off the top-level tag, so wrap it beforehand
   # diff_trees also works best with a top-level tag, so wrap it another tag too
   before_xml = lxml.html.soupparser.convert_tree(
      new_content_tag(soup, 'html', new_content_tag(soup, 'body', before))
   )[0]
   after_xml = lxml.html.soupparser.convert_tree(
      new_content_tag(soup, 'html', new_content_tag(soup, 'body', after))
   )[0]
   wrap_text_nodes(before_xml)
   wrap_text_nodes(after_xml)
   diff = xmldiff.main.diff_trees(before_xml, after_xml,
      # without fast_match, I tend to get lots of nodes moving around
      diff_options={'fast_match': True},
      formatter=xmldiff.formatting.XMLFormatter()
   )
   # have to use lxml parser to expand self-closing XML tags that aren't valid HTML
   # but it wraps the output in <html><body>...</body></html>, so unwrap the original root
   diff = bs4.BeautifulSoup(diff, 'lxml').find('body')
   assert diff is not None
   diff.name = 'div'
   html_find_replace(diff, CONTROL_MAP_REV)
   return diff

def same_day(day1: datetime.datetime, day2: datetime.datetime) -> bool:
   return day1.astimezone(datetime.UTC).date() == day2.astimezone(datetime.UTC).date()

def render_date_range(soup: bs4.BeautifulSoup, start: datetime.datetime, end: datetime.datetime) -> bs4.Tag:
   if start.astimezone(datetime.UTC) == end.astimezone(datetime.UTC):
      return render_datetime(soup, start)
   else:
      first_part = new_content_tag(soup, 'time', start.strftime('%Y-%m-%d, %I:%M:%S %p'), attrs={'datetime': start.isoformat()})
      if same_day(start, end):
         second_part = end.strftime('%I:%M:%S %p %Z')
      else:
         second_part = render_datetime(soup, end)
      return new_content_tag(soup, 'span', [
         first_part,
         ' - ',
         second_part
      ])

def render_datetime(soup: bs4.BeautifulSoup, date: datetime.datetime) -> bs4.Tag:
   formatted = date.astimezone(datetime.UTC).strftime('%Y-%m-%d, %I:%M:%S %p %Z')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': date.isoformat()})

def render_date(soup: bs4.BeautifulSoup, date: datetime.datetime) -> bs4.Tag:
   formatted = date.astimezone(datetime.UTC).strftime('%Y-%m-%d %Z')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': date.isoformat()})

def render_time(soup: bs4.BeautifulSoup, time: datetime.datetime) -> bs4.Tag:
   formatted = time.astimezone(datetime.UTC).strftime('%I:%M:%S %p')
   return new_content_tag(soup, 'time', formatted, attrs={'datetime': time.isoformat()})

def inline_list(soup: bs4.BeautifulSoup, items: typing.Iterator[bs4.Tag], separator: str = ' ') -> bs4.Tag:
   span = soup.new_tag('span')
   try:
      first = next(items)
   except StopIteration:
      return span
   span.append(first)
   for item in items:
      span.append(separator)
      span.append(item)
   return span
