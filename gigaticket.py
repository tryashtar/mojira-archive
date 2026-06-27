import typing
import bs4
import pathlib

def main():
   paths = set()
   markup_folder = pathlib.Path('/d/Archives/Mojira/markup')
   out = pathlib.Path('/d/Archives/Mojira/giga.html')
   with open(out, 'w', encoding='utf-8') as out_file:
      for root, dirs, files in markup_folder.walk():
         for path in files:
            with open(root / path, 'r', encoding='utf-8') as file:
               soup = bs4.BeautifulSoup(file, 'html.parser')
            added = False
            for entry in walk_soup(soup):
               path_to = '.'.join([to_str(x) for x in entry.parents])
               if path_to not in paths:
                  print(path_to)
                  paths.add(path_to)
                  if not added:
                     print(root / path)
                     out_file.write('<div class="another-section">' + str(soup) + '</div><hr/>\n')
                     out_file.flush()
                     added = True

def to_str(element: bs4.element.Tag) -> str:
   return element.name + '(' + str(element.attrs.get('style')) + ',' + str(element.attrs.get('class')) + ')'

def walk_soup(soup: bs4.element.Tag) -> typing.Generator[bs4.element.Tag]:
   yield soup
   for entry in soup.children:
      if isinstance(entry, bs4.element.Tag):
         yield from walk_soup(entry)

if __name__ == '__main__':
   main()
