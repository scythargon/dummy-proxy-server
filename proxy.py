#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, Response
from flask_script import Manager, Server, Command, Option
from bs4 import BeautifulSoup
import requests
import re
import webbrowser
from urlparse import urljoin, urlsplit


def is_visible(element):
    if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
        return False
    elif element.__class__.__name__ == 'Comment':
        return False
    return True


class CustomServer(Server):
    def __init__(self, host, port, site):
        self.host, self.port, self.site = host, port, site
        super(CustomServer, self).__init__(self.host, self.port, use_reloader=True)

    def __call__(self, app):
        server_args = {'processes': 1, 'threaded': False, 'use_debugger': True, 'use_reloader': True, 'host': self.host, 'passthrough_errors': False, 'port': self.port}
        webbrowser.open('http://%s:%s/' % (self.host, self.port))
        app.host, app.port, app.site = self.host, self.port, self.site
        return Server.__call__(self, app, **server_args)


class ArgumentsParser(Command):

    option_list = (
        Option('--host', '-h', dest='host', default='127.0.0.1'),
        Option('--port', '-p', dest='port', default=5000, type=int),
        Option('--site', '-s', dest='site', default='habrahabr.ru'),
    )

    def run(self, host, port, site):
        from ipdb import launch_ipdb_on_exception

        with launch_ipdb_on_exception():
            if not urlsplit(site).scheme:
                site = 'http://' + site
            CustomServer(host, port, site)(app)


what_to_add = u"\u2122"

app = Flask(__name__)
manager = Manager(app)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    url = urljoin(app.site, path)
    regexp = re.compile('([^\W\d]{6,})', re.UNICODE)
    resp = requests.get(url)
    if resp.headers.get('Content-Type') and 'text/html' not in resp.headers.get('Content-Type'):
        print(url, resp.headers.get('Content-Type'))
        return Response(resp.content, mimetype=resp.headers.get('Content-Type'))
    soup = BeautifulSoup(resp.text, "html.parser")
    strings = soup.findAll(string=regexp)
    visible_strings = filter(is_visible, strings)
    for string in visible_strings:
        new_string = re.sub(regexp, '\g<0>%s' % what_to_add, string)
        string.replace_with(new_string)

    site_domain = urlsplit(app.site).netloc
    proxy_domain = 'http://%s:%s/' % (app.host, app.port)
    for link in soup.find_all('a'):
        if not link.get('href'):
            continue
        if not urlsplit(link['href']).scheme:
            link['href'] = urljoin(proxy_domain, link['href'])
        elif site_domain == urlsplit(link['href']).netloc:
            url_parts = urlsplit(link['href'])
            uri = url_parts.path + ('?' + url_parts.query if url_parts.query else '')
            link['href'] = urljoin(proxy_domain, uri)

    return str(soup)


manager.add_command('runserver', ArgumentsParser())


if __name__ == '__main__':
    manager.run()
