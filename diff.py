import re

import bs4
import bs4.element
import lxml.etree
import lxml.html.soupparser
import xmldiff.formatting
import xmldiff.main


def html_diff(soup: bs4.BeautifulSoup, before: bs4.Tag, after: bs4.Tag) -> bs4.Tag:
   # xml throws if the tree has control characters
   # but I want to preserve them, so replace them with substitutes then replace back after
   html_find_replace(before, CONTROL_MAP)
   html_find_replace(after, CONTROL_MAP)
   # convert_tree strips off the top-level tag, so wrap it beforehand
   # diff_trees also works best with a top-level tag, so wrap it another tag too
   before_wrapped1 = soup.new_tag('html')
   before_wrapped2 = soup.new_tag('body')
   before_wrapped2.append(before)
   before_wrapped1.append(before_wrapped2)
   before_xml = lxml.html.soupparser.convert_tree(before_wrapped1)[0]
   after_wrapped1 = soup.new_tag('html')
   after_wrapped2 = soup.new_tag('body')
   after_wrapped2.append(after)
   after_wrapped1.append(after_wrapped2)
   after_xml = lxml.html.soupparser.convert_tree(after_wrapped1)[0]
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
   if 'xmlns:diff' in diff.attrs:
      del diff.attrs['xmlns:diff']
   for tag in diff.find_all(name='diff:delete'):
      tag.name = 'del'
      append_class(tag, 'diff-delete')
   for tag in diff.find_all(name='diff:insert'):
      tag.name = 'ins'
      append_class(tag, 'diff-insert')
   for tag in diff.find_all(attrs={'diff:delete': True}):
      del tag.attrs['diff:delete']
      append_class(tag, 'diff-delete')
   for tag in diff.find_all(attrs={'diff:insert': True}):
      del tag.attrs['diff:insert']
      append_class(tag, 'diff-insert')
   for tag in diff.find_all(attrs={'diff:rename': True}):
      del tag.attrs['diff:rename']
   return diff

def map_find_replace(text: str, mapping: dict[str, str]) -> str:
   pattern = re.compile('|'.join(map(re.escape, mapping.keys())))
   return pattern.sub(lambda x: mapping[x.group(0)], text)

def html_find_replace(soup: bs4.Tag, mapping: dict[str, str]):
   for tag in soup.find_all(string=True):
      if isinstance(tag, bs4.element.NavigableString):
         tag.replace_with(map_find_replace(tag.text, mapping))

CONTROL_MAP = {chr(i): f'___SUB_CTRL_CHR_{i:04x}___' for i in list(range(32)) + [127, 57346, 57348, 57350] if i not in (9, 10, 13)}
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

def append_class(tag: bs4.Tag, cls: str):
   if 'class' in tag.attrs:
      if isinstance(tag.attrs['class'], str):
         tag.attrs['class'] = tag.attrs['class'] + ' ' + cls
      elif isinstance(tag.attrs['class'], list):
         tag.attrs['class'].append(cls)
   else:
      tag.attrs['class'] = cls
