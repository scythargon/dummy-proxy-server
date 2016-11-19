#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request
from bs4 import BeautifulSoup
import requests
import re


app = Flask(__name__)


def is_visible(element):
    if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
        return False
    elif element.__class__.__name__ == 'Comment':
        return False
    return True


site = 'https://habrahabr.ru/'
what_to_add = u"\u2122"


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    url = site + path
    regexp = re.compile('([^\W\d]{6,})', re.UNICODE)
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    strings = soup.findAll(string=regexp)
    visible_strings = filter(is_visible, strings)
    for string in visible_strings:
        new_string = re.sub(regexp, '\g<0>%s' % what_to_add, string)
        string.replace_with(new_string)
    return str(soup)


if __name__ == '__main__':
    app.run(debug=True)
