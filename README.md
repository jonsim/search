# search
A general purpose, extensible search utility, written in Python.

Copyright &copy; 2017 Jonathan Simmonds

## Dependencies
* Python 2.6+

## Installation
TODO

## License
All files are licensed under the MIT license.

# Documentation
### Usage
```
usage: search [-i] [-f] [-v] [-h] [path] regex

Simple recursive file searcher, wrapping a handful of common find/grep
combos and decorating the output. Ignores .git and .svn directories.

positional arguments:
  path        Optional path to perform the search in. If ommitted the
              current working directory is used.
  regex       Perl-style regular expression to search for. It is
              recommended to pass this in single quotes to prevent
              shell expansion/interpretation of the regex characters.

optional arguments:
  -i          Enable case-insensitive searching.
  -f          Performs the search on the names of files rather than on
              their contents.
  -v          Enable verbose, full replication of the result column,
              even if it means taking multiple lines per match (by
              default the result will be condensed to keep one line per
              match if possible).
  -h, --help  Print this message and exit.
```

### Examples
```sh
search printers 'def search_result.+:'
printers/decorategrep.py:33  def search_result_from_grep(output):
printers/decoratefind.py:16  def search_results_from_find(output):

search -f -i 'e\.md'
./readme-gen/readme-usage.md
./README.md
```
