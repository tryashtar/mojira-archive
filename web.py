import dataclasses
import typing
import bs4
import bs4.element
import pathlib
import urllib.parse
import re
import PIL.Image

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

def make_desc_list(soup: bs4.BeautifulSoup) -> bs4.Tag:
   list = soup.new_tag('dl')
   return list

def append_desc_item(soup: bs4.BeautifulSoup, desc_list: bs4.Tag, name: str | bs4.Tag, value: str | bs4.Tag):
   desc_list.append(new_content_tag(soup, 'dt', new_content_tag(soup, 'label', name)))
   desc_list.append(new_content_tag(soup, 'dd', value))

def make_table(soup: bs4.BeautifulSoup, headings: list[bs4.Tag | str]) -> bs4.Tag:
   table = soup.new_tag('table')
   header = soup.new_tag('tr')
   for head in headings:
      header.append(new_content_tag(soup, 'th', head))
   table.append(header)
   return table

def append_row(soup: bs4.BeautifulSoup, table: bs4.Tag, entries: list[bs4.Tag | str | list[bs4.Tag | str]]) -> bs4.Tag:
   row = soup.new_tag('tr')
   for entry in entries:
      row.append(new_content_tag(soup, 'td', entry))
   table.append(row)
   return row

def make_embed(soup: bs4.BeautifulSoup, path: str | pathlib.PurePath, name: str) -> bs4.Tag:
   if isinstance(path, str):
      match = re.match(r'(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9\_-]+)', path)
      if match is not None:
         return soup.new_tag('iframe', attrs={'src': f'https://www.youtube.com/embed/{match.group(1)}', 'referrerpolicy': 'strict-origin-when-cross-origin'})
      raise ValueError(path)
   ext = path.suffix.lower()
   if ext in ['.gif', '.jpg', '.png', '.webp']:
      return soup.new_tag('img', attrs={'src': urllib.parse.quote(str(path)), 'alt': name})
   if ext in ['.webm', '.mov', '.mkv', '.mp4']:
      return new_content_tag(soup, 'video', soup.new_tag('source', attrs={'src': urllib.parse.quote(str(path))}), attrs={'controls': ''})
   if ext in ['.mp3', '.wav', '.m4a', '.ogg']:
      return new_content_tag(soup, 'audio', soup.new_tag('source', attrs={'src': urllib.parse.quote(str(path))}), attrs={'controls': ''})
   raise ValueError(path)

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

def make_button(soup: bs4.BeautifulSoup, text: str, link: str | None) -> bs4.Tag:
   if link is None:
      return new_content_tag(soup, 'button', text, attrs={'disabled': ''})
   else:
      return new_content_tag(soup, 'a', new_content_tag(soup, 'button', text), attrs={'href': link})

def make_cute_button(soup: bs4.BeautifulSoup, root: pathlib.Path, file: pathlib.PurePath, id: str, name: str, image: pathlib.PurePath, link: pathlib.PurePath) -> bs4.Tag:
   img = soup.new_tag('img', src=relative_link(root, file, image), attrs={'class': f'{id}-link', 'alt': name})
   with PIL.Image.open(root / image) as img_data:
      img['width'] = str(img_data.width)
      img['height'] = str(img_data.height)
   return new_content_tag(soup, 'a', img, attrs={'href': relative_link(root, file, link)})

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

def html_to_text(soup: bs4.BeautifulSoup) -> str:
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
