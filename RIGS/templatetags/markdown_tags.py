from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe
import markdown

__author__ = 'ghost'

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text, input_format='html', add_style=""):
    # markdown library can't handle text=None
    if text is None:
        return text
    html = markdown.markdown(text, extensions=['markdown.extensions.nl2br'])
    # Convert format to RML
    soup = BeautifulSoup(html, "html.parser")
    # Prevent code injection
    for script in soup('script'):
        script.string = "Your script shall not pass!"
    if input_format == 'html':
        return mark_safe('<div class="markdown">' + str(soup) + '</div>')
    elif input_format == 'rml':

        # Image aren't supported so remove them
        for img in soup('img'):
            img.parent.extract()

        # <code> should become <font>
        for c in soup('code'):
            c.name = 'font'
            c['face'] = "Courier"

        # blockquotes don't exist but we can still do something to show
        for bq in soup('blockquote'):
            bq.name = 'pre'
            bq.string = bq.text

        for alist in soup.find_all(['ul', 'ol']):
            alist['style'] = alist.name
            for li in alist.find_all('li', recursive=False):
                text = li.find(text=True)
                text.wrap(soup.new_tag('p'))

            if alist.parent.name != 'li':
                indent = soup.new_tag('indent')
                indent['left'] = '0.6cm'

                alist.wrap(indent)

        # Paragraphs have a different tag
        for p in soup('p'):
            p.name = 'para'

        return mark_safe(str(soup))
