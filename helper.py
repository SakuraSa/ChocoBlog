#!/usr/bin/env python
# coding=utf-8

__author__ = 'Rnd495'

import markdown2


def safe_markdown(content):
    content = content.replace('<', '&lt;').replace('>', '&gt;')
    content = markdown2.markdown(content,
                                 extras=["tables",
                                         "code-color",
                                         "code-friendly",
                                         "fenced-code-blocks"])
    content = content.replace("<img", '<img class="img-responsive img-rounded"')
    return content
