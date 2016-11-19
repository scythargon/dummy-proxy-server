#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request
from flask_script import Manager, Server
from bs4 import BeautifulSoup
import requests
import re
import webbrowser


def is_visible(element):
    if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
        return False
    elif element.__class__.__name__ == 'Comment':
        return False
    return True


class CustomServer(Server):
    def __call__(self, app, *args, **kwargs):
        webbrowser.open('http://127.0.0.1:5000/')
        return Server.__call__(self, app, *args, **kwargs)


site = 'https://habrahabr.ru/'
what_to_add = u"\u2122"

app = Flask(__name__)
manager = Manager(app)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    url = site + path
    regexp = re.compile('([^\W\d]{6,})', re.UNICODE)
    resp = requests.get(url)
    if resp.headers.get('Content-Type') and 'text/html' not in resp.headers.get('Content-Type'):
        return resp.content
    soup = BeautifulSoup(resp.text, "html.parser")
    strings = soup.findAll(string=regexp)
    visible_strings = filter(is_visible, strings)
    for string in visible_strings:
        new_string = re.sub(regexp, '\g<0>%s' % what_to_add, string)
        string.replace_with(new_string)
    return str(soup)


manager.add_command('runserver', CustomServer(use_reloader=True))


if __name__ == '__main__':
    manager.run()
