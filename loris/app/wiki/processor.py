"""processor class
"""

from collections import OrderedDict

import markdown

from loris.app.wiki.utils import wikilink


class Processor(object):
    """
        The processor handles the processing of file content into
        metadata and markdown and takes care of the rendering.

        It also offers some helper methods that can be used for various
        cases.
    """

    preprocessors = []
    postprocessors = [wikilink]

    def __init__(self, text):
        """
            Initialization of the processor.

            :param str text: the text to process
        """
        self.md = markdown.Markdown(extensions=[
            'codehilite',
            'fenced_code',
            'meta',
            'tables'
        ])
        self.input = text
        self.markdown = None
        self.meta_raw = None

        self.pre = None
        self.html = None
        self.final = None
        self.meta = None

    def process_pre(self):
        """
            Content preprocessor.
        """
        current = self.input
        for processor in self.preprocessors:
            current = processor(current)
        self.pre = current

    def process_markdown(self):
        """
            Convert to HTML.
        """
        self.html = self.md.convert(self.pre)

    def split_raw(self):
        """
            Split text into raw meta and content.
        """
        self.meta_raw, self.markdown = self.pre.split('\n\n', 1)

    def process_meta(self):
        """
            Get metadata.

            .. warning:: Can only be called after :meth:`html` was
                called.
        """
        # the markdown meta plugin does not retain the order of the
        # entries, so we have to loop over the meta values a second
        # time to put them into a dictionary in the correct order
        self.meta = OrderedDict()
        for line in self.meta_raw.split('\n'):
            key = line.split(':', 1)[0]
            # markdown metadata always returns a list of lines, we will
            # reverse that here
            self.meta[key.lower()] = \
                '\n'.join(self.md.Meta[key.lower()])

    def process_post(self):
        """
            Content postprocessor.
        """
        current = self.html
        for processor in self.postprocessors:
            current = processor(current)
        self.final = current

    def process(self):
        """
            Runs the full suite of processing on the given text, all
            pre and post processing, markdown rendering and meta data
            handling.
        """
        self.process_pre()
        self.process_markdown()
        self.split_raw()
        self.process_meta()
        self.process_post()

        return self.final, self.markdown, self.meta
