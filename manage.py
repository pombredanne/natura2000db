#!/usr/bin/env python

import sys
import os
import logging
from path import path
import flask
import flaskext.script
import jinja2
import babel.support
import naturasites.schema
import naturasites.views
from naturasites.storage import get_db
import tinygis.views
import auth


default_config = {
    'DEBUG': False,
    'ERROR_LOG_FILE': None,

    'HTTP_LISTEN_HOST': '127.0.0.1',
    'HTTP_LISTEN_PORT': 5000,

    'HTTP_PROXIED': False,
    'HTTP_CHERRYPY': False,
    'STORAGE_ENGINE': 'solr',

    'ZOPE_TEMPLATE_CACHE': False,
    'ZOPE_TEMPLATE_PATH': None,
    'ZOPE_TEMPLATE_LIST': ['frame.html'],
}


_i18n_path = path(__file__).parent/'i18n'
translations = babel.support.Translations.load(_i18n_path, ['ro'])


def create_app():
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.update(default_config)
    app.config.from_pyfile("settings.py", silent=True)

    app.jinja_options = app.jinja_options.copy()
    app.jinja_options['extensions'] += ['jinja2.ext.i18n', 'jinja2.ext.do']

    template_loader = app.create_global_jinja_loader()
    if app.config["ZOPE_TEMPLATE_PATH"]:
        from naturasites.loader import ZopeTemplateLoader
        template_loader = ZopeTemplateLoader(template_loader,
                                             app.config["ZOPE_TEMPLATE_PATH"],
                                             app.config["ZOPE_TEMPLATE_CACHE"],
                                             app.config["ZOPE_TEMPLATE_LIST"])
    app.jinja_options['loader'] = template_loader

    if 'STATIC_URL_MAP' in app.config:
        from werkzeug.wsgi import SharedDataMiddleware
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app,
                                            app.config['STATIC_URL_MAP'])

    naturasites.views.register(app)
    tinygis.views.register(app)
    auth.register(app)

    app.jinja_env.install_gettext_translations(translations)

    return app


manager = flaskext.script.Manager(create_app)


@manager.option('--indent', '-i', default=False, action='store_true')
@manager.option('--mysql-login', default='root:',
                help="MySQL login (username:password)")
def accessdb_mjson(indent=False, mysql_login='root:'):
    logging.getLogger('migrations.from_access').setLevel(logging.INFO)

    from migrations.from_access import load_from_sql, verify_data
    kwargs = {'indent': 2} if indent else {}
    [mysql_user, mysql_pw] = mysql_login.split(':')
    for doc in verify_data(load_from_sql(mysql_user, mysql_pw)):
        flask.json.dump(doc, sys.stdout, **kwargs)
        sys.stdout.write('\n')


@manager.command
def import_mjson():
    logging.getLogger('storage').setLevel(logging.INFO)

    def batched(iterator, count=10):
        batch = []
        for value in iterator:
            batch.append(value)
            if len(batch) >= count:
                yield batch
                batch = []
        if batch:
            yield batch

    def read_json_lines(stream):
        for line in stream:
            yield flask.json.loads(line)

    def load_document(data):
        doc = naturasites.schema.SpaDoc(data)
        assert doc.validate(), '%s does not validate' % data['section1']['code']
        assert doc.value == data, 'failed round-tripping the json data'
        return doc

    db = get_db(create_app())

    for batch in batched(load_document(d) for d in read_json_lines(sys.stdin)):
        db.save_document_batch(batch)
        sys.stdout.write('.')
        sys.stdout.flush()

    print ' done'


@manager.command
def species_to_json():
    values = set()
    db = get_db()

    search =  naturasites.views._db_search(naturasites.schema.Search.from_flat({}), facets=True)
    for d in search["docs"]:
        doc = db.load_document(d["id"])
        codes_and_labels = []

        for specie in ("species_bird", "species_bird_extra", "species_mammal",
                       "species_reptile", "species_fish", "species_invertebrate",
                       "species_plant"):
            for s in doc["section3"][specie]:
                values.add((s["code"].value, s["name"].value.strip().lower()))

        for s in doc["section3"]["species_other"]:
            values.add((s["code"].value,
                        s["scientific_name"].value.strip().lower()))

    print flask.json.dumps(dict(values), indent=4)

@manager.command
def runserver(verbose=False):
    app = create_app()

    if verbose:
        storage_logger = logging.getLogger('storage')
        storage_logger.setLevel(logging.DEBUG)
        storage_handler = logging.StreamHandler()
        storage_handler.setLevel(logging.DEBUG)
        storage_logger.addHandler(storage_handler)

    if app.config['ERROR_LOG_FILE'] is not None:
        logging.basicConfig(filename=app.config['ERROR_LOG_FILE'],
                            loglevel=logging.ERROR)

    if app.config['HTTP_PROXIED']:
        from revproxy import ReverseProxied
        app.wsgi_app = ReverseProxied(app.wsgi_app)

    if app.config['HTTP_CHERRYPY']:
        from cherrypy import wsgiserver
        listen = (app.config['HTTP_LISTEN_HOST'], app.config['HTTP_LISTEN_PORT'])
        server = wsgiserver.CherryPyWSGIServer(listen, app.wsgi_app)
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()

    else:
        app.run(app.config['HTTP_LISTEN_HOST'])


if __name__ == '__main__':
    manager.run()
