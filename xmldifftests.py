import pathlib
import mojira
import markup
import copy
import lxml.html.soupparser
import lxml.etree
import xmldiff.main
import xmldiff.formatting
from web import new_content_tag
import bs4

def convert(before: bs4.Tag, after: bs4.Tag, name: str):
   print(name)
   soup = bs4.BeautifulSoup()
   before_xml = lxml.html.soupparser.convert_tree(
      new_content_tag(soup, 'html', new_content_tag(soup, 'body', copy.deepcopy(before)))
   )[0]
   before_xml = before_xml[0]
   after_xml = lxml.html.soupparser.convert_tree(
      new_content_tag(soup, 'html', new_content_tag(soup, 'body', copy.deepcopy(after)))
   )[0]
   print(lxml.etree.tostring(after_xml))
   diff = xmldiff.main.diff_trees(before_xml, after_xml,
      diff_options={'fast_match': True},
      formatter=xmldiff.formatting.XMLFormatter(formatting_tags=('b', 'i'), text_tags=('p', 'h1', 'h2', 'h3'))
   )
   diff_soup = bs4.BeautifulSoup(diff, 'lxml').body.children
   print(diff_soup)
   with open('xmldifftests/' + name + '.html', 'w') as file:
      final_soup = bs4.BeautifulSoup()
      final_soup.append(new_content_tag(final_soup, 'html', content=[
         new_content_tag(final_soup, 'head', [final_soup.new_tag('link', attrs={'rel': 'stylesheet', 'href': '/d/Archives/Mojira/web/style.css'})]),
         new_content_tag(final_soup, 'body', [
            before,
            final_soup.new_tag('hr'),
            after,
            final_soup.new_tag('hr'),
            *diff_soup,
         ])
      ]))
      file.write('<!DOCTYPE html>\n')
      file.write(str(final_soup))

def main():
   archive = mojira.Archive(folder=pathlib.Path('/d/Archives/Mojira/data'))
   markup_source = markup.MarkupSource(pathlib.Path('/d/Archives/Mojira/markup'))
   for i, (before, after) in enumerate([
      ('<p>hi there</p>', '<p>hi<a></a> there</p>'),
      ('<p>test</p>', '<h3>blah</h3><p>test</p>'),
      ('<p>testing</p>', '<p><b>testing</b></p>'),
   ]):
      before_soup = bs4.BeautifulSoup(before, 'html.parser')
      after_soup = bs4.BeautifulSoup(after, 'html.parser')
      convert(before_soup, after_soup, 'test' + str(i))
   for issue in archive.issues():
      for revision in issue['changelog']['histories']:
         before, after = markup_source.get_issue_description_revision(issue['id'], revision['id'])
         if before is not None and after is not None:
            convert(before, after, 'ticket/' + issue['id'] + '_' + revision['id'])

if __name__ == '__main__':
   main()
