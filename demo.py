#!/usr/bin/env python
# encoding: utf-8

import flask
from flatland.out.markup import Generator
from schema import SpaDoc
from storage import MongoStorage
from widgets import WidgetDispatcher


app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'demo'

import os.path
app.config['STORAGE_PATH'] = os.path.join(os.path.dirname(__file__),
                                          'data', 'documents')

_my_extensions = app.jinja_options['extensions'] + ['jinja2.ext.do']
app.jinja_options = dict(app.jinja_options, extensions=_my_extensions)
app.jinja_env.globals['form_generator'] = Generator('html')
app.jinja_env.globals['widget'] = WidgetDispatcher(app.jinja_env)


from flatland.signals import validator_validated
from flatland.schema.base import NotEmpty
@validator_validated.connect
def validated(sender, element, result, **kwargs):
    if sender is NotEmpty:
        if not result:
            element.add_error("required")


def get_db():
    return MongoStorage('chm-forms-rio')


@app.route('/')
def index():
    db = get_db()
    return flask.render_template('index.html', doc_id_list=db.document_ids())


@app.route('/new', methods=['GET', 'POST'])
@app.route('/edit', methods=['GET', 'POST'])
def edit():
    doc_id = flask.request.args.get('doc_id', None)
    db = get_db()

    if flask.request.method == 'POST':
        doc = SpaDoc.from_flat(flask.request.form.to_dict())

        if doc.validate():
            doc_id = db.save_document(doc_id, doc.value)
            flask.flash("Document %r saved" % doc_id)
            return flask.redirect('/')

        else:
            flask.flash("Errors in document")

    else:
        if doc_id is None:
            doc = SpaDoc()
        else:
            doc = SpaDoc(db.load_document(doc_id))

    return flask.render_template('edit.html', doc=doc)


if __name__ == '__main__':
    from revproxy import ReverseProxied
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.run(debug=True)
