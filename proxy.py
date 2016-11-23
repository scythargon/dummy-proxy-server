#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

import webbrowser

from urlparse import urljoin, urlsplit

from bs4 import BeautifulSoup

from flask import Flask, Response

from flask_script import Command, Manager, Option, Server

import requests

from w3lib.html import replace_entities


def is_visible(element):
    if element.parent.name in ['style', 'script', '[document]', 'head',
                               'title']:
        return False
    elif element.__class__.__name__ == 'Comment':
        return False
    return True


class CustomDummyCache():
    """
    there is another interesting approach though:
    you can ask Cache object directly for a url content,
    and if we don't have it in cache - it is the cache who will make a request
    to fetch it, but I find it a bit perverted from control reversion and
    incapsulation point of view

    also, usually you calculate an e.g. md5 hashes from your urls and use it as
    cache keys
    yeeeeah and Redis and expiring mechanism that makes all of it super fun and
    buggy
    """
    def __init__(self):
        self.storage = {}

    def is_cached(self, url):
        return url in self.storage

    def get(self, url):
        print('using cache!')
        return self.storage.get(url)

    def store(self, url, content_type, data):
        self.storage[url] = {'content_type': content_type, 'data': data}


class CustomServer(Server):
    def __init__(self, host, port, site, use_cache, with_reloader):
        self.host, self.port, self.site, self.use_cache, self.with_reloader = \
            host, port, site, use_cache, with_reloader
        super(CustomServer, self).__init__(self.host, self.port,
                                           use_reloader=with_reloader)

    def __call__(self, app):
        server_args = {'processes': 1, 'threaded': False, 'use_debugger': True,
                       'use_reloader': self.with_reloader, 'host': self.host,
                       'passthrough_errors': False, 'port': self.port}
        webbrowser.open('http://%s:%s/' % (self.host, self.port))
        app.host, app.port, app.site, app.use_cache = self.host, self.port, \
            self.site, self.use_cache
        if self.use_cache:
            app.cache = CustomDummyCache()
        return Server.__call__(self, app, **server_args)


class ArgumentsParser(Command):

    option_list = (
        Option('--host', '-h', dest='host', default='127.0.0.1'),
        Option('--port', '-p', dest='port', default=5000, type=int),
        Option('--site', '-s', dest='site', default='habrahabr.ru'),
        Option('--cache', '-c', dest='use_cache', default=False,
               action='store_true'),
        Option('--reloader', '-r', dest='with_reloader', default=False,
               action='store_true'),
    )

    def run(self, host, port, site, use_cache, with_reloader):
        if not urlsplit(site).scheme:
            site = 'http://' + site
        CustomServer(host, port, site, use_cache, with_reloader)(app)


what_to_add = u"\u2122"
app = Flask(__name__)
manager = Manager(app)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    url = urljoin(app.site, path)
    regexp = re.compile('(^|\s)([^\W\d]{6})($|\s)', re.UNICODE)

    if app.use_cache and app.cache.is_cached(url):
        cached = app.cache.get(url)
        return Response(cached['data'], mimetype=cached['content_type'])

    resp = requests.get(url)
    if resp.headers.get('Content-Type') and \
       'text/html' not in resp.headers.get('Content-Type'):
        if app.use_cache:
            app.cache.store(url, resp.headers.get('Content-Type'),
                            resp.content)
        return Response(resp.content,
                        mimetype=resp.headers.get('Content-Type'))

    soup = BeautifulSoup(resp.text, "html.parser")
    strings = soup.findAll(string=regexp)
    visible_strings = filter(is_visible, strings)
    for string in visible_strings:
        new_string = re.sub(regexp, '\g<1>\g<2>%s\g<3>' % what_to_add, string)
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
            uri = url_parts.path + \
                ('?' + url_parts.query if url_parts.query else '')
            link['href'] = urljoin(proxy_domain, uri)

    content = replace_entities(str(soup))
    if app.use_cache:
        app.cache.store(url, 'text/html', content)
    return content


manager.add_command('runserver', ArgumentsParser())


if __name__ == '__main__':
    manager.run()
