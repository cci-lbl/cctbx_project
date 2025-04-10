from __future__ import division

"""

word_index_generator (generate an index from html directories)

Generate a multi-page alphabetical HTML word index from a directory tree of HTML files.
Only visible, non-trivial words (excluding stopwords and filtered tokens) are indexed.
Each section page contains navigable links and structured grouping by word prefix.
"""

import os
import re
import html

OK = True
try:
  from bs4 import BeautifulSoup, Comment
  from collections import defaultdict
  from nltk.corpus import stopwords
  import nltk
except Exception as e:
  OK = False

def download_stopwords():
    """Ensure stopwords are available."""
    nltk.download('stopwords')

def get_visible_text(html_content):
    """
    Extracts visible text from HTML content, excluding scripts, styles, comments, and hidden elements.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(['pre', 'script', 'style', 'meta', 'noscript']):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(style=True):
        style = tag['style'].replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()
    body = soup.body or soup
    return body.get_text(separator=' ', strip=True)

def tokenize(text):
    """Tokenize input text into lowercase words."""
    return re.findall(r'\b\w+\b', text.lower())

def get_letter_section(word):
    """Returns the first letter of the word or 'other' if not alphabetic."""
    first = word[0].lower()
    return first if first.isalpha() else "other"

def build_word_index(html_dir, stop_words, exclude_pattern, index_dir):
    """
    Walk the HTML directory and build a word index {word -> set of file paths (up to 5)}
    """
    word_index = defaultdict(set)
    for root, _, files in os.walk(html_dir):
        for file in files:
            if file.endswith(".html"):
                filepath = os.path.abspath(os.path.join(root, file))
                # index_dir must be single level path inside html_dir
                rel_filepath = os.path.join("..",os.path.relpath(
                   filepath,os.path.abspath(html_dir)))
                if filepath.find(index_dir) > -1: continue # skip indexing dirs
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        html_content = f.read()
                        text = get_visible_text(html_content)

                        if not text.strip():
                            print(f"⚠️ No visible text in: {filepath}")
                            continue
                        print(f"✅ Visible text found in: {filepath}")

                        words = tokenize(text)
                        for word in words:
                            if (
                                word not in stop_words and
                                len(word) > 2 and
                                not word[0].isdigit() and
                                not word.startswith("_") and
                                not exclude_pattern.match(word) and
                                word.isascii()
                            ):
                                if len(word_index[word]) < 5:
                                    word_index[word].add(rel_filepath)
                except Exception as e:
                    print(f"⚠️ Skipped {filepath}: {e}")
    return word_index

def generate_html_pages(word_index, index_title, index_dir):
    """
    Generate alphabetically sectioned HTML index files with navigation.
    """
    sorted_words = sorted(word_index.items())
    sectioned_words = defaultdict(list)
    for word, paths in sorted_words:
        section = get_letter_section(word)
        sectioned_words[section].append((word, paths))

    sections_sorted = sorted(sectioned_words.keys())
    overall_file = None
    for section, word_list in sectioned_words.items():
        section_file = os.path.join(index_dir, f"word_index_{section}.html")
        current_index = sections_sorted.index(section)
        prev_section = sections_sorted[current_index - 1] if current_index > 0 else None
        next_section = sections_sorted[current_index + 1] if current_index + 1 < len(sections_sorted) else None

        lines = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'>",
            f"<title>{index_title} Index: - {section.upper()}</title>",
            "<style>",
            "body { font-family: sans-serif; padding: 20px; }",
            "h1 { color: #333; margin-top: 0; }",
            ".nav { position: sticky; top: 0; background: white; padding: 10px 0; }",
            ".nav a { margin-right: 15px; text-decoration: none; font-weight: bold; color: #1a0dab; }",
            "ul { columns: 2; -webkit-columns: 2; -moz-columns: 2; list-style-type: none; padding-left: 0; }",
            "li { margin-bottom: 8px; }",
            "a.wordlink { color: #1a0dab; text-decoration: none; }",
            "h2 { margin-top: 30px; border-bottom: 1px solid #ccc; }",
            "</style>",
            "</head><body>",
            f"<h1>{index_title} Index: {section.upper()}</h1>",
            "<div class='nav'>",
        ]

        # Navigation: back to index.html one directory up, previous/next
        lines.append("<a href='../index.html'>&larr; Back to %s Documentation</a>" %(index_title))
        if prev_section:
            lines.append(f"<a href='word_index_{prev_section}.html'>&larr; Previous ({prev_section.upper()})</a>")
        if next_section:
            lines.append(f"<a href='word_index_{next_section}.html'>Next ({next_section.upper()}) &rarr;</a>")

        lines.append("</div>")
        lines.append("<div class='nav'><strong>Jump to:</strong><br>")
        for sec in sections_sorted:
            lines.append(f"<a href='word_index_{sec}.html'>{sec.upper()}</a>")
        lines.append("</div><ul>")

        current_prefix = ""
        for word, paths in word_list:
            prefix = word[:2].lower()
            if prefix != current_prefix:
                lines.append(f"</ul><h2>{prefix}</h2><ul>")
                current_prefix = prefix

            word_html = f"<strong>{html.escape(word)}</strong>: " + ", ".join(
                f"<a href='{html.escape(path)}' target='_blank'>{os.path.basename(path)}</a>"
                for path in sorted(paths)
            )
            lines.append(f"<li>{word_html}</li>")

        lines += ["</ul></body></html>"]

        with open(section_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Copy section A to index.html for default entry point
        if section == "a":
            overall_file = os.path.join(index_dir, "index.html")
            with open(overall_file,
                 "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        print(f"✅ Created section: {section_file}")

    print("✅ Main index written to '%s'" %(overall_file))

def run(args):
    """
    Entry point: index HTML files in a directory and generate navigable A–Z word index.
    Expects path to directory containing html files, path for index files
    (normally same as path to html files + /index_files/ and
    optional third arg with title

    """
    try:
      html_dir = args[0]
      assert os.path.isdir(html_dir)
      index_dir = args[1]
      assert os.path.relpath(index_dir, html_dir).find(os.path.sep) < 0 # must be single level
      if not os.path.isdir(index_dir):
        os.mkdir(index_dir)
      print("HTML to be read from '%s'" %(html_dir))
      print("Indexing HTML to be written to '%s'" %(index_dir))
    except Exception as e:
      print(
        "Please run with path to directory containing html files as 1st arg"+
         " and path to directory inside that for index files (index_files"+
         " usually)")
      return
    if len(args) > 2:
      index_title = args[2]
      print("Title to use: '%s'" %(index_title))
    else:
      index_title = "Word"

    download_stopwords()
    stop_words = set(stopwords.words('english'))
    exclude_pattern = re.compile(r'^[a-zA-Z][0-9_]')

    word_index = build_word_index(html_dir, stop_words, exclude_pattern,
      index_dir)
    print(f"\n📚 Indexed {len(word_index)} unique words.")
    generate_html_pages(word_index, index_title, index_dir)

if __name__ == "__main__":
  if OK:
    import sys
    run(sys.argv[1:])
  else:
    print("Cannot run word_index_generator without nltk beautifulsoup4 whoosh")

